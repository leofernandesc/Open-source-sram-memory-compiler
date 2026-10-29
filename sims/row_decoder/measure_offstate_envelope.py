#!/usr/bin/env python3
"""Measure terminal-current references in supported bias configurations at crossed PVT.

The resulting budget is an explicitly conservative engineering reference, not
a certified physical leakage upper bound outside measured bias/temperature coverage.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import numpy as np
import run_decoder_robustness as study
pair=study.pair


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True)
    args=p.parse_args();out=args.output_dir;pair.require(not out.exists(),'Use a new directory')
    inputs=pair.release_inputs();variants={}
    for leaf in inputs.values():
        for device in leaf['devices']:
            key=(device[5],*device[6:]);variants.setdefault(key,dict(model=device[5],parameters=device[6:]))
    for width in (0.42,0.84):
        model='sky130_fd_pr__pfet_01v8';params=[f'w={width:g}','l=0.15',f'ad={width*.29:g}',f'as={width*.29:g}',
            f'pd={2*(width+.29):g}',f'ps={2*(width+.29):g}',f'nrd={.29/width:g}',f'nrs={.29/width:g}']
        variants[(model,*params)]=dict(model=model,parameters=params,keeper_candidate_width_um=width)
    out.mkdir(parents=True);records=[];conditions=[]
    for profile,(corner,vdd,temp) in study.POINTS.items():
        folder=out/profile;folder.mkdir();lines=['Off-state envelope references, not model validation',
            f'.lib "{pair.NATIVE_MODEL}" {corner}',f'.temp {temp}'];saved=[];jobs=[]
        for number,variant in enumerate(variants.values()):
            kind='n' if '__nfet_' in variant['model'] else 'p'
            states=['off_drain_high','off_source_high','gate_on_zero_vds']
            if kind=='p':states+=['restore_at_n90']
            for state in states:
                label=f'v{number}_{state}'
                if kind=='n':
                    values=dict(d=vdd if state=='off_drain_high' else 0,
                        g=vdd if state=='gate_on_zero_vds' else 0,
                        s=vdd if state=='off_source_high' else 0,b=0)
                else:
                    values=dict(d=0 if state=='off_drain_high' else vdd,
                        g=0 if state in ('gate_on_zero_vds','restore_at_n90') else vdd,
                        s=0 if state=='off_source_high' else vdd,b=vdd)
                    if state=='restore_at_n90':values['d']=.9*vdd
                for pin,voltage in values.items():
                    source=f'V{label}_{pin}';node=label+'_'+pin
                    lines.append(f'{source} {node} 0 {voltage:.14g}');saved.append(f'i({source})')
                lines.append(f'X{label} '+' '.join(label+'_'+pin for pin in ('d','g','s','b'))+' '+variant['model']+' '+' '.join(variant['parameters']))
                jobs.append((label,kind,state,variant,values))
        lines+=['.save '+' '.join(saved),'.control','set num_threads=1','set filetype=binary','op','write currents.raw','quit','.endc','.end']
        path=(folder/'case.spice').resolve();path.write_text('\n'.join(lines)+'\n')
        run=subprocess.run(['ngspice','-n','-b',str(path)],cwd=folder,capture_output=True,text=True,timeout=60)
        log=run.stdout+run.stderr;(folder/'ngspice.txt').write_text(log)
        pair.require(run.returncode==0 and not re.search(r'(?i)warning|error:|failed',log),'DC-current reference failed')
        rawpath=folder/'currents.raw';raw=pair.read_raw(rawpath)
        for label,kind,state,variant,values in jobs:
            current={pin:-float(raw[f'i(v{label}_{pin})'][0]) for pin in ('d','g','s','b')}
            pair.require(all(np.isfinite(v) for v in current.values()),'Nonfinite current reference')
            records.append(dict(profile=profile,corner=corner,vdd_v=vdd,temp_c=temp,kind=kind,state=state,
                model=variant['model'],parameters=' '.join(variant['parameters']),
                keeper_candidate_width_um=variant.get('keeper_candidate_width_um',''),
                **{pin+'_a':value for pin,value in current.items()},kcl_residual_a=sum(current.values()),
                **{pin+'_v':value for pin,value in values.items()}))
        conditions.append(dict(profile=profile,deck_sha256=pair.sha(path),raw_sha256=pair.sha(rawpath)))
    pair.write_csv(out/'terminal_currents.csv',records)
    budgets=[]
    for profile in study.POINTS:
        group=[r for r in records if r['profile']==profile and r['keeper_candidate_width_um']=='']
        off={kind:max(max(abs(r['d_a']),abs(r['s_a'])) for r in group if r['kind']==kind and r['state'].startswith('off_')) for kind in ('n','p')}
        gate={kind:max(abs(r['g_a']) for r in group if r['kind']==kind) for kind in ('n','p')}
        budgets.append(dict(profile=profile,nfet_off_terminal_a=off['n'],pfet_off_terminal_a=off['p'],
            nfet_gate_a=gate['n'],pfet_gate_a=gate['p'],row_reference_a=2*off['n']+off['p']+gate['n']+gate['p']))
    pair.write_csv(out/'row_references.csv',budgets)
    result=dict(status='MEASURED_ENGINEERING_REFERENCE',conditions=conditions,variants=len(variants),rows=len(records),
        row_reference_formula='2 * max NFET off-port + max PFET off-port + max NFET gate + max PFET gate; deliberately uses broad width envelopes.',
        max_modeled_row_reference_a=max(r['row_reference_a'] for r in budgets),
        limitation='These are model predictions within reference configurations. They do not validate the actual negative-VGS states or form a certified physical leakage bound.',
        runner_sha256=pair.sha(Path(__file__)),models=pair.model_dependencies(pair.NATIVE_MODEL))
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(result['max_modeled_row_reference_a'])


if __name__=='__main__':main()
