#!/usr/bin/env python3
"""Replay the archived integrated observer with an explicit sense topology.

The archived observer defaults to the v6 topology (StrongARM on bits 3, 6, 7).
For the virtual eight-lane candidate, set both imported topology constants before
loading integrated_review. Results are written to an isolated analysis directory;
the evidence directory is treated as read-only.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
import sys
from pathlib import Path
import numpy as np


def isolated_input_tree(source: Path, destination: Path) -> None:
    """Create a symlink-only input view, with observer outputs kept private."""
    output_names = {
        "analysis.json", "historical_observer.json", "revised_ownership.json",
        "cycles.csv", "static_payload_witness.json", "topology_classification.json",
    }
    destination.mkdir(parents=True, exist_ok=False)
    for item in source.iterdir():
        target = destination / item.name
        if item.is_dir():
            target.symlink_to(item, target_is_directory=True)
        elif item.name not in output_names:
            target.symlink_to(item)


if not hasattr(hashlib, "file_digest"):
    def file_digest(stream, name):
        digest = hashlib.new(name)
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
        return digest
    hashlib.file_digest = file_digest
if not hasattr(np, "trapezoid"):
    np.trapezoid = np.trapz

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("run", type=Path, help="immutable integrated evidence directory")
parser.add_argument("--archive-root", type=Path, required=True,
                    help="historical checkout root containing build/phase3 and tools")
parser.add_argument("--topology", choices=("v6", "virtual-eight"), required=True)
parser.add_argument("--output-run", type=Path, required=True,
                    help="new directory for derived observer outputs")
parser.add_argument("--fixture-reference", type=Path,
                    help="pinned adjusted fixture directory for the 247.5 ns idle profile")
args = parser.parse_args()
run = args.run.resolve(strict=True)
root = args.archive_root.resolve(strict=True)
out = args.output_run.resolve()
if not (root / "build/phase3/strongarm_functional_closure_20261122").is_dir():
    parser.error("archive root does not contain the expected historical closure")
if out == run or out in run.parents or run in out.parents:
    parser.error("output-run must be separate from the evidence directory")
if out.exists():
    parser.error(f"output-run already exists: {out}")
closure = root / "build/phase3/strongarm_functional_closure_20261122"
triple = root / "build/phase3/strongarm_triple_20261122"
os.chdir(root)
for directory in (root / "tools", triple, closure):
    sys.path.insert(0, str(directory))

# The historical module imported BITS at module scope; set the canonical source
# and consumer globals before importing integrated_review.
import closure_prepare
import analyze_triple
selected_bits = tuple(range(8)) if args.topology == "virtual-eight" else (3, 6, 7)
closure_prepare.BITS = selected_bits
analyze_triple.BITS = selected_bits

# The historical current-overlap helper reduces an empty probe list with
# np.max(), aborting a topology replay. Keep the measurement explicitly
# inconclusive when the evidence has no current probes for that class.
historical_current_overlap = analyze_triple.current_overlap


def current_overlap_with_missing_probe_guard(tail_t, tail, devices, sclk):
    if not devices:
        return {
            "status": "INCONCLUSIVE",
            "reason": "no reset/precharge current probes in this lane map",
            "intervals_ns": None,
            "duration_ps": None,
            "duration_at_sclk_high_ps": None,
            "tail_charge_during_overlap_fc": None,
        }
    return historical_current_overlap(tail_t, tail, devices, sclk)


analyze_triple.current_overlap = current_overlap_with_missing_probe_guard
import integrated_review
from review_phase3_bus_ss import STRESS_WITNESS_NS, WITNESS_NS

if args.fixture_reference is not None:
    reference = args.fixture_reference.resolve(strict=True)
    source_preflight = json.loads((reference / "preflight.json").read_text())
    run_preflight = json.loads((run / "preflight.json").read_text())
    expected_pex = "a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f"
    expected_gds = "315c2ebceb2bc4cf258fa63be2279843805db3010637d0c273aea9db12813e37"
    assert source_preflight == run_preflight
    topology_gates = {"virtual-eight": "VIRTUAL_ECO_READY", "v6": "PHYSICAL_V6_READY"}
    assert source_preflight["gate"] == "READY"
    assert source_preflight["topology"] == topology_gates[args.topology]
    assert source_preflight["physical_pex_sha256"] == expected_pex
    assert source_preflight["gds_sha256"] == expected_gds
    assert source_preflight["c12_idle_start_ns"] == 247.5
    assert source_preflight["stop_ns"] == 370 and source_preflight["guard_ns"] == 1.5
    if args.topology == "v6":
        from phase3_replay_v6_integrated import validate as validate_physical_v6
        validate_physical_v6(run, source_preflight["corner"].upper())
        assert source_preflight["outputs"]["fixture.json"] == (
            "95b78b73de0aaeadaf37a508168fdd124c19b79c03f2573ba23d2320b9f7b61d"
        )
    else:
        from phase3_replay_integrated_idle import validate as validate_virtual_eight
        validate_virtual_eight(run, source_preflight["corner"].upper())
    assert source_preflight["outputs"]["fixture.json"] == hashlib.sha256((run / "fixture.json").read_bytes()).hexdigest()
    assert all(hashlib.sha256((run / name).read_bytes()).hexdigest() == digest
               for name, digest in source_preflight["outputs"].items())
    assert hashlib.sha256((reference / "fixture.json").read_bytes()).hexdigest() == source_preflight["outputs"]["fixture.json"]
    # The historical observer pins the old c12 fixture at module scope. Point
    # that comparison to this independently verified adjusted stimulus.
    integrated_review.HISTORICAL = reference

isolated_input_tree(run, out)
status = integrated_review.analyze(out)
analysis = json.loads((out / "analysis.json").read_text())
fixture = json.loads((run / "fixture.json").read_text())
simulation = json.loads((run / "simulation.json").read_text())
preflight = json.loads((run / "preflight.json").read_text())
model_hashes_sha256 = hashlib.sha256((run / "model_hashes.json").read_bytes()).hexdigest()
expected_reads = sum(row.get("operation") == "read" for row in fixture["cycles"])
architecture = Counter(
    lane.get("internal", {}).get("architecture", "MISSING")
    for cycle in analysis["cycles"].values()
    if cycle.get("operation") == "read"
    for lane in cycle.get("lanes", [])
)
expected_lanes = expected_reads * 8
expected_sa_lanes = expected_reads * len(selected_bits)
expected_native_lanes = expected_reads * (8 - len(selected_bits))
expected_architecture = {
    key: value for key, value in {
        "StrongARM PEX": expected_sa_lanes,
        "native": expected_native_lanes,
    }.items() if value
}
lane_coverage = []
for cycle_id, cycle in analysis["cycles"].items():
    if cycle.get("operation") != "read":
        continue
    lanes = cycle.get("lanes", [])
    by_bit = {lane.get("bit"): lane.get("internal", {}).get("architecture") for lane in lanes}
    expected_bits = set(range(8))
    lane_coverage.append({
        "cycle": cycle_id,
        "all_bits_once": len(lanes) == 8 and set(by_bit) == expected_bits,
        "topology_matches": all(
            by_bit.get(bit) == ("StrongARM PEX" if bit in selected_bits else "native")
            for bit in expected_bits
        ),
    })
lane_coverage_gate = "PASS" if (
    len(lane_coverage) == expected_reads
    and all(row["all_bits_once"] and row["topology_matches"] for row in lane_coverage)
) else "FAIL"
preflight_outputs = preflight.get("outputs", {})
preflight_outputs_verified = bool(preflight_outputs) and all(
    hashlib.sha256((run / name).read_bytes()).hexdigest() == expected
    for name, expected in preflight_outputs.items()
)
receipt_integrity = {
    "simulation_completed": simulation.get("status") == "COMPLETED",
    "returncode_zero": simulation.get("returncode") == 0,
    "no_simulator_errors": not simulation.get("errors"),
    "duration_is_370ns": simulation.get("simulation_ns") == 370.0,
    "waveform_hash_matches_receipt": hashlib.sha256((run / "waveform.dat").read_bytes()).hexdigest() == simulation.get("waveform_sha256"),
    "currents_hash_matches_receipt": hashlib.sha256((run / "currents.dat").read_bytes()).hexdigest() == simulation.get("currents_sha256"),
    "log_hash_matches_receipt": hashlib.sha256((run / "ngspice.log").read_bytes()).hexdigest() == simulation.get("log_sha256"),
    "model_manifest_hash_matches_receipt": model_hashes_sha256 == simulation.get("model_check", {}).get("manifest_sha256"),
    "preflight_hash_matches_receipt": hashlib.sha256((run / "preflight.json").read_bytes()).hexdigest() == simulation.get("preflight_sha256"),
    "preflight_receipt_verified": simulation.get("preflight_outputs_verified") is True,
    "preflight_outputs_verified": preflight_outputs_verified,
    "model_hash_count": simulation.get("model_check", {}).get("sha256_matches"),
}
receipt_integrity_gate = "PASS" if all(
    value is True for key, value in receipt_integrity.items() if key != "model_hash_count"
) and receipt_integrity["model_hash_count"] == 319 else "FAIL"
classification = {
    "topology_argument": args.topology,
    "strongarm_bits_configured": list(selected_bits),
    "expected_read_cycles": expected_reads,
    "expected_read_lanes": expected_lanes,
    "observed_architecture_counts": dict(architecture),
    "classification_gate": "PASS" if dict(architecture) == expected_architecture else "FAIL",
    "per_read_lane_coverage": lane_coverage,
    "lane_coverage_gate": lane_coverage_gate,
    "receipt_integrity": receipt_integrity,
    "receipt_integrity_gate": receipt_integrity_gate,
    "p1_replay_gate": "PASS" if (
        dict(architecture) == expected_architecture
        and lane_coverage_gate == "PASS"
        and receipt_integrity_gate == "PASS"
    ) else "FAIL",
    "integrated_observer_verdict": status,
    "ownership_witness_policy": {
        "drive_threshold_ns": WITNESS_NS,
        "drive_threshold_ps": WITNESS_NS * 1000,
        "stress_diagnostic_threshold_ns": STRESS_WITNESS_NS,
        "stress_diagnostic_only": True,
    },
    "simulation_status": simulation.get("status"),
    "simulation_ns": simulation.get("simulation_ns"),
    "model_hashes_verified": simulation.get("model_check", {}).get("sha256_matches"),
    "model_manifest_sha256": simulation.get("model_check", {}).get("manifest_sha256"),
    "simulation_sha256": hashlib.sha256((run / "simulation.json").read_bytes()).hexdigest(),
    "log_sha256": hashlib.sha256((run / "ngspice.log").read_bytes()).hexdigest(),
    "waveform_sha256": hashlib.sha256((run / "waveform.dat").read_bytes()).hexdigest(),
}
ownership = json.loads((out / "revised_ownership.json").read_text())
read_to_idle = next((event for event in ownership
                     if event.get("cycle") == 12 and event.get("kind") == "read_to_idle"), None)
if read_to_idle:
    probe = read_to_idle.get("probe", {})
    bit_rows = []
    for bit in probe.get("bits", []):
        conduction = bit.get("conduction")
        duration_ps = conduction.get("conservative_ps") if conduction else None
        release = bit.get("release") or {}
        bit_rows.append({
            "bit": bit.get("bit"),
            "drive_expected": bit.get("drive_expected"),
            "drive_witness_ps": duration_ps,
            "drive_verified_at_50ps": bool(duration_ps is not None and duration_ps >= WITNESS_NS * 1000),
            "stress_100ps_diagnostic_present": bit.get("conduction_100ps") is not None,
            "release_witness_ps": release.get("conservative_ps"),
        })
    classification["ownership_c12_read_to_idle"] = {
        "event_verdict": read_to_idle.get("verdict"),
        "drive_verified": read_to_idle.get("conduction_verified"),
        "release_verified": read_to_idle.get("release_verified"),
        "drive_gate_ns": WITNESS_NS,
        "stress_diagnostic_ns": STRESS_WITNESS_NS,
        "stress_diagnostic_part_of_verdict": False,
        "bits": bit_rows,
        "root_cause": "UNRESOLVED_STIMULUS_OR_BRANCH_CURRENT_OBSERVABILITY_VS_ABSENT_DRIVE",
        "interpretation": "Release after disable does not prove drive before disable; retain INCONCLUSIVE until controlled contrast/witness.",
    }
(out / "topology_classification.json").write_text(json.dumps(classification, indent=2) + "\n")
print(json.dumps({"output": str(out), **classification}, indent=2))
