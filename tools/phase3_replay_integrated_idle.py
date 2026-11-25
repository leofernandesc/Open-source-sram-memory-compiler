#!/usr/bin/env python3
"""Run pinned 370 ns virtual-eight integrated fixtures with isolated receipts.

Run inside ./tools/sram-eda so the absolute model paths resolve in the EDA image.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import time


ROOT = Path('/work')
INPUT = ROOT / 'build/phase3/integrated_idle_247p5'
OUTPUT = ROOT / 'build/phase3/integrated_replay_247p5'
PEX = 'a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f'
GDS = '315c2ebceb2bc4cf258fa63be2279843805db3010637d0c273aea9db12813e37'
BINDING = 'd2151cac96a35a99b200764eec6ebbea517915d413cc1ddb8664a1dc7e247227'


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def validate(folder: Path, corner: str) -> dict:
    pre = json.loads((folder / 'preflight.json').read_text())
    assert pre['gate'] == 'READY' and pre['topology'] == 'VIRTUAL_ECO_READY'
    assert pre['corner'] == pre['conditions']['corner'] == corner.lower()
    assert pre['physical_pex_sha256'] == PEX and pre['gds_sha256'] == GDS
    assert pre['c250_virtual_binding_sha256'] == BINDING
    assert pre['guard_ns'] == 1.5 and pre['stop_ns'] == 370
    assert pre['conditions']['maximum_step_ps'] == 25
    assert pre['c12_idle_start_ns'] == 247.5
    assert set(pre['outputs']) == {
        'bench.spice', 'binding.spice', 'buf_1.spice', 'fabric.spice',
        'model_hashes.json', 'fixture.json', 'probes.json', 'internals.json',
    }
    for name, expected in pre['outputs'].items():
        assert sha(folder / name) == expected, f'input changed: {name}'
    assert pre['outputs']['binding.spice'] == BINDING
    deck = (folder / 'bench.spice').read_text()
    assert f'.lib "/opt/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice" {corner.lower()}' in deck
    assert deck.count('tran 10p 370n 0 25p') == 1
    for source in ('V_CSb', 'V_OEb'):
        line, = (line for line in deck.splitlines() if line.startswith(source + ' '))
        assert line.count('247.5n 0 247.55n 1.8') == 1, source
    records = json.loads((folder / 'fixture.json').read_text())['cycles']
    assert len(records) == 18 and [r['cycle'] for r in records] == list(range(18))
    assert [sum(r['operation'] == op for r in records) for op in ('read', 'write', 'idle')] == [9, 6, 3]
    assert records[12]['operation'] == 'idle' and records[12]['control_start_ns'] == 247.5
    assert records[12]['rise_ns'] == 250
    return pre


def check_models(folder: Path) -> dict:
    manifest = json.loads((folder / 'model_hashes.json').read_text())
    assert len(manifest) == 319, f'wrong model closure size: {len(manifest)}'
    for name, expected in manifest.items():
        assert sha(Path(name)) == expected, f'model closure mismatch: {name}'
    return {'sha256_matches': len(manifest), 'manifest_sha256': sha(folder / 'model_hashes.json')}


def prepare(corner: str) -> Path:
    source, destination = INPUT / corner, OUTPUT / corner
    pre = validate(source, corner)
    check_models(source)
    destination.mkdir(parents=True, exist_ok=False)
    for name in pre['outputs']:
        shutil.copyfile(source / name, destination / name)
    shutil.copyfile(source / 'preflight.json', destination / 'preflight.json')
    shutil.copyfile(source / 'eco_audit.json', destination / 'eco_audit.json')
    validate(destination, corner)
    assert sha(destination / 'preflight.json') == sha(source / 'preflight.json')
    return destination


def execute(folder: Path, corner: str, wall_timeout: int, validator=None) -> dict:
    pre = (validator or validate)(folder, corner)
    models = check_models(folder)
    command = ['stdbuf', '-o0', '-e0', '/opt/ngspice/ngspice-44.2/bin/ngspice', '-n', '-b', 'bench.spice']
    begin = time.monotonic()
    with (ROOT / 'build/phase3/.eco_simulator.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        (folder / 'attempt.json').write_text(json.dumps({
            'command': command, 'timeout_s': wall_timeout,
            'model_check': models, 'preflight_sha256': sha(folder / 'preflight.json'),
            'expected_ns': 370, 'corner': corner.lower(),
        }, indent=2) + '\n')
        env = {**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'}
        exit_code, termination = None, 'PROCESS_EXIT'
        with (folder / 'ngspice.log').open('xb') as stream:
            with subprocess.Popen(command, cwd=folder, stdin=subprocess.DEVNULL,
                                  stdout=stream, stderr=subprocess.STDOUT, env=env,
                                  start_new_session=True) as proc:
                print(f'START {corner}: pid={proc.pid} run={folder}', flush=True)
                try:
                    exit_code = proc.wait(timeout=wall_timeout)
                except subprocess.TimeoutExpired:
                    termination = 'TIMEOUT'
                    os.killpg(proc.pid, signal.SIGTERM)
                    try:
                        exit_code = proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        exit_code = proc.wait()
    waveform = folder / 'waveform.dat'
    currents = folder / 'currents.dat'
    horizon = None
    if waveform.exists():
        with waveform.open('rb') as stream:
            last = b''
            for row in stream:
                if row.strip():
                    last = row
        try:
            horizon = float(last.split()[0]) * 1e9
        except (ValueError, IndexError):
            pass
    log = (folder / 'ngspice.log').read_bytes()
    errors = re.findall(rb'^\s*(?:Error:|Fatal:|.*analysis aborted).*', log, re.I | re.M)
    progress = re.findall(rb'Reference value\s*:\s*(\S+)', log)
    complete = (exit_code == 0 and horizon is not None
                and math.isclose(horizon, 370, abs_tol=1e-5) and not errors
                and currents.is_file())
    receipt = {
        'status': 'COMPLETED' if complete else 'INCONCLUSIVE',
        'corner': corner.lower(), 'electrical_qualification': 'NOT_CHARACTERIZED',
        'elapsed_s': time.monotonic() - begin, 'simulation_ns': horizon,
        'returncode': exit_code, 'termination': termination,
        'peak_rss_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        'model_check': models, 'preflight_sha256': sha(folder / 'preflight.json'),
        'preflight_outputs_verified': all(sha(folder / name) == digest for name, digest in pre['outputs'].items()),
        'last_progress_ns': float(progress[-1]) * 1e9 if progress else None,
        'log_sha256': sha(folder / 'ngspice.log'),
        'waveform_sha256': sha(waveform) if waveform.exists() else None,
        'currents_sha256': sha(currents) if currents.exists() else None,
        'errors': [item.decode(errors='replace') for item in errors[:8]],
    }
    (folder / 'simulation.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k not in ('model_check',)}, indent=2), flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corner', choices=('TT', 'SS', 'FF', 'all'))
    parser.add_argument('--timeout', type=int, default=3600)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    for corner in ('TT', 'SS', 'FF') if args.corner == 'all' else (args.corner,):
        source = INPUT / corner
        validate(source, corner)
        models = check_models(source)
        print(f'PREFLIGHT {corner}: PEX={PEX} idle=247.5 ns models={models["sha256_matches"]}', flush=True)
        if not args.check_only:
            folder = prepare(corner)
            receipt = execute(folder, corner, args.timeout)
            if receipt['status'] != 'COMPLETED':
                raise SystemExit(f'Simulator incomplete for {corner}')


if __name__ == '__main__':
    main()
