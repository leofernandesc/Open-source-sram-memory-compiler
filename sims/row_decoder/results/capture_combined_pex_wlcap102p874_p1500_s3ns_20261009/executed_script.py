#!/usr/bin/env python3
"""Check SKY130 DFF clock-to-Q timing against the dynamic decoder's PCLK.

The address launch waveforms come from the SKY130 hd-library Liberty tables for
dfxtp_1. Ngspice then evaluates the freshly netlisted B7 decoder and its four
existing WL buffers. PCLK rise is delayed from the CLK capture edge; its fall
remains aligned with the CLK falling edge, so the delay consumes high-phase
time instead of shifting the entire PCLK pulse.
"""
from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
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
CLK_FALL_PS = 20_000.0
PCLK_RISE_PS = 5_000.0
PCLK_FALL_PS = 10_000.0
INPUT_SLEW_NS = 0.0531329
LIBERTY_LOADS_PF = {"nominal": 0.003434554, "stress": 0.009001619}
LIBRARIES = {
    "tt": "sky130_fd_sc_hd__tt_025C_1v80.lib",
    "slow": "sky130_fd_sc_hd__ss_n40C_1v60.lib",
    "fast": "sky130_fd_sc_hd__ff_100C_1v65.lib",
}
SCRIPT_TEXT = Path(__file__).read_text()
SCRIPT_SHA256 = hashlib.sha256(SCRIPT_TEXT.encode()).hexdigest()
ROW_PEX_HELPER = ROOT / "sims/row_decoder/run_row_decoder_pex_contract.py"
WL_PEX_PATH = ROOT / "layout/wl_driver/pex/wl_driver_pex.spice"
WL_SOURCE_PATH = ROOT / "cells/wordline_driver/wl_driver.sch"
WL_LAYOUT_PATH = ROOT / "layout/wl_driver/wl_driver_flat.mag"
WL_EXT_PATH = ROOT / "layout/wl_driver/wl_driver_flat.ext"
WL_FLAT_NETLIST_PATH = ROOT / "layout/wl_driver/wl_driver_flat_extracted.spice"
CAPTURE_LITERAL_NODES: dict[str, str] = {}


def subckt_match(text: str, name: str):
    match = re.search(
        rf"(?ims)^\.subckt\s+{re.escape(name)}\s+([^\n]+)\n(.*?)^\.ends(?:\s+{re.escape(name)})?[^\n]*",
        text,
    )
    screen.require(match is not None, f"Missing .subckt {name}")
    return match


def wl_mos_signatures(body: str, ports: set[str]) -> Counter:
    """Canonicalize the WL buffer's four MOS devices across Xschem/Magic names."""
    lines = screen.logical_lines(body)
    raw_devices = []
    internal_aliases = set()
    for line in lines:
        tokens = line.split()
        if len(tokens) < 6 or not re.fullmatch(
                r"sky130_fd_pr__(?:n|p)fet_01v8", tokens[5], re.I):
            continue
        raw_devices.append((line, tokens))
        for node in tokens[1:5]:
            base = node.split(".", 1)[0].rstrip("#").upper()
            if base not in ports:
                internal_aliases.add(base)
    screen.require(len(raw_devices) == 4,
                   f"WL-driver netlist has {len(raw_devices)} MOS devices; expected four")
    screen.require(len(internal_aliases) == 1,
                   f"WL-driver netlist has unexpected internal nodes: {sorted(internal_aliases)}")

    signatures = Counter()
    for line, tokens in raw_devices:
        params = {key.lower(): value for key, value in re.findall(
            r"\b(\w+)\s*=\s*([^\s]+)", line)}
        screen.require("w" in params and "l" in params,
                       f"WL-driver MOS dimensions missing: {line}")
        screen.require(float(params.get("nf", "1")) == 1
                       and float(params.get("m", params.get("mult", "1"))) == 1,
                       f"WL-driver PEX audit supports only nf=1, m=1 devices: {line}")

        def canonical(node: str) -> str:
            base = node.split(".", 1)[0].rstrip("#").upper()
            return base if base in ports else "WL_N"

        drain, gate, source, bulk = [canonical(node) for node in tokens[1:5]]
        model = tokens[5].lower().replace("sky130_fd_pr__", "")
        width, length = round(float(params["w"]), 6), round(float(params["l"]), 6)
        signatures[(model, tuple(sorted((drain, source))), gate, bulk, width, length)] += 1
    return signatures


