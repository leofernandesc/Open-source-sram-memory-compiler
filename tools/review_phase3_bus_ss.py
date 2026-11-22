#!/usr/bin/env python3
"""Review port drive, release and ownership from the sealed SS waveforms."""

import argparse
from bisect import bisect_left, bisect_right
import json
from pathlib import Path

from measure_phase3_access_disable import require
from phase3_rc_extraction import sha256
from phase3_rc_probe_report import read_waveform
from phase3_rc_read_path import HIGH, LOW, OUTPUT_ENABLES
from phase3_rc_turnaround import EXTRA as CONTROL_VECTORS, SCHEDULES
from run_phase3_eco_pex import new_directory, pinned, write_csv
from run_phase3_integrated_ss import BUILD, EXTRA, LIMIT_A, PEX_SHA, checked_preparation


VDD, PROBE_OHM = 1.8, 1000.
# Require a complete stimulus-slew interval supported by at least three raw
# samples. This is an observation floor, not a macro timing specification.
WITNESS_NS, STRESS_WITNESS_NS = .05, .10
CONTROL_ON, CONTROL_OFF = 1., .8


def ge(col, value):
    return col, 1., -value


def le(col, value):
    return col, -1., value


class Trace:
    def __init__(self, rows, columns):
        self.times = [row[0]*1e9 for row in rows]
        self.rows, self.cols = rows, columns

    def value(self, when, col):
        i = bisect_left(self.times, when)
        require(self.times[0] <= when <= self.times[-1], 'Observation outside waveform')
        if self.times[i] == when:
            return self.rows[i][col]
        a, b = self.times[i-1:i+1]
        u, v = self.rows[i-1][col], self.rows[i][col]
        return u + (v-u)*(when-a)/(b-a)

    def points(self, start, end, spec):
        require(self.times[0] <= start < end <= self.times[-1], 'Incomplete observation window')
        lo, hi = bisect_right(self.times,start), bisect_left(self.times,end)
        result = [(start, tuple(sign*self.value(start,col)+bias for col,sign,bias in spec))]
        result.extend((self.times[i],tuple(sign*self.rows[i][col]+bias for col,sign,bias in spec))
                      for i in range(lo,hi))
        result.append((end,tuple(sign*self.value(end,col)+bias for col,sign,bias in spec)))
        return result

    def edge(self, name, start, end, value, rising):
        col = self.cols[name]
        spec = [ge(col,value)] if rising else [le(col,value)]
        points = self.points(start,end,spec)
        edges = [a+(b-a)*(-u)/(v-u) for (a,(u,)),(b,(v,)) in zip(points,points[1:]) if u<0<=v]
        require(len(edges)==1, f'Expected one crossing of {name} through {value:g} V at {start:g} ns')
        return edges[0]

    def regions(self, start, end, spec):
        """Intersect linear inequalities on every original sample segment."""
        points = self.points(start,end,spec)
        regions = []
        for (a,left),(b,right) in zip(points,points[1:]):
            lo,hi = a,b
            for x,y in zip(left,right):
                if x < 0 and y < 0:
                    lo,hi = b,a
                    break
                if x < 0 <= y:
                    lo = max(lo, a+(b-a)*(-x)/(y-x))
                if y < 0 <= x:
                    hi = min(hi, a+(b-a)*x/(x-y))
            if lo > hi:
                continue
            if regions and regions[-1][1] == lo:
                regions[-1] = (regions[-1][0], hi)
            else:
                regions.append((lo,hi))
        return regions

    def signal_window(self, start, end, spec, *, suffix=False, floor=WITNESS_NS):
        for a,b in reversed(self.regions(start,end,spec)):
            if suffix and b != end:
                return None
            lo, hi = bisect_left(self.times,a), bisect_right(self.times,b)
            if hi-lo >= 3 and b-self.times[lo] >= floor:
                return dict(from_ns=a, through_ns=b, first_actual_ns=self.times[lo],
                            actual_samples=hi-lo, conservative_ps=(b-self.times[lo])*1000,
                            entry_bracket_ns=[self.times[max(0,lo-1)],self.times[lo]])
        return None

    def through(self, start, end, spec):
        return all(min(margins)>=0 for _,margins in self.points(start,end,spec))


