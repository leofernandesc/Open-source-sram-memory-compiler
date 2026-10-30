#!/usr/bin/env python3
"""Probe actual BSIM4 states of the frozen decoder/WL PEX without changing it.

Published signed-range findings are separate from functional checks and from
the custom terminal-magnitude screen. They are not reliability verdicts.
"""
from __future__ import annotations
import argparse
import csv
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
from audit_signed_device_domain import LIMITS

ROOT=pair.ROOT
MODEL_DIR=Path('/opt/pdks/sky130A/libs.ref/sky130_fd_pr/spice')


def passive_islands(inputs):
    """Find resistor components touching no MOS terminal or external port."""
    result=[]
    for prefix,leaf in [('xdec','row_decoder'),*[(f'xwl{i}','wl_driver') for i in range(4)]]:
        info=inputs[leaf];active={p.lower() for p in info['pins']}|{'0'};nodes=set();parent={};caps=[]
        def find(node):
            parent.setdefault(node,node)
            if parent[node]!=node:parent[node]=find(parent[node])
            return parent[node]
        for device in info['devices']:active.update(n.lower() for n in device[1:5])
        for line in pair.logical(info['path'].read_text()):
            fields=line.lower().split()
            if not fields or fields[0][0] not in ('r','c'):continue
            a,b=fields[1:3];nodes.update((a,b))
            if fields[0][0]=='r':parent[find(a)]=find(b)
            else:
                value=fields[3];cap=float(value[:-1])*1e-15 if value.endswith('f') else float(value)
                caps.append((a,b,cap))
        groups={}
        for node in nodes:groups.setdefault(find(node),set()).add(node)
        for group in groups.values():
            if group&active:continue
            cap=sum(value for a,b,value in caps if (a in group) != (b in group))
            pair.require(cap>0,'Passive island without finite positive coupling')
            result.append(dict(node=prefix+'.'+sorted(group)[0],component=sorted(group),coupling_cap_f=cap,
                               proof='Resistor component contains no leaf port or MOS D/G/S/B terminal.'))
    return result


def probe_map(inputs):
    result={}
    for prefix,leaf in [('xdec','row_decoder'),*[(f'xwl{i}','wl_driver') for i in range(4)]]:
        for device in inputs[leaf]['devices']:
            model=device[5];kind='n' if model.endswith('__nfet_01v8') else 'p'
            pair.require(model==f'sky130_fd_pr__{kind}fet_01v8','Unexpected primitive model')
            label=prefix+'.'+device[0]
            primitive=f'm.{label.lower()}.msky130_fd_pr__{kind}fet_01v8'
            result[label]=dict(kind=kind,primitive=primitive,
                queries={q:f'@{primitive}[{q}]' for q in ('vgs','vds','vbs','id')})
    pair.require(len(result)==45,'Expected 45 intrinsic MOS probes')
    return result


def oriented_states(kind,vgs,vds,vbs):
    """Convert polarity-normalized model states to physical signed reverse-mode biases."""
    pair.require(kind in ('n','p'),'Unknown MOS polarity')
    polarity=1 if kind=='n' else -1
    shift=np.minimum(vds,0)
    return dict(VGS=polarity*(vgs-shift),VDS=polarity*np.abs(vds),VBS=polarity*(vbs-shift))


def state_trace(raw,query):
    candidates=[key for key in (query,f'v({query})',f'i({query})') if key in raw]
    pair.require(len(candidates)==1,f'Missing/ambiguous intrinsic query: {query}')
    trace=raw[candidates[0]]
    pair.require(trace.shape==raw['time'].shape and np.isfinite(trace).all(),f'Invalid query: {query}')
    return trace


def phase_at(ns,when):
    edges=(5,10,when['rise_ns'],when['fall_ns'])
    if any(abs(ns-edge)<=pair.EDGE_PS*0.5e-3 for edge in edges):return 'clock_ramp'
    if 5<ns<10 or when['rise_ns']<ns<when['fall_ns']:return 'evaluation'
    return 'precharge'


