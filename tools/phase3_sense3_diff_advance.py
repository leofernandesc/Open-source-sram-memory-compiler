#!/usr/bin/env python3
"""Check the rail feasibility of a differential-only sense-3 replay, without SPICE."""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import re

import numpy as np

from analyze_phase3_sense3_isolation import assess_event
from diagnose_phase3_sclk_startup import write_json
from phase3_rc_read_path import HIGH, LOW
from phase3_sense3_precondition import (
    BUILD, PARENT, PDK, REFERENCE, ROOT, START, STOP, checked_preparation, grid,
    model_closure, pinned, pwl_tokens, read_receipt, read_wave, require, sample,
    sha256, validate_authorization,
)


HISTORY = BUILD / "sense3_preconditioned_20261120"
ADVANCE_NS = 0.182  # Match the sole rise shift of the archived ideal contrast.
ARCHIVE_HASHES = {
    "manifest.json": "77c4074ee89750e32f2fa2cd7c8ff86ea784c5fcf06f96b4ce122444f7e6cea2",
    "control_gate.json": "9b98a8ed3e1eef0651f98b8db9dbefd2520692cfb293f96c0cb961a113589716",
    "contrast_gate.json": "b6655d7adebfd0d0f2a86797899ac76af70d8dce3dc8495d61e567bbf385466b",
}


def read_json(path):
    return json.loads(path.read_text())


def read_sources(path):
    sources = {}
    for card in re.split(r"\n(?=VPORT\d+ )", path.read_text()):
        header = card.partition(" PWL(")[0].split()
        if len(header) < 2 or header[1] not in {"rc8202", "rc8216", "VDD"}:
            continue
        head, pairs = pwl_tokens(card)
        require(head.split()[2] == "VSS" and head.split()[1] not in sources,
                "Unexpected BL/BLB/VDD boundary")
        knots = np.asarray(pairs, dtype=float).T
        require(knots[0, 0] == 0 and knots[0, -1] == STOP - START, "Invalid PWL horizon")
        sources[header[1]] = knots
    require(sources.keys() == {"rc8202", "rc8216", "VDD"}, "Incomplete source inventory")
    return sources


def reconstruct(bl, blb, target_delta, vdd):
    """Unique sources with the requested differential and fixed common mode."""
    common = (bl + blb) / 2
    left, right = common - target_delta / 2, common + target_delta / 2
    return {
        "bl_control_v": bl, "blb_control_v": blb, "vdd_v": vdd,
        "common_v": common, "delta_control_v": blb - bl, "delta_advanced_v": target_delta,
        "bl_required_v": left, "blb_required_v": right,
        "rail_capacity_v": 2 * np.minimum(common, vdd - common),
        "upper_excess_v": np.maximum(left, right) - vdd,
    }


def trajectory(sources, reference_ns):
    t = np.asarray(reference_ns) - START
    bl = np.interp(t, *sources["rc8202"])
    blb = np.interp(t, *sources["rc8216"])
    target = np.interp(t + ADVANCE_NS, *sources["rc8216"]) - np.interp(t + ADVANCE_NS, *sources["rc8202"])
    return reconstruct(bl, blb, target, np.interp(t, *sources["VDD"]))


def feasible_spans(times, *slacks):
    """Intersect linear inequalities at common PWL knots, adding exact roots."""
    spans = []
    for i, (start, stop) in enumerate(zip(times[:-1], times[1:], strict=True)):
        left, right = start, stop
        for slack in slacks:
            a, b = slack[i:i + 2]
            if max(a, b) < 0:
                left = right
                break
            if min(a, b) < 0:
                root = start + (stop - start) * a / (a - b)
                if a < 0:
                    left = max(left, root)
                else:
                    right = min(right, root)
        if left < right:
            if spans and spans[-1][1] == left:
                spans[-1][1] = float(right)
            else:
                spans.append([float(left), float(right)])
    return spans


def verify_archive():
    for name, digest in ARCHIVE_HASHES.items():
        pinned(HISTORY / name, digest)
    validate_authorization(HISTORY)
    manifest = read_json(HISTORY / "manifest.json")
    for path, digest in manifest["source_sha256"].items():
        pinned(ROOT / path, digest)
    physical = checked_preparation(PARENT)
    require(physical["pex_sha256"] == manifest["pex_sha256"], "PEX identity changed")
    models = read_json(REFERENCE / "model_hashes.json")
    require(model_closure(PDK) == models, "Installed SKY130A model closure changed")

    control = read_receipt(HISTORY, "control")
    ideal = read_receipt(HISTORY, "contrast")
    ideal_gate = read_json(HISTORY / "contrast_gate.json")
    pinned(HISTORY / "contrast/result.json", ideal_gate["result_sha256"])
    require(ideal["status"] == "COMPLETED" and ideal_gate["verdict"] == "CORROBORATED"
            and manifest["criteria"]["contrast_fidelity"]["displacement_ps"] == ADVANCE_NS * 1000,
            "Prior isolated SCLK reference changed")
    deck = HISTORY / "control"
    counts = Counter(line.split()[0][0] for line in (deck / "slice.spice").read_text().splitlines())
    require(counts == {"X": 36, "R": 493, "C": 968}, "Unexpected MOS/R/C inventory")
    require((deck / "clk_delta.spice").read_text() == "VSHIFT sclk_driver rc8562 0\n",
            "Control must use the original SCLK")
    return manifest, control, read_json(HISTORY / "control_gate.json"), dict(counts), len(models)


