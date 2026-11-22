#!/usr/bin/env python3
"""Run and audit one rise-only intervention in the extracted sense-3 tail branch."""

import argparse
import csv
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import time

import numpy as np

from analyze_phase3_sclk_r87_full import edge_table, edges, gate_shape, interpret_gate, scalar
from analyze_phase3_sense3_isolation import assess_event
from audit_phase3_sense3_diff_boundary import extract_cards
from diagnose_phase3_sclk_startup import write_json
from phase3_rc_read_path import HIGH, LOW
from phase3_sense3_diff_advance import HISTORY, verify_archive
from phase3_sense3_precondition import (
    BUILD, PDK, REFERENCE, START, STOP, TAIL_ON_A, grid, model_closure, outside, read_wave,
    require, sample, sha256,
)
from review_phase3_bus_ss import ge, le
from run_phase3_eco_pex import ngspice_limits, pinned
from run_phase3_sense3_isolation import SHIFT_PS, SHIFT_WINDOWS, compress, pwl


ORIGINAL_R = "R76 rc8571 rc8585 387.618"
LOCAL_R = "R76 tail_series rc8585 387.618"
INPUTS = ("bench.spice", "stimuli.spice", "slice.spice", "clk_delta.spice")
GATES = ("sclk_sampler_bl", "sclk_sampler_blb", "sclk_tail")
CONTROLS = ("sclk_root", "sclk_local", "precharge", *GATES)
EXTERNAL = ("sclk_root", "precharge", "vdd", "bl_at_cell", "blb_at_cell", "tail_ground")
TIMEOUT = 90


def localized_slice(original, binding):
    cards = extract_cards(original)
    full = extract_cards(binding)
    # The validated control has an existing zero-volt series VSHIFT at R87.
    require(cards.get("R87") == ["sclk_driver", "rc8571", "6.46438"], "Unexpected archived R87")
    cards["R87"] = ["rc8562", *cards["R87"][1:]]
    audited = {}
    for node, expected in {
        "rc8585": {"R76", "X351", "C12300"}, "rc8584": {"R68", "X235", "C12301"},
        "rc8586": {"R60", "X521", "C12299"}, "rc8571": {"R76", "R68", "R60", "R87", "C12280"},
    }.items():
        incident = {key: fields for key, fields in full.items()
                    if node in fields[:4 if key.startswith("X") else 2]}
        require(incident.keys() == expected and all(incident[k] == cards[k] for k in incident),
                f"NOT_READY: changed branch fanout or extracted cards at {node}")
        audited[node] = incident
    require(original.splitlines().count(ORIGINAL_R) == 1 and "tail_series" not in original,
            "NOT_READY: R76 cannot be split at the shared-side terminal")
    return original.replace(ORIGINAL_R, LOCAL_R), audited


def series_stimulus(time_ns, fork_voltage):
    """Use the archived fork's rise difference, leaving the R76 path series-connected."""
    shifted_ns = time_ns + SHIFT_PS / 1000
    knots = [(0., 0.)]
    for begin, end in SHIFT_WINDOWS:
        fade = .025
        times = np.unique(np.r_[begin, end, begin + fade, end - fade,
                                time_ns[(time_ns > begin) & (time_ns < end)],
                                shifted_ns[(shifted_ns > begin) & (shifted_ns < end)]])
        weight = np.clip(np.minimum(times - begin, end - times) / fade, 0, 1)
        delta = weight * (np.interp(times, shifted_ns, fork_voltage) - np.interp(times, time_ns, fork_voltage))
        times, delta = compress(times, delta)
        knots.extend(zip(times - START, delta, strict=True))
    knots.append((STOP - START, 0.))
    t, v = np.asarray(knots).T
    require(np.all(np.diff(t) > 0) and v[0] == v[-1] == 0., "Malformed series PWL")
    return pwl("VTAIL", "tail_series", "rc8571", t, v), dict(
        knots=len(t), min_v=float(min(v)), max_v=float(max(v)), windows_reference_ns=SHIFT_WINDOWS,
        zero_outside_windows=True, source="archived rc8571(t-182 ps) - rc8571(t), tapered at joins",
    )


def d_window(trace, case, correct):
    d = trace.cols["read_d"]
    condition = le(d, LOW) if correct else ge(d, HIGH)
    return trace.signal_window(case["low_ns"], case["capture_ns"], [condition], suffix=True)


