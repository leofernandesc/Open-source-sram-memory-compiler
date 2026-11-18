#!/usr/bin/env python3
"""Trace the 1.8 V Phase 3 TT read path on the Phase 2 qualification stimulus."""

import argparse
import csv
import json
from pathlib import Path
import re

from phase3_rc_characterization import QUAL, crossing
from phase3_rc_extraction import sha256
from phase3_rc_probe_report import read_waveform, voltage


ARRAY = 'macro_core.array_and_peripherals'
LOW, HIGH = .36, 1.44
LOCAL_CLOCKS = ('_33_.Y', *(f'_{59 + bit}_.Y' for bit in range(1, 8)))
OUTPUT_ENABLES = ('_87_.TE_B', *(f'_{59 - bit}_.Y' for bit in range(1, 7)), '_35_.Y')
WORDLINES = (*(f'{ARRAY}.wl_driver_{row}.WL' for row in range(3)),
             f'{ARRAY}.bitcell_6t_24.WL')


def correct(value, level):
    return value >= HIGH if level else value <= LOW


def settled_ns(rows, times, signals, start_ns, end_ns):
    """Return when all signals entered their final valid interval ending at end_ns."""
    if start_ns >= end_ns:
        raise ValueError('Empty settling window')
    valid_from = start_ns
    for col, level in signals:
        if not correct(voltage(rows, times, end_ns, col), level):
            return None
        edges = crossing(rows, col, start_ns * 1e-9, end_ns * 1e-9,
                         HIGH if level else LOW, 'rise' if level else 'fall')
        if edges:
            valid_from = max(valid_from, edges[-1] * 1e9)
        elif not correct(voltage(rows, times, start_ns, col), level):
            raise ValueError('Final valid level has no entry crossing')
    return valid_from


def single_edge_ns(rows, col, start_ns, end_ns, threshold, direction):
    edges = crossing(rows, col, start_ns * 1e-9, end_ns * 1e-9, threshold, direction)
    if len(edges) != 1:
        raise ValueError(f'Expected one {direction} through {threshold:g} V in '
                         f'{start_ns:g}–{end_ns:g} ns for column {col}')
    return edges[0] * 1e9


