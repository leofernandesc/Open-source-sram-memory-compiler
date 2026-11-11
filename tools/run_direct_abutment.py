#!/usr/bin/env python3
"""Independent candidate: direct bitcell abutment; never updates old selectors."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

from phase2_resources import preflight
from run_phase2_physical_pilot import normal_mos, tcl as pilot_helpers

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'release/phase1/cells/bitcell_6t/bitcell_6t.mag'
SPICE = ROOT/'release/phase1/cells/bitcell_6t/bitcell_6t.spice'
RC = Path('/opt/pdks/sky130A/libs.tech/magic/sky130A.magicrc')
SETUP = Path('/opt/pdks/sky130A/libs.tech/netgen/sky130A_setup.tcl')
WIDTH, HEIGHT = 3450, 2800  # 5-nm internal units; boundaries include shared rails.
PINS = {'VDD':('metal4',2950,100),'BL':('metal4',1850,100),
        'BLB':('metal4',2530,100),'VSS':('metal4',3150,100),
        'WL':('metal3',100,450)}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(argv, cwd, log, stdin=None, timeout=240):
    result=subprocess.run(list(map(str,argv)),cwd=cwd,input=stdin,text=True,
                          stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                          env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'),timeout=timeout)
    log.write_text(result.stdout)
    if result.returncode:raise RuntimeError(f'{argv[0]} exit {result.returncode}: {log}')
    return result.stdout


def helpers():
    text=pilot_helpers();return text[text.index('proc rect'):text.index('# Custom labels')]


def cell_source():
    """Keep every pre-M3 rectangle byte-equivalent under a uniform translation.

    Internal Q/QB M3 bars are clipped. BL/BLB M3 bars become local landings;
    vertical M4 rails connect at staggered via3 sites, away from existing via2.
    The 14-um height provides rule clearance around unshared M3 end landings;
    M4 terminals themselves reach both boundaries, without inter-cell gaps.
    """
    out=['magic','tech sky130A','magscale 1 2','timestamp 0'];layer=''
    for line in SOURCE.read_text().splitlines():
        if line.startswith('<<'):layer=line[3:-3]
        if layer in ('metal3','labels','end'):continue
        if line.startswith('<<'):out.append(line)
        elif line.startswith('rect '):
            x1,y1,x2,y2=map(int,line.split()[1:]);out.append(f'rect {x1+450} {y1+3050} {x2+450} {y2+3050}')
    out+=['<< end >>']
    return '\n'.join(out)+'\n'


def rails_tcl():
    # Three horizontal inter-cell nets, two strictly local storage nets.
    lines=[]
    for x1,x2,y in [(0,WIDTH,2650),(0,WIDTH,600),(0,WIDTH,450),
                   (870,2110,2500),(230,2750,2350)]:
        lines.append(f'rect metal3 {x1} {y-42} {x2} {y+42}')
    # Local BL/BLB pads include the original via2 landing plus the offset via3.
    lines+=['rect metal3 1630 252 1910 348','rect metal3 2250 102 2590 198']
    for x,y in [(2950,2650),(3150,600),(1850,300),(2530,150)]:
        lines += [f'promote34 {x} {y}',f'rect metal4 {x-60} 0 {x+60} {HEIGHT}']
    for index,(name,(layer,x,y)) in enumerate(PINS.items()):
        lines += [f'box values {x-12} {y-12} {x+12} {y+12}',f'label {name} center {layer}',f'port make {index} n']
    lines += [f'property FIXED_BBOX "0 0 {WIDTH} {HEIGHT}"']
    return '\n'.join(lines)+'\n'


def reference(rows, cols, top):
    leaf,count=normal_mos(SPICE.read_text(),'bitcell_6t');assert count==6
    definitions=[l for l in leaf.splitlines() if l.startswith('.model')]
    cards=[l.split() for l in leaf.splitlines() if l.startswith('M')]
    ports=['VDD','VSS',*[f'WL{r}' for r in range(rows)],
           *[n for b in range(cols) for n in (f'BL{b}',f'BLB{b}')]]
    if rows==cols==1 and top=='bitcell_6t_abut':
        ports=list(PINS);bindings={'WL':'WL','BL':'BL','BLB':'BLB'}
    result=definitions+['.subckt '+top+' '+' '.join(ports)]
    for r in range(rows):
        for b in range(cols):
            m={'VDD':'VDD','VSS':'VSS','WL':f'WL{r}','BL':f'BL{b}','BLB':f'BLB{b}',
               'Q':f'Q_{r}_{b}','QB':f'QB_{r}_{b}'}
            if top=='bitcell_6t_abut':m.update(bindings)
            for f in cards:result.append(f'{f[0]}_r{r}_b{b} '+' '.join(m[n] for n in f[1:5])+' '+' '.join(f[5:]))
    return '\n'.join(result+['.ends '+top])+'\n',ports


def physical_checks(build, top, ports, expected, output, prefix='candidate'):
    commands=[f'save {top}','select top cell','expand',f'flatten {top}_flat',f'load {top}_flat',
              'select top cell','expand','drc euclidean on','drc style drc(full)',
              'drc on','drc check','drc catchup',
              'puts "ABUT_DRC=[llength [drc listall why]]"','puts "ABUT_DETAILS=[drc listall why]"',
              f'save {top}_flat',f'load {top}',f'gds write {top}.gds',
              f'load {top}_flat','extract all','ext2spice lvs','ext2spice scale off',
              'ext2spice -o extracted.spice','quit -noprompt']
    tcl=(build/'generate.tcl').read_text()+'\n'+'\n'.join(commands)+'\n'
    (output/'generate.tcl').write_text(tcl)
    text=run(['magic','-dnull','-noconsole','-rcfile',RC],build,output/'magic.txt',tcl)
    if re.findall(r'^ABUT_DRC=(\d+)$',text,re.M)!=['0']:raise ValueError('Full DRC failed; see native details')
    extracted=(build/'extracted.spice').read_text()
    header=next((l.split()[2:] for l in extracted.splitlines() if l.lower().startswith('.subckt ')),None)
    if header is None or set(header)!=set(ports) or len(header)!=len(ports):
        raise ValueError(f'Extracted top has missing/wrong formal ports: {header}')
    normalized,count=normal_mos(extracted,top)
    if count!=expected:raise ValueError(f'Wrong expanded MOS count: {count}, expected {expected}')
    (output/'extracted.spice').write_text(extracted);(output/'layout_mos.spice').write_text(normalized)
    shutil.copyfile(build/(top+'_flat.ext'),output/'flat.ext')
    shutil.copyfile(build/(top+'.gds'),output/(top+'.gds'))
    ref=output/'reference.spice'
    text=run(['netgen','-batch','lvs',f'{output}/layout_mos.spice {top}',f'{ref} {top}',SETUP,output/'lvs.txt'],build,output/'netgen.txt')
    report=(output/'lvs.txt').read_text()
    if ('Final result: Circuits match uniquely.' not in report or
        re.search(r'(?i)property errors|do not match|black.box|placeholder|failed to open',report)):
        raise ValueError('Expanded dimension/body-aware LVS failed')
    shutil.copyfile(build/(top+'.mag'),output/(top+'.mag'))
    return dict(drc_groups=0,expanded_mos=count,lvs='UNIQUE_MATCH_W_L_TERMINALS',ports=ports)


def execute(stage, output, leaf_report=None):
    if output.exists():raise ValueError('Use a new output directory; historical results are never overwritten')
    output.mkdir(parents=True)
    record=dict(status='RUNNING',stage=stage,base_commit='3d148806ba16fcf6d9c5e46d1cefb975dfcc11d6',
                resources=preflight(ROOT),inputs={str(p.relative_to(ROOT)):sha(p) for p in [SOURCE,SPICE,Path(__file__)]},
                pdk={str(p):sha(p) for p in [RC,SETUP]})
    try:
        build_root=ROOT/'build/direct_abutment';build_root.mkdir(parents=True,exist_ok=True)
        build=Path(tempfile.mkdtemp(prefix=stage+'-',dir=build_root));record['build_directory']=str(build.relative_to(ROOT))
        if stage=='leaf':
            top='bitcell_6t_abut';rows=cols=1
            (build/(top+'.mag')).write_text(cell_source())
            script='snap internal\npath search +.\nload '+top+'\n'+helpers()+rails_tcl()
        else:
            if leaf_report is None:raise ValueError('Pilot requires a passing new leaf report')
            state=json.loads((leaf_report/'results.json').read_text())
            if state['status']!='PASS_PHYSICAL':raise ValueError('Leaf qualification is incomplete')
            for n,h in state['artifacts'].items():
                if sha(leaf_report/n)!=h:raise ValueError('Leaf artifact changed: '+n)
            record['inputs'][str((leaf_report/'results.json').relative_to(ROOT))]=sha(leaf_report/'results.json')
            shutil.copyfile(leaf_report/'bitcell_6t_abut.mag',build/'bitcell_6t_abut.mag')
            top='array_2x2_abut';rows=cols=2
            script='snap internal\npath search +.\nload '+top+'\n'+helpers()
            for r in range(rows):
                for b in range(cols):script+=f'getcell bitcell_6t_abut child 0 0 parent {b*WIDTH} {r*HEIGHT}\n'
            for i,name in enumerate(['VDD','VSS',*[f'WL{r}' for r in range(rows)],*[n for b in range(cols) for n in (f'BL{b}',f'BLB{b}')]]):
                if name.startswith('WL'):layer='metal3';x=100;y=450+int(name[2:])*HEIGHT
                else:
                    pin=name if name in ('VDD','VSS') else re.sub(r'\d+$','',name)
                    layer,x,y=PINS[pin];x+=0 if name in ('VDD','VSS') else int(re.search(r'\d+$',name)[0])*WIDTH
                # Parent labels need local conducting geometry. Without this
                # landing Magic moves labels over child-only paint to space.
                script+=f'rect {layer} {x-10} {y-10} {x+10} {y+10}\nbox values {x-10} {y-10} {x+10} {y+10}\nlabel {name} center {layer}\nport make {i} n\n'
            script+=f'save {top}\n'
        ref,ports=reference(rows,cols,top);(output/'reference.spice').write_text(ref)
        (build/'generate.tcl').write_text(script)
        result=physical_checks(build,top,ports,rows*cols*6,output)
        record.update(status='PASS_PHYSICAL',**result,width_um=WIDTH*.005*cols,height_um=HEIGHT*.005*rows,
                      abutment='Zero placement gap; horizontal WL/power and vertical BL/BLB/power touch at explicit tile boundaries')
    except Exception as e:
        record.update(status='FAIL',error=f'{type(e).__name__}: {e}')
    record['artifacts']={p.name:sha(p) for p in output.iterdir() if p.is_file() and p.name!='results.json'}
    (output/'results.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
    return 0 if record['status']=='PASS_PHYSICAL' else 1


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stage',choices=['leaf','pilot'],required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--leaf-report',type=Path)
    a=p.parse_args();output=(ROOT/a.output).resolve()
    if not output.is_relative_to(ROOT/'reports/direct_abutment'):p.error('New results must be under reports/direct_abutment')
    return execute(a.stage,output,(ROOT/a.leaf_report).resolve() if a.leaf_report else None)


if __name__=='__main__':raise SystemExit(main())
