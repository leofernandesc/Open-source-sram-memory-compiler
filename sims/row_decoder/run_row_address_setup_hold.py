#!/usr/bin/env python3
"""Screen setup/hold behavior of each captured row-address input in SKY130 SPICE.

The testbench-only single-bit wrapper is generated from the two dfxtp_1
instances in the freshly netlisted row_address_capture.sch. Each bit and each
data transition polarity is swept around a rising CLK edge in TT, SS, and FF.
This is an exploratory transistor-level screen, not metastability or signoff
characterization.
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

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sims/row_decoder"))

import run_row_decoder_capture_timing as capture
import run_valid_access_capture_spice as isolated

PDK_ROOT = Path(os.environ.get("PDK_ROOT", "/opt/pdks")) / "sky130A"
MODEL_LIBRARY = PDK_ROOT / "libs.tech/ngspice/sky130.lib.spice"
SC_LIBRARY = PDK_ROOT / "libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice"
LIBERTY_DIR = PDK_ROOT / "libs.ref/sky130_fd_sc_hd/lib"
SCHEMATIC = ROOT / "cells/control/row_address_capture.sch"
PROFILES = isolated.PROFILES
PROFILE_MODELS = {"tt": "tt", "ss": "ss", "ff": "ff"}
LIBERTY_PROFILE_KEYS = {"tt": "tt", "ss": "slow", "ff": "fast"}

PRIME_RISE_PS = 1000.0
PRIME_FALL_PS = 2000.0
TEST_RISE_PS = 3000.0
TEST_FALL_PS = 4000.0
CLOCK_SLEW_PS = 50.0
DATA_SLEW_PS = 50.0
SAMPLE_AFTER_EDGE_PS = 700.0
Q_LOAD_FF = 3.434554
TRAN_STEP_PS = 2.0
STOP_PS = 4500.0


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_text(path: Path, value: str) -> None:
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def tag(offset_ps: float) -> str:
    sign = "m" if offset_ps < 0 else "p"
    return f"{sign}{abs(int(round(offset_ps))):04d}"


def make_scenarios(offsets_ps: list[float]) -> list[dict]:
    scenarios = []
    for bit in ("A0", "A1"):
        for transition in ("rise", "fall"):
            old, new = (0, 1) if transition == "rise" else (1, 0)
            for offset in offsets_ps:
                label = f"{bit.lower()}_{transition}_{tag(offset)}"
                scenarios.append({"bit": bit, "transition": transition,
                                  "old": old, "new": new,
                                  "offset_ps": offset, "label": label})
    return scenarios


def clock_waveform(vdd: float, stop_s: float) -> str:
    ramp = CLOCK_SLEW_PS * 1e-12
    events = ((PRIME_RISE_PS * 1e-12, vdd),
              (PRIME_FALL_PS * 1e-12, 0.0),
              (TEST_RISE_PS * 1e-12, vdd),
              (TEST_FALL_PS * 1e-12, 0.0))
    points = [(0.0, 0.0)]
    current = 0.0
    for center, next_value in events:
        points.extend(((center - ramp / 2, current),
                       (center + ramp / 2, next_value)))
        current = next_value
    points.append((stop_s, current))
    return "PWL(" + " ".join(f"{time:.12g} {value:.7g}"
                               for time, value in points) + ")"


def data_waveform(old: int, new: int, center_s: float, vdd: float,
                  stop_s: float) -> str:
    ramp = DATA_SLEW_PS * 1e-12
    require(center_s - ramp / 2 > PRIME_RISE_PS * 1e-12 + ramp,
            "Data transition overlaps the priming capture edge")
    require(center_s + ramp / 2 < TEST_FALL_PS * 1e-12 - ramp,
            "Data transition overlaps the falling clock edge")
    points = [(0.0, old * vdd),
              (center_s - ramp / 2, old * vdd),
              (center_s + ramp / 2, new * vdd),
              (stop_s, new * vdd)]
    return "PWL(" + " ".join(f"{time:.12g} {value:.7g}"
                               for time, value in points) + ")"


def liberty_constraints(profile: str) -> dict:
    path = LIBERTY_DIR / capture.LIBRARIES[LIBERTY_PROFILE_KEYS[profile]]
    text = path.read_text(encoding="utf-8")
    cell = capture.extract_group(
        text, r'cell\s*\(\s*"sky130_fd_sc_hd__dfxtp_1"\s*\)')
    pin = capture.extract_group(cell, r'pin\s*\(\s*"D"\s*\)')
    found = {}
    for kind, timing_type in (("setup", "setup_rising"),
                              ("hold", "hold_rising")):
        groups = [body for body in capture.group_list(pin, "timing")
                  if re.search(rf'timing_type\s*:\s*"{timing_type}"', body)
                  and re.search(r'related_pin\s*:\s*"CLK"', body)]
        require(len(groups) == 1,
                f"Expected one D-to-CLK {timing_type} arc in {path.name}")
        found[kind] = {
            "rise": capture.table_data(groups[0], "rise_constraint"),
            "fall": capture.table_data(groups[0], "fall_constraint"),
        }
    return {"path": path, "sha256": digest(path),
            "arc": capture.liberty_arc(path, Q_LOAD_FF * 1e-3),
            **found}


def generate_bit_subckt(netlist: Path, destination: Path) -> None:
    """Derive the single-bit simulation cell from Xschem's actual pin mapping."""
    text = netlist.read_text(encoding="utf-8")
    header = re.search(r"(?m)^\*{0,2}\.subckt\s+row_address_capture\s+(.+)$", text)
    require(header is not None,
            "Xschem output is missing the row_address_capture subcircuit")
    require(header.group(1).split() ==
            ["CLK", "A0", "A1", "VDD", "VSS", "A0_Q", "A1_Q"],
            "row_address_capture SPICE interface differs from the schematic")
    instances = {}
    for bit in ("A0", "A1"):
        found = re.findall(
            rf"(?m)^X{bit}_FF\s+(.+?)\s+sky130_fd_sc_hd__dfxtp_1\s*$", text)
        require(len(found) == 1,
                f"Expected exactly one {bit} dfxtp_1 instance in Xschem netlist")
        pins = found[0].split()
        expected = ["CLK", bit, "VSS", "VSS", "VDD", "VDD", f"{bit}_Q"]
        require(pins == expected,
                f"Unexpected {bit} dfxtp_1 pin mapping: {pins}")
        instances[bit] = pins
    require(instances["A0"][2:6] == instances["A1"][2:6],
            "Address-register supply and output pin mappings differ")
    body = ("* Testbench-only single-bit wrapper derived from row_address_capture.sch\n"
            ".subckt row_address_capture_bit CLK D VDD VSS Q\n"
            "XFF CLK D VSS VSS VDD VDD Q sky130_fd_sc_hd__dfxtp_1\n"
            ".ends row_address_capture_bit\n")
    write_text(destination, body)


