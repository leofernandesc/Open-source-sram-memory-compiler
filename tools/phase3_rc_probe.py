#!/usr/bin/env python3
"""Reproducible Phase 3 RC failure probe against the accepted Phase 2 MOS deck.

Runs a SHORT, deliberately nonqualifying TT experiment for internal control
signals on two matched transistor decks. Output is diagnostic evidence only.
The original physical extraction and the Phase 2 qualification are read-only.
"""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import uuid

from phase3_rc_characterization import (PDK, PUBLIC, QUAL, at,
                                        bind_rc_deck, idealize_supply_mesh,
                                        prepare_deck)
from phase3_rc_extraction import (EXPECTED_GDS, EXPECTED_PINS, ROOT,
                                  check_baseline, logical_cards, sha256)


PROBES = (
    'macro_core.write_drive.X',
    'macro_core.sense_drive.X',
    'macro_core.precharge_drive.X',
    'macro_core.evaluation.X',
    'macro_core.array_and_peripherals.wl_driver_0.WL',
    'macro_core.array_and_peripherals.write_driver_0.BL',
    'macro_core.array_and_peripherals.write_driver_0.BLB',
    'macro_core.array_and_peripherals.sense_amp_0.SA_OUTB',
    'macro_core.phase_delay\\[0\\].delay_cell.A',
    'macro_core.phase_delay\\[40\\].delay_cell.A',
    'macro_core.phase_delay\\[79\\].delay_cell.Y',
    '_86_.CLK',
    '_86_.Q',
)
SAMPLES_NS = (139., 140.1, 140.5, 141., 141.5, 142., 143.,
              159., 160.1, 161., 161.5, 162., 163.)


def _mos(text):
    return [line.split() for line in logical_cards(text)
            if line and line[0].upper() == 'X']


def reference_node_map(ideal, phase2):
    """Map PEX nodes to Phase 2 through their signal resistor components.

    Resistors split a Phase 2 net into physical PEX MOS terminals. Reject
    resistor components that merge distinct reference nets, and preserve
    every resistor in the experimental circuit.
    """
    a, b = _mos(ideal), _mos(phase2)
    if len(a) != 1493 or len(b) != len(a):
        raise ValueError('Unexpected MOS count in reference pairing')
    parent = {}

    def find(node):
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left, right):
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for line in logical_cards(ideal):
        words = line.split()
        if words and words[0][0].upper() == 'R' and not line.startswith('.'):
            union(words[1], words[2])

    root_to_ref = {}
    ref_to_root = {}
    for current, original in zip(a, b):
        if current[0] != original[0] or current[5:] != original[5:]:
            raise ValueError('MOS device differs between reference and RC')
        for node, equivalent in zip(current[1:5], original[1:5]):
            group = find(node)
            if group in root_to_ref and root_to_ref[group] != equivalent:
                raise ValueError('RC resistor component merges Phase 2 nets: '
                                 f'{root_to_ref[group]} vs {equivalent}')
            if equivalent in ref_to_root and ref_to_root[equivalent] != group:
                raise ValueError(f'Phase 2 net {equivalent} split across RC components')
            root_to_ref[group] = equivalent
            ref_to_root[equivalent] = group
    return {node: root_to_ref[find(node)] for node in parent
            if find(node) in root_to_ref}


def rc_node_map(ideal):
    """Replicate bind_rc_deck's deterministic, lossless node names."""
    names = set(EXPECTED_PINS)
    for line in logical_cards(ideal):
        if line.startswith('.'):
            continue
        parts = line.split()
        names.update(parts[1:5] if parts[0][0].upper() == 'X' else parts[1:3])
    names.discard('0')
    public = {p: re.sub(r'^(ADDR|DATA)\[(\d+)\]$', r'\1\2', p)
              for p in EXPECTED_PINS}
    internal = {p: f'rc{i}' for i, p in
                enumerate(sorted(names - set(EXPECTED_PINS)))}
    return {**internal, **public}


def capacitance_audit(ideal, count=30):
    totals = defaultdict(float)
    groups = defaultdict(float)
    elements = 0
    for line in logical_cards(ideal):
        if not line or line[0].upper() != 'C':
            continue
        _, a, b, raw = line.split()[:4]
        f = float(raw)
        if f < 0 or not math.isfinite(f):
            raise ValueError('Invalid cap')
        elements += 1
        if f == 0:
            continue
        totals[a] += f
        totals[b] += f
        kind = ('rail' if a in ('VDD', 'VSS') else 'signal') + '_to_' + (
            'rail' if b in ('VDD', 'VSS') else 'signal')
        groups[kind] += f
    return {'positive_capacitor_pairs': elements,
            'group_capacitance_pf': {k: v * 1e12 for k, v in sorted(groups.items())},
            'top_node_incident_capacitance_ff': [
                {'node': node, 'ff': round(value * 1e15, 5)}
                for node, value in sorted(totals.items(), key=lambda x: -x[1])
                if node not in ('VDD', 'VSS')][:count]}