def verify_control(trace, cases):
    before = grid(199.5, 200., trace)
    require(min(sample(trace, "sense_out", before)) >= HIGH and max(sample(trace, "sense_bar", before)) <= LOW
            and min(sample(trace, "read_d", before)) >= HIGH, "Archived c15 was not a stable one")
    for case in cases:
        result = assess_event(trace, case)
        require(result["decision"] == "WRONG" and d_window(trace, case, False)
                and result["latch_polarity_crossings_ns"]["rise"]
                and result["latch_polarity_crossings_ns"]["fall"], "Archived c16/c17 failure not reproduced")


def prepare(root):
    require(root.is_dir() and not (root / "preflight.json").exists(), "Use a fresh output directory")
    manifest, control, gate, counts, model_count = verify_archive()
    base = read_wave(HISTORY / "control")
    criteria = manifest["criteria"]
    verify_control(base, criteria["cases"])
    deck = HISTORY / "control"
    changed, audited = localized_slice((deck / "slice.spice").read_text(),
                                       (REFERENCE / "binding.spice").read_text())
    times = np.asarray(base.times)
    stimulus, details = series_stimulus(times, sample(base, "sclk_local", times))
    for case, (_, end) in zip(criteria["cases"], SHIFT_WINDOWS, strict=True):
        shape = gate_shape(base, "sclk_tail", case["low_ns"], case["high_ns"])
        require(end < scalar(shape["fall_ns"]["80"]), "Tail perturbation overlaps recovery")
    target = root / "contrast"
    target.mkdir()
    for name in ("bench.spice", "stimuli.spice"):
        (target / name).write_bytes((deck / name).read_bytes())
    (target / "slice.spice").write_text(changed)
    (target / "clk_delta.spice").write_text((deck / "clk_delta.spice").read_text() + stimulus)
    write_json(root / "preflight.json", dict(
        status="READY_FOR_PAIRED_TEST", archive_gate=gate["verdict"], pex_sha256=manifest["pex_sha256"],
        conditions=manifest["conditions"], criteria=criteria, target_ps=SHIFT_PS,
        topology=counts, direct_incidence=audited, model_closure_files=model_count,
        control_waveform_sha256=control["artifacts"]["waveform.dat"], intervention=details,
        deck_change=[ORIGINAL_R, LOCAL_R, "VTAIL in series with R76"],
        fidelity="Archived 20/50/80% envelopes; 1 uA marker; interpolation on native time grids",
        expected_isolation="No direct cross-cap at rc8585; finite common R87 and MOS feedback remain",
        timeout_s=TIMEOUT, inputs_sha256={name: sha256(target / name) for name in INPUTS},
    ))


