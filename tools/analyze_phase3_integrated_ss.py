#!/usr/bin/env python3
"""Separate functional, ownership, and historical timing checks for the integrated run."""

import argparse
import json
from pathlib import Path

from measure_phase3_access_disable import edge, measure_word, require, survives
from phase3_rc_characterization import at, crossing, valid_suffix_start
from phase3_rc_extraction import ROOT, sha256
from phase3_rc_probe_report import read_waveform
from phase3_rc_read_path import HIGH, LOW, LOCAL_CLOCKS, OUTPUT_ENABLES, WORDLINES, correct
from phase3_rc_turnaround import current_below
from run_phase3_eco_pex import pinned, protocol_checks, write_csv
from run_phase3_integrated_ss import ADDR, EXTRA, LIMIT_A, MODE, STOP_NS, checked_preparation, ns


def stable_word(rows, start, end, expected):
    entry = [valid_suffix_start(rows, bit+2, start, end, (expected >> bit) & 1) for bit in range(8)]
    return max(entry) if all(t is not None for t in entry) else None


def logic_word(rows, when, columns):
    levels = [at(rows, when, col) for col in columns]
    chars = ''.join('1' if v >= HIGH else '0' if v <= LOW else 'X' for v in reversed(levels))
    return f'0x{int(chars,2):0{(len(chars)+3)//4}X}' if 'X' not in chars else chars


def status(flag):
    return 'PASS' if flag else 'FAIL'


def interval(rows, start, end):
    require(start < end, 'Empty observation interval')
    return [row for row in rows if start < row[0] < end]


def follow_disable(rows, columns, start, end, probe_word, before_active):
    """Find joint pad release until a programmed endpoint under an opposing probe."""
    require(bool(interval(rows, start, end)), 'Missing release samples')
    per_bit = []
    where = ns(start*1e9-.1)
    for bit, label in enumerate(OUTPUT_ENABLES):
        weak = columns[f'i(v_sense_weak{bit})']
        macro = columns[f'i(v_dut{bit})']
        precondition = (not before_active or (at(rows, where, columns[label]) <= LOW
                        and abs(at(rows, where, weak)) > LIMIT_A
                        and at(rows, where, weak)*at(rows, where, macro) < 0))
        pad = valid_suffix_start(rows, bit+2, start, end, (probe_word >> bit) & 1)
        small_probe = current_below(rows, weak, start, end, LIMIT_A)
        small_dut = current_below(rows, macro, start, end, LIMIT_A)
        gate = valid_suffix_start(rows, columns[label], start, end, 1)
        release = (max(pad,small_probe,small_dut,gate) if precondition
                   and all(x is not None for x in (pad,small_probe,small_dut,gate)) else None)
        # A single point at the endpoint is not evidence of a sustained release.
        if release is not None and (release >= end or not interval(rows, release, end)):
            release = None
        per_bit.append(dict(bit=bit, initial_driver_proven=precondition,
                            release_ns=None if release is None else release*1e9,
                            pad_agrees=pad is not None, weak_current_low=small_probe is not None,
                            macro_current_low=small_dut is not None, driver_disabled=gate is not None))
    instants = [item['release_ns'] for item in per_bit]
    return dict(last_release_ns=max(instants) if all(t is not None for t in instants) else None, bits=per_bit)


