#!/usr/bin/env python3
"""Package the 247.5 ns Phase 3 replay evidence without changing source runs.

The archive is incremental to the independently preserved 2026-11-24 snapshot.
Absolute observer links become relative links to their copied replay artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile


ROOT = Path(__file__).resolve().parent.parent
BASE_SNAPSHOT = ROOT.parent / 'phase3_evidence_20261124/manifest.json'
ROOT_NAME = 'phase3_incremental_20261125'
DIRECTORIES = (
    'build/phase3/integrated_idle_247p5',
    'build/phase3/integrated_replay_247p5',
    'build/phase3/integrated_observed_247p5',
    'build/phase3/integrated_audits_247p5',
    'build/phase3/diagnostics/physical_controls_20261124',
    'build/phase3/diagnostics/c12_idle_247p5_ss',
    'build/phase3/diagnostics/c12_5ps_candidate_ss_20261124',
)
FILES = (
    'build/phase3/diagnostics/p2_review_matrix_20261125_v3.json',
    'build/phase3/diagnostics/p2_comparison_20261125_native.json',
    'docs/phase3_plano_fechamento_20261124.md',
    'docs/phase3_comparacao_arquiteturas_20261125.md',
    'docs/phase3_characterization_contract.md',
    'memory/memory-ip/run_state.md',
    'tools/phase3_package_incremental.py',
    'tools/phase3_prepare_virtual_eight_integrated.py',
    'tools/phase3_prepare_virtual_eight_strongarm.py',
    'tools/phase3_analyze_virtual_eight_strongarm.py',
    'tools/phase3_replay_integrated_idle.py',
    'tools/run_phase3_integrated_review_compat.py',
    'tools/phase3_audit_integrated_no_transition.py',
    'tools/phase3_audit_read_to_write.py',
    'tools/phase3_compare_write_witness.py',
    'tools/phase3_bus_physical_controls.py',
    'tools/phase3_review_physical_controls.py',
    'tools/phase3_p2_review_matrix.py',
    'tools/phase3_rc_read_path.py',
    'tools/test_phase3_audit_integrated_no_transition.py',
    'tools/test_phase3_audit_read_to_write.py',
    'tools/test_phase3_bus_physical_controls.py',
    'tools/test_phase3_p2_review_matrix.py',
)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def collect() -> list[Path]:
    paths: dict[str, Path] = {}
    for name in DIRECTORIES:
        source = ROOT / name
        if not source.is_dir():
            raise ValueError(f'Missing evidence directory: {source}')
        for path in source.rglob('*'):
            if path.is_file() or path.is_symlink():
                paths[str(path.relative_to(ROOT))] = path
    for name in FILES:
        path = ROOT / name
        if not path.is_file():
            raise ValueError(f'Missing evidence source: {path}')
        paths[name] = path
    return [paths[key] for key in sorted(paths)]


def validate_evidence() -> dict:
    from phase3_p2_review_matrix import review

    result = review()
    if (result['p2_status'] != 'OPEN' or len(result['runs']) != 3
            or len(result['unresolved_lanes']) != 12):
        raise ValueError('Unexpected P2 evidence status or coverage')
    for corner in ('TT', 'SS', 'FF'):
        receipt = json.loads((ROOT / f'build/phase3/integrated_replay_247p5/{corner}/simulation.json').read_text())
        wave = ROOT / f'build/phase3/integrated_replay_247p5/{corner}/waveform.dat'
        if (receipt['status'] != 'COMPLETED' or receipt['returncode'] != 0
                or receipt['waveform_sha256'] != digest(wave)):
            raise ValueError(f'Invalid integrated waveform receipt: {corner}')
    return result['review_summary']


def verify(staged: Path) -> dict:
    manifest = json.loads((staged / 'manifest.json').read_text())
    if manifest['schema'] != 'phase3_incremental_package_v1':
        raise ValueError('Unexpected manifest schema')
    items = manifest['files']
    for record in items:
        relative = Path(record['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError(f'Unsafe archive member: {relative}')
        path = staged / relative
        if record['type'] == 'symlink':
            if not path.is_symlink() or os.readlink(path) != record['target']:
                raise ValueError(f'Link mismatch: {relative}')
            resolved = path.resolve(strict=True)
            if not resolved.is_relative_to(staged.resolve()):
                raise ValueError(f'External symlink: {relative}')
        elif not path.is_file() or path.is_symlink():
            raise ValueError(f'Missing regular file: {relative}')
        if path.stat().st_size != record['bytes'] or digest(path) != record['sha256']:
            raise ValueError(f'File mismatch: {relative}')
    actual = {str(p.relative_to(staged)) for p in staged.rglob('*')
              if p.is_file() or p.is_symlink()}
    if actual != {entry['path'] for entry in items} | {'manifest.json'}:
        raise ValueError('Unlisted files in evidence package')
    return {'files': len(items), 'bytes': sum(x['bytes'] for x in items),
            'manifest_sha256': digest(staged / 'manifest.json')}


def build(destination: Path) -> dict:
    if not BASE_SNAPSHOT.is_file():
        raise ValueError('Preserved 2026-11-24 snapshot manifest is missing')
    review = validate_evidence()
    source_paths = collect()
    destination.mkdir(parents=True, exist_ok=False)
    records = []
    try:
        source_set = {path.resolve() for path in source_paths if not path.is_symlink()}
        for path in source_paths:
            relative = path.relative_to(ROOT)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if path.is_symlink():
                original_target = path.resolve(strict=True)
                if original_target not in source_set:
                    raise ValueError(f'Link points outside package: {path}')
                copied_target = destination / original_target.relative_to(ROOT)
                link_text = os.path.relpath(copied_target, target.parent)
                target.symlink_to(link_text)
                kind = 'symlink'
            else:
                shutil.copy2(path, target)
                link_text = None
                kind = 'file'
            records.append({'path': str(relative), 'type': kind,
                            **({'target': link_text} if link_text is not None else {})})
        # Some observer symlinks precede their target paths in sorted order.
        # Compute sizes and digests only after all archive members exist.
        for record in records:
            target = destination / record['path']
            record['bytes'] = target.stat().st_size
            record['sha256'] = digest(target)
        manifest = {
            'schema': 'phase3_incremental_package_v1',
            'scope': '2026-11-25 local replay and diagnostic evidence',
            'historical_snapshot_manifest_sha256': digest(BASE_SNAPSHOT),
            'historical_snapshot_required_for_full_physical_reproduction': True,
            'source_git_head': subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'original_evidence_unmodified': True,
            'simulation_corners': ['TT', 'SS', 'FF'],
            'p2_review': review,
            'p2_status': 'OPEN',
            'qualification': 'NOT_CHARACTERIZED',
            'external_dependency': 'SKY130A PDK models and EDA environment, pinned by replay model_hashes.json',
            'archive_note': 'Restore under matching project build/phase3 tree. Historical /work references target the EDA container mount.',
            'files': records,
        }
        (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        return verify(destination)
    except BaseException:
        # Leave incomplete copy for diagnosis; never publish a partial archive.
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='New directory for package files')
    parser.add_argument('--verify', type=Path, help='Verify extracted directory')
    args = parser.parse_args()
    if (args.output is None) == (args.verify is None):
        parser.error('Choose --output or --verify')
    if args.verify is not None:
        print(json.dumps(verify(args.verify.resolve()), indent=2))
        return
    folder = args.output.resolve()
    if folder == ROOT or folder.is_relative_to(ROOT):
        parser.error('Package output must be outside source checkout')
    result = build(folder)
    archive = folder.with_suffix('.tar.gz')
    if archive.exists():
        raise ValueError(f'Archive already exists: {archive}')
    with tarfile.open(archive, 'w:gz', compresslevel=1) as stream:
        stream.add(folder, arcname=ROOT_NAME, recursive=True)
    print(json.dumps({**result, 'archive': str(archive),
                      'archive_sha256': digest(archive)}, indent=2))


if __name__ == '__main__':
    main()
