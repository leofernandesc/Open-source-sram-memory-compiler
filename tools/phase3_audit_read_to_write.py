#!/usr/bin/env python3
"""Diagnose FF c10 static write payload after a verified read-to-write handoff.

This supplementary result is provisional until the P2 electrical protocol is
approved. The original integrated observer's verdict remains authoritative.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from phase3_audit_integrated_no_transition import (
    MIN_STATIC_WITNESS_PS, input_artifact_hashes,
    lane_isolation_eligible, require, validate_receipts,
)
from phase3_rc_read_path import HIGH, LOW
from review_phase3_bus_ss import Trace, ge, le


def eligible_handoff(event: dict, fixture: dict) -> tuple[bool, list[str]]:
    """Require read release, isolated turnaround and strong-host ownership."""
    problems = []
    if (fixture.get('cycle') != 10 or fixture.get('previous_operation') != 'read'
            or fixture.get('operation') != 'write'
            or event.get('kind') != 'read_to_write'
            or event.get('verdict') != 'INCONCLUSIVO'
            or event.get('overlap') is not False):
        problems.append('not an inconclusive FF c10 read-to-write ownership event')
    probe = event.get('probe') or {}
    bridge = event.get('conductance_gap_isolated')
    if (event.get('conduction_verified') is not True
            or event.get('release_verified') is not True
            or probe.get('drive_verified') is not True
            or probe.get('release_verified') is not True
            or not isinstance(bridge, dict)
            or bridge.get('samples', 0) < 3):
        problems.append('read conduction/release or isolated bridge unverified')
    if (not isinstance(event.get('minimum_sample_separation_ns'), (float, int))
            or event['minimum_sample_separation_ns'] <= 0):
        problems.append('no positive native-sample separation before strong host')
    strong = event.get('strong_check') or {}
    if strong.get('weak_host_off') is not True or strong.get('overlap') is not False:
        problems.append('weak probe or strong-host opposition not isolated')
    lanes = strong.get('bits', [])
    if len(lanes) != 8 or {lane.get('bit') for lane in lanes} != set(range(8)):
        problems.append('incomplete eight-lane strong-host evidence')
    for lane in lanes:
        lane_ok, reason = lane_isolation_eligible(lane)
        if not lane_ok:
            problems.append(f'bit {lane.get("bit")}: {reason}')
    if not any(lane.get('charge_response') is None for lane in lanes):
        problems.append('no missing charge witness to supplement')
    return not problems, problems


def audit(run: Path, output: Path) -> dict:
    run = run.resolve(strict=True)
    output = output.resolve()
    require(output != run and run not in output.parents and not output.exists(),
            'Supplement must be written to a new location outside the replay')
    before = input_artifact_hashes(run)
    analysis = json.loads((run / 'analysis.json').read_text())
    ownership = json.loads((run / 'revised_ownership.json').read_text())
    fixtures = json.loads((run / 'fixture.json').read_text())
    receipt = validate_receipts(run, analysis, fixtures, ownership)
    event = ownership[10]
    record = fixtures['cycles'][10]
    require(event.get('cycle') == 10 and record.get('cycle') == 10,
            'Unexpected FF c10 cycle identity')
    require(analysis['cycles']['10']['operation'] == 'write'
            and analysis['cycles']['10']['verdict'] == 'PASS'
            and analysis['cycles']['10']['ownership'] == event.get('verdict'),
            'Unexpected function versus ownership status in c10')
    eligible, problems = eligible_handoff(event, record)
    strong = event['strong_check']

    with (run / 'waveform.dat').open() as stream:
        header = stream.readline().lower().split()
    columns = ['time'] + [f'v(data{bit})' for bit in range(8)]
    require(len(header) == len(set(header)) and all(key in header for key in columns),
            'Required unique native DATA vectors missing')
    values = np.loadtxt(run / 'waveform.dat', skiprows=1,
                        usecols=[header.index(key) for key in columns], ndmin=2)
    require(np.isfinite(values).all() and np.all(np.diff(values[:, 0]) > 0)
            and values.shape[0] == analysis['samples']
            and values[-1, 0] * 1e9 >= 369.999999,
            'Native DATA vectors missing full waveform coverage')
    trace = Trace(values, {key: i for i, key in enumerate(columns)})
    onset = strong['start_ns']
    require(onset < record['rise_ns'] < strong['end_ns'],
            'Invalid c10 strong-host observation interval')
    missing = []
    for lane in strong['bits']:
        bit = lane['bit']
        if lane['charge_response'] is not None:
            continue
        expected_high = bool(record['expected'] & (1 << bit))
        condition = [ge(bit + 1, HIGH)] if expected_high else [le(bit + 1, LOW)]
        before_clk = trace.signal_window(onset, record['rise_ns'], condition, suffix=True)
        during_drive = trace.signal_window(onset, strong['end_ns'], condition, suffix=True)
        # A terminal suffix may begin after host enable and hide a late DATA
        # transition. Require the expected rail across the full host-to-CLK
        # interval as well as native samples spanning the observation window.
        stable_from_host_enable = trace.through(onset, record['rise_ns'], condition)
        stable = (before_clk is not None and during_drive is not None
                  and before_clk['conservative_ps'] >= MIN_STATIC_WITNESS_PS
                  and during_drive['conservative_ps'] >= MIN_STATIC_WITNESS_PS
                  and stable_from_host_enable)
        missing.append(dict(bit=bit, expected=int(expected_high),
                            native_pre_clock=before_clk,
                            native_while_strong=during_drive,
                            stable_from_host_enable_to_clock=stable_from_host_enable,
                            stable_expected_rail=bool(stable)))
        if not stable:
            problems.append(f'bit {bit}: missing native post-turnaround DATA stability')

    result = dict(
        corner='FF', cycle=10, event_kind='read_to_write',
        raw_ownership_verdict=event['verdict'],
        candidate_supplement='ELIGIBLE_FOR_PROTOCOL_REVIEW' if eligible and not problems
        else 'INCONCLUSIVE',
        methodology_approval='PENDING', electrical_qualification='NOT_CHARACTERIZED',
        previous_read_drive_verified=event.get('conduction_verified'),
        previous_read_release_verified=event.get('release_verified'),
        gap_isolated=event.get('conductance_gap_isolated'),
        minimum_sample_separation_ns=event.get('minimum_sample_separation_ns'),
        weak_host_off=strong['weak_host_off'],
        strong_host_gate_isolation_verified=eligible,
        missing_charge_lanes=missing, blockers=problems,
        provenance=receipt, immutable_source_sha256=before,
        source_unchanged_during_audit=before == input_artifact_hashes(run),
    )
    require(result['source_unchanged_during_audit'], 'Replay changed during read-to-write audit')
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(result, indent=2, allow_nan=False) + '\n'
    with output.open('x') as stream:
        stream.write(serialized)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.run, args.output)
    print(result['candidate_supplement'], result['blockers'])


if __name__ == '__main__':
    main()
