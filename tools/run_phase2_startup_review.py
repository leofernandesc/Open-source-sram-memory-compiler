#!/usr/bin/env python3
"""Small nominal power-up campaign on the sealed, unchanged 1493-MOS circuit.

Each scenario uses a new ngspice process and fresh circuit state. No internal
initial condition is set. This is not minimum-startup/PVT characterization.
"""
import argparse
from collections import Counter
import csv
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import numpy as np

from run_digital_regression import atomic_text
from run_phase2_digital import ROOT, sha
from run_phase2_directed_review import observation_map
from phase2_access_checks import check as protocol_check
from phase2_resources import preflight

SCENARIOS = {
    'r1_idle0': dict(ramp_ns=1, idle_cycles=0, first_row=0, first_word=0x00),
    'r1_idle2': dict(ramp_ns=1, idle_cycles=2, first_row=1, first_word=0xFF),
    'r5_idle2': dict(ramp_ns=5, idle_cycles=2, first_row=2, first_word=0xAA),
    'r10_idle2': dict(ramp_ns=10, idle_cycles=2, first_row=3, first_word=0x55),
    'r1_idle3': dict(ramp_ns=1, idle_cycles=3, first_row=0, first_word=0xFF),
}
SOURCE = ROOT / 'reports/phase2/extracted_access_singlethread'
GDS = ROOT / 'reports/phase2/final_gds'


def validate_trace(data, vectors, stop_ns):
    if (data.ndim != 2 or data.shape[1] != len(vectors)+1 or len(data) < 100
            or not np.all(np.isfinite(data)) or not np.all(np.diff(data[:, 0]) > 0)):
        raise ValueError('Invalid/nonfinite/nonmonotonic startup trace')
    if data[0, 0] > 1e-15 or data[-1, 0] < (stop_ns-.02)*1e-9:
        raise ValueError('Incomplete startup transient')


def levels(values, expected):
    if not values.size:
        return False
    return bool(np.all((values >= 1.44) & (values <= 1.98))) if expected else bool(
        np.all((values >= -.18) & (values <= .36)))


def make_probes(state, design):
    probe = observation_map((GDS/'final_extracted.spice').read_text(),
                            (SOURCE/'binding.spice').read_text(),
                            (GDS/'final_flat.ext').read_text())
    vectors = list(state['vectors'])
    extra = {n: f'v({n})' for n in ('VDD', 'CLK', 'CSb', 'OEb', 'WEb', 'HOST_EN')}
    prefix = 'macro_core.array_and_peripherals.'
    for b in range(8):
        for n in ('BL', 'BLB'):
            extra[f'{n}{b}'] = probe(prefix+f'write_driver_{b}.{n}')
    for r in range(4):
        extra[f'N{r}'] = probe(prefix+f'row_decoder_0.N{r}')
    top = design['modules']['sram_4x8_wrapper']
    for signal, name in [('control.READ_Q', 'READ_Q'), ('control.WRITE_Q', 'WRITE_Q')]:
        bit = top['netnames'][signal]['bits'][0]
        ff = next(n for n, c in top['cells'].items()
                  if c['type'].startswith('sky130_fd_sc_hd__df') and c['connections']['Q'] == [bit])
        extra[name] = probe(ff+'.Q')
    for b, bit in enumerate(top['netnames']['read_data_q']['bits']):
        ff = next(n for n, c in top['cells'].items()
                  if c['type'].startswith('sky130_fd_sc_hd__df') and c['connections']['Q'] == [bit])
        extra[f'REG_Q{b}'] = probe(ff+'.Q')
    # Derive each storage node from the real access MOS touching BL, independently
    # of generator-internal storage names. Observation only; never reconnect it.
    cards = [l.split() for l in (SOURCE/'binding.spice').read_text().splitlines()
             if re.match(r'(?i)^x\S+\s', l)]
    for r in range(4):
        wl = state['vectors'][12+r][7:-1]  # v(xdut.<node>)
        for b in range(8):
            bl = extra[f'BL{b}'][7:-1]
            devices = [f for f in cards if f[2] == wl and bl in (f[1], f[3])]
            if len(devices) != 1:
                raise ValueError('Ambiguous storage access MOS')
            f = devices[0]
            other = f[3] if f[1] == bl else f[1]
            extra[f'CELL_{r}_{b}'] = f'v(xdut.{other})'
    if len({extra[f'CELL_{r}_{b}'] for r in range(4) for b in range(8)}) != 32:
        raise ValueError('Storage observations alias')
    for value in extra.values():
        if value not in vectors:
            vectors.append(value)
    return vectors, extra