def validate_and_replace_wl_pex(netlist: str) -> tuple[str, dict]:
    """Replace the schematic WL leaf only after source/layout/PEX audits pass."""
    for path in (WL_SOURCE_PATH, WL_LAYOUT_PATH, WL_EXT_PATH,
                 WL_FLAT_NETLIST_PATH, WL_PEX_PATH):
        screen.require(path.is_file(), f"Required WL-driver PEX source is missing: {path}")
    source_match = subckt_match(netlist, "wl_driver")
    source_pins = source_match[1].split()
    source_pin_set = {pin.upper() for pin in source_pins}
    screen.require(len(source_pins) == 4 and source_pin_set == {"VDD", "VSS", "WL_IN", "WL"},
                   f"Unexpected current WL-driver interface: {source_pins}")

    pex_text = WL_PEX_PATH.read_text(encoding="utf-8")
    pex_match = subckt_match(pex_text, "wl_driver_flat")
    pex_pins = pex_match[1].split()
    screen.require(pex_pins == ["VDD", "VSS", "WL_IN", "WL"],
                   f"Unexpected WL-driver PEX pin contract: {pex_pins}")
    screen.require({pin.upper() for pin in pex_pins} == source_pin_set,
                   "WL-driver PEX and schematic interfaces differ")

    flat_text = WL_FLAT_NETLIST_PATH.read_text(encoding="utf-8")
    flat_match = subckt_match(flat_text, "wl_driver_flat")
    flat_pins = flat_match[1].split()
    screen.require(flat_pins == pex_pins,
                   f"WL extracted flat-netlist pin order differs from PEX: {flat_pins}")
    source_signatures = wl_mos_signatures(source_match[2], source_pin_set)
    flat_signatures = wl_mos_signatures(flat_match[2], source_pin_set)
    pex_signatures = wl_mos_signatures(pex_match[2], source_pin_set)
    screen.require(source_signatures == flat_signatures,
                   "WL extracted flat-netlist MOS topology/sizing differs from current Xschem")
    screen.require(source_signatures == pex_signatures,
                   "WL PEX MOS topology/sizing differs from current Xschem")

    pex_body_lines = screen.logical_lines(pex_match[2])
    resistors = [line for line in pex_body_lines if re.match(r"^R\S+\s", line, re.I)]
    capacitors = [line for line in pex_body_lines if re.match(r"^C\S+\s", line, re.I)]
    screen.require(resistors and capacitors,
                   "WL-driver PEX must contain both distributed R and C parasitics")
    negative_caps = []
    for line in capacitors:
        tokens = line.split()
        screen.require(len(tokens) >= 4, f"Malformed WL-driver capacitor: {line}")
        value = re.match(r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)[a-zA-Z]*$", tokens[3])
        screen.require(value is not None, f"Cannot parse WL-driver capacitor value: {line}")
        if float(value[1]) < 0:
            negative_caps.append(line)
    screen.require(not negative_caps,
                   "Refusing combined PEX simulation with negative WL-driver capacitance")

    # The Xschem symbol pins are ordered VDD, WL_IN, WL, VSS, while Magic's
    # extracted subcircuit is VDD, VSS, WL_IN, WL. Keep the top-level instances
    # untouched and expose the PEX body through the schematic's declared order.
    replacement = (f".subckt wl_driver {' '.join(source_pins)}\n"
                   + pex_match[2].rstrip() + "\n.ends wl_driver")
    replaced, count = re.subn(
        rf"(?ims)^\.subckt\s+wl_driver\s+[^\n]+\n.*?^\.ends(?:\s+wl_driver)?[^\n]*",
        lambda _: replacement, netlist, count=1,
    )
    screen.require(count == 1, "Could not replace the schematic WL-driver subcircuit")
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in (WL_SOURCE_PATH, WL_LAYOUT_PATH, WL_EXT_PATH,
                           WL_FLAT_NETLIST_PATH, WL_PEX_PATH)}
    evidence = {
        "subcircuit_pins_in_testbench_order": source_pins,
        "source_pins_in_xschem_order": source_pins,
        "pex_pins_in_magic_order": pex_pins,
        "pex_pin_order_adapted_without_changing_top_instances": True,
        "mos_devices": sum(pex_signatures.values()),
        "resistors": len(resistors),
        "capacitors": len(capacitors),
        "mos_signature_match_current_xschem_and_flat_extraction": True,
        "negative_capacitors": len(negative_caps),
        "sha256": hashes,
    }
    return replaced, evidence


def combined_pex_mos_instances(netlist: str, decoder_count: int = 29) -> dict:
    """Map all decoder and four hierarchical WL-PEX MOS terminals for bias checks."""
    top = screen.logical_lines(netlist.split("* expanding", 1)[0])
    result = {}
    for line in top:
        parts = line.split()
        if not parts or not parts[0].lower().startswith("x"):
            continue
        subckt = parts[-1].lower()
        if subckt not in {"row_decoder", "wl_driver"}:
            continue
        pins, body = screen.subcircuit(netlist, subckt)
        port_map = {pin.upper(): node.lower() for pin, node in zip(pins, parts[1:-1])}
        for instance in body:
            tokens = instance.split()
            if (len(tokens) < 6
                    or not re.fullmatch(r"sky130_fd_pr__(?:n|p)fet_01v8", tokens[5], re.I)):
                continue
            if not re.fullmatch(r"X\d+", tokens[0], re.I):
                continue
            terminals = [port_map.get(node.upper(),
                                      f"{parts[0].lower()}.{node.lower()}")
                         for node in tokens[1:5]]
            result[f"{parts[0].lower()}.{tokens[0][1:].lower()}"] = terminals
    screen.require(len(result) == decoder_count + 16,
                   f"Expected {decoder_count + 16} decoder/WL PEX MOS terminals; found {len(result)}")
    return result


def row_pex_literal_nodes(source_netlist: str, pex_text: str) -> dict[str, str]:
    """Locate the four address literals at their extracted inverter drain terminals."""
    source_match = subckt_match(source_netlist, "row_decoder")
    pex_match = subckt_match(pex_text, "row_decoder_flat")
    source_lines = screen.logical_lines(source_match[2])
    pex_lines = screen.logical_lines(pex_match[2])

    def signature(line: str) -> tuple:
        tokens = line.split()
        screen.require(len(tokens) >= 6 and re.fullmatch(
            r"sky130_fd_pr__(?:n|p)fet_01v8", tokens[5], re.I),
            f"Not a SKY130 core MOS line: {line}")
        params = {key.lower(): value for key, value in re.findall(
            r"\b(\w+)\s*=\s*([^\s]+)", line)}
        screen.require("w" in params and "l" in params,
                       f"MOS dimensions missing in literal mapping: {line}")
        nodes = [node.split(".", 1)[0].rstrip("#").upper() for node in tokens[1:5]]
        return (tokens[5].lower(), tuple(sorted((nodes[0], nodes[2]))),
                nodes[1], nodes[3], round(float(params["w"]), 6),
                round(float(params["l"]), 6))

    pex_by_signature: dict[tuple, list[list[str]]] = {}
    for line in pex_lines:
        tokens = line.split()
        if len(tokens) >= 6 and re.fullmatch(r"sky130_fd_pr__(?:n|p)fet_01v8", tokens[5], re.I):
            pex_by_signature.setdefault(signature(line), []).append(tokens)

    result = {}
    for output, device in (("A0B", "XM1"), ("A1B", "XM3"),
                           ("A0T", "XM26"), ("A1T", "XM28")):
        source = [line for line in source_lines if re.match(rf"^{device}\s", line, re.I)]
        screen.require(len(source) == 1, f"Cannot uniquely find {device} in current decoder source")
        candidates = pex_by_signature.get(signature(source[0]), [])
        screen.require(len(candidates) == 1,
                       f"Cannot uniquely map {device} ({output}) to the decoder PEX")
        pex_tokens = candidates[0]
        output_nodes = [node for node in pex_tokens[1:5]
                        if node.split(".", 1)[0].rstrip("#").upper() == output]
        screen.require(len(output_nodes) == 1,
                       f"Extracted {device} does not have one {output} drain/source terminal")
        result[output] = "x1." + output_nodes[0].lower()
    return result