def span_bounds_ps(time,flags):
    """Bounds using endpoint classifications, without counting points as durations."""
    dt=np.diff(time)*1e12
    return float(dt[flags[:-1]&flags[1:]].sum()),float(dt[flags[:-1]|flags[1:]].sum())


def measure(raw,terminals,probes,when):
    time=raw['time'];rows=[];events=[];magnitudes=[]
    def voltage(node):return np.zeros_like(time) if node=='0' else raw[f'v({node.lower()})']
    pair.require(set(terminals)==set(probes),'Terminal/intrinsic probe mismatch')
    for label,pins in terminals.items():
        info=probes[label];kind=info['kind']
        d,g,s,b=[voltage(pins[q]) for q in ('d','g','s','b')]
        pair.require(all(np.isfinite(v).all() for v in (d,g,s,b)),'Nonfinite terminal voltage')
        effective=np.minimum(d,s) if kind=='n' else np.maximum(d,s)
        external=dict(VGS=g-effective,VDS=(1 if kind=='n' else -1)*np.abs(d-s),VBS=b-effective)
        states={q:state_trace(raw,query) for q,query in info['queries'].items()}
        intrinsic=oriented_states(kind,states['vgs'],states['vds'],states['vbs'])
        for window,start,end in [('full_transient',0,when['stop_ns']),('after_2ns',2,when['stop_ns']-0.5)]:
            indices=np.flatnonzero((time>=start*1e-9)&(time<=end*1e-9))
            pair.require(indices.size>4,'Incomplete intrinsic measurement window')
            for metric,whole in intrinsic.items():
                values=whole[indices];ext=external[metric][indices];low,high=LIMITS[kind][metric]
                bad=(values<low)|(values>high);lower,upper=span_bounds_ps(time[indices],bad)
                imin,imax=int(indices[np.argmin(values)]),int(indices[np.argmax(values)])
                record=dict(device=label,kind=kind,window=window,metric=metric,
                    published_min_v=low,published_max_v=high,external_min_v=float(ext.min()),
                    external_max_v=float(ext.max()),intrinsic_min_v=float(values.min()),
                    intrinsic_max_v=float(values.max()),min_time_ns=float(time[imin]*1e9),
                    max_time_ns=float(time[imax]*1e9),max_external_intrinsic_difference_v=float(np.max(np.abs(ext-values))),
                    outside_samples=int(bad.sum()),outside_duration_lower_ps=lower,outside_duration_upper_ps=upper,
                    status='OUTSIDE_PUBLISHED_RANGE' if bad.any() else 'INSIDE_PUBLISHED_RANGE')
                rows.append(record)
                if window!='after_2ns':continue
                for side,index,limit in [('lower',imin,low),('upper',imax,high)]:
                    peak=float(whole[index])
                    if not (peak<low if side=='lower' else peak>high):continue
                    events.append(dict(device=label,kind=kind,metric=metric,side=side,time_ns=float(time[index]*1e9),
                        intrinsic_v=peak,external_v=float(external[metric][index]),limit_v=limit,
                        excursion_v=abs(peak-limit),phase=phase_at(time[index]*1e9,when),
                        drain_v=float(d[index]),gate_v=float(g[index]),source_v=float(s[index]),bulk_v=float(b[index]),
                        normalized_vgs_v=float(states['vgs'][index]),normalized_vds_v=float(states['vds'][index]),
                        normalized_vbs_v=float(states['vbs'][index]),model_id_a=float(states['id'][index])))
        mask=(time>=2e-9)&(time<=(when['stop_ns']-0.5)*1e-9)
        for metric,signal in dict(VGS=states['vgs'],VGD=states['vgs']-states['vds'],
                                  VDS=states['vds'],VGB=states['vgs']-states['vbs']).items():
            magnitudes.append(dict(device=label,metric=metric,abs_max_v=float(np.max(np.abs(signal[mask])))))
    # Retain dense event windows for the largest signed excursions, not only isolated extrema.
    selected={}
    for event in events:
        key=(event['kind'],event['metric'],event['side'])
        if key not in selected or event['excursion_v']>selected[key]['excursion_v']:selected[key]=event
    windows=[]
    for key,event in selected.items():
        label=event['device'];pins=terminals[label];info=probes[label]
        states={q:state_trace(raw,query) for q,query in info['queries'].items()}
        oriented=oriented_states(info['kind'],states['vgs'],states['vds'],states['vbs'])
        for index in np.flatnonzero(np.abs(time-event['time_ns']*1e-9)<=0.15e-9):
            windows.append(dict(event='/'.join(key),device=label,time_ns=float(time[index]*1e9),
                **{q+'_v':float(voltage(pins[q])[index]) for q in ('d','g','s','b')},
                **{metric.lower()+'_intrinsic_v':float(v[index]) for metric,v in oriented.items()},
                id_a=float(states['id'][index]),pclk_v=float(raw['v(pclk)'][index])))
    return rows,events,magnitudes,windows


