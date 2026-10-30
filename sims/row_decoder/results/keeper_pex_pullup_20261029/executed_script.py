#!/usr/bin/env python3
"""Characterize the independently checked 33-MOS decoder PEX plus frozen WL PEX.

Results retain the published signed-bias coverage findings separately from
functional checks and the experimental 1.95 V magnitude screen.
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
import run_canonical_intrinsic_bias as intrinsic
import run_canonical_timing_limits as timing
from measure_keeper_contention import POINTS
pair=intrinsic.pair
pair.PROFILES=POINTS


def revision_inputs():
    inputs=pair.release_inputs()
    root=pair.ROOT/'layout/row_decoder_keeper'
    state=json.loads((root/'pex/provenance.json').read_text())
    pair.require(state['status']=='current','Keeper PEX is not current')
    for item in state['files'].values():
        pair.require(pair.sha(pair.ROOT/item['path'])==item['sha256'],'Changed keeper extraction input')
    proofpath=root/'qualification/verification/row_decoder/result.json'
    proof=json.loads(proofpath.read_text());folder=proofpath.parent
    pair.require(proof['status']=='PASS' and proof['mos_count']==33 and proof['drc_groups']==0 and
        proof['lvs']=='UNIQUE_MATCH_WITH_W_L_AND_TERMINALS' and len(proof['negative_controls'])==5 and
        set(proof['negative_controls'].values())=={'REJECTED_AS_EXPECTED'},'Keeper primitive-MOS physical proof missing')
    for name,expected in proof['evidence_sha256'].items():
        pair.require(pair.sha(folder/name)==expected,'Changed keeper physical evidence')
    path=root/'pex/row_decoder_pex.spice';name,pins,devices=pair.subcircuit(path)
    pair.require(len(devices)==33 and pins==inputs['row_decoder']['pins'] and pair.sha(path)==proof['pex_sha256'],
                 'Keeper PEX count/pins/hash do not match checked masks')
    for line in pair.logical(path.read_text()):
        fields=line.split()
        if fields and fields[0][0] in 'RC':
            number=float(fields[3].rstrip('f'))
            pair.require(number>=0 and (number>0 or fields[0][0]=='C'),'Nonpositive R or negative C')
    inputs['row_decoder']=dict(path=path,sha256=pair.sha(path),subcircuit=name,pins=pins,devices=devices)
    return inputs,proofpath


def make_deck(inputs,profile,old,new,when,args,load):
    deck,terminals=timing.make_deck(inputs,profile,old,new,args.step_ps,load,when,decoder_mos=33)
    probes=intrinsic.probe_map(inputs,49);islands=intrinsic.passive_islands(inputs)
    extra=' '.join(query for info in probes.values() for query in info['queries'].values())
    extra+=' '+' '.join(f'v(xdec.N{r})' for r in range(4))+' v(xdec.EVAL_GND)'
    deck=re.sub(r'(?m)^\.save (.*)$',lambda m:'.save '+m[1]+' '+extra,deck)
    if args.initialization!='uic':
        anchors='\n'.join(f'RDC_PASSIVE_ONLY_{i} {v["node"]} 0 1e12' for i,v in enumerate(islands))
        deck=deck.replace('.save ',anchors+'\n.save ',1)
    if args.initialization=='op':deck=deck.replace(' uic\n','\n')
    if args.kind!='none':
        start=(when['rise_ns']-.025)*1e-9;end=(when['fall_ns']-.025)*1e-9
        if args.kind=='charge_down':
            center=(when['rise_ns']+args.charge_offset_ns)*1e-9
            pair.require(center-50e-12>start and center+50e-12<end,'Charge outside evaluation')
            wave=pair.pwl(0,[(center-50e-12,center,2*args.value*1e-15/100e-12),
                (center,center+50e-12,0)],when['stop_ns']*1e-9)
        else:wave=pair.pwl(0,[(start,start+50e-12,args.value*1e-6),(end,end+50e-12,0)],when['stop_ns']*1e-9)
        targets=[new] if args.kind=='leak_up' else [r for r in range(4) if r!=new]
        sources=[]
        for row in targets:
            a,b=('0',f'xdec.N{row}') if args.kind=='leak_up' else (f'xdec.N{row}','0')
            sources.append(f'ISTRESS{row} {a} {b} {wave}')
        deck=deck.replace('.save ','\n'.join(sources)+'\n.save ',1)
    return deck,terminals,probes,islands


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--profiles',nargs='+',choices=POINTS,default=['tt','ss','ff'])
    p.add_argument('--transitions',nargs='+',default=[f'{a}:{b}' for a in range(4) for b in range(4)])
    p.add_argument('--initialization',choices=('uic','anchored_uic','op'),default='uic')
    p.add_argument('--kind',choices=('none','leak_down','leak_up','charge_down'),default='none')
    p.add_argument('--value',type=float,default=0,help='Extra uA or fC per target node')
    p.add_argument('--charge-offset-ns',type=float,default=1.5)
    p.add_argument('--step-ps',type=float,default=5)
    p.add_argument('--high-ns',type=float,default=2.5)
    p.add_argument('--keep-raw',action='store_true')
    args=p.parse_args();out=args.output_dir
    pair.require(not out.exists(),'Use a new directory')
    pair.require(math.isfinite(args.value) and args.value>=0 and 0<args.step_ps<=5,'Invalid stress/step')
    pair.require(args.kind!='none' or args.value==0,'A nonzero value requires a stress kind')
    transitions=[tuple(map(int,v.split(':'))) for v in args.transitions]
    pair.require(all(len(t)==2 and all(0<=a<4 for a in t) for t in transitions),'Invalid addresses')
    pair.require(len(set(transitions))==len(transitions) and len(set(args.profiles))==len(args.profiles),'Duplicate case')
    inputs,proof=revision_inputs();load=pair.load_wl_capacitance_evidence(pair.LOAD_CSV,102.873935496)
    pair.require(pair.sha(pair.LOAD_CSV)==json.loads(pair.LOAD_CSV.with_suffix('.provenance.json').read_text())['sha256'],'Changed row load')
    when=timing.schedule(3,args.high_ns,2100);out.mkdir(parents=True)
    (out/'executed_script.py').write_bytes(Path(__file__).read_bytes());helpers=out/'helper_snapshots';helpers.mkdir()
    for name in ('run_canonical_intrinsic_bias.py','run_canonical_decoder_wl.py','run_canonical_timing_limits.py',
        'audit_signed_device_domain.py','plot_row_decoder_review.py','run_row_decoder_contract.py',
        'run_row_decoder_capture_timing.py','run_row_decoder_tt.py','measure_keeper_contention.py','run_decoder_robustness.py'):
        shutil.copy2(Path(__file__).with_name(name),helpers/name)
    manifest=dict(status='RUNNING',complete=False,stage='new_distributed_RC_PEX',expected_mos=49,
        scope='Decoder + four WL drivers with row Ceff; no bitcell data access, capture/control or statistical reliability signoff.',
        profiles={p:POINTS[p] for p in args.profiles},transitions=transitions,schedule=when,
        kind=args.kind,value=args.value,charge_offset_ns=args.charge_offset_ns,initialization=args.initialization,
        step_ps=args.step_ps,row_load=load,models=pair.model_dependencies(pair.NATIVE_MODEL),
        physical_proof=dict(path=str(proof.relative_to(pair.ROOT)),sha256=pair.sha(proof)),
        inputs={k:dict(path=str(v['path'].relative_to(pair.ROOT)),sha256=v['sha256']) for k,v in inputs.items()},
        runner_sha256=pair.sha(Path(__file__)),helper_sha256={p.name:pair.sha(p) for p in helpers.iterdir()},
        ngspice_sha256=pair.sha(shutil.which('ngspice')),cases=[])
    record=out/'manifest.json';record.write_text(json.dumps(manifest,indent=2)+'\n')
    for profile in args.profiles:
        for old,new in transitions:
            label=f'{profile}_{old}_to_{new}';folder=out/label;folder.mkdir()
            deck,terminals,probes,islands=make_deck(inputs,profile,old,new,when,args,load['measured_max_ff'])
            path=(folder/'case.spice').resolve();path.write_text(deck)
            try:
                run=subprocess.run(['ngspice','-n','-b',str(path)],cwd=folder,stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,text=True,timeout=300,env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'})
                (folder/'ngspice.txt').write_text(run.stdout);rawpath=folder/'waveform.raw'
                pair.require(run.returncode==0 and rawpath.exists() and not re.search(r'(?i)warning|error:|aborted|timestep too small',run.stdout),'Simulator failed/warned')
                pair.require('TIMING_LIMITS_NUM_THREADS=1' in run.stdout,'Unconfirmed one-thread execution')
                raw=pair.read_raw(rawpath);result,checks,bias=timing.analyze(raw,profile,old,new,terminals,when,250)
                literals=result.pop('literal_settling');signed,events,magnitude,windows=intrinsic.measure(raw,terminals,probes,when)
                for name,data in [('checks.csv',checks),('external_bias.csv',bias),('literal_settling.csv',literals),
                    ('signed_bias.csv',signed),('intrinsic_magnitudes.csv',magnitude),('events.csv',events),('event_windows.csv',windows)]:
                    if data:pair.write_csv(folder/name,data)
                t=raw['time'];evaluation=(t>=(when['rise_ns']-.025)*1e-9)&(t<=(when['fall_ns']+.025)*1e-9)
                energy=(t>=10e-9)&(t<=(when['fall_ns']+3)*1e-9)
                result.update(status='MEASURED',case=label,profile=profile,old=old,new=new,
                    max_intrinsic_magnitude_v=max(r['abs_max_v'] for r in magnitude),
                    signed_domain_findings=sum(r['status']=='OUTSIDE_PUBLISHED_RANGE' for r in signed if r['window']=='after_2ns'),
                    unselected_node_min_v=min(float(raw[f'v(xdec.n{r})'][evaluation].min()) for r in range(4) if r!=new),
                    core_supply_energy_fj=float(-POINTS[profile][1]*np.trapz(raw['i(vdd_src)'][energy],t[energy])*1e15),
                    passive_islands=islands,raw_sha256=pair.sha(rawpath),deck_sha256=pair.sha(path))
                variables=['time','v(pclk)','v(a0)','v(a1)']+[f'v({f}{r})' for f in ('dec','wl') for r in range(4)]
                variables +=[f'v(xdec.n{r})' for r in range(4)]+['v(xdec.eval_gnd)']
                indices=np.linspace(0,len(t)-1,min(1800,len(t))).astype(int)
                if args.kind=='charge_down':indices=np.r_[indices,np.flatnonzero(np.abs(t-(when['rise_ns']+args.charge_offset_ns)*1e-9)<.1e-9)]
                pair.write_csv(folder/'waveforms.csv',[{v:float(raw[v][i]) for v in variables} for i in np.unique(indices)])
                if not args.keep_raw:rawpath.unlink()
                print(f'{label}: {result["timing_screen"]}/{result["voltage_screen"]}; WL90={result["wl90_delay_ps"]} ps',flush=True)
            except Exception as error:
                result=dict(status='ERROR',case=label,error=str(error));print(f'{label}: ERROR {error}',flush=True)
            (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');manifest['cases'].append(result)
            record.write_text(json.dumps(manifest,indent=2)+'\n')
    for v in inputs.values():pair.require(pair.sha(v['path'])==v['sha256'],'PEX changed during run')
    errors=sum(r['status']=='ERROR' for r in manifest['cases'])
    passes=all(r['status']=='MEASURED' and r['timing_screen']=='PASS' and r['voltage_screen']=='PASS' and
               r['max_intrinsic_magnitude_v']<=1.95 for r in manifest['cases'])
    manifest.update(complete=not errors,status='PASS_EXPERIMENTAL_SCREEN' if passes else ('ERROR' if errors else 'MEASURED_BOUNDARY'))
    record.write_text(json.dumps(manifest,indent=2)+'\n');pair.write_csv(out/'summary.csv',manifest['cases'])
    return 1 if errors else 0


if __name__=='__main__':raise SystemExit(main())
