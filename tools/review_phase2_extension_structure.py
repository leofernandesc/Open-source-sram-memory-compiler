#!/usr/bin/env python3
"""Second structural pass: real extracted inverter and bus pin relationships."""
import argparse,json,re
from pathlib import Path
from run_phase2_digital import ROOT,sha
from run_phase2_directed_review import observation_map
from run_phase2_startup_review import SOURCE,GDS
from review_phase2_structure import inspect


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=(ROOT/a.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2') or out.exists():p.error('New report directory required')
    out.mkdir(parents=True)
    try:
        reference=ROOT/'reports/phase2/integrated_import_fix/routed_reference.spice';design_path=ROOT/'reports/phase2/portable_raw/routed_reference.json';design=json.loads(design_path.read_text());top=design['modules']['sram_4x8_wrapper']
        r=inspect(GDS,reference.read_text(),design)
        lookup=observation_map((GDS/'final_extracted.spice').read_text(),(SOURCE/'binding.spice').read_text(),(GDS/'final_flat.ext').read_text())
        def node(label):return lookup(label)[7:-1]
        cards=[l.split() for l in (SOURCE/'binding.spice').read_text().splitlines() if re.match(r'(?i)^x\S+\s',l)]
        def ff(bit):return next(n for n,c in top['cells'].items() if c['type'].startswith('sky130_fd_sc_hd__df') and c['connections']['Q']==[bit])
        vdd,vss=node('VDD'),node('VSS');extra=[];enables=set()
        for b in range(8):
            prefix=f'macro_core.array_and_peripherals.write_driver_{b}.'
            din=node(ff(top['netnames']['control.DIN_Q']['bits'][b])+'.Q');real=node(prefix+'DATA');comp=node(prefix+'DATA_B')
            if din!=real:raise ValueError('Write DATA not driven by corresponding captured DIN')
            inv=[f for f in cards if f[2]==din and comp in (f[1],f[3]) and ((f[4]==vdd and vdd in (f[1],f[3]) and 'pfet_' in f[5]) or (f[4]==vss and vss in (f[1],f[3]) and 'nfet_' in f[5]))]
            if len(inv)!=2 or len({f[4] for f in inv})!=2:raise ValueError('Physical DATA_B inverter missing/wrong body')
            output=next(n for n,c in top['cells'].items() if c['type']=='sky130_fd_sc_hd__ebufn_1' and c['connections']['Z']==[top['ports']['DATA']['bits'][b]])
            if node(output+'.A')!=node(ff(top['netnames']['read_data_q']['bits'][b])+'.Q'):raise ValueError('Tri-state input not matching read FF')
            if node(output+'.Z')!=node(f'DATA[{b}]'):raise ValueError('Tri-state output bit permutation')
            enables.add(node(output+'.TE_B'));extra.append(dict(bit=b,data=din,data_b=comp,physical_inverter_mos=[f[0] for f in inv],ebuf=output))
        # The routed design replicates the same NAND mask per output bit. A shared
        # enable net is not a protocol requirement; prove the real gate function.
        mask=next((n,c) for n,c in top['cells'].items() if c['type']=='sky130_fd_sc_hd__nor3b_1' and c['connections']['Y']==top['netnames']['live_read']['bits'])
        mask_name,mask_cell=mask
        if node(mask_name+'.A')!=node('OEb') or node(mask_name+'.B')!=node('CSb') or node(mask_name+'.C_N')!=node('WEb'):
            raise ValueError('Live read mask has wrong public input polarity')
        read_q=node(ff(top['netnames']['control.READ_Q']['bits'][0])+'.Q')
        live=node(mask_name+'.Y');nand_proofs=[]
        for item in extra:
            bit=item['bit'];ebuf=top['cells'][item['ebuf']];teb=ebuf['connections']['TE_B']
            name,c=next((n,c) for n,c in top['cells'].items() if c['type']=='sky130_fd_sc_hd__nand2_1' and c['connections']['Y']==teb)
            a,b,y=node(name+'.A'),node(name+'.B'),node(name+'.Y')
            if {a,b}!={read_q,live} or y!=node(item['ebuf']+'.TE_B'):raise ValueError('Wrong output-enable Boolean inputs')
            ps=[f for f in cards if f[2] in (a,b) and {f[1],f[3]}=={vdd,y} and f[4]==vdd and 'pfet_' in f[5]]
            ns=[f for f in cards if f[2] in (a,b) and y in (f[1],f[3]) and f[4]==vss and 'nfet_' in f[5]]
            if len(ps)!=2 or {f[2] for f in ps}!={a,b} or len(ns)!=1:raise ValueError('NAND pullup/top pulldown topology mismatch')
            top_n=ns[0];mid=top_n[3] if top_n[1]==y else top_n[1]
            bottom=[f for f in cards if {f[1],f[3]}=={mid,vss} and f[2] in {a,b}-{top_n[2]} and f[4]==vss and 'nfet_' in f[5]]
            if len(bottom)!=1:raise ValueError('NAND series pulldown missing')
            nand_proofs.append(dict(bit=bit,gate=name,actual_mos=[f[0] for f in [*ps,top_n,*bottom]]))
        r.update(status='PASS_SECOND_EXTRACTED_STRUCTURAL_PASS',additional_checks=extra,distinct_ebuf_enable_nets=len(enables),physical_nand_proofs=nand_proofs,boolean_mask='TE_B = NOT(captured READ_Q AND NOT CSb AND NOT OEb AND WEb)',
                 method='Original independent terminal/coordinate audit plus CMOS inversion determined from real MOS gates/rails, not generator Boolean declarations',
                 inputs={str(s.relative_to(ROOT)):sha(s) for s in [reference,design_path,SOURCE/'binding.spice',GDS/'final_extracted.spice',GDS/'final_flat.ext',Path(__file__),ROOT/'tools/review_phase2_structure.py']})
    except Exception as e:r=dict(status='FAIL',error=str(e))
    (out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],r.get('error',''));return 0 if r['status'].startswith('PASS') else 1


if __name__=='__main__':raise SystemExit(main())
