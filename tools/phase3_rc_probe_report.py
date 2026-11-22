#!/usr/bin/env python3
"""Audit stored Phase 2 versus ideal-supply RC waveforms without simulating.

The comparison is diagnostic. It cannot establish physical PEX qualification,
timing/power signoff, or causal attribution of a failing read.
"""

import argparse
from bisect import bisect_left
import json
import math
from pathlib import Path

from phase3_rc_characterization import PUBLIC, QUAL, crossing
from phase3_rc_extraction import ROOT, sha256


SIDES = ('phase2_control', 'ideal_supply_rc')
SAMPLE_NS = (135, 139, 140, 141, 142, 143, 159, 161, 162)
WINDOW_NS = (130, 144)
DIFFERENCE_V = 0.3


def read_waveform(path, names, extra_public=(), *, minimum_end=164e-9):
    """Validate waveform vectors, preserving the simulator's column mapping."""
    public = ['time', *(name.lower() for name in PUBLIC), *(name.lower() for name in extra_public)]
    internal = [f'v(xdut.{name})'.lower() for name in names]
    with path.open() as stream:
        actual = next(stream, '').lower().split()
        if len(actual) == len(public) + len(internal):
            for index, name in enumerate(public):
                if name.startswith('i(') and actual[index] == name[2:-1] + '#branch':
                    actual[index] = name
        if (actual[:len(public)] != public or
                len(actual) != len(public) + len(internal) or
                len(set(internal)) != len(internal) or
                set(actual[len(public):]) != set(internal)):
            raise ValueError(f'Unexpected waveform vectors in {path}')
        indices = {name: actual.index(f'v(xdut.{name})'.lower()) for name in names}
        indices.update({signal: public.index(signal.lower()) for signal in extra_public})
        rows = []
        for line in stream:
            if not line.strip():
                continue
            cols = line.split()
            if len(cols) != len(actual):
                raise ValueError(f'Incomplete waveform sample in {path}')
            values = tuple(map(float, cols))
            if not all(math.isfinite(v) for v in values):
                raise ValueError(f'Nonfinite waveform sample in {path}')
            if rows and values[0] <= rows[-1][0]:
                raise ValueError(f'Nonmonotonic waveform time in {path}')
            rows.append(values)
    if len(rows) < 2 or rows[0][0] > min(130e-9, minimum_end) or rows[-1][0] < minimum_end:
        raise ValueError(f'Incomplete diagnostic waveform in {path}')
    return rows, indices


def voltage(rows, times, ns, column):
    """Linearly interpolate on a validated transient's own time grid."""
    t = ns * 1e-9
    if t < times[0] or t > times[-1]:
        raise ValueError(f'Sample outside waveform at {ns} ns')
    index = bisect_left(times, t)
    if index == 0 or times[index] == t:
        return rows[index][column]
    earlier, later = rows[index - 1], rows[index]
    return (earlier[column] + (later[column] - earlier[column]) *
            (t - earlier[0]) / (later[0] - earlier[0]))


def read_word(rows, times, ns):
    volts = [voltage(rows, times, ns, i + 2) for i in range(8)]
    states = ['1' if value >= 1.44 else '0' if value <= 0.36 else 'X'
              for value in volts]
    word = sum((state == '1') << bit for bit, state in enumerate(states))
    return {'volts': [round(v, 5) for v in volts],
            'bits_lsb_first': ''.join(states),
            'word_hex': f'0x{word:02X}' if 'X' not in states else None}


def check_artifacts(probe_run, manifest):
    if (manifest.get('status') != 'COMPLETE_DIAGNOSTIC' or
            manifest.get('qualification') != 'DIAGNOSTIC_ONLY_NOT_TIMING_POWER_SIGNOFF'):
        raise ValueError('Probe run is not a completed diagnostic')
    for side in SIDES:
        artifacts = manifest['sides'][side]['artifacts']
        if 'waveform.dat' not in artifacts or 'binding.spice' not in artifacts:
            raise ValueError(f'Missing source evidence for {side}')
        for name, digest in artifacts.items():
            file = probe_run / side / name
            if not file.is_file() or sha256(file) != digest:
                raise ValueError(f'Corrupted source artifact: {file}')


def incident_capacitance(spice, nodes):
    """Sum caps touching each PEX node, without treating them as a delay model."""
    totals = {node: {'rail_ff': 0., 'other_ff': 0., 'pairs': 0}
              for node in nodes}
    for line in spice.read_text().splitlines():
        words = line.split()
        if not words or not words[0].upper().startswith('C'):
            continue
        if len(words) < 4:
            raise ValueError('Malformed diagnostic capacitance card')
        a, b, raw = words[1:4]
        capacitance = float(raw)
        if not math.isfinite(capacitance) or capacitance < 0:
            raise ValueError('Invalid diagnostic capacitance')
        for node, other in ((a, b), (b, a)):
            if node in totals:
                kind = 'rail_ff' if other in ('VDD', 'VSS') else 'other_ff'
                totals[node][kind] += capacitance * 1e15
                totals[node]['pairs'] += 1
    return {node: {'rail_ff': round(value['rail_ff'], 5),
                   'other_ff': round(value['other_ff'], 5),
                   'pairs': value['pairs']}
            for node, value in totals.items()}


