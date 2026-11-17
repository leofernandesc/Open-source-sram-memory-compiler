#!/usr/bin/env python3
"""Run the 165 Phase 3 delivery regressions without an electrical simulation."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SUITES = (
    'test_phase3.py', 'test_phase3_revision.py', 'test_phase2_evidence.py',
    'test_phase2_output_safety.py', 'test_phase2_extension.py',
    'test_phase2_startup.py', 'test_phase2_protocol.py',
    'test_phase3_functional_a.py', 'test_digital_regression_integration.py',
    'test_phase3_nominal_bench.py', 'test_phase3_nominal_operational.py',
)


def run(output):
    output = Path(output).resolve()
    parent = ROOT/'reports/phase3'
    if output == parent or not output.is_relative_to(parent):
        raise ValueError('Use a new directory below reports/phase3')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()  # Never replace a previous transcript or result.
    results = []
    for pattern in SUITES:
        command = [sys.executable, '-m', 'unittest', 'discover',
                   '-s', 'tools/tests', '-p', pattern, '-v']
        started = time.monotonic()
        with (output/(pattern+'.stdout.txt')).open('x') as out, \
                (output/(pattern+'.stderr.txt')).open('x') as err:
            try:
                code = subprocess.run(command, cwd=ROOT, stdout=out, stderr=err,
                                      timeout=300).returncode
            except subprocess.TimeoutExpired:
                code = None
        trace = (output/(pattern+'.stderr.txt')).read_text()
        count = re.search(r'Ran (\d+) tests?', trace)
        results.append(dict(suite=pattern, command=command, return_code=code,
                            tests=int(count[1]) if count else 0,
                            skipped=bool(re.search(r'skipped=', trace)),
                            elapsed_s=time.monotonic()-started))
        print(json.dumps(results[-1]), flush=True)
    total = sum(item['tests'] for item in results)
    passed = total == 165 and all(item['return_code'] == 0 and item['tests'] > 0
                                 and not item['skipped'] for item in results)
    summary = dict(schema_version=1, status='PASS' if passed else 'FAIL', tests=total,
                   expected_tests=165, electrical_simulation_performed=False, suites=results)
    (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    return 0 if passed else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        raise SystemExit(run(args.output))
    except (ValueError, FileExistsError) as error:
        parser.exit(2, str(error)+'\n')
