#!/usr/bin/env python3
"""Prepare 370 ns post-layout v6 controls with the 247.5 ns c12 idle edge.

Rebuild from the sealed 2026-11-24 physical v6 fixture in a separate folder.
The physical binding, PEX and probes are preserved byte-for-byte.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT.parent / 'phase3_evidence_20261124'
SOURCE = ARCHIVE / 'build/phase3/strongarm_functional_closure_20261122/integrated'
OUTPUT = ROOT / 'build/phase3/integrated_v6_idle_247p5'
PEX = 'a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f'
GDS = '315c2ebceb2bc4cf258fa63be2279843805db3010637d0c273aea9db12813e37'
BINDING = '3b6f7205476b79d02754ba081a7d2eb2ef9d372670daf26067d3d0cb5745e76d'


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def assert_archive() -> dict:
    tt = SOURCE / 'TT'
    ss = SOURCE / 'SS'
    pre = json.loads((tt / 'preflight.json').read_text())
    other = json.loads((ss / 'preflight.json').read_text())
    assert pre['gate'] == other['gate'] == 'READY'
    assert pre['corner'] == 'TT' and other['corner'] == 'SS'
    assert pre['guard_ns'] == other['guard_ns'] == 1.5
    assert pre['stop_ns'] == other['stop_ns'] == 370
    assert pre['physical_pex_sha256'] == other['physical_pex_sha256'] == PEX
    assert pre['gds_sha256'] == other['gds_sha256'] == GDS
    assert pre['outputs']['binding.spice'] == other['outputs']['binding.spice'] == BINDING
    assert set(pre['outputs']) == set(other['outputs'])
    for corner, source_pre in (('TT', pre), ('SS', other)):
        source = SOURCE / corner
        for name, expected in source_pre['outputs'].items():
            assert sha(source / name) == expected, f'archived {corner} mismatch: {name}'
        if corner == 'SS':
            assert all(pre['outputs'][name] == expected for name, expected in source_pre['outputs'].items()
                       if name != 'bench.spice'), 'SS source differs outside process corner'
    assert pre['conditions']['maximum_step_ps'] == 25
    assert pre['conditions']['vdd_v'] == 1.8 and pre['conditions']['temp_c'] == 27
    assert pre['outputs']['model_hashes.json'] == sha(tt / 'model_hashes.json')
    models = json.loads((tt / 'model_hashes.json').read_text())
    assert len(models) == 319
    assert sha(ARCHIVE / 'build/phase3/strongarm_triple_20261122/physical/pex_verified/extracted_rc.spice') == PEX
    assert sha(ARCHIVE / 'build/phase3/strongarm_triple_20261122/physical/macro_v6/sram_4x8.gds') == GDS
    return pre


def update_bench(source: str, corner: str) -> str:
    assert source.count('.lib "/opt/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice" tt') == 1
    source = source.replace('.lib "/opt/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice" tt',
                            '.lib "/opt/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice" ' + corner.lower())
    for signal in ('V_CSb', 'V_OEb'):
        old, new = '247n 0 247.05n 1.8', '247.5n 0 247.55n 1.8'
        found = re.findall(rf'^{signal} [^\n]+$', source, re.M)
        assert len(found) == 1 and found[0].count(old) == 1, f'{signal} c12 edge changed'
        source = source.replace(found[0], found[0].replace(old, new), 1)
    assert source.count('tran 10p 370n 0 25p') == 1
    assert source.count('.include "binding.spice"') == 1
    assert '.include "buf_1.spice"' not in source
    return source


def prepare(corner: str, output: Path) -> dict:
    pre = assert_archive()
    archive_tt = SOURCE / 'TT'
    if output.exists():
        raise FileExistsError(f'refusing to overwrite {output}')
    fixture = json.loads((archive_tt / 'fixture.json').read_text())
    cycles = fixture['cycles']
    assert len(cycles) == 18 and [c['cycle'] for c in cycles] == list(range(18))
    assert (cycles[12]['cycle'], cycles[12]['operation'], cycles[12]['control_start_ns'],
            cycles[12]['rise_ns']) == (12, 'idle', 247, 250)
    cycles[12]['control_start_ns'] = 247.5
    output.mkdir(parents=True)
    for name in pre['outputs']:
        if name not in ('bench.spice', 'fixture.json'):
            shutil.copyfile(archive_tt / name, output / name)
    (output / 'bench.spice').write_text(update_bench((archive_tt / 'bench.spice').read_text(), corner))
    (output / 'fixture.json').write_text(json.dumps(fixture, indent=2) + '\n')
    out_pre = {
        'gate': 'READY', 'topology': 'PHYSICAL_V6_READY', 'corner': corner.lower(),
        'guard_ns': 1.5, 'stop_ns': 370,
        'conditions': {**pre['conditions'], 'corner': corner.lower()},
        'physical_pex_sha256': PEX, 'gds_sha256': GDS,
        'c12_idle_start_ns': 247.5,
        'archive_tt_preflight_sha256': sha(archive_tt / 'preflight.json'),
        'archive_ss_preflight_sha256': sha(SOURCE / 'SS/preflight.json'),
        'outputs': {name: sha(output / name) for name in pre['outputs']},
    }
    assert out_pre['outputs']['binding.spice'] == BINDING
    (output / 'preflight.json').write_text(json.dumps(out_pre, indent=2) + '\n')
    return {'corner': corner, 'output': str(output), 'preflight_sha256': sha(output / 'preflight.json'),
            'binding_sha256': BINDING, 'fixture_sha256': out_pre['outputs']['fixture.json']}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corner', choices=('TT', 'SS', 'FF', 'all'))
    args = parser.parse_args()
    for corner in ('TT', 'SS', 'FF') if args.corner == 'all' else (args.corner,):
        print(json.dumps(prepare(corner, OUTPUT / corner), indent=2), flush=True)


if __name__ == '__main__':
    main()