def simulate(root):
    preflight = root / "preflight.json"
    receipt = json.loads(preflight.read_text())
    require(receipt["status"] == "READY_FOR_PAIRED_TEST", "Preflight not ready")
    out = root / "contrast"
    require(not (out / "attempt.json").exists(), "This experiment has already been attempted")
    for name, digest in receipt["inputs_sha256"].items():
        pinned(out / name, digest)
    require(model_closure(PDK) == json.loads((REFERENCE / "model_hashes.json").read_text()), "Models changed")
    command = ["stdbuf", "-o0", "-e0", "ngspice", "-n", "-b", "bench.spice"]
    with (BUILD / ".eco_simulator.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (out / "attempt.json").open("x") as attempt:
            json.dump(dict(command=command, timeout_s=TIMEOUT, preflight_sha256=sha256(preflight),
                           inputs_sha256=receipt["inputs_sha256"]), attempt, indent=2)
        started = time.monotonic()
        code, status = None, "INCOMPLETE"
        with (out / "ngspice.log").open("xb", buffering=0) as log:
            try:
                code = subprocess.run(command, cwd=out, stdout=log, stderr=subprocess.STDOUT,
                                      preexec_fn=ngspice_limits, timeout=TIMEOUT, check=False,
                                      env={**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}).returncode
            except subprocess.TimeoutExpired:
                status = "TIMEOUT"
    data = (out / "ngspice.log").read_bytes()
    if (code == 0 and b"No. of Data Rows" in data and all((out / n).is_file() for n in ("waveform.dat", "currents.dat"))
            and not re.search(rb"analysis aborted|timestep too small|fatal error:|transient op failed", data, re.I)):
        status = "COMPLETED"
    write_json(out / "result.json", dict(status=status, elapsed_s=time.monotonic()-started, returncode=code,
                                       artifacts={p.name: sha256(p) for p in out.iterdir() if p.is_file()}))
    print(status, flush=True)


def max_delta(base, trial, names, begin, end):
    t = grid(begin, end, base, trial)
    return {key: float(max(abs(sample(trial, key, t) - sample(base, key, t)))) for key in names}


def branch_measure(trace, case):
    start, stop = case["low_ns"], case["high_ns"] + 8
    t = grid(start, stop, trace)
    current = sample(trace, "tail_id", t)
    current_spans = outside(t, current, TAIL_ON_A)
    command = gate_shape(trace, "precharge", case["low_ns"], case["high_ns"])
    recovery = scalar(command["fall_ns"]["80"])
    overlaps = [[max(a, recovery), b] for a, b in current_spans if b > recovery] if recovery is not None else None
    event = assess_event(trace, case)
    # Include separation before tail20, which can precede a delayed evaluation.
    pair = sample(trace, "sab_sampling_out", t) - sample(trace, "sa_sampling_out", t)
    preeval = (t <= case["capture_ns"])
    event.update(
        latch_sign_crossings_full_ns={name: edges(t[preeval], pair[preeval], 0., rising).tolist()
                                      for name, rising in (("positive", True), ("negative", False))},
        correct_d_until_capture=d_window(trace, case, True),
        wrong_d_until_capture=d_window(trace, case, False),
        tail_peak_ua=float(max(abs(current))*1e6), tail_peak_ns=float(t[int(np.argmax(abs(current)))]),
        tail_above_1ua_ns=current_spans, after_precharge_fall80_spans_ns=overlaps,
        tail_fall90_ns=edge_table(trace, "sclk_tail", case["high_ns"], stop, (90,), False)["90"],
        precharge_fall80_ns=recovery,
        bitline_recovery_50_ns={
            name: edge_table(trace, name, case["high_ns"], stop, (50,), True)["50"]
            for name in ("bl_at_sense", "blb_at_sense")
        },
        precharge_plateau_bitlines_v={n: float(sample(trace, n, stop)) for n in ("bl_at_sense", "blb_at_sense")},
    )
    return event


def decision(cases, c15_ok):
    c16 = cases[0]
    if not c15_ok or not all(c16["checks"].values()):
        return "INCONCLUSIVE"
    current = c16["trial"]
    if current["decision"] == "CORRECT" and current["correct_d_until_capture"]:
        return "TAIL_ONLY_SUFFICIENCY_SUPPORTED"
    if current["decision"] == "WRONG" and current["wrong_d_until_capture"]:
        return "TAIL_ONLY_NOT_SUFFICIENT"
    return "INCONCLUSIVE"


def compare_case(base, trial, case, criteria, window):
    start, end = case["low_ns"], case["high_ns"]
    zero = dict(criteria["contrast_fidelity"], displacement_ps=0)
    edges_by_node = {}
    for node in CONTROLS:
        a, b = (gate_shape(trace, node, start, end) for trace in (base, trial))
        edges_by_node[node] = dict(control=a, trial=b, comparison=interpret_gate(
            a, b, criteria["contrast_fidelity"] if node == "sclk_tail" else zero))
    a, b = (branch_measure(trace, case) for trace in (base, trial))
    before = max_delta(base, trial, (*EXTERNAL, *GATES, "sense_tail", "sense_out", "sense_bar", "read_d",
                                     "bl_at_sense", "blb_at_sense"), case["conditioning_ns"], window[0])
    all_external = max_delta(base, trial, EXTERNAL, start, end + 8)
    # Same source cards. Bound comparison residual by archived replay compression.
    checks = dict(
        delivered_and_other_edges_equivalent=all(item["comparison"]["fidelity_verified"]
                                                 for item in edges_by_node.values()),
        direct_stimulus_equivalent=max(all_external.values()) <= .0001,
        independent_initial_state=(before["sense_tail"] <= criteria["latch_conditioning_error_v"] and
                                   max(v for n, v in before.items() if n != "sense_tail") <= criteria["common_mode_error_v"]),
        recovered_after_evaluation=(b["after_precharge_fall80_spans_ns"] == [] and
                                    min(b["precharge_plateau_bitlines_v"].values()) >= HIGH),
    )
    return dict(cycle=case["cycle"], case=case, control=a, trial=b, edges=edges_by_node,
                before_window_max_delta_v=before, external_source_max_delta_v=all_external,
                gate_waveform_max_delta_v=max_delta(base, trial, CONTROLS, start, end + 8),
                checks=checks)


def export(root, traces, cycles):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = (*EXTERNAL, *GATES, "bl_at_sense", "blb_at_sense", "sense_tail", "tail_id",
             "sense_out", "sense_bar", "sa_sampling_out", "sab_sampling_out", "read_d")
    with (root / "paired.csv").open("x", newline="") as sink:
        writer = csv.writer(sink)
        writer.writerow(("cycle", "run", "reference_ns", *names, "sense_delta_v", "sense_common_v"))
        for row in cycles:
            case = row["case"]
            t = grid(case["low_ns"], case["high_ns"] + 8, *traces)
            for label, trace in zip(("control", "tail_only"), traces, strict=True):
                left, right = (sample(trace, k, t) for k in ("bl_at_sense", "blb_at_sense"))
                writer.writerows(zip([row["cycle"]]*len(t), [label]*len(t), t, *(sample(trace,k,t) for k in names),
                                     right-left, (left+right)/2, strict=True))
    fig, axes = plt.subplots(4, 2, figsize=(12, 8), sharex="col", layout="constrained")
    for col, row in enumerate(cycles):
        case = row["case"]
        t = grid(case["low_ns"], case["capture_ns"], *traces)
        active = (t >= case["tail20_ns"]-.45) & (t <= case["tail20_ns"]+2)
        t = t[active]
        for label, trace, style in zip(("Controle", "Tail atrasado"), traces, ("-", "--"), strict=True):
            x = (t-case["tail20_ns"])*1000
            get = {name: sample(trace, name, t) for name in names}
            for i, (data, ylabel) in enumerate((
                (get["sclk_tail"], "Tail gate (V)"), ((get["blb_at_sense"]-get["bl_at_sense"])*1000, "BLB−BL (mV)"),
                (get["sab_sampling_out"]-get["sa_sampling_out"], "SAB−SA (V)"), (get["tail_id"]*1e6, "I tail (µA)"),
            )):
                axes[i,col].plot(x, data, style, label=label)
                axes[i,col].set_ylabel(ylabel)
                axes[i,col].grid(alpha=.25)
        axes[0,col].set_title(f"c{row['cycle']} · TT")
        axes[3,col].set_xlabel("Tempo em relação ao SCLK20 histórico (ps)")
    axes[0,0].legend()
    fig.savefig(root / "regeneration.png", dpi=160)
    plt.close(fig)


def analyze(root):
    preflight = json.loads((root / "preflight.json").read_text())
    receipt = json.loads((root / "contrast/result.json").read_text())
    for name, digest in receipt["artifacts"].items():
        pinned(root / "contrast" / name, digest)
    result = dict(verdict="INCONCLUSIVE", simulator=receipt["status"], cases=[])
    if receipt["status"] == "COMPLETED":
        base = read_wave(HISTORY / "control")
        trial = read_wave(root / "contrast")
        criteria = preflight["criteria"]
        cycles = [compare_case(base, trial, case, criteria, w)
                  for case, w in zip(criteria["cases"], SHIFT_WINDOWS, strict=True)]
        first_sample = max(base.times[0], trial.times[0])
        c15 = max_delta(base, trial, ("sense_tail", "sense_out", "sense_bar", "read_d", *GATES),
                        first_sample, SHIFT_WINDOWS[0][0])
        checkpoint = grid(199.5, 200., trial)
        ok = bool(c15["sense_tail"] <= criteria["latch_conditioning_error_v"] and
                  max(v for k, v in c15.items() if k != "sense_tail") <= criteria["common_mode_error_v"] and
                  min(sample(trial, "read_d", checkpoint)) >= HIGH)
        result.update(verdict=decision(cycles, ok), cases=cycles, c15_identical_within_envelope=ok,
                      c15_max_delta_v=c15, sample_counts=[len(base.rows), len(trial.rows)])
        export(root, (base, trial), cycles)
    write_json(root / "analysis.json", result)
    print(result["verdict"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "simulate", "analyze"))
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    {"prepare": prepare, "simulate": simulate, "analyze": analyze}[args.phase](args.root)
