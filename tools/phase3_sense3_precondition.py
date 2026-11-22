#!/usr/bin/env python3
"""Extend the existing sense-3 replay and gate a rise-only TT contrast."""

import argparse
from collections import Counter
from decimal import Decimal
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import time

import numpy as np

from analyze_phase3_sense3_isolation import (
    assess_event, comparable, conditioning_valid, input_evidence, one_cross, tail_conditioning,
)
from analyze_phase3_sclk_r87_full import gate_shape, interpret_gate, scalar, view
from diagnose_phase3_sclk_startup import write_json
from phase3_rc_read_path import HIGH, LOW
from review_phase3_bus_ss import Trace
from run_phase3_data3_tt import BUILD, PARENT, PDK, ROOT, checked_preparation, model_closure
from run_phase3_eco_pex import new_directory, ngspice_limits, pinned, sha256
from run_phase3_sense3_isolation import (
    EDGE_PS, GATES, MOS_CURRENTS, OBSERVE, REFERENCE, REPLAY_V, SHIFT_PS, SHIFT_WINDOWS,
    START as OLD_START, STOP, TIMEOUT_S, compress, load, pwl, require,
)
from run_phase3_sclk_r87_full import FIDELITY


START = 188.0
ORIGINAL = BUILD / 'sense3_isolation_20261120'
ORIGINAL_MANIFEST = '64ed4c939c798dfa5eede631161cd477afeeb222952449ff6992d433cb5aba17'
ORIGINAL_GATE = '285bf6e021e48ee069f14fd88188bb54452f414b8abb2913c298e61abda6977a'
FILES = ('bench.spice', 'slice.spice', 'stimuli.spice')
TAIL_ON_A = 1e-6


def pwl_tokens(card):
    head, sep, values = card.partition(' PWL(')
    require(sep and values.rstrip().endswith(')'), 'Missing PWL definition')
    fields = values.rstrip()[:-1].replace('\n+', ' ').split()
    require(len(fields) >= 4 and len(fields) % 2 == 0, 'Incomplete PWL knot list')
    pairs = [(Decimal(t.removesuffix('n')), v) for t,v in zip(fields[::2], fields[1::2], strict=True)]
    require(all(a[0] < b[0] for a,b in zip(pairs, pairs[1:])), 'Nonmonotonic PWL')
    return head, pairs


def write_knots(head, pairs):
    fields = [f'{t:f}n {v}' for t,v in pairs]
    rows = [' '.join(fields[i:i+6]) for i in range(0, len(fields), 6)]
    return f'{head} PWL(' + '\n+ '.join(rows) + '\n+ )\n'


def extend_pwl(card, history_t, history_v):
    head, old = pwl_tokens(card)
    require(old[0][0] == 0 and old[-1][0] == Decimal(str(STOP - OLD_START)), 'Unexpected old PWL horizon')
    voltage = history_v.copy()
    require(abs(voltage[-1] - float(old[0][1])) < 1e-10, 'Replay seam has changed voltage')
    voltage[-1] = float(old[0][1])
    times, values = compress(history_t, voltage)
    _, prefix = pwl_tokens(pwl('Vunused', 'a', 'b', times - START, values))
    offset = Decimal(str(OLD_START - START))
    shifted = [(t + offset, v) for t,v in old]
    final = write_knots(head, [*prefix[:-1], *shifted])
    _, result = pwl_tokens(final)
    require(prefix[-1][0] == offset and result[len(prefix)-1:] == shifted, 'Old replay segment was changed')
    error = float(max(abs(history_v - np.interp(history_t - START,
                      [float(t) for t,_ in result], [float(v) for _,v in result]))))
    require(error <= REPLAY_V + 1e-8, f'Replay compression exceeded its envelope: {error} V')
    return final, dict(prefix_knots=len(prefix)-1, preserved_knots=len(old), max_history_error_v=error)


def replay_start(trace):
    levels = {name:view(trace,name,START) for name in
              ('public_clk','precharge','sclk_tail','bl_at_sense','blb_at_sense','sense_out','sense_bar','sense_tail')}
    require(all(levels[n] <= LOW for n in ('public_clk','precharge','sclk_tail')) and
            all(levels[n] >= HIGH for n in ('bl_at_sense','blb_at_sense','sense_out','sense_bar')),
            'Proposed start is outside the archived precharge plateau')
    events = {f'{name}_{edge}20_ns':one_cross(trace,name,a,b,.2,rising) for name in ('precharge','sclk_tail')
              for edge,a,b,rising in (('previous_fall',180.,START,False),('cycle15_rise',191.,199.,True),
                                      ('cycle15_fall',200.,OLD_START,False))}
    require(all(value is not None for value in events.values()), 'Missing cycle-15 event or recovery')
    return dict(levels_v=levels, events=events)


