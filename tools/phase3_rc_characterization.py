#!/usr/bin/env python3
"""Exploratory TT/SS/FF public-port timing and macro supply energy on true RC PEX.

Run each corner independently after a successful Phase 3 distributed RC extraction.
This does not characterize setup/hold, internal read nodes, or static power.
"""

import argparse
import csv
from collections import defaultdict
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

from phase3_rc_extraction import (BASE, EXPECTED_GDS, EXPECTED_PINS, ROOT,
                                  check_baseline, inspect_dc_supply_paths,
                                  inspect_netlist, logical_cards,
                                  preflight, sha256)


QUAL = ROOT / 'reports/phase2/direct_abutment_20261111/qualification_v1'
PDK = Path('/opt/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice')
COLUMNS = ('run_id', 'configuration', 'corner', 'vdd_v', 'temp_c', 'operation',
           'metric', 'bit', 'value', 'unit', 'status', 'transition', 'measure', 'reason')
PUBLIC = ('v(CLK)', *(f'v(DATA{i})' for i in range(8)), 'v(VDD)', 'i(VDD_SRC)')


def idealize_supply_mesh(extracted):
    """Diagnostic approximation: replace each resistive supply mesh with an ideal rail.

    Preserve signal resistances and capacitors, including aggregate rail
    decoupling. This is *not* a full-RC timing or power signoff model.
    """
    cards = logical_cards(extracted)
    parent = {}

    def find(n):
        parent.setdefault(n, n)
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for line in cards:
        part = line.split()
        if part and part[0][0].upper() == 'R' and not part[0].startswith('.'):
            union(part[1], part[2])
    if find('VDD') == find('VSS'):
        raise ValueError('Cannot idealize a resistive VDD/VSS short')
    supplies = {find('VDD'): 'VDD', find('VSS'): 'VSS'}

    def mapped(node):
        return supplies.get(find(node), node) if node in parent else node

    unit = {'': 1., 'a': 1e-18, 'f': 1e-15, 'p': 1e-12,
            'n': 1e-9, 'u': 1e-6, 'm': 1e-3, 'k': 1e3,
            'M': 1e-3, 'g': 1e9, 'G': 1e9, 't': 1e12, 'T': 1e12}

    def farads(raw):
        match = re.fullmatch(r'([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([afpnumkMgGtT]?)', raw)
        if not match:
            raise ValueError('Invalid capacitance in RC diagnostic: ' + raw)
        value = float(match[1]) * unit[match[2]]
        if not math.isfinite(value) or value < 0:
            raise ValueError('Invalid capacitance in RC diagnostic: ' + raw)
        return value

    output = []
    end_card = None
    caps = defaultdict(list)
    counts = {'original_resistors': 0, 'retained_signal_resistors': 0,
              'original_capacitors': 0, 'retained_capacitor_pairs': 0,
              'suppressed_zero_or_internal_capacitors': 0, 'mos': 0}
    for line in cards:
        if line.startswith('.'):
            if line.lower().startswith('.ends'):
                if end_card is not None:
                    raise ValueError('Multiple .ends cards in RC netlist')
                end_card = line
            else:
                output.append(line)
            continue
        part = line.split()
        kind = part[0][0].upper()
        if kind == 'X':
            part[1:5] = [mapped(n) for n in part[1:5]]
            counts['mos'] += 1
            output.append(' '.join(part))
        elif kind == 'R':
            counts['original_resistors'] += 1
            part[1:3] = [mapped(n) for n in part[1:3]]
            if part[1] != part[2]:
                counts['retained_signal_resistors'] += 1
                output.append(' '.join(part))
        elif kind == 'C':
            counts['original_capacitors'] += 1
            a, b = mapped(part[1]), mapped(part[2])
            value = farads(part[3])
            if a == b or value == 0:
                counts['suppressed_zero_or_internal_capacitors'] += 1
                continue
            caps[tuple(sorted((a, b)))].append(value)
        else:
            raise ValueError('Unsupported extracted element: ' + line)
    for index, (nodes, values) in enumerate(sorted(caps.items())):
        output.append(f'C_IDEAL_RAIL_{index} {nodes[0]} {nodes[1]} {math.fsum(values):.17g}')
    if end_card is None:
        raise ValueError('Missing .ends card in RC netlist')
    output.append(end_card)
    counts['retained_capacitor_pairs'] = len(caps)
    counts['rail_to_rail_capacitance_f'] = math.fsum(caps.get(('VDD', 'VSS'), ()))
    return '\n'.join(output) + '\n', counts


