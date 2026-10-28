#!/usr/bin/env python3
"""Exercise the dynamic decoder/WL PEX with Danilo's precharge PEX.

The access phases are ideal PWL stimuli in this first integration bench. This
checks the active-low PRECH interface, bitline restoration, and non-overlap
against the selected wordline. It does not claim to qualify a physical PCLK
generator, bitcell read/write behavior, or the complete SRAM macro.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sims/row_decoder"))

import run_row_decoder_capture_timing as capture
import run_row_decoder_contract as contract
import run_row_decoder_distributed_row as distributed
import run_row_decoder_tt as screen

PRECHARGE_PEX = ROOT / "sims/row_decoder/inputs/precharge_w2p52_pex_5dc00fe.spice"
PRECHARGE_PROVENANCE = PRECHARGE_PEX.with_suffix(".provenance.json")
PRECHARGE_SHA256 = "cf0fa457b4ab84a1d19e6202541b6a43149b575e492a108e36d0de62489cc423"
PRECHARGE_CEFF_MAX_FF = 13.064186
CBL_CHARACTERIZED_LIMIT_FF = 597.056241
CBL_EXTERNAL_FF = CBL_CHARACTERIZED_LIMIT_FF - PRECHARGE_CEFF_MAX_FF
CAPTURE_NS = 15.0
VALID_VECTORS = {"001": "read", "010": "write"}
ALL_CONTROL_VECTORS = ("000", "001", "010", "011", "100", "101", "110", "111")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def inspect_precharge_pex(text: str) -> dict:
    require(hashlib.sha256(text.encode()).hexdigest() == PRECHARGE_SHA256,
            "Danilo precharge PEX SHA-256 differs from the pinned source")
    lines = screen.logical_lines(text)
    start = next((i for i, line in enumerate(lines)
                  if re.match(r"(?i)^\.subckt\s+precharge_w2p52_flat\b", line)), None)
    require(start is not None, "Missing precharge_w2p52_flat subcircuit")
    header = lines[start].split()
    pins = [pin.upper() for pin in header[2:]]
    expected_pins = ["VDD", "BL", "BLB", "PRECH", "VSS"]
    require(pins == expected_pins, f"Unexpected Danilo precharge PEX pin order: {pins}")
    end = next((i for i in range(start + 1, len(lines))
                if re.match(r"(?i)^\.ends\b", lines[i])), None)
    require(end is not None, "Precharge PEX has no .ends")
    body = lines[start + 1:end]
    mos = [line for line in body if re.match(
        r"(?i)^X\S+\s+.*\bsky130_fd_pr__pfet_01v8\b", line)]
    resistors = [line for line in body if re.match(r"(?i)^R\S+\s", line)]
    capacitors = [line for line in body if re.match(r"(?i)^C\S+\s", line)]
    require(len(mos) == 3 and len(resistors) > 0 and len(capacitors) > 0,
            "Precharge PEX must retain three PFETs and extracted R-C parasitics")
    negative_caps = []
    for line in capacitors:
        tokens = line.split()
        require(len(tokens) >= 4, f"Malformed PEX capacitor: {line}")
        match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)[a-zA-Z]*", tokens[3])
        require(match is not None, f"Cannot parse PEX capacitor value: {line}")
        if float(match[1]) < 0:
            negative_caps.append(line)
    require(not negative_caps, "Precharge PEX contains negative capacitors")
    return {"subcircuit": header[1], "pins": pins, "mos_devices": len(mos),
            "resistors": len(resistors), "capacitors": len(capacitors),
            "negative_capacitors": len(negative_caps), "sha256": PRECHARGE_SHA256}


def attach_precharge_pex(netlist: str, pex_text: str) -> tuple[str, list[str]]:
    ports = capture.top_pin_map(netlist)
    instances = [
        f"XPRECH{bit} {ports['VDD']} BL{bit} BLB{bit} PRECH {ports['VSS']} precharge_w2p52_flat"
        for bit in range(8)
    ]
    marker = "* expanding"
    require(marker in netlist, "Xschem top-level expansion marker is missing")
    netlist = netlist.replace(marker, "\n".join(instances) + "\n\n" + marker, 1)
    netlist, count = re.subn(r"(?im)^\.end\s*$", pex_text.rstrip() + "\n.end", netlist, count=1)
    require(count == 1, "Could not add Danilo's precharge PEX definition")
    return netlist, instances


def trace(raw: dict[str, np.ndarray], node: str) -> np.ndarray:
    key = node.lower()
    if not key.startswith("v("):
        key = f"v({key})"
    require(key in raw, f"Missing waveform {key}")
    values = raw[key]
    require(np.isfinite(values).all(), f"Nonfinite waveform {key}")
    return values


def crossing(time: np.ndarray, signal: np.ndarray, level: float,
             rising: bool, start: float, end: float) -> float | None:
    indices = np.flatnonzero((time[:-1] >= start) & (time[1:] <= end))
    if rising:
        hits = indices[(signal[indices] < level) & (signal[indices + 1] >= level)]
    else:
        hits = indices[(signal[indices] > level) & (signal[indices + 1] <= level)]
    if not len(hits):
        return None
    i = int(hits[0])
    dv = signal[i + 1] - signal[i]
    if dv == 0:
        return float(time[i])
    return float(time[i] + (level - signal[i]) / dv * (time[i + 1] - time[i]))


def add_check(rows: list[dict], case: dict, name: str, value: float,
              low: float | None = None, high: float | None = None,
              unit: str = "") -> None:
    passed = math.isfinite(value) and (low is None or value >= low) and (high is None or value <= high)
    rows.append({"case": case["label"], "control_vector_csb_oeb_web": case["control_vector"],
                 "check": name, "value": value, "unit": unit,
                 "minimum": "" if low is None else low,
                 "maximum": "" if high is None else high,
                 "result": "PASS" if passed else "FAIL"})


def phase_waveform(schedule: dict, valid: bool, vdd: float,
                   release_lead_ps: float, turnoff_guard_ps: float) -> tuple[str, dict]:
    stop = float(schedule["stop"])
    edge_s = 50e-12
    first_release = float(schedule["first_rise"]) - release_lead_ps * 1e-12
    first_reassert = float(schedule["first_fall"]) + turnoff_guard_ps * 1e-12
    transitions = [
        (first_release - edge_s/2, first_release + edge_s/2, vdd),
        (first_reassert - edge_s/2, first_reassert + edge_s/2, 0.0),
    ]
    second_release = CAPTURE_NS * 1e-9
    second_reassert = float(schedule["second_fall"]) + turnoff_guard_ps * 1e-12
    if valid:
        transitions.extend([
            (second_release - edge_s/2, second_release + edge_s/2, vdd),
            (second_reassert - edge_s/2, second_reassert + edge_s/2, 0.0),
        ])
    require(first_release > 0 and first_reassert < second_release,
            "PRECH phases overlap or leave no low-clock precharge interval")
    require(not valid or second_reassert < stop,
            "The transient ends before the delayed PRECH assertion")
    return contract.pwl(0.0, transitions, stop), {
        "first_release_center_s": first_release,
        "first_reassert_center_s": first_reassert,
        "second_release_center_s": second_release if valid else None,
        "second_reassert_center_s": second_reassert if valid else None,
        "release_lead_ps": release_lead_ps,
        "turnoff_guard_ps": turnoff_guard_ps,
    }


def add_precharge_loads_and_waveforms(deck: str, schedule: dict, case: dict,
                                      vss: str,
                                      release_lead_ps: float,
                                      turnoff_guard_ps: float) -> tuple[str, dict]:
    valid = case["control_vector"] in VALID_VECTORS
    waveform, phase = phase_waveform(schedule, valid, float(schedule["vdd"]),
                                     release_lead_ps, turnoff_guard_ps)
    additions = [f"VPRECH PRECH 0 {waveform}"]
    for bit in range(8):
        additions.append(f"CBL_EXT_{bit} BL{bit} {vss} {CBL_EXTERNAL_FF * 1e-15:.12g}")
        additions.append(f"CBLB_EXT_{bit} BLB{bit} {vss} {CBL_EXTERNAL_FF * 1e-15:.12g}")
    deck, count = re.subn(r"(?im)^(\.lib\s+)", "\n".join(additions) + "\n\\1", deck, count=1)
    require(count == 1, "Could not insert PRECH source and bitline residual loads")
    saved = ["v(prech)"] + [f"v({name})" for bit in range(8)
                              for name in (f"BL{bit}", f"BLB{bit}")]
    deck, count = re.subn(r"(?im)^(\.save\s+[^\n]+)$",
                          lambda match: match.group(1) + " " + " ".join(saved),
                          deck, count=1)
    require(count == 1, "Could not add PRECH and bitline waveform probes")
    return deck, phase


def evaluate_phase_interface(raw: dict[str, np.ndarray], case: dict,
                             nodes: dict, schedule: dict, phase: dict,
                             release_lead_ps: float,
                             turnoff_guard_ps: float) -> tuple[list[dict], dict]:
    time = raw["time"]
    vdd = float(schedule["vdd"])
    prech = trace(raw, "PRECH")
    pclk = trace(raw, nodes["PCLK"])
    checks: list[dict] = []
    measurements: dict = {"bitline_external_load_ff": CBL_EXTERNAL_FF,
                          "bitline_target_effective_ceiling_ff": CBL_CHARACTERIZED_LIMIT_FF,
                          "precharge_releases": [], "precharge_reassertions": []}
    valid = case["control_vector"] in VALID_VECTORS

    for cycle, pclk_rise_nominal, pclk_fall_nominal, release_center, reassert_center, selected in (
        ("prime", float(schedule["first_rise"]), float(schedule["first_fall"]),
         phase["first_release_center_s"], phase["first_reassert_center_s"], int(case["old"])),
        ("access", float(schedule["second_rise"]), float(schedule["second_fall"]),
         phase["second_release_center_s"], phase["second_reassert_center_s"], int(case["new"])),
    ):
        if cycle == "access" and not valid:
            continue
        # Use 75% VDD as the conservative start of PFET turn-on/turn-off margin;
        # the precharge devices can conduct before PRECH reaches its 50% point.
        pre_release = crossing(time, prech, 0.75*vdd, True,
                               release_center-1e-9, release_center+1e-9)
        pclk_up = crossing(time, pclk, 0.5*vdd, True,
                           pclk_rise_nominal-0.5e-9, pclk_rise_nominal+1e-9)
        pclk_down = crossing(time, pclk, 0.5*vdd, False,
                             pclk_fall_nominal-0.5e-9, pclk_fall_nominal+0.5e-9)
        pre_assert = crossing(time, prech, 0.75*vdd, False,
                              reassert_center-1e-9, reassert_center+1e-9)
        require(pre_release is not None and pclk_up is not None
                and pclk_down is not None and pre_assert is not None,
                f"Missing {cycle} phase crossing in {case['label']}")
        release_margin_ps = (pclk_up-pre_release)*1e12
        reassert_margin_ps = (pre_assert-pclk_down)*1e12
        add_check(checks, case, f"{cycle}_precharge_release_before_pclk_ps",
                  release_margin_ps, low=0, unit="ps")
        add_check(checks, case, f"{cycle}_precharge_reassert_after_pclk_fall_ps",
                  reassert_margin_ps, low=0, unit="ps")
        add_check(checks, case, f"{cycle}_PRECH_high_at_PCLK_rise_v",
                  float(np.interp(pclk_up, time, prech)), low=0.9*vdd, unit="V")

        selected_wl = trace(raw, nodes[f"WL{selected}"])
        selected_off = crossing(time, selected_wl, 0.1*vdd, False,
                                pclk_down, min(float(schedule["stop"]), reassert_center+3e-9))
        add_check(checks, case, f"{cycle}_selected_WL_off_before_PRECH_conduction_ps",
                  math.nan if selected_off is None else (pre_assert-selected_off)*1e12,
                  low=0, unit="ps")
        for row in range(4):
            signal = trace(raw, nodes[f"WL{row}"])
            active_mask = (time >= pre_assert) & (time <= min(float(schedule["stop"]),
                                                                 reassert_center+1e-9))
            if active_mask.any():
                add_check(checks, case, f"{cycle}_WL{row}_max_while_PRECH_active_v",
                          float(signal[active_mask].max()), high=0.1*vdd, unit="V")
        measurements["precharge_releases"].append({"cycle": cycle,
            "precharge_release_s": pre_release, "pclk_rise_s": pclk_up,
            "lead_ps": release_margin_ps})
        measurements["precharge_reassertions"].append({"cycle": cycle,
            "pclk_fall_s": pclk_down, "precharge_assert_s": pre_assert,
            "turnoff_margin_ps": reassert_margin_ps,
            "selected_wl_below_10pct_s": selected_off})

        for bit in range(8):
            for name in (f"BL{bit}", f"BLB{bit}"):
                signal = trace(raw, name)
                sample_time = max(0.0, pclk_up-50e-12)
                add_check(checks, case, f"{cycle}_{name}_precharged_before_eval_v",
                          float(np.interp(sample_time, time, signal)), low=0.9*vdd, unit="V")

    if not valid:
        start = CAPTURE_NS*1e-9
        end = float(schedule["second_fall"])
        region = (time >= start) & (time <= end)
        require(region.any(), "Missing disabled/invalid second clock window")
        add_check(checks, case, "invalid_PCLK_peak_v", float(pclk[region].max()),
                  high=0.1*vdd, unit="V")
        for output in ("DEC0", "DEC1", "DEC2", "DEC3", "WL0", "WL1", "WL2", "WL3"):
            signal = trace(raw, nodes[output])
            add_check(checks, case, f"invalid_{output}_peak_v",
                      float(signal[region].max()), high=0.1*vdd, unit="V")
        add_check(checks, case, "invalid_PRECH_active_v",
                  float(prech[region].max()), high=0.1*vdd, unit="V")

    end_mask = time >= float(schedule["stop"])-50e-12
    require(end_mask.any(), "No terminal sample at the end of the transient")
    for bit in range(8):
        for name in (f"BL{bit}", f"BLB{bit}"):
            signal = trace(raw, name)
            value = float(signal[end_mask].min())
            add_check(checks, case, f"final_{name}_precharged_v", value,
                      low=0.9*vdd, unit="V")
    measurements["bitline_minimum_at_end_v"] = min(
        float(trace(raw, name)[end_mask].min()) for bit in range(8)
        for name in (f"BL{bit}", f"BLB{bit}"))
    return checks, measurements


def run_case(case: dict, netlist: str, model: Path, arcs: dict,
             wl_cap_ff: float, step_ps: float, release_lead_ps: float,
             turnoff_guard_ps: float, output: Path, keep_raw: bool) -> dict:
    case_dir = output / "cases" / case["label"]
    case_dir.mkdir(parents=True)
    arc = arcs[case["profile"]]
    phase_case = {
        **case,
        "campaign": "timing",
        "capture_to_pclk_ps": case["phase_ps"],
        "clk_fall_ps": case["clk_fall_ps"],
        "settling_allowance_ns": case["settling_allowance_ns"],
        "lead_ps": 2000,
        "address_ps": 50,
        "rise_ps": 25,
        "fall_ps": 25,
        "step_ps": step_ps,
        "method": "gear",
        "minbreak_fs": 1,
        "chgtol_c": 1e-18,
        "slew_lower_pct": case["slew_lower_pct"],
        "slew_upper_pct": case["slew_upper_pct"],
        "dff_load_label": "nominal",
    }
    deck, nodes, devices, terminals, schedule, sim_case = capture.make_deck(
        netlist, phase_case, model, arc, "nominal", wl_cap_ff)
    ports = capture.top_pin_map(netlist)
    deck, phase = add_precharge_loads_and_waveforms(deck, schedule, case, ports["VSS"],
                                                    release_lead_ps, turnoff_guard_ps)
    if case["control_vector"] not in VALID_VECTORS:
        deck = distributed.suppress_evaluation_pclk(deck, schedule)
    deck = re.sub(r"(?im)^(\.tran\s+\S+\s+\S+\s+0\s+)\S+",
                  rf"\g<1>{step_ps*1e-12:.12g}", deck, count=1)
    deck_path = case_dir / "case.spice"
    log_path = case_dir / "ngspice.log"
    raw_path = case_dir / "waveform.raw"
    deck_path.write_text(deck, encoding="utf-8")
    try:
        proc = subprocess.run(["ngspice", "-n", "-b", str(deck_path)],
                              cwd=case_dir, capture_output=True, text=True,
                              timeout=180)
    except subprocess.TimeoutExpired as exc:
        log_path.write_text((exc.stdout or "") + (exc.stderr or ""), encoding="utf-8")
        return {"case": case["label"], "status": "ERROR", "error": "ngspice timeout"}
    log = proc.stdout + proc.stderr
    log_path.write_text(log, encoding="utf-8")
    if (proc.returncode or re.search(r"Error:|failed!|aborted|timestep too small", log, re.I)
            or not raw_path.is_file()):
        return {"case": case["label"], "status": "ERROR",
                "ngspice_returncode": proc.returncode,
                "error": "ngspice failed or did not produce waveform.raw"}

    raw = capture.read_raw(raw_path)
    phase_checks, phase_metrics = evaluate_phase_interface(
        raw, case, nodes, schedule, phase, release_lead_ps, turnoff_guard_ps)
    valid = case["control_vector"] in VALID_VECTORS
    if valid:
        decoder_run, decoder_checks, terminal_rows = contract.analyze(
            raw, sim_case, nodes, devices, terminals, schedule)
        decoder_fail = decoder_run["check_fail"]
        decoder_model_range = decoder_run["model_upper_result"]
        decoder_magnitude = decoder_run["magnitude_result"]
    else:
        decoder_checks, terminal_rows = [], []
        decoder_fail = sum(row["result"] != "PASS" for row in phase_checks
                           if row["check"].startswith("invalid_"))
        decoder_model_range = "NOT_EVALUATED_FOR_SUPPRESSED_ACCESS"
        decoder_magnitude = "NOT_EVALUATED_FOR_SUPPRESSED_ACCESS"
    all_checks = phase_checks + decoder_checks
    phase_fail = sum(row["result"] != "PASS" for row in phase_checks)
    decoder_logic_pass = decoder_fail == 0
    passed = phase_fail == 0 and decoder_logic_pass
    result = {
        "case": case["label"], "profile": case["profile"],
        "control_vector_csb_oeb_web": case["control_vector"],
        "operation": VALID_VECTORS.get(case["control_vector"], "invalid_or_idle"),
        "old_address": case["old"], "new_address": case["new"],
        "selected_row": case["new"], "phase_ps": case["phase_ps"],
        "clk_fall_ps": case["clk_fall_ps"], "wl_cap_ff": wl_cap_ff,
        "bitline_external_load_ff": CBL_EXTERNAL_FF,
        "bitline_target_effective_ceiling_ff": CBL_CHARACTERIZED_LIMIT_FF,
        "phase_checks_pass": len(phase_checks)-phase_fail,
        "phase_checks_fail": phase_fail,
        "decoder_logic_checks_fail": decoder_fail,
        "decoder_model_upper_result": decoder_model_range,
        "decoder_terminal_magnitude_result": decoder_magnitude,
        "status": "PASS" if passed else "REJECTED_SCREEN",
        "ngspice_returncode": proc.returncode,
        "precharge_timing": phase_metrics,
        "checks": all_checks,
        "terminals": terminal_rows,
    }
    (case_dir / "case.json").write_text(json.dumps(
        {key: value for key, value in result.items() if key not in {"checks", "terminals"}},
        indent=2) + "\n", encoding="utf-8")
    write_csv(case_dir / "checks.csv", all_checks)
    write_csv(case_dir / "terminals.csv", terminal_rows)
    if not keep_raw:
        raw_path.unlink(missing_ok=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--profiles", nargs="+", choices=("tt", "slow", "fast"),
                        default=["tt"])
    parser.add_argument("--transitions", nargs="+", default=["0:0", "0:1", "0:2", "0:3"],
                        metavar="OLD:NEW")
    parser.add_argument("--control-vectors", nargs="+", choices=ALL_CONTROL_VECTORS,
                        default=["001", "010"])
    parser.add_argument("--phase-ps", type=float, default=1950.0,
                        help="Experimental capture-to-PCLK phase from the ideal-PCLK study")
    parser.add_argument("--clk-fall-ps", type=float, default=20700.0)
    parser.add_argument("--settling-allowance-ns", type=float, default=3.3)
    parser.add_argument("--wl-cap-ff", type=float, default=102.873935496,
                        help="Full-row Ceff maximum from Danilo's current owner evidence")
    parser.add_argument("--release-lead-ps", type=float, default=250.0,
                        help="PRECH release lead before the clock/initial PCLK edge")
    parser.add_argument("--turnoff-guard-ps", type=float, default=500.0,
                        help="PRECH reassertion delay after PCLK falls")
    parser.add_argument("--step-ps", type=float, default=5.0)
    parser.add_argument("--transitions-per-vector", action="store_true",
                        help="Apply every transition to every requested control vector")
    parser.add_argument("--keep-raw", action="store_true")
    args = parser.parse_args()

    output = args.output_dir.resolve()
    require(not output.exists(), f"Choose a new output directory: {output}")
    require(math.isfinite(args.phase_ps) and args.phase_ps >= 0,
            "phase must be a finite nonnegative number")
    require(math.isfinite(args.clk_fall_ps) and args.clk_fall_ps > CAPTURE_NS*1000+args.phase_ps,
            "clock fall must leave a positive PCLK evaluation phase")
    require(math.isfinite(args.settling_allowance_ns) and args.settling_allowance_ns > 0
            and args.settling_allowance_ns < (args.clk_fall_ps-CAPTURE_NS*1000-args.phase_ps)/1000,
            "settling allowance must fit inside the PCLK evaluation window")
    require(math.isfinite(args.wl_cap_ff) and args.wl_cap_ff > 0,
            "WL capacitance must be positive")
    require(math.isfinite(args.step_ps) and args.step_ps > 0,
            "maximum transient step must be positive")
    require(math.isfinite(args.release_lead_ps) and args.release_lead_ps >= 0
            and math.isfinite(args.turnoff_guard_ps) and args.turnoff_guard_ps >= 0,
            "phase margins must be finite and nonnegative")
    transitions = []
    for item in args.transitions:
        match = re.fullmatch(r"([0-3]):([0-3])", item)
        require(match is not None, f"Invalid address transition: {item}")
        transitions.append((int(match[1]), int(match[2])))
    require(len(set(transitions)) == len(transitions), "Duplicate transitions")
    control_vectors = args.control_vectors
    require(len(set(control_vectors)) == len(control_vectors), "Duplicate control vectors")
    pex_text = PRECHARGE_PEX.read_text(encoding="utf-8")
    pex_evidence = inspect_precharge_pex(pex_text)
    provenance = json.loads(PRECHARGE_PROVENANCE.read_text(encoding="utf-8"))
    require(provenance.get("source_sha256") == pex_evidence["sha256"],
            "Precharge PEX provenance does not match its content")
    row_provenance = json.loads(distributed.ROW_CEFF_SIDECAR.read_text(encoding="utf-8"))
    wl_cap_max = float(row_provenance["cwl_pex_ff_range"][1])
    require(abs(wl_cap_max-args.wl_cap_ff) <= 5e-7,
            f"Requested WL load differs from owner evidence maximum {wl_cap_max:.9f} fF")

    pdk = Path(os.environ.get("PDK_ROOT", "/opt/pdks")) / "sky130A"
    model = pdk / "libs.tech/combined/continuous/sky130.lib.spice"
    lib_dir = pdk / "libs.ref/sky130_fd_sc_hd/lib"
    require(model.is_file(), f"SKY130 transistor model not found: {model}")
    lib_paths = {profile: lib_dir / capture.LIBRARIES[profile] for profile in args.profiles}
    require(all(path.is_file() for path in lib_paths.values()), "A requested SKY130 Liberty file is missing")
    arcs = {profile: capture.liberty_arc(path, capture.LIBERTY_LOADS_PF["nominal"])
            for profile, path in lib_paths.items()}
    thresholds = {}
    for profile, path in lib_paths.items():
        text = path.read_text(encoding="utf-8")
        lower = float(re.search(r"slew_lower_threshold_pct_rise\s*:\s*([\d.]+)", text)[1])
        upper = float(re.search(r"slew_upper_threshold_pct_rise\s*:\s*([\d.]+)", text)[1])
        thresholds[profile] = {"slew_lower_pct": lower, "slew_upper_pct": upper}

    output.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="decoder-precharge-netlist-") as temp:
        netlist = contract.netlist_current(Path(temp))
    netlist, decoder_wl_pex_evidence = capture.inject_combined_pex(netlist)
    netlist, precharge_instances = attach_precharge_pex(netlist, pex_text)
    netlist_hash = hashlib.sha256(netlist.encode()).hexdigest()
    (output / "simulation_input_netlist.spice").write_text(netlist, encoding="utf-8")

    cases = []
    vector_transitions = [(vector, pair) for vector in control_vectors
                          for pair in (transitions if args.transitions_per_vector or vector in VALID_VECTORS
                                       else transitions[:1])]
    for profile in args.profiles:
        for vector, (old, new) in vector_transitions:
            label = f"{profile}_ctl{vector}_a{old}_to_{new}_p{args.phase_ps:g}"
            cases.append({"label": label, "profile": profile, "control_vector": vector,
                          "old": old, "new": new, "phase_ps": args.phase_ps,
                          "clk_fall_ps": args.clk_fall_ps,
                          "settling_allowance_ns": args.settling_allowance_ns,
                          **thresholds[profile]})

    hashes = {
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "row_decoder_schematic_sha256": hashlib.sha256((ROOT / "cells/row_decoder/row_decoder.sch").read_bytes()).hexdigest(),
        "row_decoder_pex_sha256": decoder_wl_pex_evidence["row_decoder"]["pex_sha256"],
        "wl_driver_schematic_sha256": hashlib.sha256((ROOT / "cells/wordline_driver/wl_driver.sch").read_bytes()).hexdigest(),
        "wl_driver_pex_sha256": decoder_wl_pex_evidence["wl_driver"]["sha256"][str((ROOT / "layout/wl_driver/pex/wl_driver_pex.spice").relative_to(ROOT))],
        "precharge_pex_sha256": pex_evidence["sha256"],
        "precharge_provenance_sha256": hashlib.sha256(PRECHARGE_PROVENANCE.read_bytes()).hexdigest(),
        "row_ceff_provenance_sha256": hashlib.sha256(distributed.ROW_CEFF_SIDECAR.read_bytes()).hexdigest(),
        "input_netlist_sha256": netlist_hash,
    }
    model_hashes = contract.model_dependencies(model)
    for path in lib_paths.values():
        model_hashes[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {
        "campaign": "dynamic_decoder_wl_precharge_phase_interface",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "complete": False,
        "source_branch": subprocess.run(["git", "branch", "--show-current"], cwd=ROOT,
                                         capture_output=True, text=True, check=True).stdout.strip(),
        "scope": "Current decoder R-C PEX, four WL-driver R-C PEX instances, eight Danilo W2.52 precharge PEX instances and capacitive bitline residuals. Ideal PCLK and PRECH stimuli; no explicit 6T access devices in this integration bench.",
        "precharge_candidate": {**pex_evidence, "source_provenance": provenance,
                                "instances": precharge_instances},
        "decoder_wl_pex_evidence": decoder_wl_pex_evidence,
        "wordline_load": {"full_row_max_ff": wl_cap_max,
                          "sidecar": str(distributed.ROW_CEFF_SIDECAR.relative_to(ROOT)),
                          "not_double_counted_with_distributed_row": True},
        "bitline_load": {"target_effective_ceiling_ff": CBL_CHARACTERIZED_LIMIT_FF,
                         "precharge_leaf_max_ceff_ff": PRECHARGE_CEFF_MAX_FF,
                         "external_residual_ff_per_side": CBL_EXTERNAL_FF,
                         "interpretation": "Conservative capacitance residual using Danilo's maximum reported W2.52 precharge Ceff; PEX Ceff is state dependent and the complete G7 leaf set is not instantiated."},
        "phase_assumptions": {"precharge_active_level": "PRECH low",
                              "decoder_precharge_level": "PCLK low",
                              "read_control": "001", "write_control": "010",
                              "invalid_vectors": "all other CSb/OEb/WEb combinations suppress second-cycle PCLK and keep PRECH active",
                              "release_lead_ps": args.release_lead_ps,
                              "turnoff_guard_ps": args.turnoff_guard_ps,
                              "capture_to_pclk_ps": args.phase_ps,
                              "clock_fall_ps": args.clk_fall_ps,
                              "all_numeric_phase_margins_are_experimental": True},
        "tools": {"xschem": screen.tool_version("xschem"), "ngspice": screen.tool_version("ngspice")},
        "model_dependencies_sha256": model_hashes,
        "source_hashes": hashes,
        "maximum_step_ps": args.step_ps,
        "case_count": len(cases),
        "cases": cases,
    }
    (output / "executed_script.py").write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    results = []
    checks = []
    errors = []
    for index, case in enumerate(cases, 1):
        print(f"precharge phase interface: {index}/{len(cases)} {case['label']}", flush=True)
        try:
            result = run_case(case, netlist, model, arcs, args.wl_cap_ff,
                              args.step_ps, args.release_lead_ps,
                              args.turnoff_guard_ps, output, args.keep_raw)
        except Exception as exc:  # Keep completed cases and report exact failing case.
            result = {"case": case["label"], "status": "ERROR", "error": str(exc)}
        results.append(result)
        if result.get("status") == "ERROR":
            errors.append(result)
        checks.extend(result.get("checks", []))
        print(f"  {result.get('status')} phase_fail={result.get('phase_checks_fail', '')} "
              f"decoder_fail={result.get('decoder_logic_checks_fail', '')}", flush=True)

    write_csv(output / "summary.csv", [
        {key: value for key, value in row.items() if key not in {"checks", "terminals", "precharge_timing"}}
        for row in results])
    write_csv(output / "checks.csv", checks)
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["complete"] = len(results) == len(cases) and not errors
    manifest["passed_cases"] = sum(row.get("status") == "PASS" for row in results)
    manifest["failed_cases"] = sum(row.get("status") == "REJECTED_SCREEN" for row in results)
    manifest["errors"] = errors
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Summary: {output / 'summary.csv'}")
    print(f"Checks: {output / 'checks.csv'}")
    print(f"Manifest: {output / 'manifest.json'}")
    return 2 if errors else int(any(row.get("status") != "PASS" for row in results))


if __name__ == "__main__":
    raise SystemExit(main())
