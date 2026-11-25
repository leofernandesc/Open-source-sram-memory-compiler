#!/usr/bin/env python3
"""Run sealed, physical three-StrongARM v6 370 ns TT/SS/FF controls.

Execute inside ./tools/sram-eda after phase3_prepare_v6_integrated.py.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from phase3_replay_integrated_idle import check_models, execute, sha


ROOT = Path('/work')
INPUT = ROOT / 'build/phase3/integrated_v6_idle_247p5'
PEX = 'a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f'
GDS = '315c2ebceb2bc4cf258fa63be2279843805db3010637d0c273aea9db12813e37'
BINDING = '3b6f7205476b79d02754ba081a7d2eb2ef9d372670daf26067d3d0cb5745e76d'


def validate(folder: Path, corner: str) -> dict:
    pre = json.loads((folder / 'preflight.json').read_text())
    assert pre['gate'] == 'READY' and pre['topology'] == 'PHYSICAL_V6_READY'
    assert pre['corner'] == pre['conditions']['corner'] == corner.lower()
    assert pre['physical_pex_sha256'] == PEX and pre['gds_sha256'] == GDS
    assert pre['guard_ns'] == 1.5 and pre['stop_ns'] == 370
    assert pre['conditions']['maximum_step_ps'] == 25
    assert pre['c12_idle_start_ns'] == 247.5
    assert set(pre['outputs']) == {
        'bench.spice', 'binding.spice', 'fabric.spice', 'model_hashes.json',
        'fixture.json', 'probes.json', 'internals.json',
    }
    for name, expected in pre['outputs'].items():
        assert sha(folder / name) == expected, f'v6 input changed: {name}'
    assert pre['outputs']['binding.spice'] == BINDING
    deck = (folder / 'bench.spice').read_text()
    assert f'.lib "/opt/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice" {corner.lower()}' in deck
    assert deck.count('tran 10p 370n 0 25p') == 1
    assert '.include "buf_1.spice"' not in deck
    for source in ('V_CSb', 'V_OEb'):
        line, = (line for line in deck.splitlines() if line.startswith(source + ' '))
        assert line.count('247.5n 0 247.55n 1.8') == 1
    records = json.loads((folder / 'fixture.json').read_text())['cycles']
    assert len(records) == 18 and [r['cycle'] for r in records] == list(range(18))
    assert [sum(r['operation'] == op for r in records) for op in ('read', 'write', 'idle')] == [9, 6, 3]
    assert records[12]['operation'] == 'idle' and records[12]['control_start_ns'] == 247.5
    assert records[12]['rise_ns'] == 250
    return pre


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corner', choices=('TT', 'SS', 'FF', 'all'))
    parser.add_argument('--timeout', type=int, default=3600)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    for corner in ('TT', 'SS', 'FF') if args.corner == 'all' else (args.corner,):
        folder = INPUT / corner
        validate(folder, corner)
        models = check_models(folder)
        print(f'PREFLIGHT physical v6 {corner}: PEX={PEX} idle=247.5 ns models={models["sha256_matches"]}', flush=True)
        if not args.check_only:
            receipt = execute(folder, corner, args.timeout, validator=validate)
            if receipt['status'] != 'COMPLETED':
                raise SystemExit(f'Physical v6 simulation incomplete for {corner}')


if __name__ == '__main__':
    main()
