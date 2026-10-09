#!/usr/bin/env python3
"""Screen the dynamic decoder and WL drivers against Danilo's 8-bit row PEX.

This is a transistor-level PEX simulation of the decoder, four WL drivers and
four identical extracted 8-bit physical rows. Bitlines are held at an ideal
precharged VDD level, so this isolates wordline loading; it is not a read/write
macro simulation or a substitute for the actual precharge/sense interface.
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sims/row_decoder"))

import run_row_decoder_capture_timing as capture
import run_row_decoder_contract as contract
import run_row_decoder_tt as screen

ROW_PEX = ROOT / "sims/row_decoder/inputs/row_8_wl_pex_95c23c0.spice"
ROW_PEX_SHA256 = "160b65544e12481aa99b287329ef2798e80c184c8f91566a23177ed8f0fb2dd6"
ROW_CEFF_SIDECAR = ROOT / "sims/row_decoder/inputs/row_8_wl_pex_capacitance_latch_t0_requal_20261008.provenance.json"
CAPTURE_NS = 15.0
DEFAULT_TRANSITIONS = ("1:0", "0:1", "0:2", "0:3")
CONTROL_VECTORS = ("000", "001", "010", "011", "100", "101", "110", "111")
ACCESS_CONTROL = {"001": "read", "010": "write"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def write_union_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def inspect_row_pex(text: str) -> dict:
    require(hashlib.sha256(text.encode()).hexdigest() == ROW_PEX_SHA256,
            "The copied physical-row PEX SHA-256 differs from its recorded source")
    lines = screen.logical_lines(text)
    start = next((i for i, line in enumerate(lines)
                  if re.match(r"(?i)^\.subckt\s+row_8_wl_flat\b", line)), None)
    require(start is not None, "Missing row_8_wl_flat subcircuit")
    header = lines[start].split()
    pins = [pin.upper() for pin in header[2:]]
    expected = ["VDD", "VSS", "WL"] + [pin for bit in range(8)
                                          for pin in (f"BL{bit}", f"BLB{bit}")]
    require(pins == expected, f"Unexpected physical-row PEX pin order: {pins}")
    end = next((i for i in range(start + 1, len(lines))
                if re.match(r"(?i)^\.ends\b", lines[i])), None)
    require(end is not None, "Physical-row PEX has no matching .ends")
    body = lines[start + 1:end]
    mos = [line for line in body if re.match(
        r"(?i)^X\d+\s+.*\bsky130_fd_pr__(?:n|p)fet_01v8\b", line)]
    resistors = [line for line in body if re.match(r"(?i)^R\S+\s", line)]
    capacitors = [line for line in body if re.match(r"(?i)^C\S+\s", line)]
    require((len(mos), len(resistors), len(capacitors)) == (48, 786, 349),
            "The physical-row PEX device/parasitic inventory changed: "
            f"MOS={len(mos)} R={len(resistors)} C={len(capacitors)}")
    negative = []
    for line in capacitors:
        fields = line.split()
        require(len(fields) >= 4, f"Malformed PEX capacitor: {line}")
        match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)[a-zA-Z]*", fields[3])
        require(match is not None, f"Unrecognized PEX capacitance: {line}")
        if float(match.group(1)) < 0:
            negative.append(line)
    require(not negative, "Physical-row PEX contains negative capacitors")
    return {"subcircuit": "row_8_wl_flat", "pins": pins,
            "mos_devices_per_row": len(mos), "resistors_per_row": len(resistors),
            "capacitors_per_row": len(capacitors), "negative_capacitors": 0,
            "sha256": ROW_PEX_SHA256}


def attach_physical_rows(netlist: str, pex_text: str, nodes: dict) -> tuple[str, dict]:
    """Replace no owner source: add four read-only row PEX instances to the bench."""
    pex = inspect_row_pex(pex_text)
    ports = capture.top_pin_map(netlist)
    bitlines = [name for bit in range(8) for name in (f"BL{bit}", f"BLB{bit}")]
    row_instances = [
        f"XROW{row} {ports['VDD']} {ports['VSS']} {nodes[f'WL{row}']} "
        f"{' '.join(bitlines)} row_8_wl_flat"
        for row in range(4)
    ]
    require(len(row_instances) == 4 and all(f"WL{row}" in nodes for row in range(4)),
            "Could not map all four decoder-to-WL outputs")
    marker = "* expanding"
    require(marker in netlist, "Xschem top-level expansion marker is missing")
    netlist = netlist.replace(marker, "\n".join(row_instances) + "\n\n" + marker, 1)
    netlist, count = re.subn(r"(?im)^\.end\s*$", pex_text.rstrip() + "\n.end", netlist, count=1)
    require(count == 1, "Could not add the physical-row PEX definition")
    return netlist, {**pex, "instances": row_instances,
                     "bitline_pins_shared_across_four_rows": True,
                     "bitline_mode": "one ideal VDD precharge source per BL/BLB pair, held during the complete transient"}


def add_bitline_sources(deck: str, vdd: float, vss: str) -> str:
    bitlines = [name for bit in range(8) for name in (f"BL{bit}", f"BLB{bit}")]
    sources = "\n".join(f"V_PRE_{name} {name} {vss} {vdd:.12g}" for name in bitlines)
    deck, count = re.subn(r"(?im)^(VDD_SRC\s+[^\n]+)$",
                          lambda match: match.group(1) + "\n" + sources,
                          deck, count=1)
    require(count == 1, "Could not place ideal bitline precharge sources")
    return deck


def set_transient_step(deck: str, step_ps: float, stop_s: float) -> str:
    deck, count = re.subn(
        r"(?im)^\.tran\s+\S+\s+\S+\s+0\s+\S+(?:\s+uic)?\s*$",
        f".tran {step_ps:g}p {stop_s:.14g} 0 {step_ps:g}p uic", deck, count=1)
    require(count == 1, "Could not set both transient and maximum step")
    return deck


def row_tap_checks(raw: dict, case: dict, schedule: dict) -> tuple[list[dict], list[dict]]:
    time = raw["time"]
    vdd = float(schedule["vdd"])
    settle = float(case["settling_allowance_ns"]) * 1e-9
    checks: list[dict] = []
    measurements: list[dict] = []

    def check(phase: str, row: int, tap: int, metric: str, value: float,
              low: float | None = None, high: float | None = None) -> None:
        passed = math.isfinite(value) and (low is None or value >= low) and (high is None or value <= high)
        checks.append({"case": case["label"], "phase": phase, "row": row, "tap": tap,
                       "metric": metric, "value": value,
                       "low": "" if low is None else low,
                       "high": "" if high is None else high,
                       "result": "PASS" if passed else "FAIL"})

    phases = (("prime", int(case["old"]), float(schedule["first_rise"]),
               float(schedule["first_fall"] - schedule["fall"] / 2)),
              ("test", int(case["new"]), float(schedule["second_rise"]),
               float(schedule["second_fall"] - schedule["fall"] / 2)))
    for phase, selected_row, start, end in phases:
        for row in range(4):
            for tap in range(16):
                key = f"v(xrow{row}.wl.t{tap})"
                require(key in raw, f"Missing physical row waveform {key}")
                signal = raw[key]
                segment = (time >= start) & (time <= end)
                peak = float(signal[segment].max())
                minimum = float(signal[segment].min())
                if row == selected_row:
                    crossing = capture.crossing(time, signal, 0.9 * vdd, True, start, end)
                    delay_ps = math.nan if crossing is None else (crossing - start) * 1e12
                    settle_start = start + settle
                    settled = (time >= settle_start) & (time <= end)
                    settled_min = float(signal[settled].min()) if settled.any() else math.nan
                    check(phase, row, tap, "WL90_delay_ps", delay_ps, high=settle * 1e12)
                    check(phase, row, tap, "selected_settled_min_v", settled_min, low=0.9 * vdd)
                    check(phase, row, tap, "selected_peak_v", peak, high=1.1 * vdd)
                    measurements.append({"case": case["label"], "phase": phase,
                                         "row": row, "tap": tap,
                                         "wl90_delay_from_pclk_edge_ps": delay_ps,
                                         "minimum_v": minimum, "maximum_v": peak,
                                         "settled_min_v": settled_min})
                else:
                    check(phase, row, tap, "unselected_peak_v", peak, high=0.1 * vdd)
                    measurements.append({"case": case["label"], "phase": phase,
                                         "row": row, "tap": tap,
                                         "wl90_delay_from_pclk_edge_ps": "",
                                         "minimum_v": minimum, "maximum_v": peak,
                                         "settled_min_v": ""})

    recovery_start = float(schedule["second_fall"] + schedule["fall"] / 2 + settle)
    recovery_end = float(schedule["stop"])
    recovery = (time >= recovery_start) & (time <= recovery_end)
    require(recovery.any(), "The simulation does not include the requested WL recovery window")
    for row in range(4):
        for tap in range(16):
            signal = raw[f"v(xrow{row}.wl.t{tap})"]
            peak = float(signal[recovery].max())
            check("recovery", row, tap, "deasserted_peak_v", peak, high=0.1 * vdd)
    return checks, measurements


def suppress_evaluation_pclk(deck: str, schedule: dict) -> str:
    """Keep only the priming pulse; denied controls must leave PCLK precharging."""
    vdd = float(schedule["vdd"])
    rise, fall = float(schedule["rise"]), float(schedule["fall"])
    stop = float(schedule["stop"])
    pulse = contract.pwl(0.0, [
        (float(schedule["first_rise"]) - rise / 2,
         float(schedule["first_rise"]) + rise / 2, vdd),
        (float(schedule["first_fall"]) - fall / 2,
         float(schedule["first_fall"]) + fall / 2, 0.0),
    ], stop)
    deck, count = re.subn(r"(?im)^(VPCLK\s+\S+\s+\S+)\s+[^\n]+$",
                          lambda match: match.group(1) + " " + pulse, deck, count=1)
    require(count == 1, "Could not hold PCLK in precharge for a denied access vector")
    return deck


def access_suppression_checks(raw: dict, case: dict, schedule: dict,
                              nodes: dict, ports: dict) -> list[dict]:
    """Check that an ideal access qualifier suppresses all DEC/WL activity."""
    time = raw["time"]
    vdd = float(schedule["vdd"])
    start = float(schedule["second_rise"])
    end = float(schedule["second_fall"] - schedule["fall"] / 2)
    region = (time >= start) & (time <= end)
    require(region.any(), "Missing high-clock window for access suppression checks")
    checks = []

    def trace(name: str) -> np.ndarray:
        key = name.lower()
        if not key.startswith("v("):
            key = f"v({key})"
        require(key in raw, f"Missing waveform {key} for access suppression")
        return raw[key]

    def add(output: str, metric: str, value: float,
            low: float | None = None, high: float | None = None) -> None:
        passed = math.isfinite(value) and (low is None or value >= low) and (high is None or value <= high)
        checks.append({"case": case["label"], "phase": "denied_access_window",
                       "output": output, "metric": metric, "value": value,
                       "low": "" if low is None else low,
                       "high": "" if high is None else high,
                       "result": "PASS" if passed else "FAIL"})

    add("PCLK", "maximum_v", float(trace(ports["PCLK"])[region].max()), high=0.1 * vdd)
    for row in range(4):
        internal = trace(f"x1.n{row}")
        add(f"N{row}", "minimum_precharged_v", float(internal[region].min()), low=0.9 * vdd)
        for name in (f"DEC{row}", f"WL{row}"):
            signal = trace(nodes[name])
            add(name, "maximum_inactive_v", float(signal[region].max()), high=0.1 * vdd)
        for tap in range(16):
            signal = trace(f"xrow{row}.wl.t{tap}")
            add(f"ROW{row}.WL_TAP{tap}", "maximum_inactive_v",
                float(signal[region].max()), high=0.1 * vdd)
    return checks


def parse_transition(text: str) -> tuple[int, int]:
    match = re.fullmatch(r"([0-3]):([0-3])", text)
    if not match:
        raise argparse.ArgumentTypeError("use addresses from 0 to 3, e.g. 0:3 or 2:2")
    return int(match[1]), int(match[2])


def execute_case(case: dict, netlist: str, row_evidence: dict,
                 model: Path, arc: dict, step_ps: float, timeout_s: float,
                 out_dir: Path, keep_raw: bool) -> dict:
    deck, nodes, devices, terminals, schedule, sim_case = capture.make_deck(
        netlist, case, model, arc, case["dff_load_label"], 102.873935496)
    sim_case["step_ps"] = step_ps
    ports = capture.top_pin_map(netlist)
    deck, count = re.subn(r"(?im)^C_WL[0-3]\s+[^\n]+\n?", "", deck)
    require(count == 4, f"Expected four old lumped WL loads to remove, got {count}")
    deck = add_bitline_sources(deck, float(schedule["vdd"]), ports["VSS"])
    deck = set_transient_step(deck, step_ps, float(schedule["stop"]))
    save = ".save " + " ".join(
        f"v(xrow{row}.wl.t{tap})" for row in range(4) for tap in range(16)) + "\n"
    deck, count = re.subn(r"(?im)^(\.tran\s+)", lambda match: save + match.group(1), deck, count=1)
    require(count == 1, "Could not add all physical WL taps to the waveform save list")
    control_vector = case.get("control_vector")
    access_allowed = control_vector is None or control_vector in ACCESS_CONTROL
    if control_vector is not None and not access_allowed:
        deck = suppress_evaluation_pclk(deck, schedule)

    out_dir.mkdir(parents=True, exist_ok=True)
    deck_path = out_dir / "case.spice"
    log_path = out_dir / "ngspice.log"
    raw_path = out_dir / "waveform.raw"
    deck_path.write_text(deck, encoding="utf-8")
    started = datetime.now(timezone.utc).isoformat()
    try:
        proc = subprocess.run(["ngspice", "-n", "-b", str(deck_path)], cwd=out_dir,
                              capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired as exc:
        log_path.write_text((exc.stdout or "") + (exc.stderr or ""), encoding="utf-8")
        return {"case": case["label"], "status": "ERROR", "error": f"ngspice timeout after {timeout_s:g}s"}
    log = proc.stdout + proc.stderr
    log_path.write_text(log, encoding="utf-8")
    if proc.returncode or re.search(r"Error:|failed!|aborted|timestep too small", log, re.I) or not raw_path.is_file():
        return {"case": case["label"], "status": "ERROR", "ngspice_returncode": proc.returncode,
                "error": "ngspice failed or produced no complete waveform"}

    raw = capture.read_raw(raw_path)
    if control_vector is not None and not access_allowed:
        decoder_run = None
        decoder_checks = []
        terminals_rows = []
        row_checks = access_suppression_checks(raw, case, schedule, nodes, ports)
        taps = []
        timing = {}
    else:
        decoder_run, decoder_checks, terminals_rows = capture.contract.analyze(
            raw, sim_case, nodes, devices, terminals, schedule)
        row_checks, taps = row_tap_checks(raw, case, schedule)
        timing = capture.edge_metrics(raw, case, nodes, terminals,
                                      capture.top_pin_map(netlist), arc,
                                      float(schedule["vdd"]),
                                      capture.CAPTURE_LITERAL_NODES or None)
    all_checks = decoder_checks + row_checks
    failed_checks = sum(row["result"] != "PASS" for row in all_checks)
    row_delays = [float(row["wl90_delay_from_pclk_edge_ps"])
                  for row in taps if row["phase"] == "test"
                  and row["row"] == int(case["new"])
                  and row["wl90_delay_from_pclk_edge_ps"] != ""]
    result = {
        "case": case["label"], "profile": case["profile"],
        "old_address": case["old"], "new_address": case["new"],
        "selected_physical_row": case["new"],
        "control_vector_csb_oeb_web": control_vector or "not_modeled",
        "control_operation": (ACCESS_CONTROL.get(control_vector, "denied")
                              if control_vector is not None else "independent_ideal_pclk"),
        "access_allowed_by_spec": access_allowed if control_vector is not None else "not_modeled",
        "row_pex_sha256": row_evidence["sha256"],
        "simulation_step_ps": step_ps,
        "bitline_assumption": row_evidence["bitline_mode"],
        **timing,
        "decoder_logic_pass": None if decoder_run is None else decoder_run["check_fail"] == 0,
        "decoder_voltage_screens_pass": (None if decoder_run is None else
                                          decoder_run["model_upper_result"] == "PASS"
                                          and decoder_run["magnitude_result"] == "PASS"),
        "decoder_checks_pass": 0 if decoder_run is None else decoder_run["check_pass"],
        "decoder_checks_fail": 0 if decoder_run is None else decoder_run["check_fail"],
        "access_control_checks_pass": sum(r["result"] == "PASS" for r in row_checks)
        if control_vector is not None and not access_allowed else 0,
        "access_control_checks_fail": sum(r["result"] != "PASS" for r in row_checks)
        if control_vector is not None and not access_allowed else 0,
        "row_tap_checks_pass": (0 if control_vector is not None and not access_allowed else
                                len(row_checks) - sum(r["result"] != "PASS" for r in row_checks)),
        "row_tap_checks_fail": (0 if control_vector is not None and not access_allowed else
                                sum(r["result"] != "PASS" for r in row_checks)),
        "selected_row_wl90_delay_min_ps": min(row_delays) if row_delays else "",
        "selected_row_wl90_delay_max_ps": max(row_delays) if row_delays else "",
        "unselected_row_peak_max_v": max((float(row["value"]) for row in row_checks
                                           if row["metric"] == "unselected_peak_v"), default=""),
        "recovery_tap_peak_max_v": max((float(row["value"]) for row in row_checks
                                         if row["metric"] == "deasserted_peak_v"), default=""),
        "terminal_magnitude_max_v": "" if decoder_run is None else decoder_run["terminal_magnitude_max_v"],
        "terminal_magnitude_device": "" if decoder_run is None else decoder_run["terminal_magnitude_device"],
        "screen_pass": failed_checks == 0,
        "status": "PASS" if failed_checks == 0 else "REJECTED_SCREEN",
        "ngspice_returncode": proc.returncode,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "checks": all_checks,
        "tap_measurements": taps,
        "terminals": terminals_rows,
    }
    if not keep_raw:
        raw_path.unlink(missing_ok=True)
    compact = {key: value for key, value in result.items()
               if key not in {"checks", "tap_measurements", "terminals"}}
    (out_dir / "case.json").write_text(json.dumps(compact, indent=2) + "\n", encoding="utf-8")
    write_union_csv(out_dir / "checks.csv", all_checks)
    if taps:
        screen.write_csv(out_dir / "row_taps.csv", taps)
    if terminals_rows:
        screen.write_csv(out_dir / "terminals.csv", terminals_rows)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--profiles", nargs="+", choices=tuple(capture.LIBRARIES), default=["tt"])
    parser.add_argument("--transitions", nargs="+", type=parse_transition, default=None,
                        metavar="OLD:NEW", help="include all 16 pairs (OLD may equal NEW) for full row coverage")
    parser.add_argument("--control-vectors", nargs="+", choices=CONTROL_VECTORS, default=None,
                        metavar="CSbOEbWEb",
                        help="also screen access policy; 001=read, 010=write, others must suppress PCLK")
    parser.add_argument("--loads", nargs="+", choices=tuple(capture.LIBERTY_LOADS_PF), default=["nominal"])
    parser.add_argument("--phase-ps", type=float, default=1950.0,
                        help="experimental capture-to-PCLK delay; not an approved interface limit")
    parser.add_argument("--clk-fall-ps", type=float, default=20700.0)
    parser.add_argument("--settling-allowance-ns", type=float, default=3.3,
                        help="experimental settling window; not a project specification")
    parser.add_argument("--step-ps", type=float, default=5.0,
                        help="maximum transient step for the large distributed PEX network")
    parser.add_argument("--timeout-s", type=float, default=180.0)
    parser.add_argument("--keep-raw", action="store_true")
    args = parser.parse_args()
    transitions = (args.transitions if args.transitions is not None
                   else [parse_transition(value) for value in DEFAULT_TRANSITIONS])
    control_vectors = args.control_vectors if args.control_vectors is not None else [None]
    output = args.output_dir.resolve()
    require(not output.exists(), "Choose a new output directory for this campaign")
    require(bool(transitions), "At least one address transition is required")
    require(len(set(transitions)) == len(transitions), "Duplicate address transitions")
    require(args.control_vectors is None or len(set(args.control_vectors)) == len(args.control_vectors),
            "Duplicate access-control vectors")
    require(math.isfinite(args.phase_ps) and args.phase_ps >= 0
            and args.phase_ps < args.clk_fall_ps - CAPTURE_NS * 1000,
            "Capture-to-PCLK delay must leave a positive CLK high phase")
    require(math.isfinite(args.settling_allowance_ns) and args.settling_allowance_ns > 0
            and args.settling_allowance_ns < (args.clk_fall_ps-CAPTURE_NS*1000-args.phase_ps)/1000,
            "Settling allowance must fit inside the PCLK evaluation phase")
    require(math.isfinite(args.step_ps) and args.step_ps > 0, "Step must be finite and positive")
    require(math.isfinite(args.timeout_s) and args.timeout_s > 0, "Timeout must be positive")
    output.mkdir(parents=True)

    pex_text = ROW_PEX.read_text(encoding="utf-8")
    row_pex_evidence = inspect_row_pex(pex_text)
    row_pex_evidence.update(path=str(ROW_PEX.relative_to(ROOT)),
                            source_branch="feat/sram-6t-cell",
                            source_commit="95c23c03ddc29f0d4bf40adf5fe7adb1b4af0a6a",
                            source_path="layout/row_8_wl/pex/row_8_wl_pex.spice")
    row_sidecar = json.loads(ROW_CEFF_SIDECAR.read_text(encoding="utf-8"))
    require(row_sidecar.get("row_pex_sha256", [None])[0] == row_pex_evidence["sha256"],
            "The row PEX does not match the PEX cited by the corrected Ceff input")
    pdk = Path(os.environ.get("PDK_ROOT", "/opt/pdks")) / "sky130A"
    model = pdk / "libs.tech/combined/continuous/sky130.lib.spice"
    lib_dir = pdk / "libs.ref/sky130_fd_sc_hd/lib"
    require(model.is_file(), f"SKY130 model file missing: {model}")
    libraries = {profile: lib_dir / capture.LIBRARIES[profile] for profile in args.profiles}
    require(all(path.is_file() for path in libraries.values()), "A requested Liberty file is missing")
    arcs = {profile: {load: capture.liberty_arc(path, capture.LIBERTY_LOADS_PF[load])
                      for load in args.loads}
            for profile, path in libraries.items()}

    with tempfile.TemporaryDirectory(prefix="decoder-distributed-row-netlist-") as temp:
        netlist = contract.netlist_current(Path(temp))
    netlist, pex_evidence = capture.inject_combined_pex(netlist)
    nodes, devices = screen.inspect_netlist(netlist, True)
    require(len(devices) == 29, "Distributed-row screen requires the current 29-MOS decoder")
    netlist, row_instance_evidence = attach_physical_rows(netlist, pex_text, nodes)
    netlist_sha = hashlib.sha256(netlist.encode()).hexdigest()
    cases = []
    for profile in args.profiles:
        lib = libraries[profile]
        libtext = lib.read_text(encoding="utf-8")
        lower = float(re.search(r"slew_lower_threshold_pct_rise\s*:\s*([\d.]+)", libtext)[1])
        upper = float(re.search(r"slew_upper_threshold_pct_rise\s*:\s*([\d.]+)", libtext)[1])
        for load in args.loads:
            for old, new in transitions:
                for vector in control_vectors:
                    suffix = "" if vector is None else f"_ctl{vector}"
                    case = {
                        "label": f"{profile}_{load}_row{new}_a{old}_to_{new}_p{args.phase_ps:g}ps{suffix}",
                        "profile": profile, "old": old, "new": new,
                        "capture_to_pclk_ps": args.phase_ps,
                        "dff_load_label": load,
                        "dff_load_pf": capture.LIBERTY_LOADS_PF[load],
                        "dff_liberty": arcs[profile][load]["library"],
                        "clk_fall_ps": args.clk_fall_ps,
                        "settling_allowance_ns": args.settling_allowance_ns,
                        "slew_lower_pct": lower, "slew_upper_pct": upper,
                    }
                    if vector is not None:
                        case.update(control_vector=vector,
                                    control_operation=ACCESS_CONTROL.get(vector, "denied"),
                                    access_allowed=vector in ACCESS_CONTROL)
                    cases.append(case)

    model_hashes = contract.model_dependencies(model)
    for path in libraries.values():
        model_hashes[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
    tools = {"xschem": screen.tool_version("xschem"), "ngspice": screen.tool_version("ngspice")}
    helper_hashes = {
        "script": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "capture_runner": hashlib.sha256(Path(capture.__file__).read_bytes()).hexdigest(),
        "decoder_contract": hashlib.sha256(Path(contract.__file__).read_bytes()).hexdigest(),
        "row_decoder_source": hashlib.sha256((ROOT / "cells/row_decoder/row_decoder.sch").read_bytes()).hexdigest(),
        "wl_driver_source": hashlib.sha256((ROOT / "cells/wordline_driver/wl_driver.sch").read_bytes()).hexdigest(),
        "row_pex": row_pex_evidence["sha256"],
        "row_pex_provenance": hashlib.sha256(
            ROW_PEX.with_suffix(".provenance.json").read_bytes()).hexdigest(),
        "row_ceff_provenance": hashlib.sha256(ROW_CEFF_SIDECAR.read_bytes()).hexdigest(),
    }
    environment_sha = hashlib.sha256(json.dumps(
        dict(models=model_hashes, tools=tools, helpers=helper_hashes), sort_keys=True).encode()).hexdigest()
    manifest = {
        "campaign": "row_decoder_distributed_physical_row_screen",
        "complete": False,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "current decoder and four WL-driver RC PEX plus four physical 8-bit row PEX instances",
        "candidate": "current B7 decoder, current WL-driver PEX and Danilo's extracted 8-bit row PEX",
        "evidence_scope": ("specified CSb/OEb/WEb truth-table screen plus selected physical WL assertion/deassertion; ideal access-qualified PCLK, no read/write bitline activity or sense qualification"
                           if args.control_vectors is not None else
                           "selected-row WL assertion/deassertion and one-hot taps; no bitline read/write or sense qualification"),
        "access_control_interface": ({
            "vectors_csb_oeb_web": args.control_vectors,
            "read_vector": "001", "write_vector": "010",
            "all_other_vectors": "PCLK held low through the high-clock window; check DEC, WL and all physical row taps inactive",
            "implementation_model": "Ideal testbench PCLK qualification based on each static truth-table vector; control capture and transistor-level controller/gate are not instantiated",
        } if args.control_vectors is not None else {
            "vectors_csb_oeb_web": None,
            "implementation_model": "PCLK is an independent ideal source; external access qualification is not screened",
        }),
        "timing_assumptions": {"address_capture_ns": CAPTURE_NS,
                               "capture_to_pclk_ps": args.phase_ps,
                               "clk_fall_ps": args.clk_fall_ps,
                               "settling_allowance_ns": args.settling_allowance_ns,
                               "experimental_not_specification": True},
        "row_pex": row_instance_evidence,
        "selected_row_coverage": sorted({new for _, new in transitions}),
        "row_ceff_reference": {"provenance_sidecar": str(ROW_CEFF_SIDECAR.relative_to(ROOT)),
                                "provenance_sha256": hashlib.sha256(ROW_CEFF_SIDECAR.read_bytes()).hexdigest(),
                                "full_row_max_fF": row_sidecar.get("cwl_pex_ff_range", [None, None])[1],
                                "paired_extra_max_fF": row_sidecar.get("paired_extra_cwl_ff_max")},
        "decoder_wl_pex_sources": pex_evidence,
        "bitline_model": "One ideal VDD source per shared BL/BLB line holds precharge continuously; no precharge MOS, sense amplifier, write driver or explicit access-enable logic is instantiated.",
        "known_owner_report_difference": "The detailed bitcell report body cites 98.914001 fF for row Ceff, while the latch-t0 table used by this project records up to 102.873935496 fF with the same row PEX SHA. This test instantiates row PEX directly and does not replace either source result.",
        "model_domain_scope": "Decoder and WL-driver terminal screens are included; bitcell row device terminal biases are not qualified by this runner.",
        "netlist_sha256": netlist_sha,
        "helper_sha256": helper_hashes,
        "model_dependencies_sha256": model_hashes,
        "environment_sha256": environment_sha,
        "tools": tools,
        "max_step_ps": args.step_ps,
        "timeout_s_per_case": args.timeout_s,
        "workers": 1,
        "cases": cases,
    }
    (output / "executed_script.py").write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8")
    (output / "simulation_input_netlist.spice").write_text(netlist, encoding="utf-8")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    results = []
    errors = []
    all_checks = []
    all_taps = []
    all_terminals = []
    for index, case in enumerate(cases, start=1):
        case_dir = output / "cases" / case["label"]
        try:
            result = execute_case(case, netlist, row_instance_evidence,
                                  model, arcs[case["profile"]][case["dff_load_label"]],
                                  args.step_ps, args.timeout_s, case_dir, args.keep_raw)
        except Exception as exc:
            errors.append({"case": case["label"], "error": f"{type(exc).__name__}: {exc}"})
            print(json.dumps(errors[-1]), flush=True)
            continue
        results.append(result)
        if result.get("status") == "ERROR":
            errors.append({"case": case["label"], "error": result.get("error", "ngspice error")})
        all_checks.extend(result.pop("checks", []))
        all_taps.extend(result.pop("tap_measurements", []))
        all_terminals.extend(result.pop("terminals", []))
        print(f"distributed row: {index}/{len(cases)} {case['label']} {result['status']}", flush=True)

    if results:
        screen.write_csv(output / "summary.csv", results)
        write_union_csv(output / "checks.csv", all_checks)
        if all_taps:
            screen.write_csv(output / "row_taps.csv", all_taps)
        if all_terminals:
            screen.write_csv(output / "terminals.csv", all_terminals)
    complete = not errors and len(results) == len(cases)
    manifest.update(complete=complete, completed_cases=len(results), errors=errors,
                    pass_cases=sum(row.get("status") == "PASS" for row in results),
                    rejected_screen_cases=sum(row.get("status") == "REJECTED_SCREEN" for row in results),
                    finished_utc=datetime.now(timezone.utc).isoformat())
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