def make_deck(config, state, vectors):
    ramp = config['ramp_ns']
    first_clock = ramp+9  # same 9-ns settled-supply wait in every scenario
    row, word = config['first_row'], config['first_word']
    cycles = [('idle', 0, 0)] * config['idle_cycles']
    cycles += [('write', row, word), ('read', row, word)]
    memory = {row: word}
    for other in range(4):
        if other != row:
            value = (0x00, 0xFF, 0xAA, 0x55)[other]
            # Preserve distinct row signatures even when the first word duplicates
            # a different row's usual pattern.
            if value == word:
                value = word ^ 0x3C
            memory[other] = value
            cycles.append(('write', other, value))
    cycles.append(('write', row, word ^ 255)); memory[row] = word ^ 255
    cycles += [('read', r, memory[r]) for r in range(4)]
    cycles += [('idle', 0, 0), ('read', row, memory[row])]
    names = ['CLK', 'CSb', 'OEb', 'WEb', 'ADDR0', 'ADDR1', 'HOST_EN', 'HOST_WEAK_EN',
             *[f'HOST{b}' for b in range(8)]]
    signals = {n: [(0., 0.)] for n in names}
    for n in ('CSb', 'OEb', 'WEb'):
        signals[n] = [(0., 0.), (float(ramp), 1.)]  # inactive controls track VDD ramp

    def event(name, t, value):
        if t < signals[name][-1][0]:
            raise ValueError('Nonmonotonic stimulus')
        signals[name].extend([(t, signals[name][-1][1]), (t+.05, float(value))])

    # Weak external host probes test release, rather than assuming a floating
    # analog DATA voltage is a digital Z. Probe starts only after full supply.
    for b in range(8):
        event(f'HOST{b}', ramp+1, (0x69 >> b) & 1)
    event('HOST_WEAK_EN', ramp+1, 1)
    for b in range(8):
        event(f'HOST{b}', ramp+3, (0x96 >> b) & 1)
    event('HOST_WEAK_EN', ramp+5, 0)
    records = []
    for i, (op, address, value) in enumerate(cycles):
        edge = first_clock+20*i
        ctl = (0, 1, 0) if op == 'write' else (0, 0, 1) if op == 'read' else (1, 1, 1)
        for n, v in zip(('CSb', 'OEb', 'WEb'), ctl):
            event(n, edge-3, v)
        for b in range(2):
            event(f'ADDR{b}', edge-3, (address >> b) & 1)
        for b in range(8):
            event(f'HOST{b}', edge-2.5, (value >> b) & 1)
        event('HOST_EN', edge-2, op == 'write'); event('HOST_EN', edge+1, 0)
        if op == 'idle':
            event('HOST_WEAK_EN', edge+1, 1)
            for b in range(8):
                event(f'HOST{b}', edge+4, (0xFF >> b) & 1)
            event('HOST_WEAK_EN', edge+8, 0)
        event('CLK', edge, 1); event('CLK', edge+10, 0)
        records.append(dict(cycle=i, operation=op, row=address, expected=value,
                            rise_ns=edge, fall_ns=edge+10, sample_ns=edge+12))
    stop = first_clock+20*len(cycles)
    old = (SOURCE/'bench.spice').read_text().splitlines()
    start = next(i for i, l in enumerate(old) if l.startswith('V_CLK '))
    lines = [l for l in old[:start] if not l.startswith('VDD_SRC ')]
    lines += [f'VDD_SRC VDD 0 PWL(0 0 {ramp}n 1.8)']
    for name, events in signals.items():
        lines.append(f'V_{name} {name} 0 PWL('+ ' '.join(f'{t:.9g}n {v*1.8:.9g}' for t, v in events)+')')
    lines.extend(l for l in old if l.startswith(('S_HOST', 'S_WEAK', 'XDUT ')))
    lines += ['.save '+' '.join(vectors), '.control', 'set num_threads=1', 'set noaskquit',
              'set wr_singlescale', 'set wr_vecnames', f'tran 10p {stop:g}n 0 10p',
              'wrdata waveform.dat '+' '.join(vectors), 'quit', '.endc', '.end']
    deck = '\n'.join(lines)+'\n'
    if re.search(r'(?mi)^\s*\.(ic|nodeset)\b', deck):
        raise ValueError('Internal initialization forbidden')
    return deck, records, stop