def currents(cols, bit, control):
    names = ('vh','vm','vw') if control else ('v_sense_host','v_dut','v_sense_weak')
    return tuple(cols[f'i({name}{bit})'] for name in names)


def bounded_current(col):
    return [ge(col,-LIMIT_A),le(col,LIMIT_A)]


def inspect_probe(trace, bit, polarity, start, change, end, drive_required):
    cols = trace.cols
    _, macro, weak = currents(cols,bit,False)
    te = cols[OUTPUT_ENABLES[bit]]
    weak_gate,strong = (cols[f'v({name})'] for name in ('HOST_WEAK_EN','HOST_EN'))
    pad = bit+2
    rail, sign = (VDD,1.) if polarity else (0.,-1.)
    probe_alone = [ge(weak_gate,CONTROL_OFF),le(strong,CONTROL_OFF)]
    enabled = [le(te,LOW), *probe_alone]
    pad_shift = (pad,-sign,sign*rail-PROBE_OHM*LIMIT_A)
    drive_spec = [*enabled, (weak,sign,-LIMIT_A),(macro,-sign,-LIMIT_A),pad_shift]
    released_spec = [*probe_alone,ge(te,HIGH), *bounded_current(weak),*bounded_current(macro),
                     ge(pad,HIGH) if polarity else le(pad,LOW)]
    drive = trace.signal_window(start,change,drive_spec,suffix=True) if drive_required else None
    strict = (trace.signal_window(start,change,drive_spec,suffix=True,floor=STRESS_WITNESS_NS)
              if drive_required else None)
    logic = trace.signal_window(start,change,enabled,suffix=True) if drive_required else None
    release = trace.signal_window(change,end,released_spec,suffix=True)
    drive_during_release = trace.regions(change,end,drive_spec) if drive else []
    def values_at(when):
        return dict(pad_v=trace.value(when,pad), te_b_v=trace.value(when,te),
                    weak_ua=trace.value(when,weak)*1e6, dut_ua=trace.value(when,macro)*1e6)
    # Secondary record distinguishes an indeterminate witness from a genuine
    # overlap. No verdict is derived from the old single instant.
    old = change-.1
    return dict(bit=bit, probe_word_bit=polarity, at_disable_request=values_at(change),
                old_witness_ns=old, old_witness=values_at(old) if drive_required else None,
                first_drive=values_at(drive['first_actual_ns']) if drive else None,
                first_release=values_at(release['first_actual_ns']) if release else None,
                drive_expected=drive_required, conduction=drive, conduction_100ps=strict,
                drive_through_disable_ns=(drive_during_release[0][1] if drive_during_release
                                          and drive_during_release[0][0]==change else None),
                internal_enable=logic, release=release)


def probe_transition(trace, word, start, change, end, drive_required=True):
    pins = [inspect_probe(trace,b,(word>>b)&1,start,change,end,drive_required) for b in range(8)]
    # The first raw observation in the final suffix gives a conservative
    # upper bound and avoids treating interpolation as physical precision.
    released = [pin['release']['first_actual_ns'] for pin in pins if pin['release']]
    return dict(change_ns=change, end_ns=end, bits=pins,
                drive_verified=all(pin['conduction'] for pin in pins) if drive_required else None,
                release_verified=len(released)==8,
                all_released_by_ns=max(released) if len(released)==8 else None)


def strong_time(trace, start, end, rising):
    return trace.edge('v(HOST_EN)',start,end,CONTROL_ON if rising else CONTROL_OFF,rising)


def strong_closure(trace, ramp_start, control=False):
    commanded = strong_time(trace,ramp_start,ramp_start+.1,True)
    cols = [currents(trace.cols,b,control)[0] for b in range(8)]
    gate = trace.cols['v(HOST_EN)']
    lo, hi = bisect_left(trace.times,ramp_start), bisect_right(trace.times,ramp_start+WITNESS_NS)
    for index in range(lo,hi):
        if trace.rows[index][gate]>=CONTROL_OFF and any(abs(trace.rows[index][c])>LIMIT_A for c in cols):
            return dict(command_crossing_ns=commanded, time_ns=trace.times[index],
                        closure_bracket_ns=trace.times[index-1:index+1], mode='native_host_current')
    j = bisect_left(trace.times,commanded)
    return dict(command_crossing_ns=commanded,time_ns=commanded,
                closure_bracket_ns=trace.times[j-1:j+1],mode='switch_control_without_resolved_current')