def inject_combined_pex(netlist: str) -> tuple[str, dict]:
    """Inject current decoder and WL-driver PEX, then patch contract probes."""
    import run_row_decoder_pex_contract as decoder_pex

    decoder_pex.require_current_pex()
    decoder_pex.load_simulation_dependencies()
    decoder_pex.SOURCE_NETLIST = netlist
    decoder_pex.SOURCE_NODES, decoder_pex.SOURCE_DEVICES = decoder_pex.ORIGINAL_INSPECT(netlist, True)
    decoder_pins, _ = screen.subcircuit(netlist, "row_decoder")
    decoder_pex.SOURCE_DEVICES["__pins__"] = decoder_pins
    row_pex_text = decoder_pex.PEX_PATH.read_text(encoding="utf-8")
    netlist, row_counts, gate_nodes, dynamic_segments = decoder_pex.inject_pex(netlist, row_pex_text)
    netlist, wl_evidence = validate_and_replace_wl_pex(netlist)
    decoder_pex.PEX_COUNTS = row_counts
    decoder_pex.PEX_DYNAMIC_NODES = gate_nodes
    decoder_pex.PEX_DYNAMIC_SEGMENTS = dynamic_segments
    global CAPTURE_LITERAL_NODES, read_raw
    CAPTURE_LITERAL_NODES = row_pex_literal_nodes(
        decoder_pex.SOURCE_NETLIST, row_pex_text)

    screen.inspect_netlist = decoder_pex.inspect_netlist
    contract.mos_instances = combined_pex_mos_instances
    contract.make_deck = decoder_pex.make_deck
    contract.read_raw = decoder_pex.read_raw
    contract.analyze = decoder_pex.analyze
    read_raw = decoder_pex.read_raw
    return netlist, {
        "row_decoder": {
            "pex_sha256": hashlib.sha256(decoder_pex.PEX_PATH.read_bytes()).hexdigest(),
            "counts": row_counts,
            "dynamic_gate_nodes": gate_nodes,
            "dynamic_segment_nodes": {str(key): sorted(value)
                                       for key, value in dynamic_segments.items()},
            "capture_literal_nodes": CAPTURE_LITERAL_NODES,
        },
        "wl_driver": wl_evidence,
        "topology_scope": "Current decoder R-C PEX and four hierarchical WL-driver R-C PEX instances; 102.873935496 fF full-row Ceff remains an explicit lumped output load per WL.",
    }


def extract_group(text: str, pattern: str) -> str:
    match = re.search(pattern + r"\s*\{", text, re.I | re.S)
    screen.require(match is not None, f"Missing Liberty group: {pattern}")
    start = match.end()
    depth = 1
    index = start
    while depth:
        screen.require(index < len(text), f"Unterminated Liberty group: {pattern}")
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
        index += 1
    return text[start:index - 1]


def group_list(text: str, name: str) -> list[str]:
    pattern = re.compile(rf"\b{re.escape(name)}\s*\([^)]*\)\s*\{{", re.I | re.S)
    result = []
    for match in pattern.finditer(text):
        start = match.end()
        depth = 1
        index = start
        while depth:
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
            index += 1
        result.append(text[start:index - 1])
    return result


def index_values(body: str, key: str) -> list[float]:
    match = re.search(rf"\b{key}\s*\(\s*\"([^\"]+)\"\s*\)", body, re.I | re.S)
    screen.require(match is not None, f"Missing Liberty {key}")
    return [float(value) for value in match[1].split(",")]


