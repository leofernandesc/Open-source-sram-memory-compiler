#!/usr/bin/env python3
"""Add an explicit static-payload witness for integrated ownership gaps."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from phase3_rc_read_path import HIGH, LOW


EXPECTED_CYCLES = set(range(18))
EXPECTED_BITS = set(range(8))
EXPECTED_DURATION_NS = 370.0
MIN_STATIC_WITNESS_PS = 50.0
INPUT_ARTIFACTS = (
    "simulation.json",
    "model_hashes.json",
    "analysis.json",
    "revised_ownership.json",
    "fixture.json",
    "waveform.dat",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def input_artifact_hashes(run: Path) -> dict[str, str]:
    return {name: sha256(run / name) for name in INPUT_ARTIFACTS}


def validate_receipts(run: Path, analysis: dict, fixture: dict, ownership: list) -> dict:
    receipt = json.loads((run / "simulation.json").read_text())
    model_hashes = json.loads((run / "model_hashes.json").read_text())
    waveform = run / "waveform.dat"
    actual_waveform_sha = sha256(waveform)
    require(receipt.get("status") == "COMPLETED", "Simulation receipt is not COMPLETED")
    require(receipt.get("returncode") == 0 and not receipt.get("errors"),
            "Simulation receipt reports a failed process or simulator errors")
    require(abs(float(receipt.get("simulation_ns", -1)) - EXPECTED_DURATION_NS) < 1e-9,
            "Simulation duration is not the complete 370 ns fixture")
    require(receipt.get("waveform_sha256") == actual_waveform_sha,
            "Waveform SHA-256 differs from simulation receipt")
    require(analysis.get("waveform_sha256") == actual_waveform_sha,
            "Analysis is not tied to the waveform SHA-256")
    require(isinstance(model_hashes, dict) and len(model_hashes) == 319,
            "Expected complete 319-model hash inventory")
    require(receipt.get("model_check", {}).get("sha256_matches") == len(model_hashes),
            "Simulation receipt does not confirm all model hashes")
    fixture_ids = [int(row["cycle"]) for row in fixture.get("cycles", [])]
    ownership_ids = [int(row["cycle"]) for row in ownership]
    analysis_ids = [int(key) for key in analysis.get("cycles", {})]
    require(len(fixture_ids) == 18 and set(fixture_ids) == EXPECTED_CYCLES,
            "Fixture does not contain each of the 18 unique cycles")
    require(len(ownership_ids) == 18 and set(ownership_ids) == EXPECTED_CYCLES,
            "Ownership analysis does not contain each of the 18 unique cycles")
    require(len(analysis_ids) == 18 and set(analysis_ids) == EXPECTED_CYCLES,
            "Functional analysis does not contain each of the 18 unique cycles")
    require(len(set(fixture_ids)) == len(fixture_ids)
            and len(set(ownership_ids)) == len(ownership_ids)
            and len(set(analysis_ids)) == len(analysis_ids),
            "Duplicate cycle identifiers in evidence")
    require(int(analysis.get("samples", -1)) > 0, "Analysis reports no waveform samples")
    return {
        "simulation_status": receipt["status"],
        "simulation_ns": receipt["simulation_ns"],
        "waveform_sha256": actual_waveform_sha,
        "waveform_samples_reported": analysis["samples"],
        "model_hash_count": len(model_hashes),
        "cycle_count": len(fixture_ids),
    }


def lane_isolation_eligible(lane: dict) -> tuple[bool, str]:
    if lane.get("disabled_gate") is not True or lane.get("strong_host_on") is not True:
        return False, "lane does not prove macro disabled and host enabled"
    for field in ("sustained_opposition", "opposition_with_gate_off"):
        if field not in lane or lane[field] is not None:
            return False, f"lane has missing or unresolved {field} evidence"
    quiet = lane.get("quiet_suffix")
    if not isinstance(quiet, dict):
        return False, "lane has no quiet suffix witness"
    if int(quiet.get("actual_samples", 0)) < 3:
        return False, "quiet suffix has fewer than three raw samples"
    duration = float(quiet.get("conservative_ps", 0.0))
    if not np.isfinite(duration) or duration < MIN_STATIC_WITNESS_PS:
        return False, "quiet suffix is shorter than 50 ps or invalid"
    return True, "lane isolation verified"


def static_witness_eligible(event: dict, record: dict, lane: dict) -> tuple[bool, str]:
    if event.get("kind") != "write" or event.get("operation") != "write":
        return False, "static witness is allowed only for a write ownership event"
    if event.get("verdict") != "INCONCLUSIVO":
        return False, "only an inconclusive ownership event can be supplemented"
    if event.get("overlap") is not False:
        return False, "write ownership reports overlap or has no explicit overlap result"
    if (record.get("previous_operation") != "idle"
            or event.get("release_verified") is not True
            or not event.get("initial_idle_bridged")
            or (event.get("initial_idle_probe") or {}).get("release_verified") is not True):
        return False, "independent idle-to-write release and bridge are not verified"
    strong = event.get("strong_check")
    if (not isinstance(strong, dict) or strong.get("weak_host_off") is not True
            or strong.get("overlap") is not False):
        return False, "strong-host isolation evidence is missing"
    eligible, reason = lane_isolation_eligible(lane)
    if not eligible:
        return False, reason
    if "charge_response" not in lane or lane["charge_response"] is not None:
        return False, "lane does not explicitly lack a charge witness"
    if record.get("host_payload_ns") is None or strong.get("end_ns") is None:
        return False, "write payload observation window is incomplete"
    return True, "eligible static payload lane"


def audit(run: Path, output: Path) -> dict:
    run = run.resolve(strict=True)
    output = output.resolve()
    require(output != run and run not in output.parents,
            "Output must be outside the immutable input run directory")
    require(not output.exists(), f"Refusing to overwrite existing audit output: {output}")
    input_hashes_before = input_artifact_hashes(run)
    analysis = json.loads((run / "analysis.json").read_text())
    ownership = json.loads((run / "revised_ownership.json").read_text())
    fixture = json.loads((run / "fixture.json").read_text())
    provenance = validate_receipts(run, analysis, fixture, ownership)
    records = {int(row["cycle"]): row for row in fixture["cycles"]}

    with (run / "waveform.dat").open() as stream:
        names = stream.readline().lower().split()
    require(len(names) == len(set(names)), "Waveform header contains duplicate signal names")
    require(bool(names) and names[0] == "time", "Waveform first vector is not time")
    data = np.loadtxt(run / "waveform.dat", skiprows=1, ndmin=2)
    require(data.ndim == 2 and data.shape[1] == len(names),
            "Waveform vector width differs from its header")
    require(data.shape[0] == int(analysis["samples"]),
            "Waveform row count differs from the observer sample count")
    require(np.isfinite(data[:, 0]).all(), "Waveform time vector contains non-finite samples")
    times_ns = data[:, 0] * 1e9
    require(np.all(np.diff(times_ns) > 0), "Waveform time vector is not strictly increasing")
    require(times_ns[0] >= 0 and times_ns[-1] >= EXPECTED_DURATION_NS - 1e-6,
            "Waveform does not cover the full 370 ns simulation")
    columns = {name: index for index, name in enumerate(names)}

    supplements = []
    unresolved = []
    for event in ownership:
        cycle = int(event["cycle"])
        cycle_analysis = analysis["cycles"][str(cycle)]
        if (cycle_analysis.get("ownership") != event.get("verdict")
                or cycle_analysis.get("operation") != records[cycle].get("operation")):
            unresolved.append({"cycle": cycle, "reason": "cycle evidence disagrees with fixture or ownership"})
            continue
        if event.get("verdict") == "PASS":
            continue
        if (cycle_analysis.get("operation") != "write"
                or cycle_analysis.get("verdict") != "PASS"
                or cycle_analysis.get("ownership") == "PASS"):
            unresolved.append({"cycle": cycle, "reason": "cycle has an unrelated functional or ownership failure"})
            continue
        strong = event.get("strong_check") or {}
        lanes = strong.get("bits", [])
        lane_ids = [int(lane["bit"]) for lane in lanes]
        if len(lane_ids) != 8 or set(lane_ids) != EXPECTED_BITS:
            unresolved.append({"cycle": cycle, "reason": "ownership lane coverage is not exactly bits 0 through 7"})
            continue
        # A missing charge response must be the only unresolved strong-host
        # condition across all eight lanes, including lanes with charge evidence.
        lane_failures = []
        for lane in lanes:
            eligible, reason = lane_isolation_eligible(lane)
            if not eligible or "charge_response" not in lane:
                lane_failures.append({"cycle": cycle, "bit": int(lane["bit"]),
                                      "reason": reason if not eligible else "charge evidence missing"})
        if lane_failures:
            unresolved.extend(lane_failures)
            continue
        missing_charge = [lane for lane in lanes if lane.get("charge_response") is None]
        if not missing_charge:
            unresolved.append({"cycle": cycle, "reason": "inconclusive ownership has no missing charge witness to supplement"})
            continue
        for lane in missing_charge:
            bit = int(lane["bit"])
            eligible, reason = static_witness_eligible(event, records[cycle], lane)
            if not eligible:
                unresolved.append({"cycle": cycle, "bit": bit, "reason": reason})
                continue
            record = records[cycle]
            expected = (int(record["expected"]) >> bit) & 1
            pad_name = f"v(data{bit})"
            if pad_name not in columns:
                unresolved.append({"cycle": cycle, "bit": bit, "reason": "DATA probe absent"})
                continue
            event_ns = float(record.get("host_payload_ns", strong.get("start_ns")))
            end_ns = float(strong.get("end_ns", event_ns))
            begin_ns = event_ns - 0.1
            if (not np.isfinite([begin_ns, end_ns]).all() or end_ns <= begin_ns
                    or begin_ns < times_ns[0] or end_ns > times_ns[-1]):
                unresolved.append({"cycle": cycle, "bit": bit, "reason": "invalid DATA observation interval"})
                continue
            window = (times_ns >= begin_ns) & (times_ns <= end_ns)
            observed = data[window, columns[pad_name]]
            observed_times = times_ns[window]
            if (len(observed) < 3 or not np.isfinite(observed).all()
                    or observed_times[-1] - observed_times[0] < MIN_STATIC_WITNESS_PS / 1000):
                unresolved.append({"cycle": cycle, "bit": bit, "reason": "DATA witness lacks three samples over 50 ps"})
                continue
            lo, hi = float(observed.min()), float(observed.max())
            stable_correct = hi < LOW if expected == 0 else lo > HIGH
            quiet_and_isolated = bool(
                not event.get("overlap")
                and strong.get("weak_host_off")
                and lane.get("disabled_gate")
                and lane.get("strong_host_on")
                and lane.get("opposition_with_gate_off") is None
                and lane.get("quiet_suffix")
            )
            evidence = {
                "cycle": cycle,
                "bit": bit,
                "expected": expected,
                "window_ns": [begin_ns, end_ns],
                "data_min_v": lo,
                "data_max_v": hi,
                "logic_thresholds_v": {"low_max": LOW, "high_min": HIGH},
                "stable_at_expected_logic": bool(stable_correct),
                "ownership_isolated_and_quiet": quiet_and_isolated,
                "raw_samples": int(len(observed)),
                "observed_span_ps": float((observed_times[-1] - observed_times[0]) * 1000),
                "classification": "NO_PAYLOAD_TRANSITION_REQUIRED"
                if stable_correct and quiet_and_isolated else "UNRESOLVED",
            }
            supplements.append(evidence)
            if evidence["classification"] == "UNRESOLVED":
                unresolved.append(evidence)

    cycle_data_pass = all(row.get("verdict") == "PASS" for row in analysis["cycles"].values())
    unresolved_events = [event for event in ownership if event.get("verdict") != "PASS"]
    ownership_pass = True
    for event in unresolved_events:
        if event.get("verdict") == "PASS":
            continue
        repairs = [s for s in supplements if s["cycle"] == int(event["cycle"])]
        expected_missing = {
            int(lane["bit"])
            for lane in (event.get("strong_check") or {}).get("bits", [])
            if lane.get("charge_response") is None
        }
        observed_repairs = {int(s["bit"]) for s in repairs}
        if (event.get("kind") != "write" or not expected_missing
                or observed_repairs != expected_missing
                or any(s["classification"] != "NO_PAYLOAD_TRANSITION_REQUIRED" for s in repairs)):
            ownership_pass = False
            break
    if not unresolved_events:
        verdict = ("NO_SUPPLEMENT_REQUIRED" if cycle_data_pass and not unresolved
                   and analysis.get("verdict") == "PASS" else "INCONCLUSIVE")
    else:
        verdict = ("PASS_WITH_STATIC_PAYLOAD_WITNESS"
                   if cycle_data_pass and ownership_pass and supplements and not unresolved
                   and analysis.get("verdict") == "INCONCLUSIVO"
                   else "INCONCLUSIVE")
    input_hashes_after = input_artifact_hashes(run)
    require(input_hashes_before == input_hashes_after,
            "Immutable input artifacts changed during static-payload audit")
    report = {
        "source_run": str(run),
        "output_path": str(output),
        "scope": "supplemental observer for payload bits that do not transition",
        "raw_integrated_observer_verdict": analysis["verdict"],
        "supplemental_verdict": verdict,
        "cycles_data_pass": cycle_data_pass,
        "ownership_pass_or_static_witness": ownership_pass and not unresolved,
        "provenance": provenance,
        "supplements": supplements,
        "unresolved": unresolved,
        "qualification": "NOT_CHARACTERIZED",
        "immutable_input_artifacts": input_hashes_before,
        "input_unchanged_during_audit": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True,
                        help="new audit report path outside the immutable input run")
    args = parser.parse_args()
    report = audit(args.run, args.output)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
