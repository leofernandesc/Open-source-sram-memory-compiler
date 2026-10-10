#!/usr/bin/env python3
"""Compare the transistor-level captured row-control path with a Liberty-Q reference.

Both cases use the checked-in transistor-level PCLK/PRECH source, current
decoder/WL-driver PEX, and the pinned Danilo precharge PEX. The captured case
instantiates the Xschem row-address register, access qualifier, and phase
source. The reference drives the decoder address and phase source with Q PWLs
derived from the dfxtp_1 Liberty arcs.
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

import run_precharge_phase_interface as phase
import run_row_decoder_capture_timing as capture

PDK_ROOT = Path(os.environ.get("PDK_ROOT", "/opt/pdks")) / "sky130A"
NATIVE_MODEL = PDK_ROOT / "libs.tech/ngspice/sky130.lib.spice"
SC_LIBRARY = PDK_ROOT / "libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice"
LIBERTY_DIR = PDK_ROOT / "libs.ref/sky130_fd_sc_hd/lib"
CONTROL_DIR = ROOT / "cells/control"
CAPTURED_SCHEMATIC = CONTROL_DIR / "captured_row_decoder_control.sch"
CAPTURED_SYMBOL = CONTROL_DIR / "captured_row_decoder_control.sym"
ADDRESS_CAPTURE_SCHEMATIC = CONTROL_DIR / "row_address_capture.sch"
ADDRESS_CAPTURE_SYMBOL = CONTROL_DIR / "row_address_capture.sym"
CAPTURE_SCHEMATIC = CONTROL_DIR / "valid_access_capture.sch"
PHASE_SCHEMATIC = CONTROL_DIR / "pclk_phase_source.sch"
PHASE_SYMBOL = CONTROL_DIR / "pclk_phase_source.sym"
ADDRESS_SETUP_LEAD_PS = 500.0
PRECHARGE_PEX = ROOT / "sims/row_decoder/inputs/precharge_w2p52_pex_5dc00fe.spice"
PRECHARGE_PROVENANCE = PRECHARGE_PEX.with_suffix(".provenance.json")
PRECHARGE_SHA256 = "cf0fa457b4ab84a1d19e6202541b6a43149b575e492a108e36d0de62489cc423"

MODEL_CORNERS = {"tt": "tt", "slow": "ss", "fast": "ff"}
ALL_CONTROL_VECTORS = ("000", "001", "010", "011", "100", "101", "110", "111")
VALID_VECTORS = phase.VALID_VECTORS
CAPTURE_NS = 15.0
ADDRESS_HOLD_CHALLENGE_NS = CAPTURE_NS + 0.8
PRIME_RISE_NS = 5.0
PRIME_FALL_NS = 10.0
CONTROL_EDGE_SLEW_PS = 50.0
CONTROL_UPDATE_AFTER_EDGE_NS = 0.8
Q_CAPTURE_SAMPLE_PS = 700.0
Q_HIGH_HOLD_SAMPLE_PS = 1500.0
Q_FALL_HOLD_SAMPLE_NS = 1.0
Q_LIBERTY_LOAD_PF = capture.LIBERTY_LOADS_PF["nominal"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_text(path: Path, content: str) -> None:
    path.write_text("\n".join(line.rstrip() for line in content.splitlines()).rstrip()
                    + "\n", encoding="utf-8")


def vector_value(vector: str) -> int:
    csb, oeb, web = (int(bit) for bit in vector)
    return int((not csb) and (oeb ^ web))


def decode_vector(vector: str) -> tuple[int, int, int]:
    require(re.fullmatch(r"[01]{3}", vector) is not None,
            f"Invalid CSb/OEb/WEb vector: {vector}")
    return tuple(int(bit) for bit in vector)


def opposite_capture_vector(vector: str) -> str:
    """Choose the opposite validity class for the post-edge hold challenge."""
    return "000" if vector in VALID_VECTORS else "001"


def make_clock_waveform(vdd: float, fall_ns: float, stop_s: float) -> str:
    ramp = CONTROL_EDGE_SLEW_PS * 1e-12
    events = [
        (PRIME_RISE_NS*1e-9-ramp/2, PRIME_RISE_NS*1e-9+ramp/2, vdd),
        (PRIME_FALL_NS*1e-9-ramp/2, PRIME_FALL_NS*1e-9+ramp/2, 0.0),
        (CAPTURE_NS*1e-9-ramp/2, CAPTURE_NS*1e-9+ramp/2, vdd),
        (fall_ns*1e-9-ramp/2, fall_ns*1e-9+ramp/2, 0.0),
    ]
    return phase.contract.pwl(0.0, events, stop_s)


def make_control_waveform(index: int, vector: str, vdd: float,
                          stop_s: float) -> str:
    target = decode_vector(vector)
    after = decode_vector(opposite_capture_vector(vector))
    ramp = CONTROL_EDGE_SLEW_PS * 1e-12
    centers = ((PRIME_RISE_NS + CONTROL_UPDATE_AFTER_EDGE_NS)*1e-9,
               (CAPTURE_NS + CONTROL_UPDATE_AFTER_EDGE_NS)*1e-9)
    initial = vdd
    events = []
    for center, bits in zip(centers, (target, after)):
        value = bits[index] * vdd
        events.append((center-ramp/2, center+ramp/2, value))
    return phase.contract.pwl(initial, events, stop_s)


def make_address_input_waveform(index: int, old: int, new: int, vdd: float,
                                stop_s: float) -> str:
    old_bit = (old >> index) & 1
    new_bit = (new >> index) & 1
    ramp = CONTROL_EDGE_SLEW_PS * 1e-12
    target_center = CAPTURE_NS * 1e-9 - ADDRESS_SETUP_LEAD_PS * 1e-12
    live_change_center = ADDRESS_HOLD_CHALLENGE_NS * 1e-9
    events = [
        (target_center-ramp/2, target_center+ramp/2, new_bit*vdd),
        (live_change_center-ramp/2, live_change_center+ramp/2, (1-new_bit)*vdd),
    ]
    return phase.contract.pwl(old_bit*vdd, events, stop_s)


def netlist_captured_wrapper(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    command = [
        "xschem", "--tcl", f"append XSCHEM_LIBRARY_PATH :{CONTROL_DIR}",
        "-n", "-q", "-o", str(output), str(CAPTURED_SCHEMATIC),
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=120)
    log = result.stdout
    write_text(output / "xschem.log", log)
    raw_path = output / "captured_row_decoder_control.spice"
    require(result.returncode == 0 and raw_path.is_file(),
            f"Xschem could not netlist the captured row-control wrapper; see {output/'xschem.log'}")
    require(not re.search(r"missing symbol|symbol not found|unresolved symbol|Error:",
                          log, re.I),
            f"Xschem reported a netlist problem; see {output/'xschem.log'}")
    raw = raw_path.read_text(encoding="utf-8")
    lines = []
    found_top = False
    found_end = False
    for line in raw.splitlines():
        if line.startswith("**.subckt captured_row_decoder_control "):
            line = line[2:]
            found_top = True
        elif found_top and not found_end and line.strip() == "**.ends":
            line = ".ends captured_row_decoder_control"
            found_end = True
        elif line.strip().lower() == ".end":
            continue
        lines.append(line)
    active = "\n".join(lines).rstrip() + "\n"
    expected = (
        ".subckt captured_row_decoder_control CLK A0 A1 CSb OEb WEb VDD VSS A0_Q A1_Q VALID_ACCESS_Q PCLK PRECH",
        "XADDR CLK A0 A1 VDD VSS A0_Q A1_Q row_address_capture",
        "XPHASE CLK CSb OEb WEb VDD VSS VALID_ACCESS_Q PCLK PRECH captured_pclk_phase_source",
        "XA0_FF CLK A0 VSS VSS VDD VDD A0_Q sky130_fd_sc_hd__dfxtp_1",
        "XA1_FF CLK A1 VSS VSS VDD VDD A1_Q sky130_fd_sc_hd__dfxtp_1",
        "XACCESS CLK CSb OEb WEb VDD VSS VALID_ACCESS_Q valid_access_capture",
        ".subckt valid_access_capture CLK CSb OEb WEb VDD VSS VALID_ACCESS_Q",
        ".subckt pclk_phase_source VDD CLK VSS VALID_ACCESS_Q PCLK PRECH",
    )
    require(found_top and found_end and all(item in active for item in expected),
            "Fresh wrapper netlist failed the captured-address/control/phase hierarchy audit")
    wrapper_path = output / "captured_row_decoder_control_active.spice"
    write_text(wrapper_path, active)
    return {
        "raw_netlist": raw,
        "active_netlist": active,
        "raw_path": raw_path,
        "active_path": wrapper_path,
        "command": command,
        "sha256": sha256(raw_path),
        "active_sha256": sha256(wrapper_path),
    }


def replace_native_model(deck: str, profile: str) -> str:
    pattern = r'(?im)^\.lib\s+"?[^"\s]+"?\s+\S+\s*$'
    replacement = f'.lib "{NATIVE_MODEL}" {MODEL_CORNERS[profile]}'
    deck, count = re.subn(pattern, replacement, deck, count=1)
    require(count == 1, "Could not select the native SKY130 PM3 model corner")
    require(str(NATIVE_MODEL) in deck, "Native SKY130 model library was not inserted")
    return deck


def add_xschem_path(deck: str, netlist: dict, case: dict, mode: str,
                    arc: dict, schedule: dict, ports: dict, nodes: dict) -> str:
    vdd = float(schedule["vdd"])
    vss = ports["VSS"]
    fall_ns = float(case["clk_fall_ps"]) / 1000.0
    stop_s = float(schedule["stop"])
    ramp = CONTROL_EDGE_SLEW_PS*1e-12
    clock_waveform = make_clock_waveform(vdd, fall_ns, stop_s)
    sources = [f"VPHASE_CLK PHASE_CLK {vss} {clock_waveform}"]
    for index, name in enumerate(("CSb", "OEb", "WEb")):
        waveform = make_control_waveform(index, case["control_vector"], vdd, stop_s)
        sources.append(f"V{name}_IN {name} {vss} {waveform}")

    if mode == "actual":
        for source in ("VA0", "VA1"):
            deck, count = re.subn(rf"(?im)^{source}\s+[^\n]*\n", "", deck, count=1)
            require(count == 1, f"Could not replace ideal {source} address source")
        save_match = re.search(r"(?im)^\.save\s+([^\n]+)$", deck)
        require(save_match is not None, "Base deck has no waveform .save line")
        save_tokens = [token for token in save_match[1].split()
                       if token.lower() not in {"i(va0)", "i(va1)"}]
        save_tokens.extend(("v(A0_IN)", "v(A1_IN)",
                            "i(VA0_IN)", "i(VA1_IN)"))
        deck = (deck[:save_match.start()] + ".save " + " ".join(save_tokens)
                + deck[save_match.end():])
        for index, (source, node) in enumerate((("VA0_IN", "A0_IN"),
                                                 ("VA1_IN", "A1_IN"))):
            waveform = make_address_input_waveform(
                index, int(case["old"]), int(case["new"]), vdd, stop_s)
            sources.append(f"{source} {node} {vss} {waveform}")
        instance = (
            f"XCAPTURED PHASE_CLK A0_IN A1_IN CSb OEb WEb {ports['VDD']} {vss} "
            f"{ports['A0']} {ports['A1']} VALID_ACCESS_Q PHASE_PCLK PRECH "
            "captured_row_decoder_control"
        )
    else:
        expected = vector_value(case["control_vector"])
        q_waveform = capture.q_waveform(
            0, expected, vdd, CAPTURE_NS*1e-9,
            arc["clock_to_q_rise_ns"] if expected else 0.0,
            arc["q_rise_transition_ns"] if expected else 0.0,
            float(case["slew_lower_pct"]), float(case["slew_upper_pct"]), stop_s)
        sources.append(f"VVALID_ACCESS_Q VALID_ACCESS_Q {vss} {q_waveform}")
        instance = (
            f"XPHASE {ports['VDD']} PHASE_CLK {vss} VALID_ACCESS_Q "
            "PHASE_PCLK PRECH pclk_phase_source"
        )
    lines = sources + [
        instance,
        f"VPCLK {nodes['PCLK']} PHASE_PCLK 0",
    ]
    # Keep the actual address/control/phase hierarchy attached to the same
    # device model and PEX network as the existing decoder interface bench.
    deck, count = re.subn(r"(?im)^VPCLK\s+\S+\s+\S+\s+[^\n]+\n", "", deck, count=1)
    require(count == 1, "Could not replace the ideal PCLK source")
    deck = replace_native_model(deck, case["profile"])
    lib_match = re.search(r"(?im)^\.lib\s+", deck)
    require(lib_match is not None, "Native model selector disappeared from deck")
    deck = deck[:lib_match.start()] + "\n".join(lines) + "\n" + deck[lib_match.start():]
    deck = deck.replace(f'.lib "{NATIVE_MODEL}" {MODEL_CORNERS[case["profile"]]}',
                        f'.include "{SC_LIBRARY}"\n.lib "{NATIVE_MODEL}" '
                        f'{MODEL_CORNERS[case["profile"]]}', 1)
    end_match = re.search(r"(?im)^\.end\s*$", deck)
    require(end_match is not None, "SPICE deck is missing its final .end")
    active_netlist = netlist["active_netlist"]
    deck = deck[:end_match.start()] + active_netlist + "\n" + deck[end_match.start():]
    deck, count = re.subn(
        r"(?im)^(\.save\s+[^\n]+)$",
        r"\1 v(PHASE_CLK) v(CSb) v(OEb) v(WEb) v(VALID_ACCESS_Q) v(PHASE_PCLK)",
        deck, count=1)
    require(count == 1, "Could not add captured-phase waveform probes")
    return deck


def logic_level(value: float, vdd: float) -> int | None:
    if value >= 0.9*vdd:
        return 1
    if value <= 0.1*vdd:
        return 0
    return None


def q_checks(raw: dict[str, np.ndarray], case: dict, schedule: dict,
             vdd: float) -> tuple[list[dict], dict]:
    time = raw["time"]
    q = phase.trace(raw, "VALID_ACCESS_Q")
    expected = vector_value(case["control_vector"])
    capture_edge = phase.crossing(time, phase.trace(raw, "CAPCLK"), 0.5*vdd,
                                  True, (CAPTURE_NS-0.2)*1e-9,
                                  (CAPTURE_NS+0.2)*1e-9)
    require(capture_edge is not None, f"Missing address/control capture marker in {case['label']}")
    fall_edge = phase.crossing(time, phase.trace(raw, "PHASE_CLK"), 0.5*vdd,
                               False, float(schedule["second_fall"])-0.2e-9,
                               float(schedule["second_fall"])+0.5e-9)
    require(fall_edge is not None, f"Missing phase-clock falling edge in {case['label']}")
    sample_points = {
        "capture": capture_edge + Q_CAPTURE_SAMPLE_PS*1e-12,
        "hold_after_live_controls_change": capture_edge + Q_HIGH_HOLD_SAMPLE_PS*1e-12,
        "hold_after_falling_edge": fall_edge + Q_FALL_HOLD_SAMPLE_NS*1e-9,
    }
    values = {label: float(np.interp(point, time, q))
              for label, point in sample_points.items()}
    checks = []
    for label, value in values.items():
        result = logic_level(value, vdd)
        checks.append({
            "case": case["label"], "mode": case["mode"],
            "control_vector": case["control_vector"],
            "check": f"VALID_ACCESS_Q_{label}", "value": value,
            "expected": expected, "result": "PASS" if result == expected else "FAIL",
        })
    q_rise = (phase.crossing(time, q, 0.5*vdd, True,
                             capture_edge-0.1e-9, capture_edge+2e-9)
              if expected else None)
    q_fall = (phase.crossing(time, q, 0.5*vdd, False,
                             capture_edge-0.1e-9, capture_edge+2e-9)
              if not expected else None)
    metrics = {
        "capture_edge_ns": capture_edge*1e9,
        "q_rise_ns": None if q_rise is None else q_rise*1e9,
        "q_fall_ns": None if q_fall is None else q_fall*1e9,
        "capture_to_q_rise_ps": None if q_rise is None else (q_rise-capture_edge)*1e12,
        "capture_to_q_fall_ps": None if q_fall is None else (q_fall-capture_edge)*1e12,
        "q_capture_v": values["capture"],
        "q_high_hold_v": values["hold_after_live_controls_change"],
        "q_falling_hold_v": values["hold_after_falling_edge"],
        "q_min_v": float(np.min(q)), "q_max_v": float(np.max(q)),
        "peak_below_vss_v": max(0.0, -float(np.min(q))),
        "peak_above_vdd_v": max(0.0, float(np.max(q))-vdd),
    }
    return checks, metrics


def address_checks(raw: dict[str, np.ndarray], case: dict, schedule: dict,
                   ports: dict, vdd: float) -> tuple[list[dict], dict]:
    time = raw["time"]
    capture_edge = phase.crossing(time, phase.trace(raw, "CAPCLK"), 0.5*vdd,
                                  True, (CAPTURE_NS-0.2)*1e-9,
                                  (CAPTURE_NS+0.2)*1e-9)
    require(capture_edge is not None,
            f"Missing row-address capture edge in {case['label']}")
    target = int(case["new"])
    samples = {
        "post_capture": capture_edge + Q_CAPTURE_SAMPLE_PS*1e-12,
        "after_live_address_change": capture_edge + Q_HIGH_HOLD_SAMPLE_PS*1e-12,
    }
    checks = []
    metrics = {}
    for bit, pin in enumerate(("A0", "A1")):
        signal = phase.trace(raw, ports[pin])
        expected = (target >> bit) & 1
        for label, sample_time in samples.items():
            value = float(np.interp(sample_time, time, signal))
            result = logic_level(value, vdd)
            checks.append({
                "case": case["label"], "mode": case["mode"],
                "control_vector": case["control_vector"],
                "check": f"{pin}_Q_{label}", "value": value,
                "expected": expected, "result": "PASS" if result == expected else "FAIL",
            })
            metrics[f"{pin.lower()}_q_{label}_v"] = value
    return checks, metrics


def measured_phase(raw: dict[str, np.ndarray], case: dict, nodes: dict,
                   schedule: dict, vdd: float) -> tuple[dict, dict]:
    time = raw["time"]
    pclk = phase.trace(raw, nodes["PCLK"])
    prech = phase.trace(raw, "PRECH")
    capture_edge = phase.crossing(time, phase.trace(raw, "CAPCLK"), 0.5*vdd,
                                  True, (CAPTURE_NS-0.2)*1e-9,
                                  (CAPTURE_NS+0.2)*1e-9)
    require(capture_edge is not None, f"Missing capture clock edge in {case['label']}")
    q = phase.trace(raw, "VALID_ACCESS_Q")
    expected = vector_value(case["control_vector"])
    q_rise = (phase.crossing(time, q, 0.5*vdd, True,
                             capture_edge-0.1e-9, capture_edge+2e-9)
              if expected else None)
    q_fall = (phase.crossing(time, q, 0.5*vdd, False,
                             capture_edge-0.1e-9, capture_edge+2e-9)
              if not expected else None)
    if expected:
        pclk_rise = phase.crossing(time, pclk, 0.5*vdd, True,
                                    14.8e-9, float(schedule["second_fall"])-0.1e-9)
        pclk_fall = phase.crossing(time, pclk, 0.5*vdd, False,
                                   float(schedule["second_fall"])-0.1e-9,
                                   float(schedule["second_fall"])+1e-9)
        pclk_rise_10 = phase.crossing(time, pclk, 0.1*vdd, True,
                                      14.8e-9, float(schedule["second_fall"])-0.1e-9)
        pclk_rise_90 = phase.crossing(time, pclk, 0.9*vdd, True,
                                      14.8e-9, float(schedule["second_fall"])-0.1e-9)
        pclk_fall_90 = phase.crossing(time, pclk, 0.9*vdd, False,
                                      float(schedule["second_fall"])-0.1e-9,
                                      float(schedule["second_fall"])+1e-9)
        pclk_fall_10 = phase.crossing(time, pclk, 0.1*vdd, False,
                                      float(schedule["second_fall"])-0.1e-9,
                                      float(schedule["second_fall"])+1e-9)
        pre_release = phase.crossing(time, prech, 0.75*vdd, True,
                                     14.8e-9, float(schedule["second_fall"]))
        pre_assert = phase.crossing(time, prech, 0.75*vdd, False,
                                    float(schedule["second_fall"]),
                                    float(schedule["stop"]))
        require(all(value is not None for value in
                    (q_rise, pclk_rise, pclk_fall, pclk_rise_10, pclk_rise_90,
                     pclk_fall_90, pclk_fall_10, pre_release, pre_assert)),
                f"Missing captured Q/PCLK/PRECH crossing for {case['label']}")
        rise_slew = abs(pclk_rise_90-pclk_rise_10)
        fall_slew = abs(pclk_fall_10-pclk_fall_90)
        # The decoder contract samples just before actual evaluation, not at
        # the requested nominal phase reference. Preserve the measured PCLK
        # edge and slew for its dynamic-node recovery/evaluation windows.
        schedule.update({"second_rise": pclk_rise, "second_fall": pclk_fall,
                         "rise": rise_slew, "fall": fall_slew})
        phase_info = {
            "first_release_center_s": None,
            "first_reassert_center_s": None,
            "second_release_center_s": pre_release,
            "second_reassert_center_s": pre_assert,
            "release_lead_ps": None,
            "turnoff_guard_ps": None,
        }
        metrics = {
            "capture_to_q_rise_ps": (q_rise-capture_edge)*1e12,
            "capture_to_pclk_rise_ps": (pclk_rise-capture_edge)*1e12,
            "capture_to_prech_release_ps": (pre_release-capture_edge)*1e12,
            "prech_release_lead_before_pclk_ps": (pclk_rise-pre_release)*1e12,
            "pclk_fall_after_clock_fall_ps":
                (pclk_fall-float(schedule["second_fall"]))*1e12,
            "pclk_fall_to_precharge_conduction_ps": (pre_assert-pclk_fall)*1e12,
            "pclk_rise_ns": pclk_rise*1e9,
            "pclk_fall_ns": pclk_fall*1e9,
            "pclk_rise_slew_ps": rise_slew*1e12,
            "pclk_fall_slew_ps": fall_slew*1e12,
            "prech_release_ns": pre_release*1e9,
            "prech_assert_ns": pre_assert*1e9,
        }
    else:
        pclk_region = pclk[(time >= CAPTURE_NS*1e-9) & (time <= float(schedule["stop"]))]
        prech_region = prech[(time >= CAPTURE_NS*1e-9) & (time <= float(schedule["stop"]))]
        phase_info = {
            "first_release_center_s": None,
            "first_reassert_center_s": None,
            "second_release_center_s": None,
            "second_reassert_center_s": None,
            "release_lead_ps": None,
            "turnoff_guard_ps": None,
        }
        metrics = {
            "capture_to_q_fall_ps": None if q_fall is None else (q_fall-capture_edge)*1e12,
            "pclk_peak_v": float(np.max(pclk_region)),
            "prech_max_v": float(np.max(prech_region)),
        }
    return phase_info, metrics


def run_simulation(deck: str, case_dir: Path, case: dict, mode: str,
                   model_hash: str) -> dict:
    case_dir.mkdir(parents=True, exist_ok=True)
    deck_path = case_dir / "case.spice"
    raw_path = case_dir / "waveform.raw"
    log_path = case_dir / "ngspice.log"
    write_text(deck_path, deck)
    try:
        proc = subprocess.run(["ngspice", "-n", "-b", str(deck_path)],
                              cwd=case_dir, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=180)
    except subprocess.TimeoutExpired as exc:
        write_text(log_path, (exc.stdout or "") + (exc.stderr or ""))
        return {"mode": mode, "status": "ERROR", "error": "ngspice timeout"}
    write_text(log_path, proc.stdout)
    fatal = ("could not find a valid modelname", "fatal error in ngspice",
             "simulation interrupted due to error", "error on line",
             "timestep too small", "simulation aborted")
    if proc.returncode or any(token in proc.stdout.lower() for token in fatal) or not raw_path.is_file():
        return {"mode": mode, "status": "ERROR", "ngspice_returncode": proc.returncode,
                "error": "ngspice failed or produced no transient waveform"}
    raw = phase.capture.read_raw(raw_path)
    return {"mode": mode, "status": "SIMULATED", "raw_path": raw_path,
            "raw": raw, "log_path": log_path, "model_hash": model_hash,
            "ngspice_returncode": proc.returncode}


def save_representative_csv(path: Path, raw: dict[str, np.ndarray],
                            pclk_node: str) -> None:
    time = raw["time"]
    mask = (time >= 14.5e-9) & (time <= 27e-9)
    indices = np.flatnonzero(mask)[::5]
    if len(indices) == 0 or indices[-1] != np.flatnonzero(mask)[-1]:
        indices = np.append(indices, np.flatnonzero(mask)[-1])
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("time_ns", "valid_access_q_v", "pclk_v", "prech_v", "clk_v"))
        q = phase.trace(raw, "VALID_ACCESS_Q")
        pclk = phase.trace(raw, pclk_node)
        prech = phase.trace(raw, "PRECH")
        clk = phase.trace(raw, "PHASE_CLK")
        for index in indices:
            writer.writerow((f"{time[index]*1e9:.9f}", f"{q[index]:.9g}",
                             f"{pclk[index]:.9g}", f"{prech[index]:.9g}",
                             f"{clk[index]:.9g}"))


def plot_representative(actual_csv: Path, liberty_csv: Path, output: Path,
                        vdd: float, profile: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    traces = {}
    for label, path in (("transistor-level capture", actual_csv),
                        ("Liberty-timed Q reference", liberty_csv)):
        with path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        traces[label] = {key: [float(row[key]) for row in rows]
                         for key in rows[0]}
    fig, axes = plt.subplots(3, 1, figsize=(10, 7.0), sharex=True,
                             layout="constrained")
    signals = (("valid_access_q_v", "VALID_ACCESS_Q"),
               ("pclk_v", "PCLK at decoder input"),
               ("prech_v", "PRECH (active low)"))
    colors = ("#1765a3", "#c15b23")
    for ax, (key, title) in zip(axes, signals):
        for (label, data), color in zip(traces.items(), colors):
            ax.plot(data["time_ns"], data[key], color=color, linewidth=1.4,
                    label=label)
        if key == "valid_access_q_v":
            ax.axhline(0.9*vdd, color="#58936c", linestyle="--", linewidth=0.8)
            ax.axhline(0.1*vdd, color="#a85b48", linestyle="--", linewidth=0.8)
        ax.set_ylabel("V")
        ax.set_title(title, loc="left", fontsize=10)
        ax.grid(axis="y", color="#dddddd", linewidth=0.6)
        ax.legend(loc="best", fontsize=8)
    axes[-1].set_xlim(14.5, 27)
    axes[-1].set_xlabel("Time (ns); capture at 15 ns, phase clock falls at 22 ns")
    fig.suptitle(f"Captured-control phase path · {profile.upper()} · matched PEX load")
    fig.savefig(output, dpi=180, facecolor="white")
    plt.close(fig)


def threshold_pct(path: Path, key: str) -> float:
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"{re.escape(key)}\s*:\s*([\d.]+)", text)
    require(match is not None, f"Missing {key} in {path.name}")
    return float(match[1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New result directory; must not already exist")
    parser.add_argument("--profiles", nargs="+", choices=("tt", "slow", "fast"),
                        default=["tt"],
                        help="Default is one TT screen; request additional corners explicitly")
    parser.add_argument("--control-vectors", nargs="+", choices=ALL_CONTROL_VECTORS,
                        default=["001"],
                        help="Default is representative valid-read vector 001")
    parser.add_argument("--transitions", nargs="+", default=["0:3"],
                        metavar="OLD:NEW")
    parser.add_argument("--transitions-per-vector", action="store_true")
    parser.add_argument("--phase-ps", type=float, default=2100.0,
                        help="Nominal input reference only; the generated PCLK edge is measured")
    parser.add_argument("--clk-fall-ps", type=float, default=22000.0)
    parser.add_argument("--settling-allowance-ns", type=float, default=3.4)
    parser.add_argument("--release-lead-ps", type=float, default=250.0,
                        help="Experimental minimum PRECH release lead screen")
    parser.add_argument("--turnoff-guard-ps", type=float, default=1800.0,
                        help="Experimental minimum wordline turn-off guard")
    parser.add_argument("--wl-cap-ff", type=float, default=102.873935496)
    parser.add_argument("--step-ps", type=float, default=5.0)
    parser.add_argument("--keep-raw", action="store_true")
    args = parser.parse_args()

    output = (ROOT / args.output_dir).resolve()
    require(not output.exists(), f"Choose a new output directory: {output}")
    require(output.is_relative_to(ROOT), "Output directory must remain inside the repository")
    require(set(args.profiles) and len(set(args.profiles)) == len(args.profiles),
            "Profile list must be unique and nonempty")
    require(len(set(args.control_vectors)) == len(args.control_vectors),
            "Control-vector list must be unique")
    require(math.isfinite(args.phase_ps) and args.phase_ps >= 0,
            "phase reference must be finite and nonnegative")
    require(math.isfinite(args.clk_fall_ps) and args.clk_fall_ps > 15000+args.phase_ps,
            "clock fall must leave a positive evaluation interval")
    require(math.isfinite(args.settling_allowance_ns) and args.settling_allowance_ns > 0
            and args.settling_allowance_ns < (args.clk_fall_ps-15000-args.phase_ps)/1000,
            "settling window must fit inside the high phase")
    require(math.isfinite(args.step_ps) and args.step_ps > 0,
            "transient maximum step must be positive")
    require(NATIVE_MODEL.is_file() and SC_LIBRARY.is_file(),
            "Native SKY130 PM3 model library or standard-cell SPICE file is missing")
    require(all(path.is_file() for path in (CAPTURED_SCHEMATIC, CAPTURED_SYMBOL,
            ADDRESS_CAPTURE_SCHEMATIC, ADDRESS_CAPTURE_SYMBOL,
            CAPTURE_SCHEMATIC, PHASE_SCHEMATIC, PHASE_SYMBOL,
            CONTROL_DIR / "captured_pclk_phase_source.sch",
            CONTROL_DIR / "captured_pclk_phase_source.sym",
            PRECHARGE_PEX, PRECHARGE_PROVENANCE)),
            "A required project source or PEX input is missing")

    transitions = []
    for item in args.transitions:
        match = re.fullmatch(r"([0-3]):([0-3])", item)
        require(match is not None, f"Invalid address transition: {item}")
        transitions.append((int(match[1]), int(match[2])))
    require(len(set(transitions)) == len(transitions), "Address transitions must be unique")

    pex_text = PRECHARGE_PEX.read_text(encoding="utf-8")
    pex_evidence = phase.inspect_precharge_pex(pex_text)
    provenance = json.loads(PRECHARGE_PROVENANCE.read_text(encoding="utf-8"))
    require(pex_evidence["sha256"] == PRECHARGE_SHA256
            and provenance.get("source_sha256") == PRECHARGE_SHA256,
            "Pinned read-only precharge PEX does not match its provenance")

    lib_paths = {profile: LIBERTY_DIR / capture.LIBRARIES[profile]
                 for profile in args.profiles}
    require(all(path.is_file() for path in lib_paths.values()),
            "A requested dfxtp_1 Liberty file is unavailable")
    arcs = {profile: capture.liberty_arc(path, Q_LIBERTY_LOAD_PF)
            for profile, path in lib_paths.items()}
    thresholds = {
        profile: {
            "slew_lower_pct": threshold_pct(path, "slew_lower_threshold_pct_rise"),
            "slew_upper_pct": threshold_pct(path, "slew_upper_threshold_pct_rise"),
        }
        for profile, path in lib_paths.items()
    }

    output.mkdir(parents=True)
    xschem_dir = output / "xschem"
    wrapper_info = netlist_captured_wrapper(xschem_dir)
    with tempfile.TemporaryDirectory(prefix="captured-phase-pex-") as temp_name:
        temp = Path(temp_name)
        netlist = phase.contract.netlist_current(temp)
        netlist, decoder_wl_evidence = capture.inject_combined_pex(netlist)
        netlist, precharge_instances = phase.attach_precharge_pex(netlist, pex_text)
    base_netlist_sha = hashlib.sha256(netlist.encode()).hexdigest()
    (output / "simulation_input_netlist.spice").write_text(netlist, encoding="utf-8")

    cases = []
    for profile in args.profiles:
        for vector in args.control_vectors:
            selected_transitions = (transitions if args.transitions_per_vector
                                    or vector in VALID_VECTORS else transitions[:1])
            for old, new in selected_transitions:
                cases.append({
                    "label": f"{profile}_ctl{vector}_a{old}_to_{new}_p{args.phase_ps:g}",
                    "profile": profile, "control_vector": vector,
                    "old": old, "new": new, "phase_ps": args.phase_ps,
                    "clk_fall_ps": args.clk_fall_ps,
                    "settling_allowance_ns": args.settling_allowance_ns,
                    **thresholds[profile],
                })

    script_hash = sha256(Path(__file__).resolve())
    source_hashes = {
        str(path.relative_to(ROOT)): sha256(path)
        for path in (Path(__file__).resolve(), CAPTURED_SCHEMATIC, CAPTURED_SYMBOL,
                     ADDRESS_CAPTURE_SCHEMATIC, ADDRESS_CAPTURE_SYMBOL,
                     CONTROL_DIR / "captured_pclk_phase_source.sch",
                     CONTROL_DIR / "captured_pclk_phase_source.sym",
                     CAPTURE_SCHEMATIC, CONTROL_DIR / "valid_access_capture.sym",
                     PHASE_SCHEMATIC, PHASE_SYMBOL,
                     CONTROL_DIR / "phase_delay_inv.sch", CONTROL_DIR / "phase_delay_inv.sym",
                     CONTROL_DIR / "phase_and3.sch", CONTROL_DIR / "phase_and3.sym",
                     CONTROL_DIR / "phase_or2.sch", CONTROL_DIR / "phase_or2.sym",
                     ROOT / "tools/generate_pclk_phase_source.py")
    }
    result_rows = []
    manifest = {
        "campaign": "captured_q_to_transistor_phase_source_matched_interface",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "complete": False,
        "scope": ("Current dynamic decoder and four WL-driver R-C PEX instances plus eight pinned "
                  "Danilo precharge PEX instances and lumped BL residuals. Actual mode netlists "
                  "the captured row-address registers, valid-access qualifier and transistor "
                  "phase source as one wrapper. Reference mode drives address-Q and valid-access-Q "
                  "with dfxtp_1 Liberty-timed PWL waveforms. "
                  "The source outputs drive the same downstream PEX in both modes."),
        "model_family": "SKY130 native ngspice PM3 model library for decoder, WL, precharge, phase logic and standard cells",
        "native_model_corner_by_profile": MODEL_CORNERS,
        "q_reference": {"type": "dfxtp_1 Liberty output arc as PWL",
                        "load_pf": Q_LIBERTY_LOAD_PF,
                        "arcs": arcs},
        "control_equation": "VALID_ACCESS_D = !CSb AND (OEb XOR WEb)",
        "initial_conditioning": ("Controls start at 111; the first 5 ns clock pulse captures invalid/disabled "
                                 "Q=0 and the old address. The target control vector is applied at 5.8 ns; "
                                 "the target row address is applied with 500 ps nominal setup. Both are captured "
                                 "on the 15 ns rising edge."),
        "post_capture_hold_challenge": ("At 15.8 ns, live controls change to the opposite validity class; "
                                        "live address inputs change to the complement of the target address. "
                                        "The captured control and A0_Q/A1_Q must hold through the high phase."),
        "address_capture": {"schematic": "cells/control/row_address_capture.sch",
                            "external_setup_lead_ps": ADDRESS_SETUP_LEAD_PS,
                            "live_address_change_ns": ADDRESS_HOLD_CHALLENGE_NS,
                            "reference": "dfxtp_1 Liberty clock-to-Q PWL from the same address transition",
                            "actual_input_energy_probes": ["v(A0_IN)*i(VA0_IN)",
                                                            "v(A1_IN)*i(VA1_IN)"]},
        "sampling": {"capture_after_edge_ps": Q_CAPTURE_SAMPLE_PS,
                     "high_phase_after_edge_ps": Q_HIGH_HOLD_SAMPLE_PS,
                     "post_fall_delay_ns": Q_FALL_HOLD_SAMPLE_NS},
        "pclk_phase_source": {"schematic": "cells/control/pclk_phase_source.sch",
                              "equations": {"PCLK": "VALID_ACCESS_Q AND CLK AND DLY60",
                                            "PRECH": "VALID_ACCESS_Q AND ((CLK AND DLY24) OR DLY80)"},
                              "delay_taps": [24, 60, 80],
                              "phase_device_sizing_um": {"pfet_w": 1.26, "nfet_w": 0.42,
                                                          "l": 0.15}},
        "precharge_candidate": {**pex_evidence, "source_provenance": provenance,
                                "instances": precharge_instances},
        "decoder_wl_pex_evidence": decoder_wl_evidence,
        "wordline_load_ff": args.wl_cap_ff,
        "bitline_load": {"target_effective_ceiling_ff": phase.CBL_CHARACTERIZED_LIMIT_FF,
                         "precharge_leaf_max_ceff_ff": phase.PRECHARGE_CEFF_MAX_FF,
                         "external_residual_ff_per_side": phase.CBL_EXTERNAL_FF,
                         "interpretation": "lumped residual using pinned precharge leaf evidence; not a distributed bitline"},
        "experimental_checks": {"minimum_release_lead_ps": args.release_lead_ps,
                                "minimum_wl_turnoff_guard_ps": args.turnoff_guard_ps,
                                "not_specification_limits": True},
        "maximum_step_ps": args.step_ps,
        "source_hashes": source_hashes,
        "xschem_wrapper_netlist_sha256": wrapper_info["sha256"],
        "active_wrapper_subcircuit_sha256": wrapper_info["active_sha256"],
        "simulation_input_netlist_sha256": base_netlist_sha,
        "pdk_sha256": {"sky130.lib.spice": sha256(NATIVE_MODEL),
                       "sky130_fd_sc_hd.spice": sha256(SC_LIBRARY),
                       **{path.name: sha256(path) for path in lib_paths.values()}},
        "tools": {"xschem": phase.screen.tool_version("xschem"),
                  "ngspice": phase.screen.tool_version("ngspice")},
        "case_count": len(cases), "cases": cases, "results": result_rows,
        "warnings": {"native_pm3_osdi": "Each ngspice log must be reviewed for unavailable OSDI startup libraries.",
                     "rail_excursions": "No Q/PCLK/PRECH rail-excursion acceptance limit is defined by this bench."},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                           encoding="utf-8")

    summary_rows = []
    comparison_rows = []
    all_checks = []
    failures = []
    representative_case_requested = any(
        case["profile"] == "tt" and case["control_vector"] == "001"
        and case["old"] == 0 and case["new"] == 3 for case in cases)
    representative_saved = False
    for case in cases:
        profile = case["profile"]
        arc = arcs[profile]
        phase_case = {
            **case, "campaign": "timing", "capture_to_pclk_ps": args.phase_ps,
            "skip_prime": True, "clk_fall_ps": args.clk_fall_ps,
            "settling_allowance_ns": args.settling_allowance_ns,
            "lead_ps": 2000, "address_ps": 50, "rise_ps": 25, "fall_ps": 25,
            "step_ps": args.step_ps, "method": "gear", "minbreak_fs": 1,
            "chgtol_c": 1e-18, "dff_load_label": "nominal",
        }
        deck, nodes, devices, terminals, schedule, sim_case = capture.make_deck(
            netlist, phase_case, NATIVE_MODEL, arc, "nominal", args.wl_cap_ff)
        ports = capture.top_pin_map(netlist)
        deck, _ = phase.add_precharge_loads_and_waveforms(
            deck, schedule, case, ports["VSS"], args.release_lead_ps,
            args.turnoff_guard_ps, drive_ideal_prech=False)
        schedule.update({"first_rise": PRIME_RISE_NS*1e-9,
                         "first_fall": PRIME_FALL_NS*1e-9,
                         "second_rise": (CAPTURE_NS*1000+args.phase_ps)*1e-12,
                         "second_fall": args.clk_fall_ps*1e-12,
                         "stop": args.clk_fall_ps*1e-12+5e-9})
        mode_results = {}
        for mode in ("actual", "liberty_reference"):
            mode_case = {**case, "mode": mode}
            mode_dir = output / "cases" / case["label"] / mode
            deck_mode = add_xschem_path(deck, wrapper_info, mode_case, mode,
                                        arc, schedule, ports, nodes)
            sim = run_simulation(deck_mode, mode_dir, mode_case, mode,
                                 manifest["pdk_sha256"]["sky130.lib.spice"])
            if sim["status"] == "ERROR":
                result = {"case": case["label"], "mode": mode, "status": "ERROR",
                          "error": sim["error"]}
                mode_results[mode] = result
                result_rows.append({"case": case["label"], "mode": mode,
                                    "profile": profile,
                                    "control_vector": case["control_vector"],
                                    "status": "ERROR", "check_failures": None,
                                    "error": sim["error"]})
                failures.append(f"{case['label']} {mode}: {sim['error']}")
                summary_rows.append({"case": case["label"], "profile": profile,
                                     "control_vector": case["control_vector"],
                                     "mode": mode, "status": "ERROR"})
                continue
            raw = sim["raw"]
            vdd = float(schedule["vdd"])
            q_rows, q_metrics = q_checks(raw, mode_case, schedule, vdd)
            address_rows, address_metrics = address_checks(
                raw, mode_case, schedule, ports, vdd)
            phase_info, raw_phase_metrics = measured_phase(
                raw, mode_case, nodes, schedule, vdd)
            phase_checks, phase_metrics = phase.evaluate_phase_interface(
                raw, mode_case, nodes, schedule, phase_info,
                args.release_lead_ps, args.turnoff_guard_ps,
                enforce_release_lead=True)
            if case["control_vector"] in VALID_VECTORS:
                contract_raw = raw
                contract_schedule = schedule
                if mode == "actual":
                    # The base decoder contract reports energy contributed by
                    # its address sources. In the transistor-level capture
                    # path, those are the external input sources VA0_IN/VA1_IN,
                    # while the decoder pins are driven by the register Qs.
                    # Alias only for that reporting calculation; leave the
                    # waveform used by all electrical checks untouched.
                    require(all(name in raw for name in
                                ("i(va0_in)", "i(va1_in)",
                                 "v(a0_in)", "v(a1_in)")),
                            "Missing row-address capture input voltage/current probes")
                    contract_raw = dict(raw)
                    contract_raw["i(va0)"] = raw["i(va0_in)"]
                    contract_raw["i(va1)"] = raw["i(va1_in)"]
                    contract_schedule = {
                        **schedule,
                        "ports": {**schedule["ports"],
                                  "A0": "A0_IN", "A1": "A1_IN"},
                    }
                decoder_run, decoder_checks, terminal_rows = phase.contract.analyze(
                    contract_raw, sim_case, nodes, devices, terminals,
                    contract_schedule)
                decoder_failures = decoder_run["check_fail"]
            else:
                decoder_checks, terminal_rows = [], []
                decoder_failures = 0
            checks = q_rows + address_rows + phase_checks + decoder_checks
            all_checks.extend(checks)
            check_failures = sum(row.get("result") != "PASS" for row in checks)
            # Keep both the phase function's checks and the direct edge metrics.
            metrics = {**q_metrics, **address_metrics, **raw_phase_metrics,
                       "precharge_timing": phase_metrics,
                       "decoder_model_upper_result": (decoder_run["model_upper_result"]
                           if case["control_vector"] in VALID_VECTORS else "NOT_EVALUATED"),
                       "decoder_terminal_magnitude_result": (decoder_run["magnitude_result"]
                           if case["control_vector"] in VALID_VECTORS else "NOT_EVALUATED"),
                       "terminal_rows": terminal_rows}
            result_status = "PASS" if check_failures == 0 and decoder_failures == 0 else "REJECTED_SCREEN"
            result = {"case": case["label"], "mode": mode, "profile": profile,
                      "control_vector": case["control_vector"], "operation":
                          VALID_VECTORS.get(case["control_vector"], "invalid_or_idle"),
                      "address_transition": f"{case['old']}:{case['new']}",
                      "status": result_status, "check_failures": check_failures,
                      "decoder_logic_check_failures": decoder_failures,
                      "metrics": metrics, "checks": checks}
            mode_results[mode] = result
            result_rows.append({"case": case["label"], "mode": mode,
                                "profile": profile,
                                "control_vector": case["control_vector"],
                                "address_transition": f"{case['old']}:{case['new']}",
                                "status": result_status,
                                "check_failures": check_failures,
                                "decoder_logic_check_failures": decoder_failures,
                                "metrics": {key: metrics.get(key) for key in (
                                    "capture_to_q_rise_ps", "capture_to_q_fall_ps",
                                    "a0_q_post_capture_v", "a1_q_post_capture_v",
                                    "a0_q_after_live_address_change_v",
                                    "a1_q_after_live_address_change_v",
                                    "capture_to_pclk_rise_ps",
                                    "prech_release_lead_before_pclk_ps",
                                    "pclk_fall_to_precharge_conduction_ps",
                                    "q_min_v", "q_max_v")}})
            write_text(mode_dir / "case.json",
                       json.dumps({key: value for key, value in result.items()
                                   if key != "checks"}, indent=2))
            phase.write_csv(mode_dir / "checks.csv", checks)
            if (not representative_saved and profile == "tt"
                    and case["control_vector"] == "001" and case["old"] == 0
                    and case["new"] == 3):
                save_representative_csv(output / f"{mode}_representative.csv",
                                        raw, nodes["PCLK"])
                representative_saved = mode == "liberty_reference"
            raw["time"] = np.asarray(raw["time"])
            if not args.keep_raw:
                sim["raw_path"].unlink(missing_ok=True)
            summary_rows.append({
                "case": case["label"], "profile": profile,
                "control_vector": case["control_vector"], "address_transition": f"{case['old']}:{case['new']}",
                "mode": mode, "status": result_status,
                "q_capture_ps": metrics.get("capture_to_q_rise_ps",
                                             metrics.get("capture_to_q_fall_ps", "")),
                "capture_to_pclk_rise_ps": metrics.get("capture_to_pclk_rise_ps", ""),
                "precharge_release_lead_ps": metrics.get("prech_release_lead_before_pclk_ps", ""),
                "pclk_fall_to_precharge_conduction_ps": metrics.get("pclk_fall_to_precharge_conduction_ps", ""),
                "q_min_v": metrics["q_min_v"], "q_max_v": metrics["q_max_v"],
                "check_failures": check_failures,
                "decoder_logic_check_failures": decoder_failures,
            })
        actual = mode_results.get("actual", {})
        reference = mode_results.get("liberty_reference", {})
        am = actual.get("metrics", {})
        rm = reference.get("metrics", {})
        comparison_rows.append({
            "case": case["label"], "profile": profile,
            "control_vector": case["control_vector"],
            "actual_status": actual.get("status", "ERROR"),
            "liberty_reference_status": reference.get("status", "ERROR"),
            "actual_q_to_pclk_ps": am.get("capture_to_pclk_rise_ps", ""),
            "liberty_q_to_pclk_ps": rm.get("capture_to_pclk_rise_ps", ""),
            "delta_q_to_pclk_ps": (am.get("capture_to_pclk_rise_ps", 0)
                                    - rm.get("capture_to_pclk_rise_ps", 0)
                                    if am.get("capture_to_pclk_rise_ps") is not None
                                    and rm.get("capture_to_pclk_rise_ps") is not None else ""),
            "actual_release_lead_ps": am.get("prech_release_lead_before_pclk_ps", ""),
            "liberty_release_lead_ps": rm.get("prech_release_lead_before_pclk_ps", ""),
            "actual_pclk_fall_to_prech_ps": am.get("pclk_fall_to_precharge_conduction_ps", ""),
            "liberty_pclk_fall_to_prech_ps": rm.get("pclk_fall_to_precharge_conduction_ps", ""),
        })
        if actual.get("status") not in ("PASS", "REJECTED_SCREEN") or reference.get("status") not in ("PASS", "REJECTED_SCREEN"):
            failures.append(f"{case['label']}: a paired simulation failed")

    phase.write_csv(output / "summary.csv", summary_rows)
    phase.write_csv(output / "matched_comparison.csv", comparison_rows)
    phase.write_csv(output / "checks.csv", all_checks)
    actual_csv = output / "actual_representative.csv"
    liberty_csv = output / "liberty_reference_representative.csv"
    plot_path = output / "captured_phase_vs_liberty_tt_read_a0_to_3.png"
    if actual_csv.is_file() and liberty_csv.is_file():
        plot_representative(actual_csv, liberty_csv, plot_path, 1.8, "tt")
    elif representative_case_requested:
        failures.append("representative TT read waveform was not retained")

    warning_summary = {}
    for path in (output / "cases").rglob("ngspice.log"):
        text = path.read_text(encoding="utf-8", errors="replace")
        missing_osdi = re.findall(r'Error opening osdi lib "([^"]+)"', text)
        warning_summary[str(path.relative_to(output))] = {
            "missing_osdi_libraries": sorted(set(missing_osdi)),
            "no_compatibility_mode_notice": "No compatibility mode selected!" in text,
        }
    failed_rows = [row for row in summary_rows if row.get("status") != "PASS"]
    manifest.update({
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "complete": not failures,
        "status": "PASS" if not failures and not failed_rows else "REVIEW_REQUIRED",
        "simulation_errors": failures,
        "screen_rejections": len(failed_rows),
        "warnings_by_run": warning_summary,
        "summary_files": [path.name for path in (
            output / "summary.csv", output / "matched_comparison.csv",
            output / "checks.csv", plot_path, actual_csv, liberty_csv)
            if path.is_file()],
        "cases_completed": sum(row.get("status") != "ERROR" for row in summary_rows),
    })
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                           encoding="utf-8")
    print(f"Completed: {manifest['cases_completed']} paired case runs across {len(cases)} cases")
    print(f"Passed paired case rows: {sum(row.get('status') == 'PASS' for row in summary_rows)}/{len(summary_rows)}")
    print(f"Screen-rejected rows: {len(failed_rows)}; simulation errors: {len(failures)}")
    if plot_path.is_file():
        print(f"Waveform comparison: {plot_path.relative_to(ROOT)}")
    print(f"Results: {output.relative_to(ROOT)}")
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