def table_data(body: str, name: str) -> tuple[list[float], list[float], np.ndarray]:
    table = extract_group(body, rf"{re.escape(name)}\s*\([^)]*\)")
    first, second = index_values(table, "index_1"), index_values(table, "index_2")
    values = re.search(r"\bvalues\s*\((.*?)\)\s*;", table, re.I | re.S)
    screen.require(values is not None, f"Missing values for Liberty table {name}")
    flat = [float(x) for x in re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", values[1])]
    screen.require(len(flat) == len(first) * len(second), f"Unexpected dimensions in Liberty table {name}")
    return first, second, np.asarray(flat).reshape(len(first), len(second))


def interpolate(x: list[float], y: list[float], values: np.ndarray,
                xq: float, yq: float) -> float:
    screen.require(x[0] <= xq <= x[-1] and y[0] <= yq <= y[-1],
                   "Requested slew/load is outside the Liberty table")
    along_y = np.asarray([np.interp(yq, y, row) for row in values])
    return float(np.interp(xq, x, along_y))


def liberty_arc(path: Path, load_pf: float) -> dict:
    text = path.read_text(errors="strict")
    cell = extract_group(text, r"cell\s*\(\s*\"sky130_fd_sc_hd__dfxtp_1\"\s*\)")
    qpin = extract_group(cell, r"pin\s*\(\s*\"Q\"\s*\)")
    arcs = [arc for arc in group_list(qpin, "timing")
            if re.search(r'\brelated_pin\s*:\s*"CLK"', arc)
            and re.search(r'\btiming_type\s*:\s*"rising_edge"', arc)]
    screen.require(len(arcs) == 1, f"Expected one rising CLK-to-Q arc in {path.name}")
    arc = arcs[0]
    delay_r = table_data(arc, "cell_rise")
    delay_f = table_data(arc, "cell_fall")
    slew_r = table_data(arc, "rise_transition")
    slew_f = table_data(arc, "fall_transition")
    values = {
        "clock_to_q_rise_ns": interpolate(*delay_r, INPUT_SLEW_NS, load_pf),
        "clock_to_q_fall_ns": interpolate(*delay_f, INPUT_SLEW_NS, load_pf),
        "q_rise_transition_ns": interpolate(*slew_r, INPUT_SLEW_NS, load_pf),
        "q_fall_transition_ns": interpolate(*slew_f, INPUT_SLEW_NS, load_pf),
    }
    operating = re.search(r'operating_conditions\s*\(\s*"[^"]+"\s*\)\s*\{.*?'
                          r'voltage\s*:\s*([^;]+);.*?temperature\s*:\s*([^;]+);', text, re.I | re.S)
    screen.require(operating is not None, f"No operating condition in {path.name}")
    values.update(library=path.name, voltage_v=float(operating[1]),
                  temperature_c=float(operating[2]), input_slew_ns=INPUT_SLEW_NS,
                  output_load_pf=load_pf)
    return values


def pwl(initial: float, transitions: list[tuple[float, float, float]], stop: float) -> str:
    return contract.pwl(initial, transitions, stop)


def q_waveform(old_bit: int, new_bit: int, vdd: float, capture_s: float,
               delay_ns: float, transition_ns: float, lower_pct: float,
               upper_pct: float, stop_s: float) -> str:
    initial, target = old_bit * vdd, new_bit * vdd
    if old_bit == new_bit:
        return pwl(initial, [], stop_s)
    fraction = (upper_pct - lower_pct) / 100.0
    ramp_s = transition_ns * 1e-9 / fraction
    center = capture_s + delay_ns * 1e-9
    return pwl(initial, [(center - ramp_s / 2, center + ramp_s / 2, target)], stop_s)


def top_pin_map(netlist: str) -> dict[str, str]:
    top = screen.logical_lines(netlist.split("* expanding", 1)[0])
    instance = next((line.split() for line in top if line.lower().startswith("x1 ")), None)
    screen.require(instance is not None, "Missing top-level row_decoder instance x1")
    pins, _ = screen.subcircuit(netlist, "row_decoder")
    return dict(zip(pins, instance[1:-1]))


def load_wl_capacitance_evidence(path: Path | None, requested_ff: float) -> dict:
    if path is None:
        return {"path": None, "sha256": None, "rows": None,
                "measured_max_ff": None, "interpretation": "load supplied as an explicit simulation parameter"}
    path = path.resolve()
    screen.require(path.is_file(), f"Wordline capacitance evidence not found: {path}")
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    expected_cases = {
        (corner, vdd, temp, state)
        for corner in ("tt", "ff", "ss", "fs", "sf")
        for vdd in ("1.62", "1.8")
        for temp in ("-40.0", "27.0", "125.0")
        for state in ("0", "1")
    }
    observed_cases = {
        (row.get("corner", "").lower(), row.get("vdd_v", ""),
         row.get("temp_c", ""), row.get("state", ""))
        for row in rows
    }
    screen.require(len(rows) == 60 and observed_cases == expected_cases,
                   f"Expected the complete 60-case 5-corner WL capacitance matrix: {path}")
    screen.require(all(row.get("status") == "PASS" for row in rows),
                   f"Wordline capacitance evidence contains non-PASS rows: {path}")
    try:
        values = [float(row["cwl_pex_ff"]) for row in rows]
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid cwl_pex_ff data in {path}") from exc
    maximum = max(values)
    screen.require(math.isfinite(requested_ff) and abs(maximum-requested_ff) <= 5e-7,
                   f"Requested WL load {requested_ff:g} fF does not match evidence maximum {maximum:.9f} fF")
    pex_hashes = {row.get("pex_netlist_sha256", "") for row in rows}
    screen.require(len(pex_hashes) == 1 and "" not in pex_hashes,
                   f"WL capacitance matrix must identify one source PEX hash: {path}")
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "rows": len(rows), "measured_max_ff": maximum,
            "source_pex_sha256": next(iter(pex_hashes)),
            "interpretation": "maximum extracted 8-bit physical-row Ceff across the supplied PVT/state table"}


def make_deck(netlist: str, case: dict, model: Path, arc: dict,
              load_label: str, wl_cap_ff: float) -> tuple[str, dict, dict, dict, dict, dict]:
    phase_ps = float(case["capture_to_pclk_ps"])
    clk_fall_ps = float(case.get("clk_fall_ps", CLK_FALL_PS))
    screen.require(phase_ps >= 0 and phase_ps < clk_fall_ps - CAPTURE_PS,
                   "PCLK phase must leave positive high-phase time")
    low_ns = (15_000.0 + phase_ps - PCLK_FALL_PS) / 1000.0
    high_ns = (clk_fall_ps - (15_000.0 + phase_ps)) / 1000.0
    settling_ns = float(case.get("settling_allowance_ns", 1.0))
    screen.require(math.isfinite(settling_ns) and 0 < settling_ns < high_ns,
                   "Settling allowance must be positive and shorter than the PCLK high phase")
    sim_case = {
        **case, "campaign": "timing", "low_ns": low_ns, "high_ns": high_ns,
        "settling_allowance_ns": settling_ns,
        "lead_ps": 2000, "address_ps": 50,
        "rise_ps": 25, "fall_ps": 25, "step_ps": 1,
        "method": "gear", "minbreak_fs": 1, "chgtol_c": 1e-18,
    }
    deck, nodes, devices, terminals, schedule = contract.make_deck(netlist, sim_case, model)
    deck, count = re.subn(
        r"(?im)^(C_WL[0-3]\s+\S+\s+\S+)\s+\S+",
        lambda match: f"{match.group(1)} {wl_cap_ff*1e-15:.14g}", deck,
    )
    screen.require(count == 4, f"Expected four WL load capacitors, replaced {count}")
    ports = top_pin_map(netlist)
    vdd, stop_s = float(schedule["vdd"]), float(schedule["stop"])
    lower = float(case["slew_lower_pct"])
    upper = float(case["slew_upper_pct"])
    cap50 = CAPTURE_PS * 1e-12
    for bit, name, pin in ((0, "VA0", "A0"), (1, "VA1", "A1")):
        old_bit = (int(case["old"]) >> bit) & 1
        new_bit = (int(case["new"]) >> bit) & 1
        delay_key = "clock_to_q_rise_ns" if new_bit else "clock_to_q_fall_ns"
        slew_key = "q_rise_transition_ns" if new_bit else "q_fall_transition_ns"
        waveform = q_waveform(old_bit, new_bit, vdd, cap50, arc[delay_key], arc[slew_key],
                              lower, upper, stop_s)
        pattern = rf"(?im)^{name}\s+\S+\s+\S+\s+[^\n]+$"
        deck, count = re.subn(pattern, f"{name} {ports[pin]} GND {waveform}", deck, count=1)
        screen.require(count == 1, f"Expected one Xschem source for {pin}")

    input_ramp_s = INPUT_SLEW_NS * 1e-9 / ((upper - lower) / 100.0)
    clock = pwl(0.0, [(cap50-input_ramp_s/2, cap50+input_ramp_s/2, vdd),
                      (clk_fall_ps*1e-12-input_ramp_s/2,
                       clk_fall_ps*1e-12+input_ramp_s/2, 0.0)], stop_s)
    deck = deck.replace(".lib ", f"VCAPCLK CAPCLK GND {clock}\n.lib ", 1)
    deck, count = re.subn(r"(?im)^(\.save\s+[^\n]+)$", r"\1 v(CAPCLK)", deck, count=1)
    screen.require(count == 1, "Could not add CLK capture marker to the save list")
    schedule["second_fall"] = clk_fall_ps * 1e-12
    schedule["second_rise"] = (CAPTURE_PS + phase_ps) * 1e-12
    schedule["stop"] = float(schedule["second_fall"] + 5e-9)
    return deck, nodes, devices, terminals, schedule, sim_case


