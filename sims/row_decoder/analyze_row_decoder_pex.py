#!/usr/bin/env python3
"""Analyze retained PEX evidence without running EDA tools or changing circuits."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'sims/row_decoder/results/row_decoder_pex_output_pfets_3um_20261008'
PEX = ROOT / 'layout/row_decoder/archive/precompact_20261008/pex/row_decoder_pex.spice'


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def logical_lines(text):
    lines = []
    for line in text.splitlines():
        if line.startswith('+'):
            lines[-1] += ' ' + line[1:].strip()
        else:
            lines.append(line.strip())
    return lines


def spice_value(value):
    match = re.fullmatch(r'([+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?)([a-z]*)', value, re.I)
    if not match:
        raise ValueError(f'Unsupported SPICE number: {value}')
    scales = {'': 1, 'f': 1e-15, 'p': 1e-12, 'n': 1e-9, 'u': 1e-6,
              'm': 1e-3, 'k': 1e3, 'meg': 1e6, 'g': 1e9}
    return float(match[1]) * scales[match[2].lower()]


def write_csv(path, rows):
    if not rows:
        raise ValueError(f'No rows for {path}')
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def resistance_to_vss(resistors, terminals):
    """DC driving-point R with MOS/C removed; not transient ground bounce."""
    nodes = sorted({node for a, b, _ in resistors for node in (a, b)} - {'VSS'})
    indices = {node: i for i, node in enumerate(nodes)}
    n = len(nodes)
    matrix = [[0.0] * n for _ in range(n)]
    for a, b, value in resistors:
        if value <= 0:
            raise ValueError('Nonpositive resistor')
        g = 1 / value
        for node in (a, b):
            if node != 'VSS':
                matrix[indices[node]][indices[node]] += g
        if a != 'VSS' and b != 'VSS':
            i, j = indices[a], indices[b]
            matrix[i][j] -= g
            matrix[j][i] -= g
    factor = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            value = matrix[i][j] - sum(factor[i][k] * factor[j][k] for k in range(j))
            if i == j:
                if value <= 0:
                    raise ValueError('VSS resistor network is singular or not connected to VSS')
                factor[i][j] = math.sqrt(value)
            else:
                factor[i][j] = value / factor[j][j]
    rows = []
    for terminal in sorted(terminals):
        if terminal == 'VSS':
            resistance = 0.0
        else:
            idx = indices[terminal]
            vector = [0.0] * n
            for i in range(n):
                vector[i] = ((1.0 if i == idx else 0.0)
                             - sum(factor[i][j] * vector[j] for j in range(i))) / factor[i][i]
            resistance = sum(v * v for v in vector)
        rows.append(dict(terminal=terminal, dc_resistance_to_vss_ohm=resistance))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path,
                        default=ROOT / 'sims/row_decoder/results/row_decoder_pex_analysis_20261008')
    args = parser.parse_args()
    data = PEX.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    manifest = json.loads((RUN / 'pex/manifest.json').read_text())
    if not manifest['complete'] or manifest['errors'] or manifest['pex_sha256'] != digest:
        raise ValueError('Incomplete campaign or current PEX differs from the analyzed campaign')
    baseline_text = (RUN / 'baseline_input_netlist.spice').read_text()
    original_body = re.search(r'(?ims)^\.subckt row_decoder\s+[^\n]+\n(.*?)^\.ends', baseline_text)[1]
    originals = [line.split() for line in logical_lines(original_body) if line.startswith('XM')]
    capacitors, resistors, mos = [], [], []
    for line in logical_lines(data.decode()):
        parts = line.split()
        if not parts:
            continue
        if re.fullmatch(r'C\d+', parts[0]):
            value = spice_value(parts[3])
            if value < 0:
                raise ValueError('Negative capacitor in PEX')
            capacitors.append((parts[1], parts[2], value))
        elif re.fullmatch(r'R\d+', parts[0]):
            resistors.append((parts[1], parts[2], spice_value(parts[3])))
        elif re.fullmatch(r'X\d+', parts[0]):
            mos.append(parts)
    mappings = {}
    if len(mos) != 29 or len(originals) != 29:
        raise ValueError('Expected 29 decoder MOS in both extracted and schematic netlists')
    for device in mos:
        d, g, s, b = (x.split('.')[0] for x in device[1:5])
        matches = [o for o in originals if o[2] == g and {o[1], o[3]} == {d, s}
                   and o[4] == b and o[5] == device[5]]
        if len(matches) != 1:
            raise ValueError(f'Cannot uniquely identify extracted MOS: {device[0]}')
        mappings['x1.' + device[0][1:]] = matches[0][0][1:]
    timing = []
    for row in read_csv(RUN / 'comparison.csv'):
        delta_dec = float(row['delta_dec_delay50_ps'])
        delta_wl = float(row['delta_wl_delay50_ps'])
        timing.append(dict(case=row['case'], result=row['pex_result'],
                           baseline_dec90_ps=float(row['baseline_dec_delay90_ps']),
                           pex_dec90_ps=float(row['pex_dec_delay90_ps']),
                           baseline_wl90_ps=float(row['baseline_wl_delay90_ps']),
                           pex_wl90_ps=float(row['pex_wl_delay90_ps']),
                           wl90_excess_over_1ns_ps=float(row['pex_wl_delay90_ps']) - 1000,
                           delta_dec50_ps=delta_dec, delta_wl50_ps=delta_wl,
                           decoder_fraction_of_added_50pct_delay=delta_dec / delta_wl))
    cap_rows = []
    for node in sorted({x for a, b, _ in capacitors for x in (a, b)}):
        if node.startswith('VSS.'):
            continue
        incident = [(a, b, v) for a, b, v in capacitors if node in (a, b)]
        cap_rows.append(dict(node=node, incident_capacitance_ff=sum(v for _, _, v in incident)*1e15,
                             capacitance_to_vss_port_ff=sum(v for a, b, v in incident
                                                          if node != 'VSS' and 'VSS' in (a, b))*1e15,
                             capacitor_count=len(incident)))
    terminals = read_csv(RUN / 'pex/terminals.csv')
    warnings = []
    for case in sorted({r['case'] for r in terminals}):
        rows = [r for r in terminals if r['case'] == case and r['voltage'] != 'VBS']
        worst = max(rows, key=lambda r: max(abs(float(r['min_v'])), abs(float(r['max_v']))))
        low_worst = abs(float(worst['min_v'])) > abs(float(worst['max_v']))
        value = float(worst['min_v'] if low_worst else worst['max_v'])
        if abs(value) > 1.95:
            warnings.append(dict(case=case, extracted_device=worst['device'],
                                 schematic_device=mappings.get(worst['device'], 'WL buffer'),
                                 voltage=worst['voltage'], signed_peak_v=value,
                                 time_ns=float(worst['min_time_ns'] if low_worst else worst['max_time_ns'])))
    vss_terminals = {node for device in mos for node in device[1:5] if node.startswith('VSS')}
    resistance_rows = resistance_to_vss(resistors, vss_terminals)
    for row in resistance_rows:
        row['mos_connections'] = ';'.join(f'{d[0]}:{role}' for d in mos
                                         for role, node in zip(('D', 'G', 'S', 'B'), d[1:5])
                                         if node == row['terminal'])
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / 'timing_breakdown.csv', timing)
    write_csv(out / 'capacitance_by_node.csv', cap_rows)
    write_csv(out / 'terminal_warnings.csv', warnings)
    write_csv(out / 'vss_dc_resistance.csv', resistance_rows)
    write_csv(out / 'failed_checks.csv', [r for r in read_csv(RUN / 'pex/checks.csv') if r['result'] == 'FAIL'])
    history_inputs = []
    history = []
    for directory in ('row_decoder_pex_20261007_235827', 'row_decoder_pex_20261008_000419', RUN.name):
        path = RUN.parent / directory / 'comparison.csv'
        history_inputs.append(path)
        rows = [r for r in read_csv(path) if r['case'].startswith('slow')]
        entry = dict(run=directory, slow_case_count=len(rows))
        for metric in ('dec_delay90_ps', 'wl_delay90_ps', 'dec_precharge10_ps', 'wl_precharge10_ps'):
            values = [float(r['pex_' + metric]) for r in rows]
            entry[metric + '_min'] = min(values)
            entry[metric + '_max'] = max(values)
        history.append(entry)
    write_csv(out / 'sizing_history.csv', history)
    inputs = [PEX, RUN / 'comparison.csv', RUN / 'pex/checks.csv', RUN / 'pex/terminals.csv',
              RUN / 'baseline_input_netlist.spice', RUN / 'pex/manifest.json', Path(__file__), *history_inputs]
    metadata = dict(mode='analysis of existing artifacts; no new simulation or extraction',
                    inputs={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
                    mos_count=len(mos), resistor_count=len(resistors), capacitor_count=len(capacitors),
                    all_resistors_in_vss_network=all(a.split('.')[0] == b.split('.')[0] == 'VSS'
                                                     for a, b, _ in resistors),
                    extracted_to_schematic_device=mappings,
                    caveats=['Incident capacitance includes coupling; not a constant effective load.',
                             'DC resistance calculation removes all MOS and capacitors; not transient voltage.',
                             'Delay fraction uses matching 50% crossings; not an independent-stage delay.',
                             'The 1 ns/1.95 V screens remain unchanged and experimental.'])
    (out / 'manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(f'Analyzed {len(timing)} cases, {len(mos)} MOS, {len(resistors)} R, {len(capacitors)} C.')
    print(f'Evidence: {out.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
