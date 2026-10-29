#!/usr/bin/env python3
"""Context controls: ordinary hold/NAND states can produce negative off-NFET VGS.

These are model-based reference circuits, not independent device measurements.
The existing bitcell is read-only and is not requalified by this small control.
"""
import json
from pathlib import Path
import re
import subprocess
import numpy as np
import run_canonical_decoder_wl as pair
import run_canonical_intrinsic_bias as intrinsic


def main():
    out=pair.ROOT/'sims/row_decoder/results/offstate_reference_controls_20261029'
    pair.require(not out.exists(),'Use a fresh reference-control directory')
    pair.release_inputs();out.mkdir(parents=True)
    library=Path('/opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice')
    match=re.search(r'(?mis)^\.subckt sky130_fd_sc_hd__nand2_1\s+.*?^\.ends\b[^\n]*',library.read_text())
    pair.require(match is not None,'Missing upstream NAND2')
    nand=out/'pdk_nand2_excerpt.spice'
    nand.write_text('* Copyright 2020 The SkyWater PDK Authors; Apache-2.0\n'
                    '* Extracted unchanged subcircuit from installed sky130_fd_sc_hd.spice\n'+match[0]+'\n')
    bit=pair.RELEASE/'cells/bitcell_6t/bitcell_6t.spice'
    blocks={}
    for name,text in [('nand',match[0]),('bit',bit.read_text())]:
        lines=pair.logical(text);header=next(l.split() for l in lines if l.lower().startswith('.subckt'))
        blocks[name]=dict(subckt=header[1],ports=header[2:],devices=[l.split() for l in lines if l.lower().startswith('x')])
    records=[];cases=[]
    for profile in ('tt','ss','ff'):
        corner,vdd,temp=pair.PROFILES[profile];folder=out/profile;folder.mkdir()
        lines=['Off-state context control, not measured silicon',f'.lib "{pair.NATIVE_MODEL}" {corner}',
               f'.temp {temp}',f'VDD VDD 0 {vdd}',f'.include "{nand}"',f'.include "{bit}"']
        instances=[]
        for a in range(2):
            for b in range(2):
                label=f'xnand{a}{b}';nets=dict(A=f'a{a}{b}',B=f'b{a}{b}',VGND='0',VNB='0',VPB='VDD',VPWR='VDD',Y=f'y{a}{b}')
                lines +=[f'VA{a}{b} {nets["A"]} 0 {a*vdd}',f'VB{a}{b} {nets["B"]} 0 {b*vdd}',
                         pair.instance(label,blocks['nand']['subckt'],blocks['nand']['ports'],nets)]
                instances.append((label,'nand',nets))
        for state in (0,1):
            label=f'xbit{state}';nets=dict(VDD='VDD',BL=f'bl{state}',BLB=f'blb{state}',VSS='0',WL=f'wl{state}')
            lines +=[f'VBL{state} bl{state} 0 {vdd}',f'VBLB{state} blb{state} 0 {vdd}',f'VWL{state} wl{state} 0 0',
                pair.instance(label,blocks['bit']['subckt'],blocks['bit']['ports'],nets),
                f'.nodeset V({label}.Q)={state*vdd} V({label}.QB)={(1-state)*vdd}']
            instances.append((label,'bit',nets))
        saved={'v(VDD)'};devices=[]
        for label,block,nets in instances:
            for device in blocks[block]['devices']:
                model=device[5];kind='n' if '__nfet' in model else 'p'
                nodes=[nets.get(node,label+'.'+node) for node in device[1:5]]
                saved.update(f'v({n})' for n in nodes if n!='0')
                primitive='m.'+label+'.'+device[0].lower()+'.m'+model
                queries={q:f'@{primitive}[{q}]' for q in ('vgs','vds','vbs')}
                saved.update(queries.values());devices.append((label,block,device[0],kind,nodes,queries))
        lines +=['.save '+' '.join(sorted(saved)),'.control','set num_threads=1','set filetype=binary','op',
                  'write operating_point.raw','quit','.endc','.end']
        deck=folder/'case.spice';deck.write_text('\n'.join(lines)+'\n')
        run=subprocess.run(['ngspice','-n','-b',str(deck)],cwd=folder,capture_output=True,text=True,timeout=60)
        log=run.stdout+run.stderr;(folder/'ngspice.txt').write_text(log)
        pair.require(run.returncode==0 and not re.search(r'(?i)warning|error:|failed',log),'Reference control OP failed')
        rawpath=folder/'operating_point.raw';raw=pair.read_raw(rawpath)
        def voltage(n):return 0.0 if n=='0' else float(raw[f'v({n.lower()})'][0])
        for label,block,name,kind,nodes,queries in devices:
            normalized={q:next(raw[k] for k in (query,f'v({query})') if k in raw) for q,query in queries.items()}
            bias=intrinsic.oriented_states(kind,normalized['vgs'],normalized['vds'],normalized['vbs'])
            records.append(dict(profile=profile,circuit=block,instance=label,device=name,kind=kind,
                **{q.lower()+'_v':float(v[0]) for q,v in bias.items()},
                **{key+'_v':voltage(n) for key,n in zip(('d','g','s','b'),nodes)}))
        for a in range(2):
            for b in range(2):
                value=voltage(f'y{a}{b}');expected=1-(a&b)
                pair.require(value>=0.9*vdd if expected else value<=0.1*vdd,'NAND2 truth-table failure')
        for state in (0,1):
            q,qb=voltage(f'xbit{state}.Q'),voltage(f'xbit{state}.QB')
            pair.require((q>=0.9*vdd and qb<=0.1*vdd) if state else (q<=0.1*vdd and qb>=0.9*vdd),'Bitcell hold control failed')
        cases.append(dict(profile=profile,logic_controls_pass=6,raw_sha256=pair.sha(rawpath),deck_sha256=pair.sha(deck)))
    pair.write_csv(out/'bias.csv',records)
    summary=dict(status='MEASURED_CONTEXT_CONTROL',cases=cases,
        negative_off_nfet_vgs_min_v=min(r['vgs_v'] for r in records if r['kind']=='n'),
        scope='A negative VGS signed screen is not a decoder-specific fault test. This does not validate the model against physical measurements.',
        input_library_sha256=pair.sha(library),bitcell_sha256=pair.sha(bit),runner_sha256=pair.sha(Path(__file__)),
        models=pair.model_dependencies(pair.NATIVE_MODEL))
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(summary['negative_off_nfet_vgs_min_v'])


if __name__=='__main__':main()
