#!/usr/bin/env python3
"""Gate an isolated sense-3 experiment on observable TT replay fidelity."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_phase3_data3_tt import load
from analyze_phase3_sclk_r87_full import edges, gate_shape, interpret_gate, scalar, view
from diagnose_phase3_sclk_startup import write_json
from phase3_rc_read_path import HIGH, LOW
from review_phase3_bus_ss import Trace, ge, le
from run_phase3_eco_pex import pinned, sha256
from run_phase3_sclk_r87_full import FIDELITY
from run_phase3_sense3_isolation import GATES, MOS_CURRENTS, OBSERVE, REFERENCE, START, STOP, require


CASES = [(16,211.,219.),(17,231.,239.)]


def one_cross(trace,name,lo,hi,fraction,rising=True):
    points = trace.points(lo,hi,[(trace.cols[name],1.,0.)])
    t,v = np.asarray([(t,v[0]) for t,v in points]).T
    return scalar(edges(t,v,1.8*fraction,rising).tolist())


def reference_criteria(trace):
    margins, cases = [],[]
    for cycle,lo,hi in CASES:
        capture = one_cross(trace,'capture_clock',hi+1,hi+1.30,.5)
        tail20 = one_cross(trace,'sclk_tail',lo,hi,.2)
        tail80 = one_cross(trace,'sclk_tail',lo,hi,.8)
        require(tail20 and tail80 and capture and tail20<tail80<capture, 'Unobservable archived SCLK markers')
        margin = view(trace,'blb_at_sense',tail20)-view(trace,'bl_at_sense',tail20)
        require(margin>0.,'Missing archived input margin')
        margins.append(margin)
        # Require agreement in the neighborhood of the early sense timing.
        # Continue tracking bitlines throughout regeneration and capture.
        cases.append(dict(cycle=cycle,low_ns=lo,high_ns=hi,capture_ns=capture,tail20_ns=tail20,
                          tail80_ns=tail80,early_input_window_ns=[tail20-.05,tail20+.05],
                          conditioning_ns=lo-1.10,settle_tolerance_ns=tail80-tail20))
    reference_margin = min(margins)
    return dict(cases=cases, observed_early_margin_v=reference_margin,
                early_max_delta_error_v=reference_margin/2, common_mode_error_v=reference_margin,
                latch_conditioning_error_v=2*reference_margin,
                later_relative_delta_tolerance=.05, clock_edge_tolerance_ps=25)


def read_wave(path,receipt):
    filename = pinned(path/'waveform.dat',receipt['artifacts']['waveform.dat'])
    expected = ['time',*[f'v({node.lower()})' for node in OBSERVE.values()]]
    with filename.open() as stream:
        require(stream.readline().lower().split()==expected,'Reduced waveform columns do not match manifest')
        data = np.loadtxt(stream,ndmin=2)
    require(data.shape[0]>2 and data.shape[1]==len(expected) and np.all(np.isfinite(data))
            and np.all(np.diff(data[:,0])>0) and abs(data[-1,0]*1e9-(STOP-START))<1e-5,
            'Incomplete or nonmonotonic reduced waveform')
    currents = path/'currents.dat'
    if currents.is_file():
        with currents.open() as stream:
            head = stream.readline().lower().split()
            values = np.loadtxt(stream,ndmin=2)
        if (head==['time',*MOS_CURRENTS] and values.shape==(len(data),4)
                and np.all(np.isfinite(values)) and np.array_equal(values[:,0],data[:,0])):
            data = np.column_stack((data,values[:,1:]))
    data[:,0] += START*1e-9
    labels = list(OBSERVE)
    if data.shape[1]==len(expected)+3:
        labels.extend(('sampler_bl_id','sampler_blb_id','tail_id'))
    return Trace(data.tolist(),{name:i for i,name in enumerate(labels,1)})


def input_evidence(expected, measured, case, criteria, additional_early_center=None):
    start,stop = case['low_ns']-.1,case['capture_ns']
    ta,tb = np.asarray(expected.times),np.asarray(measured.times)
    a,b = case['early_input_window_ns']
    times = np.union1d(np.r_[ta[(ta>start)&(ta<stop)],start,stop,a,b],tb[(tb>start)&(tb<stop)])
    if additional_early_center is not None:
        x,y = additional_early_center-.05,additional_early_center+.05
        times = np.union1d(times,[x,y])
    def probes(trace,clock):
        return [np.interp(times,clock,[row[trace.cols[signal]] for row in trace.rows])
                for signal in ('bl_at_sense','blb_at_sense')]
    l0,r0 = probes(expected,ta)
    l1,r1 = probes(measured,tb)
    d0,d1 = r0-l0,r1-l1
    delta_error = abs(d0-d1)
    common_error = abs((l0+r0-l1-r1)/2)
    early = (times>=a)&(times<=b)
    if additional_early_center is not None:
        early |= (times>=x)&(times<=y)
    tolerance = np.maximum(criteria['early_max_delta_error_v'],criteria['later_relative_delta_tolerance']*abs(d0))
    tolerance[early] = criteria['early_max_delta_error_v']
    early_err = float(max(delta_error[early]))
    early_cm = float(max(common_error[early]))
    return dict(eligible=bool(np.all(delta_error<=tolerance) and max(common_error)<=criteria['common_mode_error_v']),
                max_delta_error_early_v=early_err,max_common_mode_error_early_v=early_cm,
                max_delta_error_window_v=float(max(delta_error)),max_common_mode_error_window_v=float(max(common_error)),
                max_delta_error_at_ns=float(times[np.argmax(delta_error)]),
                max_common_error_at_ns=float(times[np.argmax(common_error)]),
                peak_excess_delta_v=float(max(delta_error-tolerance)),
                bitline_error_peaks_v=[float(max(abs(l0-l1))),float(max(abs(r0-r1)))])


def assess_event(trace,case):
    begin,end = case['low_ns'],case['high_ns']
    captured = case['capture_ns']
    shape = {g:gate_shape(trace,g,begin,end) for g in GATES}
    tail20 = scalar(shape['sclk_tail']['rise_ns']['20'])
    tail50 = scalar(shape['sclk_tail']['rise_ns']['50'])
    tone = tail20 if tail20 is not None else begin
    lhs,rhs = trace.cols['sense_out'],trace.cols['sense_bar']
    positive = trace.signal_window(tone,captured,[ge(lhs,HIGH),le(rhs,LOW)],suffix=True)
    negative = trace.signal_window(tone,captured,[le(lhs,LOW),ge(rhs,HIGH)],suffix=True)
    decision = 'WRONG' if positive else ('CORRECT' if negative else 'UNRESOLVED')
    window = positive or negative
    t0 = case['conditioning_ns']
    probes = ('bl_at_sense','blb_at_sense','sense_out','sense_bar','sa_sampling_out','sab_sampling_out',
              'sclk_tail','sense_tail','tail_ground','read_d','precharge','vdd')
    def snapshot(t):
        values = {n:view(trace,n,t) for n in probes if n in trace.cols}
        values['difference_bl_v'] = values['blb_at_sense']-values['bl_at_sense']
        values['common_mode_v'] = (values['blb_at_sense']+values['bl_at_sense'])/2
        values['latch_difference_v'] = values['sab_sampling_out']-values['sa_sampling_out']
        if 'tail_ground' in values:
            values['tail_vgs'] = values['sclk_tail']-values['tail_ground']
        for name in ('sampler_bl_id','sampler_blb_id','tail_id'):
            if name in trace.cols:
                values[name+'_a'] = view(trace,name,t)
        return dict(at_ns=t,**values)
    points = [(t,x[0]-x[1]) for t,x in trace.points(tone,captured,
                       [(trace.cols['sab_sampling_out'],1.,0.),(trace.cols['sa_sampling_out'],1.,0.)])]
    t,y = np.asarray(points).T
    return dict(cycle=case['cycle'],decision=decision,stable_decision=window,clock=shape,
                conditioning=snapshot(t0),before_activation=snapshot(tone-.05),activation=snapshot(tone),
                tail50=snapshot(tail50) if tail50 is not None else None,
                latch_polarity_crossings_ns={name:edges(t,y,0,rising).tolist()
                                             for name,rising in [('rise',True),('fall',False)]},
                captured_observation=snapshot(captured),
                decision_delay_from_tail20_ps=(window['first_actual_ns']-tone)*1000 if window and tail20 is not None else None)


def comparable(reference, control, limit):
    old,new = reference['stable_decision'],control['stable_decision']
    return bool(old and new and abs(new['first_actual_ns']-old['first_actual_ns'])<=limit)


def control_verdict(events):
    if len(events)!=2:
        return 'INCONCLUSIVE'
    if any(case['isolated']['decision']=='CORRECT' for case in events):
        return 'NOT_REPRODUCED'
    if all(case['isolated']['decision']=='WRONG' and case['input']['eligible'] and
           case['conditioning_valid'] and case['tail_conditioning']['compatible']
           and case['clock_valid'] and case['decision_timing_compatible']
           and case['reference']['decision']=='WRONG' for case in events):
        return 'REPRODUCED'
    return 'INCONCLUSIVE'


def contrast_verdict(events):
    if len(events)!=2 or not all(r['sclk_fidelity'] and r['same_bitline_terminals'] and r['same_conditioning']
                                 for r in events):
        return 'INCONCLUSIVE'
    states = {r['isolated']['decision'] for r in events}
    if states=={'CORRECT'}:
        return 'CORROBORATED'
    if states=={'WRONG'}:
        return 'NOT_CORROBORATED'
    return 'INCONCLUSIVE'


def conditioning_valid(reference,trial,threshold):
    return all(reference['conditioning'][n]>=HIGH and trial['conditioning'][n]>=HIGH and
               abs(reference['conditioning'][n]-trial['conditioning'][n])<=threshold
               for n in ('sense_out','sense_bar','sa_sampling_out','sab_sampling_out'))


def tail_conditioning(reference,trial,threshold):
    """Check retained charge in the floating tail as well as the latch rails."""
    delta = trial['conditioning']['sense_tail']-reference['conditioning']['sense_tail']
    early_delta = trial['activation']['sense_tail']-reference['activation']['sense_tail']
    old50,new50 = reference['tail50'],trial['tail50']
    return dict(initial_difference_v=delta,at_tail20_difference_v=early_delta,
                at_tail50_difference_v=new50['sense_tail']-old50['sense_tail'] if old50 and new50 else None,
                tail_id_at_tail50_a=new50.get('tail_id_a') if new50 else None,
                compatible=abs(delta)<=threshold)


def analyze(root,case):
    run = root/case
    result = run/'result.json'
    receipt = json.loads(result.read_text())
    for name,digest in receipt['artifacts'].items():
        pinned(run/name,digest)
    raw = root/'manifest.json'
    pinned(raw,json.loads((run/'attempt.json').read_text())['manifest_sha256'])
    manifest = json.loads(raw.read_text())
    report = dict(verdict='INCONCLUSIVE',stage=case,result_sha256=sha256(result),
                  manifest_sha256=sha256(raw),electrical_qualification='NOT_CHARACTERIZED',
                  analyzer_sha256=sha256(Path(__file__)))
    gate_path = root/f'{case}_gate.json'
    if case=='control':
        report['control_result_sha256'] = sha256(result)
    if receipt['status']!='COMPLETED':
        report['reason'] = 'Simulator did not complete the authorized reduced transient'
        write_json(gate_path,report)
        return report
    _,_,origin = load(REFERENCE,True)
    origin.cols['vdd']=10
    observed = read_wave(run,receipt)
    criteria = manifest['criteria']
    events = []
    if case=='control':
        for window in criteria['cases']:
            a,b = assess_event(origin,window),assess_event(observed,window)
            nominal = dict(FIDELITY,displacement_ps=0)
            timing = [interpret_gate(a['clock'][g],b['clock'][g],nominal) for g in GATES]
            events.append(dict(window=window,reference=a,isolated=b,input=input_evidence(origin,observed,window,criteria),
                               clock=timing,clock_valid=all(r['fidelity_verified'] for r in timing),
                               conditioning_valid=conditioning_valid(a,b,criteria['latch_conditioning_error_v']),
                               tail_conditioning=tail_conditioning(a,b,criteria['latch_conditioning_error_v']),
                               decision_timing_compatible=comparable(a,b,window['settle_tolerance_ns'])))
        verdict = control_verdict(events)
        reproduced = all(r['reference']['decision']==r['isolated']['decision']=='WRONG' for r in events)
        report.update(verdict=verdict,decision_reproduction='REPRODUCED' if reproduced else 'NOT_REPRODUCED',
                      contrast_authorized=verdict=='REPRODUCED',comparisons=events)
    else:
        control = root/'control'
        accepted = json.loads((root/'control_gate.json').read_text())
        require(accepted['verdict']=='REPRODUCED','Control does not authorize contrast analysis')
        checked_result = json.loads(pinned(control/'result.json',accepted['control_result_sha256']).read_text())
        require(all((control/file).read_bytes()==(run/file).read_bytes() for file in ('slice.spice','stimuli.spice','bench.spice')),
                'Non-SCLK deck difference in contrast')
        prior = read_wave(control,checked_result)
        for window in criteria['cases']:
            a,b = assess_event(prior,window),assess_event(observed,window)
            timing = [interpret_gate(a['clock'][g],b['clock'][g],FIDELITY) for g in GATES]
            input_quality = input_evidence(prior,observed,window,criteria,b['activation']['at_ns'])
            events.append(dict(window=window,control=a,isolated=b,input=input_quality,clock=timing,
                      sclk_fidelity=all(r['fidelity_verified'] for r in timing),same_bitline_terminals=input_quality['eligible'],
                      same_conditioning=conditioning_valid(a,b,criteria['latch_conditioning_error_v'])
                      and tail_conditioning(a,b,criteria['latch_conditioning_error_v'])['compatible']))
        report.update(verdict=contrast_verdict(events),comparisons=events)
    write_json(gate_path,report)
    print(case,report['verdict'],flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('control','contrast'))
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    analyze(args.output,args.stage)


if __name__=='__main__':
    main()