def prepare(output):
    old_manifest_path = pinned(ORIGINAL/'manifest.json', ORIGINAL_MANIFEST)
    old_gate = pinned(ORIGINAL/'control_gate.json', ORIGINAL_GATE)
    old = json.loads(old_manifest_path.read_text())
    base_files = {name:pinned(ORIGINAL/name, old['artifacts_sha256'][name]) for name in FILES}
    physical = checked_preparation(PARENT)
    reference, receipt, trace = load(REFERENCE, True)
    trace.cols['vdd'] = 10
    require(physical['pex_sha256'] == reference['pex_sha256'] and
            receipt['waveform_sha256'] == old['reference_waveform_sha256'], 'Physical or waveform lineage changed')
    models = REFERENCE/'model_hashes.json'
    require(model_closure(PDK) == json.loads(models.read_text()), 'Model closure has changed')
    provenance = replay_start(trace)
    old_sources = base_files['stimuli.spice'].read_text()
    source_cards = re.split(r'\n(?=VPORT\d+ )', old_sources.rstrip('\n'))
    require(source_cards[0] == 'VSS_REF VSS 0 0' and len(source_cards) == 1+len(old['ports']),
            'Unexpected archived source inventory')
    cards, extensions = [source_cards[0]+'\n'], {}
    for index,(node,port) in enumerate(old['ports'].items()):
        card = source_cards[index+1]
        if 'trace' not in port:
            require(card == f'VPORT{index} {node} {port["rail"]} 0', 'Archived DC pin changed')
            cards.append(card+'\n')
            continue
        head, _ = pwl_tokens(card)
        require(head == f'VPORT{index} {node} VSS' and node != OBSERVE['sense_tail'],
                'Archived replay pins do not match the reduced circuit')
        name = port['trace']
        values = trace.points(START,OLD_START,[(trace.cols[name],1.,0.)])
        t,v = np.asarray([(ns,volts[0]) for ns,volts in values]).T
        extension, details = extend_pwl(card,t,v)
        cards.append(extension)
        extensions[node] = details
    slice_bytes = base_files['slice.spice'].read_bytes()
    require(Counter(line[:1] for line in slice_bytes.splitlines()) == {b'X':36,b'R':493,b'C':968},
            'Unexpected MOS/R/C inventory')
    bench = base_files['bench.spice'].read_text()
    old_tran = f'tran 10p {STOP-OLD_START:g}n 0 25p'
    require(bench.splitlines().count(old_tran) == 1, 'Unexpected archived transient')
    bench = bench.replace(old_tran, f'tran 10p {STOP-START:g}n 0 25p')
    criteria = old['criteria']
    criteria['tail_envelope_windows_ns'] = [[case['conditioning_ns'],
        criteria['cases'][i+1]['conditioning_ns'] if i+1 < len(criteria['cases']) else STOP]
        for i,case in enumerate(criteria['cases'])]
    criteria['tail_channel_conduction_marker_a'] = TAIL_ON_A
    criteria['contrast_fidelity'] = FIDELITY
    criteria['contrast_timing_windows_ns'] = SHIFT_WINDOWS
    source_files = [Path(__file__).resolve(), old_manifest_path, old_gate, *base_files.values(), models,
                    *[REFERENCE/name for name in ('preflight.json','simulation.json','waveform.dat','bench.spice',
                                                  'binding.spice','probes.json')]]
    out = new_directory(output)
    (out/'slice.spice').write_bytes(slice_bytes)
    (out/'bench.spice').write_text(bench)
    (out/'stimuli.spice').write_text(''.join(cards))
    write_json(out/'manifest.json',dict(schema='phase3.sense3_precondition.v1', conditions=dict(old['conditions'],
        start_reference_ns=START,horizon_ns=STOP-START), previous_slice_manifest=str(old_manifest_path.relative_to(ROOT)),
        previous_control_gate=str(old_gate.relative_to(ROOT)), reference_waveform_sha256=receipt['waveform_sha256'],
        pex_sha256=reference['pex_sha256'], ports=old['ports'], replay_extensions=extensions, precharge_start=provenance,
        criteria=criteria, limitations=old['limits'], source_sha256={str(p.relative_to(ROOT)):sha256(p) for p in source_files},
        artifacts_sha256={name:sha256(out/name) for name in FILES}))
    print(f'Prepared {out}',flush=True)


