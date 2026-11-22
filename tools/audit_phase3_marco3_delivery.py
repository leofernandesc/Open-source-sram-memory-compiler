"""Verify archived Phase 3 evidence and produce machine-readable delivery summaries."""

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from functools import cache
from pathlib import Path


BUILD = Path("build/phase3")
PHYSICAL = Path("reports/phase2/local/phase3_danilo_ss_ff2_spaced")
GDS = PHYSICAL.with_name(PHYSICAL.name + "_gds")
LEF = PHYSICAL.with_name(PHYSICAL.name + "_lef")
LAYOUT = PHYSICAL.with_name(PHYSICAL.name + "_layout")
ROUTE = BUILD / "danilo_ss_ff2_spaced_route"
PEX = BUILD / "danilo_ss_ff2_spaced_pex_sealed"
SS = BUILD / "integrated_ss_20261119_preflight"
TT = BUILD / "integrated_tt_20261120"
SS_REVIEW = BUILD / "bus_review_ss_20261120_report"
TT_REVIEW = BUILD / "integrated_tt_review_20261120"
TT_RAW = BUILD / "data3_tt_20261120"
DIAGNOSIS = BUILD / "data3_tt_diagnosis_final_20261120"
SNM = BUILD / "snm_endpoints_final_20261120"
V2 = BUILD / "sclk_local_driver_20261121_v2"
V2_GATE = BUILD / "sclk_v2_integration_preflight_20261121/final"
PROPOSAL_SHA256 = "59021f96db0202678b9ec4c9f6195fceeb95cfd60a8ecf5c5a3845a72c332644"


@cache
def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def read_csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def require(condition, description):
    if not condition:
        raise ValueError(f"Evidence mismatch: {description}")


def seal(path, expected):
    actual = sha256(path)
    require(actual == expected, f"{path}: expected {expected}, found {actual}")
    return actual


def physical(root):
    gds = read_json(root / GDS / "results.json")
    lef = read_json(root / LEF / "results.json")
    pex = read_json(root / PEX / "manifest.json")
    layout = read_json(root / LAYOUT / "results.json")
    gds_hash = seal(root / GDS / "sram_4x8.gds", gds["artifacts"]["sram_4x8.gds"])
    gds_receipt = seal(root / GDS / "results.json", pex["geometry_receipt_sha256"])
    require(pex["gds_sha256"] == lef["source_gds_sha256"] == gds_hash, "same GDS for LEF/PEX")
    require(gds["status"] == "PASS_GEOMETRY_LVS", "GDS receipt status")
    require(lef["status"] == "PASS_GEOMETRY_ABSTRACT", "LEF receipt status")
    require(pex["status"] == "PASS_RC_STRUCTURE", "PEX receipt status")
    for name in ("magic.txt", "lvs.txt", "reference_mos.spice", "final_extracted.spice"):
        seal(root / GDS / name, gds["artifacts"][name])
    require(gds["drc_markers"] == ["0"] and "FINAL_GDS_DRC=0" in (root / GDS / "magic.txt").read_text(),
            "archived GDS DRC")
    require(gds["lvs"] == "UNIQUE_MATCH_W_L_BODY_MODEL" and
            "Circuits match uniquely." in (root / GDS / "lvs.txt").read_text(), "archived GDS LVS")
    require(gds["mos"] == pex["extraction_stats"]["mos"] == 1749, "MOS count")
    for name in ("sram_4x8.gds", "reference_mos.spice", "results.json"):
        seal(root / LAYOUT / name, gds["inputs"][f"/work/{LAYOUT / name}"])
    seal(root / LAYOUT / "final.v", layout["artifacts"]["final.v"])
    seal(root / ROUTE / "results.json", layout["route_receipt_sha256"])
    seal(root / ROUTE / "routed.v", read_json(root / ROUTE / "results.json")["build_artifacts"]["routed.v"])
    return {
        "gds": gds_hash, "gds_receipt": gds_receipt,
        "lef": seal(root / LEF / "sram_4x8.lef", lef["artifacts"]["sram_4x8.lef"]),
        "pex": seal(root / PEX / "extracted_rc.spice", pex["extraction_stats"]["netlist_sha256"]),
        "extraction_stats": pex["extraction_stats"], "lef_size_um": lef["size_um"],
        "archived_drc_markers": 0, "archived_lvs": gds["lvs"],
    }


