#!/usr/bin/env python3
"""Add an explicit static-payload witness for integrated ownership gaps."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from phase3_rc_read_path import HIGH, LOW


def audit(run: Path) -> dict:
    analysis = json.loads((run / "analysis.json").read_text())
    ownership = json.loads((run / "revised_ownership.json").read_text())
    fixture = json.loads((run / "fixture.json").read_text())
    records = {int(row["cycle"]): row for row in fixture["cycles"]}

    with (run / "waveform.dat").open() as stream:
        names = stream.readline().lower().split()
    data = np.loadtxt(run / "waveform.dat", skiprows=1)
    times_ns = data[:, 0] * 1e9
    columns = {name: index for index, name in enumerate(names)}

    supplements = []
    unresolved = []
    for event in ownership:
        cycle = int(event["cycle"])
        strong = event.get("strong_check") or {}
        for lane in strong.get("bits", []):
            if lane.get("charge_response") is not None:
                continue
            bit = int(lane["bit"])
            record = records[cycle]
            expected = (int(record["expected"]) >> bit) & 1
            pad_name = f"v(data{bit})"
            if pad_name not in columns:
                unresolved.append({"cycle": cycle, "bit": bit, "reason": "DATA probe absent"})
                continue
            event_ns = float(record.get("host_payload_ns", strong.get("start_ns")))
            end_ns = float(strong.get("end_ns", event_ns))
            begin_ns = event_ns - 0.1
            window = (times_ns >= begin_ns) & (times_ns <= end_ns)
            observed = data[window, columns[pad_name]]
            if not len(observed):
                unresolved.append({"cycle": cycle, "bit": bit, "reason": "empty DATA observation"})
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
                "classification": "NO_PAYLOAD_TRANSITION_REQUIRED"
                if stable_correct and quiet_and_isolated else "UNRESOLVED",
            }
            supplements.append(evidence)
            if evidence["classification"] == "UNRESOLVED":
                unresolved.append(evidence)

    cycle_data_pass = all(row.get("verdict") == "PASS" for row in analysis["cycles"].values())
    ownership_pass = True
    for event in ownership:
        if event.get("verdict") == "PASS":
            continue
        repairs = [s for s in supplements if s["cycle"] == int(event["cycle"])]
        if not repairs or any(s["classification"] != "NO_PAYLOAD_TRANSITION_REQUIRED" for s in repairs):
            ownership_pass = False
            break
    verdict = "PASS_WITH_STATIC_PAYLOAD_WITNESS" if cycle_data_pass and ownership_pass and not unresolved else "INCONCLUSIVE"
    report = {
        "scope": "supplemental observer for payload bits that do not transition",
        "raw_integrated_observer_verdict": analysis["verdict"],
        "supplemental_verdict": verdict,
        "cycles_data_pass": cycle_data_pass,
        "ownership_pass_or_static_witness": ownership_pass,
        "supplements": supplements,
        "unresolved": unresolved,
        "qualification": "NOT_CHARACTERIZED",
    }
    (run / "static_payload_witness.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    report = audit(args.run.resolve())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