def trace_read_path(rows, indices, cycles, weak_disabled):
    times = [row[0] for row in rows]
    checks = []
    for cycle in cycles:
        if cycle['operation'] != 'read' or times[-1] < cycle['sample_ns'] * 1e-9:
            continue
        rise, fall, sample = (cycle[key] for key in ('rise_ns', 'fall_ns', 'sample_ns'))
        calibration = cycle['calibration']
        # Stop before the enable mask, and before the competing weak driver if active.
        end = (calibration['mask_ns'] if weak_disabled else calibration['weak_on_ns']) - .05
        if end * 1e-9 > times[-1]:
            raise ValueError(f'Missing post-capture samples for cycle {cycle["cycle"]}')
        sclk = indices['macro_core.sense_drive.X']
        sclk20 = single_edge_ns(rows, sclk, rise, fall, LOW, 'rise')
        sclk50 = single_edge_ns(rows, sclk, sclk20, fall, .9, 'rise')
        public_fall = single_edge_ns(rows, 1, fall, sample, .9, 'fall')
        wl = indices.get(WORDLINES[cycle['row']])
        wl80 = None if wl is None else single_edge_ns(rows, wl, rise, fall, HIGH, 'rise')
        for bit, clk_node in enumerate(LOCAL_CLOCKS):
            expected = (cycle['expected'] >> bit) & 1
            sense_out, d = indices[f'_{43 - bit}_.A1'], indices[f'_{75 + bit}_.D']
            sense_out_b = indices.get(f'{ARRAY}.sense_amp_{bit}.SA_OUTB')
            q = indices['_75_.Q' if bit == 0 else f'_{87 + bit}_.A']
            bl = indices[f'{ARRAY}.write_driver_{bit}.BL']
            blb = indices[f'{ARRAY}.write_driver_{bit}.BLB']
            enable = indices.get(OUTPUT_ENABLES[bit])
            data = bit + 2
            capture = single_edge_ns(rows, indices[clk_node], public_fall, sample, .9, 'rise')
            bl_delta = voltage(rows, times, sclk20 - .05, bl) - voltage(rows, times, sclk20 - .05, blb)
            signed_delta50 = (2 * expected - 1) * (
                voltage(rows, times, sclk50, bl) - voltage(rows, times, sclk50, blb))
            paired = None if sense_out_b is None else settled_ns(
                rows, times, [(sense_out, expected), (sense_out_b, 1 - expected)], sclk20, capture)
            data_stable = settled_ns(rows, times, [(data, expected)], public_fall, end)
            observed = voltage(rows, times, sample, data)
            sample_window = settled_ns(rows, times, [(data, expected)], sample - .1, sample + .1)
            checks.append({
                'cycle': cycle['cycle'], 'row': cycle['row'], 'bit': bit, 'expected': expected,
                'wl80_ns': wl80, 'sclk20_ns': sclk20, 'sclk50_ns': sclk50,
                'wl80_to_sclk20_ns': None if wl80 is None else sclk20 - wl80,
                'bl_minus_blb_50ps_before_sclk20_v': bl_delta,
                'signed_delta_50ps_before_sclk20_v': (2 * expected - 1) * bl_delta,
                'signed_delta_at_sclk50_v': signed_delta50,
                'sense_out_stable_to_capture_ns': settled_ns(
                    rows, times, [(sense_out, expected)], sclk20, capture),
                'sense_pair_stable_to_capture_ns': paired,
                'sense_out_at_capture_v': voltage(rows, times, capture, sense_out),
                'd_stable_to_capture_ns': settled_ns(rows, times, [(d, expected)], sclk20, capture),
                'd_at_capture_v': voltage(rows, times, capture, d),
                'public_fall_ns': public_fall, 'local_capture_ns': capture,
                'q_before_capture_v': voltage(rows, times, capture - .05, q),
                'q_at_sample_v': voltage(rows, times, sample, q),
                'q_stable_post_capture_ns': settled_ns(rows, times, [(q, expected)], capture, end),
                'data_at_sample_v': observed,
                'data_at_sample_pass': correct(observed, expected),
                'data_sample_window_pass': sample_window == sample - .1,
                'data_stable_before_mask_or_probe_ns': data_stable,
                'data_observation_end_ns': end,
                'output_enable_n_at_end_v': None if enable is None else voltage(
                    rows, times, end, enable),
            })
    if not checks:
        raise ValueError('No complete read cycles found')
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--probes', type=Path, help='probe mapping if stored outside the run')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    probes = args.probes or args.run / 'probes.json'
    bench, log, waveform, binding, fabric = (args.run / name for name in
        ('bench.spice', 'ngspice.log', 'waveform.dat', 'binding.spice', 'fabric.spice'))
    log_text = log.read_text()
    if (not re.search(r'^ngspice-\S+ done\s*$', log_text, re.M) or
            re.search(r'analysis aborted|simulation interrupted|^Error:', log_text, re.I | re.M)):
        raise ValueError('ngspice did not complete the transient')
    deck = bench.read_text()
    stop = re.search(r'^tran \S+ ([\d.]+)n 0 \S+\s*$', deck, re.M)
    if stop is None:
        raise ValueError('Missing transient duration in nanoseconds')
    weak_disabled = 'V_HOST_WEAK_EN HOST_WEAK_EN 0 0' in deck.splitlines()
    nodes = json.loads(probes.read_text())
    rows, indices = read_waveform(waveform, nodes.values())
    if rows[-1][0] < float(stop[1]) * 1e-9 - 1e-15:
        raise ValueError('Waveform ended before deck transient completed')
    cycles_path = QUAL / 'results.json'
    cycles = json.loads(cycles_path.read_text())['cycles']
    checks = trace_read_path(rows, {name: indices[node] for name, node in nodes.items()},
                             cycles, weak_disabled)
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    with (output / 'read_path.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(checks[0]))
        writer.writeheader()
        writer.writerows(checks)
    summary = {
        'electrical_qualification': 'NOT_CHARACTERIZED',
        'run': str(args.run),
        'weak_driver_disabled': weak_disabled,
        'source_sha256': {str(p): sha256(p) for p in
                          (bench, binding, fabric, waveform, log, probes, cycles_path)},
        'metrics': {'data_at_sample_pass': 'point sample using 20% and 80% of 1.8 V',
                    'data_sample_window_pass': 'same thresholds held for sample ± 100 ps',
                    'stable_ns': 'start of final contiguous valid interval in the named window'},
        'cycles': {},
    }
    measure_pair = all(f'{ARRAY}.sense_amp_{bit}.SA_OUTB' in nodes for bit in range(8))
    for cycle in sorted({row['cycle'] for row in checks}):
        bits = [row for row in checks if row['cycle'] == cycle]
        summary['cycles'][cycle] = {
            'minimum_signed_delta_50ps_before_sclk20_v': min(
                b['signed_delta_50ps_before_sclk20_v'] for b in bits),
            'resolved_sense_out_bits': sum(b['sense_out_stable_to_capture_ns'] is not None for b in bits),
            'resolved_sense_pair_bits': None if not measure_pair else sum(
                b['sense_pair_stable_to_capture_ns'] is not None for b in bits),
            'valid_d_at_capture_bits': sum(b['d_stable_to_capture_ns'] is not None for b in bits),
            'valid_q_at_sample_bits': sum(correct(b['q_at_sample_v'], b['expected']) for b in bits),
            'valid_data_at_sample_bits': sum(b['data_at_sample_pass'] for b in bits),
            'valid_data_sample_window_bits': sum(b['data_sample_window_pass'] for b in bits),
            'valid_data_at_observation_end_bits': sum(
                b['data_stable_before_mask_or_probe_ns'] is not None for b in bits),
        }
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(output / 'summary.json')


if __name__ == '__main__':
    main()