def cycle_evidence(trace, baseline, sources):
    case = baseline["window"]
    event = assess_event(trace, case)
    require(event["decision"] == "WRONG" and event["stable_decision"]["through_ns"] == case["capture_ns"]
            and baseline["clock_valid"] and baseline["conditioning_valid"]
            and baseline["tail"]["envelope_compatible"] and baseline["input"]["eligible"],
            f"The control for c{case['cycle']} is no longer qualified")
    onset = baseline["tail"]["tail_conduction"][0]["start_ns"]
    tail20, tail50 = event["activation"]["at_ns"], event["tail50"]["at_ns"]
    correct_sign, wrong_sign = (event["latch_polarity_crossings_ns"][key][0] for key in ("rise", "fall"))
    early_start, early_end = case["early_input_window_ns"]
    markers = {
        "initial": case["conditioning_ns"], "tail20": tail20, "tail_1ua": onset,
        "tail50": tail50, "first_correct_sign": correct_sign, "inversion": wrong_sign,
        "stable_wrong": event["stable_decision"]["from_ns"], "capture": case["capture_ns"],
    }
    start, stop = early_start - 0.3, correct_sign + 1.1
    t = np.unique(np.concatenate([
        [start, stop, early_start, early_end, *[x for x in markers.values() if start < x < stop]],
        *[pwl[0] + START for pwl in sources.values()],
        *[sources[name][0] + START - ADVANCE_NS for name in ("rc8202", "rc8216")],
    ]))
    t = t[(t >= start) & (t <= stop)]
    data = trajectory(sources, t)
    early = (t >= early_start) & (t <= early_end)
    early_capacity = float(max(data["rail_capacity_v"][early]))
    if early_capacity < 0:
        verdict = "NO_RAIL_BOUNDED_PAIR_AT_FIXED_CM_IN_EARLY_WINDOW"
    else:
        verdict = "FURTHER_FEASIBILITY_REVIEW_REQUIRED"
    left, right, vdd = (data[key] for key in ("bl_required_v", "blb_required_v", "vdd_v"))
    spans = feasible_spans(t, left, right, vdd - left, vdd - right, data["delta_advanced_v"])
    signal_names = ("sclk_root", "sclk_sampler_bl", "sclk_sampler_blb", "sclk_tail", "precharge", "vdd",
                    "bl_at_sense", "blb_at_sense", "sense_tail", "tail_id", "sa_center", "sab_center",
                    "sense_out", "sense_bar", "read_d")
    table = []
    for label, when in markers.items():
        values = {key: float(value) for key, value in trajectory(sources, when).items()}
        values.update({key: float(sample(trace, key, when)) for key in signal_names})
        values["sense_delta_v"] = values["blb_at_sense"] - values["bl_at_sense"]
        values["sense_common_v"] = (values["blb_at_sense"] + values["bl_at_sense"]) / 2
        table.append(dict(cycle=case["cycle"], marker=label, reference_ns=when, **values))
    timing_grid = grid(start, stop, trace)
    samples = {key: sample(trace, key, timing_grid) for key in signal_names}
    evidence = dict(
        cycle=case["cycle"], decision=event["decision"], control_stable=event["stable_decision"],
        stage="OFFLINE_BOUNDARY", verdict=verdict, early_window_reference_ns=[early_start, early_end],
        max_early_capacity_v=early_capacity, max_native_step_in_plot_ps=float(max(np.diff(timing_grid)) * 1000),
        min_early_upper_excess_v=float(min(data["upper_excess_v"][early])),
        rail_legal_target_spans_reference_ns=spans,
        peak_original_blb_v=float(max(data["blb_control_v"])),
        peak_required_blb_v=float(max(data["blb_required_v"])),
        archived_sclk_edges=event["clock"], markers=table,
        control_tail_peak_a=baseline["tail"]["tail_conduction"][0]["peak_abs_current_a"],
        control_ntail_max_error_v=abs(baseline["tail"]["peak_delta_v"]),
    )
    return evidence, (t, data, timing_grid, samples)