def compare_reference(raw,profile,old,new,when,step_ps):
    paths=[]
    for path in (ROOT/'sims/row_decoder/results').glob('canonical_contract_robust*20261028/manifest.json'):
        manifest=json.loads(path.read_text())
        paths.extend((path,manifest,row) for row in manifest['cases']
                     if (row['profile'],row['old'],row['new'])==(profile,old,new))
    pair.require(len(paths)==1,'Missing/ambiguous archived UIC reference')
    path,manifest,row=paths[0]
    pair.require(manifest['complete'] and row['schedule']==when and manifest['step_ps']==step_ps,
                 'Archived UIC schedule/step differs')
    for model,expected in manifest['models'].items():
        pair.require(pair.sha(Path(model))==expected,'Native model changed from archived UIC reference')
    source=path.parent/row['case']/'waveforms.csv'
    with source.open() as handle:records=list(csv.DictReader(handle))
    indices=np.linspace(0,len(raw['time'])-1,min(1800,len(raw['time']))).astype(int)
    equal=len(records)==len(indices) and all(np.array_equal(
        np.array([float(r[name]) for r in records]),raw[name][indices]) for name in records[0])
    return dict(manifest=str(path.relative_to(ROOT)),manifest_sha256=pair.sha(path),
                waveforms_sha256=pair.sha(source),saved_plot_samples_bitwise_equal=bool(equal))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles',nargs='+',choices=pair.PROFILES,default=list(pair.PROFILES))
    parser.add_argument('--transitions',nargs='+',default=['1:2','3:2'])
    parser.add_argument('--initializations',nargs='+',choices=('uic','anchored_uic','op'),default=['uic','anchored_uic','op'])
    parser.add_argument('--dc-anchor-ohm',type=float,default=1e12,
        help='Simulation-only DC reference on passive capacitive islands, used by anchored_uic/op')
    parser.add_argument('--step-ps',type=float,default=5)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--keep-raw',action='store_true')
    args=parser.parse_args()
    pair.require(not args.output_dir.exists(),'Use a new output directory')
    pair.require(math.isfinite(args.step_ps) and 0<args.step_ps<=5,'Invalid maximum step')
    pair.require(math.isfinite(args.dc_anchor_ohm) and args.dc_anchor_ohm>0,'Invalid DC anchor')
    transitions=[tuple(map(int,t.split(':'))) for t in args.transitions]
    pair.require(all(len(t)==2 and all(0<=a<4 for a in t) for t in transitions),'Invalid addresses')
    pair.require(len(set(transitions))==len(transitions) and len(set(args.profiles))==len(args.profiles)
                 and len(set(args.initializations))==len(args.initializations),'Duplicate case request')
    inputs=pair.release_inputs();probes=probe_map(inputs);islands=passive_islands(inputs);when=timing.schedule(3,2.5,2100)
    provenance=json.loads(pair.LOAD_CSV.with_suffix('.provenance.json').read_text())
    pair.require(pair.sha(pair.LOAD_CSV)==provenance['sha256'],'Changed pinned row Ceff')
    load=pair.load_wl_capacitance_evidence(pair.LOAD_CSV,102.873935496)
    wrappers={}
    for kind in ('n','p'):
        path=MODEL_DIR/f'sky130_fd_pr__{kind}fet_01v8.pm3.spice';text=path.read_text()
        pair.require(re.search(rf'(?m)^msky130_fd_pr__{kind}fet_01v8\s+d\s+g\s+s\s+b\s+',text)
                     and re.search(r'version\s*=\s*4\.5\b',text),'Unrecognized native primitive/state model')
        wrappers[kind]=dict(path=str(path),sha256=pair.sha(path),version='BSIM4.5')
    out=args.output_dir;out.mkdir(parents=True)
    (out/'executed_script.py').write_bytes(Path(__file__).read_bytes())
    helpers=out/'helper_snapshots';helpers.mkdir()
    names=('run_canonical_decoder_wl.py','run_canonical_timing_limits.py','audit_signed_device_domain.py',
           'plot_row_decoder_review.py','run_row_decoder_contract.py','run_row_decoder_capture_timing.py','run_row_decoder_tt.py')
    for name in names:shutil.copy2(Path(__file__).with_name(name),helpers/name)
    manifest=dict(status='RUNNING',complete=False,scope='Focused intrinsic-state probe of all 45 MOS in six profile/transition cases, comparing unmodified UIC, passive-island-anchored UIC and anchored OP; no model/reliability acceptance.',
        profiles={p:pair.PROFILES[p] for p in args.profiles},transitions=transitions,
        initializations=args.initializations,schedule=when,step_ps=args.step_ps,row_load=load,
        passive_islands=islands,dc_anchor_ohm=args.dc_anchor_ohm,
        published_signed_ranges=LIMITS,model_wrappers=wrappers,models=pair.model_dependencies(pair.NATIVE_MODEL),
        runner_sha256=pair.sha(Path(__file__)),helper_sha256={p.name:pair.sha(p) for p in helpers.iterdir()},
        ngspice_sha256=pair.sha(shutil.which('ngspice')),probes=probes,
        inputs={k:dict(path=str(v['path'].relative_to(ROOT)),sha256=v['sha256']) for k,v in inputs.items()},cases=[])
    record=out/'manifest.json';record.write_text(json.dumps(manifest,indent=2)+'\n')
    for profile in args.profiles:
        for old,new in transitions:
            for initialization in args.initializations:
                label=f'{profile}_{old}_to_{new}_{initialization}';directory=out/label;directory.mkdir()
                deck,terminals=timing.make_deck(inputs,profile,old,new,args.step_ps,load['measured_max_ff'],when)
                extra=' '.join(query for info in probes.values() for query in info['queries'].values())
                extra+=' '+' '.join(f'v({island["node"]})' for island in islands)
                deck=re.sub(r'(?m)^\.save (.*)$',lambda m:'.save '+m[1]+' '+extra,deck)
                anchored=initialization!='uic'
                if anchored:
                    additions='\n'.join(f'RDC_ISLAND_ONLY_{i} {island["node"]} 0 {args.dc_anchor_ohm:g}'
                                        for i,island in enumerate(islands))
                    deck=deck.replace('.save ',additions+'\n.save ',1)
                if initialization=='op':deck=deck.replace(' uic\n','\n')
                path=(directory/'case.spice').resolve();path.write_text(deck)
                try:
                    process=subprocess.run(['ngspice','-n','-b',str(path)],cwd=directory,
                        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=240,
                        env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'})
                    (directory/'ngspice.txt').write_text(process.stdout);rawpath=directory/'waveform.raw'
                    pair.require(process.returncode==0 and rawpath.exists() and not re.search(
                        r'(?i)warning|error:|aborted|timestep too small',process.stdout),'Simulator/query warning or failure')
                    pair.require(re.search(r'(?m)^TIMING_LIMITS_NUM_THREADS=1\s*$',process.stdout),'Unconfirmed one-thread execution')
                    raw=pair.read_raw(rawpath)
                    functional,checks,external_bias=timing.analyze(raw,profile,old,new,terminals,when,250)
                    literals=functional.pop('literal_settling')
                    pair.require(functional['timing_screen']=='PASS','Local timing/selection screen failed')
                    rows,events,magnitudes,windows=measure(raw,terminals,probes,when)
                    for name,data in [('checks.csv',checks),('external_bias.csv',external_bias),
                        ('literal_settling.csv',literals),('signed_bias.csv',rows),('intrinsic_magnitudes.csv',magnitudes)]:
                        pair.write_csv(directory/name,data)
                    if events:pair.write_csv(directory/'events.csv',events)
                    if windows:pair.write_csv(directory/'event_windows.csv',windows)
                    variables=['time','v(pclk)','v(a0)','v(a1)']+[f'v({f}{i})' for f in ('dec','wl') for i in range(4)]
                    indices=np.linspace(0,len(raw['time'])-1,min(1800,len(raw['time']))).astype(int)
                    pair.write_csv(directory/'waveforms.csv',[{v:float(raw[v][i]) for v in variables} for i in indices])
                    reference=None
                    if initialization=='uic' and args.step_ps==5:
                        reference=compare_reference(raw,profile,old,new,when,args.step_ps)
                        pair.require(reference['saved_plot_samples_bitwise_equal'],'Added intrinsic queries changed archived plot samples')
                    after=[r for r in rows if r['window']=='after_2ns']
                    outside=[r for r in after if r['status']=='OUTSIDE_PUBLISHED_RANGE']
                    result=dict(status='MEASURED',case=label,profile=profile,old=old,new=new,initialization=initialization,
                        raw_sha256=pair.sha(rawpath),raw_points=len(raw['time']),raw_variables=len(raw),
                        deck_sha256=pair.sha(path),functional=functional,reference=reference,
                        signed_domain='REVIEW_REQUIRED' if outside else 'INSIDE_PUBLISHED_SCREEN',
                        intrinsic_outside_device_metrics=len(outside),max_intrinsic_magnitude_v=max(r['abs_max_v'] for r in magnitudes),
                        max_signed_excursion_v=max((r['excursion_v'] for r in events),default=0),
                        dc_anchor_ohm=args.dc_anchor_ohm if anchored else None,
                        dc_anchor_peak_current_a=max((float(np.max(np.abs(raw[f'v({i["node"]})'])))/args.dc_anchor_ohm
                                                     for i in islands),default=0) if anchored else 0,
                        raw_retained_locally=args.keep_raw)
                    if not args.keep_raw:rawpath.unlink()
                    print(f'{label}: timing PASS; intrinsic range {result["signed_domain"]}; {len(outside)} device/metric findings',flush=True)
                except Exception as error:
                    result=dict(status='ERROR',case=label,error=str(error))
                    print(f'{label}: ERROR {error}',flush=True)
                (directory/'result.json').write_text(json.dumps(result,indent=2)+'\n')
                manifest['cases'].append(result);record.write_text(json.dumps(manifest,indent=2)+'\n')
    for info in inputs.values():pair.require(pair.sha(info['path'])==info['sha256'],'Frozen PEX changed')
    errors=sum(r['status']=='ERROR' for r in manifest['cases'])
    manifest.update(complete=not errors,errors=errors,status='MEASURED_REVIEW_REQUIRED' if not errors and
                    any(r['signed_domain']=='REVIEW_REQUIRED' for r in manifest['cases']) else ('MEASURED' if not errors else 'ERROR'))
    record.write_text(json.dumps(manifest,indent=2)+'\n')
    return 1 if errors else 0


if __name__=='__main__':raise SystemExit(main())