def table_value(table: tuple, clk_slew_ns: float,
                data_slew_ns: float) -> float | None:
    x, y, values = table
    if not (x[0] <= clk_slew_ns <= x[-1]
            and y[0] <= data_slew_ns <= y[-1]):
        return None
    return capture.interpolate(x, y, values, clk_slew_ns, data_slew_ns)


def make_deck(profile: str, cell_netlist: Path, output_raw: Path,
              scenarios: list[dict]) -> tuple[str, dict[str, dict]]:
    vdd = float(PROFILES[profile]["vdd"])
    stop_s = STOP_PS * 1e-12
    sources = ["VSS_SRC VSS 0 0", f"VDD_SRC VDD VSS {vdd:g}",
               f"VCLK CLK VSS {clock_waveform(vdd, stop_s)}"]
    instances = []
    probes = ["v(CLK)"]
    named = {}
    for scenario in scenarios:
        label = scenario["label"].upper()
        d_node = f"D_{label}"
        q_node = f"Q_{label}"
        transition_center = (TEST_RISE_PS + float(scenario["offset_ps"])) * 1e-12
        sources.append(
            f"V{label} {d_node} VSS "
            f"{data_waveform(int(scenario['old']), int(scenario['new']), transition_center, vdd, stop_s)}")
        instances.append(f"X{label} CLK {d_node} VDD VSS {q_node} row_address_capture_bit")
        instances.append(f"CLOAD_{label} {q_node} VSS {Q_LOAD_FF}f")
        probes.extend((f"v({d_node})", f"v({q_node})"))
        named[scenario["label"]] = {**scenario, "d_node": d_node,
                                     "q_node": q_node,
                                     "transition_center_s": transition_center}
    lines = [f"* row_address_capture setup/hold screen: {profile.upper()}",
             f'.lib "{MODEL_LIBRARY}" {PROFILE_MODELS[profile]}',
             f'.include "{SC_LIBRARY}"',
             f'.include "{cell_netlist}"',
             f".temp {int(PROFILES[profile]['temp_c'])}",
             ".options method=gear reltol=1e-4 vabstol=1e-9 iabstol=1e-12",
             *sources, *instances,
             ".save " + " ".join(probes),
             ".control", "set noaskquit", "tran 2p 4.5n 0 2p",
             f"write {output_raw} all", "quit", ".endc", ".end"]
    return "\n".join(lines) + "\n", named


