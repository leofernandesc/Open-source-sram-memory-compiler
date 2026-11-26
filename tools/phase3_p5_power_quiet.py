#!/usr/bin/env python3
"""Exploratory quiet-state supply runs on the sealed physical v6 PEX."""
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
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'build/phase3/integrated_v6_idle_247p5'
OUTPUT = ROOT / 'build/phase3/p5_power_quiet_v6_fullcycle_20261125'
NGSPICE = '/opt/ngspice/ngspice-44.2/bin/ngspice'
PEX = 'a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f'
BINDING = '3b6f7205476b79d02754ba081a7d2eb2ef9d372670daf26067d3d0cb5745e76d'


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def clamp_pwl(line: str, cut_ns: float) -> str:
    prefix, payload = line.split('PWL(', 1)
    pairs = re.fullmatch(r'(.+)\)', payload).group(1).split()
    assert len(pairs) % 2 == 0
    samples = [(float(pairs[i][:-1]), float(pairs[i + 1])) for i in range(0, len(pairs), 2)]
    assert all(pairs[i].endswith('n') for i in range(0, len(pairs), 2))
    before = [(t, v) for t, v in samples if t <= cut_ns]
    assert before
    t0, v0 = before[-1]
    after = [(t, v) for t, v in samples if t > cut_ns]
    if after:
        t1, v1 = after[0]
        value = v0 if t0 == cut_ns else v0 + (v1 - v0) * (cut_ns - t0) / (t1 - t0)
    else:
        value = v0
    if t0 != cut_ns:
        before.append((cut_ns, value))
    before.append((300.0, value))
    return prefix + 'PWL(' + ' '.join(f'{t:g}n {v:g}' for t, v in before) + ')'