def delayed_source(stimulus):
    source = next(card for card in re.split(r'\n(?=VPORT\d+ )', stimulus) if re.match(r'VPORT\d+ rc8562 VSS PWL\(',card))
    _, pairs = pwl_tokens(source)
    times = np.array([float(t) for t,_ in pairs]) + START
    volts = np.array([float(v) for _,v in pairs])
    delay = SHIFT_PS / 1000
    knots = [(0.,0.)]
    for begin,end in SHIFT_WINDOWS:
        grid = np.union1d(times[(times>begin)&(times<end)], (times+delay)[(times+delay>begin)&(times+delay<end)])
        grid = np.unique(np.r_[begin,begin+.025,grid,end-.025,end])
        weight = np.clip(np.minimum(grid-begin,end-grid)/.025,0.,1.)
        delta = weight*(np.interp(grid-delay,times,volts)-np.interp(grid,times,volts))
        knots.extend(zip(grid-START,delta))
    t,v = np.asarray(knots).T
    return pwl('VSHIFT','sclk_driver','rc8562',t,v)


def read_receipt(root,stage):
    base = root/stage
    path = base/'result.json'
    receipt = json.loads(path.read_text())
    attempt = json.loads(pinned(base/'attempt.json',receipt['artifacts']['attempt.json']).read_text())
    pinned(root/'manifest.json',attempt['manifest_sha256'])
    for name,digest in receipt['artifacts'].items():
        pinned(base/name,digest)
    for name,digest in attempt['inputs_sha256'].items():
        pinned(base/name,digest)
    for name in FILES:
        pinned(base/name,sha256(root/name))
    return receipt


def validate_authorization(root):
    gate_path = root/'control_gate.json'
    gate = json.loads(gate_path.read_text())
    require(gate['verdict']=='VALIDATED' and gate['contrast_authorized'] is True,
            'BLOCKED: extended control did not validate')
    pinned(root/'manifest.json',gate['manifest_sha256'])
    pinned(root/'control/result.json',gate['result_sha256'])
    require(read_receipt(root,'control')['status']=='COMPLETED','BLOCKED: control simulation is incomplete')
    return gate_path


def run(root,stage):
    manifest = json.loads((root/'manifest.json').read_text())
    require(manifest['schema']=='phase3.sense3_precondition.v1', 'Unexpected experiment schema')
    for file,digest in manifest['source_sha256'].items():
        pinned(ROOT/file,digest)
    for file,digest in manifest['artifacts_sha256'].items():
        pinned(root/file,digest)
    require(model_closure(PDK) == json.loads((REFERENCE/'model_hashes.json').read_text()), 'Model closure has drifted')
    gate = validate_authorization(root) if stage=='contrast' else None
    shift = delayed_source((root/'stimuli.spice').read_text()) if gate else 'VSHIFT sclk_driver rc8562 0\n'
    out = new_directory(root/stage)
    for name in FILES:
        (out/name).write_bytes((root/name).read_bytes())
    (out/'clk_delta.spice').write_text(shift)
    cmd = ['stdbuf','-o0','-e0','ngspice','-n','-b','bench.spice']
    version = subprocess.check_output(['ngspice','--version'],text=True,timeout=10)
    write_json(out/'attempt.json',dict(command=cmd,stage=stage,simulator=version.strip(),timeout_s=TIMEOUT_S,
        manifest_sha256=sha256(root/'manifest.json'), inputs_sha256={p.name:sha256(p) for p in out.iterdir()},
        control_gate_sha256=sha256(gate) if gate else None))
    started = time.monotonic()
    status, result = 'INCOMPLETE', None
    with (BUILD/'.eco_simulator.lock').open('a') as lock, (out/'ngspice.log').open('xb',buffering=0) as log:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            result = subprocess.run(cmd,cwd=out,stdout=log,stderr=subprocess.STDOUT,
                env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'},
                preexec_fn=ngspice_limits,timeout=TIMEOUT_S,check=False)
        except subprocess.TimeoutExpired:
            status = 'TIMEOUT'
    elapsed = time.monotonic()-started
    log = (out/'ngspice.log').read_bytes()
    if (result and result.returncode==0 and b'No. of Data Rows' in log
            and all((out/name).is_file() for name in ('waveform.dat','currents.dat'))
            and not re.search(rb'analysis aborted|timestep too small|fatal error:|transient op failed',log,re.I)):
        status = 'COMPLETED'
    write_json(out/'result.json',dict(status=status,elapsed_s=elapsed,
        ngspice_exit_code=result.returncode if result else None,
        artifacts={p.name:sha256(p) for p in out.iterdir() if p.is_file()}))
    print(stage,status,flush=True)
    return int(status!='COMPLETED')


