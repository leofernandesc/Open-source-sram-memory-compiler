#!/usr/bin/env python3
"""Route selected 401-MOS leaf fabric; expose unbound glue at named ports.

This intermediate fabric is not the qualified core or public SRAM. Row
qualification/data complements and physical phase/capture cells remain outside.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import phase2_core as core
from run_digital_regression import atomic_text,output_lock
from run_phase2_physical_pilot import normal_mos,digest,tcl as pilot_tcl

ROOT=core.ROOT
RC=Path('/opt/pdks/sky130A/libs.tech/magic/sky130A.magicrc')


def generate(build):
    leaves=core.selected_leaves(); design=core.graph(); core.audit(design)
    fabric=[i for i in design['instances'] if not i['cell'].startswith('sky130_')]
    ports=['VDD','VSS','A0','A1','PCLK','PRECH','SCLK','WE',
           *[f'DIN{b}' for b in range(8)],*[f'DIN_B{b}' for b in range(8)],
           *[f'DOUT{b}' for b in range(8)],*[f'ROW{r}' for r in range(4)],*[f'DEC{r}' for r in range(4)]]
    definitions=[];reference=[]; inputs={}; places={}
    for name,item in leaves.items():
        mask=item['files']['layout'];shutil.copyfile(mask,build/(name+'.mag'))
        source=item['files'].get('netlist',item['files']['schematic'].with_suffix('.spice'))
        normalized,count=normal_mos(source.read_text(),name)
        if count!=item['mos']:raise ValueError('Wrong selected leaf count')
        definitions.append(normalized)
        for p in (mask,source):inputs[str(p.relative_to(ROOT))]=digest(p)
    reference=definitions+['.subckt leaf_fabric '+' '.join(ports)]
    for i in fabric:
        reference.append('X'+i['name']+' '+' '.join(i['pins'][p] for p in leaves[i['cell']]['pins'])+' '+i['cell'])
        name=i['name'];cell=i['cell']
        if cell=='bitcell_6t':
            m=re.fullmatch(r'bit_r(\d)_b(\d)',name); places[name]=(6000*int(m[2]),36000+5000*int(m[1]))
        elif cell=='row_decoder':places[name]=(-27000,26000)
        elif cell=='wl_driver':places[name]=(-7000,35600+5000*int(name[-1]))
        else:places[name]=(6000*int(name[-1]),{'precharge':30000,'sense_amp':23000,'write_driver':15000}[cell])
    reference.append('.ends leaf_fabric')
    (build/'reference.spice').write_text('\n'.join(reference)+'\n')
    script=['snap internal','path search +.','load fabric_hier']
    helpers=pilot_tcl();a=helpers.index('proc rect');b=helpers.index('# Custom labels')
    script.append(helpers[a:b])
    script.append('''proc via45 {x y} {
    rect metal4 [expr {$x-140}] [expr {$y-140}] [expr {$x+140}] [expr {$y+140}]
    rect metal5 [expr {$x-180}] [expr {$y-200}] [expr {$x+180}] [expr {$y+200}]
    box values [expr {$x-118}] [expr {$y-118}] [expr {$x+118}] [expr {$y+118}]
    contact via4
}
''')
    for i in fabric:
        x,y=places[i['name']]
        script.append(f"getcell {i['cell']} child 0 0 parent {x} {y}")
    pin_points={}
    # All selected non-decoder leaves have full-width labelled M3 pin bars.
    # M4 column trunks cross M5 row/control rails only at explicit via45 sites.
    trunks={'BL':600,'BLB':1200,'VDD':1800,'VSS':2400}
    label_coords={}
    for name,item in leaves.items():
        text=item['files']['layout'].read_text()
        label_coords[name]={m[5]:(int(m[1])+int(m[3]))//2 for m in
            re.finditer(r'rlabel metal3 (-?\d+) (-?\d+) (-?\d+) (-?\d+) \d+ (\S+)',text)}
    def yof(cell,pin):
        text=leaves[cell]['files']['layout'].read_text()
        m=re.search(r'rlabel metal3 -?\d+ (-?\d+) -?\d+ (-?\d+) \d+ '+re.escape(pin)+r'\n',text)
        return (int(m[1])+int(m[2]))//2
    for i in fabric:
        cell=i['cell'];x,y=places[i['name']]
        if cell=='row_decoder':continue
        for pin in ('VDD','VSS','BL','BLB'):
            if pin not in i['pins']:continue
            px=x+trunks[pin];py=y+yof(cell,pin)
            script.append(f'promote34 {px} {py}')
    for bit in range(8):
        for net,dx in trunks.items():
            x=6000*bit+dx;top=55000 if net=='VDD' else 56500 if net=='VSS' else 52500
            script.append(f'rect metal4 {x-48} 9000 {x+48} {top+140}')
            if net in ('VDD','VSS'):script.append(f'via45 {x} {top}')
            else:pin_points[f'{net}{bit}']=(x,9000+200)
    # Dedicated power trunks for the WL drivers.
    for pin,x,top in [('VDD',-5200,55000),('VSS',-4600,56500)]:
        script.append(f'rect metal4 {x-48} 31500 {x+48} {top+140}')
        for r in range(4):script.append(f'promote34 {x} {35600+5000*r+yof("wl_driver",pin)}')
        script.append(f'via45 {x} {top}')
    # Selected WL connects eight bitcells and its driver, via M5 row bus.
    for r in range(4):
        y=36400+5000*r
        script.append(f'rect metal5 -7410 {y-200} 42180 {y+200}')
        for x,py in [(-7230,33400+5000*r)]+[(6000*b-230,33400+5000*r) for b in range(8)]:
            script += [f'promote34 {x} {py}',f'rect metal4 {x-48} {py} {x+48} {y}',f'via45 {x} {y}']
        px=-6000;py=35100+5000*r
        script.append(f'promote34 {px} {py}');pin_points[f'ROW{r}']=(px,py)
    for role,pin,bus_y in [('precharge','PRECH',30500),('sense','SCLK',23500),('write','WE',15500)]:
        cell={'precharge':'precharge','sense':'sense_amp','write':'write_driver'}[role]
        script.append(f'rect metal5 -410 {bus_y-200} 42180 {bus_y+200}')
        for bit in range(8):
            x=6000*bit-230;py=places[f'{role}{bit}'][1]+yof(cell,pin)
            script += [f'promote34 {x} {py}',f'rect metal4 {x-48} {py} {x+48} {bus_y}',f'via45 {x} {bus_y}']
        # External port on a short M4 extension at the first via.
        pin_points[pin]=(-230,bus_y)
    for bit in range(8):
        for pin,dx in [('DATA',4000),('DATA_B',3600)]:
            x=6000*bit+dx;y=15000+yof('write_driver',pin)
            script.append(f'promote34 {x} {y}');pin_points[f'{"DIN" if pin=="DATA" else "DIN_B"}{bit}']=(x,y)
        x=6000*bit+170;y=23000+yof('sense_amp','SA_OUT')
        script.append(f'promote34 {x} {y}');pin_points[f'DOUT{bit}']=(x,y)
    # Decoder signals remain external to the fabric so row qualification can
    # be physically bound and independently checked in the next hierarchy.
    for pin in ('A0','A1','PCLK','DEC0','DEC1','DEC2','DEC3'):
        x=-27000+label_coords['row_decoder'][pin];y=26000+yof('row_decoder',pin)
        script.append(f'promote34 {x} {y}');pin_points[pin]=(x,y)
    for pin,x,source_y,top in [('VDD',-25500,27700,55000),('VSS',-24500,24300,56500)]:
        script += [f'promote34 -26500 {source_y}',f'rect metal4 -26548 {source_y-48} {x+48} {source_y+48}',
                   f'rect metal4 {x-48} {source_y} {x+48} {top}',f'via45 {x} {top}']
    for pin,y in [('VDD',55000),('VSS',56500)]:
        script.append(f'rect metal5 -27000 {y-200} 44800 {y+200}')
        pin_points[pin]=(-25500 if pin=='VDD' else -24500,y)
    # BL/BLB are internal to this fabric, not extra functional ports.
    for index,pin in enumerate(ports,1):
        x,y=pin_points[pin]
        # Routing-grid access pad, outside the read-only leaf. The original
        # tiny label alone can miss every preferred-direction routing track.
        script.append(f'rect metal4 {x-120} {y-80} {x+120} {y+80}')
        script.append(f'pin {pin} {index} {x} {y}')
    script += ['select top cell','expand','flatten leaf_fabric','load leaf_fabric','select top cell','expand',
               'drc euclidean on','drc style drc(full)','drc on','drc check','drc catchup',
               'puts "FABRIC_DRC=[llength [drc listall why]]"','puts "FABRIC_DETAILS=[drc listall why]"',
               'save leaf_fabric','gds write leaf_fabric.gds','lef write leaf_fabric.lef',
               'extract all','ext2spice lvs','ext2spice scale off',
               'ext2spice -o fabric_extracted.spice','quit -noprompt']
    (build/'fabric.tcl').write_text('\n'.join(script)+'\n')
    return inputs


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',default='reports/phase2/fabric')
    args=p.parse_args();output=(ROOT/args.output).resolve()
    if not output.is_relative_to(ROOT/'reports/phase2') or output==ROOT/'reports/phase2':p.error('Output under reports/phase2 required')
    output.mkdir(parents=True,exist_ok=True)
    with output_lock(output):
        receipt={'status':'RUNNING','CORE':'NOT_EVALUATED','F2_FIS':'NOT_EVALUATED',
                 'scope':'401-MOS leaf fabric only; qualified rows/complement data/physical phases unbound'}
        def publish():atomic_text(output/'results.json',json.dumps(receipt,indent=2)+'\n')
        publish()
        try:
            root=ROOT/'build/phase2';root.mkdir(parents=True,exist_ok=True)
            build=Path(tempfile.mkdtemp(prefix='fabric-',dir=root));receipt['build_directory']=str(build.relative_to(ROOT))
            receipt['inputs']=generate(build)
            result=subprocess.run(['magic','-dnull','-noconsole','-rcfile',str(RC)],cwd=build,
                                  input=(build/'fabric.tcl').read_text(),capture_output=True,text=True,timeout=180)
            text=result.stdout+result.stderr;atomic_text(output/'magic.txt',text)
            for name in ('fabric.tcl','reference.spice','leaf_fabric.mag','leaf_fabric.gds','leaf_fabric.lef','fabric_extracted.spice'):
                if (build/name).is_file():shutil.copyfile(build/name,output/name)
            drc=re.findall(r'^FABRIC_DRC=(\d+)$',text,re.M);receipt['drc']=drc
            if result.returncode or drc!=['0']:raise ValueError('Fabric DRC failed')
            normalized,count=normal_mos((build/'fabric_extracted.spice').read_text(),'leaf_fabric')
            if count!=401:raise ValueError(f'Expected 401 leaf MOS, extracted {count}')
            (build/'layout_mos.spice').write_text(normalized)
            report=build/'lvs.txt'
            result=subprocess.run(['netgen','-batch','lvs','layout_mos.spice leaf_fabric','reference.spice leaf_fabric',
                                   '/opt/pdks/sky130A/libs.tech/netgen/sky130A_setup.tcl',str(report)],
                                  cwd=build,capture_output=True,text=True,timeout=180)
            atomic_text(output/'netgen.txt',result.stdout+result.stderr)
            text=report.read_text();atomic_text(output/'lvs.txt',text)
            if result.returncode or 'Circuits match uniquely.' not in text or re.search(r'(?i)property errors|do not match|black.box|placeholder',text):
                raise ValueError('Fabric LVS failed')
            reimport=build/'reimport';reimport.mkdir()
            commands=f'''gds read {build}/leaf_fabric.gds
load leaf_fabric
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
            result=subprocess.run(['magic','-dnull','-noconsole','-rcfile',str(RC)],cwd=reimport,
                                  input=commands,capture_output=True,text=True,timeout=180)
            text=result.stdout+result.stderr;atomic_text(output/'reimport_magic.txt',text)
            if result.returncode or re.findall(r'^REIMPORT_DRC=(\d+)$',text,re.M)!=['0']:
                raise ValueError('Fabric GDS reimport DRC failed')
            normalized,n=normal_mos((build/'reimport_extracted.spice').read_text(),'leaf_fabric')
            if n!=401:raise ValueError('Reimported fabric lost MOS')
            (build/'reimport_mos.spice').write_text(normalized)
            report=build/'reimport_lvs.txt'
            result=subprocess.run(['netgen','-batch','lvs','reimport_mos.spice leaf_fabric','reference.spice leaf_fabric',
                                   '/opt/pdks/sky130A/libs.tech/netgen/sky130A_setup.tcl',str(report)],
                                  cwd=build,capture_output=True,text=True,timeout=180)
            text=report.read_text();atomic_text(output/'reimport_lvs.txt',text)
            if result.returncode or 'Circuits match uniquely.' not in text or re.search(r'(?i)property errors|do not match|black.box|placeholder',text):
                raise ValueError('Fabric GDS reimport LVS failed')
            for name in ('reimport_extracted.spice','layout_mos.spice'):
                shutil.copyfile(build/name,output/name)
            receipt.update(status='PASS_LEAF_FABRIC',mos=count,reimport_drc=0,reimport_lvs='UNIQUE_MATCH_W_L_TERMINALS')
        except Exception as error:receipt.update(status='FAIL',error=str(error))
        receipt['artifacts']={p.name:digest(p) for p in output.iterdir() if p.is_file() and p.name not in ('results.json','.run.lock')}
        publish();print(json.dumps({k:receipt[k] for k in receipt if k!='inputs'},indent=2))
        return 0 if receipt['status']=='PASS_LEAF_FABRIC' else 1


if __name__=='__main__':raise SystemExit(main())