def bind_rc_deck(extracted):
    """Rename nodes only; retain every R, C and X card and their parameters."""
    lines = logical_cards(extracted)
    heads = [c.split() for c in lines if c.lower().startswith('.subckt ')]
    if len(heads) != 1 or tuple(heads[0][2:]) != EXPECTED_PINS:
        raise ValueError('Expected canonical flat Phase 3 physical ports')
    top = heads[0][2:]
    public = {p: re.sub(r'^(ADDR|DATA)\[(\d+)\]$', r'\1\2', p) for p in top}
    parts = []
    nodes = set(top)
    for line in lines:
        if line.startswith('.'):
            continue
        card = line.split()
        kind = card[0][0].upper()
        if kind not in ('X', 'R', 'C'):
            raise ValueError('Unexpected extracted element: ' + line)
        width = 4 if kind == 'X' else 2
        if len(card) < width + 2:
            raise ValueError('Truncated extracted element: ' + line)
        nodes.update(card[1:1 + width])
        parts.append((card, width))
    nodes.discard('0')
    internals = sorted(nodes - set(top))
    names = {**public, **{n: f'rc{i}' for i, n in enumerate(internals)}, '0': '0'}
    if len(set(names.values())) != len(names):
        raise ValueError('Node name alias in RC binding')
    result = ['* Phase 3 flat RC: node renaming only, all parasitic cards retained',
              '.subckt sram_4x8_wrapper ' + ' '.join(names[n] for n in top)]
    for card, width in parts:
        result.append(' '.join([card[0], *(names[n] for n in card[1:1 + width]),
                                *card[1 + width:]]))
    result.append('.ends sram_4x8_wrapper')
    if len(result) - 3 != len(parts):
        raise ValueError('Some RC circuit elements were dropped')
    return '\n'.join(result) + '\n', {k: v for k, v in names.items() if k in public}


def prepare_deck(template, corner, load_ff):
    if corner not in ('tt', 'ss', 'ff') or not 0 < load_ff <= 100:
        raise ValueError('Unsupported corner or capacitive load')
    lines = template.splitlines()
    model = [i for i, s in enumerate(lines) if s.strip().lower().startswith('.lib ')]
    if len(model) != 1:
        raise ValueError('Expected one explicit PDK .lib line')
    lines[model[0]] = f'.lib "{PDK}" {corner}'
    saves = [i for i, s in enumerate(lines) if s.lower().startswith('.save ')]
    waves = [i for i, s in enumerate(lines) if s.lower().startswith('wrdata waveform.dat ')]
    if len(saves) != 1 or len(waves) != 1:
        raise ValueError('Expected public waveform slots in Phase 2 deck')
    lines[saves[0]] = '.save ' + ' '.join(PUBLIC)
    lines[waves[0]] = 'wrdata waveform.dat ' + ' '.join(PUBLIC)
    dut = [i for i, s in enumerate(lines) if s.upper().startswith('XDUT ')]
    if len(dut) != 1:
        raise ValueError('Expected one extracted SRAM instance')
    lines[dut[0]:dut[0]] = [f'C_PHASE3_LOAD{i} DATA{i} 0 {load_ff:g}f' for i in range(8)]
    joined = '\n'.join(lines) + '\n'
    if '.ic ' in joined.lower() or '.nodeset' in joined.lower():
        raise ValueError('Artificial electrical initialization is disallowed')
    if '370n' not in joined:
        raise ValueError('Unexpected functional testbench duration')
    return joined


def parse_waveform(path):
    rows = []
    with path.open() as f:
        header = next(f, '').strip().split()
        if len(header) != len(PUBLIC) + 1:
            raise ValueError(f'Unexpected waveform columns: {header}')
        expected = ['time', *(n.lower() for n in PUBLIC)]
        actual = [name.lower() for name in header]
        # Ngspice may rename the branch current to its raw vector name.
        if actual[-1] == 'vdd_src#branch':
            actual[-1] = 'i(vdd_src)'
        if actual != expected:
            raise ValueError(f'Incorrect public waveform order: {header}')
        for line in f:
            cols = line.split()
            if len(cols) != len(PUBLIC) + 1:
                raise ValueError('Incomplete raw waveform row')
            values = tuple(map(float, cols))
            if not all(map(math.isfinite, values)):
                raise ValueError('Nonfinite ngspice sample')
            if rows and values[0] <= rows[-1][0]:
                raise ValueError('Nonmonotonic ngspice time vector')
            rows.append(values)
    if len(rows) < 100 or rows[-1][0] < 365e-9:
        raise ValueError('Transient missing required operating cycles')
    return rows