def read_wave(base):
    def read(name, columns):
        with (base/name).open() as stream:
            require(stream.readline().lower().split()==['time',*columns], f'Unexpected columns in {name}')
            data = np.loadtxt(stream,ndmin=2)
        require(data.shape[0]>2 and data.shape[1]==len(columns)+1 and np.all(np.isfinite(data)),f'Invalid {name}')
        return data
    values = read('waveform.dat',[f'v({node.lower()})' for node in OBSERVE.values()])
    currents = read('currents.dat',list(MOS_CURRENTS))
    require(abs(values[0,0])<1e-20 and abs(values[-1,0]*1e9-(STOP-START))<1e-5 and
            np.all(np.diff(values[:,0])>0) and np.array_equal(values[:,0],currents[:,0]), 'Incomplete waveform or current')
    values[:,0] += START*1e-9
    names = [*OBSERVE,'sampler_bl_id','sampler_blb_id','tail_id']
    return Trace(np.column_stack((values,currents[:,1:])).tolist(),{n:i for i,n in enumerate(names,1)})


def sample(trace, signal, times):
    return np.interp(times,trace.times,[row[trace.cols[signal]] for row in trace.rows])


def grid(start,end,*traces):
    times = np.array([start,end])
    for trace in traces:
        require(trace.times[0]<=start<end<=trace.times[-1]+1e-9,'Analysis interval outside waveform')
        points = np.asarray(trace.times)
        times=np.union1d(times,points[(points>start)&(points<end)])
    return times


def outside(times, values, limit):
    """Return all over-limit spans for the linear interpolant of a signed quantity."""
    spans = []
    for a,b,x,y in zip(times[:-1],times[1:],values[:-1],values[1:],strict=True):
        cuts=[a,b]
        for bound in (-limit,limit):
            if min(x,y)<bound<max(x,y):
                cuts.append(a+(b-a)*(bound-x)/(y-x))
        cuts.sort()
        for l,r in zip(cuts,cuts[1:]):
            mid=(l+r)/2
            if abs(x+(y-x)*(mid-a)/(b-a))>limit:
                if spans and abs(spans[-1][1]-l)<1e-10:
                    spans[-1][1]=float(r)
                else:
                    spans.append([float(l),float(r)])
    return spans


def tail_report(origin,observed,bounds,threshold,current_threshold,old,new):
    t = grid(*bounds,origin,observed)
    delta = sample(observed,'sense_tail',t)-sample(origin,'sense_tail',t)
    peak = int(np.argmax(abs(delta)))
    excursion = outside(t,delta,threshold)
    conduction = []
    current = sample(observed,'tail_id',t)
    for start,end in outside(t,current,current_threshold):
        selected = np.r_[start,t[(t>start)&(t<end)],end]
        d = np.interp(selected,t,delta)
        j = int(np.argmax(abs(d)))
        conduction.append(dict(start_ns=start,end_ns=end,peak_abs_current_a=float(max(abs(np.interp(selected,t,current)))),
            peak_delta_v=float(d[j]),peak_delta_ns=float(selected[j])))
    fall20 = scalar(new['clock']['sclk_tail']['fall_ns']['20'])
    marker = {name:float(np.interp(event,t,delta)) for name,event in
              [('conditioning',bounds[0]),('tail20',new['activation']['at_ns']),
               ('tail50',new['tail50']['at_ns'] if new['tail50'] else None),('fall20',fall20),
               ('fall20_plus_1ns',fall20+1 if fall20 else None),('next_precharge_or_end',bounds[1])]
              if event is not None and bounds[0]<=event<=bounds[1]}
    return dict(bounds_ns=bounds,threshold_v=threshold,peak_delta_v=float(delta[peak]),peak_delta_ns=float(t[peak]),
        markers_delta_v=marker, markers_relative=tail_conditioning(old,new,threshold),
        outside_envelope_ns=excursion,total_outside_ns=sum(b-a for a,b in excursion),tail_conduction=conduction,
        envelope_compatible=not excursion and float(max(abs(delta)))<=threshold)


def timing_compatible(old,new,limit):
    a,b = (item['latch_polarity_crossings_ns']['fall'] for item in (old,new))
    return bool(a and b and abs(a[0]-b[0])<=limit and comparable(old,new,limit))


