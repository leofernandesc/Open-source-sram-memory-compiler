#!/usr/bin/env python3
"""Run a pinned Phase 3 experiment. No SRAM characterization claim is made."""
import argparse
import json
from phase3.runner import run

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        result = run(args.config, args.output, args.dry_run)
    except (ValueError, FileExistsError) as error:
        parser.exit(2, str(error) + '\n')
    print(json.dumps({k: result[k] for k in ('run_id', 'status', 'electrical_simulation_performed')}))
    success = result['status'] == 'PASS' or (
        args.dry_run and result['status'] == 'NOT_CHARACTERIZED'
        and not result['electrical_simulation_performed'])
    raise SystemExit(0 if success else 1)
