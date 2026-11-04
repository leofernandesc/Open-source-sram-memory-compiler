"""Named-pin structural assembly of the selected 4x8 leaves.

The phase-port harness is an intermediate electrical fixture, not the public
SRAM macro: physical clock/capture glue must be bound before F2-FIS acceptance.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]


def selected_leaves():
    pointer=json.loads((ROOT/'release/phase1_current.json').read_text())
    # The checked-in selector spells its target as manifest.
    manifest_path=ROOT/pointer['manifest']
    manifest=json.loads(manifest_path.read_text())
    result={}
    for name,item in manifest['cells'].items():
        files={}
        for kind,info in item['files'].items():
            path=ROOT/info['path']
            if hashlib.sha256(path.read_bytes()).hexdigest()!=info['sha256']:
                raise ValueError('Frozen view changed: '+info['path'])
            files[kind]=path
        source=files.get('netlist',files['schematic'].with_suffix('.spice'))
        text=source.read_text()
        pins=re.search(r'(?mi)^\.subckt\s+'+re.escape(name)+r'\s+(.+)$',text)[1].split()
        result[name]={'pins':pins,'files':files,'mos':item['expected_mos']}
    return result


def graph():
    instances=[]
    def put(name,cell,bindings):
        instances.append({'name':name,'cell':cell,'pins':bindings})
    for row in range(4):
        for bit in range(8):
            put(f'bit_r{row}_b{bit}','bitcell_6t',
                {'VDD':'VDD','VSS':'VSS','WL':f'WL{row}','BL':f'BL{bit}','BLB':f'BLB{bit}'})
    put('decode','row_decoder',{'VDD':'VDD','VSS':'VSS','PCLK':'PCLK','A0':'A0','A1':'A1',
                              **{f'DEC{r}':f'DEC{r}' for r in range(4)}})
    for row in range(4):
        put(f'qualify{row}','sky130_fd_sc_hd__and2_1',
            {'A':f'DEC{row}','B':'WL_EN','X':f'ROW{row}','VPWR':'VDD','VPB':'VDD','VGND':'VSS','VNB':'VSS'})
        put(f'drive{row}','wl_driver',{'VDD':'VDD','VSS':'VSS','WL_IN':f'ROW{row}','WL':f'WL{row}'})
    for bit in range(8):
        put(f'complement{bit}','sky130_fd_sc_hd__inv_1',
            {'A':f'DIN{bit}','Y':f'DIN_B{bit}','VPWR':'VDD','VPB':'VDD','VGND':'VSS','VNB':'VSS'})
        put(f'precharge{bit}','precharge',{'VDD':'VDD','VSS':'VSS','BL':f'BL{bit}','BLB':f'BLB{bit}','PRECH':'PRECH'})
        put(f'write{bit}','write_driver',{'VDD':'VDD','VSS':'VSS','BL':f'BL{bit}','BLB':f'BLB{bit}',
                                       'DATA':f'DIN{bit}','DATA_B':f'DIN_B{bit}','WE':'WE'})
        put(f'sense{bit}','sense_amp',{'VDD':'VDD','VSS':'VSS','BL':f'BL{bit}','BLB':f'BLB{bit}',
                                    'SCLK':'SCLK','SA_OUT':f'DOUT{bit}','SA_OUTB':f'DOUT_B{bit}'})
    return {'name':'sram_4x8_phase_harness','rows':4,'bits':8,
            'ports':['VDD','VSS','A0','A1',*[f'DIN{b}' for b in range(8)],
                     'PCLK','PRECH','SCLK','WE','WL_EN',*[f'DOUT{b}' for b in range(8)]],
            'instances':instances}


def audit(design):
    """Independent spec-level row/bit audit; does not reuse assembly loops/bindings."""
    if design['rows']!=4 or design['bits']!=8:
        raise ValueError('Only physical 4x8 is implemented')
    names=[i['name'] for i in design['instances']]
    if len(names)!=len(set(names)):
        raise ValueError('Duplicate structural instance')
    counts=Counter(i['cell'] for i in design['instances'])
    required={'bitcell_6t':32,'row_decoder':1,'wl_driver':4,'precharge':8,'write_driver':8,'sense_amp':8,
              'sky130_fd_sc_hd__and2_1':4,'sky130_fd_sc_hd__inv_1':8}
    if counts!=required:raise ValueError(f'Wrong instance inventory: {counts}')
    positions=set()
    rows={f'WL{n}' for n in range(4)}
    columns={f'BL{n}':f'BLB{n}' for n in range(8)}
    for instance in design['instances']:
        cell,pins=instance['cell'],instance['pins']
        for p,n in [('VDD','VDD'),('VSS','VSS')] if not cell.startswith('sky130_') else [('VPWR','VDD'),('VPB','VDD'),('VGND','VSS'),('VNB','VSS')]:
            if pins.get(p)!=n:raise ValueError(f'Wrong rail/body on {instance["name"]}')
        if cell=='bitcell_6t':
            position=(pins['WL'],pins['BL'])
            if pins['WL'] not in rows or columns.get(pins['BL'])!=pins['BLB'] or position in positions:
                raise ValueError('Missing/aliased row-column or swapped bitline')
            positions.add(position)
            match=re.fullmatch(r'bit_r([0-3])_b([0-7])',instance['name'])
            if not match or position!=(f'WL{match[1]}',f'BL{match[2]}'):
                raise ValueError('Placement identity disagrees with electrical row/bit')
    if len(positions)!=32:raise ValueError('Incomplete storage matrix')
    # Stable instance names independently identify each physical column/row.
    indexed={i['name']:i for i in design['instances']}
    for b in range(8):
        for role in ('write','sense','precharge'):
            p=indexed[f'{role}{b}']['pins']
            if p['BL']!=f'BL{b}' or p['BLB']!=f'BLB{b}':raise ValueError('Peripheral bitline alias')
        if indexed[f'sense{b}']['pins']['SA_OUT']!=f'DOUT{b}':raise ValueError('Sense polarity/order')
        if indexed[f'sense{b}']['pins']['SCLK']!='SCLK':raise ValueError('Sense phase')
        if indexed[f'precharge{b}']['pins']['PRECH']!='PRECH':raise ValueError('Precharge phase')
        p=indexed[f'write{b}']['pins']
        if (p['DATA'],p['DATA_B'],p['WE'])!=(f'DIN{b}',f'DIN_B{b}','WE'):raise ValueError('Write binding')
        p=indexed[f'complement{b}']['pins']
        if (p['A'],p['Y'])!=(f'DIN{b}',f'DIN_B{b}'):raise ValueError('Write complement')
    for r in range(4):
        if indexed['decode']['pins'][f'DEC{r}']!=f'DEC{r}':raise ValueError('Decoder pin permutation')
        if indexed[f'drive{r}']['pins']['WL']!=f'WL{r}':raise ValueError('WL row mapping')
        if indexed[f'drive{r}']['pins']['WL_IN']!=f'ROW{r}':raise ValueError('WL qualifier binding')
        p=indexed[f'qualify{r}']['pins']
        if (p['A'],p['B'],p['X'])!=(f'DEC{r}','WL_EN',f'ROW{r}'):raise ValueError('WL phase binding')
    return {'leaf_mos':401,'storage_bits':32,'rows':4,'columns':8,'status':'PASS'}


def emit(directory,hd_library):
    leaves=selected_leaves(); design=graph(); proof=audit(design)
    directory.mkdir(parents=True,exist_ok=True)
    definitions=[]; formals={}
    for name,item in leaves.items():
        source=item['files'].get('netlist',item['files']['schematic'].with_suffix('.spice'))
        definitions.append(source.read_text());formals[name]=item['pins']
    hd_text=hd_library.read_text()
    for name in ('sky130_fd_sc_hd__inv_1','sky130_fd_sc_hd__and2_1'):
        text=re.search(r'(?ms)^\.subckt '+name+r' .*?^\.ends[^\n]*',hd_text)[0]
        formals[name]=text.splitlines()[0].split()[2:];definitions.append(text+'\n')
    lines=['.subckt '+design['name']+' '+' '.join(design['ports'])]
    for instance in design['instances']:
        ports=formals[instance['cell']]
        if set(ports)!=set(instance['pins']):raise ValueError('Unbound/extra formal pin')
        lines.append('X'+instance['name']+' '+' '.join(instance['pins'][p] for p in ports)+' '+instance['cell'])
    lines.append('.ends '+design['name'])
    (directory/'core.spice').write_text('\n'.join(definitions+lines)+'\n')
    (directory/'graph.json').write_text(json.dumps(design,indent=2)+'\n')
    (directory/'topology.json').write_text(json.dumps(proof,indent=2)+'\n')
    return design