def logic_level(value: float, vdd: float) -> int | None:
    if value >= 0.9 * vdd:
        return 1
    if value <= 0.1 * vdd:
        return 0
    return None


def measure_scenario(raw: dict[str, np.ndarray], profile: str,
                     scenario: dict, constraints: dict) -> dict:
    time = raw["time"]
    vdd = float(PROFILES[profile]["vdd"])
    clock = capture.trace(raw, "CLK")
    clk50 = capture.crossing(time, clock, 0.5 * vdd, True,
                             2.8e-9, 3.2e-9)
    clk10 = capture.crossing(time, clock, 0.1 * vdd, True,
                             2.8e-9, 3.2e-9)
    clk90 = capture.crossing(time, clock, 0.9 * vdd, True,
                             2.8e-9, 3.2e-9)
    require(clk50 is not None and clk10 is not None and clk90 is not None,
            f"Missing measured clock rise in {scenario['label']}")
    d = capture.trace(raw, scenario["d_node"])
    q = capture.trace(raw, scenario["q_node"])
    center = float(scenario["transition_center_s"])
    rising = scenario["transition"] == "rise"
    d50 = capture.crossing(time, d, 0.5 * vdd, rising,
                           max(0.0, center - 1.0e-9),
                           min(time[-1], center + 1.0e-9))
    d10 = capture.crossing(time, d, 0.1 * vdd, rising,
                           max(0.0, center - 1.0e-9),
                           min(time[-1], center + 1.0e-9))
    d90 = capture.crossing(time, d, 0.9 * vdd, rising,
                           max(0.0, center - 1.0e-9),
                           min(time[-1], center + 1.0e-9))
    require(d50 is not None and d10 is not None and d90 is not None,
            f"Missing {scenario['transition']} data crossings in {scenario['label']}")
    data_slew = abs(d90 - d10)
    signed_offset = (d50 - clk50) * 1e12
    if signed_offset < -1e-6:
        side = "before_clock_setup_side"
        actual_margin = -signed_offset
        constraint_kind = "setup"
    elif signed_offset > 1e-6:
        side = "after_clock_hold_side"
        actual_margin = signed_offset
        constraint_kind = "hold"
    else:
        side = "at_clock_edge"
        actual_margin = None
        constraint_kind = None
    table = (constraints[constraint_kind][scenario["transition"]]
             if constraint_kind else None)
    constraint_ns = (table_value(table, abs(clk90 - clk10) * 1e9,
                                 data_slew * 1e9)
                     if table else None)
    constraint_ps = None if constraint_ns is None else constraint_ns * 1000.0
    slack = (None if actual_margin is None or constraint_ps is None
             else actual_margin - constraint_ps)

    sample_time = (TEST_RISE_PS + SAMPLE_AFTER_EDGE_PS) * 1e-12
    q_value = float(np.interp(sample_time, time, q))
    q_logic = logic_level(q_value, vdd)
    old, new = int(scenario["old"]), int(scenario["new"])
    if q_logic == new:
        state = "captured_new"
        plot_value = 1.0
    elif q_logic == old:
        state = "retained_old"
        plot_value = 0.0
    else:
        state = "indeterminate"
        plot_value = 0.5

    safe_expected = None
    if slack is not None and slack >= 0:
        safe_expected = new if constraint_kind == "setup" else old
    q_matches_safe_expected = (None if safe_expected is None
                               else q_logic == safe_expected)
    table_name = (f"{constraint_kind}_{scenario['transition']}"
                  if constraint_kind else "none")
    return {
        "corner": profile,
        "bit": scenario["bit"],
        "transition": scenario["transition"],
        "case": scenario["label"],
        "requested_offset_ps": float(scenario["offset_ps"]),
        "measured_d_to_clk_50_ps": signed_offset,
        "timing_region": side,
        "measured_margin_ps": actual_margin,
        "clock_slew_10_90_ps": abs(clk90 - clk10) * 1e12,
        "data_slew_10_90_ps": data_slew * 1e12,
        "liberty_table": table_name,
        "liberty_constraint_ps": constraint_ps,
        "liberty_slack_ps": slack,
        "q_sample_time_ns": sample_time * 1e9,
        "q_sample_v": q_value,
        "q_sample_logic": q_logic,
        "q_capture_state": state,
        "q_plot_value": plot_value,
        "safe_expected_q": safe_expected,
        "q_matches_liberty_safe_expectation": q_matches_safe_expected,
        "liberty_table_in_range": constraint_ps is not None,
    }