def trace(raw: dict[str, np.ndarray], node: str) -> np.ndarray:
    key = node.lower()
    if not key.startswith("v("):
        key = f"v({key})"
    screen.require(key in raw, f"Missing saved waveform {key}")
    return raw[key]


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
    delta = signal[i + 1] - signal[i]
    return float(time[i] if delta == 0 else time[i] + (threshold-signal[i])*(time[i+1]-time[i])/delta)


def edge_metrics(raw: dict[str, np.ndarray], case: dict, nodes: dict,
                 terminals: dict, ports: dict, arc: dict, vdd: float,
                 pex_literal_nodes: dict[str, str] | None = None) -> dict:
    time = raw["time"]
    capture = crossing(time, trace(raw, "CAPCLK"), 0.5*vdd, True,
                       (CAPTURE_PS-200)*1e-12, (CAPTURE_PS+200)*1e-12)
    pclk = crossing(time, trace(raw, nodes["PCLK"]), 0.5*vdd, True, 10e-9, time[-1])
    screen.require(capture is not None and pclk is not None, "Missing capture or PCLK crossing")
    previous, target = int(case["old"]), int(case["new"])
    settles = {}
    q_delays = {}
    for bit, name, pin in ((0, "A0", "A0"), (1, "A1", "A1")):
        old_bit, new_bit = (previous >> bit)&1, (target >> bit)&1
        if old_bit == new_bit:
            settles[name] = capture
            q_delays[name] = ""
            continue
        rising = bool(new_bit)
        y = trace(raw, ports[pin])
        q50 = crossing(time, y, 0.5*vdd, rising, capture, pclk+2e-9)
        q90 = crossing(time, y, (0.9 if rising else 0.1)*vdd, rising, capture, pclk+2e-9)
        screen.require(q50 is not None and q90 is not None, f"{name} did not reach its captured value")
        q_delays[name] = (q50-capture)*1e12
        settles[name] = q90
    for name, device, literal in (("A0B", "M1", 1-(target&1)),
                                  ("A0T", "M26", target&1),
                                  ("A1B", "M3", 1-((target>>1)&1)),
                                  ("A1T", "M28", (target>>1)&1)):
        node = (pex_literal_nodes[name] if pex_literal_nodes is not None
                else terminals["x1."+device.lower()][0])
        raw_bit = (target & 1) if name.startswith("A0") else ((target >> 1) & 1)
        old_raw = (previous & 1) if name.startswith("A0") else ((previous >> 1) & 1)
        old_literal = 1-old_raw if name.endswith("B") else old_raw
        if literal == old_literal:
            settles[name] = capture
            continue
        rising = bool(literal)
        y = trace(raw, node)
        q90 = crossing(time, y, (0.9 if rising else 0.1)*vdd, rising, capture, pclk+2e-9)
        screen.require(q90 is not None, f"{name} did not reach its captured value")
        settles[name] = q90
    q_settle = max(settles[name] for name in ("A0", "A1"))
    literal_settle = max(settles.values())
    actual_phase = (pclk-capture)*1e12
    return {
        "capture_to_pclk50_ps": actual_phase,
        "capture_to_pclk_target_ps": float(case["capture_to_pclk_ps"]),
        "pclk_phase_error_ps": actual_phase-float(case["capture_to_pclk_ps"]),
        "a0_clk_to_q50_ps": q_delays["A0"], "a1_clk_to_q50_ps": q_delays["A1"],
        "latest_q_10_90_settle_ps": (q_settle-capture)*1e12,
        "q_settle_lead_to_pclk_ps": (pclk-q_settle)*1e12,
        "latest_literal_10_90_settle_ps": (literal_settle-capture)*1e12,
        "literal_settle_lead_to_pclk_ps": (pclk-literal_settle)*1e12,
        "pclk_high_phase_ps": (float(case.get("clk_fall_ps", CLK_FALL_PS))
                               -CAPTURE_PS-float(case["capture_to_pclk_ps"])),
        "dff_load_label": case["dff_load_label"],
        "dff_load_ff": float(case["dff_load_pf"])*1000,
        "dff_liberty": case["dff_liberty"],
        "dff_clk_to_q_rise_ps": arc["clock_to_q_rise_ns"]*1000,
        "dff_clk_to_q_fall_ps": arc["clock_to_q_fall_ns"]*1000,
        "dff_q_rise_transition_ps": arc["q_rise_transition_ns"]*1000,
        "dff_q_fall_transition_ps": arc["q_fall_transition_ns"]*1000,
    }