def control_verdict(events):
    if len(events)!=2:
        return 'INCONCLUSIVE'
    if any(e['isolated']['decision']=='CORRECT' for e in events):
        return 'NOT_REPRODUCED'
    passed=all(e['reference']['decision']==e['isolated']['decision']=='WRONG' and e['input']['eligible'] and
               e['clock_valid'] and e['conditioning_valid'] and e['tail']['envelope_compatible'] and
               e['tail']['tail_conduction'] and e['decision_timing_compatible'] for e in events)
    return 'VALIDATED' if passed else 'INCONCLUSIVE'


def rail_control_comparison(base,trial,bounds,criteria):
    t=grid(*bounds,base,trial)
    signals=('bl_at_cell','blb_at_cell','vdd','precharge','sclk_root')
    errors={signal:float(max(abs(sample(base,signal,t)-sample(trial,signal,t)))) for signal in signals}
    return dict(max_error_v=errors,compatible=max(errors.values())<=criteria['common_mode_error_v'])


def analyze(root,stage):
    receipt = read_receipt(root,stage)
    manifest_path = root/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    report = dict(verdict='INCONCLUSIVE',stage=stage,result_sha256=sha256(root/stage/'result.json'),
                  manifest_sha256=sha256(manifest_path),electrical_qualification='NOT_CHARACTERIZED')
    if stage=='control':
        report.update(contrast_authorized=False,contrast_status='NOT_RUN')
    if receipt['status']=='COMPLETED':
        if stage=='control':
            _,_,base = load(REFERENCE,True)
            base.cols['vdd'] = 10
        else:
            gate = validate_authorization(root)
            attempt = json.loads((root/stage/'attempt.json').read_text())
            pinned(gate,attempt['control_gate_sha256'])
            base = read_wave(root/'control')
        trial = read_wave(root/stage)
        criteria = manifest['criteria']
        events = []
        for window,bounds in zip(criteria['cases'],criteria['tail_envelope_windows_ns'],strict=True):
            a,b = assess_event(base,window),assess_event(trial,window)
            fidelity = dict(criteria['contrast_fidelity'])
            if stage=='control':
                fidelity.update(displacement_ps=0,each_rise_ps=EDGE_PS,unchanged_fall_ps=EDGE_PS)
            clock = {g:interpret_gate(a['clock'][g],b['clock'][g],fidelity) for g in GATES}
            tail = tail_report(base,trial,bounds,criteria['latch_conditioning_error_v'],
                               criteria['tail_channel_conduction_marker_a'],a,b)
            inputs = input_evidence(base,trial,window,criteria)
            if stage=='contrast':
                # Precharge, artificial aggressors and BL ports are exogenous and unchanged.
                # The sense-terminal differential may respond to the delayed samplers.
                stimulus = rail_control_comparison(base,trial,bounds,criteria)
                stimulus['sample_count'] = len(trial.rows)
            else:
                stimulus = None
            events.append(dict(window=window,reference=a,isolated=b,clock=clock,
                clock_valid=all(c['fidelity_verified'] for c in clock.values()), input=inputs,
                conditioning_valid=conditioning_valid(a,b,criteria['latch_conditioning_error_v']),
                tail=tail,decision_timing_compatible=timing_compatible(a,b,window['settle_tolerance_ns']),
                external_stimulus=stimulus))
        report['comparisons'] = events
        if stage=='control':
            report['verdict'] = control_verdict(events)
            report['contrast_authorized'] = report['verdict']=='VALIDATED'
        elif all(e['clock_valid'] and e['conditioning_valid'] and e['external_stimulus']['compatible']
                 and e['tail']['markers_relative']['compatible'] for e in events):
            decisions={e['isolated']['decision'] for e in events}
            report['verdict']={'CORRECT':'CORROBORATED','WRONG':'NOT_CORROBORATED'}.get(next(iter(decisions)),
                                                                                      'INCONCLUSIVE') if len(decisions)==1 else 'INCONCLUSIVE'
    else:
        report['reason']='The authorized reduced transient did not complete'
    write_json(root/f'{stage}_gate.json',report)
    print(stage,report['verdict'],flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','control','contrast','analyze-control','analyze-contrast'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=args.output.resolve()
    if args.action=='prepare':
        prepare(root)
    elif args.action.startswith('analyze-'):
        analyze(root,args.action.removeprefix('analyze-'))
    else:
        return run(root,args.action)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
