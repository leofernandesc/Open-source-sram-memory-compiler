#!/usr/bin/env python3
"""Check the frozen masks with Magic and parameter-aware primitive-MOS LVS.

Use tools/sram-eda python3 tools/verify_phase1_physical.py. This performs
connectivity extraction only; it never runs extresist or regenerates PEX.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/'release/phase1'
MAGIC_RC=Path('/opt/pdks/sky130A/libs.tech/magic/sky130A.magicrc')
NETGEN_SETUP=Path('/opt/pdks/sky130A/libs.tech/netgen/sky130A_setup.tcl')
MODELS={'sky130_fd_pr__nfet_01v8':'nmos','sky130_fd_pr__pfet_01v8':'pmos'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(command, cwd, log, input_text=None):
    result=subprocess.run(command,cwd=cwd,input=input_text,text=True,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
    log.write_text(result.stdout)
    if result.returncode:
        raise RuntimeError(f'{command[0]} returned {result.returncode}: {log}')
    return result.stdout


def joined(text):
    lines=[]
    for line in text.splitlines():
        if line.startswith('+') and lines:
            lines[-1]+=' '+line[1:].strip()
        else:
            lines.append(line)
    return lines


def netlist(text, name):
    text='\n'.join(joined(text))
    header=re.search(r'(?mi)^(?:\*\*)?\.subckt\s+\S+\s+([^\n]+)',text)
    if not header:
        raise ValueError('Missing subcircuit header')
    pins=header.group(1).split()
    devices=[]
    for line in joined(text):
        if re.match(r'(?i)^X\S+\s',line) and any(m in line for m in MODELS):
            devices.append(line)
    return '.subckt '+name+' '+' '.join(pins)+'\n'+'\n'.join(devices)+'\n.ends '+name+'\n'


def primitives(text, name, fault=None):
    """Map four-terminal foundry wrappers to M devices, preserving D/G/S/B/W/L.

    Both input files express W/L in micrometres. No W/L values are rounded.
    Area/perimeter and PCell-generation options are outside this LVS contract.
    nf and multiplicity must be one; other values require a new normalization.
    """
    text='\n'.join(joined(text))
    header=re.search(r'(?mi)^\.subckt\s+\S+\s+([^\n]+)',text)
    pins=header.group(1).split()
    result=[f'.model {m} {t}' for m,t in MODELS.items()]
    result.append('.subckt '+name+' '+' '.join(pins))
    count=0
    for line in joined(text):
        if not re.match(r'(?i)^X\S+\s',line):
            continue
        fields=line.split()
        if len(fields)<6 or fields[5] not in MODELS:
            raise ValueError(f'Unsupported instance: {line}')
        params=dict((k.lower(),v.strip("'\"")) for k,v in
                    re.findall(r'(\w+)=([^\s]+)',line))
        if any(float(params.get(k,'1'))!=1 for k in ('nf','m','mult')):
            raise ValueError('Only unit-finger, unit-multiplicity leaves are supported')
        width=float(params['w'])
        length=float(params['l'])
        if count==0 and fault=='width':
            width*=1.2
        if count==0 and fault=='length':
            length*=1.2
        if count==0 and fault=='gate':
            fields[2]='PHASE1_FAULT_GATE'
        if count==0 and fault=='bulk':
            fields[4]='PHASE1_FAULT_BULK'
        if count==0 and fault=='model':
            fields[5]=next(m for m in MODELS if m!=fields[5])
        result.append('M'+fields[0][1:]+' '+' '.join(fields[1:6])+
                      f' w={width:.12g}u l={length:.12g}u')
        count+=1
    result.append('.ends '+name)
    return '\n'.join(result)+'\n',count,pins


def pex_connectivity(text,name):
    """Short only extracted parasitic R networks for a connectivity binding check.

    This is not an electrical PEX simulation. The stored PEX remains untouched.
    The selected leaves contain no intentional passive resistors.
    """
    lines=joined(text)
    pins=re.search(r'(?mi)^\.subckt\s+\S+\s+([^\n]+)',text).group(1).split()
    parent={}
    def find(node):
        parent.setdefault(node,node)
        if parent[node]!=node:
            parent[node]=find(parent[node])
        return parent[node]
    for line in lines:
        if re.match(r'(?i)^R\S+\s',line):
            fields=line.split()
            a,b=find(fields[1]),find(fields[2])
            parent[b]=a
    groups={}
    for node in list(parent):
        groups.setdefault(find(node),[]).append(node)
    aliases={}
    for nodes in groups.values():
        boundary=[n for n in nodes if n in pins]
        if len(boundary)>1:
            raise ValueError(f'PEX resistively shorts independent ports: {boundary}')
        representative=boundary[0] if boundary else sorted(nodes)[0]
        aliases.update({n:representative for n in nodes})
    devices=[]
    for line in lines:
        if re.match(r'(?i)^X\S+\s',line):
            fields=line.split()
            fields[1:5]=[aliases.get(n,n) for n in fields[1:5]]
            devices.append(' '.join(fields))
    return '.subckt '+name+' '+' '.join(pins)+'\n'+'\n'.join(devices)+'\n.ends '+name+'\n'


def make_symbol(name,pins):
    # Pin box order, rather than display position, defines SPICE pin order.
    height=20*(len(pins)+1)
    lines=['v {xschem version=3.4.6 file_version=1.2}',
        'K {type=subcircuit\nformat="@name @pinlist @symname"\ntemplate="name=x1"\n}',
        f'B 4 -130 {-height//2} 130 {height//2} {{}}',
        'T {@symname} -120 0 0 0 0.25 0.25 {}',
        f'T {{@name}} 0 {-height//2-20} 0 0 0.2 0.2 {{}}']
    for i,pin in enumerate(pins):
        y=-height//2+20*(i+1)
        lines.extend([f'B 5 -152.5 {y-2.5} -147.5 {y+2.5} {{name={pin} dir=inout}}',
                      f'L 7 -150 {y} -130 {y} {{}}',
                      f'T {{{pin}}} -125 {y-4} 0 0 0.2 0.2 {{}}'])
    return '\n'.join(lines)+'\n'


def matched(text):
    return ('Circuits match uniquely.' in text and not
        re.search(r'(?i)property errors|do not match|black.box|placeholder|failed to open',text))


def verify(name,item,negative_controls):
    directory=RELEASE/'verification'/name
    directory.mkdir(parents=True,exist_ok=True)
    for info in item['files'].values():
        if sha(ROOT/info['path'])!=info['sha256']:
            raise ValueError(f'{name}: frozen input changed: {info["path"]}')
    schematic=ROOT/item['files']['schematic']['path']
    mask=ROOT/item['files']['layout']['path']
    library='set XSCHEM_LIBRARY_PATH [join [list "$XSCHEM_SHAREDIR/xschem_library" "$XSCHEM_SHAREDIR/xschem_library/devices" "/opt/pdks/sky130A/libs.tech/xschem"] ":"]'
    with tempfile.TemporaryDirectory(prefix=f'phase1-{name}-') as scratch:
        scratch=Path(scratch)
        run(['xschem','-x','-q','-n','--tcl',library,'-o',str(scratch),str(schematic)],
             ROOT,directory/'xschem.txt')
        canonical=netlist((scratch/f'{name}.spice').read_text(),name)
        source=schematic.with_suffix('.spice')
        source.write_text('* Xschem-derived canonical electrical leaf; standalone stimuli omitted.\n'+canonical)
        normalized,count,pins=primitives(canonical,name)
        if count!=item['expected_mos']:
            raise ValueError(f'{name}: expected {item["expected_mos"]} devices, got {count}')
        symbol=schematic.with_suffix('.sym')
        if name!='row_decoder':
            symbol.write_text(make_symbol(name,pins))
        (directory/'schematic_mos.spice').write_text(normalized)
        shutil.copy2(mask,scratch/f'{name}.mag')
        commands=f'''load {name}
select top cell
expand
drc euclidean on
drc style drc(full)
drc on
drc check
drc catchup
set findings [drc listall why]
puts "PHASE1_DRC_GROUPS=[llength $findings]"
puts "PHASE1_DRC_DETAILS=$findings"
extract do local
extract all
ext2spice lvs
ext2spice scale off
ext2spice -o {directory}/layout_extracted.spice
quit -noprompt
'''
        (directory/'verify.tcl').write_text(commands)
        drc=run(['magic','-dnull','-noconsole','-rcfile',str(MAGIC_RC)],scratch,
                directory/'magic.txt',commands)
        markers=re.findall(r'PHASE1_DRC_GROUPS=(\d+)',drc)
        if markers!=['0']:
            raise ValueError(f'{name}: DRC did not pass: {markers}')
        extracted=(directory/'layout_extracted.spice').read_text()
        normalized_layout,layout_count,layout_pins=primitives(extracted,name)
        if count!=layout_count or set(pins)!=set(layout_pins):
            raise ValueError(f'{name}: device count or pin set differs in extraction')
        (directory/'layout_mos.spice').write_text(normalized_layout)
        report=directory/'lvs_report.txt'
        run(['netgen','-batch','lvs',f'{directory}/layout_mos.spice {name}',
            f'{directory}/schematic_mos.spice {name}',str(NETGEN_SETUP),str(report)],
            scratch,directory/'netgen.txt')
        lvs=report.read_text()
        if not matched(lvs):
            raise ValueError(f'{name}: parameter-aware LVS failed: {report}')
        faults={}
        if negative_controls:
            for fault in ('width','length','gate','bulk','model'):
                fault_path=directory/f'negative_{fault}.spice'
                fault_path.write_text(primitives(canonical,name,fault)[0])
                fault_report=directory/f'negative_{fault}_report.txt'
                run(['netgen','-batch','lvs',f'{directory}/layout_mos.spice {name}',
                     f'{fault_path} {name}',str(NETGEN_SETUP),str(fault_report)],
                    scratch,directory/f'negative_{fault}_console.txt')
                if matched(fault_report.read_text()):
                    raise ValueError(f'{name}: faulty {fault} input incorrectly passed LVS')
                faults[fault]='REJECTED_AS_EXPECTED'
        pex=ROOT/item['files']['pex']['path']
        pex_mos,pex_count,pex_pins=primitives(pex_connectivity(pex.read_text(),name),name)
        if pex_count!=count or set(pex_pins)!=set(pins):
            raise ValueError(f'{name}: PEX pin/device count mismatch')
        (directory/'pex_connectivity_mos.spice').write_text(pex_mos)
        pex_report=directory/'pex_binding_report.txt'
        run(['netgen','-batch','lvs',f'{directory}/pex_connectivity_mos.spice {name}',
             f'{directory}/schematic_mos.spice {name}',str(NETGEN_SETUP),str(pex_report)],
             scratch,directory/'pex_binding_console.txt')
        if not matched(pex_report.read_text()):
            raise ValueError(f'{name}: existing PEX connectivity/geometry binding failed')
        result=dict(status='PASS',cell=name,mos_count=count,pins=pins,drc_groups=0,
            lvs='UNIQUE_MATCH_WITH_W_L_AND_TERMINALS',negative_controls=faults,
            pex_connectivity_binding='PASS_PARASITIC_RESISTORS_COLLAPSED',
            source_sha256=sha(source),symbol_sha256=sha(symbol),
            layout_sha256=sha(mask),pex_sha256=sha(ROOT/item['files']['pex']['path']),
            extracted_sha256=sha(directory/'layout_extracted.spice'),
            pdk_setup_sha256=sha(NETGEN_SETUP),magic_rc_sha256=sha(MAGIC_RC),
            completed_utc=datetime.now(timezone.utc).isoformat())
        result['evidence_sha256']={p.name:sha(p) for p in sorted(directory.iterdir())
                                  if p.is_file() and p.name!='result.json'}
        (directory/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cells',nargs='+')
    parser.add_argument('--skip-negative-controls',action='store_true')
    args=parser.parse_args()
    manifest=json.loads((RELEASE/'manifest.json').read_text())
    selected=args.cells or list(manifest['cells'])
    results=[]
    for name in selected:
        print(f'Checking {name}...',flush=True)
        try:
            result=verify(name,manifest['cells'][name],not args.skip_negative_controls)
            results.append(result)
            print(f'{name}: DRC 0, parameter-aware LVS PASS, {result["mos_count"]} MOS',flush=True)
        except Exception as error:
            failed=dict(cell=name,status='FAIL',error=str(error))
            results.append(failed)
            (RELEASE/'verification'/name/'result.json').write_text(json.dumps(failed,indent=2)+'\n')
            print(f'{name}: FAIL: {error}',flush=True)
    output=RELEASE/'verification'
    output.mkdir(exist_ok=True)
    summary=dict(status='PASS' if all(r['status']=='PASS' for r in results) else 'FAIL',
        cells=results,tools={tool:dict(path=shutil.which(tool),sha256=sha(shutil.which(tool)))
                            for tool in ('magic','netgen','xschem')},
        scripts_sha256={script:sha(ROOT/'tools'/script) for script in
            ('prepare_phase1_release.py','verify_phase1_physical.py','verify_phase1_g7_support.py','audit_phase1_release.py')},
        scope='Frozen flat leaf masks; connectivity extraction, DRC(full), MOS terminal/W/L LVS; existing PEX unchanged.')
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    if summary['status']=='PASS' and set(selected)==set(manifest['cells']):
        for name,item in manifest['cells'].items():
            schematic=ROOT/item['files']['schematic']['path']
            for kind,suffix in [('spice','.spice'),('symbol','.sym')]:
                path=schematic.with_suffix(suffix)
                item['files'][kind]=dict(path=str(path.relative_to(ROOT)),sha256=sha(path))
            item['physical_result']=str((output/name/'result.json').relative_to(ROOT))
            item['pin_order']=next(r['pins'] for r in results if r['cell']==name)
        manifest['physical_scope']='Six selected flat masks: DRC(full), primitive-MOS W/L/terminal LVS, negative controls and existing-PEX connectivity binding.'
        (RELEASE/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
        checksums={str(p.relative_to(ROOT)):sha(p) for p in sorted(RELEASE.rglob('*'))
                   if p.is_file() and p.name!='checksums.json'}
        (RELEASE/'checksums.json').write_text(json.dumps(checksums,indent=2)+'\n')
    raise SystemExit(0 if summary['status']=='PASS' else 1)


if __name__=='__main__':
    main()
