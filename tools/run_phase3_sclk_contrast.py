#!/usr/bin/env python3
"""Seal one fixture-only displacement of the three local SCLK gates of sense 3."""

import argparse
from bisect import bisect_left, bisect_right
import json
import math
from pathlib import Path
import re

from analyze_phase3_data3_tt import SS, event, load, snapshot
from run_phase3_data3_tt import BUILD, ROOT, require, sha256, simulate
from run_phase3_eco_pex import new_directory


REFERENCE = BUILD/'data3_tt_20261120'
GATES = ('sclk_sampler_bl','sclk_sampler_blb','sclk_tail')
CYCLES = (16,17)
BL_GATE = 'sclk_sampler_bl'


def sizing(evidence):
    """Borrow the successful *relative* timing in SS as a contrast, not a limit."""
    cases = {name:{r['origin_cycle']:r for r in items['checks']}
             for name,items in evidence['cases'].items()}
    proof = []
    for cycle in CYCLES:
        tt,ss = cases['reduced_tt'][cycle], cases['archived_ss'][cycle]
        tt_wait = tt['sclk_tail_ns']['20']-tt['wl_ns']['80']
        ss_wait = ss['sclk_sampling_ns']['20']-ss['wl_ns']['80']
        proof.append(dict(cycle=cycle,tt_tail20_minus_local_wl80_ps=1000*tt_wait,
                          ss_sampler20_minus_row_probe_wl80_ps=1000*ss_wait,
                          displacement_to_match_ps=1000*(ss_wait-tt_wait),
                          reference_tt_capture_ns=tt['capture_ns'],
                          baseline_tt_tail20_ns=tt['sclk_tail_ns']['20']))
    delay = math.ceil(max(row['displacement_to_match_ps'] for row in proof))
    require(0<delay<1000,'Expected one sub-ns displacement from independently measured events')
    for row in proof:
        row['post_displacement_time_to_capture_ns'] = row['reference_tt_capture_ns']-(
            row['baseline_tt_tail20_ns']+delay/1000)
    return delay,proof


def playback(trace, col, zones, delay_ns):
    """Translate native PWL points, including the exact interpolated seam values."""
    result=[]
    for start,end in zones:
        i,j=bisect_right(trace.times,start-delay_ns),bisect_left(trace.times,end-delay_ns)
        result.append((start,trace.value(start-delay_ns,col)))
        result.extend((trace.times[k]+delay_ns,trace.rows[k][col]) for k in range(i,j))
        result.append((end,trace.value(end-delay_ns,col)))
    return result


def pwl(label,node,points):
    pts=[' '.join(f'{t:.9f}n {v:.10g}' for t,v in points[i:i+4]) for i in range(0,len(points),4)]
    return [f'{label} {node} 0 PWL({pts[0]}', *('+ '+s for s in pts[1:]), '+ )']


def instrument(binding,mapping,trace,zones,delay_ns):
    # Add a *fixture* source in series with each existing split-node gate
    # resistor. R and C values and all transistor terminals remain intact.
    # Outside the two interventions the source is zero volts (transparent).
    # With mask=1, V(gate)=V(replay) exactly. This ideal intervention is not
    # evidence of physical driver impedance, edge generation or power.
    cards = binding.splitlines()
    injected = []
    paths=[]
    masks=[(0.,0.)]
    for begin,end in zones:
        masks.extend([(begin,0.),(begin+.025,1.),(end-.025,1.),(end,0.)])
    decks = pwl('V_sclk_fixture_mask','sclk_fixture_mask',masks)
    for index,alias in enumerate(GATES):
        node=mapping[alias]
        found=[i for i,line in enumerate(cards) if re.match(r'^R\d+ ',line) and node in line.split()[1:3]]
        require(len(found)==1, f'Expected one original access resistor for {alias}')
        i,=found
        ideal=f'sclk_fixture_series_{index}'
        target=f'sclk_fixture_replay_{index}'
        orig=cards[i]
        resistor,a,b,ohm=orig.split()
        require(b==node and a!=node, 'Unexpected extracted topology at local SCLK gate')
        cards[i]=f'{resistor} {a} {ideal} {ohm}'
        paths.append(dict(gate=alias,spice_node=node,original_card=orig,adapter_card=cards[i]))
        decks.extend(pwl(f'V_sclk_fixture_{index}',target,playback(trace,trace.cols[alias],zones,delay_ns)))
        injected.append(f'B_sclk_fixture_{index} {node} {ideal} V={{V(sclk_fixture_mask)*(V({target})-V({ideal}))}}')
    end=cards.pop()
    require(end.lower().startswith('.ends '),'Unexpected binding structure')
    return '\n'.join([*cards,*decks,*injected,end])+'\n',paths


