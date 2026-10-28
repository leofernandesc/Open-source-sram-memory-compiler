#!/usr/bin/env python3
"""Measure a SKY130 register-to-dynamic-decoder timing contract.

The two address bits are launched by the PDK's transistor-level dfxtp_1 cell.
PCLK remains an independent evaluator waveform so its delay from the address
capture edge can be swept without assuming an unapproved clock generator.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import numpy as np

import run_row_decoder_contract as contract
import run_row_decoder_tt as screen
from plot_row_decoder_review import read_raw

ROOT = screen.ROOT
CAPTURE_PS = 15_000.0
FIRST_CAPTURE_PS = 2_000.0
D_SETUP_PS = 2_000.0
D_SLEW_PS = 50.0
CAPTURE_SLEW_PS = 50.0
SCRIPT_TEXT = Path(__file__).read_text()
SCRIPT_SHA256 = hashlib.sha256(SCRIPT_TEXT.encode()).hexdigest()


def profile_condition(profile: str) -> tuple[str, float, float]:
    return contract.PROFILES[profile]


def dff_subckt(path: Path) -> str:
    text = path.read_text()
    pattern = r"(?ims)^\.subckt\s+sky130_fd_sc_hd__dfxtp_1\s+([^\n]+)\n(.*?)^\.ends\b[^\n]*"
    matches = list(re.finditer(pattern, text))
    screen.require(len(matches) == 1, "PDK must contain exactly one dfxtp_1 SPICE subcircuit")
    pins = matches[0].group(1).upper().split()
    screen.require(pins == ["CLK", "D", "VGND", "VNB", "VPB", "VPWR", "Q"],
                   f"Unexpected dfxtp_1 terminal order: {pins}")
    return matches[0].group(0)


def source_pwl(initial: float, target: float, start_ps: float, slew_ps: float,
               stop_s: float) -> str:
    transitions = [] if initial == target else [
        (start_ps * 1e-12, (start_ps + slew_ps) * 1e-12, target)
    ]
    return contract.pwl(initial, transitions, stop_s)


def clock_pwl(vdd: float, rise_ps: float, stop_s: float) -> str:
    edges = []
    for center, target in ((FIRST_CAPTURE_PS, vdd),
                           (FIRST_CAPTURE_PS + 500.0, 0.0),
                           (CAPTURE_PS, vdd),
                           (CAPTURE_PS + 500.0, 0.0)):
        edges.append((center * 1e-12 - rise_ps * 0.5e-12,
                      center * 1e-12 + rise_ps * 0.5e-12, target))
    return contract.pwl(0.0, edges, stop_s)


def top_pin_map(netlist: str) -> dict[str, str]:
    top = screen.logical_lines(netlist.split("* expanding", 1)[0])
    instance = next((line.split() for line in top if line.lower().startswith("x1 ")), None)
    screen.require(instance is not None, "Missing top-level row_decoder instance x1")
    pins, _ = screen.subcircuit(netlist, "row_decoder")
    return dict(zip(pins, instance[1:-1]))


def make_capture_deck(netlist: str, case: dict, model: Path, cell_text: str,
                      cell_path: Path) -> tuple[str, dict, dict, dict, dict, dict]:
    phase_ps = float(case["capture_to_pclk_ps"])
    pclk_rise_ps = float(case.get("pclk_rise_ps", 25.0))
    pclk_fall_ps = float(case.get("pclk_fall_ps", 25.0))
    screen.require(phase_ps >= 0 and math.isfinite(phase_ps), "Capture-to-PCLK phase must be nonnegative")
    # The first PCLK evaluation starts at 5 ns and ends at 10 ns. The captured
    # address changes at 15 ns; the second PCLK rise is placed phase_ps later.
    low_ns = 5.0 + phase_ps / 1000.0
    sim_case = {
        **case,
        "campaign": "timing",
        "low_ns": low_ns,
        "high_ns": float(case.get("high_ns", 5.0)),
        "lead_ps": 2_000,
        "address_ps": 50,
        "rise_ps": pclk_rise_ps,
        "fall_ps": pclk_fall_ps,
        "step_ps": float(case.get("step_ps", 1.0)),
        "method": "gear",
        "minbreak_fs": 1,
        "chgtol_c": 1e-18,
    }
    deck, nodes, decoder_devices, terminals, schedule = contract.make_deck(netlist, sim_case, model)
    ports = top_pin_map(netlist)
    vdd = float(schedule["vdd"])
    stop_s = float(schedule["stop"])
    old, new = int(case["old"]), int(case["new"])

    for bit, name in ((0, "VA0"), (1, "VA1")):
        old_bit, new_bit = (old >> bit) & 1, (new >> bit) & 1
        d_start_ps = CAPTURE_PS - D_SETUP_PS
        waveform = source_pwl(old_bit * vdd, new_bit * vdd, d_start_ps, D_SLEW_PS, stop_s)
        pattern = rf"(?im)^{name}\s+\S+\s+\S+\s+[^\n]+$"
        deck, count = re.subn(pattern, f"{name} D{bit} GND {waveform}", deck, count=1)
        screen.require(count == 1, f"Expected one {name} source in the Xschem netlist")

    capclk = clock_pwl(vdd, CAPTURE_SLEW_PS, stop_s)
    clock_line = f"VCAPCLK CAPCLK GND {capclk}"
    flops = (f"XCAP0 CAPCLK D0 GND GND {ports['VDD']} {ports['VDD']} {ports['A0']} sky130_fd_sc_hd__dfxtp_1\n"
             f"XCAP1 CAPCLK D1 GND GND {ports['VDD']} {ports['VDD']} {ports['A1']} sky130_fd_sc_hd__dfxtp_1")
    spice_cell = f"* SKY130A dfxtp_1 cell subcircuit extracted from {cell_path}\n{cell_text}\n"
    deck = deck.replace(".lib ", spice_cell + "\n" + clock_line + "\n" + flops + "\n.lib ", 1)
    screen.require("XCAP0 CAPCLK D0" in deck and "XCAP1 CAPCLK D1" in deck,
                   "Could not insert the address capture flip-flops")
    deck, count = re.subn(r"(?im)^(\.save\s+[^\n]+)$", r"\1 v(CAPCLK) v(D0) v(D1)", deck, count=1)
    screen.require(count == 1, "Could not add capture waveforms to the save list")
    # Do not include the full cell-library file: embed the exact selected PDK
    # subcircuit while hashing the full source file in the run manifest.
    screen.require(cell_path.is_file() and str(model) in deck,
                   "Missing PDK source or transistor model include")
    return deck, nodes, decoder_devices, terminals, schedule, sim_case, ports


def crossing(time: np.ndarray, signal: np.ndarray, threshold: float, rising: bool,
             start_s: float, end_s: float) -> float | None:
    indices = np.flatnonzero((time[:-1] >= start_s) & (time[1:] <= end_s))
    if rising:
        hits = indices[(signal[indices] < threshold) & (signal[indices + 1] >= threshold)]
    else:
        hits = indices[(signal[indices] > threshold) & (signal[indices + 1] <= threshold)]
    if not hits.size:
        return None
    i = int(hits[0])
    dv = signal[i + 1] - signal[i]
    if dv == 0:
        return float(time[i + 1])
    return float(time[i] + (threshold - signal[i]) * (time[i + 1] - time[i]) / dv)


def trace(raw: dict[str, np.ndarray], node: str) -> np.ndarray:
    key = node.lower()
    if not key.startswith("v("):
        key = f"v({key})"
    screen.require(key in raw, f"Missing saved waveform {key}")
    return raw[key]


def edge_metrics(raw: dict[str, np.ndarray], case: dict, nodes: dict,
                 decoder_devices: dict, terminals: dict, ports: dict, vdd: float) -> dict:
    time = raw["time"]
    capture = crossing(time, trace(raw, "CAPCLK"), 0.5 * vdd, True,
                       (CAPTURE_PS - 200) * 1e-12, (CAPTURE_PS + 200) * 1e-12)
    pclk_node = nodes["PCLK"]
    pclk = crossing(time, trace(raw, pclk_node), 0.5 * vdd, True, 10e-9, time[-1])
    screen.require(capture is not None and pclk is not None, "Missing capture or PCLK rising crossing")
    target = int(case["new"])
    old = int(case["old"])
    q_nodes = {"A0": ports["A0"], "A1": ports["A1"]}
    bits = {"A0": target & 1, "A1": (target >> 1) & 1}
    previous = {"A0": old & 1, "A1": (old >> 1) & 1}
    settle_times: dict[str, float] = {}
    q50: dict[str, float | None] = {}
    for name, node in q_nodes.items():
        y = trace(raw, node)
        direction = bool(bits[name])
        q50[name] = (crossing(time, y, 0.5 * vdd, direction, capture, pclk + 2e-9)
                     if bits[name] != previous[name] else None)
        threshold = 0.9 * vdd if direction else 0.1 * vdd
        settled = (crossing(time, y, threshold, direction, capture, pclk + 2e-9)
                   if bits[name] != previous[name] else capture)
        screen.require(settled is not None, f"{name} did not reach its 10/90% target")
        settle_times[name] = float(settled)

    def mos_drain(device: str) -> str:
        pins = terminals["x1." + device.lower()]
        return pins[0]

    literal_nodes = {
        "A0B": (mos_drain("M1"), 1 - bits["A0"]),
        "A0T": (mos_drain("M26"), bits["A0"]),
        "A1B": (mos_drain("M3"), 1 - bits["A1"]),
        "A1T": (mos_drain("M28"), bits["A1"]),
    }
    for name, (node, target_bit) in literal_nodes.items():
        y = trace(raw, node)
        rising = bool(target_bit)
        threshold = 0.9 * vdd if rising else 0.1 * vdd
        bit_name = "A0" if name.startswith("A0") else "A1"
        old_literal = previous[bit_name] if name.endswith("T") else 1 - previous[bit_name]
        changed = target_bit != old_literal
        settled = crossing(time, y, threshold, rising, capture, pclk + 2e-9) if changed else capture
        screen.require(settled is not None, f"{name} did not reach its 10/90% target")
        settle_times[name] = float(settled)

    latest_q = max(settle_times[name] for name in ("A0", "A1"))
    latest_literal = max(settle_times.values())
    pclk50_ps = (pclk - capture) * 1e12
    return {
        "capture_to_pclk50_ps": pclk50_ps,
        "a0_clk_to_q50_ps": "" if q50["A0"] is None else (q50["A0"] - capture) * 1e12,
        "a1_clk_to_q50_ps": "" if q50["A1"] is None else (q50["A1"] - capture) * 1e12,
        "latest_q_10_90_settle_ps": (latest_q - capture) * 1e12,
        "q_settle_lead_to_pclk_ps": (pclk - latest_q) * 1e12,
        "latest_literal_10_90_settle_ps": (latest_literal - capture) * 1e12,
        "literal_settle_lead_to_pclk_ps": (pclk - latest_literal) * 1e12,
        "pclk_phase_target_ps": float(case["capture_to_pclk_ps"]),
        "pclk_phase_error_ps": pclk50_ps - float(case["capture_to_pclk_ps"]),
    }


def execute_case(case: dict, netlist: str, model: Path, cell_text: str,
                 cell_path: Path, out_dir: Path, keep_raw: bool) -> dict:
    deck, nodes, decoder_devices, terminals, schedule, sim_case, ports = make_capture_deck(
        netlist, case, model, cell_text, cell_path)
    deck_hash = hashlib.sha256(deck.encode()).hexdigest()
    out_dir.mkdir(parents=True, exist_ok=True)
    deck_path = out_dir / "case.spice"
    log_path = out_dir / "ngspice.log"
    raw_path = out_dir / "waveform.raw"
    cached_path = out_dir / "case.json"
    if cached_path.is_file():
        cached = json.loads(cached_path.read_text())
        if cached.get("deck_sha256") == deck_hash and cached.get("status") != "ERROR":
            return cached
    deck_path.write_text(deck)
    raw_path.unlink(missing_ok=True)
    proc = subprocess.run(["ngspice", "-n", "-b", str(deck_path)], cwd=out_dir,
                          capture_output=True, text=True, timeout=240)
    log = proc.stdout + proc.stderr
    log_path.write_text(log)
    if proc.returncode != 0 or re.search(r"Error:|failed!|aborted|timestep too small", log, re.I) or not raw_path.is_file():
        result = {"case": case["label"], "status": "ERROR", "deck_sha256": deck_hash,
                  "ngspice_returncode": proc.returncode, "error": "ngspice failed or produced no complete waveform"}
        cached_path.write_text(json.dumps(result, indent=2) + "\n")
        return result
    raw = read_raw(raw_path)
    run, checks, extrema = contract.analyze(raw, sim_case, nodes, decoder_devices,
                                             terminals, schedule)
    vdd = float(schedule["vdd"])
    edge = edge_metrics(raw, case, nodes, decoder_devices, terminals, ports, vdd)
    model_pass = run["model_upper_result"] == "PASS" and run["magnitude_result"] == "PASS"
    logic_pass = run["check_fail"] == 0
    result = {
        "case": case["label"], "profile": case["profile"],
        "corner": run["corner"], "vdd_v": run["vdd_v"], "temperature_c": run["temperature_c"],
        "old_address": int(case["old"]), "new_address": int(case["new"]),
        "capture_to_pclk_target_ps": float(case["capture_to_pclk_ps"]),
        **edge, "logic_pass": logic_pass, "voltage_screen_pass": model_pass,
        "qualification_pass": logic_pass and model_pass,
        "logic_checks_pass": run["check_pass"], "logic_checks_fail": run["check_fail"],
        "terminal_magnitude_max_v": run["terminal_magnitude_max_v"],
        "terminal_magnitude_device": run["terminal_magnitude_device"],
        "terminal_magnitude_voltage": run["terminal_magnitude_voltage"],
        "wl_delay90_ps": run["wl_delay90_ps"], "dec_delay90_ps": run["dec_delay90_ps"],
        "decoder_channel_area_proxy_um2": run["channel_area_proxy_um2"],
        "deck_sha256": deck_hash, "ngspice_returncode": proc.returncode,
        "status": "PASS" if logic_pass and model_pass else "REJECTED_TIMING_OR_VOLTAGE",
        "checks": checks, "terminals": extrema,
    }
    cached_path.write_text(json.dumps(result, indent=2) + "\n")
    if not keep_raw:
        raw_path.unlink(missing_ok=True)
    return result


def write_csv(path: Path, rows: list[dict]) -> None:
    screen.write_csv(path, rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--profiles", nargs="+", choices=tuple(contract.PROFILES),
                        default=["tt", "slow", "fast"])
    parser.add_argument("--phase-ps", nargs="+", type=float,
                        default=[0, 100, 200, 300, 400, 500, 600, 750, 1000, 1250, 1500])
    parser.add_argument("--workers", type=int, choices=(1, 2, 4), default=2)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--keep-raw", action="store_true",
                        help="Keep a raw waveform for every case (large output)")
    args = parser.parse_args()
    screen.require(args.resume or not args.output_dir.exists(), "Use a new output directory or --resume")
    args.output_dir.mkdir(parents=True, exist_ok=args.resume)
    pdk = Path(os.environ.get("PDK_ROOT", "/opt/pdks")) / "sky130A"
    model = pdk / "libs.tech/combined/continuous/sky130.lib.spice"
    cell_path = pdk / "libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice"
    screen.require(model.is_file() and cell_path.is_file(), "SKY130A MOS or standard-cell model not found")
    cell_text = dff_subckt(cell_path)
    cell_sha256 = hashlib.sha256(cell_text.encode()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="decoder-capture-netlist-") as temp:
        netlist = contract.netlist_current(Path(temp))
    nodes, devices = screen.inspect_netlist(netlist, True)
    screen.require(len(devices) == 29, "Capture timing study requires the retained 29-MOS B7 decoder")
    netlist_sha256 = hashlib.sha256(netlist.encode()).hexdigest()
    profiles = {name: profile_condition(name) for name in args.profiles}
    cases = []
    for profile in args.profiles:
        for old in range(4):
            for new in range(4):
                if old == new:
                    continue
                for phase_ps in args.phase_ps:
                    label = f"{profile}_a{old}_to_{new}_p{phase_ps:g}ps"
                    cases.append({"label": label, "profile": profile, "old": old, "new": new,
                                  "capture_to_pclk_ps": phase_ps, "pclk_rise_ps": 25.0,
                                  "pclk_fall_ps": 25.0, "step_ps": 1.0})
    screen.require(len(cases) == len({case["label"] for case in cases}), "Case labels are not unique")
    existing_manifest = args.output_dir / "manifest.json"
    if args.resume:
        screen.require(existing_manifest.is_file(), "No manifest to resume")
        previous = json.loads(existing_manifest.read_text())
        screen.require(previous.get("cases") == cases and previous.get("netlist_sha256") == netlist_sha256,
                       "Resume requires the same case matrix and fresh source netlist")
    script_file = args.output_dir / "executed_script.py"
    script_file.write_text(SCRIPT_TEXT)
    cell_copy = args.output_dir / "dfxtp_1.spice"
    cell_copy.write_text(cell_text + "\n")
    tools = {"xschem": screen.tool_version("xschem"), "ngspice": screen.tool_version("ngspice")}
    models = contract.model_dependencies(model)
    models[str(cell_path.resolve())] = hashlib.sha256(cell_path.read_bytes()).hexdigest()
    models = dict(sorted(models.items()))
    manifest = {
        "campaign": "capture_to_pclk", "stage": "pre-layout", "complete": False,
        "started_utc": datetime.now(timezone.utc).isoformat(), "source": "fresh Xschem netlist",
        "candidate": "B7 dynamic decoder and four existing WL buffers",
        "capture_cell": "sky130_fd_sc_hd__dfxtp_1", "capture_cell_model": str(cell_path),
        "capture_cell_source_sha256": hashlib.sha256(cell_path.read_bytes()).hexdigest(),
        "capture_cell_subckt_sha256": cell_sha256,
        "capture_cell_pins": ["CLK", "D", "VGND", "VNB", "VPB", "VPWR", "Q"],
        "capture_clock_edge_ps": CAPTURE_PS, "initialization_capture_edge_ps": FIRST_CAPTURE_PS,
        "D_transition_start_ps": CAPTURE_PS-D_SETUP_PS,
        "D_transition_slew_ps": D_SLEW_PS,
        "D_input_settled_before_capture_ps": D_SETUP_PS-D_SLEW_PS/2,
        "capture_clock_slew_ps": CAPTURE_SLEW_PS,
        "PCLK_role": "independent delayed evaluation edge; low before edge precharges dynamic nodes",
        "timing_screen": "same 10/90 output logic checks and 1 ns settling allowance as B7 contract study",
        "address_setup_scope": "D-to-capture is held stable about 1.925 ns; this experiment measures capture-Q-to-PCLK, not external D setup/hold",
        "no_claim": "No full macro Fmax, setup/hold specification, extracted parasitics, or physical clock-delay implementation",
        "profiles": profiles, "cases": cases, "netlist_sha256": netlist_sha256,
        "canonical_decoder_sha256": hashlib.sha256((ROOT/"cells/row_decoder/row_decoder.sch").read_bytes()).hexdigest(),
        "script_sha256": SCRIPT_SHA256, "model_dependencies_sha256": models, "tools": tools,
        "workers": args.workers, "resume": args.resume,
    }
    existing_manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    cases_dir = args.output_dir / "cases"
    cases_dir.mkdir(exist_ok=True)
    results: list[dict] = []
    errors: list[dict] = []

    def work(case: dict) -> tuple[dict | None, dict | None]:
        try:
            result = execute_case(case, netlist, model, cell_text, cell_path,
                                  cases_dir / case["label"], args.keep_raw)
            return result, None
        except Exception as exc:  # Store failed case identity and continue independent runs.
            return None, {"case": case["label"], "error": type(exc).__name__ + ": " + str(exc)}

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for index, (result, error) in enumerate(pool.map(work, cases), 1):
            if error:
                errors.append(error)
                print(json.dumps(error), flush=True)
            else:
                results.append(result)
            if index % 24 == 0 or index == len(cases):
                print(f"capture-to-PCLK: {index}/{len(cases)} cases completed", flush=True)
    summary_rows = [{key: value for key, value in result.items() if key not in {"checks", "terminals"}}
                    for result in results]
    all_checks = [row for result in results for row in result.get("checks", [])]
    all_terminals = [row for result in results for row in result.get("terminals", [])]
    if summary_rows:
        write_csv(args.output_dir / "summary.csv", summary_rows)
    if all_checks:
        write_csv(args.output_dir / "checks.csv", all_checks)
    if all_terminals:
        write_csv(args.output_dir / "terminals.csv", all_terminals)
    errors_path = args.output_dir / "errors.json"
    errors_path.write_text(json.dumps(errors, indent=2) + "\n")
    complete = not errors and len(results) == len(cases)
    manifest.update(complete=complete, completed_cases=len(results), errors=errors,
                    qualification_pass_cases=sum(bool(row.get("qualification_pass")) for row in results),
                    qualification_rejected_cases=sum(not bool(row.get("qualification_pass")) for row in results),
                    finished_utc=datetime.now(timezone.utc).isoformat())
    existing_manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    return 2 if not complete else 0


if __name__ == "__main__":
    raise SystemExit(main())