def write_plot(rows: list[dict], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    corners = ("tt", "ss", "ff")
    colors = {"tt": "#1765a3", "ss": "#b45d20", "ff": "#43804e"}
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharex=True,
                             sharey=True, layout="constrained")
    for ax, bit, transition in zip(axes.flat,
                                   ("A0", "A0", "A1", "A1"),
                                   ("rise", "fall", "rise", "fall")):
        selected_group = [row for row in rows
                          if row["bit"] == bit and row["transition"] == transition]
        for corner in corners:
            selected = [row for row in selected_group if row["corner"] == corner]
            selected.sort(key=lambda row: row["measured_d_to_clk_50_ps"])
            if not selected:
                continue
            x = [row["measured_d_to_clk_50_ps"] for row in selected]
            y = [row["q_plot_value"] for row in selected]
            ax.plot(x, y, marker="o", markersize=4, linewidth=1.0,
                    color=colors[corner], label=corner.upper())
            setup = [row["liberty_constraint_ps"] for row in selected
                     if row["liberty_table"].startswith("setup_")
                     and row["liberty_constraint_ps"] is not None]
            hold = [row["liberty_constraint_ps"] for row in selected
                    if row["liberty_table"].startswith("hold_")
                    and row["liberty_constraint_ps"] is not None]
            if setup and hold:
                ax.axvspan(-float(np.mean(setup)), float(np.mean(hold)),
                           color=colors[corner], alpha=0.07)
        ax.axvline(0.0, color="#444444", linewidth=0.8, linestyle=":")
        ax.set_title(f"{bit} data {transition}")
        ax.set_ylim(-0.15, 1.15)
        ax.set_yticks((0.0, 0.5, 1.0), labels=("old", "indeterminate", "new"))
        ax.grid(True, color="#dddddd", linewidth=0.55)
        ax.legend(fontsize=8, loc="best")
    for ax in axes[-1, :]:
        ax.set_xlabel("Measured D 50% crossing relative to CLK 50% (ps)\n"
                      "negative: before edge; positive: after edge")
    for ax in axes[:, 0]:
        ax.set_ylabel("Q at 700 ps after rising CLK")
    fig.suptitle("SKY130 row-address DFF · sampled transition aperture screen")
    fig.savefig(path, dpi=180, facecolor="white")
    plt.close(fig)