def prepare(out):
    archived=BUILD/'data3_tt_diagnosis_final_20261120'/'diagnosis.json'
    evidence=json.loads(archived.read_text())
    parent,run,trace=load(REFERENCE,True)
    _,ss,_=load(SS,False)
    require(evidence['cases']['reduced_tt']['waveform_sha256']==run['waveform_sha256'] and
            evidence['cases']['archived_ss']['waveform_sha256']==ss['waveform_sha256'] and
            evidence['cases']['reduced_tt']['reproduced_same_readback_failure'],'Invalid replay inputs')
    delay,checks=sizing(evidence)
    for row in checks:
        cycle=row['cycle']
        nominal_fall=220.+20*(cycle-16)
        row['reference_tt_fall50_ns']=event(trace,'public_clk',nominal_fall-.01,nominal_fall+.1,.9,False)
        early=row['baseline_tt_tail20_ns']
        row['reference_before']=snapshot(trace,early,'baseline_tail20')
        row['reference_at_proposed_tail20']=snapshot(trace,early+delay/1000,'unmodified_trajectory_at_planned_event')
    # Intervention in the low-slew region before the rise, then release
    # on the flat high plateau before the original falling edge.
    zones=[(211.,219.),(231.,239.)]
    seams=[]
    for begin,end in zones:
        for alias in GATES:
            col=trace.cols[alias]
            for when in (begin,begin+.025,end-.025,end):
                delta=abs(trace.value(when,col)-trace.value(when-delay/1000,col))
                require(delta<.001,'Expected flat playback seam (1 mV instrumentation criterion)')
                seams.append(dict(gate=alias,time_ns=when,baseline_delta_v=delta))
    mapping=json.loads((REFERENCE/'probes.json').read_text())
    binding=(REFERENCE/'binding.spice').read_text()
    overlay,links=instrument(binding,mapping,trace,zones,delay/1000)
    bench=(REFERENCE/'bench.spice').read_text()
    require(bench.count('.include "binding.spice"')==1,'Missing original bench include')
    output=new_directory(out)
    for name in ('binding.spice','fabric.spice','model_hashes.json','probes.json'):
        (output/name).write_bytes((REFERENCE/name).read_bytes())
    (output/'bench.spice').write_text(bench.replace('.include "binding.spice"','.include "sclk_fixture.spice"'))
    (output/'sclk_fixture.spice').write_text(overlay)
    paths=(REFERENCE/'preflight.json',REFERENCE/'simulation.json',REFERENCE/'waveform.dat',archived,
           SS/'simulation.json',Path(__file__).resolve())
    parent.update(role='sclk_contrast_fixture_only',displacement_ps=delay,choice=checks,seams=seams,
                  intervention_intervals_ns=zones,local_gate_resistors=links,
                  sources={str(p.relative_to(ROOT)):sha256(p) for p in paths},
                  contrast_waveform_sha256=run['waveform_sha256'],
                  artifacts={p.name:sha256(p) for p in output.iterdir()})
    (output/'preflight.json').write_text(json.dumps(parent,indent=2)+'\n')
    print(f'Sealed one local SCLK activation displacement: {delay} ps',flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','simulate'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--timeout',type=int,default=2100)
    args=parser.parse_args()
    out=args.output.resolve()
    if args.action=='prepare':
        prepare(out)
        return 0
    require(0<args.timeout<=2100,'Use wall timeout of at most 2100 seconds')
    require(json.loads((out/'preflight.json').read_text())['role']=='sclk_contrast_fixture_only',
            'Expected a sealed fixture-only intervention')
    return simulate(out,args.timeout)


if __name__=='__main__':
    raise SystemExit(main())