def prepare(corner: str, mode: str, threads: int = 1) -> Path:
    source = SOURCE / corner
    pre = json.loads((source / 'preflight.json').read_text())
    assert pre['gate'] == 'READY' and pre['topology'] == 'PHYSICAL_V6_READY'
    assert pre['physical_pex_sha256'] == PEX and pre['outputs']['binding.spice'] == BINDING
    assert pre['corner'] == corner.lower() and pre['c12_idle_start_ns'] == 247.5
    for name, expected in pre['outputs'].items():
        assert sha(source / name) == expected, name
    assert 1 <= threads <= 16
    destination = OUTPUT / (f'threads{threads}' if threads != 1 else '') / mode / corner
    destination.mkdir(parents=True, exist_ok=False)
    for name in ('binding.spice', 'fabric.spice', 'model_hashes.json'):
        shutil.copyfile(source / name, destination / name)
    lines = []
    for line in (source / 'bench.spice').read_text().splitlines():
        if line.startswith('V_HOST_WEAK_EN '):
            line = clamp_pwl(line, 241.5)
        elif line.startswith('V_') and ' PWL(' in line:
            if line.startswith('V_CLK '):
                if mode == 'static':
                    line = clamp_pwl(line, 260.05)
            else:
                line = clamp_pwl(line, 247.55)
        if line.startswith('.save '):
            line = '.save v(CLK) v(CSb) v(OEb) v(WEb) v(HOST_EN) v(HOST_WEAK_EN) v(VDD) i(VDD_SRC) ' + ' '.join(f'v(DATA{i})' for i in range(8))
        if line.startswith('tran 10p 370n 0 25p'):
            line = 'tran 10p 300n 0 25p'
        if line.startswith('wrdata waveform.dat '):
            line = 'wrdata waveform.dat v(CLK) v(CSb) v(OEb) v(WEb) v(HOST_EN) v(HOST_WEAK_EN) v(VDD) i(VDD_SRC) ' + ' '.join(f'v(DATA{i})' for i in range(8))
        if line.startswith('wrdata currents.dat '):
            continue
        if line == 'set num_threads=1':
            line = f'set num_threads={threads}'
        lines.append(line)
    deck = '\n'.join(lines) + '\n'
    assert deck.count('.include "binding.spice"') == 1
    assert deck.count('v(VDD) i(VDD_SRC)') == 2
    (destination / 'bench.spice').write_text(deck)
    receipt = {
        'status': 'PREPARED', 'mode': mode, 'corner': corner, 'source_preflight_sha256': sha(source / 'preflight.json'),
        'source_deck_sha256': sha(source / 'bench.spice'), 'physical_pex_sha256': PEX,
        'binding_sha256': BINDING, 'input_hashes': {name: sha(destination / name) for name in ('bench.spice', 'binding.spice', 'fabric.spice', 'model_hashes.json')},
        'window_ns': [280, 295] if mode == 'static' else [270, 290],
        'threads': threads, 'qualification': 'PROVISIONAL', 'electrical_qualification': 'NOT_CHARACTERIZED',
    }
    (destination / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return destination


def measure(folder: Path, window: list[int]) -> dict:
    start, stop = (value * 1e-9 for value in window)
    with (folder / 'waveform.dat').open() as stream:
        header = stream.readline().strip().lower().split()
        assert header == ['time', 'v(clk)', 'v(csb)', 'v(oeb)', 'v(web)', 'v(host_en)', 'v(host_weak_en)', 'v(vdd)', 'i(vdd_src)'] + [f'v(data{i})' for i in range(8)], header
        rows = []
        last_time = -1.0
        before = after = None
        for line in stream:
            values = [float(x) for x in line.split()]
            assert len(values) == len(header) and all(math.isfinite(x) for x in values)
            assert values[0] > last_time
            last_time = values[0]
            if values[0] < start:
                before = values
            elif values[0] <= stop:
                rows.append(values)
            elif after is None:
                after = values
    assert last_time >= 300e-9 - 1e-14
    assert len(rows) > 100 and before is not None and after is not None
    def at(edge: float, left: list[float], right: list[float]) -> list[float]:
        fraction = (edge - left[0]) / (right[0] - left[0])
        return [edge] + [a + fraction * (b - a) for a, b in zip(left[1:], right[1:])]
    rows = [at(start, before, rows[0]), *rows, at(stop, rows[-1], after)]
    for index in (2, 3, 4):
        assert min(r[index] for r in rows) >= 1.44, (header[index], 'not idle')
    for index in (5, 6):
        assert max(r[index] for r in rows) <= 0.36, (header[index], 'probe/host active')
    clocks = [r[1] for r in rows]
    if folder.parent.name == 'static':
        assert max(clocks) <= 0.36
    else:
        assert min(clocks) <= 0.36 and max(clocks) >= 1.44
    power = [-r[7] * r[8] for r in rows]
    area = sum((power[i] + power[i - 1]) * (rows[i][0] - rows[i - 1][0]) / 2 for i in range(1, len(rows)))
    return {'sample_count': len(rows) - 2, 'window_ns': window, 'actual_duration_ns': (rows[-1][0] - rows[0][0]) * 1e9,
            'mean_power_w': area / (rows[-1][0] - rows[0][0]), 'min_power_w': min(power), 'max_power_w': max(power),
            'control_ranges_v': {header[i]: [min(r[i] for r in rows), max(r[i] for r in rows)] for i in range(1, 7)},
            'vdd_range_v': [min(r[7] for r in rows), max(r[7] for r in rows)]}


def run(folder: Path) -> dict:
    from phase3_replay_integrated_idle import check_models
    models = check_models(folder)
    assert models['sha256_matches'] == 319
    receipt_path = folder / 'receipt.json'
    receipt = json.loads(receipt_path.read_text())
    assert receipt['status'] == 'PREPARED'
    assert all(sha(folder / name) == digest for name, digest in receipt['input_hashes'].items())
    receipt['status'] = 'RUNNING'
    receipt['started_unix_s'] = time.time()
    receipt['runner_sha256'] = sha(Path(__file__))
    receipt['simulator_sha256'] = sha(Path(NGSPICE))
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    begin = time.monotonic()
    try:
        with (ROOT / 'build/phase3/.eco_simulator.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with (folder / 'ngspice.log').open('xb') as log:
                result = subprocess.run([NGSPICE, '-n', '-b', 'bench.spice'], cwd=folder, stdin=subprocess.DEVNULL,
                                        stdout=log, stderr=subprocess.STDOUT, timeout=7200,
                                        env={**os.environ, 'OMP_NUM_THREADS': str(receipt['threads'])})
    except (OSError, subprocess.TimeoutExpired) as error:
        receipt['status'] = 'INCONCLUSIVE'
        receipt['error'] = str(error)
        receipt['elapsed_s'] = time.monotonic() - begin
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
        raise
    receipt['elapsed_s'] = time.monotonic() - begin
    receipt['returncode'] = result.returncode
    receipt['peak_child_rss_kib'] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    receipt['log_sha256'] = sha(folder / 'ngspice.log')
    errors = re.findall(rb'^\s*(?:Error:|Fatal:|.*analysis aborted).*',
                        (folder / 'ngspice.log').read_bytes(), re.I | re.M)
    receipt['simulator_errors'] = [error.decode(errors='replace') for error in errors[:8]]
    receipt['waveform_sha256'] = sha(folder / 'waveform.dat') if (folder / 'waveform.dat').exists() else None
    receipt['model_check'] = models
    receipt['inputs_preserved'] = all(sha(folder / name) == digest for name, digest in receipt['input_hashes'].items())
    if result.returncode == 0 and receipt['waveform_sha256'] and receipt['inputs_preserved'] and not errors:
        try:
            receipt['measurement'] = measure(folder, receipt['window_ns'])
            receipt['status'] = 'PROVISIONAL'
        except (AssertionError, ValueError) as error:
            receipt['status'] = 'INCONCLUSIVE'
            receipt['error'] = str(error)
    else:
        receipt['status'] = 'INCONCLUSIVE'
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('idle', 'static'))
    parser.add_argument('corner', choices=('TT', 'SS', 'FF'))
    parser.add_argument('--threads', type=int, default=1)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--prepare-only', action='store_true')
    group.add_argument('--run-prepared', action='store_true')
    args = parser.parse_args()
    folder = OUTPUT / (f'threads{args.threads}' if args.threads != 1 else '') / args.mode / args.corner
    if not args.run_prepared:
        folder = prepare(args.corner, args.mode, args.threads)
        print(f'PREPARED {folder}', flush=True)
    if not args.prepare_only:
        result = run(folder)
        print(json.dumps(result, indent=2), flush=True)
        if result['status'] != 'PROVISIONAL':
            raise SystemExit(1)


if __name__ == '__main__':
    main()