def crossing(rows, col, start, stop, threshold, direction):
    found = []
    for a, b in zip(rows, rows[1:]):
        if a[0] > stop:
            break
        if b[0] < start:
            continue
        lo, hi = a[col], b[col]
        if (lo < threshold <= hi if direction == 'rise' else lo > threshold >= hi):
            t = a[0] + (threshold - lo) * (b[0] - a[0]) / (hi - lo)
            if start <= t <= stop:
                found.append(t)
    return found


def at(rows, t, col):
    import bisect
    # Limit compensation to IEEE-754 rounding at an exact sample boundary.
    epsilon = 1e-15
    if t < rows[0][0] - epsilon or t > rows[-1][0] + epsilon:
        raise ValueError('Probe outside sampled transient')
    if t <= rows[0][0]:
        return rows[0][col]
    if t >= rows[-1][0]:
        return rows[-1][col]
    i = bisect.bisect_left([r[0] for r in rows], t)
    a, b = rows[i - 1], rows[i]
    fraction = (t - a[0]) / (b[0] - a[0])
    return a[col] + fraction * (b[col] - a[col])


def supply_energy(rows, start, stop):
    # Integral of -V(VDD) * I(VDD_SRC); includes clock/precharge and leakage.
    points = [start]
    vals = [-at(rows, start, 10) * at(rows, start, 11)]
    for row in rows:
        if start < row[0] < stop:
            points.append(row[0])
            vals.append(-row[10] * row[11])
    points.append(stop)
    vals.append(-at(rows, stop, 10) * at(rows, stop, 11))
    return sum((v + w) * (b - a) * .5
               for a, b, v, w in zip(points, points[1:], vals, vals[1:]))