def inspect_charge(trace, bit, start, end, event, payload, host, macro):
    """Check whether measured branch current is consistent with a pad charge event."""
    pad = bit+2
    sign = 1. if (payload >> bit) & 1 else -1.
    rail = [ge(pad,HIGH)] if sign > 0 else [le(pad,LOW)]
    quiet = [*bounded_current(host), *bounded_current(macro)]
    # A payload source can charge the port from the beginning of its PWL ramp.
    # At switch closure, use the last pre-closure native pad sample as baseline.
    prior = trace.times[bisect_left(trace.times,event)-1]
    final = trace.signal_window(event,end,[*rail,*quiet],suffix=True)
    if not final or (event>start and not trace.through(start,event,quiet)):
        return None
    edges = (trace.points(event,final['first_actual_ns'],[(macro,sign,0.),(host,sign,0.)])
             if event < final['first_actual_ns'] else [])
    active = [(t,im,ih) for t,(im,ih) in edges if abs(im)>LIMIT_A and t>=start]
    if active and (active[0][0]-event > WITNESS_NS
                   or (trace.value(final['first_actual_ns'],pad)-trace.value(prior,pad))*sign < HIGH-LOW
                   or any(im>0 or ih<=0 for _,im,ih in active)
                   or (event<active[-1][0] and trace.signal_window(event,active[-1][0],[*rail,*quiet]))):
        return None
    return dict(programmed_event_ns=event, pad_before_v=trace.value(prior,pad),
                pad_settled_v=trace.value(final['first_actual_ns'],pad),
                last_large_dut_sample_ns=active[-1][0] if active else None,
                settled=final)


def inspect_strong(trace, start, end, control=False, payload_event=None, payload=None):
    """Measure strong host opposition with current, gate and switch state."""
    cols = trace.cols
    comparisons = []
    for bit,label in enumerate(OUTPUT_ENABLES):
        host, macro, _ = currents(cols,bit,control)
        te = cols[label]
        conducting = le(te,HIGH)
        base = [ge(cols['v(HOST_EN)'],CONTROL_OFF),conducting]
        opposition = (trace.signal_window(start,end,[*base,ge(host,LIMIT_A),le(macro,-LIMIT_A)])
                      or trace.signal_window(start,end,[*base,le(host,-LIMIT_A),ge(macro,LIMIT_A)]))
        disabled = trace.through(start,end,[ge(te,HIGH)])
        strong_on = trace.through(start,end,[ge(cols['v(HOST_EN)'],CONTROL_OFF)])
        charge = inspect_charge(trace,bit,start,end,payload_event,payload,host,macro) if (
            disabled and payload_event is not None) else None
        quiet = trace.signal_window(start,end,[*bounded_current(host),*bounded_current(macro)],suffix=True)
        off_gate_opposition = (
            trace.signal_window(start,end,[ge(host,LIMIT_A),le(macro,-LIMIT_A)])
            or trace.signal_window(start,end,[le(host,-LIMIT_A),ge(macro,LIMIT_A)])
        ) if disabled and not charge else None
        comparisons.append(dict(bit=bit, sustained_opposition=opposition, disabled_gate=disabled,
                                strong_host_on=strong_on, opposition_with_gate_off=off_gate_opposition,
                                charge_response=charge, quiet_suffix=quiet))
    overlap = any(p['sustained_opposition'] for p in comparisons)
    weak_off = trace.through(start,end,[le(cols['v(HOST_WEAK_EN)'],CONTROL_OFF)])
    isolated = weak_off and all(p['disabled_gate'] and p['strong_host_on'] and p['quiet_suffix']
                   and not p['opposition_with_gate_off'] and (payload_event is None or p['charge_response'])
                   for p in comparisons)
    return dict(overlap=overlap, isolated=isolated, weak_host_off=weak_off,
                start_ns=start, end_ns=end, bits=comparisons)


