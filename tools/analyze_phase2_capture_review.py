#!/usr/bin/env python3
"""Measured valid-level windows at raw sense output and actual FF D.

This is nominal waveform analysis, not setup/hold characterization. Unchanged
bits may already be valid at the start of observation; report lower bounds.
"""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from run_phase2_digital import ROOT,sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',default='reports/phase2/extracted_access_singlethread')
    p.add_argument('--output',default='reports/phase2/review_20261104/capture_baseline')
    args=p.parse_args();source=ROOT/args.source;out=(ROOT/args.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2') or out==ROOT/'reports/phase2':p.error('Output under reports/phase2 required')
    out.mkdir(parents=True,exist_ok=True)
    try:
        state=json.loads((source/'results.json').read_text())
        if state['status'] not in ('PASS_EXTRACTED_NOMINAL_ACCESS','PASS_DIRECTED_NOMINAL'):raise ValueError('Completed electrical trace required')
        base=ROOT/'reports/phase2/extracted_access_singlethread';capture=state
        if 'capture_inputs' not in state:
            if state['baseline_receipt_sha256']!=sha(base/'results.json'):raise ValueError('Capture reference changed')
            capture=json.loads((base/'results.json').read_text())
        wave=ROOT/state['build_directory']/'waveform.dat'
        if sha(wave)!=state['raw_waveform_sha256']:raise ValueError('Raw waveform changed')
        data=np.loadtxt(wave,skiprows=1);time=data[:,0]*1e9;vectors=state['vectors'];rows=[]
        for r in state['cycles']:
            if r['operation']!='read':continue
            for bit in range(8):
                clk=data[:,vectors.index(capture['capture_clocks'][bit])+1]
                candidates=np.flatnonzero((clk[:-1]<.9)&(clk[1:]>=.9)&(time[:-1]>r['fall_ns']-.5)&(time[:-1]<r['fall_ns']+1))
                if len(candidates)!=1:raise ValueError('Ambiguous local capture clock')
                i=int(candidates[0]);edge=float(time[i]+(.9-clk[i])/(clk[i+1]-clk[i])*(time[i+1]-time[i]));expected=(r['expected']>>bit)&1
                for stage,column in [('DOUT_RAW/SA_OUT',17+bit),('FF_D_after_mux',vectors.index(capture['capture_inputs'][bit])+1)]:
                    values=data[:,column];valid=((values>=1.44)&(values<=1.98)) if expected else ((values>=-.18)&(values<=.36))
                    before=np.flatnonzero((time>=r['rise_ns'])&(time<edge)&~valid)
                    after=np.flatnonzero((time>=edge)&(time<=edge+2)&~valid)
                    start=float(time[before[-1]+1]) if len(before) else float(r['rise_ns'])
                    stop=float(time[after[0]]) if len(after) else edge+2
                    rows.append(dict(cycle=r['cycle'],bit=bit,stage=stage,local_capture_ns=edge,
                                     setup_valid_window_ns=edge-start,hold_valid_window_ns=stop-edge,
                                     setup_lower_bound=not bool(len(before)),hold_lower_bound=not bool(len(after))))
        with (out/'valid_windows.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        result={'status':'PASS_RAW_CAPTURE_MEASUREMENTS','scope':'Measured valid-level observation windows; no new timing criterion or full SRAM STA',
                'hold_observation_limit_ns':2.0,'interpretation':'A hold window of 2 ns is a lower bound limited by this observation window, not an exact hold specification',
                'source_receipt_sha256':sha(source/'results.json'),'raw_sha256':sha(wave),'rows':len(rows),
                'minimum_setup_window_ns':{s:min(r['setup_valid_window_ns'] for r in rows if r['stage']==s) for s in {r['stage'] for r in rows}},
                'minimum_hold_window_ns':{s:min(r['hold_valid_window_ns'] for r in rows if r['stage']==s) for s in {r['stage'] for r in rows}},
                'table_sha256':sha(out/'valid_windows.csv')}
    except Exception as e:result={'status':'FAIL','error':str(e)}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    return 0 if result['status']=='PASS_RAW_CAPTURE_MEASUREMENTS' else 1


if __name__=='__main__':raise SystemExit(main())
