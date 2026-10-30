#!/usr/bin/env python3
"""Measure local PCLK/address boundary screens on the frozen decoder/WL PEX.

Crossings and fixed dwell criteria are identical across sweep points. A failed
boundary point is measured data, not a simulator error. No SRAM access-time,
frequency, flip-flop setup/hold or intrinsic model-validity limit is approved.
"""
from __future__ import annotations
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

ROOT=pair.ROOT
HIGH_DWELL_NS=0.25
RESET_DWELL_NS=0.10
EDGE_NS=pair.EDGE_PS*1e-3


def schedule(low_ns=7.1,high_ns=5.4,lead_ps=2100):
    pair.require(all(math.isfinite(v) for v in (low_ns,high_ns,lead_ps)), 'Nonfinite schedule')
    pair.require(low_ns>EDGE_NS and high_ns>EDGE_NS,'PCLK pulses must exceed ramp duration')
    rise=10+low_ns;fall=rise+high_ns
    return dict(low_ns=low_ns,high_ns=high_ns,address_lead_ps=lead_ps,
                rise_ns=rise,fall_ns=fall,address_ns=rise-lead_ps*1e-3,stop_ns=fall+5)


def make_deck(inputs,profile,old,new,step_ps,cap_ff,when):
    deck,terminals=pair.make_deck(inputs,profile,old,new,step_ps,cap_ff)
    # The installed system spinit sets eight frontend threads, overriding OMP.
    # Set the frontend variable after initialization and before executing run.
    deck=deck.replace('.control\n','.control\nset num_threads=1\necho TIMING_LIMITS_NUM_THREADS=$num_threads\n',1)
    vdd=pair.PROFILES[profile][1];stop=when['stop_ns']*1e-9
    transitions=[(c*1e-9-EDGE_NS*0.5e-9,c*1e-9+EDGE_NS*0.5e-9,v)
                 for c,v in ((5,vdd),(10,0),(when['rise_ns'],vdd),(when['fall_ns'],0))]
    deck=re.sub(r'(?m)^VPCLK .*$', 'VPCLK PCLK 0 '+pair.pwl(0,transitions,stop),deck)
    for bit in range(2):
        old_bit,new_bit=(old>>bit)&1,(new>>bit)&1
        change=[]
        if old_bit!=new_bit:
            center=when['address_ns']*1e-9
            pair.require(center-EDGE_NS*0.5e-9>=10e-9+EDGE_NS*0.5e-9,
                         'Address change would overlap the first evaluation')
            change=[(center-EDGE_NS*0.5e-9,center+EDGE_NS*0.5e-9,new_bit*vdd)]
        deck=re.sub(rf'(?m)^VA{bit} .*$',f'VA{bit} A{bit} 0 '+pair.pwl(old_bit*vdd,change,stop),deck)
    deck=re.sub(r'(?m)^\.tran .*$',f'.tran {step_ps:g}p {when["stop_ns"]:g}n 0 {step_ps:g}p uic',deck)
    return deck,terminals


def longest_dwell(time,good,start,end,tail=False):
    """Conservative duration from consecutive sampled points, not an isolated peak."""
    indices=np.flatnonzero((time>=start)&(time<=end))
    pair.require(indices.size>=4,'Too few samples in the dwell window')
    t=time[indices];flags=good[indices]
    if tail:
        if not flags[-1]:return 0.0
        bad=np.flatnonzero(~flags)
        first=int(bad[-1]+1) if bad.size else 0
        return float(t[-1]-t[first])*1e9
    boundaries=np.diff(np.r_[False,flags,False].astype(int))
    starts=np.flatnonzero(boundaries==1);ends=np.flatnonzero(boundaries==-1)-1
    return max((float(t[b]-t[a])*1e9 for a,b in zip(starts,ends)),default=0.0)


def stable_lead_ns(time,good,start,end,rise):
    """Lead of the final continuously valid tail, conservatively sampled."""
    indices=np.flatnonzero((time>=start)&(time<=end))
    pair.require(indices.size>=4,'Too few literal samples')
    t=time[indices];flags=good[indices]
    if not flags[-1]:return float(rise-t[-1])*1e9
    bad=np.flatnonzero(~flags)
    first=int(bad[-1]+1) if bad.size else 0
    return float(rise-t[first])*1e9