def probe_deck(template, corner, nodes, stop_ns):
    if not 164 <= stop_ns <= 370:
        raise ValueError('Probe must include both initial reads')
    deck = prepare_deck(template, corner, 10.)
    lines = deck.splitlines()
    saves = [i for i, x in enumerate(lines) if x.startswith('.save ')]
    outputs = [i for i, x in enumerate(lines) if x.startswith('wrdata waveform.dat ')]
    transients = [i for i, x in enumerate(lines) if x == 'tran 10p 370n 0 10p']
    if len(saves) != 1 or len(outputs) != 1 or len(transients) != 1:
        raise ValueError('Changed source benchmark structure')
    extra = [f'v(xdut.{node})' for node in nodes]
    signals = [*PUBLIC, *extra]
    lines[saves[0]] = '.save ' + ' '.join(signals)
    lines[outputs[0]] = 'wrdata waveform.dat ' + ' '.join(signals)
    lines[transients[0]] = f'tran 10p {stop_ns:g}n 0 10p'
    return '\n'.join(lines) + '\n'


def parse_samples(path, nodes, samples_ns):
    with path.open() as f:
        header = next(f).split()
        expected = ['time', *(p.lower() for p in PUBLIC),
                    *(f'v(xdut.{n})'.lower() for n in nodes)]
        actual = [p.lower() for p in header]
        if actual[-len(nodes)-1] == 'vdd_src#branch':
            actual[-len(nodes)-1] = 'i(vdd_src)'
        if actual != expected:
            raise ValueError(f'Unexpected internal waveform columns: {header}')
        records = [tuple(map(float, line.split())) for line in f if line.strip()]
    if not records or records[-1][0] < max(samples_ns)*1e-9:
        raise ValueError('Incomplete diagnostic transient')
    return [{"time_ns": ns, "data_volts": [round(at(records, ns*1e-9, i), 5)
                                             for i in range(2, 10)],
             "probes_volts": {n: round(at(records, ns*1e-9, 12+i), 5)
                              for i, n in enumerate(nodes)}}
            for ns in samples_ns]


def run_probe(args):
    check_baseline()
    extraction = args.extract_run.resolve(strict=True)
    provenance = json.loads((extraction / 'manifest.json').read_text())
    if (provenance.get('status') != 'PASS_RC_NETLIST_STRUCTURE' or
            provenance.get('rc_profile') != 'all' or
            provenance.get('gds_sha256') != EXPECTED_GDS):
        raise ValueError('Expected pinned full RC extraction')
    if any(sha256(extraction / k) != v for k, v in provenance['artifacts'].items()):
        raise ValueError('Changed extraction source')
    ideal, _ = idealize_supply_mesh((extraction / 'extracted_rc.spice').read_text())
    binding, _ = bind_rc_deck(ideal)
    source_ref = (QUAL / 'binding.spice').read_text()
    pairs = reference_node_map(ideal, source_ref)
    names = rc_node_map(ideal)
    if any(n not in names or n not in pairs for n in PROBES):
        raise ValueError('Missing expected internal nets')

    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    target = args.output_root.resolve() / run_id
    target.mkdir(parents=True, exist_ok=False)
    audit = capacitance_audit(ideal)
    output = {'status': 'RUNNING', 'run_id': run_id,
              'qualification': 'DIAGNOSTIC_ONLY_NOT_TIMING_POWER_SIGNOFF',
              'gds_sha256': EXPECTED_GDS,
              'extraction_manifest_sha256': sha256(extraction / 'manifest.json'),
              'extracted_spice_sha256': sha256(extraction / 'extracted_rc.spice'),
              'baseline_spice_sha256': sha256(QUAL / 'binding.spice'),
              'bench_sha256': sha256(QUAL / 'bench.spice'),
              'corner': 'tt', 'temp_c': 27, 'vdd_v': 1.8, 'load_ff': 10,
              'stop_ns': args.stop_ns, 'capacitance_audit': audit,
              'internal_probe_map': {n: {'pex': names[n], 'phase2': pairs[n]}
                                     for n in PROBES}, 'sides': {}}
    try:
        for side, netlist, selected in (
                ('phase2_control', source_ref, [pairs[n] for n in PROBES]),
                ('ideal_supply_rc', binding, [names[n] for n in PROBES])):
            folder = target / side
            folder.mkdir()
            (folder / 'binding.spice').write_text(netlist)
            (folder / 'fabric.spice').write_text('* Flat MOS circuit\n')
            (folder / 'bench.spice').write_text(probe_deck(
                (QUAL / 'bench.spice').read_text(), 'tt', selected, args.stop_ns))
            with (folder / 'ngspice.log').open('wb') as log:
                subprocess.run([args.ngspice, '-n', '-b', 'bench.spice'], cwd=folder,
                               stdout=log, stderr=subprocess.STDOUT,
                               timeout=args.timeout, check=True)
            output['sides'][side] = {
                'samples': parse_samples(folder / 'waveform.dat',
                                         selected, SAMPLES_NS),
                'artifacts': {p.name: sha256(p) for p in folder.iterdir()}}
        output['status'] = 'COMPLETE_DIAGNOSTIC'
    except Exception as exc:
        output['status'] = 'FAIL_DIAGNOSTIC'
        output['error'] = str(exc)
    (target / 'manifest.json').write_text(json.dumps(output, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'run': str(target), 'status': output['status'],
                      'error': output.get('error')}))
    return 0 if output['status'] == 'COMPLETE_DIAGNOSTIC' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extract-run', type=Path, required=True)
    parser.add_argument('--output-root', type=Path,
                        default=ROOT / 'build/phase3/probe_runs')
    parser.add_argument('--stop-ns', type=float, default=170)
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--ngspice', default='ngspice')
    return run_probe(parser.parse_args())


if __name__ == '__main__':
    sys.exit(main())