def analyze(data, records, vectors, extra, config, state, stop_ns):
    validate_trace(data, vectors, stop_ns)
    t = data[:, 0]*1e9
    # Reuse the existing numerical criteria only after the supply has settled.
    # Fixed 1.8-V thresholds have no digital meaning during the supply ramp.
    powered = t >= config['ramp_ns']+2
    checks, reference = protocol_check(data[powered], records, vectors,
                                       state['capture_inputs'], state['capture_clocks'])

    def col(n): return vectors.index(extra[n])+1
    def put(kind, passed, **details):
        checks.append(dict(kind=kind, status='PASS' if passed else 'FAIL', **details))
    def window(a, b): return (t >= a) & (t <= b)

    first_write = next(r for r in records if r['operation'] == 'write')
    first = first_write['rise_ns']
    startup = window(config['ramp_ns']+2, first-3.1)
    pre = window(first-.8, first-.2)
    put('supply_ready', bool(np.any(startup)) and bool(np.all(np.abs(data[startup, col('VDD')]-1.8) <= .018)))
    put('startup_no_wordline', bool(np.any(startup)) and bool(np.all(data[startup, 13:17] <= .36)))
    put('startup_no_evaluation_write_sense', bool(np.any(startup)) and bool(np.all(data[startup][:, [9, 11, 12]] <= .36)))
    for r in range(4):
        put('decoder_precharged_before_first_access', levels(data[pre, col(f'N{r}')], 1), row=r)
    for b in range(8):
        for n in ('BL', 'BLB'):
            put('bitline_precharged_before_first_access', levels(data[pre, col(f'{n}{b}')], 1), bit=b, line=n)
    for at, word in ((config['ramp_ns']+2.5, 0x69), (config['ramp_ns']+4.5, 0x96)):
        sample = int(np.searchsorted(t, at))
        for b in range(8):
            put('startup_bus_release_1kohm', abs(float(data[sample, b+1])-1.8*((word >> b) & 1)) <= .05, bit=b, time_ns=at)
    memory = {}; reads = 0; previous = None
    for r in records:
        edge = r['rise_ns']; op = r['operation']; sample = int(np.searchsorted(t, r['sample_ns']))
        high = window(edge+1, r['fall_ns']-.5)
        for n, expected in [('READ_Q', op == 'read'), ('WRITE_Q', op == 'write')]:
            put('captured_request', levels(data[high, col(n)], expected), cycle=r['cycle'], signal=n)
        if op == 'write':
            memory[r['row']] = r['expected']
        # No assertion whatsoever on cells until that address was legally written.
        # Reading all known rows after each operation detects collateral writes.
        for address, word in memory.items():
            for b in range(8):
                put('known_storage_preserved', levels(data[sample:sample+1, col(f'CELL_{address}_{b}')], (word >> b) & 1),
                    cycle=r['cycle'], row=address, bit=b)
        if op == 'read':
            reads += 8
            if memory.get(r['row']) != r['expected']:
                raise ValueError('Independent scoreboard read before matching write')
            for b in range(8):
                expected = (r['expected'] >> b) & 1
                put('read_bus_bit', levels(data[sample:sample+1, b+1], expected), cycle=r['cycle'], bit=b)
                put('read_register_bit', levels(data[sample:sample+1, col(f'REG_Q{b}')], expected), cycle=r['cycle'], bit=b)
            previous = r['expected']
        elif previous is not None:
            for b in range(8):
                put('read_register_retained', levels(data[high, col(f'REG_Q{b}')], (previous >> b) & 1), cycle=r['cycle'], bit=b)
        if op == 'idle':
            for offset, word in ((3, 0), (7, 0xFF)):
                sample = int(np.searchsorted(t, edge+offset))
                for b in range(8):
                    put('idle_bus_release_1kohm', abs(float(data[sample, b+1])-1.8*((word >> b) & 1)) <= .05,
                        cycle=r['cycle'], bit=b)
    metrics = {'read_bit_checks': reads, 'first_write_rising_ns': first,
               'first_write_after_vdd_plateau_ns': first-config['ramp_ns'],
               'first_read_sample_ns': next(r['sample_ns'] for r in records if r['operation'] == 'read'),
               'startup_evaluation_window_ns': [config['ramp_ns']+2, first-3.1],
               'no_digital_claim_during_ramp': True,
               'checks_by_kind': dict(Counter(c['kind'] for c in checks))}
    return checks, reference, metrics