def summarize(rows: list[dict], scenarios: list[dict], corners: list[str]) -> dict:
    summary = {}
    for corner in corners:
        corner_rows = [row for row in rows if row["corner"] == corner]
        safe_rows = [row for row in corner_rows
                     if row["q_matches_liberty_safe_expectation"] is not None]
        by_path = {}
        for bit in ("A0", "A1"):
            for transition in ("rise", "fall"):
                selected = [row for row in corner_rows
                            if row["bit"] == bit and row["transition"] == transition]
                before_new = [row["measured_d_to_clk_50_ps"] for row in selected
                              if row["measured_d_to_clk_50_ps"] < 0
                              and row["q_capture_state"] == "captured_new"]
                after_old = [row["measured_d_to_clk_50_ps"] for row in selected
                             if row["measured_d_to_clk_50_ps"] > 0
                             and row["q_capture_state"] == "retained_old"]
                by_path[f"{bit}_{transition}"] = {
                    "sampled_points": len(selected),
                    "observed_new_capture_closest_pre_edge_ps": (
                        max(before_new) if before_new else None),
                    "observed_old_retention_closest_post_edge_ps": (
                        min(after_old) if after_old else None),
                    "setup_liberty_constraint_range_ps": _constraint_range(
                        selected, "setup_"),
                    "hold_liberty_constraint_range_ps": _constraint_range(
                        selected, "hold_"),
                }
        summary[corner] = {
            "status": "MEASURED",
            "scenario_count": len(corner_rows),
            "captured_new_samples": sum(row["q_capture_state"] == "captured_new"
                                         for row in corner_rows),
            "retained_old_samples": sum(row["q_capture_state"] == "retained_old"
                                         for row in corner_rows),
            "indeterminate_samples": sum(row["q_capture_state"] == "indeterminate"
                                         for row in corner_rows),
            "liberty_safe_expectation_checks": len(safe_rows),
            "liberty_safe_expectation_passes": sum(
                row["q_matches_liberty_safe_expectation"] is True for row in safe_rows),
            "liberty_safe_expectation_mismatches": sum(
                row["q_matches_liberty_safe_expectation"] is False for row in safe_rows),
            "points_without_liberty_reference": sum(
                row["liberty_table"] == "none" for row in corner_rows),
            "points_outside_liberty_table_range": sum(
                row["liberty_table"] != "none" and not row["liberty_table_in_range"]
                for row in corner_rows),
            "paths": by_path,
        }
    return summary


