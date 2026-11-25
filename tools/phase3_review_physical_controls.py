#!/usr/bin/env python3
"""Cross-check physical-fault slices against the unchanged bus observer.

The original 370 ns evidence and the isolated control receipts are inputs.
The report distinguishes a detected physical fault from the observer verdict.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from phase3_bus_physical_controls import CONTROL_WINDOWS, INPUT_FILES, digest
from phase3_rc_read_path import OUTPUT_ENABLES
from review_phase3_bus_ss import Trace, inspect_strong

REPO_ROOT = Path(__file__).resolve().parent.parent


def examine(run: Path) -> dict:
    run = run.resolve(strict=True)
    receipt_path = run / 'control_receipt.json'
    manifest_path = run / 'control_manifest.json'
    receipt = json.loads(receipt_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    mode = receipt['mode']
    cycle, stop_ns, start_ns, end_ns = CONTROL_WINDOWS[mode]

    if (manifest['mode'] != mode or manifest['cycle'] != cycle
            or receipt['corner'] != manifest['corner']
            or receipt['status'] != 'COMPLETED' or receipt['returncode'] != 0
            or receipt['errors'] or not receipt['negative_control_rejected']
            or not receipt['witness']['fault_detected']
            or manifest['model_count_verified'] != 319
            or manifest['changed_deck_sha256'] != digest(run / 'bench.spice')
            or receipt['deck_sha256'] != manifest['changed_deck_sha256']
            or receipt['waveform_sha256'] != digest(run / 'waveform.dat')
            or receipt['ngspice_log_sha256'] != digest(run / 'ngspice.log')):
        raise ValueError(f'Invalid physical control provenance: {run}')

    # The receipts were generated in the EDA container, where /work is this
    # repository. Resolve that mount before verifying host-side hashes.
    container_source = Path(manifest['source_run'])
    source = (REPO_ROOT / container_source.relative_to('/work')
              if container_source.is_relative_to('/work') else container_source)
    if (manifest['source_receipt_sha256'] != digest(source / 'simulation.json')
            or manifest['source_waveform_sha256'] != digest(source / 'waveform.dat')
            or any(manifest['source_hashes'][name] != digest(source / name)
                   for name in INPUT_FILES)):
        raise ValueError(f'Control source no longer matches pinned 370 ns replay: {run}')

    probes = json.loads((run / 'probes.json').read_text())
    names = ['time', 'v(HOST_EN)', 'v(HOST_WEAK_EN)']
    for bit, label in enumerate(OUTPUT_ENABLES):
        names.extend((f'i(v_sense_host{bit})', f'i(v_dut{bit})',
                      f'i(v_sense_weak{bit})', f'v(DATA{bit})',
                      f'v(xdut.{probes[label]})'))
    with (run / 'waveform.dat').open() as stream:
        header = stream.readline().lower().split()
    if len(header) != len(set(header)) or any(name.lower() not in header for name in names):
        raise ValueError(f'Missing or duplicate required native waveform vectors: {run}')
    values = np.loadtxt(run / 'waveform.dat', skiprows=1,
                        usecols=[header.index(name.lower()) for name in names], ndmin=2)
    if (not np.isfinite(values).all() or not np.all(np.diff(values[:, 0]) > 0)
            or abs(values[-1, 0] * 1e9 - stop_ns) > 1e-5):
        raise ValueError(f'Incomplete physical control waveform: {run}')
    trace = Trace(values, {name: i for i, name in enumerate(names)})
    for label in OUTPUT_ENABLES:
        trace.cols[label] = trace.cols[f'v(xdut.{probes[label]})']

    # No payload witness is requested here: the physical control tests only
    # whether the original strong-host isolation criterion accepts the fault.
    observed = inspect_strong(trace, start_ns, end_ns)
    original_verdict = ('FAIL' if observed['overlap'] else
                        'PASS' if observed['isolated'] else 'INCONCLUSIVO')
    if original_verdict == 'PASS':
        raise ValueError(f'Original observer incorrectly accepts physical fault: {run}')

    lanes = [dict(bit=lane['bit'], disabled_gate=lane['disabled_gate'],
                  strong_host_on=lane['strong_host_on'],
                  sustained_opposition=bool(lane['sustained_opposition']),
                  opposition_with_gate_off=bool(lane['opposition_with_gate_off']),
                  quiet_suffix=bool(lane['quiet_suffix'])) for lane in observed['bits']]
    return dict(run=str(run), corner=receipt['corner'], cycle=cycle, mode=mode,
                status=receipt['status'], injected_fault_detected=True,
                original_observer_verdict=original_verdict,
                original_observer_rejects_pass=True,
                original_observer_weak_off=observed['weak_host_off'],
                original_observer_overlap=observed['overlap'],
                lanes=lanes, witness=receipt['witness'],
                source_waveform_sha256=manifest['source_waveform_sha256'],
                control_waveform_sha256=receipt['waveform_sha256'],
                receipt_sha256=digest(receipt_path), manifest_sha256=digest(manifest_path))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', nargs='+', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = {'scope': 'diagnostic_negative_controls_only',
              'electrical_qualification': 'NOT_CHARACTERIZED',
              'controls': [examine(run) for run in args.runs]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    for control in report['controls']:
        print(control['corner'], control['cycle'], control['mode'],
              control['original_observer_verdict'])


if __name__ == '__main__':
    main()