def verify_pins(pinned):
    for name, expected in pinned.items():
        if sha(name) != expected:
            raise ValueError('Changed input or model: '+name)


def run_case(out, config, state, vectors, extra, pinned, timeout):
    out.mkdir(exist_ok=False)
    result = dict(status='RUNNING', scenario=config, condition=dict(corner='tt', vdd_v=1.8, temp_c=27),
                  clock=dict(period_ns=20, high_ns=10, low_ns=10, transition_ns=.05,
                             first_clock_ns=config['ramp_ns']+9), inputs=pinned)
    def publish(): atomic_text(out/'results.json', json.dumps(result, indent=2)+'\n')
    publish()
    try:
        result['resources'] = preflight(ROOT)
        verify_pins(pinned)
        deck, records, stop = make_deck(config, state, vectors)
        build = Path(tempfile.mkdtemp(prefix='startup-review-', dir=ROOT/'build/phase2'))
        (build/'bench.spice').write_text(deck)
        for name in ('binding.spice', 'fabric.spice'):
            shutil.copyfile(SOURCE/name, build/name)
        for name in ('bench.spice', 'binding.spice', 'fabric.spice'):
            shutil.copyfile(build/name, out/name)
        result.update(build_directory=str(build.relative_to(ROOT)), cycles=records, vectors=vectors,
                      probes=extra, stop_ns=stop,
                      simulation_inputs={n: sha(build/n) for n in ('bench.spice', 'binding.spice', 'fabric.spice')})
        publish()
        with (out/'ngspice.txt').open('w') as log:
            run = subprocess.run(['ngspice', '-n', '-b', 'bench.spice'], cwd=build,
                                 stdout=log, stderr=subprocess.STDOUT, timeout=timeout,
                                 env=dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1'))
        result['ngspice_return_code'] = run.returncode
        if run.returncode != 0 or not (build/'waveform.dat').is_file():
            raise ValueError('Simulator failed or no transient produced')
        raw = build/'waveform.dat'
        data = np.loadtxt(raw, skiprows=1)
        header = raw.open().readline().split()
        if header != ['time', *vectors]:
            raise ValueError('Raw probe header differs from declared vectors')
        checks, reference, metrics = analyze(data, records, vectors, extra, config, state, stop)
        atomic_text(out/'checks.json', json.dumps(dict(checks=checks, capture_reference=reference), indent=2)+'\n')
        # Keep lossless raw data locally. Portable selected waveform is explicitly
        # decimated; all assertions above used the full transient.
        np.savetxt(out/'waveform_excerpt.csv', data[::25], delimiter=',',
                   header=','.join(['time_s', *vectors]), comments='')
        verify_pins(pinned)
        for n, h in result['simulation_inputs'].items():
            if sha(build/n) != h or sha(out/n) != h:
                raise ValueError('Simulation input changed during execution')
        result.update(metrics=metrics, checks=len(checks), failures=sum(c['status'] == 'FAIL' for c in checks),
                      raw_waveform_sha256=sha(raw), rows=len(data))
        result['status'] = 'PASS' if checks and result['failures'] == 0 else 'FAIL'
        result['classification'] = 'NOMINAL_SCENARIO' if result['status'] == 'PASS' else 'REQUIRES_WAVEFORM_DIAGNOSIS'
    except Exception as error:
        result.update(status='BLOCKED' if 'Resource preflight' in str(error) else 'FAIL',
                      classification='EXECUTION_OR_EVIDENCE_FAILURE', error=str(error))
    result['artifacts'] = {p.name: sha(p) for p in out.iterdir() if p.is_file() and p.name != 'results.json'}
    publish()
    print(json.dumps(dict(scenario=out.name, status=result['status'], checks=result.get('checks'),
                          failures=result.get('failures'), error=result.get('error'))), flush=True)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    p.add_argument('--scenarios', nargs='+', choices=SCENARIOS, default=list(SCENARIOS))
    p.add_argument('--timeout', type=int, default=1800)
    args = p.parse_args()
    out = (ROOT/args.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2') or out == ROOT/'reports/phase2' or out.exists():
        p.error('Use a new directory under reports/phase2; existing evidence is never overwritten')
    if len(set(args.scenarios)) != len(args.scenarios) or args.timeout <= 0:
        p.error('Unique scenarios and a positive timeout required')
    out.mkdir(parents=True, exist_ok=False)
    record = dict(status='RUNNING', scope='Additional TT power-up scenarios; unchanged circuit; no minimum-startup guarantee',
                  requested_scenarios=args.scenarios, scenarios={})
    def publish(): atomic_text(out/'results.json', json.dumps(record, indent=2)+'\n')
    publish()
    try:
        state = json.loads((SOURCE/'results.json').read_text())
        if state['status'] != 'PASS_EXTRACTED_NOMINAL_ACCESS':
            raise ValueError('Sealed baseline electrical run required')
        seal = json.loads((ROOT/'reports/phase2/review_20261104/acceptance/results.json').read_text())
        required = [SOURCE/'results.json', SOURCE/'binding.spice', SOURCE/'bench.spice', SOURCE/'fabric.spice',
                    GDS/'final_extracted.spice', GDS/'final_flat.ext']
        for path in required:
            if seal['verified_files'].get(str(path.relative_to(ROOT))) != sha(path):
                raise ValueError('Baseline source not sealed: '+str(path))
        design_path = ROOT/'reports/phase2/portable_raw/routed_reference.json'
        sources = [*required, design_path, Path(__file__), ROOT/'tools/run_phase2_directed_review.py',
                   ROOT/'tools/phase2_access_checks.py', ROOT/'tools/phase2_resources.py']
        pinned = {str(path): sha(path) for path in sources}
        pinned.update(state['model_inputs'])
        verify_pins(pinned)
        versions = subprocess.run(['ngspice', '--version'], capture_output=True, text=True, check=True)
        (out/'ngspice_version.txt').write_text(versions.stdout+versions.stderr)
        vectors, extra = make_probes(state, json.loads(design_path.read_text()))
        record['inputs'] = pinned
        for name in args.scenarios:
            result = run_case(out/name, SCENARIOS[name], state, vectors, extra, pinned, args.timeout)
            record['scenarios'][name] = dict(status=result['status'], receipt_sha256=sha(out/name/'results.json'),
                                            parameters=SCENARIOS[name], metrics=result.get('metrics'),
                                            failures=result.get('failures'), checks=result.get('checks'))
            publish()
        states = [r['status'] for r in record['scenarios'].values()]
        record['status'] = 'PASS' if states and all(s == 'PASS' for s in states) else 'FAIL' if 'FAIL' in states else 'BLOCKED'
    except Exception as error:
        record.update(status='FAIL', error=str(error))
    record['artifacts'] = {s.name: sha(s) for s in out.iterdir() if s.is_file() and s.name != 'results.json'}
    publish(); print(json.dumps(dict(status=record['status'], error=record.get('error')), indent=2))
    return 0 if record['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