def plot(paired, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 2, figsize=(12, 8), sharex="col", layout="constrained")
    for col, (evidence, (t, data, native, samples)) in enumerate(paired):
        a, b, c = axes[:, col]
        markers = {row["marker"]: row["reference_ns"] for row in evidence["markers"]}
        offset = markers["tail20"]
        x = (t - offset) * 1000
        xn = (native - offset) * 1000
        a.plot(x, data["delta_control_v"] * 1e3, label="Δ de fronteira, controle")
        a.plot(x, data["delta_advanced_v"] * 1e3, "--", label="Δ alvo (+182 ps), cálculo")
        a.plot(x, data["rail_capacity_v"] * 1e3, ":", label="Capacidade com CM fixo")
        a.axhline(0, color="0.6", linewidth=0.7)
        a.set_title(f"c{evidence['cycle']} · TT")
        a.set_ylabel("Diferencial (mV)")
        b.plot(x, data["common_v"], label="CM de fronteira, controle")
        b.plot(x, data["blb_control_v"], label="BLB de fronteira, controle")
        b.plot(x, data["blb_required_v"], "--", label="BLB requerida, cálculo")
        b.plot(x, data["vdd_v"], ":", label="VDD")
        b.set_ylabel("Tensão (V)")
        c.plot(xn, samples["sclk_tail"], label="Gate do tail")
        c.plot(xn, samples["sense_bar"] - samples["sense_out"], label="SAB − SA")
        c.plot(xn, samples["sense_tail"], label="NTAIL")
        c.set(xlabel="Tempo em relação ao SCLK20 do controle (ps)", ylabel="Controle (V)")
        for ax in (a, b, c):
            window = (np.asarray(evidence["early_window_reference_ns"]) - offset) * 1000
            ax.axvspan(*window, color="0.8", alpha=0.35)
            ax.axvline((markers["tail_1ua"] - offset) * 1000, color="0.45", linestyle=":", linewidth=0.9)
            ax.axvline((markers["inversion"] - offset) * 1000, color="0.45", linestyle="--", linewidth=0.9)
            ax.grid(alpha=.25)
        if col == 0:
            for ax in (a, b, c):
                ax.legend(loc="best", fontsize=8)
    fig.suptitle("Antecipação diferencial sem margem nos trilhos durante a avaliação inicial")
    fig.savefig(output, dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    out = args.output
    require(out.is_dir() and not (out / "manifest.json").exists(), "Use a fresh output directory")
    manifest, control, gate, counts, model_count = verify_archive()
    trace = read_wave(HISTORY / "control")
    c15_times = grid(199.5, 200., trace)
    c15 = {
        "stable_1_window_ns": [199.5, 200.],
        "min_sense_v": float(min(sample(trace, "sense_out", c15_times))),
        "max_complement_v": float(max(sample(trace, "sense_bar", c15_times))),
        "min_d_v": float(min(sample(trace, "read_d", c15_times))),
        "ntail_188_v": float(sample(trace, "sense_tail", 188.)),
        "ntail_208_v": float(sample(trace, "sense_tail", 208.)),
    }
    require(min(c15["min_sense_v"], c15["min_d_v"]) >= HIGH and c15["max_complement_v"] <= LOW,
            "Control no longer shows the c15 predecessor decision")
    sources = read_sources(HISTORY / "control/stimuli.spice")
    paired = [cycle_evidence(trace, baseline, sources) for baseline in gate["comparisons"]]
    cases = [case for case, _ in paired]
    blocked = all(case["verdict"] == "NO_RAIL_BOUNDED_PAIR_AT_FIXED_CM_IN_EARLY_WINDOW" for case in cases)
    rows = [row for case in cases for row in case["markers"]]
    with (out / "markers.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    with (out / "trajectories.csv").open("x", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["cycle", "reference_ns", *paired[0][1][1]])
        for case, (t, data, _, _) in paired:
            writer.writerows(zip([case["cycle"]] * len(t), t, *data.values(), strict=True))
    plot(paired, out / "rail_feasibility.png")
    write_json(out / "manifest.json", dict(
        schema="phase3.sense3_diff_advance.preflight.v1", advance_ps=ADVANCE_NS * 1000,
        advance_basis="Match prior 182 ps isolated rise shift without changing SCLK",
        proposed_trajectory="D(t+182 ps) at fixed CM(t), evaluated on common PWL knots",
        preflight="NOT_READY" if blocked else "FURTHER_FEASIBILITY_REVIEW_REQUIRED",
        control_gate="VALIDATED", contrast_status="NOT_RUN", causal_verdict="INCONCLUSIVE",
        runs=0, conditions=manifest["conditions"], pex_sha256=manifest["pex_sha256"],
        ports={node: manifest["ports"][node] for node in sources}, topology=counts,
        model_closure_count=model_count, model_hashes_sha256=sha256(REFERENCE / "model_hashes.json"),
        archive_hashes=ARCHIVE_HASHES, control_artifacts=control["artifacts"], control_sample_count=len(trace.rows),
        control_receipt_sha256=sha256(HISTORY / "control/result.json"), control_c15=c15, cycles=cases,
        expander_sha256=sha256(Path(__file__)),
        artifacts_sha256={name: sha256(out / name) for name in
                          ("markers.csv", "trajectories.csv", "rail_feasibility.png")},
    ))
    print(f"{'NOT_READY' if blocked else 'REVIEW_REQUIRED'} / NOT_RUN, {len(trace.rows)} control samples")


if __name__ == "__main__":
    main()
