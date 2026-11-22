#!/usr/bin/env python3
"""One device-based R87 candidate with separate functional and electrical checks."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import time

import numpy as np

from analyze_phase3_sense3_isolation import conditioning_valid, one_cross
from diagnose_phase3_sclk_startup import write_json
from phase3_sclk_local_driver import (
    DRIVER, GATES, HIGH, LIB, LOW, archived, augmented_wave, branch, compare_gates,
    instrument, measures, pulse_inventory, reset_measure,
)
from phase3_sense3_precondition import BUILD, PDK, REFERENCE, ROOT, grid, model_closure, read_wave, sample
from phase3_sense3_tail_only import EXTERNAL, HISTORY, max_delta, ngspice_limits, pinned, require, sha256
from analyze_phase3_data3_tt import load
from review_phase3_bus_ss import ge


CELL = "sky130_fd_sc_hd__inv_2"
MODULE = "phase3_sclk_local_v2"
CANDIDATE = DRIVER.with_name("sclk_local_driver_v2.spice")
PRIOR = BUILD / "sclk_local_driver_20261120_v1"
TIMEOUT = 120
OVERLAY = f"""* Series meters report input and supply current. The output is driven by MOS.
.include "driver_library.spice"
.include "driver_cell.spice"
VDRIVER_INPUT rc8562 driver_input 0
VDRIVER_VDD VDD driver_vdd 0
XLOCAL driver_input sclk_driver driver_vdd VSS {MODULE}
"""


def read_json(path):
    return json.loads(path.read_text())


def select_library_cell(text):
    m = re.search(rf"(?m)^\.subckt {CELL} A VGND VNB VPB VPWR Y\n(?:[^\n]+\n)*?\.ends[ \t]*(?:{CELL})?\n", text)
    require(m is not None, "Installed restoring cell or pinout missing")
    devices = [line.split() for line in m[0].splitlines() if line.startswith("X")]
    require(len(devices) == 4 and all(p[2] == "A" for p in devices) and
            sum("nfet_01v8" in p[5] for p in devices) == 2 and
            sum("pfet_01v8_hvt" in p[5] for p in devices) == 2, "Unexpected restoring cell")
    return m[0]


def module_body(text):
    return [line for line in text.splitlines() if line and not line.startswith("*")]


def verify_prior():
    receipt = read_json(PRIOR / "result.json")
    require(receipt["status"] == "COMPLETED", "v1 reference is incomplete")
    for name, digest in receipt["artifacts"].items():
        pinned(PRIOR / name, digest)
    return read_json(PRIOR / "analysis.json")


def prepare(out):
    require(out.is_dir() and not (out / "manifest.json").exists(), "Use a fresh output directory")
    baseline = archived()
    models_path = REFERENCE / "model_hashes.json"
    models = read_json(models_path)
    require(model_closure(PDK) == models, "TT models drifted")
    v1 = verify_prior()
    text = CANDIDATE.read_text()
    require(module_body(text) == module_body(DRIVER.read_text().replace("phase3_sclk_local_v1", MODULE)
                                            .replace("sky130_fd_sc_hd__inv_4", CELL)),
            "The only device change must be the restoring strength")
    proof = branch((REFERENCE / "binding.spice").read_text(), read_json(REFERENCE / "probes.json"))
    require(proof["upstream"] == "rc8562" and proof["local"] == "rc8571" and proof["resistance_ohm"] == 6.46438
            and {name for name, _ in proof["consumers"]} == {"X235", "X521", "X351"}, "Unexpected R87 fanout")
    lib = LIB / "spice/sky130_fd_sc_hd.spice"
    lef = LIB / "lef/sky130_fd_sc_hd.lef"
    dimensions = re.search(rf"(?ms)^MACRO {CELL}\n.*?SIZE ([\d.]+) BY ([\d.]+) ;", lef.read_text())
    require(dimensions is not None, "Missing library cell dimensions")
    w, h = map(float, dimensions.groups())
    local_lib = select_library_cell(lib.read_text())
    bench = (HISTORY / "control/bench.spice").read_text()
    require(".temp 27" in bench and "tran 10p 59n 0 25p" in bench, "Unexpected preconditioned bench")
    run = out / "run"
    run.mkdir()
    (run / "driver_cell.spice").write_text(text)
    (run / "driver_library.spice").write_text(local_lib)
    (run / "clk_delta.spice").write_text(OVERLAY)
    (run / "bench.spice").write_text(instrument(bench))
    for name in ("slice.spice", "stimuli.spice"):
        (run / name).write_bytes((HISTORY / "control" / name).read_bytes())
    write_json(out / "manifest.json", dict(
        status="READY", pex_sha256=baseline["pex_sha256"], model_closure_count=len(models),
        model_manifest_sha256=sha256(models_path), conditions=baseline["conditions"], timeout_s=TIMEOUT,
        polarity="Two inversions with CMOS pull-up and pull-down; no ideal delay or source on OUT",
        inputs_outputs={"input": "rc8562", "output": "sclk_driver", "fork_after_R87": "rc8571"},
        r87=proof, driver_cell=CELL, footprint_um2=w*h, restored_fingers={"nmos": 2, "pmos_hvt": 2},
        dimension_basis="First stage remains at the previously tested W/L. inv_2 halves the parallel "
                        "unit devices of inv_4 while retaining twice the output branches of inv_1.",
        historical_v1_analysis_sha256=sha256(PRIOR / "analysis.json"),
        historical_r87_rising_charge_fc=[c["loading"]["archived_branch_charge_c"]*1e15 for c in v1["cycles"]],
        cells_library_sha256=sha256(lib), library_lef_sha256=sha256(lef), runner_sha256=sha256(Path(__file__)),
        criteria={
            "function": "c15 preserved; c16/c17 complementary latch and D low continuously, with native samples up to capture",
            "electrical": "Each gate must produce three complete logical pulses, and latch and bitlines must recover",
            "coordinated": "At every rise and fall the gate 20–80% transition intervals must overlap",
            "recovery_risk": "An overlap of monitored tail and precharge currents at the archived 1 uA marker "
                             "or lost gate/prech margin merits integration review",
            "integration_risk": "Risk if peak current is closer to v1 than to the ideal contrast, "
                                "if shared R87 input loading increases, or if state/pulse checks leave ambiguity",
            "ideal_182_ps": "Comparison only. Edge shifts and slew do not establish functional failure",
        },
        inputs_sha256={p.name:sha256(p) for p in run.iterdir()},
    ))
    print("READY", flush=True)


def simulate(out):
    path = out / "manifest.json"
    manifest = read_json(path)
    run = out / "run"
    require(manifest["status"] == "READY" and not (run / "attempt.json").exists(), "No eligible attempt")
    pinned(Path(__file__), manifest["runner_sha256"])
    for name, digest in manifest["inputs_sha256"].items():
        pinned(run / name, digest)
    require(model_closure(PDK) == read_json(REFERENCE / "model_hashes.json"), "TT models drifted")
    command = ["stdbuf","-o0","-e0","ngspice","-n","-b","bench.spice"]
    with (BUILD / ".eco_simulator.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (run / "attempt.json").open("x") as stream:
            json.dump(dict(command=command, timeout_s=TIMEOUT, manifest_sha256=sha256(path)), stream, indent=2)
        start = time.monotonic()
        code, status = None, "INCOMPLETE"
        with (run / "ngspice.log").open("xb", buffering=0) as log:
            try:
                code = subprocess.run(command, cwd=run, stdout=log, stderr=subprocess.STDOUT,
                                      preexec_fn=ngspice_limits, timeout=TIMEOUT, check=False,
                                      env={**os.environ,"OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1"}).returncode
            except subprocess.TimeoutExpired:
                status = "TIMEOUT"
    elapsed = time.monotonic() - start
    log = (run / "ngspice.log").read_bytes()
    if (code == 0 and b"No. of Data Rows" in log and all((run / name).is_file()
            for name in ("waveform.dat","currents.dat","driver.dat")) and
            not re.search(rb"analysis aborted|timestep too small|fatal error:|transient op failed", log, re.I)):
        status = "COMPLETED"
    write_json(run / "result.json", dict(status=status, elapsed_s=elapsed, exit_code=code,
              artifacts={p.name:sha256(p) for p in run.iterdir() if p.is_file()}))
    print(status, flush=True)


def coordinated(clock):
    for edge, first, last in (("rise","20","80"),("fall","80","20")):
        start, end = ([clock[g][f"{edge}_ns"][level] for g in GATES] for level in (first,last))
        if (any(len(x)!=1 for x in start+end) or max(x[0] for x in start) >= min(x[0] for x in end)):
            return False
    return True


def logic_pulses(trace, signal):
    states = []
    for row in trace.rows:
        value = row[trace.cols[signal]]
        level = 0 if value <= LOW else 1 if value >= HIGH else None
        if level is not None and (not states or states[-1] != level):
            states.append(level)
    return states


def has_electrical_failure(rails, resets):
    return any(states != [0,1,0,1,0,1,0] for states in rails.values()) or any(
        not r["recovered"] or not r["bitlines_recovered"] for r in resets)


def judge(electrical_failure, correct, risks):
    if electrical_failure:
        return "ELECTRICAL_FAIL"
    if not correct:
        return "FUNCTIONAL_FAIL"
    return "FUNCTIONAL_WITH_INTEGRATION_RISK" if risks else "PROMISING_LOCAL_DRIVER"


def case_reset(trace, case):
    reset = reset_measure(trace, case)
    end = case["high_ns"]+8
    reset["bitlines_recovered"] = all(float(sample(trace,k,end)) >= HIGH for k in ("bl_at_sense","blb_at_sense"))
    return reset


def integral(values, times_ns):
    return float(np.sum(np.diff(times_ns) * (values[:-1] + values[1:]) * .5e-9))


def energy_and_loading(control, trial, case, resistance):
    a, b = case["low_ns"], case["high_ns"]
    t = grid(a, b, control, trial)
    old = (sample(control,"sclk_driver",t) - sample(control,"sclk_local",t))/resistance
    new = sample(trial,"input_current",t)
    q_old, q_new = integral(old,t), integral(new,t)
    power_times = grid(a,b+8,trial)
    rail = sample(trial,"supply_current",power_times)
    return dict(archived_branch_charge_c=q_old,driver_input_charge_c=q_new,comparable_load=q_new<=q_old,
                peak_input_current_a=float(max(abs(new))),peak_replaced_branch_current_a=float(max(abs(old))),
                supply_peak_a=float(max(abs(rail))),
                supply_energy_j=integral(rail*sample(trial,"vdd",power_times),power_times))


def plot(out, traces, cases):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(6,2,figsize=(12,10),layout="constrained")
    for col,case in enumerate(cases):
        a = case["tail20_ns"]
        recovery = case["capture_ns"]+3.5
        for label,trace in traces.items():
            for row,(lo,hi,names,scale,unit) in enumerate((
                (a-.5,a+1.6,GATES,1,"Gates (V)"),
                (a-.5,a+1.6,("sa_sampling_out","sab_sampling_out"),1,"SA, SAB (V)"),
                (a-.5,a+1.6,("tail_id",),1e6,"I tail (µA)"),
                (recovery,recovery+1.7,("sclk_tail","precharge"),1,"Tail, PRECH (V)"),
                (recovery,recovery+1.7,("tail_id",),1e6,"I tail (µA)"),
                (a-.5,case["capture_ns"],("read_d",),1,"D (V)"),
            )):
                t = grid(lo,hi,trace)
                for j,name in enumerate(names):
                    axs[row,col].plot(t,sample(trace,name,t)*scale,ls=["-","--",":"][j],
                                      color={"Controle":".45","Ideal":"tab:blue","v1":"tab:orange","v2":"tab:green"}[label],
                                      label=label if j==0 else None)
                axs[row,col].set_ylabel(unit)
                axs[row,col].grid(alpha=.24)
        axs[0,col].set_title(f"c{case['cycle']} · TT")
        axs[0,col].legend(loc="upper left",ncols=2,fontsize=8)
        axs[-1,col].set_xlabel("Tempo na referência TT (ns)")
    fig.suptitle("Subida/SA: BL ou SA sólido, BLB ou SAB tracejado, tail pontilhado. Na descida: PRECH tracejado.")
    fig.savefig(out / "comparison.png",dpi=155)
    plt.close(fig)


def analyze(out):
    run = out / "run"
    result = read_json(run / "result.json")
    try:
        for name,digest in result["artifacts"].items():
            pinned(run/name,digest)
        require(result["status"]=="COMPLETED", "Transiente incompleto")
        trial = augmented_wave(run)
    except (ValueError,FileNotFoundError) as exc:
        write_json(out/"analysis.json",dict(verdict="SIMULATION_INCONCLUSIVE",reason=str(exc)))
        return
    baseline = archived()
    verify_prior()
    traces = dict(Controle=read_wave(HISTORY/"control"),Ideal=read_wave(HISTORY/"contrast"),
                  v1=augmented_wave(PRIOR),v2=trial)
    _,_,ref = load(REFERENCE, True)
    capture = one_cross(ref,"capture_clock",200.,200.3,.5)
    require(capture is not None,"Missing archived c15 capture")
    c15 = dict(cycle=15,low_ns=191.,high_ns=199.,capture_ns=capture,conditioning_ns=189.9)
    cases = baseline["criteria"]["cases"]
    rail_states = {name:logic_pulses(trial,name) for name in GATES}
    pulses = {name:pulse_inventory(trial,name,[c15,*cases]) for name in GATES}
    predecessor = measures(trial,c15)
    predecessor_high = trial.signal_window(c15["low_ns"],capture,[ge(trial.cols["read_d"],HIGH)],suffix=True)
    resets = [case_reset(trial,c) for c in (c15,*cases)]
    cycles, risks = [], []
    for case,reset in zip(cases,resets[1:],strict=True):
        a,b,c,d = (measures(w,case) for w in traces.values())
        effects = max_delta(traces["Controle"],trial,EXTERNAL,case["conditioning_ns"],case["high_ns"]+8)
        loadings = energy_and_loading(traces["Controle"],trial,case,6.46438)
        condition = conditioning_valid(a,d,baseline["criteria"]["latch_conditioning_error_v"])
        coord = coordinated(d["clock"])
        peak = d.get("first_tail_conduction_peak_a")
        if peak is not None and abs(peak-c["first_tail_conduction_peak_a"])<abs(peak-b["first_tail_conduction_peak_a"]):
            risks.append(f"c{case['cycle']}: pico de corrente mais próximo do v1 que do contraste ideal")
        if not coord or not condition or not reset["adequate"] or not loadings["comparable_load"]:
            risks.append(f"c{case['cycle']}: margem de desativação, coordenação, estado ou carga requer revisão")
        if max(effects.values())>.0001 or loadings["peak_input_current_a"]>loadings["peak_replaced_branch_current_a"]:
            risks.append(f"c{case['cycle']}: carregamento ou desvio externo a revisar")
        cycles.append(dict(cycle=case["cycle"],control=a,ideal=b,v1=c,candidate=d,gates_vs_control=compare_gates(a,d),
                           coordinated=coord,conditioned=condition,reset=reset,loading=loadings,externals_v=effects))
    if any(not event["compatible"] for event in pulses.values()):
        risks.append("Cruzamento analógico adicional em um dos gates")
    if not resets[0]["adequate"]:
        risks.append("Margem de desativação de c15 requer revisão")
    correct = bool(predecessor_high and predecessor["decision"]=="WRONG" and all(
        row["candidate"]["decision"]=="CORRECT" and row["candidate"]["stable_d_low"] and
        row["candidate"]["stable_d_low"]["actual_samples"]>=2 for row in cycles))
    electrical = has_electrical_failure(rail_states,resets)
    write_json(out/"analysis.json",dict(verdict=judge(electrical,correct,risks),cycles=cycles,c15=predecessor,
               c15_reset=resets[0],c15_d_high=predecessor_high,logical_pulses=rail_states,functionally_correct=correct,
               electrical_failure=electrical,risks=risks,waveform_rows=len(trial.rows)))
    plot(out,traces,cases)
    print(judge(electrical,correct,risks), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("prepare","simulate","analyze"))
    parser.add_argument("output",type=Path)
    args = parser.parse_args()
    try:
        {"prepare":prepare,"simulate":simulate,"analyze":analyze}[args.phase](args.output)
    except (ValueError, FileNotFoundError) as exc:
        if args.phase == "prepare" and not (args.output/"manifest.json").exists():
            write_json(args.output/"manifest.json",dict(status="NOT_READY",verdict="NO_DEFENSIBLE_DRIVER",reason=str(exc)))
        raise