def functional(root, identity, run, revised):
    prep = read_json(root / run / "preparation.json")
    sim = read_json(root / run / "simulation.json")
    validation = read_json(root / run / "validation.json")
    review = read_json(root / revised / "review.json")
    corner = prep["conditions"]["corner"]
    require(prep["candidate"]["gds_sha256"] == identity["gds"], f"{corner}: GDS")
    require(prep["candidate"]["physical_receipt_sha256"] == identity["gds_receipt"], f"{corner}: GDS receipt")
    require(prep["pex_sha256"] == review["pex_sha256"] == identity["pex"], f"{corner}: PEX")
    require(sim["simulator_status"] == "PASS" and sim["simulator_returncode"] == 0,
            f"{corner}: archived simulator exit")
    seal(root / run / "preparation.json", sim["preparation_sha256"])
    for name, digest in prep["artifacts"].items():
        seal(root / run / name, digest)
    for name, digest in review["source_sha256"].items():
        source = Path(name)
        if source.is_absolute():
            source = Path("tools") / source.name
        seal(root / source, digest)
    waveform = seal(root / run / "waveform.dat", sim["waveform_sha256"])
    seal(root / run / "ngspice.log", sim["log_sha256"])
    require(waveform == validation["source_waveform_sha256"] == review["source_waveform_sha256"],
            f"{corner}: waveform lineage")
    with (root / run / "waveform.dat").open("rb") as stream:
        require(sum(1 for _ in stream) - 1 == validation["samples"], f"{corner}: waveform sample count")
    cycles = read_csv(root / run / "cycles.csv")
    require(len(cycles) == 18 and len({row["cycle"] for row in cycles}) == 18, f"{corner}: cycles")
    window = read_csv(root / run / "historical_read_window.csv")
    require([(int(row["cycle"]), int(row["bit"]), row["status"]) for row in window] ==
            [(row["cycle"], row["bit"], row["status"]) for row in validation["historical_window"]],
            f"{corner}: diagnostic archive")
    revised_cycles = read_csv(root / revised / "cycles.csv")
    require([(int(row["cycle"]), row["verdict"]) for row in revised_cycles] ==
            [(row["cycle"], row["verdict"]) for row in review["cycles"]], f"{corner}: ownership review CSV")
    require([(int(row["cycle"]), row["operation_status"], row["ownership_status"]) for row in cycles] ==
            [(row["cycle"], row["operation_status"], row["ownership_status"]) for row in validation["cycles"]],
            f"{corner}: original verdict CSV")
    require(len(revised_cycles) == 18, f"{corner}: ownership review coverage")
    by_operation = {
        op: dict(Counter(row["operation_status"] for row in cycles if row["operation"] == op))
        for op in ("read", "write")
    }
    transitions = [row["measurement"] for row in validation["reads"]
                   if row["measurement"] and row["measurement"]["tACCESS_s"] is not None]
    access_ns = [row["tACCESS_s"] * 1e9 for row in transitions]
    transition_ps = [bit["tCLK_TO_DATA_s"] * 1e12 for row in transitions for bit in row["bits"]
                     if bit["tCLK_TO_DATA_s"] is not None]
    expected_status = "PASS" if corner == "ss" else "FAIL"
    require(review["revised_functional_verdict"] == expected_status, f"{corner}: revised verdict")
    return {
        "status": expected_status, "conditions": prep["conditions"], "guard_ns": prep["guard_ns"],
        "samples": validation["samples"], "simulator_wall_s": sim["elapsed_s"],
        "waveform_sha256": waveform, "fixture_sha256": prep["artifacts"]["fixture.json"],
        "counts": by_operation,
        "write_rows": sorted({int(row["expected_address"]) for row in cycles if row["operation"] == "write"}),
        "ownership_original": dict(Counter(row["ownership_status"] for row in cycles)),
        "ownership_revised": dict(Counter(row["verdict"] for row in revised_cycles)),
        "ownership_unresolved_revised": [int(row["cycle"]) for row in revised_cycles if row["verdict"] != "PASS"],
        "read_window_diagnostic": dict(Counter(row["status"] for row in validation["historical_window"])),
        "read_window_diagnostic_failures": [[row["cycle"], row["bit"]]
                                            for row in validation["historical_window"] if row["status"] == "FAIL"],
        "read_mismatches": [row for row in cycles if row["operation"] == "read" and row["operation_status"] == "FAIL"],
        "diagnostic_access_ns": [min(access_ns), max(access_ns)],
        "diagnostic_access_count": len(access_ns),
        "diagnostic_clk_to_data_ps": [min(transition_ps), max(transition_ps)],
        "diagnostic_clk_to_data_count": len(transition_ps),
    }