def analyze(raw,profile,old,new,terminals,when,literal_guard_ps=None):
    time=raw['time'];vdd=pair.PROFILES[profile][1]
    pair.require(np.all(np.isfinite(time)) and np.all(np.diff(time)>0),'Invalid time vector')
    pair.require(time[-1]>=when['stop_ns']*1e-9-1e-14,'Incomplete transient')
    def trace(node):
        if node=='0':return np.zeros_like(time)
        result=raw['v('+node.lower()+')']
        pair.require(np.all(np.isfinite(result)),f'Nonfinite voltage: {node}')
        return result
    def mask(start,end):
        result=(time>=start*1e-9)&(time<=end*1e-9)
        pair.require(np.count_nonzero(result)>=4,'Incomplete measurement window')
        return result
    checks=[]
    def check(name,value,minimum,maximum):
        checks.append(dict(check=name,value=float(value),min=minimum,max=maximum,
                           status='PASS' if minimum<=value<=maximum else 'FAIL'))
    # Keep the normal first pulse as a fixed priming/control check.
    for row in range(4):
        for family in ('DEC','WL'):
            signal=trace(f'{family}{row}')
            value=np.min(signal[mask(8.8,9.975)]) if row==old else np.max(signal[mask(8.8,9.975)])
            check(f'{family}{row}_priming',value,0.9*vdd if row==old else -0.1*vdd,
                  1.1*vdd if row==old else 0.1*vdd)
    pre=when['rise_ns']-EDGE_NS/2
    low=np.ones_like(time,dtype=bool)
    for row in range(4):
        for family in ('DEC','WL'):
            signal=trace(f'{family}{row}')
            low&=(signal>=-0.1*vdd)&(signal<=0.1*vdd)
        dynamic={node for pins in terminals.values() for node in pins.values()
                 if node.lower().startswith(f'xdec.n{row}.')}
        pair.require(bool(dynamic),f'Missing dynamic-node probes for row {row}')
        minimum=min(float(np.interp(pre*1e-9,time,trace(node))) for node in dynamic)
        check(f'N{row}_precharge_min',minimum,0.9*vdd,1.1*vdd)
    reset=longest_dwell(time,low,10e-9,pre*1e-9,tail=True)
    check('all_outputs_reset_dwell_ns',reset,RESET_DWELL_NS,math.inf)
    start=when['rise_ns']+0.4*EDGE_NS
    end=when['fall_ns']-0.4*EDGE_NS
    evaluation=mask(when['rise_ns']-EDGE_NS/2,when['fall_ns']+EDGE_NS/2)
    for row in range(4):
        if row!=new:
            for family in ('DEC','WL'):
                signal=trace(f'{family}{row}')[evaluation]
                check(f'{family}{row}_unselected_peak',np.max(signal),-0.1*vdd,0.1*vdd)
    selected_dec=trace(f'DEC{new}');selected_wl=trace(f'WL{new}')
    high=(selected_dec>=0.9*vdd)&(selected_wl>=0.9*vdd)
    high_time=longest_dwell(time,high,start*1e-9,end*1e-9)
    check('selected_DEC_WL_high90_dwell_ns',high_time,HIGH_DWELL_NS,math.inf)
    literals=[]
    if literal_guard_ps is not None:
        for name in ('A0','A0T','A0B','A1','A1T','A1B'):
            bit=int(name[1]);expected=((new>>bit)&1) ^ name.endswith('B')
            nodes=sorted({node for pins in terminals.values() for node in pins.values()
                          if node.lower().startswith(f'xdec.{name.lower()}.')})
            pair.require(bool(nodes),f'Missing literal probes: {name}')
            for node in nodes:
                signal=trace(node)
                good=((signal>=0.9*vdd)&(signal<=1.1*vdd) if expected else
                      (signal>=-0.1*vdd)&(signal<=0.1*vdd))
                lead=stable_lead_ns(time,good,(10+EDGE_NS/2)*1e-9,
                    (when['fall_ns']-EDGE_NS/2)*1e-9,when['rise_ns']*1e-9)
                literals.append(dict(node=node,expected=expected,stable_lead_ps=lead*1e3))
        check('all_literals_stable_lead_ps',min(r['stable_lead_ps'] for r in literals),
              literal_guard_ps,math.inf)
    recovery=mask(when['fall_ns']+2,when['fall_ns']+4.5)
    for row in range(4):
        for family in ('DEC','WL'):
            check(f'{family}{row}_final_precharge',np.max(trace(f'{family}{row}')[recovery]),-0.1*vdd,0.1*vdd)
    wl90=pair.crossing(time,selected_wl,0.9*vdd,True,when['rise_ns']*1e-9-25e-12,when['fall_ns']*1e-9+25e-12)
    bias_window=mask(2,when['stop_ns']-0.5)
    extrema=[]
    for device,pins in terminals.items():
        for label,a,b in [('vgs','g','s'),('vgd','g','d'),('vds','d','s'),('vgb','g','b')]:
            values=(trace(pins[a])-trace(pins[b]))[bias_window]
            extrema.append(dict(device=device,voltage=label,min_v=float(np.min(values)),
                max_v=float(np.max(values)),abs_max_v=float(np.max(np.abs(values)))))
    worst=max(extrema,key=lambda row:row['abs_max_v'])
    passed=all(row['status']=='PASS' for row in checks)
    return dict(timing_screen='PASS' if passed else 'FAIL',
        voltage_screen='PASS' if worst['abs_max_v']<=pair.MAGNITUDE_SCREEN_V else 'REVIEW_REQUIRED',
        reset_dwell_ns=reset,selected_high90_dwell_ns=high_time,
        literal_settling=literals,
        wl90_delay_ps=None if wl90 is None else (wl90-when['rise_ns']*1e-9)*1e12,
        worst_external_bias=worst,checks_pass=sum(row['status']=='PASS' for row in checks),
        checks_fail=sum(row['status']=='FAIL' for row in checks)),checks,extrema


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--axis',choices=('address','precharge','evaluation','retention','confirm'),required=True)
    parser.add_argument('--values',nargs='+',type=float)
    parser.add_argument('--profiles',nargs='+',choices=pair.PROFILES,default=['ss','ff'])
    parser.add_argument('--transitions',nargs='+',default=['1:2'])
    parser.add_argument('--precharge-ns',type=float,default=7.1)
    parser.add_argument('--evaluation-ns',type=float,default=5.4)
    parser.add_argument('--address-lead-ps',type=float,default=2100)
    parser.add_argument('--step-ps',type=float,default=5)
    parser.add_argument('--literal-guard-ps',type=float,
        help='Optional experimental internal-literal stable lead before PCLK50')
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--keep-raw',action='store_true')
    args=parser.parse_args()
    pair.require(not args.output_dir.exists(),'Use a new output directory')
    pair.require(math.isfinite(args.step_ps) and 0<args.step_ps<=5,'Step must be in (0,5] ps')
    pair.require(args.axis=='confirm' or bool(args.values),'Sweep values are required')
    pair.require(args.literal_guard_ps is None or
                 (math.isfinite(args.literal_guard_ps) and args.literal_guard_ps>=0),
                 'Literal guard must be finite and nonnegative')
    transitions=[tuple(map(int,t.split(':'))) for t in args.transitions]
    pair.require(all(len(t)==2 and all(0<=a<4 for a in t) for t in transitions),'Invalid addresses')
    inputs=pair.release_inputs()
    load_provenance=json.loads(pair.LOAD_CSV.with_suffix('.provenance.json').read_text())
    pair.require(pair.sha(pair.LOAD_CSV)==load_provenance['sha256'],'Changed pinned row-load evidence')
    evidence=pair.load_wl_capacitance_evidence(pair.LOAD_CSV,102.873935496)
    cap=evidence['measured_max_ff']
    out=args.output_dir;out.mkdir(parents=True)
    (out/'executed_script.py').write_bytes(Path(__file__).read_bytes())
    helpers=out/'helper_snapshots';helpers.mkdir()
    for name in ('run_canonical_decoder_wl.py','plot_row_decoder_review.py','run_row_decoder_contract.py',
                 'run_row_decoder_capture_timing.py','run_row_decoder_tt.py'):
        shutil.copy2(Path(__file__).with_name(name),helpers/name)
    manifest=dict(status='RUNNING',complete=False,axis=args.axis,profiles={p:pair.PROFILES[p] for p in args.profiles},
        criteria=dict(selected_high90_dwell_ns=HIGH_DWELL_NS,all_outputs_reset_dwell_ns=RESET_DWELL_NS,
            precharge_dynamic_min_fraction=0.9,unselected_max_fraction=0.1,
            meaning='Fixed experimental electrical dwell screens; not a bitcell read/write or clock-frequency guarantee.'),
        requested=dict(transitions=transitions,values=args.values,precharge_ns=args.precharge_ns,
            evaluation_ns=args.evaluation_ns,address_lead_ps=args.address_lead_ps,
            literal_guard_ps=args.literal_guard_ps),
        inputs={key:dict(path=str(info['path'].relative_to(ROOT)),sha256=info['sha256']) for key,info in inputs.items()},
        row_load=evidence,step_ps=args.step_ps,ngspice_threads=1,runner_sha256=pair.sha(Path(__file__)),
        helper_sha256={p.name:pair.sha(p) for p in helpers.iterdir()},
        models=pair.model_dependencies(pair.NATIVE_MODEL),ngspice_sha256=pair.sha(shutil.which('ngspice')),cases=[])
    record=out/'manifest.json';record.write_text(json.dumps(manifest,indent=2)+'\n')
    all_checks=[]
    for profile in args.profiles:
        for old,new in transitions:
            for value in ([0.0] if args.axis=='confirm' else args.values):
                low,high,lead=args.precharge_ns,args.evaluation_ns,args.address_lead_ps
                if args.axis=='address':lead=value
                if args.axis=='precharge':low=value
                if args.axis in ('evaluation','retention'):high=value
                when=schedule(low,high,lead)
                label=f'{profile}_{old}_to_{new}_{args.axis}_{value:g}'
                directory=out/label;directory.mkdir()
                deck,terminals=make_deck(inputs,profile,old,new,args.step_ps,cap,when)
                deck_path=(directory/'case.spice').resolve();deck_path.write_text(deck)
                try:
                    process=subprocess.run(['ngspice','-n','-b',str(deck_path)],cwd=directory,
                        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180,
                        env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'})
                    (directory/'ngspice.txt').write_text(process.stdout)
                    rawpath=directory/'waveform.raw'
                    pair.require(process.returncode==0 and rawpath.exists() and not re.search(
                        r'(?i)Error:|aborted|timestep too small',process.stdout),'ngspice failed')
                    pair.require(re.search(r'(?m)^TIMING_LIMITS_NUM_THREADS=1\s*$',process.stdout),
                                 'ngspice did not confirm the one-thread frontend setting')
                    raw=pair.read_raw(rawpath)
                    result,checks,extrema=analyze(raw,profile,old,new,terminals,when,args.literal_guard_ps)
                    literals=result.pop('literal_settling')
                    if literals:pair.write_csv(directory/'literal_settling.csv',literals)
                    pair.write_csv(directory/'checks.csv',checks);pair.write_csv(directory/'bias_extrema.csv',extrema)
                    variables=['time','v(pclk)','v(a0)','v(a1)']+[f'v({f}{i})' for f in ('dec','wl') for i in range(4)]
                    indices=np.linspace(0,len(raw['time'])-1,min(1800,len(raw['time']))).astype(int)
                    pair.write_csv(directory/'waveforms.csv',[{v:float(raw[v][i]) for v in variables} for i in indices])
                    if not args.keep_raw:rawpath.unlink()
                    result.update(status='MEASURED',profile=profile,old=old,new=new,value=value,schedule=when,
                                  case=label,deck_sha256=pair.sha(deck_path))
                    all_checks.extend(dict(case=label,**check) for check in checks)
                    print(f'{label}: {result["timing_screen"]}; reset={result["reset_dwell_ns"]:.3f} ns; high90={result["selected_high90_dwell_ns"]:.3f} ns',flush=True)
                except Exception as error:
                    result=dict(status='ERROR',case=label,profile=profile,value=value,schedule=when,error=str(error))
                    print(f'{label}: ERROR {error}',flush=True)
                (directory/'result.json').write_text(json.dumps(result,indent=2)+'\n')
                manifest['cases'].append(result);record.write_text(json.dumps(manifest,indent=2)+'\n')
    for info in inputs.values():pair.require(pair.sha(info['path'])==info['sha256'],'PEX changed during campaign')
    errors=sum(r['status']=='ERROR' for r in manifest['cases'])
    manifest.update(complete=not errors,status='COMPLETE_BOUNDARY_SCREEN' if not errors else 'ERROR',
                    timing_pass=sum(r.get('timing_screen')=='PASS' for r in manifest['cases']),
                    timing_fail=sum(r.get('timing_screen')=='FAIL' for r in manifest['cases']),errors=errors)
    record.write_text(json.dumps(manifest,indent=2)+'\n')
    pair.write_csv(out/'summary.csv',manifest['cases'])
    if all_checks:pair.write_csv(out/'checks.csv',all_checks)
    return 1 if errors else 0


if __name__=='__main__':
    raise SystemExit(main())
