#!/usr/bin/env python3
"""Requalify a finished full-RC extraction rejected only for zero-valued C.

Keep the original run and its FAIL manifest unchanged. This rechecks every
original artifact, confirms the Magic completion markers and writes a separate
qualified copy of the netlist for subsequent exploratory electrical runs.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import uuid

from phase3_rc_extraction import (EXPECTED_BASELINE, EXPECTED_GDS, BASE_REF, ROOT,
                                  check_baseline, inspect_netlist, sha256)


LEGACY_ERROR = 'Nonpositive passive: C4 _86_.CLK _89_.A 0'
MARKERS = ('PHASE3_IMPORT_COMPLETE=1', 'PHASE3_CONNECTIVITY_EXTRACTED=1',
           'PHASE3_EXTRESIST_COMPLETE=1', 'PHASE3_EXTRACTION_COMPLETE=1',
           'PHASE3_THRESHOLD=0')


def verify(source):
    """Only accept the pinned, immutable legacy extraction and its audit trail."""
    check_baseline()
    source = source.resolve(strict=True)
    old = json.loads((source / 'manifest.json').read_text())
    if (old.get('status') != 'FAIL' or old.get('error') != LEGACY_ERROR or
            old.get('baseline_commit') != EXPECTED_BASELINE or
            old.get('baseline_ref') != BASE_REF or
            old.get('gds_sha256') != EXPECTED_GDS):
        raise ValueError('Legacy run did not fail solely on the known zero-C parser issue')
    artifacts = old.get('artifacts', {})
    for name in ('extract.tcl', 'magic.log', 'extracted_rc.spice',
                 'phase3_rc_flat.ext', 'phase3_rc_flat.mag',
                 'phase3_rc_flat.nodes', 'phase3_rc_flat.res.ext',
                 'phase3_rc_flat.sim'):
        if name not in artifacts or sha256(source / name) != artifacts[name]:
            raise ValueError('Original extraction artifact changed: ' + name)
    script = (source / 'extract.tcl').read_text()
    if (not all(s in script for s in ('gds read ', 'extresist threshold 0',
                                    'extresist all', 'ext2spice extresist on')) or
            'extresist include ' in script):
        raise ValueError('Legacy script does not prove full resistance extraction')
    log = (source / 'magic.log').read_text(errors='replace')
    if not all(marker in log for marker in MARKERS):
        raise ValueError('Magic log does not prove completed extraction')
    extraction = inspect_netlist(source / 'extracted_rc.spice')
    return old, extraction


def requalify(source, output_root):
    source = source.resolve(strict=True)
    old, extraction = verify(source)
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    dest = output_root / run_id
    dest.mkdir(exist_ok=False)
    for name in ('extracted_rc.spice', 'magic.log', 'extract.tcl'):
        shutil.copyfile(source / name, dest / name)
    shutil.copyfile(source / 'manifest.json', dest / 'source_manifest.json')
    artifacts = {p.name: sha256(p) for p in dest.iterdir() if p.is_file()}
    if artifacts['extracted_rc.spice'] != extraction['netlist_sha256']:
        raise ValueError('Copied RC netlist differs from verified source')
    result = {
        'schema_version': 1, 'run_id': run_id,
        'status': 'PASS_RC_NETLIST_STRUCTURE', 'rc_profile': 'all',
        'baseline_ref': BASE_REF, 'baseline_commit': EXPECTED_BASELINE,
        'gds_sha256': EXPECTED_GDS, 'extraction': extraction,
        'artifacts': artifacts, 'scope': 'Full SRAM 4x8, distributed R and C',
        'qualification': 'RETROSPECTIVE_STRUCTURE_ONLY',
        'electrical_function': 'NOT_CHARACTERIZED',
        'source_path': str(source),
        'source_manifest_sha256': sha256(source / 'manifest.json'),
        'source_error': old['error'],
        'source_artifacts_verified': old['artifacts'],
        'magic_legacy_profile_marker': 'ABSENT',
        'notes': ('All original artifact hashes verified; completed all-net Magic '
                  'run; zero-value extraction capacitors accepted. No electrical '
                  'function, timing, power or signoff implied.'),
    }
    (dest / 'manifest.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    return dest, extraction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output-root', type=Path,
                        default=ROOT / 'build/phase3/rc_requalified')
    args = parser.parse_args()
    dest, extraction = requalify(args.source, args.output_root)
    print(json.dumps({'run': str(dest), 'status': 'PASS_RC_NETLIST_STRUCTURE',
                      'extraction': extraction}, indent=2))


if __name__ == '__main__':
    sys.exit(main())
