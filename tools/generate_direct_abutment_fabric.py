#!/usr/bin/env python3
"""New direct-abutment fabric; the original generator and selected cells are untouched.

Periphery ports, decoder, dimensions and phase binding remain unchanged.
Only bitcell geometry/tiling and the core-to-periphery interconnect are new.
The existing fabric qualification engine runs on this explicit generator.
"""
import argparse,json,re,shutil,sys
from pathlib import Path
import phase2_core as core
import run_phase2_fabric as engine
from run_phase2_physical_pilot import normal_mos,digest,tcl as pilot_tcl
ROOT=core.ROOT
GATE=ROOT/'physical/phase2_direct_abutment/pilot_gate.json'


def generate(build):
    leaves=core.selected_leaves(); design=core.graph(); core.audit(design)
    gate=json.loads(GATE.read_text())
    if gate['status']!='PASS_2X2_GATE':raise ValueError('2x2 gate is not approved')
    for evidence in gate['evidence'].values():
        p=ROOT/evidence['path']
        if digest(p)!=evidence['sha256']:raise ValueError('Pilot receipt changed')
        state=json.loads(p.read_text())
        if not state['status'].startswith('PASS'):raise ValueError('Incomplete pilot')
        for n,h in state['artifacts'].items():
            if digest(p.parent/n)!=h:raise ValueError('Pilot artifact changed: '+n)
    mask=ROOT/gate['cell_mag']['path']
    if digest(mask)!=gate['cell_mag']['sha256']:raise ValueError('New bitcell changed')
    leaves['bitcell_6t']['files']['layout']=mask
    # Derive pitch from the qualified physical boundary, never the old spacing.
    bounds=re.search(r'string FIXED_BBOX ([-\d ]+)',mask.read_text())[1].split()
    x1,y1,x2,y2=map(int,bounds);width,height=x2-x1,y2-y1
    if (x1,y1)!=(0,0):raise ValueError('Expected origin-normalized new tile')

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
            m=re.fullmatch(r'bit_r(\d)_b(\d)',name); places[name]=(width*int(m[2]),36000+height*int(m[1]))
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
        if cell in ('row_decoder','bitcell_6t'):continue
        for pin in ('VDD','VSS','BL','BLB'):
            if pin not in i['pins']:continue
            px=x+trunks[pin];py=y+yof(cell,pin)
            script.append(f'promote34 {px} {py}')
    # Periphery stays at its original safe pitch. New orthogonal fanout
    # connects its BL/BLB to the compact core without crossing M4 power.
    for bit in range(8):
        for net,dx in trunks.items():
            x=6000*bit+dx
            if net in ('VDD','VSS'):
                y=31400 if net=='VDD' else 32400
                script += [f'rect metal4 {x-48} 9000 {x+48} {y+140}',f'via45 {x} {y}']
            else:
                index=2*bit+(net=='BLB');y=33200+180*index
                cx=width*bit+(1850 if net=='BL' else 2530)
                script += [f'rect metal4 {x-48} 9000 {x+48} {y+48}',
                           f'promote34 {x} {y}',f'promote34 {cx} {y}',
                           f'rect metal3 {min(x,cx)-48} {y-48} {max(x,cx)+48} {y+48}',
                           f'rect metal4 {cx-60} {y} {cx+60} 36000']
                pin_points[f'{net}{bit}']=(x,9200)
    for pin,y,x in [('VDD',31400,-25500),('VSS',32400,-24500)]:
        script += [f'rect metal5 -27000 {y-200} 44800 {y+200}',f'via45 {x} {y}']
    # Actual M4 rails touch at every vertical tile seam; one strap reaches
    # each global power header. M3 rails already join all eight columns.
    for x,escape,jog,y in [(2950,1500,48000,55000),(3150,4000,48600,56500)]:
        # The large via4 pad must be staggered away from the adjacent
        # in-array power track; otherwise its enclosure touches the other rail.
        script += [f'rect metal4 {x-60} {36000+4*height} {x+60} {jog+60}',
                   f'rect metal4 {min(x,escape)-60} {jog-60} {max(x,escape)+60} {jog+60}',
                   f'rect metal4 {escape-60} {jog} {escape+60} {y}',f'via45 {escape} {y}']
    # Dedicated power trunks for the WL drivers.
    for pin,x,top in [('VDD',-5200,55000),('VSS',-4600,56500)]:
        script.append(f'rect metal4 {x-48} 31500 {x+48} {top+140}')
        for r in range(4):script.append(f'promote34 {x} {35600+5000*r+yof("wl_driver",pin)}')
        script.append(f'via45 {x} {top}')
    # WL drivers remain separated; the four M4 escape channels terminate
    # at four distinct M3 wordlines on the compact array's left boundary.
    for r in range(4):
        # Keep the M4/M5 via away from the M3/M4 contact on row 0.
        # Overlapping different Magic contact types can cut the landing.
        y=36800+5000*r;target=36000+450+height*r;cx=-1800+400*r
        x=-7230;py=33400+5000*r
        script += [f'promote34 {x} {py}',f'rect metal4 {x-48} {py} {x+48} {y}',
                   f'via45 {x} {y}',f'rect metal5 {x-180} {y-200} {cx+180} {y+200}',
                   f'via45 {cx} {y}',f'rect metal4 {cx-48} {min(y,target)} {cx+48} {max(y,target)}',
                   f'promote34 {cx} {target}',f'rect metal3 {cx-48} {target-48} 100 {target+48}']
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
    inputs[str(GATE.relative_to(ROOT))]=digest(GATE)
    inputs[str(Path(__file__).relative_to(ROOT))]=digest(Path(__file__))
    return inputs


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args()
    out=(ROOT/a.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2/direct_abutment_20261111') or out.exists():
        p.error('Use a new candidate directory under reports/phase2/direct_abutment_20261111')
    engine.generate=generate  # Dependency injection in this process; no source mutation.
    sys.argv=[sys.argv[0],'--output',str(out.relative_to(ROOT))]
    return engine.main()


if __name__=='__main__':raise SystemExit(main())