def execute_case(case: dict, netlist: str, model: Path, lib_arcs: dict,
                 lower: float, upper: float, guard_ps: float, environment_sha256: str,
                 wl_cap_ff: float, out_dir: Path, keep_raw: bool) -> dict:
    arc = lib_arcs[case["profile"]][case["dff_load_label"]]
    case = {**case, "slew_lower_pct": lower, "slew_upper_pct": upper}
    deck, nodes, devices, terminals, schedule, sim_case = make_deck(netlist, case, model, arc,
                                                                    case["dff_load_label"], wl_cap_ff)
    deck_hash = hashlib.sha256((deck + "\n" + environment_sha256).encode()).hexdigest()
    out_dir.mkdir(parents=True, exist_ok=True)
    deck_path = (out_dir / "case.spice").resolve()
    log_path = out_dir / "ngspice.log"
    raw_path = out_dir / "waveform.raw"
    cached_path = out_dir / "case.json"
    if cached_path.is_file():
        cached = json.loads(cached_path.read_text())
        if (cached.get("deck_sha256") == deck_hash
                and cached.get("environment_sha256") == environment_sha256
                and cached.get("status") != "ERROR"):
            return cached
    deck_path.write_text(deck)
    raw_path.unlink(missing_ok=True)
    proc = subprocess.run(["ngspice", "-n", "-b", str(deck_path)], cwd=out_dir,
                          capture_output=True, text=True, timeout=180)
    log = proc.stdout + proc.stderr
    log_path.write_text(log)
    if proc.returncode or re.search(r"Error:|failed!|aborted|timestep too small", log, re.I) or not raw_path.is_file():
        result = {"case": case["label"], "status": "ERROR", "deck_sha256": deck_hash,
                  "environment_sha256": environment_sha256,
                  "ngspice_returncode": proc.returncode,
                  "error": "ngspice failed or produced no complete waveform"}
        cached_path.write_text(json.dumps(result, indent=2)+"\n")
        return result
    raw = read_raw(raw_path)
    run, checks, extrema = contract.analyze(raw, sim_case, nodes, devices, terminals, schedule)
    arc_metrics = edge_metrics(raw, case, nodes, terminals, top_pin_map(netlist), arc,
                               float(schedule["vdd"]),
                               CAPTURE_LITERAL_NODES if CAPTURE_LITERAL_NODES else None)
    logic_pass = run["check_fail"] == 0
    voltage_pass = run["model_upper_result"] == "PASS" and run["magnitude_result"] == "PASS"
    timing_pass = logic_pass and voltage_pass and arc_metrics["literal_settle_lead_to_pclk_ps"] >= guard_ps
    result = {
        "case": case["label"], "profile": case["profile"], "corner": run["corner"],
        "vdd_v": run["vdd_v"], "temperature_c": run["temperature_c"],
        "old_address": case["old"], "new_address": case["new"],
        **arc_metrics, "logic_pass": logic_pass, "voltage_screen_pass": voltage_pass,
        "qualification_pass": logic_pass and voltage_pass,
        "timing_contract_pass": timing_pass, "required_literal_guard_ps": guard_ps,
        "logic_checks_pass": run["check_pass"], "logic_checks_fail": run["check_fail"],
        "terminal_magnitude_max_v": run["terminal_magnitude_max_v"],
        "terminal_magnitude_device": run["terminal_magnitude_device"],
        "terminal_magnitude_voltage": run["terminal_magnitude_voltage"],
        "wl_delay90_ps": run["wl_delay90_ps"], "dec_delay90_ps": run["dec_delay90_ps"],
        "status": "PASS" if logic_pass and voltage_pass else "REJECTED_TIMING_OR_VOLTAGE",
        "deck_sha256": deck_hash, "environment_sha256": environment_sha256,
        "ngspice_returncode": proc.returncode,
        "checks": checks, "terminals": extrema,
    }
    cached_path.write_text(json.dumps(result, indent=2)+"\n")
    if not keep_raw:
        raw_path.unlink(missing_ok=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--profiles", nargs="+", choices=tuple(LIBRARIES), default=["tt", "slow", "fast"])
    parser.add_argument("--phase-ps", nargs="+", type=float,
                        default=[0, 250, 500, 750, 1000, 1250, 1500, 2000])
    parser.add_argument("--transitions", nargs="+", metavar="OLD:NEW",
                        help="Address transitions to run, for example 0:3 3:0; default runs all 12")
    parser.add_argument("--loads", nargs="+", choices=tuple(LIBERTY_LOADS_PF),
                        default=["nominal", "stress"])
    parser.add_argument("--workers", type=int, choices=(1, 2, 4), default=2)
    parser.add_argument("--internal-guard-ps", type=float, default=250.0,
                        help="Required literal-settling margin before PCLK evaluation")
    parser.add_argument("--wl-cap-ff", type=float, default=17.4,
                        help="Capacitance on each simulated wordline (default: historical 17.4 fF)")
    parser.add_argument("--wl-load-evidence-csv", type=Path,
                        help="Optional PVT table; its maximum cwl_pex_ff must equal --wl-cap-ff")
    parser.add_argument("--settling-allowance-ns", type=float, default=1.0,
                        help="Output settling window (default: historical 1 ns screen)")
    parser.add_argument("--clk-fall-ps", type=float, default=CLK_FALL_PS,
                        help="Captured clock falling edge in ps (default: 20000 ps)")
    parser.add_argument("--post-layout-pex", action="store_true",
                        help="Use current decoder and four WL-driver Magic R-C PEX subcircuits")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--keep-raw", action="store_true")
    args = parser.parse_args()
    screen.require(args.resume or not args.output_dir.exists(), "Use a new output directory or --resume")
    args.output_dir.mkdir(parents=True, exist_ok=args.resume)
    pdk = Path(os.environ.get("PDK_ROOT", "/opt/pdks")) / "sky130A"
    model = pdk / "libs.tech/combined/continuous/sky130.lib.spice"
    lib_dir = pdk / "libs.ref/sky130_fd_sc_hd/lib"
    libs = {profile: lib_dir / LIBRARIES[profile] for profile in args.profiles}
    screen.require(model.is_file() and all(path.is_file() for path in libs.values()),
                   "SKY130A transistor or selected Liberty timing model not found")
    lib_text = {profile: path.read_text(errors="strict") for profile, path in libs.items()}
    lower = float(re.search(r"slew_lower_threshold_pct_rise\s*:\s*([\d.]+)", lib_text[args.profiles[0]])[1])
    upper = float(re.search(r"slew_upper_threshold_pct_rise\s*:\s*([\d.]+)", lib_text[args.profiles[0]])[1])
    screen.require(lower < upper, "Invalid Liberty slew thresholds")
    screen.require(math.isfinite(args.internal_guard_ps) and args.internal_guard_ps >= 0,
                   "Internal timing guard must be finite and nonnegative")
    screen.require(math.isfinite(args.wl_cap_ff) and args.wl_cap_ff > 0,
                   "WL capacitance must be finite and positive")
    screen.require(math.isfinite(args.settling_allowance_ns) and args.settling_allowance_ns > 0,
                   "Settling allowance must be finite and positive")
    screen.require(math.isfinite(args.clk_fall_ps) and args.clk_fall_ps > CAPTURE_PS,
                   "Clock falling edge must occur after the address capture edge")
    screen.require(all(args.settling_allowance_ns < (args.clk_fall_ps-CAPTURE_PS-phase)/1000
                       for phase in args.phase_ps),
                   "Settling allowance must be shorter than every PCLK high phase")
    wl_load_evidence = load_wl_capacitance_evidence(args.wl_load_evidence_csv, args.wl_cap_ff)
    lib_arcs = {profile: {label: liberty_arc(path, load)
                          for label, load in LIBERTY_LOADS_PF.items() if label in args.loads}
                for profile, path in libs.items()}
    with tempfile.TemporaryDirectory(prefix="decoder-capture-netlist-") as temp:
        netlist = contract.netlist_current(Path(temp))
    pex_evidence = None
    if args.post_layout_pex:
        netlist, pex_evidence = inject_combined_pex(netlist)
    _, devices = screen.inspect_netlist(netlist, True)
    screen.require(len(devices) == 29, "Capture timing study requires retained B7 decoder")
    netlist_sha = hashlib.sha256(netlist.encode()).hexdigest()
    transitions = [(old, new) for old in range(4) for new in range(4) if old != new]
    if args.transitions:
        transitions = []
        for item in args.transitions:
            match = re.fullmatch(r"([0-3]):([0-3])", item)
            screen.require(match is not None and match[1] != match[2],
                           f"Invalid non-repeat address transition {item!r}")
            transitions.append((int(match[1]), int(match[2])))
        screen.require(len(transitions) == len(set(transitions)), "Duplicate address transitions")
    cases = []
    for profile in args.profiles:
        for load_label in args.loads:
            for old, new in transitions:
                for phase in args.phase_ps:
                    label = (f"{profile}_{load_label}_wl{args.wl_cap_ff:g}fF_a{old}_to_{new}"
                             f"_p{phase:g}ps_s{args.settling_allowance_ns:g}ns")
                    cases.append({"label": label, "profile": profile, "old": old, "new": new,
                                  "capture_to_pclk_ps": phase, "dff_load_label": load_label,
                                  "clk_fall_ps": args.clk_fall_ps,
                                  "settling_allowance_ns": args.settling_allowance_ns,
                                  "wl_cap_ff": args.wl_cap_ff,
                                  "wl_load_evidence_sha256": wl_load_evidence["sha256"],
                                  "dff_load_pf": LIBERTY_LOADS_PF[load_label],
                                  "dff_liberty": lib_arcs[profile][load_label]["library"]})
    screen.require(len(cases) == len({case["label"] for case in cases}), "Duplicate case labels")
    manifest_path = args.output_dir / "manifest.json"
    previous = None
    if args.resume:
        screen.require(manifest_path.is_file(), "No campaign manifest to resume")
        previous = json.loads(manifest_path.read_text())
        screen.require(previous.get("cases") == cases and previous.get("netlist_sha256") == netlist_sha,
                       "Resume requires identical cases and fresh Xschem source")
    (args.output_dir / "executed_script.py").write_text(SCRIPT_TEXT)
    model_hashes = contract.model_dependencies(model)
    for path in libs.values():
        model_hashes[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
    model_hashes = dict(sorted(model_hashes.items()))
    tools = {"xschem": screen.tool_version("xschem"), "ngspice": screen.tool_version("ngspice")}
    helpers = {"contract": contract.SCRIPT_HASH,
               "netlist_audit": hashlib.sha256(Path(screen.__file__).read_bytes()).hexdigest(),
               "raw_reader": hashlib.sha256(Path(__file__).with_name("plot_row_decoder_review.py").read_bytes()).hexdigest()}
    if args.post_layout_pex:
        helpers.update({
            "decoder_pex_helper": hashlib.sha256(ROW_PEX_HELPER.read_bytes()).hexdigest(),
            "wl_driver_pex": pex_evidence["wl_driver"]["sha256"][str(WL_PEX_PATH.relative_to(ROOT))],
            "wl_driver_source": pex_evidence["wl_driver"]["sha256"][str(WL_SOURCE_PATH.relative_to(ROOT))],
        })
    environment_sha256 = hashlib.sha256(json.dumps(
        dict(models=model_hashes, tools=tools, helpers=helpers, script=SCRIPT_SHA256),
        sort_keys=True).encode()).hexdigest()
    if previous:
        screen.require(previous.get("environment_sha256") == environment_sha256,
                       "Resume requires identical PDK, Liberty, script, helper and tool hashes")
    manifest = {
        "campaign": "row_decoder_capture_to_pclk",
        "stage": "post-layout-combined-pex" if args.post_layout_pex else "pre-layout",
        "complete": False,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "candidate": ("B7 dynamic decoder R-C PEX plus four WL-driver R-C PEX instances"
                      if args.post_layout_pex else
                      "B7 dynamic decoder plus four original WL buffers"),
        "address_launch_model": "SKY130 FD SC HD dfxtp_1 Liberty clock-to-Q and transition tables; Q is a PWL launch waveform",
        "clock_to_q_thresholds": "CLK and Q 50 percent thresholds",
        "output_transition_thresholds_percent": [lower, upper],
        "liberty_input_slew_ns": INPUT_SLEW_NS,
        "liberty_output_loads_pf": LIBERTY_LOADS_PF,
        "address_dff_load_interpretation": "Liberty lookup points: 3.434554 fF nominal and 9.001619 fF stress; actual captured-address Q-pin fanout has not been extracted yet.",
        "capture_clock_edge_ps": CAPTURE_PS, "clk_fall_ps": CLK_FALL_PS,
        "actual_clk_fall_ps": args.clk_fall_ps,
        "pclk_fall_behavior": "PCLK fall remains at CLK falling edge; capture-to-PCLK delay shortens PCLK high phase",
        "wordline_load": {"capacitance_per_wl_ff": args.wl_cap_ff,
                          "evidence": wl_load_evidence,
                          "placement": ("lumped full-row Ceff capacitor from each WL output to VSS; decoder and WL-driver local parasitics are represented by their current R-C PEX"
                                        if args.post_layout_pex else
                                        "lumped capacitor from each WL output to VSS; decoder and WL driver remain schematic")},
        "timing_criteria": "B7 full waveform checks; unselected DEC/WL below 10 percent VDD, selected reaches 90 percent and the declared settling allowance",
        "settling_allowance_ns": args.settling_allowance_ns,
        "literal_settling_guard_ps": args.internal_guard_ps,
        "literal_settling_guard_basis": "Experimental engineering margin; requires raw address and all regenerated/complemented literals to settle before PCLK, then retains this guard",
        "external_setup_hold": "Not measured; address register D setup/hold and capture-cell metastability are outside this capture-to-PCLK study",
        "pdk_liberty_files": {profile: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                        "arc_at_load": lib_arcs[profile]}
                              for profile, path in libs.items()},
        "profiles": {profile: contract.PROFILES[profile] for profile in args.profiles},
        "cases": cases, "netlist_sha256": netlist_sha,
        "canonical_decoder_sha256": hashlib.sha256((ROOT/"cells/row_decoder/row_decoder.sch").read_bytes()).hexdigest(),
        "script_sha256": SCRIPT_SHA256, "model_dependencies_sha256": model_hashes,
        "helper_sha256": helpers, "environment_sha256": environment_sha256, "tools": tools,
        "workers": args.workers,
        "modeling_attempt_note": "A direct dfxtp_1 SPICE subckt mixed with continuous MOS models failed model resolution; those runs are excluded. Liberty table-driven Q waveforms are used here.",
    }
    if pex_evidence is not None:
        manifest["post_layout_pex_sources"] = pex_evidence
    manifest_path.write_text(json.dumps(manifest, indent=2)+"\n")
    if pex_evidence is not None:
        (args.output_dir / "simulation_input_netlist.spice").write_text(netlist, encoding="utf-8")
    cases_dir = args.output_dir / "cases"
    cases_dir.mkdir(exist_ok=True)
    results, errors = [], []
    def work(case: dict):
        try:
            return execute_case(case, netlist, model, lib_arcs, lower, upper, args.internal_guard_ps,
                                environment_sha256, args.wl_cap_ff,
                                cases_dir/case["label"], args.keep_raw), None
        except Exception as exc:
            return None, {"case": case["label"], "error": f"{type(exc).__name__}: {exc}"}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for idx, (result, error) in enumerate(pool.map(work, cases), 1):
            if error:
                errors.append(error)
                print(json.dumps(error), flush=True)
            else:
                results.append(result)
            if idx % 24 == 0 or idx == len(cases):
                print(f"capture-to-PCLK: {idx}/{len(cases)} cases completed", flush=True)
    summary = [{key: value for key, value in result.items() if key not in {"checks", "terminals"}}
               for result in results]
    if summary:
        screen.write_csv(args.output_dir/"summary.csv", summary)
        screen.write_csv(args.output_dir/"checks.csv", [row for result in results for row in result["checks"]])
        screen.write_csv(args.output_dir/"terminals.csv", [row for result in results for row in result["terminals"]])
    (args.output_dir/"errors.json").write_text(json.dumps(errors, indent=2)+"\n")
    complete = not errors and len(results) == len(cases)
    if pex_evidence is not None:
        import run_row_decoder_pex_contract as decoder_pex
        decoder_pex.require_current_pex()
        current_row_pex = hashlib.sha256(decoder_pex.PEX_PATH.read_bytes()).hexdigest()
        current_wl_pex = hashlib.sha256(WL_PEX_PATH.read_bytes()).hexdigest()
        screen.require(current_row_pex == pex_evidence["row_decoder"]["pex_sha256"],
                       "Decoder PEX changed during the combined capture campaign")
        screen.require(current_wl_pex == pex_evidence["wl_driver"]["sha256"][
            str(WL_PEX_PATH.relative_to(ROOT))],
            "WL-driver PEX changed during the combined capture campaign")
    manifest.update(complete=complete, completed_cases=len(results), errors=errors,
                    qualification_pass_cases=sum(bool(row.get("qualification_pass")) for row in results),
                    qualification_rejected_cases=sum(not bool(row.get("qualification_pass")) for row in results),
                    timing_contract_pass_cases=sum(bool(row.get("timing_contract_pass")) for row in results),
                    timing_contract_rejected_cases=sum(not bool(row.get("timing_contract_pass")) for row in results),
                    finished_utc=datetime.now(timezone.utc).isoformat())
    manifest_path.write_text(json.dumps(manifest, indent=2)+"\n")
    return 2 if not complete else 0


if __name__ == "__main__":
    raise SystemExit(main())
