#!/usr/bin/env python3
"""Reconcile startup campaign receipts with stimulus, full raw data and checks."""
import argparse
import json
from pathlib import Path
import numpy as np

from run_phase2_digital import ROOT, sha
from run_phase2_startup_review import (SCENARIOS, SOURCE, GDS, analyze, make_deck,
                                       make_probes, verify_pins)
from phase2_evidence import hashes


def verify_case(source, expected_name, baseline, vectors, probes):
    state = json.loads((source/'results.json').read_text())
    if state['status'] not in ('PASS', 'FAIL') or state.get('error'):
        raise ValueError('Completed electrical scenario required')
    if state['scenario'] != SCENARIOS[expected_name]:
        raise ValueError('Startup scenario configuration differs')
    if state['condition'] != dict(corner='tt', vdd_v=1.8, temp_c=27):
        raise ValueError('Wrong startup experimental condition')
    if state['vectors'] != vectors or state['probes'] != probes:
        raise ValueError('Startup observations differ')
    required_inputs = [SOURCE/'results.json', SOURCE/'binding.spice', SOURCE/'bench.spice', SOURCE/'fabric.spice',
                       GDS/'final_extracted.spice', GDS/'final_flat.ext',
                       ROOT/'reports/phase2/portable_raw/routed_reference.json',
                       ROOT/'tools/run_phase2_startup_review.py', ROOT/'tools/run_phase2_directed_review.py',
                       ROOT/'tools/phase2_access_checks.py', ROOT/'tools/phase2_resources.py']
    hashes(state['inputs'], [str(p) for p in required_inputs]+list(baseline['model_inputs']))
    verify_pins(state['inputs'])
    for p, h in baseline['model_inputs'].items():
        if state['inputs'].get(p) != h:
            raise ValueError('PDK closure differs from baseline')
    # The portable copy must also be exactly the routed design used by the
    # sealed original run, not merely a new self-consistent observation map.
    original_design = [h for n, h in baseline['inputs'].items() if n.endswith('/routed_reference.json')]
    if original_design != [sha(ROOT/'reports/phase2/portable_raw/routed_reference.json')]:
        raise ValueError('Portable routed design differs from sealed baseline')
    artifact_names = ('bench.spice', 'binding.spice', 'fabric.spice', 'ngspice.txt', 'checks.json', 'waveform_excerpt.csv')
    hashes(state['artifacts'], artifact_names)
    for n in artifact_names:
        if sha(source/n) != state['artifacts'][n]:
            raise ValueError('Changed startup artifact: '+n)
    hashes(state['simulation_inputs'], ('bench.spice', 'binding.spice', 'fabric.spice'))
    for n, h in state['simulation_inputs'].items():
        if sha(source/n) != h:
            raise ValueError('Changed pre-run simulation input: '+n)
    if sha(source/'binding.spice') != sha(SOURCE/'binding.spice'):
        raise ValueError('Startup circuit differs from baseline')
    deck, records, stop = make_deck(SCENARIOS[expected_name], baseline, vectors)
    if (source/'bench.spice').read_text() != deck or state['cycles'] != records or state['stop_ns'] != stop:
        raise ValueError('Startup stimulus/operations differ from declared scenario')
    log = (source/'ngspice.txt').read_text()
    if state['ngspice_return_code'] != 0 or 'No. of Data Rows :' not in log or 'ngspice-44.2 done' not in log:
        raise ValueError('Missing successful simulator completion')
    raw = ROOT/state['build_directory']/'waveform.dat'
    if sha(raw) != state['raw_waveform_sha256']:
        raise ValueError('Changed startup raw data')
    with raw.open() as f:
        if f.readline().split() != ['time', *vectors]:
            raise ValueError('Startup raw header differs')
    data = np.loadtxt(raw, skiprows=1)
    checks, reference, metrics = analyze(data, records, vectors, probes, SCENARIOS[expected_name], baseline, stop)
    reported = json.loads((source/'checks.json').read_text())
    if reported != dict(checks=checks, capture_reference=reference):
        raise ValueError('Startup checks differ from full raw reanalysis')
    failures = sum(c['status'] == 'FAIL' for c in checks)
    if (state['checks'] != len(checks) or state['failures'] != failures
            or state['metrics'] != metrics or state['rows'] != len(data)):
        raise ValueError('Startup counters/metrics differ from actual checks')
    if state['status'] != ('FAIL' if failures else 'PASS'):
        raise ValueError('Startup PASS/FAIL does not match actual checks')
    # Check inputs again after consuming raw data; do not seal a moving target.
    verify_pins(state['inputs'])
    return dict(status=state['status'], checks=len(checks), failures=failures,
                metrics=metrics, parameters=SCENARIOS[expected_name],
                receipt_sha256=sha(source/'results.json'), raw_sha256=sha(raw))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sources', nargs='+', required=True); p.add_argument('--output', required=True)
    args = p.parse_args(); out = (ROOT/args.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2') or out.exists():
        p.error('A new output directory under reports/phase2 is required')
    out.mkdir(parents=True)
    result = dict(status='RUNNING', scenarios={}, scope='Raw reanalysis, not minimum startup qualification')
    try:
        baseline = json.loads((SOURCE/'results.json').read_text())
        seal = json.loads((ROOT/'reports/phase2/review_20261104/acceptance/results.json').read_text())
        for rel, h in seal['verified_files'].items():
            if sha(ROOT/rel) != h:
                raise ValueError('Previous acceptance payload changed: '+rel)
        vectors, probes = make_probes(baseline, json.loads((ROOT/'reports/phase2/portable_raw/routed_reference.json').read_text()))
        campaign_hashes = {}
        for name in args.sources:
            source = ROOT/name; campaign = json.loads((source/'results.json').read_text())
            campaign_hashes[str(source/'results.json')] = sha(source/'results.json')
            if campaign['status'] not in ('PASS', 'FAIL') or campaign.get('error'):
                raise ValueError('Incomplete startup campaign')
            names = campaign['requested_scenarios']
            if not names or len(names) != len(set(names)) or set(names) != set(campaign['scenarios']):
                raise ValueError('Incomplete/duplicate startup scenarios')
            for case in names:
                if case not in SCENARIOS or case in result['scenarios']:
                    raise ValueError('Unknown/duplicate startup case')
                reported = campaign['scenarios'][case]
                actual = verify_case(source/case, case, baseline, vectors, probes)
                for key in ('status', 'checks', 'failures', 'parameters', 'receipt_sha256', 'metrics'):
                    if reported[key] != actual[key]:
                        raise ValueError('Campaign summary differs from scenario: '+key)
                result['scenarios'][case] = actual
        if set(result['scenarios']) != set(SCENARIOS):
            raise ValueError('Five planned startup scenarios are required')
        verify_pins(campaign_hashes)
        result.update(status='PASS' if all(s['status'] == 'PASS' for s in result['scenarios'].values()) else 'FAIL',
                      inputs=campaign_hashes, verifier_sha256=sha(Path(__file__)),
                      checks=sum(s['checks'] for s in result['scenarios'].values()),
                      read_bit_checks=sum(s['metrics']['read_bit_checks'] for s in result['scenarios'].values()),
                      prior_acceptance_sha256=sha(ROOT/'reports/phase2/review_20261104/acceptance/results.json'))
    except Exception as error:
        result.update(status='FAIL', error=str(error))
    (out/'results.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
