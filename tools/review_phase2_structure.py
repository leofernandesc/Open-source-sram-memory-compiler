#!/usr/bin/env python3
"""Independent 4x8 audit from extracted terminals/coordinates and PDK definitions.

Does not import the layout generator or its graph. Index-to-position agreement
is checked using actual access-transistor coordinates, not placement constants.
"""
from collections import Counter
import json
from pathlib import Path
import re
import shlex
from run_phase2_digital import ROOT,sha


def inspect(source,reference,design):
    text=(source/'final_flat.ext').read_text();parent={}
    def clean(n):return n.replace('\\','')
    def find(n):
        n=clean(n);parent.setdefault(n,n)
        if parent[n]!=n:parent[n]=find(parent[n])
        return parent[n]
    for line in text.splitlines():
        q=re.findall(r'"([^"]*)"',line)
        if line.startswith('node ') and q:find(q[0])
        elif line.startswith('equiv ') and len(q)==2:parent[find(q[1])]=find(q[0])
    def actual(label):
        if clean(label) not in parent:raise ValueError('Missing extracted label: '+label)
        return find(label)
    cells=[]
    for line in text.splitlines():
        if not line.startswith('device msubckt '):continue
        q=re.findall(r'"([^"]*)"',line);fields=line.split()
        if len(q)!=4:raise ValueError('Unexpected extracted MOS terminal syntax')
        cells.append({'model':fields[2],'xy':[(int(fields[3])+int(fields[5]))/2,(int(fields[4])+int(fields[6]))/2],
                      'body':find(q[0]),'gate':find(q[1]),'ds':{find(q[2]),find(q[3])}})
    prefix='macro_core.array_and_peripherals.';matrix=[];wl_gates=[];xrows=[];yrows=[]
    vdd,vss=actual('VDD'),actual('VSS')
    if vdd==vss:raise ValueError('Extracted supply short')
    wl_roots=[actual(prefix+f'wl_driver_{r}.WL') for r in range(4)]
    bl_roots=[actual(prefix+f'write_driver_{b}.BL') for b in range(8)]
    blb_roots=[actual(prefix+f'write_driver_{b}.BLB') for b in range(8)]
    if len(set(bl_roots+blb_roots))!=16 or len(set(wl_roots))!=4:raise ValueError('Aliased BL/BLB/WL')
    for row,wl in enumerate(wl_roots):
        selected=[c for c in cells if c['gate']==wl]
        if len(selected)!=16 or any(c['model']!='sky130_fd_pr__nfet_01v8' or c['body']!=vss for c in selected):raise ValueError('Wrong access count/model/body')
        wl_gates.append(len(selected));xrow=[];ys=[]
        for bit in range(8):
            path=prefix+f'bitcell_6t_{row*8+bit}.'
            for name,expected in [('WL',wl),('BL',bl_roots[bit]),('BLB',blb_roots[bit]),('VDD',vdd),('VSS',vss)]:
                if actual(path+name)!=expected:raise ValueError('Wrong extracted bitcell row/column/rail')
            devices=[c for c in selected if bl_roots[bit] in c['ds'] or blb_roots[bit] in c['ds']]
            if len(devices)!=2 or not all(sum(root in c['ds'] for c in devices)==1 for root in (bl_roots[bit],blb_roots[bit])):
                raise ValueError('Wrong access pairing on differential column')
            xrow.append(sum(c['xy'][0] for c in devices)/2);ys.extend(c['xy'][1] for c in devices)
            for family in ('precharge','sense_amp'):
                for name,expected in [('BL',bl_roots[bit]),('BLB',blb_roots[bit]),('VDD',vdd),('VSS',vss)]:
                    if actual(prefix+f'{family}_{bit}.'+name)!=expected:raise ValueError('Peripheral column/rail mismatch')
            matrix.append({'row':row,'bit':bit,'access_devices':2,'x_internal_units':xrow[-1]})
        if not all(a<b for a,b in zip(xrow,xrow[1:])):raise ValueError('Logical bit order disagrees with physical x order')
        xrows.append(xrow);yrows.append(sum(ys)/len(ys))
    if not all(a<b for a,b in zip(yrows,yrows[1:])):raise ValueError('Logical row order disagrees with physical y order')
    for bit in range(8):
        # Sense output must reach the matching wrapper read-data bus bit.
        fabric=next(c for c in design['modules']['sram_4x8_wrapper']['cells'].values() if c['type']=='leaf_fabric')
        target=fabric['connections'][f'DOUT{bit}']
        mux=next((n,c) for n,c in design['modules']['sram_4x8_wrapper']['cells'].items()
                 if c['type']=='sky130_fd_sc_hd__mux2_1' and c['connections'].get('A1')==target)
        if actual(prefix+f'sense_amp_{bit}.SA_OUT')!=actual(mux[0]+'.A1'):raise ValueError('Sense output bit permutation')
    top=design['modules']['sram_4x8_wrapper'];inventory=Counter(c['type'] for c in top['cells'].values())
    definitions={m[1]:m[0] for m in re.finditer(r'(?ms)^\.subckt\s+(\S+)[^\n]*\n.*?^\.ends[^\n]*',reference)}
    def mos_count(name,ancestors=()):
        if name in ancestors or name not in definitions:raise ValueError('Invalid reference hierarchy: '+name)
        total=0
        for line in definitions[name].splitlines():
            if not re.match(r'(?i)^x\S+\s',line):continue
            tokens=line.split();end=next((i for i,t in enumerate(tokens) if '=' in t),len(tokens));child=tokens[end-1]
            total+=1 if child.startswith('sky130_fd_pr__') else mos_count(child,(*ancestors,name))
        return total
    per={n:mos_count(n) for n in inventory}
    table=[{'master':n,'instances':qty,'mos_per_instance':per[n],
            'mos_total':qty*per[n]} for n,qty in sorted(inventory.items())]
    total=sum(r['mos_total'] for r in table)
    if len(cells)!=1493 or total!=len(cells):raise ValueError('Independent MOS count disagreement')
    for bit,node in enumerate(top['ports']['DATA']['bits']):
        drive=next(c for c in top['cells'].values() if c['type']=='sky130_fd_sc_hd__ebufn_1' and c['connections'].get('Z')==[node])
        if drive['connections']['A']!=[top['netnames']['read_data_q']['bits'][bit]]:raise ValueError('Output tri-state data permutation')
    return {'status':'PASS_INDEPENDENT_STRUCTURE','mos':len(cells),'hierarchical_instances':sum(inventory.values()),
            'custom_mos':per['leaf_fabric'],'hd_mos':total-per['leaf_fabric'],'wl_access_gates':wl_gates,'storage_bits':len(matrix),
            'matrix':matrix,'physical_row_y_internal_units':yrows,'transistor_inventory':table,
            'scope':'Actual extracted aliases, access MOS coordinates/model/body and HD PDK transistor definitions; not generator graph assertions'}


def main():
    source=ROOT/'reports/phase2/final_gds';reference=ROOT/'reports/phase2/integrated_import_fix/routed_reference.spice';design=ROOT/'reports/phase2/portable_raw/routed_reference.json'
    out=ROOT/'reports/phase2/review_20261104/structure';out.mkdir(parents=True,exist_ok=True)
    try:
        result=inspect(source,reference.read_text(),json.loads(design.read_text()))
        result['inputs']={str(p.relative_to(ROOT)):sha(p) for p in [source/'final_flat.ext',reference,design,Path(__file__)]}
    except Exception as e:result={'status':'FAIL','error':str(e)}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],result.get('error',''))
    return 0 if result['status']=='PASS_INDEPENDENT_STRUCTURE' else 1


if __name__=='__main__':raise SystemExit(main())
