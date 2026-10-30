#!/usr/bin/env python3
"""Sample selected-row DC discharge against feedback keeper width at 30 PVT points.

This six-device branch is a schematic sizing experiment. It is not an extracted
decoder, dynamic noise calculation, mismatch test or proof between sampled points.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import numpy as np
import run_decoder_robustness as study
pair=study.pair

WIDTHS=(0,0.42,0.84,1.25,3)
POINTS=dict(study.POINTS)
for corner in ('sf','fs'):
    for vdd in (1.62,1.8):
        for temp in (-40,27,125):POINTS[f'{corner}_{vdd:g}_{temp:g}']=(corner,vdd,temp)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True)
    args=p.parse_args();out=args.output_dir;pair.require(not out.exists(),'Use a new directory');out.mkdir(parents=True)
    rows=[];curves=[];conditions=[]
    for profile,(corner,vdd,temp) in POINTS.items():
        folder=out/profile;folder.mkdir()
        lines=['Schematic selected-branch DC contention screen',f'.lib "{pair.NATIVE_MODEL}" {corner}',
            f'.temp {temp}',f'VDD VDD 0 {vdd}','VSCAN scan 0 0'];saved=['v(scan)']
        def mos(label,d,g,s,b,kind,w):
            return (f'X{label} {d} {g} {s} {b} sky130_fd_pr__{kind}fet_01v8 '
                f'w={w:g} l=.15 ad={w*.29:g} as={w*.29:g} '
                f'pd={2*(w+.29):g} ps={2*(w+.29):g} nrd={.29/w:g} nrs={.29/w:g}')
        for i,w in enumerate(WIDTHS):
            n=f'n{i}';dec=f'dec{i}';m1=f'm1_{i}';m2=f'm2_{i}'
            lines.extend([f'EFORCE{i} force{i} 0 scan 0 1',f'VSENSE{i} {n} force{i} 0',
                mos(f'UP{i}',n,'VDD',m1,'0','n',2),mos(f'LOW{i}',m1,'VDD',m2,'0','n',2),
                mos(f'FOOT{i}',m2,'VDD','0','0','n',1.5),
                mos(f'POUT{i}',dec,n,'VDD','VDD','p',3),mos(f'NOUT{i}',dec,n,'0','0','n',2)])
            if w:lines.append(mos(f'KEEP{i}',n,dec,'VDD','VDD','p',w))
            saved.extend([f'i(VSENSE{i})',f'v({dec})'])
        lines+=['.save '+' '.join(saved),'.control','set num_threads=1','set filetype=binary',
            f'dc VSCAN 0 {vdd:g} {vdd/160:.15g}','write curves.raw','quit','.endc','.end']
        path=(folder/'case.spice').resolve();path.write_text('\n'.join(lines)+'\n')
        run=subprocess.run(['ngspice','-n','-b',str(path)],cwd=folder,capture_output=True,text=True,timeout=60)
        log=run.stdout+run.stderr;(folder/'ngspice.txt').write_text(log)
        pair.require(run.returncode==0 and not re.search(r'(?i)warning|error:|failed',log),'DC contention failed')
        rawpath=folder/'curves.raw';raw=pair.read_raw(rawpath);voltage=raw['v(scan)'];window=(voltage>=.1*vdd)
        for i,width in enumerate(WIDTHS):
            discharge=-raw[f'i(vsense{i})']
            minimum=float(discharge[window].min());weakest=int(np.flatnonzero(window)[np.argmin(discharge[window])])
            rows.append(dict(profile=profile,corner=corner,vdd_v=vdd,temp_c=temp,keeper_width_um=width,
                min_net_discharge_ua=minimum*1e6,weakest_node_v=float(voltage[weakest]),
                status='PASS_SAMPLED_DISCHARGE' if minimum>0 else 'REJECT_BIAS_POINT'))
            curves.extend(dict(profile=profile,keeper_width_um=width,node_v=float(v),
                output_v=float(raw[f'v(dec{i})'][j]),net_discharge_ua=float(discharge[j])*1e6) for j,v in enumerate(voltage))
        conditions.append(dict(profile=profile,deck_sha256=pair.sha(path),raw_sha256=pair.sha(rawpath)))
    pair.write_csv(out/'summary.csv',rows);pair.write_csv(out/'curves.csv',curves)
    result=dict(status='MEASURED_SAMPLED_BOUNDARY',conditions=conditions,widths_um=WIDTHS,
        rejected_widths_um=sorted(set(r['keeper_width_um'] for r in rows if r['min_net_discharge_ua']<=0)),
        geometry=dict(evaluation_nfet_w_um=2,footer_nfet_w_um=1.5,output_pfet_w_um=3,output_nfet_w_um=2,l_um=.15),
        limitation='Settled-address schematic branch; real input/inverter delay, R-C parasitics, mismatch and dynamic noise require separate tests.',
        runner_sha256=pair.sha(Path(__file__)),models=pair.model_dependencies(pair.NATIVE_MODEL))
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(result['rejected_widths_um'])


if __name__=='__main__':main()
