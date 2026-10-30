#!/usr/bin/env python3
"""Measure extra-current/charge tolerance of frozen PEX and explicit keeper candidates.

Keeper candidates combine baseline PEX with schematic keeper devices; they are
hybrid pre-layout experiments, never labelled as newly extracted layouts.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import numpy as np
import run_canonical_decoder_wl as pair
import run_canonical_timing_limits as timing

POINTS=dict(pair.PROFILES)
for _corner in ('tt','ss','ff'):
    for _vdd in (1.62,1.8):
        for _temp in (-40,27,125):
            _value=(_corner,_vdd,_temp)
            if _value not in POINTS.values():POINTS[f'{_corner}_{_vdd:g}_{_temp:g}']=_value
pair.PROFILES=POINTS


def candidate_file(inputs,width,path):
    if not width:return None
    original=inputs['row_decoder']['path'].read_text()
    devices=[]
    for row in range(4):
        devices.append(f'XKEEP{row} N{row} DEC{row} VDD VDD sky130_fd_pr__pfet_01v8 '
            f'w={width:g} l=0.15 ad={width*0.29:g} as={width*0.29:g} '
            f'pd={2*(width+0.29):g} ps={2*(width+0.29):g} nrd={0.29/width:g} nrs={0.29/width:g}')
    pair.require(len(re.findall(r'(?mi)^\.ends\b',original))==1,'Unexpected PEX hierarchy')
    text=re.sub(r'(?mi)^\.ends\b',lambda m:'\n'.join(devices)+'\n'+m[0],original)
    path.write_text('* HYBRID BENCH CANDIDATE: baseline R-C PEX plus schematic feedback keepers\n'+text)
    return path.resolve()


def make_deck(inputs,profile,old,new,when,step_ps,cap_ff,keeper_width,candidate,kind,value,offset_ns):
    deck,terminals=timing.make_deck(inputs,profile,old,new,step_ps,cap_ff,when)
    if keeper_width:
        deck=deck.replace(f'.include "{inputs["row_decoder"]["path"]}"',f'.include "{candidate}"')
        for row in range(4):
            terminals[f'xdec.XKEEP{row}']=dict(d=f'xdec.N{row}',g=f'DEC{row}',s='VDD',b='VDD')
    pair.require(len(terminals)==45+(4 if keeper_width else 0),'Wrong device coverage')
    saved=' '.join(f'v(xdec.N{r})' for r in range(4))+' v(xdec.EVAL_GND)'
    deck=re.sub(r'(?m)^\.save (.*)$',lambda m:'.save '+m[1]+' '+saved,deck)
    start=(when['rise_ns']-0.025)*1e-9;stop=when['stop_ns']*1e-9
    if kind in ('leak_down','leak_up'):
        amplitude=value*1e-6
        wave=pair.pwl(0,[(start,start+50e-12,amplitude),
            ((when['fall_ns']-0.025)*1e-9,(when['fall_ns']+0.025)*1e-9,0)],stop)
    else:
        center=(when['rise_ns']+offset_ns)*1e-9
        pair.require(center-50e-12>start and center+50e-12<(when['fall_ns']-0.025)*1e-9,
                     'Charge pulse outside evaluation')
        amplitude=2*value*1e-15/100e-12
        wave=pair.pwl(0,[(center-50e-12,center,amplitude),(center,center+50e-12,0)],stop)
    targets=[new] if kind=='leak_up' else [r for r in range(4) if r!=new]
    sources=[]
    for row in targets:
        a,b=('0',f'xdec.N{row}') if kind=='leak_up' else (f'xdec.N{row}','0')
        sources.append(f'ISTRESS{row} {a} {b} {wave}')
    deck=deck.replace('.save ','\n'.join(sources)+'\n.save ',1)
    return deck,terminals,targets


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profiles',nargs='+',choices=POINTS,default=['tt','ss','ff'])
    p.add_argument('--transitions',nargs='+',default=['1:2'])
    p.add_argument('--kind',choices=('leak_down','leak_up','charge_down'),required=True)
    p.add_argument('--values',nargs='+',type=float,required=True,help='Extra current uA per target node, or charge fC per node')
    p.add_argument('--keeper-width-um',type=float,default=0)
    p.add_argument('--evaluation-ns',type=float,default=2.5)
    p.add_argument('--charge-offset-ns',type=float,default=1.5)
    p.add_argument('--step-ps',type=float,default=5)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--keep-raw',action='store_true')
    args=p.parse_args();out=args.output_dir
    pair.require(not out.exists(),'Use a new output directory')
    pair.require(all(math.isfinite(v) and v>=0 for v in args.values),'Invalid stress amplitudes')
    pair.require(len(set(args.values))==len(args.values),'Duplicate stress point')
    pair.require(args.keeper_width_um==0 or 0.42<=args.keeper_width_um<=3,'Keeper width outside exploratory range')
    pair.require(0<args.step_ps<=5,'Invalid maximum step')
    transitions=[tuple(map(int,s.split(':'))) for s in args.transitions]
    pair.require(all(len(t)==2 and all(0<=v<4 for v in t) for t in transitions),'Invalid addresses')
    inputs=pair.release_inputs();cap=pair.load_wl_capacitance_evidence(pair.LOAD_CSV,102.873935496)
    pair.require(pair.sha(pair.LOAD_CSV)==json.loads(pair.LOAD_CSV.with_suffix('.provenance.json').read_text())['sha256'],
                 'Changed row-load evidence')
    when=timing.schedule(3,args.evaluation_ns,2100);out.mkdir(parents=True)
    candidate=candidate_file(inputs,args.keeper_width_um,out/'hybrid_candidate.spice')
    (out/'executed_script.py').write_bytes(Path(__file__).read_bytes())
    helpers=out/'helper_snapshots';helpers.mkdir()
    for name in ('run_canonical_decoder_wl.py','run_canonical_timing_limits.py','plot_row_decoder_review.py',
                 'run_row_decoder_contract.py','run_row_decoder_capture_timing.py','run_row_decoder_tt.py'):
        shutil.copy2(Path(__file__).with_name(name),helpers/name)
    manifest=dict(status='RUNNING',complete=False,kind=args.kind,values=args.values,keeper_width_um=args.keeper_width_um,
        circuit_stage='hybrid_pre_layout_keeper_candidate' if candidate else 'frozen_post_layout_baseline',
        stress_interpretation='Imposed EXTRA adversarial current/charge, not measured physical leakage or an approved noise budget.',
        profiles={s:POINTS[s] for s in args.profiles},transitions=transitions,schedule=when,step_ps=args.step_ps,
        charge_offset_ns=args.charge_offset_ns,row_load=cap,models=pair.model_dependencies(pair.NATIVE_MODEL),
        runner_sha256=pair.sha(Path(__file__)),ngspice_sha256=pair.sha(shutil.which('ngspice')),
        helper_sha256={q.name:pair.sha(q) for q in helpers.iterdir()},
        inputs={k:dict(path=str(v['path'].relative_to(pair.ROOT)),sha256=v['sha256']) for k,v in inputs.items()},
        candidate_sha256=pair.sha(candidate) if candidate else None,cases=[])
    record=out/'manifest.json';record.write_text(json.dumps(manifest,indent=2)+'\n')
    for profile in args.profiles:
        for old,new in transitions:
            for value in args.values:
                label=f'{profile}_{old}_to_{new}_{args.kind}_{value:g}';folder=out/label;folder.mkdir()
                deck,terminals,targets=make_deck(inputs,profile,old,new,when,args.step_ps,cap['measured_max_ff'],
                    args.keeper_width_um,candidate,args.kind,value,args.charge_offset_ns)
                path=(folder/'case.spice').resolve();path.write_text(deck)
                try:
                    run=subprocess.run(['ngspice','-n','-b',str(path)],cwd=folder,stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,text=True,timeout=240,env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'})
                    (folder/'ngspice.txt').write_text(run.stdout);rawpath=folder/'waveform.raw'
                    pair.require(run.returncode==0 and rawpath.exists() and not re.search(
                        r'(?i)warning|error:|aborted|timestep too small',run.stdout),'Simulator failed/warned')
                    pair.require('TIMING_LIMITS_NUM_THREADS=1' in run.stdout,'Thread limit unconfirmed')
                    raw=pair.read_raw(rawpath);result,checks,extrema=timing.analyze(raw,profile,old,new,terminals,when,250)
                    literals=result.pop('literal_settling')
                    for name,data in [('checks.csv',checks),('bias_extrema.csv',extrema),('literal_settling.csv',literals)]:pair.write_csv(folder/name,data)
                    evaluation=(raw['time']>=(when['rise_ns']-0.025)*1e-9)&(raw['time']<=(when['fall_ns']+0.025)*1e-9)
                    energy=(raw['time']>=10e-9)&(raw['time']<=(when['fall_ns']+3)*1e-9)
                    result.update(status='MEASURED',case=label,profile=profile,old=old,new=new,value=value,targets=targets,
                        unselected_node_min_v=min(float(raw[f'v(xdec.n{r})'][evaluation].min()) for r in range(4) if r!=new),
                        core_supply_energy_fj=float(-POINTS[profile][1]*np.trapz(raw['i(vdd_src)'][energy],raw['time'][energy])*1e15),
                        raw_sha256=pair.sha(rawpath),deck_sha256=pair.sha(path))
                    variables=['time','v(pclk)','v(a0)','v(a1)']+[f'v({f}{r})' for f in ('dec','wl') for r in range(4)]
                    variables +=[f'v(xdec.n{r})' for r in range(4)]+['v(xdec.eval_gnd)']
                    indices=np.linspace(0,len(raw['time'])-1,min(1600,len(raw['time']))).astype(int)
                    if args.kind=='charge_down':
                        indices=np.r_[indices,np.flatnonzero(np.abs(raw['time']-(when['rise_ns']+args.charge_offset_ns)*1e-9)<0.1e-9)]
                    indices=np.unique(indices)
                    pair.write_csv(folder/'waveforms.csv',[{v:float(raw[v][i]) for v in variables} for i in indices])
                    if not args.keep_raw:rawpath.unlink()
                    print(f'{label}: {result["timing_screen"]}/{result["voltage_screen"]}; Nmin={result["unselected_node_min_v"]:.3f} V',flush=True)
                except Exception as error:
                    result=dict(status='ERROR',case=label,error=str(error));print(f'{label}: ERROR {error}',flush=True)
                (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');manifest['cases'].append(result)
                record.write_text(json.dumps(manifest,indent=2)+'\n')
    errors=sum(r['status']=='ERROR' for r in manifest['cases'])
    for info in inputs.values():pair.require(pair.sha(info['path'])==info['sha256'],'Frozen PEX changed')
    manifest.update(complete=not errors,status='MEASURED_BOUNDARY' if not errors else 'ERROR',errors=errors)
    record.write_text(json.dumps(manifest,indent=2)+'\n');pair.write_csv(out/'summary.csv',manifest['cases'])
    return 1 if errors else 0


if __name__=='__main__':raise SystemExit(main())