def isolated_gap(trace, start, end):
    # The two SPICE switch transitions are discontinuities. Interpolating
    # their branch current across closure can pull the charging peak into
    # the gap. Check the switch-open native samples plus TE_B independently.
    lo, hi = bisect_right(trace.times,start), bisect_left(trace.times,end)
    if hi-lo < 3 or trace.times[hi-1]-trace.times[lo] < WITNESS_NS:
        return None
    checks = [term for b in range(8) for col in currents(trace.cols,b,False) for term in bounded_current(col)]
    gates = [ge(trace.cols[label],HIGH) for label in OUTPUT_ENABLES]
    if not (trace.through(trace.times[lo],trace.times[hi-1],checks) and trace.through(start,end,gates)):
        return None
    return dict(first_actual_ns=trace.times[lo], last_actual_ns=trace.times[hi-1],
                samples=hi-lo, unobserved_edges_ps=[1000*(trace.times[lo]-start),1000*(end-trace.times[hi-1])])


def review_cycles(trace, records, historical):
    result = []
    for i,rec in enumerate(records):
        op, before = rec['operation'], rec['previous_operation']
        previous = records[i-1] if i else None
        following = records[i+1] if i+1 < len(records) else None
        old = historical['cycles'][i]
        control, rise, fall = rec['control_start_ns'],rec['rise_ns'],rec['fall_ns']
        event = dict(cycle=i, operation=op, historical_ownership=old['ownership_status'], overlap=False,
                     conduction_verified=None, release_verified=None)
        if op == 'read':
            cal = rec['calibration']
            start, mask, restore = (cal[key] for key in ('weak_on_ns','mask_ns','restore_ns'))
            probe = probe_transition(trace,rec['expected']^255,start+WITNESS_NS,mask,restore)
            end_read = cal['weak_on_ns']
            host_off = trace.through(control,end_read,[le(trace.cols['v(HOST_EN)'],CONTROL_OFF)])
            if before == 'write':
                t = strong_time(trace,previous['host_off_ns'],control,False)
                event['strong_host_off_ns'] = t
                host_off &= all(trace.through(control,end_read,bounded_current(currents(trace.cols,b,False)[0]))
                                for b in range(8))
            event.update(kind='read_CSb_mask',conduction_verified=probe['drive_verified'],
                         release_verified=probe['release_verified'], probe=probe, host_off=host_off)
            enough = probe['drive_verified'] and probe['release_verified'] and host_off
        elif op == 'idle':
            resumed = before == 'read'
            start = previous['calibration']['restore_ns'] if resumed else 3.55
            change = control if resumed else rise
            word = (previous['expected']^255) if resumed else 0xAA
            end = (trace.edge('v(HOST_WEAK_EN)',previous['weak_off_ns'],previous['weak_off_ns']+.1,CONTROL_OFF,False)
                   if resumed else fall)
            probe = probe_transition(trace,word,start,change,end,resumed)
            event.update(kind='read_to_idle' if resumed else 'idle',probe=probe,
                         conduction_verified=probe['drive_verified'],release_verified=probe['release_verified'])
            if resumed:
                event['CSb_restore50_ns'] = trace.edge('v(CSb)',start,start+.1,.9,False)
                event['disable_control50_ns'] = trace.edge('v(CSb)',control,control+.1,.9,True)
            enough = (probe['release_verified'] and (not resumed or probe['drive_verified'])
                      and all(pin['release']['from_ns'] <= rise for pin in probe['bits']))
        else:
            on_start = rec['host_enable_ns']
            if before == 'write':
                # Consecutive writes reuse the same owner through payload changes.
                on = control
            else:
                closure = strong_closure(trace,on_start)
                on = closure['time_ns']
                event['host_closure'] = closure
            payload_event = rec['host_payload_ns'] if before == 'write' else on
            if 'host_off_ns' in rec:
                opening = strong_time(trace,rec['host_off_ns'],rec['host_off_ns']+.1,False)
                j = bisect_left(trace.times,opening)
                event['host_opening_bracket_ns'] = trace.times[j-1:j+1]
                until = trace.times[j-1]
            else:
                until = following['control_start_ns']
            strong = inspect_strong(trace,on,until,payload_event=payload_event,payload=rec['expected'])
            event.update(kind='write',overlap=strong['overlap'],host_on_ns=on,
                         strong_check=strong, release_verified=strong['isolated'])
            enough = strong['isolated']
            if before == 'idle':
                # Initial idle has a separate weak witness through 46 ns.
                probe_off = trace.edge('v(HOST_WEAK_EN)',45.99,on,CONTROL_OFF,False)
                pre = probe_transition(trace,0xAA,previous['fall_ns'],previous['fall_ns'],probe_off,False)
                bridged = pre['release_verified'] and isolated_gap(trace,probe_off,on)
                event.update(initial_idle_probe=pre,initial_idle_bridged=bridged,release_verified=bool(bridged))
                enough = enough and bool(bridged)
            if before == 'read':
                restore = previous['calibration']['restore_ns']
                probe_end = trace.edge('v(HOST_WEAK_EN)',previous['weak_off_ns'],on,CONTROL_OFF,False)
                probe = probe_transition(trace,previous['expected']^255,restore,control,probe_end)
                bridge = isolated_gap(trace,probe_end,on)
                event.update(kind='read_to_write',probe=probe,conductance_gap_isolated=bridge,
                    conduction_verified=probe['drive_verified'],release_verified=probe['release_verified'] and bool(bridge),
                    CSb_restore50_ns=trace.edge('v(CSb)',restore,restore+.1,.9,False),
                    disable_control50_ns={name:trace.edge(f'v({name})',control,control+.1,.9,up)
                                          for name,up in (('OEb',True),('WEb',False))},
                    separation_ns=on-probe['all_released_by_ns'] if probe['release_verified'] else None,
                    minimum_sample_separation_ns=(closure['closure_bracket_ns'][0]-probe['all_released_by_ns']
                                                  if probe['release_verified'] else None))
                enough = enough and probe['drive_verified'] and probe['release_verified'] and bool(bridge)
        event['verdict'] = 'FAIL' if event['overlap'] else 'PASS' if enough else 'INCONCLUSIVO'
        result.append(event)
    return result


