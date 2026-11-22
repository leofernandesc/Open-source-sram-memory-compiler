#!/usr/bin/env python3
"""Compare archived sense-3 traces in absolute time and relative to tail current."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from analyze_phase3_sclk_r87_full import interpret_gate, scalar
from diagnose_phase3_sclk_startup import write_json
from phase3_sense3_diff_advance import verify_archive
from phase3_sense3_precondition import START, grid, pinned, pwl_tokens, read_wave, require, sample, sha256
from phase3_sense3_tail_only import (
    BUILD, EXTERNAL, GATES, HISTORY, INPUTS, LOCAL_R, ORIGINAL_R, SHIFT_WINDOWS,
    branch_measure, compare_case, max_delta, verify_control,
)


TAIL = BUILD / "sense3_tail_only_20261121"
RUNS = {"A": HISTORY / "control", "B": HISTORY / "contrast", "C": TAIL / "contrast"}
SIGNALS = (*GATES, "sampler_bl_id", "sampler_blb_id", "tail_id",
           "sa_sampling_out", "sab_sampling_out", "sense_tail", "bl_at_sense", "blb_at_sense", "read_d")
SAMPLER_CURRENTS = ("sampler_bl_id", "sampler_blb_id")


def load_json(path):
    return json.loads(path.read_text())


def verify_source(card, expected):
    head, knots = pwl_tokens(card)
    require(head == expected, f"Unexpected series source {head}")
    time, values = np.asarray(knots, dtype=float).T
    for index, (begin, end) in enumerate(zip(time, time[1:], strict=False)):
        if values[index] or values[index+1]:
            require(any(lo-1e-9 <= begin+START and end+START <= hi+1e-9 for lo, hi in SHIFT_WINDOWS),
                    f"Source {head} active outside archived rise windows")


def check_identity():
    manifest, _, gate, counts, models = verify_archive()
    c = RUNS["C"]
    receipt = load_json(c / "result.json")
    require(receipt["status"] == "COMPLETED", "C waveform incomplete")
    for name, value in receipt["artifacts"].items():
        pinned(c / name, value)
    attempt = load_json(c / "attempt.json")
    preflight = load_json(pinned(TAIL / "preflight.json", attempt["preflight_sha256"]))
    require(preflight["archive_gate"] == gate["verdict"] == "VALIDATED"
            and preflight["conditions"] == manifest["conditions"]
            and preflight["criteria"] == manifest["criteria"] and preflight["topology"] == counts
            and preflight["model_closure_files"] == models and preflight["pex_sha256"] == manifest["pex_sha256"],
            "C did not use the archived slice and conditions")
    for name in INPUTS:
        pinned(c / name, attempt["inputs_sha256"][name])
    for name in ("bench.spice", "stimuli.spice"):
        require(len({sha256(path / name) for path in RUNS.values()}) == 1, f"Changed benches or inputs: {name}")
    slice_a = (RUNS["A"] / "slice.spice").read_text()
    require((RUNS["B"] / "slice.spice").read_text() == slice_a and
            (c / "slice.spice").read_text() == slice_a.replace(ORIGINAL_R, LOCAL_R), "Changed topology")
    control = (RUNS["A"] / "clk_delta.spice").read_text()
    only_tail = (c / "clk_delta.spice").read_text()
    require(only_tail.startswith(control), "C modified R87")
    verify_source((RUNS["B"] / "clk_delta.spice").read_text(), "VSHIFT sclk_driver rc8562")
    verify_source(only_tail.removeprefix(control), "VTAIL tail_series rc8571")
    return manifest


def current_exposure(t, i):
    """Integrate abs(Id); dates describe the archived current, not switching thresholds."""
    z = np.flatnonzero(i[1:] * i[:-1] < 0)
    roots = t[z] + np.diff(t)[z] * i[z] / (i[z] - i[z+1])
    times = np.union1d(t, roots)
    y = np.abs(np.interp(times, t, i))
    cumulative = np.r_[0., np.cumsum(np.diff(times) * (y[:-1]+y[1:])/2)]
    return dict(integral_abs_id_fc=float(cumulative[-1]*1e6), peak_ua=float(max(y)*1e6),
                peak_ns=float(times[np.argmax(y)]),
                cumulative_10_50_90_ns=(np.interp([.1,.5,.9]*np.asarray(cumulative[-1]), cumulative, times).tolist()
                                        if cumulative[-1] else None))


def read_events(trace, case):
    m = branch_measure(trace, case)
    t0 = m["tail_above_1ua_ns"][0][0]
    lo = case["early_input_window_ns"][0]
    positive = [t for t in m["latch_sign_crossings_full_ns"]["positive"] if t >= lo]
    inversions = [t for t in m["latch_sign_crossings_full_ns"]["negative"] if t >= t0]
    t = grid(lo, case["high_ns"], trace)
    currents = {name: current_exposure(t, sample(trace, name, t)) for name in SAMPLER_CURRENTS}
    return dict(
        cycle=case["cycle"], first_tail_1ua_ns=t0, initial_ntail_v=m["conditioning"]["sense_tail"],
        initial_latch_v=[m["conditioning"][n] for n in ("sa_sampling_out","sab_sampling_out")],
        first_positive_separation_ns=positive[0] if positive else None,
        first_inversion_ns=inversions[0] if inversions else None,
        inversion_from_tail_on_ps=(inversions[0]-t0)*1000 if inversions else None,
        sense_valid_from_ns=m["stable_decision"]["from_ns"] if m["stable_decision"] else None,
        stable_d=m["correct_d_until_capture"] or m["wrong_d_until_capture"],
        capture_ns=case["capture_ns"], tail_peak_ua=m["tail_peak_ua"], tail_peak_ns=m["tail_peak_ns"],
        d_at_capture_v=m["captured_observation"]["read_d"], decision=m["decision"], current=currents,
        values_at_conduction=snapshot(trace, t0), clock=m["clock"],
    )


def snapshot(trace, t):
    values = {name: float(sample(trace, name, t)) for name in SIGNALS}
    values["sab_minus_sa_v"] = values["sab_sampling_out"] - values["sa_sampling_out"]
    values["blb_minus_bl_v"] = values["blb_at_sense"] - values["bl_at_sense"]
    return dict(at_ns=t, **values)


def summary_cycle(traces, case, criteria, shift):
    a = traces["A"]
    comparisons = {key: compare_case(a, traces[key], case, criteria, shift) for key in ("B", "C")}
    # B moves the fork downstream of R87 as well as both sampler gates.
    fidelity = criteria["contrast_fidelity"]
    b_edges = comparisons["B"]["edges"]
    for name in ("sclk_local", *GATES[:2]):
        edge = b_edges[name]
        edge["comparison"] = interpret_gate(edge["control"], edge["trial"], fidelity)
    comparisons["B"]["checks"]["delivered_and_other_edges_equivalent"] = all(
        edge["comparison"]["fidelity_verified"] for edge in b_edges.values())
    result = {key: read_events(trace, case) for key, trace in traces.items()}
    bt, ct = result["B"]["first_tail_1ua_ns"], result["C"]["first_tail_1ua_ns"]
    pre_tail = min(bt, ct)
    base20 = scalar(result["A"]["clock"]["sclk_tail"]["rise_ns"]["20"])
    anchor = scalar(result["B"]["clock"]["sclk_tail"]["rise_ns"]["10"])
    observed = {label: {key: snapshot(trace, when) for key, trace in traces.items()}
                for label, when in (("control_tail20", base20), ("joint_tail10", anchor),
                                    ("before_either_tail_reaches_1ua", pre_tail))}
    following = {str(k): {key: snapshot(trace, result[key]["first_tail_1ua_ns"]+k/1000)
                          for key, trace in traces.items()} for k in (100, 200, 300, 400, 600)}
    common = {}
    for key in ("B", "C"):
        t = grid(base20, pre_tail, traces[key])
        common[key] = {name: current_exposure(t, sample(traces[key], name, t)) for name in SAMPLER_CURRENTS}
    return dict(cycle=case["cycle"], runs=result, aligned_ps=following, simultaneous=observed,
                pre_tail_window_ns=[base20,pre_tail], pre_tail_current=common, comparison_checks={
                    key: pair["checks"] for key,pair in comparisons.items()
                }, edges_and_boundaries={key: {"edge_max_deltas_v": pair["gate_waveform_max_delta_v"],
                                               "external_max_deltas_v": pair["external_source_max_delta_v"]}
                                          for key,pair in comparisons.items()})


def write_tables(output, traces, cycles, cases):
    with (output/"gates.csv").open("x", newline="") as g, (output/"series.csv").open("x", newline="") as s:
        gates, series = csv.writer(g), csv.writer(s)
        gates.writerow(("cycle","run","percent","sampler_bl_ns","sampler_blb_ns","tail_ns",
                        "bl_minus_tail_ps","blb_minus_tail_ps","blb_minus_bl_ps",
                        "tail_1ua_minus_bl_ps","tail_1ua_minus_blb_ps","tail_1ua_minus_tail_gate_ps"))
        series.writerow(("cycle","run","reference_ns","from_tail_1ua_ps",*SIGNALS,"sab_minus_sa_v","blb_minus_bl_v"))
        for case, cycle in zip(cases,cycles,strict=True):
            for key,run in cycle["runs"].items():
                t0 = run["first_tail_1ua_ns"]
                for level in ("20","50","80"):
                    x,y,z = [scalar(run["clock"][name]["rise_ns"][level]) for name in GATES]
                    gates.writerow((case["cycle"],key,level,x,y,z,*[(v-u)*1000 for v,u in
                                    ((x,z),(y,z),(y,x),(t0,x),(t0,y),(t0,z))]))
                t = grid(case["tail20_ns"]-.4,case["capture_ns"],traces[key])
                vals = {name:sample(traces[key],name,t) for name in SIGNALS}
                series.writerows(zip([case["cycle"]]*len(t),[key]*len(t),t,(t-t0)*1000,*vals.values(),
                    vals["sab_sampling_out"]-vals["sa_sampling_out"],vals["blb_at_sense"]-vals["bl_at_sense"],strict=True))


def plots(output, traces, cycles, cases):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    panels = [
        ("Gates (V)", GATES, 1), ("|Id| samplers (µA)", SAMPLER_CURRENTS, 1e6),
        ("|Id| tail (µA)", ("tail_id",), 1e6), ("SA / SAB (V)", SIGNALS[6:8], 1),
        ("SAB−SA (V)", ("sab_minus_sa_v",), 1), ("NTAIL (V)", ("sense_tail",), 1),
        ("BLB−BL (mV)", ("blb_minus_bl_v",), 1e3), ("D (V)", ("read_d",), 1),
    ]
    for relative in (False,True):
        fig, axes = plt.subplots(len(panels),2,figsize=(12,14),sharex="col",layout="constrained")
        for col,(cycle,case) in enumerate(zip(cycles,cases,strict=True)):
            for color,(key,trace) in zip(("tab:gray","tab:blue","tab:orange"),traces.items(),strict=True):
                t0=cycle["runs"][key]["first_tail_1ua_ns"]
                start,stop=(t0-.5,t0+1.25) if relative else (case["tail20_ns"]-.35,case["tail20_ns"]+1.6)
                t=grid(start,stop,trace)
                x=(t-t0)*1000 if relative else t
                values={n:sample(trace,n,t) for n in SIGNALS}
                values["sab_minus_sa_v"]=values["sab_sampling_out"]-values["sa_sampling_out"]
                values["blb_minus_bl_v"]=values["blb_at_sense"]-values["bl_at_sense"]
                for ax,(label,names,scale) in zip(axes[:,col],panels,strict=True):
                    for name,style in zip(names,("-","--",":"),strict=False):
                        v=abs(values[name]) if name.endswith("_id") else values[name]
                        ax.plot(x,v*scale,color=color,ls=style,label=key if name==names[0] else None)
                    ax.set_ylabel(label)
                    ax.grid(alpha=.22)
                    if relative and key=="A": ax.axvline(0,color=".7",lw=.8)
            axes[0,col].set_title(f"c{case['cycle']}")
            axes[-1,col].set_xlabel("Tempo em relação a |Id tail| = 1 µA (ps)" if relative else "Tempo absoluto (ns)")
            if col==0:
                axes[0,col].legend(loc="upper left",ncols=3)
        fig.suptitle("A controle · B três gates · C só tail | sólido BL ou SA · tracejado BLB ou SAB · pontilhado tail")
        fig.savefig(output/("relative.png" if relative else "absolute.png"),dpi=155)
        plt.close(fig)


def audit(output):
    try:
        manifest = check_identity()
        traces = {key:read_wave(path) for key,path in RUNS.items()}
        criteria = manifest["criteria"]
        cases = criteria["cases"]
        verify_control(traces["A"],cases)
        c15_times = (199.5,200.)
        initial = max(trace.times[0] for trace in traces.values())
        checks = {}
        for key,trace in traces.items():
            checkpoint = grid(*c15_times,trace)
            old=traces["A"]
            before=max_delta(old,trace,(*EXTERNAL,*GATES,"sense_tail","sense_out","sense_bar","read_d"),
                             initial,SHIFT_WINDOWS[0][0])
            require(min(sample(trace,"read_d",checkpoint))>=1.44 and max(before.values())<.0001,
                    "c15 or history before c16 changed")
            checks[key]=before
        cycles=[summary_cycle(traces,c,criteria,window) for c,window in zip(cases,SHIFT_WINDOWS,strict=True)]
        require(all(all(c["comparison_checks"][r].values()) for c in cycles for r in ("B","C")),
                "Differences in stimuli, conditioning, or intended gate edges exceeded the archives' envelopes")
    except (ValueError, FileNotFoundError) as exc:
        write_json(output/"analysis.json", dict(verdict="COMPARISON_INCONCLUSIVE", reason=str(exc)))
        raise
    write_tables(output,traces,cycles,cases)
    plots(output,traces,cycles,cases)
    write_json(output/"analysis.json",dict(
        status="COMPARABLE", pex_sha256=manifest["pex_sha256"], conditions=manifest["conditions"],
        cycles=cycles, before_intervention_max_delta_v=checks,
        samples={key:len(trace.rows) for key,trace in traces.items()},
        hashes={key:{name:sha256(path/name) for name in (*INPUTS,"waveform.dat","currents.dat")}
                for key,path in RUNS.items()},
    ))
    print("COMPARABLE · A, B e C · c16/c17", flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    audit(parser.parse_args().output)