def snm(root, output):
    published = read_json(root / SNM / "reproduction.json")
    path = root / SNM / "audit.json"
    digest = seal(path, published["identical_replay_sha256"][str(SNM / "audit.json")])
    sample_rows = []
    summary_rows = []
    all_seeds = set()
    modes = read_json(path)["modes"]
    for mode, expected_count in (("hold", 200), ("read", 206)):
        mode_audit = modes[mode]
        entries = mode_audit["entries"]
        summary = mode_audit["summary"]
        seeds = {entry["seed"] for entry in entries}
        require(len(seeds) == len(entries) == expected_count and not (seeds & all_seeds), f"{mode}: unique seeds")
        all_seeds.update(seeds)
        require(all(entry["verdict"] == "VALID" and entry["point_count"] == 1801 for entry in entries),
                f"{mode}: valid DC VTC entries")
        require(summary["model_sections"] == {"tt_mm": {
            "mismatch": 1, "global_process": 0, "fet_parameters": "parameters_fet_tt.spice"
        }}, f"{mode}: mismatch domain")
        require((summary["domain"]["vdd"], summary["domain"]["temp_c"]) == (1.8, 27.0), f"{mode}: PVT")
        recovered = [entry["seed"] for entry in entries if entry["original_status"] == "ERROR"]
        require(recovered == ([] if mode == "hold" else [30005, 30021, 30053, 30090, 30148, 30192]),
                f"{mode}: recovered seeds")
        values = [entry["snm_v"] for entry in entries]
        revision = summary["offline_revised"]
        require(revision["count"] == expected_count and
                math.isclose(statistics.mean(values), revision["mean_v"]) and
                math.isclose(statistics.stdev(values), revision["sample_std_v"]),
                f"{mode}: independently computed summary")
        for entry in entries:
            sample_rows.append(dict(mode=mode, seed=entry["seed"], historical_status=entry["original_status"],
                                    status=entry["verdict"], snm_mv=entry["snm_v"] * 1000,
                                    vtc_sha256=entry["vtc_sha256"]))
        ci_lo, ci_hi = revision["mean_ci95_v"]
        summary_rows.append(dict(mode=mode, corner="tt_mm", vdd_v=1.8, temp_c=27,
                                 seeds=expected_count, recovered=len(recovered),
                                 mean_mv=statistics.mean(values) * 1000,
                                 sample_std_mv=statistics.stdev(values) * 1000,
                                 median_mv=statistics.median(values) * 1000,
                                 min_mv=min(values) * 1000, max_mv=max(values) * 1000,
                                 ci95_mean_lo_mv=ci_lo * 1000, ci95_mean_hi_mv=ci_hi * 1000))
    write_csv(output / "snm_samples.csv", sample_rows)
    write_csv(output / "snm_summary.csv", summary_rows)
    return {"audit_sha256": digest, "modes": summary_rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new output directory")
    args = parser.parse_args()
    root = args.repo.resolve()
    proposal = seal(args.proposal, PROPOSAL_SHA256)
    identity = physical(root)
    ss = functional(root, identity, SS, SS_REVIEW)
    tt = functional(root, identity, TT, TT_REVIEW)
    require(ss["fixture_sha256"] == tt["fixture_sha256"] and ss["guard_ns"] == tt["guard_ns"] == 1.5,
            "shared fixture and guard")
    decks = [(root / run / "bench.spice").read_text() for run in (SS, TT)]
    require(decks[0].replace('sky130.lib.spice" ss', 'sky130.lib.spice" tt', 1) == decks[1],
            "only the SKY130 .lib section changes in the integrated decks")
    require(all(sha256(root / SS / name) == sha256(root / TT / name)
                for name in ("binding.spice", "fabric.spice", "model_hashes.json", "probes.json")),
            "integrated RC/fixture/model-manifest equivalence")
    reduced = read_json(root / DIAGNOSIS / "diagnosis.json")["cases"]["reduced_tt"]
    diagnosis_waveform = seal(root / TT_RAW / "waveform.dat", reduced["waveform_sha256"])
    reduced_run = read_json(root / TT_RAW / "simulation.json")
    seal(root / TT_RAW / "preflight.json", reduced_run["preflight_sha256"])
    require(reduced["candidate"]["gds_sha256"] == identity["gds"] and
            reduced_run["waveform_sha256"] == diagnosis_waveform and
            reduced["cell_correct_through_all_reduced_observations"] and
            reduced["reproduced_same_readback_failure"], "reduced TT storage and sense diagnostic")
    v2 = read_json(root / V2 / "analysis.json")
    v2_run = read_json(root / V2 / "run/result.json")
    for name in ("bench.spice", "driver_cell.spice", "waveform.dat", "currents.dat"):
        seal(root / V2 / "run" / name, v2_run["artifacts"][name])
    preflight = read_json(root / V2_GATE / "manifest.json")
    require(preflight["pex_sha256"] == read_json(root / V2 / "manifest.json")["pex_sha256"] ==
            identity["pex"], "v2 PEX lineage")
    require(v2["verdict"] == "FUNCTIONAL_WITH_INTEGRATION_RISK" and v2["functionally_correct"] and
            preflight["assessment"] == "COMPACT_BOUNDARY_PARTIALLY_DEFINED" and
            not preflight["simulation_authorized"], "v2 scope and integration gate")

    args.output.mkdir(parents=True, exist_ok=False)
    payload = dict(status="ARCHIVED_EVIDENCE_VERIFIED", simulator_invocations=0, proposal_sha256=proposal,
                   physical=identity, integrated=dict(ss=ss, tt=tt, ff="NOT_RUN"),
                   reduced_tt_waveform_sha256=diagnosis_waveform,
                   v2_reduced=v2["verdict"], v2_integration=preflight["assessment"], snm=snm(root, args.output))
    (args.output / "verification.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(payload["status"])


if __name__ == "__main__":
    main()
