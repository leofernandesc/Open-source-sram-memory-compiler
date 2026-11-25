#!/usr/bin/env python3
"""Compare raw write ownership gaps across the preserved virtual-eight runs."""
import argparse
import json
from pathlib import Path

import numpy as np

from phase3_audit_integrated_no_transition import sha256
from phase3_rc_read_path import HIGH, LOW, OUTPUT_ENABLES
from run_phase3_integrated_ss import LIMIT_A


def compare(run, corner, observed=None):
    provenance_notes = []
    if observed is not None:
        receipt = json.loads((run / "simulation.json").read_text())
        analysis = json.loads((observed / "analysis.json").read_text())
        classification = json.loads((observed / "topology_classification.json").read_text())
        model_hashes = json.loads((run / "model_hashes.json").read_text())
        if (receipt.get("status") != "COMPLETED" or receipt.get("returncode") != 0
                or receipt.get("errors") or receipt.get("simulation_ns") != 370.0
                or receipt.get("model_check", {}).get("sha256_matches") != 319
                or len(model_hashes) != 319):
            raise ValueError(f"Unverified integrated replay receipt: {corner}")
        for gate in ("p1_replay_gate", "receipt_integrity_gate", "lane_coverage_gate",
                     "classification_gate"):
            if classification.get(gate) != "PASS":
                raise ValueError(f"Integrated observation {corner}: {gate} did not pass")
        if (receipt["waveform_sha256"] != sha256(run / "waveform.dat")
                or analysis["waveform_sha256"] != receipt["waveform_sha256"]):
            raise ValueError(f"Integrated waveform digest mismatch: {corner}")
        events = json.loads((observed / "revised_ownership.json").read_text())
        hashes = {"waveform.dat": receipt["waveform_sha256"]}
    elif corner == "FF":
        report = json.loads((run / "integrated_ff_diagnostic.json").read_text())
        events = report["ownership_cycles"]
        hashes = dict(report["source_sha256"])
        manifest_path = run / "diagnostic_run_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        # The final manifest contains the hash of the diagnostic report itself.
        # Its pre-analysis digest in that report is necessarily stale after sealing.
        historical_manifest_hash = hashes.pop("diagnostic_run_manifest.json")
        if manifest["outputs"]["integrated_ff_diagnostic.json"] != sha256(run / "integrated_ff_diagnostic.json"):
            raise ValueError("Final FF manifest does not bind the diagnostic analysis")
        if manifest["pex_sha256"] != report["preflight_pex_sha256"]:
            raise ValueError("FF PEX identity mismatch")
        for name, expected in manifest["outputs"].items():
            if sha256(run / name) != expected:
                raise ValueError(f"Final FF manifest output mismatch: {name}")
        if historical_manifest_hash != sha256(manifest_path):
            provenance_notes.append(dict(
                issue="Report refers to a different pre-analysis manifest digest; final manifest binds report",
                historical_sha256=historical_manifest_hash,
                final_sha256=sha256(manifest_path)))
    else:
        report = json.loads((run / "simulation.json").read_text())
        events = json.loads((run / "revised_ownership.json").read_text())
        hashes = {"waveform.dat": report["waveform_sha256"]}
        derived_manifest = json.loads((run.parent / "manifest.json").read_text())
        relative = f"derived_integrated/{run.name}/revised_ownership.json"
        recorded = [row["sha256"] for row in derived_manifest["derived_outputs"]
                    if row["path"] == relative]
        if len(recorded) != 1:
            raise ValueError(f"Missing derived ownership digest: {relative}")
        hashes["revised_ownership.json"] = recorded[0]
    for name, expected in hashes.items():
        if sha256(run / name) != expected:
            raise ValueError(f"Hash mismatch: {run / name}")
    fixture = json.loads((run / "fixture.json").read_text())["cycles"]
    probes = json.loads((run / "probes.json").read_text())
    path = run / "waveform.dat"
    with path.open() as stream:
        header = stream.readline().lower().split()
    if not header or header[0] != "time" or len(set(header)) != len(header):
        raise ValueError("Invalid waveform header")
    common = ["time", "v(host_en)", "v(host_weak_en)", "v(csb)", "v(oeb)", "v(web)"]
    lanes = [
        [f"v(data{bit})", f"v(xdut.{probes[label]})",
         f"i(v_sense_host{bit})", f"i(v_sense_weak{bit})", f"i(v_dut{bit})"]
        for bit, label in enumerate(OUTPUT_ENABLES)
    ]
    names = common + [name.lower() for lane in lanes for name in lane]
    values = np.loadtxt(path, skiprows=1, usecols=[header.index(name) for name in names])
    t = values[:, 0] * 1e9
    if not np.isfinite(values).all() or not (np.diff(t) > 0).all() or t[-1] < 369.999999:
        raise ValueError("Invalid or incomplete waveform")
    records = []
    for cycle in (2, 10):
        event = events[cycle]
        rec = fixture[cycle]
        if event["cycle"] != cycle or rec["cycle"] != cycle:
            raise ValueError("Cycle identity mismatch")
        strong = event["strong_check"]
        if {row["bit"] for row in strong["bits"]} != set(range(8)):
            raise ValueError("Incomplete lane coverage")
        intervals = {
            "pre_closure": (rec["control_start_ns"], strong["start_ns"]),
            "strong": (strong["start_ns"], strong["end_ns"]),
            "complete": (rec["control_start_ns"], strong["end_ns"]),
        }
        result = dict(corner=corner, cycle=cycle, operation=event["kind"],
                      raw_verdict=event["verdict"], expected=rec["expected"],
                      previous_operation=rec["previous_operation"],
                      release_verified=event["release_verified"],
                      conduction_verified=event["conduction_verified"],
                      host_on_ns=event.get("host_on_ns"),
                      all_released_by_ns=(event.get("probe") or {}).get("all_released_by_ns"),
                      conductance_gap_isolated=event.get("conductance_gap_isolated"),
                      weak_host_off=strong["weak_host_off"], lanes=[])
        for bit, lane in enumerate(strong["bits"]):
            if lane["bit"] != bit:
                raise ValueError("Unexpected lane order")
            expected_high = bool(rec["expected"] & (1 << bit))
            stats = {}
            for name, (start, end) in intervals.items():
                mask = (t >= start) & (t <= end)
                rows = values[mask, 6 + bit * 5:11 + bit * 5]
                times = t[mask]
                if len(rows) < 3:
                    raise ValueError("Insufficient native samples")
                pad, gate, host, weak, dut = rows.T
                opposed = (host*dut < 0) & (abs(host) > LIMIT_A) & (abs(dut) > LIMIT_A)
                opposed_indices = np.flatnonzero(opposed)
                stats[name] = dict(samples=len(rows), first_ns=float(times[0]),
                    last_ns=float(times[-1]), pad_min_v=float(pad.min()),
                    pad_max_v=float(pad.max()), gate_min_v=float(gate.min()),
                    gate_max_v=float(gate.max()),
                    host_peak_abs_ua=float(abs(host).max()*1e6),
                    weak_peak_abs_ua=float(abs(weak).max()*1e6),
                    dut_peak_abs_ua=float(abs(dut).max()*1e6),
                    pad_in_expected_rail=bool((pad >= HIGH).all() if expected_high else (pad <= LOW).all()),
                    dut_samples_above_current_limit=int((abs(dut) > LIMIT_A).sum()),
                    host_dut_opposition_samples=int(len(opposed_indices)),
                    opposition_native_points=[dict(time_ns=float(times[i]),
                        host_ua=float(host[i]*1e6), dut_ua=float(dut[i]*1e6))
                        for i in opposed_indices[:3]])
            result["lanes"].append(dict(bit=bit, expected_high=expected_high,
                charge_witness=lane["charge_response"] is not None,
                disabled_gate=lane["disabled_gate"], strong_host_on=lane["strong_host_on"],
                sustained_opposition=lane["sustained_opposition"],
                opposition_with_gate_off=lane["opposition_with_gate_off"],
                quiet_suffix=lane["quiet_suffix"], intervals=stats))
        records.append(result)
    return dict(corner=corner, waveform_sha256=sha256(path), samples=len(t),
                provenance_notes=provenance_notes, events=records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replay-root", type=Path,
                        help="New 247.5 ns replay directory containing TT/SS/FF")
    parser.add_argument("--observed-root", type=Path,
                        help="Matching observed directory containing TT/SS/FF")
    args = parser.parse_args()
    root = args.evidence.resolve(strict=True)
    if (args.replay_root is None) != (args.observed_root is None):
        parser.error("--replay-root and --observed-root must be provided together")
    if args.replay_root is not None:
        replay = args.replay_root.resolve(strict=True)
        observed = args.observed_root.resolve(strict=True)
        records = [compare(replay / corner, corner, observed / corner)
                   for corner in ("TT", "SS", "FF")]
    else:
        runs = {
            "TT": root / "derived_integrated/virtual_eight_TT_final",
            "SS": root / "derived_integrated/virtual_eight_SS_final",
            "FF": root / "build/phase3/diagnostics/strongarm_eight_integrated_ff_20261124",
        }
        records = [compare(run, corner) for corner, run in runs.items()]
    result = dict(qualification="NOT_CHARACTERIZED",
                  scope="Diagnostic comparison; preserves raw verdicts; native samples only",
                  rail_thresholds_v=[LOW, HIGH], current_limit_a=LIMIT_A,
                  runs=records)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    for run in result["runs"]:
        for event in run["events"]:
            for lane in event["lanes"]:
                if lane["charge_witness"]:
                    continue
                full = lane["intervals"]["complete"]
                strong = lane["intervals"]["strong"]
                print(run["corner"], event["cycle"], lane["bit"],
                      "raw", event["raw_verdict"],
                      "full_static", full["pad_in_expected_rail"],
                      "strong_static", strong["pad_in_expected_rail"],
                      "range", round(full["pad_min_v"], 5), round(full["pad_max_v"], 5),
                      "DUT_peak_uA", round(strong["dut_peak_abs_ua"], 3),
                      "opposition_samples", strong["host_dut_opposition_samples"])


if __name__ == "__main__":
    main()