def _constraint_range(rows: list[dict], prefix: str) -> list[float] | None:
    values = [float(row["liberty_constraint_ps"]) for row in rows
              if row["liberty_table"].startswith(prefix)
              and row["liberty_constraint_ps"] is not None]
    return [min(values), max(values)] if values else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New result directory inside the repository")
    parser.add_argument("--corners", nargs="+", choices=("tt", "ss", "ff"),
                        default=["tt", "ss", "ff"])
    parser.add_argument("--transition-offsets-ps", nargs="+", type=float,
                        default=[-500, -300, -200, -150, -100, -75, -50,
                                 -25, 0, 10, 25, 50, 100, 200],
                        help="Requested D 50%% crossing relative to CLK 50%%; negative is early")
    parser.add_argument("--keep-raw", action="store_true")
    args = parser.parse_args()
    output = (ROOT / args.output_dir).resolve()
    require(output.is_relative_to(ROOT), "Output directory must remain inside the repository")
    require(not output.exists(), f"Choose a new output directory: {output}")
    require(args.corners and len(set(args.corners)) == len(args.corners),
            "Corners must be unique and nonempty")
    require(args.transition_offsets_ps
            and len(set(args.transition_offsets_ps)) == len(args.transition_offsets_ps),
            "Transition offsets must be unique and nonempty")
    require(all(math.isfinite(x) for x in args.transition_offsets_ps),
            "Transition offsets must be finite")
    require(MODEL_LIBRARY.is_file() and SC_LIBRARY.is_file()
            and SCHEMATIC.is_file(),
            "SKY130 models, standard-cell library or address schematic is missing")

    output.mkdir(parents=True)
    constraints = {corner: liberty_constraints(corner) for corner in args.corners}
    scenarios = make_scenarios(args.transition_offsets_ps)
    xschem_dir = output / "xschem"
    xschem_dir.mkdir()
    xschem_command = ["xschem", "-s", "-n", "-q", "-o", str(xschem_dir),
                      str(SCHEMATIC)]
    xschem = subprocess.run(xschem_command, cwd=ROOT, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=120)
    write_text(xschem_dir / "xschem.log", xschem.stdout)
    source_netlist = xschem_dir / "row_address_capture.spice"
    require(xschem.returncode == 0 and source_netlist.is_file(),
            "Xschem SPICE netlisting failed; inspect xschem/xschem.log")
    require(not re.search(r"missing symbol|unresolved symbol|symbol not found|Error:",
                          xschem.stdout, re.I),
            "Xschem reported a netlisting problem")
    cell_netlist = xschem_dir / "row_address_capture_bit.spice"
    generate_bit_subckt(source_netlist, cell_netlist)

    manifest = {
        "campaign": "row_address_capture_setup_hold_transistor_level_screen",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "complete": False,
        "status": "RUNNING",
        "scope": ("Each address input of the Xschem row_address_capture.sch is swept through a rising or falling "
                  "transition around the second rising CLK edge. The freshly netlisted dfxtp_1 instance is "
                  "used in a testbench-only single-bit wrapper, with one independent instance per timing point."),
        "profiles": {corner: {"pm3_corner": PROFILE_MODELS[corner],
                              "vdd_v": PROFILES[corner]["vdd"],
                              "temperature_c": PROFILES[corner]["temp_c"],
                              "liberty_file": constraints[corner]["arc"]["library"],
                              "liberty_voltage_v": constraints[corner]["arc"]["voltage_v"],
                              "liberty_temperature_c": constraints[corner]["arc"]["temperature_c"],
                              "liberty_setup_groups": ["setup_rising/rise_constraint",
                                                       "setup_rising/fall_constraint"],
                              "liberty_hold_groups": ["hold_rising/rise_constraint",
                                                      "hold_rising/fall_constraint"]}
                      for corner in args.corners},
        "stimulus": {
            "primer_rising_edge_ns": PRIME_RISE_PS / 1000,
            "primer_falling_edge_ns": PRIME_FALL_PS / 1000,
            "measured_rising_edge_ns": TEST_RISE_PS / 1000,
            "measured_falling_edge_ns": TEST_FALL_PS / 1000,
            "clock_slew_ps": CLOCK_SLEW_PS,
            "data_slew_ps": DATA_SLEW_PS,
            "data_transition_offsets_ps": args.transition_offsets_ps,
            "data_offset_reference": "requested D 50% crossing relative to rising CLK 50% crossing; negative is before",
            "q_sample_after_measured_edge_ps": SAMPLE_AFTER_EDGE_PS,
            "q_load_ff": Q_LOAD_FF,
            "transient_step_ps": TRAN_STEP_PS,
            "timing_points_per_profile": len(scenarios),
        },
        "initialization": ("No reset exists. A first rising edge at 1 ns captures the initial input value; "
                           "a single D transition is swept around the measured rising edge at 3 ns."),
        "measurement_probe": ("A simulation-only one-bit wrapper is generated from the freshly netlisted "
                              "XA0_FF/XA1_FF dfxtp_1 instance pin mapping. Neither the schematic nor its "
                              "symbols are changed."),
        "interpretation": ("Q is sampled once, 700 ps after the measured edge. For a D crossing before CLK, "
                           "the measured margin is compared with the matching Liberty setup table; for a "
                           "crossing after CLK, it is compared with the matching Liberty hold table. "
                           "Liberty operating points do not exactly match every native PM3 run point. "
                           "The table values and sampled Q are comparative exploratory evidence, not signoff."),
        "source_sha256": {
            "cells/control/row_address_capture.sch": digest(SCHEMATIC),
            "sims/row_decoder/run_row_address_setup_hold.py": digest(Path(__file__).resolve()),
        },
        "pdk_sha256": {"sky130.lib.spice": digest(MODEL_LIBRARY),
                       "sky130_fd_sc_hd.spice": digest(SC_LIBRARY),
                       **{value["path"].name: value["sha256"]
                          for value in constraints.values()}},
        "xschem_command": xschem_command,
        "generated_source_netlist_sha256": digest(source_netlist),
        "generated_testbench_cell_netlist_sha256": digest(cell_netlist),
        "results": {}, "simulation_errors": [], "warnings_by_corner": {},
    }
    rows = []
    for corner in args.corners:
        corner_dir = output / corner
        corner_dir.mkdir()
        raw_path = corner_dir / "waveform.raw"
        deck_path = corner_dir / "case.spice"
        log_path = corner_dir / "ngspice.log"
        deck, named = make_deck(corner, cell_netlist, raw_path, scenarios)
        write_text(deck_path, deck)
        try:
            simulation = subprocess.run(["ngspice", "-n", "-b", str(deck_path)],
                                        cwd=corner_dir, text=True,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, timeout=240)
        except subprocess.TimeoutExpired as exc:
            write_text(log_path, (exc.stdout or "") + (exc.stderr or ""))
            manifest["simulation_errors"].append(f"{corner}: ngspice timeout")
            continue
        write_text(log_path, simulation.stdout)
        fatal = (simulation.returncode != 0
                 or "fatal error in ngspice" in simulation.stdout.lower()
                 or "simulation interrupted due to error" in simulation.stdout.lower()
                 or not raw_path.is_file())
        missing_osdi = re.findall(r'Error opening osdi lib "([^"]+)"',
                                  simulation.stdout)
        manifest["warnings_by_corner"][corner] = {
            "missing_osdi_libraries": sorted(set(missing_osdi)),
            "no_compatibility_mode_notice": "No compatibility mode selected!" in simulation.stdout,
        }
        if fatal:
            manifest["simulation_errors"].append(
                f"{corner}: ngspice failed or produced no waveform; see {corner}/ngspice.log")
            continue
        raw = capture.read_raw(raw_path)
        corner_rows = [measure_scenario(raw, corner, named[scenario["label"]],
                                        constraints[corner])
                       for scenario in scenarios]
        rows.extend(corner_rows)
        manifest["results"][corner] = {
            "status": "MEASURED",
            "scenario_count": len(corner_rows),
            "waveform_sample_count": len(raw["time"]),
            "deck_sha256": digest(deck_path),
        }
        if not args.keep_raw:
            raw_path.unlink(missing_ok=True)

    expected_rows = len(scenarios) * len(args.corners)
    if rows:
        csv_path = output / "checks.csv"
        fieldnames = list(dict.fromkeys(key for row in rows for key in row))
        with csv_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames,
                                    lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        plot_path = output / "setup_hold_aperture.png"
        write_plot(rows, plot_path)
        manifest["summary"] = summarize(rows, scenarios, args.corners)
        manifest["summary_files"] = ["checks.csv", "setup_hold_aperture.png"]
    else:
        plot_path = None
        manifest["summary_files"] = []
    complete = not manifest["simulation_errors"] and len(rows) == expected_rows
    manifest.update({
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "complete": complete,
        "status": "MEASURED" if complete else "INCOMPLETE",
        "row_count": len(rows),
    })
    write_text(output / "manifest.json", json.dumps(manifest, indent=2))
    print(f"Measured {len(rows)}/{expected_rows} address setup/hold points across {len(args.corners)} profiles")
    print(f"Simulation errors: {len(manifest['simulation_errors'])}")
    if complete:
        for corner, result in manifest["summary"].items():
            print(f"{corner.upper()}: safe Liberty-reference checks "
                  f"{result['liberty_safe_expectation_passes']}/"
                  f"{result['liberty_safe_expectation_checks']}; "
                  f"no-reference edge points "
                  f"{result['points_without_liberty_reference']}; "
                  f"Q states new/old/indeterminate "
                  f"{result['captured_new_samples']}/{result['retained_old_samples']}/"
                  f"{result['indeterminate_samples']}")
    print(f"Results: {output.relative_to(ROOT)}")
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
