#!/usr/bin/env python3
"""Run isolated ngspice negative controls for integrated write-bus ownership.

The FF c2 and c10 slices preserve the original PEX, models and original
stimulus outside the deliberately injected fault. These do not qualify P2.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

import numpy as np

from phase3_rc_read_path import OUTPUT_ENABLES, LOW


ROOT = Path('/work')
SOURCE_ROOT = ROOT / 'build/phase3/integrated_replay_247p5'
LOCK = ROOT / 'build/phase3/.eco_simulator.lock'
INPUT_FILES = ('bench.spice', 'binding.spice', 'buf_1.spice', 'fabric.spice',
               'fixture.json', 'probes.json', 'preflight.json', 'model_hashes.json')
CURRENT_LIMIT = 50e-6
CONTROL_WINDOWS = {
    'no_host': (2, 70., 48.2, 48.8),
    'contention': (2, 70., 48.2, 49.05),
    'c10_no_host': (10, 230., 208.7, 209.3),
    'c10_contention': (10, 211., 208.8, 209.5),
    'c10_stuck_weak': (10, 211., 208.8, 209.5),
    'c10_delayed_release': (10, 211., 208.8, 209.45),
}


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def change_deck(text: str, mode: str) -> str:
    cycle, stop_ns, _, _ = CONTROL_WINDOWS[mode]
    assert text.count('tran 10p 370n 0 25p') == 1
    text = text.replace('tran 10p 370n 0 25p', f'tran 10p {stop_ns:g}n 0 25p')
    if mode.endswith('no_host'):
        if cycle == 2:
            text, n = re.subn(r'^V_HOST_EN HOST_EN 0 PWL\([^\n]+\)$',
                              'V_HOST_EN HOST_EN 0 PWL(0n 0 70n 0)',
                              text, count=1, flags=re.M)
            assert n == 1
        else:
            original = ('208.500000n 0 208.550000n 1.8 '
                        '226.500000n 1.8 226.550000n 0')
            disabled = ('208.500000n 0 208.550000n 0 '
                        '226.500000n 0 226.550000n 0')
            assert text.count(original) == 1
            text = text.replace(original, disabled, 1)
    elif mode == 'c10_stuck_weak':
        original = '208.400000n 1.8 208.450000n 0 241.500000n 0'
        extended = ('208.400000n 1.8 208.450000n 1.8 '
                    '209.550000n 1.8 209.600000n 0 241.500000n 0')
        assert text.count(original) == 1
        text = text.replace(original, extended, 1)
    elif mode == 'c10_delayed_release':
        # Keep the preceding read's OEb/WEb controls active until well after
        # the strong host engages. This checks real DUT drive contention.
        old_oe = '207n 0 207.05n 1.8 227n 1.8'
        new_oe = '207n 0 207.05n 0 209.50n 0 209.55n 1.8 227n 1.8'
        old_we = '207n 1.8 207.05n 0 227n 0'
        new_we = '207n 1.8 207.05n 1.8 209.50n 1.8 209.55n 0 227n 0'
        for signal, old, new in (('OEb', old_oe, new_oe),
                                 ('WEb', old_we, new_we)):
            pattern = rf'^V_{signal} [^\n]+$'
            lines = re.findall(pattern, text, flags=re.M)
            assert len(lines) == 1 and lines[0].count(old) == 1
            text = text.replace(lines[0], lines[0].replace(old, new, 1), 1)
    elif mode.endswith('contention'):
        # Bit 4 of 0xAA is zero in c2 and c10. Deliberately drive it high
        # from an independent source after the host turns on.
        if cycle == 2:
            times = ('48.10n 0 48.15n 1.8 49.10n 1.8 49.15n 0')
        else:
            times = ('208.65n 0 208.70n 1.8 209.70n 1.8 209.75n 0')
        fault = ('V_FAULT_SUPPLY4 FAULT_SUPPLY4 0 1.8\n'
                 f'V_FAULT_EN4 FAULT_EN4 0 PWL(0n 0 {times} {stop_ns:g}n 0)\n'
                 'R_FAULT4 FAULT_SUPPLY4 FAULT_R4 300\n'
                 'S_FAULT4 FAULT_R4 FAULT_METER4 FAULT_EN4 0 HOST_SWITCH\n'
                 # Inject on the macro side of the DUT current sensor.
                 # The existing reviewer observes the HOST4 / DUT4 opposition.
                 'v_sense_fault4 FAULT_METER4 DUT_DATA4 0\n')
        assert text.count('.save ') == 1 and text.count('wrdata waveform.dat ') == 1
        text = text.replace('.save ', fault + '.save v(FAULT_EN4) i(v_sense_fault4) ', 1)
        text = text.replace('wrdata waveform.dat ',
                            'wrdata waveform.dat v(FAULT_EN4) i(v_sense_fault4) ', 1)
    else:
        raise ValueError(f'Unknown control: {mode}')
    return text


def check_witness(wave: Path, mode: str) -> dict:
    cycle, stop_ns, window_start, window_end = CONTROL_WINDOWS[mode]
    with wave.open() as stream:
        columns = stream.readline().lower().split()
    names = ['time', 'v(host_en)', 'i(v_sense_host4)']
    if mode.endswith('contention'):
        names += ['i(v_dut4)', 'v(fault_en4)', 'i(v_sense_fault4)']
    elif mode == 'c10_stuck_weak':
        names += ['v(host_weak_en)']
    elif mode == 'c10_delayed_release':
        probes = json.loads((wave.parent / 'probes.json').read_text())
        names += ['i(v_dut4)', f'v(xdut.{probes[OUTPUT_ENABLES[4]]})'.lower()]
    assert all(name in columns for name in names) and len(set(columns)) == len(columns)
    sample = np.loadtxt(wave, skiprows=1,
                        usecols=[columns.index(name) for name in names], ndmin=2)
    times = sample[:, 0] * 1e9
    assert sample.ndim == 2 and np.isfinite(sample).all()
    assert np.all(np.diff(times) > 0) and abs(times[-1] - stop_ns) < 1e-5
    window = (times >= window_start) & (times <= window_end)
    points = sample[window]
    local_times = times[window]
    assert len(points) >= 3
    if mode == 'c10_stuck_weak':
        qualifying = (points[:, 1] >= 1.0) & (points[:, 3] >= 1.0)
        reason = 'weak host remains enabled while strong host drives after read-to-write'
    elif mode == 'c10_delayed_release':
        host, macro = points[:, 2], points[:, 3]
        qualifying = ((points[:, 1] >= 1.0) & (points[:, 4] <= LOW)
                      & (np.abs(host) > CURRENT_LIMIT) & (np.abs(macro) > CURRENT_LIMIT)
                      & (host * macro < 0))
        reason = 'macro read driver remains enabled and opposes strong write host after c10 handoff'
    elif mode.endswith('no_host'):
        qualifying = (np.abs(points[:, 1]) < .8) & (np.abs(points[:, 2]) < CURRENT_LIMIT)
        reason = 'host disabled and measured branch current below 50 uA'
    else:
        host, macro, fault = points[:, 2], points[:, 3], points[:, 5]
        qualifying = ((points[:, 1] >= 1.0) & (points[:, 4] >= 1.0)
                      & (np.abs(host) > CURRENT_LIMIT)
                      & (np.abs(macro) > CURRENT_LIMIT)
                      & (np.abs(fault) > CURRENT_LIMIT)
                      & (host * macro < 0) & (host * fault < 0))
        reason = 'opposing host and macro-sense currents exceed 50 uA'
    longest_ns, largest_samples, first_ns, last_ns = 0., 0, None, None
    start = None
    for index in range(len(qualifying) + 1):
        active = index < len(qualifying) and qualifying[index]
        if active and start is None:
            start = index
        if not active and start is not None:
            end = index - 1
            duration = float(local_times[end] - local_times[start])
            if duration > longest_ns:
                longest_ns, largest_samples = duration, end - start + 1
                first_ns, last_ns = float(local_times[start]), float(local_times[end])
            start = None
    detected = largest_samples >= 3 and longest_ns >= .05
    return {
        'fault_detected': bool(detected), 'reason': reason,
        'cycle': cycle, 'window_ns': [window_start, window_end],
        'current_threshold_a': CURRENT_LIMIT, 'minimum_witness_ps': 50.,
        'qualifying_samples': largest_samples,
        'conservative_witness_ps': longest_ns * 1000,
        'witness_first_ns': first_ns, 'witness_last_ns': last_ns,
        'host_current_min_a': float(points[:, 2].min()),
        'host_current_max_a': float(points[:, 2].max()),
        'macro_current_min_a': float(points[:, 3].min()) if mode.endswith('contention') or mode == 'c10_delayed_release' else None,
        'macro_current_max_a': float(points[:, 3].max()) if mode.endswith('contention') or mode == 'c10_delayed_release' else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=CONTROL_WINDOWS)
    parser.add_argument('--corner', choices=('TT', 'SS', 'FF'), default='FF')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--timeout', type=int, default=3600)
    args = parser.parse_args()
    output = args.output.resolve()
    source = SOURCE_ROOT / args.corner
    cycle, stop_ns, window_start, window_end = CONTROL_WINDOWS[args.mode]
    source_hashes = {name: digest(source / name) for name in INPUT_FILES}
    baseline_receipt = json.loads((source / 'simulation.json').read_text())
    baseline_wave = source / 'waveform.dat'
    assert baseline_receipt['status'] == 'COMPLETED'
    assert baseline_receipt['returncode'] == 0
    assert baseline_receipt['waveform_sha256'] == digest(baseline_wave)
    assert baseline_receipt['model_check']['sha256_matches'] == 319
    assert source_hashes['binding.spice'] == 'd2151cac96a35a99b200764eec6ebbea517915d413cc1ddb8664a1dc7e247227'
    fixture = json.loads((source / 'fixture.json').read_text())
    assert fixture['cycles'][cycle]['expected'] == 170
    assert fixture['cycles'][cycle]['previous_operation'] == ('read' if cycle == 10 else 'idle')
    model_hashes = json.loads((source / 'model_hashes.json').read_text())
    assert len(model_hashes) == 319 and all(digest(Path(p)) == expected
                                           for p, expected in model_hashes.items())

    output.mkdir(parents=True, exist_ok=False)
    for name in INPUT_FILES:
        if name != 'bench.spice':
            shutil.copyfile(source / name, output / name)
    (output / 'bench.spice').write_text(change_deck((source / 'bench.spice').read_text(), args.mode))
    manifest = {
        'mode': args.mode, 'corner': args.corner.lower(), 'cycle': cycle,
        'simulation_target_ns': stop_ns,
        'witness_window_ns': [window_start, window_end],
        'source_run': str(source), 'source_hashes': source_hashes,
        'source_receipt_sha256': digest(source / 'simulation.json'),
        'source_waveform_sha256': baseline_receipt['waveform_sha256'],
        'changed_deck_sha256': digest(output / 'bench.spice'),
        'model_count_verified': len(model_hashes),
        'purpose': 'physical_negative_control_only',
    }
    write_json(output / 'control_manifest.json', manifest)
    cmd = ['/opt/ngspice/ngspice-44.2/bin/ngspice', '-n', '-b', 'bench.spice']
    started = time.monotonic()
    with LOCK.open('a') as guard:
        fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (output / 'ngspice.log').open('xb') as log:
            try:
                proc = subprocess.run(cmd, cwd=output, stdout=log, stderr=subprocess.STDOUT,
                                      timeout=args.timeout, check=False)
                exit_code, failure = proc.returncode, None
            except subprocess.TimeoutExpired:
                exit_code, failure = None, 'TIMEOUT'
    wave = output / 'waveform.dat'
    log_text = (output / 'ngspice.log').read_text(errors='replace')
    errors = re.findall(r'^\s*(?:Error:|Fatal:|.*analysis aborted).*', log_text,
                        re.I | re.M)
    diagnostic = check_witness(wave, args.mode) if exit_code == 0 and wave.is_file() else None
    receipt = {
        'status': 'COMPLETED' if exit_code == 0 and not errors and diagnostic else 'INCONCLUSIVE',
        'corner': args.corner.lower(), 'mode': args.mode,
        'returncode': exit_code, 'failure': failure,
        'elapsed_s': round(time.monotonic() - started, 3),
        'errors': errors[:5], 'witness': diagnostic,
        'negative_control_rejected': diagnostic['fault_detected'] if diagnostic else False,
        'waveform_sha256': digest(wave) if wave.is_file() else None,
        'ngspice_log_sha256': digest(output / 'ngspice.log'),
        'deck_sha256': manifest['changed_deck_sha256'],
        'electrical_qualification': 'NOT_CHARACTERIZED',
    }
    write_json(output / 'control_receipt.json', receipt)
    print(json.dumps(receipt, indent=2))
    if receipt['status'] != 'COMPLETED' or not receipt['negative_control_rejected']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
