#!/usr/bin/env python3
"""Small custom-WL/HD-inverter physical pilot; connectivity extraction, no RC PEX."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from run_digital_regression import atomic_text, output_lock

ROOT = Path(__file__).resolve().parents[1]
PDK = Path('/opt/pdks/sky130A')
HD = PDK / 'libs.ref/sky130_fd_sc_hd'
RC = PDK / 'libs.tech/magic/sky130A.magicrc'


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def normal_mos(text, name):
    """PDK wrapper W/L are micron-valued expressions, including SI suffixes.

    For example 650000u evaluates to 0.65 in a wrapper's W parameter;
    the normalized primitive MOS then requires w=0.65u metres.
    """
    lines = []
    for line in text.splitlines():
        if line.startswith('+') and lines:
            lines[-1] += ' ' + line[1:].strip()
        else:
            lines.append(line)
    def number(value):
        match = re.fullmatch(r'([\d.eE+-]+)([a-zA-Z]*)', value)
        if not match:
            raise ValueError(f'Non-numeric geometry: {value}')
        scale = {'':1, 'u':1e-6, 'n':1e-9, 'm':1e-3}
        return float(match[1]) * scale[match[2].lower()]
    header = re.search(r'(?mi)^\.subckt\s+\S+\s+(.+)$', '\n'.join(lines))
    if not header:
        raise ValueError('Missing subckt')
    result = ['.model sky130_fd_pr__nfet_01v8 nmos',
              '.model sky130_fd_pr__pfet_01v8 pmos',
              '.model sky130_fd_pr__pfet_01v8_hvt pmos',
              '.model sky130_fd_pr__special_nfet_01v8 nmos',
              '.subckt ' + name + ' ' + header[1]]
    count = 0
    for line in lines:
        if not re.match(r'^[xX]\S+\s', line):
            continue
        f = line.split()
        if f[5] not in ('sky130_fd_pr__nfet_01v8','sky130_fd_pr__pfet_01v8',
                        'sky130_fd_pr__pfet_01v8_hvt','sky130_fd_pr__special_nfet_01v8'):
            raise ValueError('Expected flattened primitive foundry wrapper: ' + line)
        params = dict((k.lower(), v) for k,v in re.findall(r'(\w+)=([^\s]+)', line))
        if any(number(params.get(k,'1')) != 1 for k in ('nf','m','mult')):
            raise ValueError('Unsupported MOS multiplicity')
        result.append('M' + f[0][1:] + ' ' + ' '.join(f[1:6]) +
                      f' w={number(params["w"]):.12g}u l={number(params["l"]):.12g}u')
        count += 1
    result.append('.ends ' + name)
    return '\n'.join(result) + '\n', count


def tcl():
    return '''snap internal
path search +.
path search +/opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd/mag
load pilot
getcell wl_driver child 0 0 parent 600 4000
getcell sky130_fd_sc_hd__inv_1 child 0 0 parent 5000 2500
getcell sky130_fd_sc_hd__tapvpwrvgnd_1 child 0 0 parent 4908 2500
proc rect {layer x1 y1 x2 y2} {
    box values $x1 $y1 $x2 $y2
    paint $layer
}
proc promote34 {x y} {
    rect metal3 [expr {$x-48}] [expr {$y-48}] [expr {$x+48}] [expr {$y+48}]
    rect metal4 [expr {$x-60}] [expr {$y-48}] [expr {$x+60}] [expr {$y+48}]
    box values [expr {$x-32}] [expr {$y-32}] [expr {$x+32}] [expr {$y+32}]
    contact via3
}
proc via12 {x y} {
    rect metal1 [expr {$x-34}] [expr {$y-34}] [expr {$x+34}] [expr {$y+34}]
    rect metal2 [expr {$x-34}] [expr {$y-34}] [expr {$x+34}] [expr {$y+34}]
    box values [expr {$x-26}] [expr {$y-26}] [expr {$x+26}] [expr {$y+26}]
    contact via1
}
proc via23 {x y} {
    rect metal2 [expr {$x-48}] [expr {$y-48}] [expr {$x+48}] [expr {$y+48}]
    rect metal3 [expr {$x-60}] [expr {$y-48}] [expr {$x+60}] [expr {$y+48}]
    box values [expr {$x-30}] [expr {$y-30}] [expr {$x+30}] [expr {$y+30}]
    contact via2
}
proc pin {name index x y} {
    box values [expr {$x-20}] [expr {$y-20}] [expr {$x+20}] [expr {$y+20}]
    label $name center metal4
    port make $index n
}
# Custom labels are at x=-230 before placement, on five distinct M3 bars.
foreach {y name idx} {3700 VDD 1 400 VSS 2 3500 IN 3 1800 LINK 0} {
    promote34 370 $y
}
# Stagger contact layers: overlapping different Magic contact types would
# cut holes in the contacts. Escape LI -> M1 -> M2 -> M3 -> M4 separately.
rect locali 4883 2721 5106 2755
rect locali 5164 2789 5417 2823
foreach {x y} {4900 2738 5400 2806} {
    rect metal1 [expr {$x-32}] [expr {$y-32}] [expr {$x+32}] [expr {$y+32}]
    box values [expr {$x-17}] [expr {$y-17}] [expr {$x+17}] [expr {$y+17}]
    contact mcon
}
rect metal1 4766 2712 4926 2764
rect metal1 5374 2780 5534 2832
via12 4800 2738
via12 5500 2806
rect metal2 4466 2704 4834 2772
rect metal2 5466 2772 5834 2840
via23 4500 2738
via23 5800 2806
rect metal3 4240 2690 4560 2786
rect metal3 5740 2758 6060 2854
promote34 4300 2738
promote34 6000 2806
# Tap and inverter share abutting M1 power rails and well ties.
foreach {y escapeY customY} {3044 3300 3700 2500 2200 400} {
    rect metal1 5200 [expr {$y-34}] 6534 [expr {$y+34}]
    via12 6500 $y
    rect metal2 6466 [expr {min($y,$escapeY)-34}] 6534 [expr {max($y,$escapeY)+34}]
    via23 6500 $escapeY
    rect metal3 6440 [expr {$escapeY-48}] 6860 [expr {$escapeY+48}]
    promote34 6800 $escapeY
    rect metal4 6752 [expr {min($escapeY,$customY)-48}] 6848 [expr {max($escapeY,$customY)+48}]
    rect metal4 322 [expr {$customY-48}] 6848 [expr {$customY+48}]
}
rect metal4 322 1752 4348 1848
rect metal4 4252 1752 4348 2786
pin VDD 1 370 3700
pin VSS 2 370 400
pin IN 3 370 3500
pin OUT 4 6000 2806
select top cell
expand
flatten pilot_flat
load pilot_flat
select top cell
expand
drc euclidean on
drc style drc(full)
drc on
drc check
drc catchup
puts "PILOT_DRC=[llength [drc listall why]]"
puts "PILOT_DETAILS=[drc listall why]"
save pilot_flat
# Keep original HD GDS references when streaming the hierarchical pilot.
load pilot
gds write pilot.gds
load pilot_flat
extract all
ext2spice lvs
ext2spice scale off
ext2spice -o pilot_extracted.spice
quit -noprompt
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='reports/phase2/physical_pilot')
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    if not output.is_relative_to(ROOT / 'reports/phase2') or output == ROOT / 'reports/phase2':
        parser.error('Output must be under reports/phase2')
    output.mkdir(parents=True,exist_ok=True)
    with output_lock(output):
        receipt = {'status':'RUNNING', 'scope':'Custom WL plus HD inverter/tap connectivity pilot; no RC PEX',
                   'F2_FIS':'NOT_EVALUATED', 'commands':[]}
        def publish():
            atomic_text(output/'results.json',json.dumps(receipt,indent=2)+'\n')
        publish()
        try:
            build_root = ROOT/'build/phase2'; build_root.mkdir(parents=True,exist_ok=True)
            build = Path(tempfile.mkdtemp(prefix='physical-pilot-',dir=build_root))
            receipt['build_directory']=str(build.relative_to(ROOT))
            def run(argv,log,stdin=None):
                receipt['commands'].append({'argv':[str(a) for a in argv],'cwd':str(build),'log':log})
                p=subprocess.run([str(a) for a in argv],cwd=build,input=stdin,text=True,
                                 capture_output=True,timeout=180)
                atomic_text(output/log,p.stdout+p.stderr)
                if p.returncode: raise RuntimeError(f'{argv[0]} exited {p.returncode}: {log}')
                return p.stdout+p.stderr
            manifest=json.loads((ROOT/'release/phase1_keeper/manifest.json').read_text())
            for kind in ('layout','netlist'):
                info=manifest['cells']['wl_driver']['files'].get(kind)
                if info and digest(ROOT/info['path'])!=info['sha256']:
                    raise ValueError('Frozen WL input changed')
            source=ROOT/'release/phase1/cells/wl_driver/wl_driver.mag'
            shutil.copyfile(source,build/'wl_driver.mag')
            receipt['inputs']={str(source.relative_to(ROOT)):digest(source),str(RC):digest(RC)}
            commands=tcl(); (build/'pilot.tcl').write_text(commands)
            atomic_text(output/'pilot.tcl',commands)
            transcript=run(['magic','-dnull','-noconsole','-rcfile',RC], 'magic.txt',commands)
            receipt['drc_markers']=re.findall(r'^PILOT_DRC=(\d+)$',transcript,re.M)
            for name in ('pilot_flat.mag','pilot_extracted.spice','pilot.gds'):
                if (build/name).exists(): shutil.copyfile(build/name,output/name)
            if receipt['drc_markers']!=['0']:
                raise ValueError('Physical pilot DRC failed; see magic.txt before macro generation')
            leaf=ROOT/'release/phase1/cells/wl_driver/wl_driver.spice'
            hd_spice=HD/'spice/sky130_fd_sc_hd.spice'
            hd_text=hd_spice.read_text()
            inv=re.search(r'(?ms)^\.subckt sky130_fd_sc_hd__inv_1 .*?^\.ends[^\n]*',hd_text)[0]
            wl_normal,nwl=normal_mos(leaf.read_text(),'wl_driver')
            inv_normal,ninv=normal_mos(inv,'sky130_fd_sc_hd__inv_1')
            reference=wl_normal+inv_normal+'''\n.subckt pilot_flat VDD VSS IN OUT
XW VDD VSS IN LINK wl_driver
XI LINK VSS VSS VDD VDD OUT sky130_fd_sc_hd__inv_1
.ends pilot_flat
'''
            extracted,n=normal_mos((build/'pilot_extracted.spice').read_text(),'pilot_flat')
            if n!=6 or nwl!=4 or ninv!=2:
                raise ValueError('Expected four custom and two HD transistors')
            (build/'reference.spice').write_text(reference)
            (build/'layout_mos.spice').write_text(extracted)
            setup=PDK/'libs.tech/netgen/sky130A_setup.tcl'
            def compare(layout, label):
                report=build/(label+'.txt')
                run(['netgen','-batch','lvs',f'{layout} pilot_flat',
                     'reference.spice pilot_flat',setup,report],label+'_console.txt')
                text=report.read_text(); atomic_text(output/(label+'.txt'),text)
                return ('Circuits match uniquely.' in text and not
                        re.search(r'(?i)property errors|do not match|black.box|placeholder|failed to open',text))
            if not compare('layout_mos.spice','lvs'):
                raise ValueError('Pilot parameter-aware LVS failed')
            negatives={}
            for fault in ('gate','width'):
                bad=extracted
                if fault=='gate':
                    lines=bad.splitlines()
                    i=next(i for i,l in enumerate(lines) if l.startswith('M'))
                    f=lines[i].split(); f[2]='INJECTED_GATE'; lines[i]=' '.join(f)
                    bad='\n'.join(lines)+'\n'
                else:
                    bad=re.sub(r'w=([0-9.e+-]+)u',lambda m:f'w={float(m[1])*1.2:.12g}u',bad,count=1)
                filename=f'negative_{fault}.spice'; (build/filename).write_text(bad)
                negatives[fault]='REJECTED' if not compare(filename,'negative_'+fault) else 'MISSED'
            if set(negatives.values())!={'REJECTED'}:
                raise ValueError('LVS missed deliberate defect')
            reimport=build/'reimport'; reimport.mkdir()
            cmds=f'''gds read {build}/pilot.gds
load pilot
select top cell
expand
flatten pilot_flat
load pilot_flat
select top cell
expand
drc euclidean on
drc style drc(full)
drc on
drc check
drc catchup
puts "REIMPORT_DRC=[llength [drc listall why]]"
puts "REIMPORT_DETAILS=[drc listall why]"
extract all
ext2spice lvs
ext2spice scale off
ext2spice -o {build}/reimport_extracted.spice
quit -noprompt
'''
            # A separate Magic process with no live source cell loaded verifies
            # the exported GDS, not the in-memory pre-export geometry.
            (reimport/'verify.tcl').write_text(cmds)
            run(['magic','-dnull','-noconsole','-rcfile',RC],
                'reimport_magic.txt','cd '+str(reimport)+'\n'+cmds)
            text=(output/'reimport_magic.txt').read_text()
            if re.findall(r'^REIMPORT_DRC=(\d+)$',text,re.M)!=['0']:
                raise ValueError('Reimported GDS DRC failed')
            normalized,n=normal_mos((build/'reimport_extracted.spice').read_text(),'pilot_flat')
            (build/'reimport_mos.spice').write_text(normalized)
            if n!=6 or not compare('reimport_mos.spice','reimport_lvs'):
                raise ValueError('Reimported GDS LVS failed')
            for name in ('reference.spice','layout_mos.spice','reimport_extracted.spice','reimport_mos.spice'):
                shutil.copyfile(build/name,output/name)
            receipt['inputs'].update({str(leaf.relative_to(ROOT)):digest(leaf),str(hd_spice):digest(hd_spice),
                                     str(setup):digest(setup),
                                     str(Path(__file__).relative_to(ROOT)):digest(__file__)})
            receipt.update(status='PASS',lvs='UNIQUE_MATCH_W_L_TERMINALS',mos=6,
                           reimport_drc=0,reimport_lvs='UNIQUE_MATCH_W_L_TERMINALS',negative_controls=negatives)
        except Exception as error:
            receipt.update(status='FAIL',error=str(error))
        receipt['artifacts']={p.name:digest(p) for p in output.iterdir()
                              if p.is_file() and p.name not in ('results.json','.run.lock')}
        publish(); print(json.dumps(receipt,indent=2))
        return 0 if receipt['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