def waveform(run, receipt, vector_set):
    pins = json.loads((run/'probes.json').read_text())
    raw_sha = receipt['waveform_sha256'] if 'waveform_sha256' in receipt else receipt['artifacts']['waveform.dat']
    raw = pinned(run/'waveform.dat',raw_sha)
    stop = 370 if vector_set == EXTRA else SCHEDULES['v2'].end_ns
    rows, cols = read_waveform(raw,sorted(set(pins.values())),vector_set,minimum_end=stop*1e-9-1e-15)
    cols.update({key:cols[val] for key,val in pins.items()})
    return Trace(rows,cols)


def review_controls(gds_sha):
    results = []
    for guard in (300,1500):
        run = BUILD/f'turnaround_ref_ss_v2_{guard}'
        p = run/'manifest.json'
        receipt = json.loads(p.read_text())
        require(receipt['campaign']=='v2' and receipt['host_guard_ps']==guard and receipt['corner']=='ss'
                and receipt['simulator_status']=='PASS' and receipt['gds_sha256']==gds_sha
                and receipt['netlist_sha256']==PEX_SHA, 'Unexpected historical control')
        for name in ('probes.json','bench.spice'):
            pinned(run/name,receipt['artifacts'][name])
        trace = waveform(run,receipt,CONTROL_VECTORS)
        require(len(trace.rows)==receipt['samples'], 'Historical control sample count differs')
        schedule = SCHEDULES['v2']
        t = schedule.handoff_ns + guard/1000
        closure = strong_closure(trace,t,True)
        on = closure['time_ns']
        report = inspect_strong(trace,on,schedule.write_ns-1,control=True,payload_event=on,payload=0x55)
        results.append(dict(guard_ps=guard, source_sha256=sha256(p), waveform_sha256=receipt['artifacts']['waveform.dat'],
                            verdict='FAIL' if report['overlap'] else 'PASS' if report['isolated'] else 'INCONCLUSIVO',
                            strong_on_ns=on, host_closure=closure, **report))
    return results


