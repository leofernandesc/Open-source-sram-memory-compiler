#!/usr/bin/env python3
"""Measure provisional full-cycle supply energy from pinned integrated PEX replays.

The measurement includes clock, precharge and leakage. It does not establish
static power, standalone idle power, power arcs or electrical qualification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def energy_window(time_s: np.ndarray, power_w: np.ndarray,
                  begin_s: float, end_s: float) -> float:
    boundary_tolerance_s = 1e-14
    require(end_s > begin_s
            and begin_s >= time_s[0] - boundary_tolerance_s
            and end_s <= time_s[-1] + boundary_tolerance_s,
            'Energy window is outside the available waveform')
    begin_s = max(begin_s, float(time_s[0]))
    end_s = min(end_s, float(time_s[-1]))
    inner = (time_s > begin_s) & (time_s < end_s)
    times = np.concatenate(([begin_s], time_s[inner], [end_s]))
    powers = np.concatenate(([np.interp(begin_s, time_s, power_w)],
                             power_w[inner], [np.interp(end_s, time_s, power_w)]))
    return float(np.trapz(powers, times))


def analyze(run: Path) -> dict:
    run = run.resolve(strict=True)
    receipt = json.loads((run / 'simulation.json').read_text())
    fixture = json.loads((run / 'fixture.json').read_text())
    preflight = json.loads((run / 'preflight.json').read_text())
    require(receipt['status'] == 'COMPLETED' and receipt['returncode'] == 0
            and not receipt['errors'] and receipt['simulation_ns'] == 370,
            'Simulation must be complete and error-free')
    require(receipt['model_check']['sha256_matches'] == 319
            and receipt['preflight_outputs_verified'] is True,
            'Pinned model or input closure missing')
    require(preflight['gate'] == 'READY' and preflight['stop_ns'] == 370
            and preflight['c12_idle_start_ns'] == 247.5,
            'Unrecognized replay preflight or idle profile')
    require(digest(run / 'preflight.json') == receipt['preflight_sha256']
            and digest(run / 'model_hashes.json') == receipt['model_check']['manifest_sha256']
            and digest(run / 'waveform.dat') == receipt['waveform_sha256']
            and digest(run / 'ngspice.log') == receipt['log_sha256']
            and digest(run / 'currents.dat') == receipt['currents_sha256'],
            'Simulation receipt does not match the actual evidence')
    require(all(digest(run / name) == expected
                for name, expected in preflight['outputs'].items()),
            'A pinned input artifact changed')
    deck = (run / 'bench.spice').read_text()
    require(sum(line.upper().startswith('VDD_SRC ') for line in deck.splitlines()) == 1,
            'Power source VDD_SRC is missing or ambiguous')

    with (run / 'waveform.dat').open() as source:
        header = [name.lower() for name in source.readline().split()]
    probes = ('time', 'v(vdd)', 'i(vdd_src)')
    require(all(header.count(name) == 1 for name in probes),
            'Unique supply voltage, source current and time probes are required')
    columns = [header.index(name) for name in probes]
    samples = np.loadtxt(run / 'waveform.dat', skiprows=1,
                         usecols=columns, ndmin=2)
    time_s, voltage_v, current_a = samples.T
    require(len(time_s) >= 4 and np.isfinite(samples).all()
            and np.all(np.diff(time_s) > 0)
            and abs(time_s[-1] - 370e-9) < 1e-14,
            'Native waveform is incomplete or invalid')

    records = fixture['cycles']
    require(len(records) == 18 and [row['cycle'] for row in records] == list(range(18))
            and [sum(row['operation'] == op for row in records)
                 for op in ('read', 'write', 'idle')] == [9, 6, 3],
            'Unexpected integrated 18-cycle fixture')
    power_w = -voltage_v * current_a
    cycles = []
    for record in records:
        if record['cycle'] < 2:
            continue  # Supply start-up / memory initialization: no idle metric.
        begin_s = record['rise_ns'] * 1e-9
        end_s = begin_s + 20e-9
        joules = energy_window(time_s, power_w, begin_s, end_s)
        require(np.isfinite(joules), f'Non-finite energy in cycle {record["cycle"]}')
        cycles.append(dict(cycle=record['cycle'], operation=record['operation'],
                           start_ns=record['rise_ns'], end_ns=record['rise_ns'] + 20,
                           energy_j=joules, average_power_w=joules / (20e-9)))

    groups = {}
    for operation in ('read', 'write'):
        energies = [row['energy_j'] for row in cycles if row['operation'] == operation]
        require(len(energies) == {'read': 9, 'write': 6}[operation],
                f'Missing {operation} cycles')
        groups[operation] = dict(count=len(energies), mean_full_cycle_energy_j=float(np.mean(energies)),
                                 mean_full_cycle_power_w=float(np.mean(energies)) / 20e-9,
                                 min_energy_j=min(energies), max_energy_j=max(energies))

    return dict(status='PROVISIONAL', electrical_qualification='NOT_CHARACTERIZED',
                corner=preflight['corner'], topology=preflight['topology'],
                physical_pex_sha256=preflight['physical_pex_sha256'],
                gds_sha256=preflight['gds_sha256'],
                simulation_receipt_sha256=digest(run / 'simulation.json'),
                waveform_sha256=receipt['waveform_sha256'],
                fixture_sha256=digest(run / 'fixture.json'),
                conditions=dict(supply_source='VDD_SRC', voltage_probe='v(VDD)',
                                current_probe='i(VDD_SRC)', sign='-V*I',
                                cycle_length_ns=20, nominal_vdd_v=1.8,
                                startup_cycles_excluded=[0, 1],
                                note='Full supply cycle including clock, precharge and leakage; no baseline subtraction.'),
                metrics=groups, cycle_results=cycles,
                incomplete_metrics=['P_STATIC', 'qualified P_IDLE', 'Liberty power tables',
                                    'setup/hold', 'SNM post-layout'])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    destination = args.output.resolve()
    if destination.exists() or destination == args.run.resolve() or args.run.resolve() in destination.parents:
        parser.error('Report output must be new and outside the replay input')
    result = analyze(args.run)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x') as output:
        json.dump(result, output, indent=2, allow_nan=False)
        output.write('\n')
    print(result['corner'], result['topology'], result['status'], result['metrics'])


if __name__ == '__main__':
    main()