def analyze(rows, cycles, corner, run_id):
    evidence = []
    checks = []

    def metric(op, name, bit, value, unit, status='PASS', transition='na', reason='', measure=''):
        evidence.append(dict(zip(COLUMNS, (run_id, '4x8', corner, 1.8, 27, op,
                                           name, bit, value, unit, status, transition,
                                           measure, reason))))

    for rec in cycles:
        op = rec['operation']
        rise = rec['rise_ns'] * 1e-9
        fall = rec['fall_ns'] * 1e-9
        if op == 'read':
            rise_edges = crossing(rows, 1, rise, rise + 0.1e-9, .9, 'rise')
            fall_edges = crossing(rows, 1, fall, fall + 0.1e-9, .9, 'fall')
            if len(rise_edges) != 1 or len(fall_edges) != 1:
                raise ValueError(f'Clock edge invalid in read cycle {rec["cycle"]}')
            for bit in range(8):
                target = (rec['expected'] >> bit) & 1
                col = bit + 2
                direction = 'rise' if target else 'fall'
                sample = rec['sample_ns'] * 1e-9
                observed = at(rows, sample, col)
                stable = all((r[col] >= 1.44 if target else r[col] <= .36)
                             for r in rows if sample - .1e-9 <= r[0] <= sample + .1e-9)
                good = stable and (observed >= 1.44 if target else observed <= .36)
                checks.append({'cycle': rec['cycle'], 'bit': bit, 'expected': target,
                               'observed_v': observed, 'status': 'PASS' if good else 'FAIL'})
                edges = crossing(rows, col, rise_edges[0], sample, .9, direction)
                previous = at(rows, rise_edges[0] - .2e-9, col)
                previous_opposite = (previous <= .36 if target else previous >= 1.44)
                # A transition before the falling capture edge can be recovery
                # of the previous word. It cannot qualify new read-data timing.
                after_capture = len(edges) == 1 and edges[0] >= fall_edges[0]
                valid_delay = good and previous_opposite and after_capture
                if valid_delay:
                    after = [r[col] for r in rows if edges[0] + .1e-9 <= r[0] <= sample]
                    valid_delay = all((v >= 1.44 if target else v <= .36) for v in after)
                for name, reference in (('tCLK_TO_DATA', fall_edges[0]),
                                        ('tACCESS', rise_edges[0])):
                    measured = valid_delay
                    reason = ('READ_INVALID' if not good else
                              'PREVIOUS_WORD_ALREADY_MATCHED' if not previous_opposite else
                              'OUTPUT_BEFORE_FALLING_EDGE' if len(edges) == 1 and not after_capture else
                              'NO_UNIQUE_SETTLED_SWITCH' if not valid_delay else
                              '')
                    metric('read', name, bit, edges[0] - reference if measured else None,
                           's', 'PASS' if measured else 'NOT_CHARACTERIZED',
                           direction if valid_delay else 'stable',
                           reason,
                           f'cycle_{rec["cycle"]}_bit_{bit}')
        end = rise + 20e-9
        energy = supply_energy(rows, rise, end)
        metric(op, 'E_' + op.upper(), None, energy, 'J',
               measure=f'cycle_{rec["cycle"]}_full_20ns')
        metric(op, ('P_IDLE' if op == 'idle' else 'P_' + op.upper() + '_AVG'),
               None, energy / (end - rise), 'W',
               measure=f'cycle_{rec["cycle"]}_full_20ns')

    return evidence, checks


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extract-run', type=Path, required=True)
    parser.add_argument('--corner', choices=('tt', 'ss', 'ff'), required=True)
    parser.add_argument('--load-ff', type=float, default=10.)
    parser.add_argument('--supply-model', choices=('full', 'ideal'), default='full',
                        help='ideal is a diagnostic approximation, not full-RC qualification')
    parser.add_argument('--ngspice', default='ngspice')
    parser.add_argument('--timeout', type=int, default=2400)
    parser.add_argument('--output-root', type=Path, default=ROOT / 'build/phase3/electrical_runs')
    args = parser.parse_args(argv)
    check_baseline()
    resources = preflight(ROOT)
    source = args.extract_run.resolve()
    provenance = json.loads((source / 'manifest.json').read_text())
    valid_profiles = {'PASS_RC_NETLIST_STRUCTURE': 'all',
                      'PASS_TARGETED_RC_NETLIST_STRUCTURE': 'critical_signals'}
    if (provenance['status'] not in valid_profiles or
            provenance.get('rc_profile', 'all') != valid_profiles[provenance['status']] or
            provenance['gds_sha256'] != EXPECTED_GDS):
        raise ValueError('Input is not qualified Phase 3 distributed RC extraction')
    if args.supply_model == 'ideal' and provenance.get('rc_profile', 'all') != 'all':
        raise ValueError('Ideal-supply diagnostic requires full distributed RC source')
    for file, digest in provenance['artifacts'].items():
        if sha256(source / file) != digest:
            raise ValueError('Changed extraction artifact: ' + file)
    extracted = source / 'extracted_rc.spice'
    info = inspect_netlist(extracted)
    if info != provenance['extraction']:
        raise ValueError('Extraction counters/hash changed after qualification')
    run_id = (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-'
              + args.corner + '-' + uuid.uuid4().hex[:8])
    output = args.output_root.resolve()
    output.mkdir(parents=True, exist_ok=True)
    run = output / run_id
    run.mkdir(exist_ok=False)
    result = {'run_id': run_id, 'status': 'RUNNING', 'corner': args.corner,
              'configuration': '4x8', 'vdd_v': 1.8, 'temp_c': 27,
              'supply_model': args.supply_model,
              'load_ff_per_bit': args.load_ff, 'full_cycle_ns': 20,
              'extraction_manifest_sha256': sha256(source / 'manifest.json'),
              'rc_profile': provenance.get('rc_profile', 'all'),
              'model_sha256': sha256(PDK), 'resources': resources,
              'bench_source_sha256': sha256(QUAL / 'bench.spice'),
              'cycles_sha256': sha256(QUAL / 'results.json'),
              'scope': 'RC PEX per extraction profile, public DATA and macro VDD',
              'simulator_status': 'NOT_RUN',
              'functional_validation': {
                  'status': 'NOT_CHARACTERIZED',
                  'method': 'legacy 72-bit public DATA sample checks',
                  'phase3_nominal_bench_r1': 'NOT_EVALUATED_RC_DOMAIN',
              },
              'electrical_qualification': 'NOT_CHARACTERIZED',
              'not_characterized': ['tREAD_INTERNAL', 'tSETUP', 'tHOLD', 'P_STATIC',
                                    'tOUT_SETUP', 'tOUT_HOLD', 'Fmax'],
              'definitions': {'tACCESS': 'rising CLK50 to unique new DATA50 after falling capture edge',
                              'tCLK_TO_DATA': 'falling CLK50 to unique new DATA50 after capture edge',
                              'power': 'negative VDD times supply-source current; full 20ns per cycle'},
              }
    try:
        source_text = extracted.read_text()
        result['power_connectivity'] = inspect_dc_supply_paths(source_text)
        isolated = [rail for rail in ('VDD', 'VSS')
                    if not result['power_connectivity'][rail]['mos_terminals_reachable']]
        if isolated:
            raise ValueError('Extracted supply port has no DC path to MOS terminals: '
                             + ', '.join(isolated))
        if result['power_connectivity']['rails_short_through_resistors']:
            raise ValueError('Extracted VDD and VSS are shorted through resistors')
        if args.supply_model == 'ideal':
            source_text, result['ideal_supply_diagnostic'] = idealize_supply_mesh(source_text)
            result['scope'] = ('Signal distributed RC with ideal VDD/VSS meshes; '
                               'diagnostic approximation, not full-RC signoff')
            result['not_characterized'] += ['FULL_RC_TIMING', 'FULL_RC_POWER', 'RAIL_IR_DROP']
        binding, ports = bind_rc_deck(source_text)
        if len(ports) != 16:
            raise ValueError('Wrong public net alias count')
        (run / 'binding.spice').write_text(binding)
        (run / 'fabric.spice').write_text('* Fabric included in flat PEX\n')
        deck = prepare_deck((QUAL / 'bench.spice').read_text(), args.corner, args.load_ff)
        (run / 'bench.spice').write_text(deck)
        with (run / 'ngspice.log').open('wb') as log:
            proc = subprocess.run([args.ngspice, '-n', '-b', 'bench.spice'], cwd=run,
                                  stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout,
                                  env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'})
        if proc.returncode:
            raise RuntimeError(f'ngspice exited {proc.returncode}; see ngspice.log')
        result['simulator_status'] = 'PASS'
        rows = parse_waveform(run / 'waveform.dat')
        records = json.loads((QUAL / 'results.json').read_text())['cycles']
        measurements, checks = analyze(rows, records, args.corner, run_id)
        if not measurements or not checks:
            raise ValueError('No read timing or functional checks')
        with (run / 'metrics.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(measurements)
        (run / 'functional_checks.json').write_text(json.dumps(checks, indent=2) + '\n')
        result['read_bits_checked'] = len(checks)
        result['read_bits_failed'] = sum(c['status'] == 'FAIL' for c in checks)
        result['functional_validation']['legacy_read_bits_checked'] = len(checks)
        result['functional_validation']['legacy_read_bits_failed'] = result['read_bits_failed']
        result['functional_validation']['status'] = (
            'FAIL_DIAGNOSTIC_READ_BITS' if result['read_bits_failed'] else
            'PASS_DIAGNOSTIC_READ_BITS_ONLY')
        result['metric_pass_count'] = sum(m['status'] == 'PASS' for m in measurements)
        result['metrics_not_characterized'] = sum(m['status'] == 'NOT_CHARACTERIZED' for m in measurements)
        result['status'] = (('PASS_DIAGNOSTIC_IDEAL_SUPPLY' if args.supply_model == 'ideal'
                             else 'PASS_EXPLORATORY_FULL_RC' if result['rc_profile'] == 'all'
                             else 'PASS_EXPLORATORY_TARGETED_RC') if not result['read_bits_failed']
                            else 'FAIL_FUNCTIONAL')
    except Exception as exc:
        result['status'] = 'FAIL'
        result['error'] = str(exc)
    finally:
        result['artifacts'] = {p.name: sha256(p) for p in run.iterdir() if p.is_file()}
        (run / 'manifest.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'run': str(run), 'status': result['status'],
                      'read_bits_failed': result.get('read_bits_failed'),
                      'error': result.get('error')}, indent=2))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    sys.exit(main())
