#!/usr/bin/env python3
"""Exercise the dynamic decoder/WL PEX with Danilo's precharge PEX.

The default phase source is ideal PWL. Experimental transistor-level delay
chain sources are also available to screen PCLK/PRECH generation, including a
hierarchical implementation netlisted from the Xschem source. Neither mode
models the captured access qualifier or validates a complete SRAM operation.
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
    transitions = []
    first_release = None
    first_reassert = None
    second_release = None
    second_reassert = None
    if valid:
        first_release = float(schedule["first_rise"]) - release_lead_ps * 1e-12
        first_reassert = float(schedule["first_fall"]) + turnoff_guard_ps * 1e-12
        # Apply the same release lead to the real access pulse. Using the
        # capture edge here released PRECH far earlier than the PCLK event.
        second_release = float(schedule["second_rise"]) - release_lead_ps * 1e-12
        second_reassert = float(schedule["second_fall"]) + turnoff_guard_ps * 1e-12
        transitions.extend([
            (first_release - edge_s/2, first_release + edge_s/2, vdd),
            (first_reassert - edge_s/2, first_reassert + edge_s/2, 0.0),
            (second_release - edge_s/2, second_release + edge_s/2, vdd),
            (second_reassert - edge_s/2, second_reassert + edge_s/2, 0.0),
        ])
        half_edge = edge_s / 2
        require(first_release > half_edge
                and first_release + half_edge < first_reassert - half_edge
                and first_reassert + half_edge < second_release - half_edge
                and second_release + half_edge < second_reassert - half_edge,
                "PRECH release/reassert phases overlap or leave no precharge interval")
        require(second_reassert < stop,
                "The transient ends before the delayed PRECH assertion")
    return contract.pwl(0.0, transitions, stop), {
        "first_release_center_s": first_release,
        "first_reassert_center_s": first_reassert,
        "second_release_center_s": second_release,
        "second_reassert_center_s": second_reassert,
        "release_lead_ps": release_lead_ps,
        "turnoff_guard_ps": turnoff_guard_ps,
    }


def tapped_phase_subcircuit(release_stages: int, evaluation_stages: int,
                           reassert_stages: int) -> str:
    """Build an experimental transistor-level, three-tap phase generator.

    PRECH = VALID & ((CLK & DLY_RELEASE) | DLY_REASSERT). The release tap
    delays the rising transition, while the reassert tap holds PRECH released
    after CLK falls. PCLK = VALID & CLK & DLY_EVALUATION.
    """
    require(0 < release_stages < evaluation_stages < reassert_stages,
            "Delay taps must satisfy 0 < release < evaluation < reassert")
    require(all(stage % 2 == 0 for stage in
                (release_stages, evaluation_stages, reassert_stages)),
            "Delay taps must have an even number of inverters to preserve polarity")
    lines = [
        ".subckt phase_delay_inv A Y VDD VSS",
        "XMP Y A VDD VDD sky130_fd_pr__pfet_01v8 w=0.84 l=0.15 nf=1 m=1",
        "XMN Y A VSS VSS sky130_fd_pr__nfet_01v8 w=0.42 l=0.15 nf=1 m=1",
        ".ends phase_delay_inv",
        ".subckt phase_output_inv A Y VDD VSS",
        "XMP Y A VDD VDD sky130_fd_pr__pfet_01v8 w=3.0 l=0.15 nf=1 m=1",
        "XMN Y A VSS VSS sky130_fd_pr__nfet_01v8 w=1.5 l=0.15 nf=1 m=1",
        ".ends phase_output_inv",
        ".subckt phase_and3 A B C Y VDD VSS",
        "XMPA N A VDD VDD sky130_fd_pr__pfet_01v8 w=0.84 l=0.15 nf=1 m=1",
        "XMPB N B VDD VDD sky130_fd_pr__pfet_01v8 w=0.84 l=0.15 nf=1 m=1",
        "XMPC N C VDD VDD sky130_fd_pr__pfet_01v8 w=0.84 l=0.15 nf=1 m=1",
        "XMNA N A N1 VSS sky130_fd_pr__nfet_01v8 w=0.42 l=0.15 nf=1 m=1",
        "XMNB N1 B N2 VSS sky130_fd_pr__nfet_01v8 w=0.42 l=0.15 nf=1 m=1",
        "XMNC N2 C VSS VSS sky130_fd_pr__nfet_01v8 w=0.42 l=0.15 nf=1 m=1",
        "XINV N Y VDD VSS phase_output_inv",
        ".ends phase_and3",
        ".subckt phase_or2 A B Y VDD VSS",
        "XMPA N1 A VDD VDD sky130_fd_pr__pfet_01v8 w=1.68 l=0.15 nf=1 m=1",
        "XMPB N B N1 VDD sky130_fd_pr__pfet_01v8 w=1.68 l=0.15 nf=1 m=1",
        "XMNA N A VSS VSS sky130_fd_pr__nfet_01v8 w=0.42 l=0.15 nf=1 m=1",
        "XMNB N B VSS VSS sky130_fd_pr__nfet_01v8 w=0.42 l=0.15 nf=1 m=1",
        "XINV N Y VDD VSS phase_output_inv",
        ".ends phase_or2",
        ".subckt pclk_phase_gen CLK VALID_ACCESS_Q VDD VSS PCLK PRECH",
    ]
    for stage in range(1, reassert_stages + 1):
        source = "CLK" if stage == 1 else f"DLY{stage-1}"
        lines.append(f"XDL{stage:02d} {source} DLY{stage} VDD VSS phase_delay_inv")
    lines.extend([
        f"XREL CLK DLY{release_stages} VDD CLK_RELEASED VDD VSS phase_and3",
        f"XOR1 CLK_RELEASED DLY{reassert_stages} PRECH_SET VDD VSS phase_or2",
        f"XPCLK VALID_ACCESS_Q CLK DLY{evaluation_stages} PCLK VDD VSS phase_and3",
        "XPRECH VALID_ACCESS_Q PRECH_SET VDD PRECH VDD VSS phase_and3",
        ".ends pclk_phase_gen",
    ])
    return "\n".join(lines)


def resize_phase_delay_subcircuit(block: str, pfet_width_um: float,
                                 nfet_width_um: float) -> str:
    """Apply an experimental width pair to the Xschem-generated delay inverter."""
    replacements = (
        ("XMP", "sky130_fd_pr__pfet_01v8", pfet_width_um),
        ("XMN", "sky130_fd_pr__nfet_01v8", nfet_width_um),
    )
    for instance, model, width in replacements:
        lines = block.splitlines()
        matching = [index for index, line in enumerate(lines)
                    if re.match(rf"(?i)^{instance}\s", line)
                    and model.lower() in line.lower()]
        require(len(matching) == 1,
                f"Expected one {instance} {model} in phase_delay_inv; found {len(matching)}")
        index = matching[0]
        updated, count = re.subn(r"(?i)\bW=[^\s]+", f"W={width:.6g}",
                                 lines[index], count=1)
        require(count == 1, f"Could not replace {instance} width in phase_delay_inv")
        lines[index] = updated
        block = "\n".join(lines)
    return block


def netlist_xschem_phase_source(folder: Path,
                                delay_pfet_w_um: float | None = None,
                                delay_nfet_w_um: float | None = None) -> dict:
    """Netlist the checked-in Xschem phase source and return a reusable SPICE hierarchy."""
    pdk = Path(os.environ.get("PDK_ROOT", "/opt/pdks")) / "sky130A"
    library_dirs = [pdk / "libs.tech/xschem", ROOT / "cells/control"]
    tcl = ('set XSCHEM_LIBRARY_PATH [join [list "$XSCHEM_SHAREDIR/xschem_library" '
           '"$XSCHEM_SHAREDIR/xschem_library/devices" ' +
           " ".join("{" + str(path) + "}" for path in library_dirs) + '] ":"]')
    folder.mkdir(parents=True, exist_ok=True)
    command = ["xschem", "-x", "-q", "-n", "--tcl", tcl,
               "--netlist_path", str(folder), "-N", "pclk_phase_source_xschem.spice",
               str(ROOT / "cells/control/pclk_phase_source.sch")]
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
    log = proc.stdout + proc.stderr
    (folder / "xschem.log").write_text(log, encoding="utf-8")
    require(proc.returncode == 0 and not re.search(
        r"Error:|symbol not found|IS MISSING|overlapped instance", log, re.I),
        "Xschem phase-source netlist failed: " + log)
    netlist_path = folder / "pclk_phase_source_xschem.spice"
    require(netlist_path.is_file(), "Xschem did not create the phase-source netlist")
    raw = netlist_path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    top_start = next((i for i, line in enumerate(lines)
                      if re.match(r"^\*\*\.subckt\s+pclk_phase_source\b", line)), None)
    require(top_start is not None, "Xschem netlist has no pclk_phase_source top cell")
    top_end = next((i for i in range(top_start + 1, len(lines))
                    if re.match(r"^\*\*\.ends\s*$", lines[i])), None)
    require(top_end is not None, "Xschem top phase-source cell has no end marker")
    original_header = lines[top_start].split()
    original_pins = original_header[2:]
    require(original_pins == ["VDD", "CLK", "VSS", "VALID_ACCESS_Q", "PCLK", "PRECH"],
            f"Unexpected Xschem phase-source pin order: {original_pins}")
    # The shared simulation harness uses a stable canonical order. These are
    # named SPICE formals, so changing the header order preserves connectivity.
    active_top = [".subckt pclk_phase_gen CLK VALID_ACCESS_Q VDD VSS PCLK PRECH"]
    active_top.extend(line for line in lines[top_start + 1:top_end]
                      if not line.startswith("**"))
    active_top.append(".ends pclk_phase_gen")
    child_subckts = []
    for match in re.finditer(
            r"(?ms)^\.subckt\s+(phase_delay_inv|phase_and3|phase_or2)\b[^\n]*\n"
            r".*?^\.ends\s*$", raw):
        child_subckts.append(match.group(0))
    child_names = [re.match(r"(?im)^\.subckt\s+(\S+)", block)[1]
                   for block in child_subckts]
    require(set(child_names) == {"phase_delay_inv", "phase_and3", "phase_or2"},
            f"Unexpected Xschem phase-source hierarchy: {child_names}")
    require((delay_pfet_w_um is None) == (delay_nfet_w_um is None),
            "Specify both phase-delay PFET and NFET widths, or neither")
    if delay_pfet_w_um is not None:
        require(math.isfinite(delay_pfet_w_um) and math.isfinite(delay_nfet_w_um)
                and delay_pfet_w_um >= 0.42 and delay_nfet_w_um >= 0.42,
                "Phase-delay device widths must be finite and at least 0.42 um per finger")
        delay_index = child_names.index("phase_delay_inv")
        child_subckts[delay_index] = resize_phase_delay_subcircuit(
            child_subckts[delay_index], delay_pfet_w_um, delay_nfet_w_um)
    phase_delay_block = child_subckts[child_names.index("phase_delay_inv")]
    phase_delay_widths = {}
    for instance, model, key in (
            ("XMP", "sky130_fd_pr__pfet_01v8", "pfet_w_um"),
            ("XMN", "sky130_fd_pr__nfet_01v8", "nfet_w_um")):
        device_line = next(line for line in phase_delay_block.splitlines()
                           if re.match(rf"(?i)^{instance}\s", line)
                           and model.lower() in line.lower())
        width_match = re.search(r"(?i)\bW=([0-9.eE+-]+)", device_line)
        require(width_match is not None,
                f"Could not read {instance} width from phase_delay_inv")
        phase_delay_widths[key] = float(width_match[1])
    subckt = "\n".join(
        active_top + [""] + [block.rstrip() for block in child_subckts]).rstrip() + "\n"
    top_body = "\n".join(active_top)
    require(len(re.findall(r"(?im)^XDL\d+\s", top_body)) == 80,
            "Xschem phase source does not contain 80 delay stages")
    require(all(re.search(rf"(?im)^X{name}\s", top_body)
                for name in ("REL", "OR1", "PCLK", "PRECH")),
            "Xschem phase-source gate instances are incomplete")
    mos_counts = {}
    for name, block in zip(child_names, child_subckts):
        mos_counts[name] = len(re.findall(
            r"(?im)^X\S+\s+.*\bsky130_fd_pr__(?:p|n)fet_01v8\b", block))
    total_mos = 80 * mos_counts["phase_delay_inv"] + \
        3 * mos_counts["phase_and3"] + mos_counts["phase_or2"]
    require(mos_counts == {"phase_delay_inv": 2, "phase_and3": 8, "phase_or2": 6}
            and total_mos == 190,
            f"Unexpected Xschem phase-source transistor count: {mos_counts}, total={total_mos}")
    return {
        "subcircuit": subckt,
        "raw_netlist": raw,
        "netlist_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "active_subcircuit_sha256": hashlib.sha256(subckt.encode()).hexdigest(),
        "phase_delay_sizing_um": phase_delay_widths,
        "hierarchy_mos_count": mos_counts,
        "total_mos_count": total_mos,
        "delay_stages": 80,
        "xschem_version": screen.tool_version("xschem"),
    }


def attach_tapped_phase_source(deck: str, schedule: dict, case: dict,
                               ports: dict, nodes: dict, release_stages: int,
                               evaluation_stages: int, reassert_stages: int,
                               phase_subcircuit: str | None = None,
                               valid_access_q_delay_ps: float = 0.0) -> str:
    vdd = float(schedule["vdd"])
    stop = float(schedule["stop"])
    edge_s = 25e-12
    first_rise = 5e-9
    first_fall = 10e-9
    second_rise = CAPTURE_NS * 1e-9
    second_fall = float(schedule["second_fall"])
    valid = case["control_vector"] in VALID_VECTORS
    clock = contract.pwl(0.0, [
        (first_rise-edge_s/2, first_rise+edge_s/2, vdd),
        (first_fall-edge_s/2, first_fall+edge_s/2, 0.0),
        (second_rise-edge_s/2, second_rise+edge_s/2, vdd),
        (second_fall-edge_s/2, second_fall+edge_s/2, 0.0),
    ], stop)
    valid_access_q_rise = second_rise + valid_access_q_delay_ps * 1e-12
    valid_waveform = contract.pwl(
        0.0,
        [(valid_access_q_rise-edge_s/2, valid_access_q_rise+edge_s/2, vdd)] if valid else [],
        stop,
    )
    deck, count = re.subn(r"(?im)^VPCLK\s+\S+\s+\S+\s+[^\n]+\n", "", deck, count=1)
    require(count == 1, "Could not remove the ideal PCLK source for phase-chain mode")
    additions = [
        f"VPHASE_CLK PHASE_CLK 0 {clock}",
        f"VVALID_ACCESS_Q VALID_ACCESS_Q 0 {valid_waveform}",
        f"XPHASEGEN PHASE_CLK VALID_ACCESS_Q {ports['VDD']} {ports['VSS']} "
        f"PHASE_PCLK PRECH pclk_phase_gen",
        # A zero-volt series probe preserves i(VPCLK) for the decoder's
        # existing supply/load accounting. Orient its positive terminal at
        # the decoder side to retain the original delivered-power sign.
        f"VPCLK {nodes['PCLK']} PHASE_PCLK 0",
        (phase_subcircuit or tapped_phase_subcircuit(
            release_stages, evaluation_stages, reassert_stages)),
    ]
    deck, count = re.subn(r"(?im)^(\.lib\s+)", "\n".join(additions)+"\n\\1", deck, count=1)
    require(count == 1, "Could not insert the transistor-level phase generator")
    tap_nodes = " ".join(f"v(xphasegen.dly{stage})" for stage in sorted(
        {release_stages, evaluation_stages, reassert_stages}))
    tap_nodes += " v(xphasegen.clk_released) v(xphasegen.prech_set) "
    tap_nodes += "v(xphasegen.pclk) v(xphasegen.prech)"
    deck, count = re.subn(r"(?im)^(\.save\s+[^\n]+)$",
                          lambda match: match.group(1)+" v(PHASE_CLK) v(VALID_ACCESS_Q) "
                          + "i(VPHASE_CLK) " + tap_nodes,
                          deck, count=1)
    require(count == 1, "Could not add phase-generator waveform probes")
    return deck


def measure_tapped_phase(raw: dict[str, np.ndarray], case: dict,
                         nodes: dict, schedule: dict,
                         release_stages: int, evaluation_stages: int,
                         reassert_stages: int) -> tuple[dict, dict]:
    """Use the simulated phase-source crossings for decoder and PRECH checks."""
    time = raw["time"]
    vdd = float(schedule["vdd"])
    pclk = trace(raw, nodes["PCLK"])
    prech = trace(raw, "PRECH")
    second_rise = crossing(time, pclk, 0.5*vdd, True, 14.8e-9,
                           float(schedule["second_fall"])-0.1e-9)
    second_fall = crossing(time, pclk, 0.5*vdd, False,
                           float(schedule["second_fall"])-0.1e-9,
                           float(schedule["second_fall"])+1e-9)
    require(all(value is not None for value in (second_rise, second_fall)),
            f"Missing generated PCLK edge in {case['label']}")
    phase_clk = trace(raw, "PHASE_CLK")
    clk_edges = {
        "prime_rise": crossing(time, phase_clk, 0.5*vdd, True, 4.8e-9, 5.5e-9),
        "prime_fall": crossing(time, phase_clk, 0.5*vdd, False, 9.8e-9, 10.5e-9),
        "access_rise": crossing(time, phase_clk, 0.5*vdd, True, 14.8e-9, 15.5e-9),
        "access_fall": crossing(time, phase_clk, 0.5*vdd, False,
                                 float(schedule["second_fall"])-0.2e-9,
                                 float(schedule["second_fall"])+0.5e-9),
    }
    require(all(value is not None for value in clk_edges.values()),
            f"Missing input-clock crossing in {case['label']}")
    tap_timing = {}
    for stage in sorted({release_stages, evaluation_stages, reassert_stages}):
        signal = trace(raw, f"xphasegen.dly{stage}")
        tap_edges = {
            "prime_rise": crossing(time, signal, 0.5*vdd, True, 4.8e-9, 10e-9),
            "prime_fall": crossing(time, signal, 0.5*vdd, False, 10e-9, 15e-9),
            "access_rise": crossing(time, signal, 0.5*vdd, True, 14.8e-9,
                                     float(schedule["second_fall"])),
            "access_fall": crossing(time, signal, 0.5*vdd, False,
                                     float(schedule["second_fall"]),
                                     float(schedule["stop"])),
        }
        require(all(value is not None for value in tap_edges.values()),
                f"Missing delay-tap crossing at stage {stage} in {case['label']}")
        tap_timing[str(stage)] = {
            f"{edge}_delay_ps": (tap_edges[edge]-clk_edges[edge])*1e12
            for edge in tap_edges
        }
    release = crossing(time, prech, 0.75*vdd, True,
                       (CAPTURE_NS-0.2)*1e-9, second_fall)
    reassertion = crossing(time, prech, 0.75*vdd, False,
                           second_fall, float(schedule["stop"]))
    require(release is not None and reassertion is not None,
            f"Missing generated PRECH edge in {case['label']}")
    edge_widths = []
    for center, rising in ((second_rise, True), (second_fall, False)):
        t10 = crossing(time, pclk, 0.1*vdd, rising, center-0.5e-9, center+0.5e-9)
        t90 = crossing(time, pclk, 0.9*vdd, rising, center-0.5e-9, center+0.5e-9)
        require(t10 is not None and t90 is not None,
                f"Missing PCLK slew crossing in {case['label']}")
        edge_widths.append(abs(t90-t10))
    phase = {
        "first_release_center_s": None,
        "first_reassert_center_s": None,
        "second_release_center_s": release,
        "second_reassert_center_s": reassertion,
        "release_lead_ps": None,
        "turnoff_guard_ps": None,
    }
    schedule.update({"second_rise": second_rise, "second_fall": second_fall,
                     "rise": edge_widths[0], "fall": edge_widths[1]})
    capclk = trace(raw, "CAPCLK")
    capture_edge = crossing(time, capclk, 0.5*vdd, True,
                            (CAPTURE_NS-0.2)*1e-9, (CAPTURE_NS+0.2)*1e-9)
    require(capture_edge is not None, "Missing captured CLK edge in phase-chain case")
    valid_access_q = trace(raw, "VALID_ACCESS_Q")
    valid_access_q_rise = crossing(time, valid_access_q, 0.5*vdd, True,
                                   capture_edge-0.1e-9, float(schedule["stop"]))
    require(valid_access_q_rise is not None,
            "Missing VALID_ACCESS_Q rising crossing in phase-chain case")
    measured = {
        "capture_to_pclk_rise_ps": (second_rise-capture_edge)*1e12,
        "capture_to_valid_access_q_rise_ps": (valid_access_q_rise-capture_edge)*1e12,
        "valid_access_q_rise_ns": valid_access_q_rise*1e9,
        "prime_pclk_rise_ns": None,
        "pclk_rise_ns": second_rise*1e9,
        "pclk_fall_ns": second_fall*1e9,
        "precharge_release_ns": release*1e9,
        "precharge_reassert_ns": reassertion*1e9,
        "prime_clock_suppressed_until_access": True,
        "phase_source": "tapped_transistor_inverter_chain",
        "delay_tap_stages": {
            "release": release_stages,
            "evaluation": evaluation_stages,
            "reassert": reassert_stages,
        },
        "delay_tap_timing": tap_timing,
    }
    return phase, measured


def delay_prime_pclk(deck: str, schedule: dict, vdd: float,
                     prime_rise_ns: float, release_lead_ps: float,
                     rise_ps: float = 25.0,
                     fall_ps: float = 25.0) -> tuple[str, dict]:
    """Extend power-up precharge before the bench's first conditioning pulse."""
    first_rise = prime_rise_ns * 1e-9
    first_fall = float(schedule["first_fall"])
    second_rise = float(schedule["second_rise"])
    second_fall = float(schedule["second_fall"])
    stop = float(schedule["stop"])
    rise_s, fall_s = rise_ps*1e-12, fall_ps*1e-12
    require(first_rise > rise_s and first_rise + rise_s/2 < first_fall-fall_s/2,
            "Prime PCLK pulse must fit before its falling edge")
    waveform = contract.pwl(0.0, [
        (first_rise-rise_s/2, first_rise+rise_s/2, vdd),
        (first_fall-fall_s/2, first_fall+fall_s/2, 0.0),
        (second_rise-rise_s/2, second_rise+rise_s/2, vdd),
        (second_fall-fall_s/2, second_fall+fall_s/2, 0.0),
    ], stop)
    deck, count = re.subn(r"(?im)^(VPCLK\s+\S+\s+\S+)\s+[^\n]+$",
                          lambda match: match.group(1) + " " + waveform,
                          deck, count=1)
    require(count == 1, "Could not extend the initial PCLK precharge interval")
    schedule["first_rise"] = first_rise
    return deck, {"prime_pclk_rise_ns": prime_rise_ns,
                  "precharge_release_center_ns": prime_rise_ns-release_lead_ps/1000.0,
                  "initial_precharge_until_release_ns": prime_rise_ns-release_lead_ps/1000.0}