def high_phase(rows, cols, rec):
    start, finish = ns(rec['rise_ns']), ns(rec['fall_ns'])
    fall = edge(rows, 1, finish, finish+ns(.1), 'fall')
    rise = edge(rows, 1, start, start+ns(.1), 'rise')
    samples = interval(rows,rise,fall)
    peaks = [max(row[cols[wl]] for row in samples) for wl in WORDLINES]
    active = [i for i,value in enumerate(peaks) if value >= HIGH]
    idle = rec['operation'] == 'idle'
    # At the active row, address and the captured operation must already have
    # settled and remain valid throughout that access.
    wl = cols[WORDLINES[rec['row']]]
    matches = crossing(rows, wl, rise, fall, HIGH, 'rise') if not idle else []
    anchor = matches[0] if len(matches) == 1 else fall-ns(.25)
    wl_ok = all(value <= LOW for value in peaks) if idle else (
        active == [rec['row']] and len(matches) == 1 and all(value <= LOW for i,value in enumerate(peaks) if i != rec['row']))
    mode_ok = all(survives(rows,cols[node],anchor,fall,int(rec['operation']==op))
                  for node,op in zip(MODE,('write','read')))
    address_ok = idle or all(survives(rows,cols[node],anchor,fall,(rec['row']>>bit)&1)
                             for bit,node in enumerate(ADDR))
    return dict(rise=rise, fall=fall, observed_address=logic_word(rows, anchor, [cols[node] for node in ADDR]),
                active_wordlines=active, wl_ok=wl_ok, mode_ok=mode_ok, address_ok=address_ok,
                access_event_ns=anchor*1e9)


def ownership(rows, cols, rec, prev, phase):
    op = rec['operation']
    control = ns(rec['control_start_ns'])
    if op == 'read':
        cal = rec['calibration']
        mask, end = ns(cal['mask_ns']), ns(cal['restore_ns']-.05)
        proof = follow_disable(rows, cols, mask, end, rec['expected'] ^ 255, True)
        host_off = survives(rows,cols['v(HOST_EN)'],control,ns(cal['weak_on_ns']),0)
        proof.update(kind='read_and_CSb_mask', strong_host_off=host_off, observation_end_ns=end*1e9,
                     status='FAIL' if not host_off else 'PASS' if proof['last_release_ns'] is not None else 'INCONCLUSIVO')
        if rec['previous_operation'] == 'write':
            clock = ns(prev['host_off_ns'])
            off_edges = crossing(rows,cols['v(HOST_EN)'],clock,control,.8,'fall')
            proof.update(host_off_ns=off_edges[0]*1e9 if len(off_edges)==1 else None)
            if len(off_edges) != 1 or any(abs(at(rows,control,cols[f'i(v_sense_host{b})'])) > LIMIT_A for b in range(8)):
                proof['status'] = 'FAIL'
        if rec['previous_operation'] == 'read':
            begin = ns(prev['weak_off_ns']+.05)
            retained = stable_word(rows, begin, phase['fall'], prev['expected'])
            proof['retained_previous_word_since_ns'] = None if retained is None else retained*1e9
            if (retained is None or retained == phase['fall'] or not interval(rows,retained,phase['fall'])) and proof['status']=='PASS':
                proof['status'] = 'INCONCLUSIVO'
        return proof
    if op == 'idle':
        begin, end = phase['rise'], phase['fall']
        probe_word = prev['expected'] ^ 255 if rec['previous_operation']=='read' else 0xAA
        from_read = rec['previous_operation']=='read'
        proof = follow_disable(rows, cols, control if from_read else begin, end, probe_word, from_read)
        isolated = proof['last_release_ns'] is not None and proof['last_release_ns'] <= begin*1e9+1e-6
        host_off = survives(rows,cols['v(HOST_EN)'],begin,end,0)
        proof.update(kind='idle_or_read_to_idle', observation_end_ns=end*1e9, strong_host_off=host_off,
                     status='FAIL' if not host_off else 'PASS' if isolated else 'INCONCLUSIVO')
        return proof

    before = ns(max(rec['host_enable_ns'],rec['host_payload_ns'])+.05)
    after = phase['fall']
    gate_off = all(survives(rows,cols[label],before,after,1) for label in OUTPUT_ENABLES)
    host_owns = survives(rows,cols['v(HOST_EN)'],before,after,1)
    proof = dict(kind='strong_host_write', status=status(gate_off and host_owns),
                 sram_disabled_during_write=gate_off, strong_host_active=host_owns)
    if rec['previous_operation'] == 'read':
        on_start = ns(rec['host_enable_ns'])
        on, = crossing(rows,cols['v(HOST_EN)'],on_start,on_start+ns(.05),1.,'rise')
        probe_end, = crossing(rows,cols['v(HOST_WEAK_EN)'],ns(prev['weak_off_ns']),on,.8,'fall')
        release = follow_disable(rows,cols,control,probe_end,prev['expected'] ^ 255,True)
        held = all(survives(rows,cols[label],probe_end,after,1) for label in OUTPUT_ENABLES)
        proven = release['last_release_ns'] is not None
        proof.update(release, kind='read_to_write', strong_on_ns=on*1e9, probe_off_ns=probe_end*1e9,
                     separation_ns=None if not proven else on*1e9-release['last_release_ns'],
                     isolation_held_through_write=held)
        proof['status'] = 'PASS' if proven and held and gate_off and host_owns else 'FAIL' if proven else 'INCONCLUSIVO'
        proof['opposition_at_host_plus_200ps_ua'] = []
        for bit in range(8):
            host = at(rows,on+ns(.2),cols[f'i(v_sense_host{bit})'])
            macro = at(rows,on+ns(.2),cols[f'i(v_dut{bit})'])
            proof['opposition_at_host_plus_200ps_ua'].append(min(abs(host),abs(macro))*1e6 if host*macro < 0 else 0.)
    return proof