def detail_rows(cycles):
    for event in cycles:
        if event['kind'] not in ('read_to_write','read_to_idle'):
            continue
        for pin in event['probe']['bits']:
            enable, drive, release = (pin[k] or {} for k in ('internal_enable','conduction','release'))
            row = dict(cycle=event['cycle'],bit=pin['bit'],retained_bit=1-pin['probe_word_bit'],
                       cs_restore50_ns=event['CSb_restore50_ns'],te_enable_first_sample_ns=enable.get('first_actual_ns'),
                       drive_first_sample_ns=drive.get('first_actual_ns'),
                       drive_before_request_ps=drive.get('conservative_ps'),
                       disable_request_ns=event['probe']['change_ns'],
                       drive_through_disable_ns=pin['drive_through_disable_ns'],
                       release_first_sample_ns=release.get('first_actual_ns'),release_through_ns=release.get('through_ns'),
                       strong_on_ns=event.get('host_on_ns'))
            for key in ('old_witness','first_drive','at_disable_request','first_release'):
                values = pin[key] or {}
                row.update((f'{key}_{column}',values.get(column))
                           for column in ('pad_v','te_b_v','weak_ua','dut_ua'))
            yield row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    prep = checked_preparation(args.run)
    require(prep['guard_ns']==1.5, 'Integrated guard differs from the fixed fixture')
    sim_file, history_file = (args.run/name for name in ('simulation.json','validation.json'))
    sim, history = (json.loads(path.read_text()) for path in (sim_file,history_file))
    require(sim['simulator_status']=='PASS' and sha256(args.run/'preparation.json')==sim['preparation_sha256']
            and sim['waveform_sha256']==history['source_waveform_sha256'], 'Unexpected electrical evidence')
    trace = waveform(args.run,sim,EXTRA)
    require(len(trace.rows)==history['samples'], 'Integrated sample count differs')
    records = json.loads((args.run/'fixture.json').read_text())['cycles']
    cycles = review_cycles(trace,records,history)
    controls = review_controls(prep['candidate']['gds_sha256'])
    require([control['verdict'] for control in controls]==['FAIL','PASS'], 'Unable to distinguish the stress control')
    verdicts = [x['verdict'] for x in cycles]+[x['operation_status'] for x in history['cycles']]
    verdict = 'FAIL' if 'FAIL' in verdicts else 'INCONCLUSIVO' if 'INCONCLUSIVO' in verdicts else 'PASS'
    output = new_directory(args.output)
    table = [{k:v for k,v in record.items() if k in
              ('cycle','operation','kind','historical_ownership','conduction_verified','release_verified','overlap','verdict')}
             for record in cycles]
    write_csv(output/'cycles.csv',table,list(table[0]))
    detail = list(detail_rows(cycles))
    write_csv(output/'direction_changes_by_bit.csv',detail,list(detail[0]))
    result = dict(schema_version=1, mode='offline_existing_waveforms', new_spice_runs=0,
                  historical_verdict=history['functional_status'], revised_functional_verdict=verdict,
                  electrical_qualification='NOT_CHARACTERIZED', historical_read_window=history['historical_window'],
                  current_floor_a=LIMIT_A, minimum_supported_witness_ps=50, cycles=cycles, controls=controls,
                  candidate=prep['candidate'], conditions=prep['conditions'], pex_sha256=prep['pex_sha256'],
                  historical_operations=[dict(cycle=x['cycle'],status=x['operation_status']) for x in history['cycles']],
                  source_sha256={str(p):sha256(p) for p in (args.run/'preparation.json',sim_file,history_file,Path(__file__))},
                  source_waveform_sha256=sim['waveform_sha256'])
    (output/'review.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(verdict)
    return int(verdict!='PASS')


if __name__ == '__main__':
    raise SystemExit(main())