def add_precharge_loads_and_waveforms(deck: str, schedule: dict, case: dict,
                                      vss: str,
                                      release_lead_ps: float,
                                      turnoff_guard_ps: float,
                                      drive_ideal_prech: bool = True) -> tuple[str, dict]:
    valid = case["control_vector"] in VALID_VECTORS
    if drive_ideal_prech:
        waveform, phase = phase_waveform(schedule, valid, float(schedule["vdd"]),
                                         release_lead_ps, turnoff_guard_ps)
        additions = [f"VPRECH PRECH 0 {waveform}"]
    else:
        phase = {
            "first_release_center_s": None,
            "first_reassert_center_s": None,
            "second_release_center_s": None,
            "second_reassert_center_s": None,
        }
        additions = []
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


def suppress_all_pclk(deck: str, schedule: dict) -> str:
    """Keep PCLK low throughout an invalid/idle control case."""
    waveform = contract.pwl(0.0, [], float(schedule["stop"]))
    deck, count = re.subn(r"(?im)^(VPCLK\s+\S+\s+\S+)\s+[^\n]+$",
                          lambda match: match.group(1) + " " + waveform,
                          deck, count=1)
    require(count == 1, "Could not suppress PCLK for the invalid/idle case")
    return deck


def evaluate_phase_interface(raw: dict[str, np.ndarray], case: dict,
                             nodes: dict, schedule: dict, phase: dict,
                             release_lead_ps: float,
                             turnoff_guard_ps: float,
                             enforce_release_lead: bool = False) -> tuple[list[dict], dict]:
    time = raw["time"]
    vdd = float(schedule["vdd"])
    prech = trace(raw, "PRECH")
    pclk = trace(raw, nodes["PCLK"])
    checks: list[dict] = []
    minimum_release_lead_ps = release_lead_ps if enforce_release_lead else 0.0
    measurements: dict = {"bitline_external_load_ff": CBL_EXTERNAL_FF,
                          "bitline_target_effective_ceiling_ff": CBL_CHARACTERIZED_LIMIT_FF,
                          "minimum_release_lead_required_ps": minimum_release_lead_ps,
                          "release_lead_measurement": (
                              "PRECH rising 75% VDD crossing to PCLK rising 50% VDD crossing"),
                          "precharge_releases": [], "precharge_reassertions": []}
    valid = case["control_vector"] in VALID_VECTORS

    phase_cycles = []
    if phase.get("first_release_center_s") is not None:
        phase_cycles.append(("prime", float(schedule["first_rise"]),
                             float(schedule["first_fall"]),
                             phase["first_release_center_s"],
                             phase["first_reassert_center_s"], int(case["old"])))
    phase_cycles.append(("access", float(schedule["second_rise"]),
                         float(schedule["second_fall"]),
                         phase["second_release_center_s"],
                         phase["second_reassert_center_s"], int(case["new"])))
    for cycle, pclk_rise_nominal, pclk_fall_nominal, release_center, reassert_center, selected in phase_cycles:
        if not valid:
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
                  release_margin_ps, low=minimum_release_lead_ps, unit="ps")
        add_check(checks, case, f"{cycle}_precharge_reassert_after_pclk_fall_ps",
                  reassert_margin_ps, low=0, unit="ps")
        add_check(checks, case, f"{cycle}_PRECH_high_at_PCLK_rise_v",
                  float(np.interp(pclk_up, time, prech)), low=0.9*vdd, unit="V")

        selected_wl = trace(raw, nodes[f"WL{selected}"])
        selected_off = crossing(time, selected_wl, 0.1*vdd, False,
                                pclk_down, min(float(schedule["stop"]), reassert_center+3e-9))
        selected_off_clearance_ps = (
            None if selected_off is None else (pre_assert-selected_off)*1e12)
        add_check(checks, case, f"{cycle}_selected_WL_off_before_PRECH_conduction_ps",
                  math.nan if selected_off_clearance_ps is None else selected_off_clearance_ps,
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
            "pclk_fall_to_precharge_conduction_ps": reassert_margin_ps,
            "selected_wl_off_clearance_ps": selected_off_clearance_ps,
            "selected_wl_below_10pct_s": selected_off})

        for bit in range(8):
            for name in (f"BL{bit}", f"BLB{bit}"):
                signal = trace(raw, name)
                sample_time = max(0.0, pclk_up-50e-12)
                add_check(checks, case, f"{cycle}_{name}_precharged_before_eval_v",
                          float(np.interp(sample_time, time, signal)), low=0.9*vdd, unit="V")

    if not valid:
        start = float(schedule["first_rise"])
        end = float(schedule["stop"])
        region = (time >= start) & (time <= end)
        require(region.any(), "Missing disabled/invalid second clock window")
        add_check(checks, case, "invalid_PCLK_peak_v", float(pclk[region].max()),
                  high=0.1*vdd, unit="V")
        add_check(checks, case, "invalid_PRECH_active_v",
                  float(prech[region].max()), high=0.1*vdd, unit="V")
        for output in ("DEC0", "DEC1", "DEC2", "DEC3", "WL0", "WL1", "WL2", "WL3"):
            signal = trace(raw, nodes[output])
            add_check(checks, case, f"invalid_{output}_peak_v",
                      float(signal[region].max()), high=0.1*vdd, unit="V")
        for row in range(4):
            internal = trace(raw, f"x1.n{row}")
            add_check(checks, case, f"invalid_N{row}_precharged_min_v",
                      float(internal[region].min()), low=0.9*vdd, unit="V")

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
             turnoff_guard_ps: float, prime_pclk_rise_ns: float,
             output: Path, keep_raw: bool, phase_source: str,
             delay_release_stages: int, delay_evaluation_stages: int,
             delay_reassert_stages: int,
             phase_subcircuit: str | None = None,
             valid_access_q_delay_ps: float = 0.0) -> dict:
    case_dir = output / "cases" / case["label"]
    case_dir.mkdir(parents=True)
    arc = arcs[case["profile"]]
    phase_case = {
        **case,
        "campaign": "timing",
        "capture_to_pclk_ps": case["phase_ps"],
        "skip_prime": phase_source != "ideal",
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
                                                    release_lead_ps, turnoff_guard_ps,
                                                    drive_ideal_prech=phase_source == "ideal")
    phase_source_metrics = None
    if phase_source == "ideal":
        deck, prime_metrics = delay_prime_pclk(deck, schedule, float(schedule["vdd"]),
                                               prime_pclk_rise_ns, release_lead_ps,
                                               float(phase_case["rise_ps"]),
                                               float(phase_case["fall_ps"]))
        if case["control_vector"] not in VALID_VECTORS:
            deck = suppress_all_pclk(deck, schedule)
    else:
        prime_metrics = {"phase_source": ("xschem_hierarchical_transistor_phase_source"
                                           if phase_source == "xschem-tapped-delay-chain"
                                           else "tapped_transistor_inverter_chain"),
                         "prime_clk_input_rise_ns": 5.0,
                         "prime_clk_input_fall_ns": 10.0,
                         "prime_access_suppressed": True,
                         "bitline_precharge_remains_active_until_access": True}
        deck = attach_tapped_phase_source(
            deck, schedule, case, ports, nodes, delay_release_stages,
            delay_evaluation_stages, delay_reassert_stages,
            phase_subcircuit=phase_subcircuit,
            valid_access_q_delay_ps=valid_access_q_delay_ps)
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
    if phase_source != "ideal" and case["control_vector"] in VALID_VECTORS:
        phase, phase_source_metrics = measure_tapped_phase(
            raw, case, nodes, schedule, delay_release_stages,
            delay_evaluation_stages, delay_reassert_stages)
        if phase_source == "xschem-tapped-delay-chain":
            phase_source_metrics["phase_source"] = "xschem_hierarchical_transistor_phase_source"
    phase_checks, phase_metrics = evaluate_phase_interface(
        raw, case, nodes, schedule, phase, release_lead_ps, turnoff_guard_ps,
        enforce_release_lead=phase_source != "ideal")
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
        "valid_access_q_delay_ps": valid_access_q_delay_ps,
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
        "signal_nodes": {"PCLK": nodes["PCLK"],
                         **{f"DEC{row}": nodes[f"DEC{row}"] for row in range(4)},
                         **{f"WL{row}": nodes[f"WL{row}"] for row in range(4)},
                         "PRECH": "PRECH", "BL0": "BL0", "BLB0": "BLB0"},
        "precharge_timing": phase_metrics,
        "initial_precharge": prime_metrics,
        "phase_source": phase_source,
        "phase_source_timing": phase_source_metrics,
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
    parser.add_argument("--phase-ps", type=float, default=2100.0,
                        help="Initial experimental capture-to-PCLK candidate; not a specification limit")
    parser.add_argument("--clk-fall-ps", type=float, default=20700.0)
    parser.add_argument("--settling-allowance-ns", type=float, default=3.3)
    parser.add_argument("--wl-cap-ff", type=float, default=102.873935496,
                        help="Full-row Ceff maximum from Danilo's current owner evidence")
    parser.add_argument("--release-lead-ps", type=float, default=250.0,
                        help=("Nominal ideal-source lead and minimum measured lead for "
                              "transistor-level phase-source modes"))
    parser.add_argument("--turnoff-guard-ps", type=float, default=1800.0,
                        help="Initial experimental PRECH reassertion delay after PCLK falls")
    parser.add_argument("--prime-pclk-rise-ns", type=float, default=6.0,
                        help="Delay the nonarchitectural first conditioning pulse to allow startup precharge")
    parser.add_argument("--phase-source", choices=("ideal", "tapped-delay-chain",
                                                    "xschem-tapped-delay-chain"), default="ideal",
                        help="Use ideal phases, generated transistor phases, or the checked-in Xschem phase source")
    parser.add_argument("--delay-release-stages", type=int, default=24,
                        help="Even inverter count for the early PRECH release tap")
    parser.add_argument("--delay-evaluation-stages", type=int, default=60,
                        help="Even inverter count for the delayed PCLK evaluation tap")
    parser.add_argument("--delay-reassert-stages", type=int, default=80,
                        help="Even inverter count for the delayed PRECH reassertion tap")
    parser.add_argument("--phase-delay-pfet-w-um", type=float,
                        help="Experimental Xschem phase-chain PFET width override; requires the NFET override")
    parser.add_argument("--phase-delay-nfet-w-um", type=float,
                        help="Experimental Xschem phase-chain NFET width override; requires the PFET override")
    parser.add_argument("--valid-access-q-delay-ps", type=float, default=0.0,
                        help="Idealized delay from the CLK capture edge to VALID_ACCESS_Q rising; not a capture-cell model")
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
    require(math.isfinite(args.prime_pclk_rise_ns)
            and args.prime_pclk_rise_ns > args.release_lead_ps/1000
            and args.prime_pclk_rise_ns < 10.0,
            "prime PCLK rise must leave startup precharge and fit before the fixed 10 ns fall")
    require(args.phase_source == "ideal" or
            (0 < args.delay_release_stages < args.delay_evaluation_stages
             < args.delay_reassert_stages
             and all(stage % 2 == 0 for stage in (args.delay_release_stages,
                                                    args.delay_evaluation_stages,
                                                    args.delay_reassert_stages))),
            "Tapped phase-chain counts must be positive, even, and ordered release<evaluation<reassert")
    require((args.phase_delay_pfet_w_um is None)
            == (args.phase_delay_nfet_w_um is None),
            "Specify both phase-delay PFET and NFET width overrides, or neither")
    if args.phase_delay_pfet_w_um is not None:
        require(args.phase_source == "xschem-tapped-delay-chain",
                "Phase-delay width overrides require --phase-source xschem-tapped-delay-chain")
        require(math.isfinite(args.phase_delay_pfet_w_um)
                and math.isfinite(args.phase_delay_nfet_w_um)
                and args.phase_delay_pfet_w_um >= 0.42
                and args.phase_delay_nfet_w_um >= 0.42,
                "Phase-delay widths must be finite and at least 0.42 um per finger")
    require(math.isfinite(args.valid_access_q_delay_ps)
            and args.valid_access_q_delay_ps >= 0
            and args.valid_access_q_delay_ps
            < args.clk_fall_ps - CAPTURE_NS*1000,
            "VALID_ACCESS_Q delay must be finite, nonnegative, and rise before the scheduled CLK falling edge")
    require(args.phase_source != "ideal" or args.valid_access_q_delay_ps == 0,
            "VALID_ACCESS_Q delay requires a transistor-level phase-source mode")
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
        phase_source_info = (
            netlist_xschem_phase_source(
                Path(temp) / "phase-source", args.phase_delay_pfet_w_um,
                args.phase_delay_nfet_w_um)
            if args.phase_source == "xschem-tapped-delay-chain" else None)
    phase_subcircuit = (phase_source_info["subcircuit"]
                        if phase_source_info is not None else None)
    if phase_source_info is not None:
        (output / "pclk_phase_source_xschem.spice").write_text(
            phase_source_info["raw_netlist"], encoding="utf-8")
        (output / "pclk_phase_source_subcircuit.spice").write_text(
            phase_subcircuit, encoding="utf-8")
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
            delay_suffix = (f"_vq{args.valid_access_q_delay_ps:g}"
                            if args.valid_access_q_delay_ps else "")
            label = f"{profile}_ctl{vector}_a{old}_to_{new}_p{args.phase_ps:g}{delay_suffix}"
            cases.append({"label": label, "profile": profile, "control_vector": vector,
                          "old": old, "new": new, "phase_ps": args.phase_ps,
                          "clk_fall_ps": args.clk_fall_ps,
                          "settling_allowance_ns": args.settling_allowance_ns,
                          "valid_access_q_delay_ps": args.valid_access_q_delay_ps,
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
    if phase_source_info is not None:
        for relpath in ("cells/control/pclk_phase_source.sch",
                        "cells/control/pclk_phase_source.sym",
                        "cells/control/phase_delay_inv.sch",
                        "cells/control/phase_delay_inv.sym",
                        "cells/control/phase_and3.sch",
                        "cells/control/phase_and3.sym",
                        "cells/control/phase_or2.sch",
                        "cells/control/phase_or2.sym",
                        "tools/generate_pclk_phase_source.py"):
            hashes[relpath.replace("/", "_") + "_sha256"] = hashlib.sha256(
                (ROOT / relpath).read_bytes()).hexdigest()
        hashes["xschem_phase_source_netlist_sha256"] = phase_source_info["netlist_sha256"]
        hashes["active_phase_source_subcircuit_sha256"] = phase_source_info[
            "active_subcircuit_sha256"]
    model_hashes = contract.model_dependencies(model)
    for path in lib_paths.values():
        model_hashes[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {
        "campaign": "dynamic_decoder_wl_precharge_phase_interface",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "complete": False,
        "source_branch": subprocess.run(["git", "branch", "--show-current"], cwd=ROOT,
                                         capture_output=True, text=True, check=True).stdout.strip(),
        "scope": ("Current decoder R-C PEX, four WL-driver R-C PEX instances, eight Danilo W2.52 precharge PEX instances and capacitive bitline residuals. "
                  + ("Ideal PCLK and PRECH stimuli; no explicit 6T access devices in this integration bench."
                     if args.phase_source == "ideal" else
                     ("PCLK and active-low PRECH are driven by the checked-in hierarchical Xschem SKY130 transistor-level phase source; external CLK and VALID_ACCESS_Q remain ideal sources, and no explicit 6T access devices are present."
                      if args.phase_source == "xschem-tapped-delay-chain" else
                      "PCLK and active-low PRECH are driven by an experimental transistor-level inverter-tap phase generator; external CLK and VALID_ACCESS_Q remain ideal sources, and no explicit 6T access devices are present."))),
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
                              "release_lead_screen": {
                                  "minimum_ps": args.release_lead_ps,
                                  "enforced_for": ("transistor-level phase-source modes"
                                                   if args.phase_source != "ideal" else
                                                   "not applied as a measured minimum in ideal mode"),
                                  "crossings": "PRECH rising 75% VDD to PCLK rising 50% VDD",
                              },
                              "release_lead_applies_to": (
                                  "initial_conditioning_and_access_pclk_rises" if args.phase_source == "ideal"
                                  else "valid access PCLK rise; the initial clock pulse is suppressed"),
                              "turnoff_guard_ps": args.turnoff_guard_ps,
                              "phase_source": args.phase_source,
                              "valid_access_q_delay_ps": args.valid_access_q_delay_ps,
                              "phase_source_xschem_transistor_audit": (
                                  {"hierarchy_mos_count": phase_source_info["hierarchy_mos_count"],
                                   "total_mos_count": phase_source_info["total_mos_count"],
                                   "delay_stages": phase_source_info["delay_stages"],
                                   "xschem_netlist_sha256": phase_source_info["netlist_sha256"],
                                   "active_subcircuit_sha256": phase_source_info[
                                       "active_subcircuit_sha256"],
                                   "phase_delay_sizing_um": phase_source_info[
                                       "phase_delay_sizing_um"]}
                                  if phase_source_info is not None else None),
                              "tapped_delay_stages": {
                                  "release": args.delay_release_stages,
                                  "evaluation": args.delay_evaluation_stages,
                                  "reassert": args.delay_reassert_stages},
                              "tapped_phase_equations": {
                                  "PCLK": "VALID_ACCESS_Q AND CLK AND DLY_EVALUATION",
                                  "PRECH": "VALID_ACCESS_Q AND ((CLK AND DLY_RELEASE) OR DLY_REASSERT)"},
                              "phase_chain_qualification": (
                                  "Not applicable to ideal PWL mode" if args.phase_source == "ideal" else
                                  ("Checked-in hierarchical Xschem SKY130 transistor-level source simulated against the selected decoder/WL/precharge PEX; no phase-source layout, PEX, captured qualifier, bitcell read/write path, or silicon timing signoff"
                                   if args.phase_source == "xschem-tapped-delay-chain" else
                                   "Exploratory SKY130 transistor-level delay chain only; no layout, PEX, captured qualifier, or silicon timing signoff")),
                              "valid_access_qualifier_model": (
                                  ("Access-vector-dependent ideal DC source in ideal mode; no delayed VALID_ACCESS_Q is modeled"
                                   if args.phase_source == "ideal" else
                                   "VALID_ACCESS_Q is an ideal PWL source rising at the access capture edge plus valid_access_q_delay_ps; this is an arrival-skew screen only, not a transistor-level capture or qualification circuit")),
                              "capture_to_pclk_target_interpretation": (
                                  "Requested ideal timing reference; tapped-delay mode stores the actual measured edge in each case result"),
                              "prime_pclk_rise_ns": (args.prime_pclk_rise_ns
                                                     if args.phase_source == "ideal" else None),
                              "initial_precharge_until_release_ns": (
                                  args.prime_pclk_rise_ns-args.release_lead_ps/1000.0
                                  if args.phase_source == "ideal" else None),
                              "tapped_startup_state": (
                                  "VALID_ACCESS_Q low suppresses the priming input-clock pulse; PCLK and PRECH remain low so decoder and bitlines stay precharged until the captured access edge"
                                  if args.phase_source != "ideal" else None),
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
                              args.turnoff_guard_ps, args.prime_pclk_rise_ns,
                              output, args.keep_raw, args.phase_source,
                              args.delay_release_stages, args.delay_evaluation_stages,
                              args.delay_reassert_stages,
                              phase_subcircuit=phase_subcircuit,
                              valid_access_q_delay_ps=args.valid_access_q_delay_ps)
        except Exception as exc:  # Keep completed cases and report exact failing case.
            result = {"case": case["label"], "status": "ERROR",
                      "error": f"{type(exc).__name__}: {exc}"}
        results.append(result)
        if result.get("status") == "ERROR":
            errors.append(result)
        checks.extend(result.get("checks", []))
        print(f"  {result.get('status')} phase_fail={result.get('phase_checks_fail', '')} "
              f"decoder_fail={result.get('decoder_logic_checks_fail', '')}", flush=True)

    write_csv(output / "summary.csv", [
        {key: value for key, value in row.items() if key not in {"checks", "terminals", "precharge_timing", "signal_nodes", "initial_precharge", "phase_source_timing"}}
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