def analyze(rows, cols, records):
    raw_checks = protocol_checks(rows,cols,records)
    writes = {(r['cycle'],r['bit']):r for r in raw_checks if r['kind']=='write_data_ready_before_we20'}
    cycles, windows, read_details, ownership_details = [], [], [], []
    last_read = None
    q_cols = [cols['_75_.Q' if bit==0 else f'_{87+bit}_.A'] for bit in range(8)]
    for rec in records:
        index, op, expected = rec['cycle'], rec['operation'], rec['expected']
        prev = records[index-1] if index else None
        phase = high_phase(rows,cols,rec)
        owner = ownership(rows,cols,rec,prev,phase)
        ownership_details.append(dict(cycle=index,**owner))
        result = dict(cycle=index, operation=op, expected_address=None if op=='idle' else rec['row'],
                      observed_address=None if op=='idle' else phase['observed_address'],
                      active_wordlines=' '.join(map(str,phase['active_wordlines'])),
                      expected_word=None if op=='idle' else f'0x{expected:02X}',
                      observed_word=None, operation_status='PASS', ownership_status=owner['status'],
                      historical_window=None, tACCESS_ns=None, CLKfall_to_valid_ns=None,
                      data_valid_from_ns=None, data_valid_through_ns=None, first_divergence=None)
        if not all(phase[key] for key in ('wl_ok','mode_ok','address_ok')):
            result.update(operation_status='FAIL',first_divergence='captured operation/address/wordline')
        if last_read is not None:
            q_word, since = last_read
            end = phase['fall']
            if not all(survives(rows,col,since,end,(q_word>>bit)&1) for bit,col in enumerate(q_cols)):
                result.update(operation_status='FAIL',first_divergence=result['first_divergence'] or 'previous Q retention')
        if op == 'write':
            entries = [writes[index,bit] for bit in range(8)]
            event = next((r['we20_ns'] for r in entries if r['we20_ns'] is not None),None)
            if event is not None:
                result['observed_word'] = logic_word(rows,ns(event),[cols[f'_{67+bit}_.Q'] for bit in range(8)])
            external = logic_word(rows,phase['rise'],list(range(2,10)))
            if any(r['status']!='PASS' for r in entries) or external != result['expected_word']:
                result.update(operation_status='FAIL',first_divergence=result['first_divergence'] or 'DATA/DIN before WE')
        if op == 'read':
            sample, end = ns(rec['sample_ns']), ns(rec['calibration']['weak_on_ns'])
            begin_window, end_window = sample-ns(.1), sample+ns(.1)
            win = [survives(rows,bit+2,begin_window,end_window,(expected>>bit)&1) for bit in range(8)]
            windows.extend(dict(cycle=index,bit=bit,status=status(passed)) for bit,passed in enumerate(win))
            result['historical_window'] = f'{sum(win)}/8'
            result['observed_word'] = logic_word(rows,end,list(range(2,10)))
            try:
                word = measure_word(rows,cols,rec)
            except ValueError as error:
                word = dict(word_verification='NOT_CHARACTERIZED',bits=[],analysis_error=str(error))
            read_details.append(dict(cycle=index, measurement=word))
            unavailable = [b for b in word['bits'] if not b['internal_capture_verified']]
            if unavailable or not word['bits']:
                result.update(operation_status='FAIL',first_divergence=result['first_divergence'] or
                              (f'sense/D/Q bit {unavailable[0]["bit"]}' if unavailable else word['analysis_error']))
            elif word['word_verification'] != 'VERIFIED':
                if result['operation_status']=='PASS':
                    result.update(operation_status='INCONCLUSIVO',first_divergence='no sustained valid DATA before fixture probe')
            else:
                stamp = word['stable_word_since_s']
                result.update(data_valid_from_ns=word['word_verified_from_s']*1e9, data_valid_through_ns=end*1e9,
                              tACCESS_ns=None if stamp is None else word['tACCESS_s']*1e9,
                              CLKfall_to_valid_ns=None if stamp is None else word['tREAD_VALID_s']*1e9)
                last_read = expected, word['word_verified_from_s']
        cycles.append(result)

    for written in (c for c in cycles if c['operation']=='write'):
        row = written['expected_address']
        later = next((c for c in cycles[written['cycle']+1:]
                      if c['expected_address']==row and c['operation'] in ('read','write')),None)
        confirmed = (later is not None and later['operation']=='read' and later['operation_status']=='PASS'
                     and later['observed_word']==written['expected_word'])
        written['readback_cycle'] = later['cycle'] if confirmed else None
        if not confirmed and written['operation_status']=='PASS':
            written.update(operation_status='INCONCLUSIVO',first_divergence='write readback not confirmed')
    evaluations = [c[key] for c in cycles for key in ('operation_status','ownership_status')]
    return dict(functional_status='FAIL' if 'FAIL' in evaluations else 'INCONCLUSIVO' if 'INCONCLUSIVO' in evaluations else 'PASS',
                cycles=cycles, historical_window=windows, reads=read_details, ownership=ownership_details,
                write_diagnostics=raw_checks, electrical_qualification='NOT_CHARACTERIZED',
                normative_read_deadline='NOT_SPECIFIED')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run',type=Path)
    args = p.parse_args()
    run = args.run.resolve()
    checked_preparation(run)
    sim = json.loads((run/'simulation.json').read_text())
    require(sim['preparation_sha256'] == sha256(run/'preparation.json') and sim['simulator_status']=='PASS',
            'Expected a completed sealed transiente')
    pinned(run/'ngspice.log',sim['log_sha256'])
    wave = pinned(run/'waveform.dat',sim['waveform_sha256'])
    aliases = json.loads((run/'probes.json').read_text())
    rows, cols = read_waveform(wave,sorted(set(aliases.values())),EXTRA,minimum_end=ns(STOP_NS)-1e-15)
    cols.update({name:cols[node] for name,node in aliases.items()})
    records = json.loads((run/'fixture.json').read_text())['cycles']
    evidence = analyze(rows,cols,records)
    evidence.update(samples=len(rows), source_waveform_sha256=sim['waveform_sha256'],
                    analyzer_sha256=sha256(Path(__file__)), simulator_status=sim['simulator_status'])
    with (run/'validation.json').open('x') as file:
        json.dump(evidence,file,indent=2,allow_nan=False)
        file.write('\n')
    write_csv(run/'cycles.csv',evidence['cycles'],list(dict.fromkeys(k for row in evidence['cycles'] for k in row)))
    write_csv(run/'historical_read_window.csv',evidence['historical_window'],['cycle','bit','status'])
    print(evidence['functional_status'])
    return int(evidence['functional_status'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