def compare(probe_run):
    manifest_file = probe_run / 'manifest.json'
    manifest = json.loads(manifest_file.read_text())
    check_artifacts(probe_run, manifest)
    probes = manifest['internal_probe_map']
    if not probes:
        raise ValueError('No internal probe mappings')
    series = {}
    for side in SIDES:
        label = 'phase2' if side == 'phase2_control' else 'pex'
        names = [probe[label] for probe in probes.values()]
        rows, indices = read_waveform(probe_run / side / 'waveform.dat', names)
        series[side] = (rows, [row[0] for row in rows], indices)

    report = {
        'source_run': manifest['run_id'],
        'source_manifest_sha256': sha256(manifest_file),
        'source_waveform_sha256': {
            side: manifest['sides'][side]['artifacts']['waveform.dat'] for side in SIDES},
        'waveform_rows': {side: len(series[side][0]) for side in SIDES},
        'qualification': 'DIAGNOSTIC_ONLY',
        'electrical_qualification': 'NOT_CHARACTERIZED',
        'phase3_nominal_bench_r1': 'NOT_EVALUATED_RC_DOMAIN',
        'first_difference_definition': (
            'first sampled |RC-Phase2| >= 0.3V from 130 to 144ns on a 0.05ns grid; '
            'limited to mapped probes, not earliest divergence in the SRAM'),
        'probes': {},
        'public_data': [],
    }
    caps = incident_capacitance(
        probe_run / 'ideal_supply_rc' / 'binding.spice',
        [probe['pex'] for probe in probes.values()])
    for name, mapping in probes.items():
        values = {}
        for side in SIDES:
            rows, times, indices = series[side]
            label = 'phase2' if side == 'phase2_control' else 'pex'
            index = indices[mapping[label]]
            values[side] = {
                'samples_v': {str(ns): round(voltage(rows, times, ns, index), 5)
                              for ns in SAMPLE_NS},
                'crossings_130_144_ns': {
                    direction: [round(t * 1e9, 5) for t in crossing(
                        rows, index, WINDOW_NS[0]*1e-9, WINDOW_NS[1]*1e-9,
                        0.9, direction)]
                    for direction in ('rise', 'fall')},
            }
        first = None
        for step in range(281):
            ns = 130 + step * 0.05
            left_rows, left_times, left_indices = series['phase2_control']
            right_rows, right_times, right_indices = series['ideal_supply_rc']
            left = voltage(left_rows, left_times, ns, left_indices[mapping['phase2']])
            right = voltage(right_rows, right_times, ns, right_indices[mapping['pex']])
            if abs(right - left) >= DIFFERENCE_V:
                first = round(ns, 5)
                break
        report['probes'][name] = {
            'pex_node': mapping['pex'], 'phase2_node': mapping['phase2'],
            'first_0p3v_difference_ns': first,
            'incident_capacitance_ff': caps[mapping['pex']],
            **values,
        }

    cycles = json.loads((QUAL / 'results.json').read_text())['cycles']
    for cycle in cycles:
        if cycle['operation'] != 'read' or cycle['sample_ns'] not in (141, 161):
            continue
        ns = cycle['sample_ns']
        evidence = {'cycle': cycle['cycle'], 'sample_ns': ns,
                    'expected_hex': f'0x{cycle["expected"]:02X}',
                    'post_sample_ns': ns + 1}
        for side in SIDES:
            rows, times, _ = series[side]
            evidence[side] = {'at_sample': read_word(rows, times, ns),
                              'one_ns_later_diagnostic': read_word(rows, times, ns + 1)}
        report['public_data'].append(evidence)
    if len(report['public_data']) != 2:
        raise ValueError('Expected two historical read cycles at 141 and 161ns')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe-run', type=Path, required=True)
    parser.add_argument('--output-root', type=Path,
                        default=ROOT / 'build/phase3/probe_reports')
    args = parser.parse_args(argv)
    source = args.probe_run.resolve(strict=True)
    report = compare(source)
    target = args.output_root / f'{source.name}-comparison.json'
    content = json.dumps(report, indent=2, sort_keys=True) + '\n'
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_text() != content:
            raise ValueError(f'Existing report differs: {target}')
    else:
        target.write_text(content)
    print(json.dumps({'report': str(target), 'qualification': report['qualification'],
                      'probe_count': len(report['probes'])}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
