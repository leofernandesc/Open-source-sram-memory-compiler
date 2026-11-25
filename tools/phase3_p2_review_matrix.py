#!/usr/bin/env python3
"""Consolidate immutable P2 replay and physical-control evidence per lane.

This report supports a protocol review. It does not reclassify original
ownership verdicts or approve a static-payload characterization method.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from phase3_audit_integrated_no_transition import (
    input_artifact_hashes, lane_isolation_eligible, validate_receipts,
)
from phase3_review_physical_controls import examine


ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'build/phase3'
OBSERVED = BASE / 'integrated_observed_247p5'
AUDITS = BASE / 'integrated_audits_247p5'
CONTROLS = BASE / 'diagnostics/physical_controls_20261124'

CONTROL_RUNS = {
    ('TT', 2): ('TT_c2_no_host_70ns', 'TT_c2_contention_dut_70ns'),
    ('FF', 2): ('FF_c2_no_host_70ns', 'FF_c2_contention_dut_70ns'),
    ('FF', 10): ('FF_c10_no_host_230ns', 'FF_c10_delayed_release_211ns',
                 'FF_c10_stuck_weak_211ns'),
}

POSITIVE_RUNS = {
    ('TT', 2): (('SS', 2),),
    ('FF', 2): (('SS', 2),),
    ('FF', 10): (('TT', 10), ('SS', 10)),
}


def load(path: Path) -> dict | list:
    return json.loads(path.read_text())


def validate_supplement(run: Path, supplement: dict, receipt: dict, cycle: int) -> None:
    """Pin external observations to the same six immutable replay inputs."""
    digest_key = 'immutable_input_artifacts' if cycle == 2 else 'immutable_source_sha256'
    unchanged_key = 'input_unchanged_during_audit' if cycle == 2 else 'source_unchanged_during_audit'
    if (supplement.get(digest_key) != input_artifact_hashes(run)
            or supplement.get('provenance') != receipt
            or supplement.get(unchanged_key) is not True):
        raise ValueError(f'Unbound supplement provenance: {run.name} c{cycle}')
    if cycle == 2 and Path(supplement.get('source_run', '')).resolve() != run.resolve():
        raise ValueError(f'Wrong static supplement source: {run.name}')
    if cycle == 10 and (supplement.get('corner') != run.name
                        or supplement.get('cycle') != cycle
                        or supplement.get('event_kind') != 'read_to_write'):
        raise ValueError('Wrong read-to-write supplement identity')


def validate_positive_control(corner: str, cycle: int, event: dict,
                              fixture: dict, receipt: dict) -> dict:
    """Use naturally passing 370 ns corners as native-wave positive controls."""
    strong = event.get('strong_check') or {}
    lanes = strong.get('bits') or []
    previous = 'idle' if cycle == 2 else 'read'
    kind = 'write' if cycle == 2 else 'read_to_write'
    if (event.get('cycle') != cycle or event.get('kind') != kind
            or event.get('verdict') != 'PASS' or event.get('overlap') is not False
            or fixture.get('cycle') != cycle
            or fixture.get('previous_operation') != previous
            or fixture.get('expected') != 0xAA
            or strong.get('weak_host_off') is not True
            or strong.get('overlap') is not False
            or len(lanes) != 8 or {lane.get('bit') for lane in lanes} != set(range(8))):
        raise ValueError(f'Invalid positive control: {corner} c{cycle}')
    if cycle == 10 and (event.get('conduction_verified') is not True
                        or event.get('release_verified') is not True
                        or (event.get('conductance_gap_isolated') or {}).get('samples', 0) < 3
                        or event.get('minimum_sample_separation_ns', 0) <= 0):
        raise ValueError(f'Unverified read-to-write positive handoff: {corner}')
    for lane in lanes:
        good, reason = lane_isolation_eligible(lane)
        charge = lane.get('charge_response')
        settled = (charge or {}).get('settled') or {}
        if (not good or not isinstance(charge, dict)
                or settled.get('actual_samples', 0) < 3
                or settled.get('conservative_ps', 0) < 50):
            raise ValueError(f'Invalid positive lane {corner} c{cycle} bit {lane.get("bit")}: {reason}')
    return dict(corner=corner, cycle=cycle, kind=kind, original_ownership='PASS',
                native_charge_witness_lanes=8, waveform_sha256=receipt['waveform_sha256'])


def review() -> dict:
    supplements = {
        ('TT', 2): load(AUDITS / 'TT_static_payload.json'),
        ('FF', 2): load(AUDITS / 'FF_static_payload_diagnostic.json'),
        ('FF', 10): load(BASE / 'diagnostics/p2_revalidation_20261125T083047/FF_c10_read_to_write_candidate_v2.json'),
    }
    controls = {}
    for event, paths in CONTROL_RUNS.items():
        records = [examine(CONTROLS / name) for name in paths]
        if any(rec['corner'].upper() != event[0] or rec['cycle'] != event[1]
               or not rec['original_observer_rejects_pass'] for rec in records):
            raise ValueError(f'Invalid physical control event binding: {event}')
        controls[event] = records

    runs = []
    rows = []
    positive = {}
    source = {}
    for corner in ('TT', 'SS', 'FF'):
        run = OBSERVED / corner
        analysis = load(run / 'analysis.json')
        ownership = load(run / 'revised_ownership.json')
        fixture = load(run / 'fixture.json')
        receipt = validate_receipts(run, analysis, fixture, ownership)
        topology = load(run / 'topology_classification.json')
        if not all(topology[name] == 'PASS' for name in
                   ('classification_gate', 'lane_coverage_gate',
                    'receipt_integrity_gate', 'p1_replay_gate')):
            raise ValueError(f'Integrated topology/coverage gate failed: {corner}')
        if (any(item['verdict'] != 'PASS' for item in analysis['cycles'].values())
                or len(ownership) != 18):
            raise ValueError(f'Integrated function/cycle count failed: {corner}')
        if corner == 'SS' and any(event['verdict'] != 'PASS' for event in ownership):
            raise ValueError('SS ownership is no longer all PASS')
        runs.append(dict(corner=corner, raw_ownership=analysis['verdict'],
                         functional_operations_pass=18, receipt=receipt,
                         input_sha256=input_artifact_hashes(run)))
        source[corner] = (run, ownership, fixture, receipt)
        fixtures = {rec['cycle']: rec for rec in fixture['cycles']}
        for event in ownership:
            if event['verdict'] == 'PASS':
                continue
            cycle = event['cycle']
            key = (corner, cycle)
            if key not in CONTROL_RUNS:
                raise ValueError(f'Unanticipated unresolved P2 event: {key}')
            strong = event.get('strong_check') or {}
            missing = [lane for lane in strong.get('bits', [])
                       if lane.get('charge_response') is None]
            if not missing or event['overlap'] is not False:
                raise ValueError(f'Unrecognized unresolved ownership mode: {key}')
            supplemental = supplements[key]
            validate_supplement(run, supplemental, receipt, cycle)
            if key[1] == 2:
                if (supplemental['raw_integrated_observer_verdict'] != 'INCONCLUSIVO'
                        or not supplemental['input_unchanged_during_audit']):
                    raise ValueError(f'Unbound static witness supplement: {key}')
                support = {rec['bit']: rec for rec in supplemental['supplements']
                           if rec['cycle'] == cycle}
            else:
                if (supplemental['raw_ownership_verdict'] != 'INCONCLUSIVO'
                        or not supplemental['source_unchanged_during_audit']):
                    raise ValueError('Unbound FF c10 read-to-write supplement')
                support = {rec['bit']: rec for rec in supplemental['missing_charge_lanes']}
            if set(support) != {lane['bit'] for lane in missing}:
                raise ValueError(f'Supplement does not cover missing lanes: {key}')
            for lane in missing:
                bit = lane['bit']
                item = support[bit]
                supported = (item['stable_at_expected_logic'] and
                             item['ownership_isolated_and_quiet']) if cycle == 2 else (
                                 item['stable_expected_rail'] and
                                 supplemental['candidate_supplement'] == 'ELIGIBLE_FOR_PROTOCOL_REVIEW')
                rows.append(dict(
                    corner=corner, cycle=cycle, operation=event['kind'],
                    previous_operation=fixtures[cycle]['previous_operation'],
                    bit=bit, expected=(fixtures[cycle]['expected'] >> bit) & 1,
                    raw_ownership='INCONCLUSIVO', charge_transition_observed=False,
                    disabled_macro_gate=lane['disabled_gate'],
                    strong_host_enable=lane['strong_host_on'],
                    quiet_suffix=lane['quiet_suffix'],
                    supplemental_static_rail_supported=bool(supported),
                    supplemental_method='idle_to_write' if cycle == 2 else 'read_to_write',
                    physical_negative_controls=[dict(
                        mode=control['mode'],
                        original_observer_verdict=control['original_observer_verdict'],
                        physical_fault_detected=control['injected_fault_detected'],
                        source_waveform_sha256=control['source_waveform_sha256'],
                        receipt_sha256=control['receipt_sha256'],
                        control_waveform_sha256=control['control_waveform_sha256'])
                        for control in controls[key]],
                    status='PENDING_PROTOCOL_APPROVAL',
                ))

    for key, references in POSITIVE_RUNS.items():
        positive[key] = [validate_positive_control(
            reference_corner, reference_cycle,
            source[reference_corner][1][reference_cycle],
            source[reference_corner][2]['cycles'][reference_cycle],
            source[reference_corner][3])
            for reference_corner, reference_cycle in references]
    for row in rows:
        row['native_positive_controls'] = positive[row['corner'], row['cycle']]

    if len(rows) != 12 or not all(row['supplemental_static_rail_supported'] for row in rows):
        raise ValueError('Missing or inconsistent static-payload evidence')
    return dict(scope='P2 offline evidence consolidation, original verdicts preserved',
                qualification='NOT_CHARACTERIZED', p2_status='OPEN',
                methodology_approval='PENDING',
                blockers=['Static-payload and read-to-write protocol acceptance',
                          'Final ownership decision for TT c2 and FF c2/c10'],
                downstream_requirements={
                    'P3': 'Architecture decision and matching DRC/LVS/PEX physical views',
                    'P4': 'TT/SS/FF validation on the selected final physical PEX',
                    'P5': 'Timing, power, Hold/Read SNM and generated Liberty',
                },
                runs=runs, unresolved_lanes=rows,
                review_summary=dict(functional_operations_pass_per_corner=18,
                                    raw_ownership_pass_corners=['SS'],
                                    positive_control_events=['SS c2', 'TT c10', 'SS c10'],
                                    outstanding_events=['TT c2', 'FF c2', 'FF c10'],
                                    unresolved_bit_count=len(rows)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or OBSERVED.resolve() in output.parents or AUDITS.resolve() in output.parents:
        parser.error('Output must be new and outside immutable evidence')
    result = review()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(result['review_summary'], 'P2:', result['p2_status'])


if __name__ == '__main__':
    main()
