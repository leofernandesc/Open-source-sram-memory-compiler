#!/usr/bin/env python3
"""Screen setup/hold behavior of the captured valid-access path in SKY130 SPICE.

Many independent qualifier instances share one clock in each corner run. Their
external control edges are shifted around the second rising clock edge; the
actual internal VALID_ACCESS_D crossings are measured and compared with the
dfxtp_1 Liberty constraint tables. This is an exploratory transistor-level
screen, not a metastability or signoff characterization.
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
SCHEMATIC = ROOT / "cells/control/valid_access_capture.sch"
PROFILES = isolated.PROFILES
PROFILE_MODELS = {"tt": "tt", "ss": "ss", "ff": "ff"}
LIBRARIES = capture.LIBRARIES
LIBERTY_PROFILE_KEYS = {"tt": "tt", "ss": "slow", "ff": "fast"}

PRIME_RISE_PS = 1000.0
PRIME_FALL_PS = 2000.0
TEST_RISE_PS = 3000.0
TEST_FALL_PS = 4000.0
CONTROL_SLEW_PS = 50.0
CLOCK_SLEW_PS = 50.0
SAMPLE_AFTER_EDGE_PS = 700.0
Q_LOAD_FF = 3.434554
TRAN_STEP_PS = 2.0
STOP_PS = 4500.0
VALID_VECTOR = "001"  # CSb/OEb/WEb: legal read
INVALID_VECTOR = "000"  # simultaneous read/write request


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


def scenario_list(setup_leads: list[float], hold_offsets: list[float]) -> list[dict]:
    result = []
    for value in setup_leads:
        result.append({"kind": "setup", "external_offset_ps": value,
                       "label": f"setup_{tag(value)}"})
    for value in hold_offsets:
        result.append({"kind": "hold", "external_offset_ps": value,
                       "label": f"hold_{tag(value)}"})
    return result


def control_waveform(initial: int, events: list[tuple[float, int]],
                     stop_s: float) -> str:
    current = initial
    values = [(0.0, float(initial))]
    ramp = CONTROL_SLEW_PS * 1e-12
    for center_s, next_value in sorted(events):
        require(center_s - ramp / 2 >= 0,
                "Control transition begins before time zero")
        values.extend(((center_s - ramp / 2, float(current)),
                       (center_s + ramp / 2, float(next_value))))
        current = next_value
    values.append((stop_s, float(current)))
    return "PWL(" + " ".join(f"{time:.12g} {value:.7g}"
                               for time, value in values) + ")"


def vector_bits(vector: str) -> tuple[int, int, int]:
    return tuple(int(bit) for bit in vector)


def scenario_events(scenario: dict) -> tuple[int, list[tuple[float, str]]]:
    center = TEST_RISE_PS * 1e-12
    if scenario["kind"] == "setup":
        change_center = center - float(scenario["external_offset_ps"]) * 1e-12
        return 1, [(change_center, VALID_VECTOR)]
    change_to_valid = 1.5e-9
    change_to_invalid = center + float(scenario["external_offset_ps"]) * 1e-12
    return 1, [(change_to_valid, VALID_VECTOR),
               (change_to_invalid, INVALID_VECTOR)]


def make_clock(vdd: float, stop_s: float) -> str:
    ramp = CLOCK_SLEW_PS * 1e-12
    events = ((PRIME_RISE_PS * 1e-12, vdd),
              (PRIME_FALL_PS * 1e-12, 0.0),
              (TEST_RISE_PS * 1e-12, vdd),
              (TEST_FALL_PS * 1e-12, 0.0))
    values = [(0.0, 0.0)]
    current = 0.0
    for center, value in events:
        values.extend(((center - ramp / 2, current),
                       (center + ramp / 2, value)))
        current = value
    values.append((stop_s, current))
    return "PWL(" + " ".join(f"{time:.12g} {value:.7g}"
                               for time, value in values) + ")"


def liberty_constraints(profile: str) -> dict:
    path = LIBERTY_DIR / LIBRARIES[LIBERTY_PROFILE_KEYS[profile]]
    text = path.read_text(encoding="utf-8")
    cell = capture.extract_group(
        text, r"cell\s*\(\s*\"sky130_fd_sc_hd__dfxtp_1\"\s*\)")
    pin = capture.extract_group(cell, r"pin\s*\(\s*\"D\"\s*\)")
    found = {}
    for timing_type, table_name in (("setup_rising", "rise_constraint"),
                                    ("hold_rising", "fall_constraint")):
        groups = [body for body in capture.group_list(pin, "timing")
                  if re.search(rf"timing_type\s*:\s*\"{timing_type}\"", body)
                  and re.search(r"related_pin\s*:\s*\"CLK\"", body)]
        require(len(groups) == 1,
                f"Expected one D-to-CLK {timing_type} arc in {path.name}")
        found[timing_type] = capture.table_data(groups[0], table_name)
    arc = capture.liberty_arc(path, Q_LOAD_FF * 1e-3)
    return {"path": path, "sha256": digest(path), "arc": arc,
            "setup_table": found["setup_rising"],
            "hold_table": found["hold_rising"]}


def expose_data_probe(cell_netlist: Path) -> None:
    """Promote the existing D wire to a testbench-only subcircuit port."""
    text = cell_netlist.read_text(encoding="utf-8")
    header = ".subckt valid_access_capture CLK CSb OEb WEb VDD VSS VALID_ACCESS_Q"
    exposed_header = (".subckt valid_access_capture CLK CSb OEb WEb VDD VSS "
                      "VALID_ACCESS_D VALID_ACCESS_Q")
    require(text.count(header) == 1, "Unexpected captured-access subcircuit header")
    require(text.count("XVALID_AND net1 net2 VSS VSS VDD VDD net3 ") == 1,
            "Cannot identify the existing VALID_ACCESS_D net at the AND output")
    require(text.count("XVALID_FF CLK net3 VSS VSS VDD VDD VALID_ACCESS_Q ") == 1,
            "Cannot identify the existing DFF input wire")
    text = text.replace(header, exposed_header, 1)
    text = re.sub(r"(?<=\s)net3(?=\s)", "VALID_ACCESS_D", text)
    require("XVALID_AND net1 net2 VSS VSS VDD VDD VALID_ACCESS_D " in text
            and "XVALID_FF CLK VALID_ACCESS_D VSS VSS VDD VDD VALID_ACCESS_Q " in text,
            "Testbench D probe did not preserve the original net connection")
    cell_netlist.write_text(text, encoding="utf-8")


def table_value(table: tuple, clk_slew_ns: float,
                data_slew_ns: float) -> float | None:
    x, y, values = table
    if not (x[0] <= clk_slew_ns <= x[-1]
            and y[0] <= data_slew_ns <= y[-1]):
        return None
    return capture.interpolate(x, y, values, clk_slew_ns, data_slew_ns)


def make_deck(profile: str, cell_netlist: Path, output: Path,
              scenarios: list[dict]) -> tuple[str, dict[str, dict]]:
    vdd = float(PROFILES[profile]["vdd"])
    stop_s = STOP_PS * 1e-12
    sources = [f"VSS_SRC VSS 0 0", f"VDD_SRC VDD VSS {vdd:g}",
               f"VCLK CLK VSS {make_clock(vdd, stop_s)}"]
    instances = []
    probes = ["v(CLK)"]
    scenario_by_label = {}
    for scenario in scenarios:
        label = scenario["label"]
        instance_name = ("XSETUP_" if scenario["kind"] == "setup" else "XHOLD_") + tag(
            float(scenario["external_offset_ps"]))
        upper_name = instance_name[1:]
        q_node = f"Q_{upper_name}"
        d_node = f"D_{upper_name}"
        csb_node, oeb_node, web_node = (
            f"{upper_name}_CSB", f"{upper_name}_OEB", f"{upper_name}_WEB")
        initial, events = scenario_events(scenario)
        source_nodes = (csb_node, oeb_node, web_node)
        for index, (prefix, node) in enumerate(zip(("CSb", "OEb", "WEb"), source_nodes)):
            changes = [(time, vector_bits(vector)[index])
                       for time, vector in events]
            sources.append(f"V{upper_name}_{prefix} {node} VSS "
                           f"{control_waveform(1, changes, stop_s)}")
        instances.append(f"{instance_name} CLK {csb_node} {oeb_node} {web_node} "
                         f"VDD VSS {d_node} {q_node} valid_access_capture")
        instances.append(f"CLOAD_{upper_name} {q_node} VSS {Q_LOAD_FF}f")
        probes.extend((f"v({d_node})", f"v({q_node})"))
        scenario_by_label[label] = {**scenario, "instance": instance_name,
                                    "d_node": d_node,
                                    "q_node": q_node}
    lines = [f"* valid_access_capture setup/hold screen: {profile.upper()}",
             f'.lib "{MODEL_LIBRARY}" {PROFILE_MODELS[profile]}',
             f'.include "{SC_LIBRARY}"',
             f'.include "{cell_netlist}"',
             f".temp {int(PROFILES[profile]['temp_c'])}",
             ".options method=gear reltol=1e-4 vabstol=1e-9 iabstol=1e-12",
             *sources, *instances,
             ".save " + " ".join(probes),
             ".control", "set noaskquit", "tran 2p 4.5n 0 2p",
             f"write {output} all", "quit", ".endc", ".end"]
    return "\n".join(lines) + "\n", scenario_by_label


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
            f"Missing test clock edge in {scenario['label']}")
    d = capture.trace(raw, scenario["d_node"])
    q = capture.trace(raw, scenario["q_node"])
    q_sample_s = (TEST_RISE_PS + SAMPLE_AFTER_EDGE_PS) * 1e-12
    q_value = float(np.interp(q_sample_s, time, q))
    expected_q = 1
    q_result = logic_level(q_value, vdd)
    offset = float(scenario["external_offset_ps"])
    event_center = (TEST_RISE_PS - offset if scenario["kind"] == "setup"
                    else TEST_RISE_PS + offset) * 1e-12
    d_cross50 = capture.crossing(
        time, d, 0.5 * vdd, scenario["kind"] == "setup",
        max(0.0, event_center - 1.0e-9), min(time[-1], event_center + 1.5e-9))
    require(d_cross50 is not None,
            f"Missing VALID_ACCESS_D 50% crossing in {scenario['label']}")
    if scenario["kind"] == "setup":
        d10 = capture.crossing(time, d, 0.1 * vdd, True,
                               max(0.0, event_center - 1e-9),
                               min(time[-1], event_center + 1.5e-9))
        d90 = capture.crossing(time, d, 0.9 * vdd, True,
                               max(0.0, event_center - 1e-9),
                               min(time[-1], event_center + 1.5e-9))
        require(d10 is not None and d90 is not None,
                f"Missing rising D slew crossings in {scenario['label']}")
        data_slew = abs(d90 - d10)
        actual_margin = (clk50 - d_cross50) * 1e12
        constraint_ns = table_value(constraints["setup_table"],
                                    abs(clk90 - clk10) * 1e9, data_slew * 1e9)
        constraint_name = "liberty_setup_requirement_ps"
        crossing_name = "d_rise_50_ns"
        side_of_edge = "before"
        d_at_edge = float(np.interp(clk50, time, d))
    else:
        d90 = capture.crossing(time, d, 0.9 * vdd, False,
                               max(0.0, event_center - 1e-9),
                               min(time[-1], event_center + 1.5e-9))
        d10 = capture.crossing(time, d, 0.1 * vdd, False,
                               max(0.0, event_center - 1e-9),
                               min(time[-1], event_center + 1.5e-9))
        require(d10 is not None and d90 is not None,
                f"Missing falling D slew crossings in {scenario['label']}")
        data_slew = abs(d10 - d90)
        actual_margin = (d_cross50 - clk50) * 1e12
        constraint_ns = table_value(constraints["hold_table"],
                                    abs(clk90 - clk10) * 1e9, data_slew * 1e9)
        constraint_name = "liberty_hold_requirement_ps"
        crossing_name = "d_fall_50_ns"
        side_of_edge = "after"
        d_at_edge = float(np.interp(clk50, time, d))
    constraint_ps = None if constraint_ns is None else constraint_ns * 1000.0
    slack = None if constraint_ps is None else actual_margin - constraint_ps
    return {
        "corner": profile, "kind": scenario["kind"], "case": scenario["label"],
        "external_control_offset_ps": offset,
        "valid_d_crossing_side": side_of_edge,
        crossing_name: d_cross50 * 1e9,
        "clock_rise_50_ns": clk50 * 1e9,
        "actual_d_margin_ps": actual_margin,
        "clock_slew_10_90_ps": abs(clk90 - clk10) * 1e12,
        "data_slew_10_90_ps": data_slew * 1e12,
        constraint_name: constraint_ps,
        "liberty_slack_ps": slack,
        "d_at_clock_50_v": d_at_edge,
        "q_at_700ps_v": q_value,
        "q_expected": expected_q,
        "q_sample_logic": q_result,
        "q_sample_matches": q_result == expected_q,
        "liberty_table_in_range": constraint_ps is not None,
    }


def write_plot(rows: list[dict], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    corners = ("tt", "ss", "ff")
    colors = {"tt": "#1765a3", "ss": "#b45d20", "ff": "#43804e"}
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout="constrained")
    for kind, ax in zip(("setup", "hold"), axes):
        for corner in corners:
            selected = [row for row in rows if row["kind"] == kind
                        and row["corner"] == corner]
            selected.sort(key=lambda row: row["external_control_offset_ps"])
            x = [row["external_control_offset_ps"] for row in selected]
            y = [row["actual_d_margin_ps"] for row in selected]
            ax.plot(x, y, marker="o", linewidth=1.25, color=colors[corner],
                    label=f"{corner.upper()} measured D margin")
            limits = [row.get("liberty_setup_requirement_ps") if kind == "setup"
                      else row.get("liberty_hold_requirement_ps") for row in selected]
            if limits and all(value is not None for value in limits):
                ax.axhline(float(np.mean(limits)), color=colors[corner],
                           linestyle="--", linewidth=0.9,
                           label=f"{corner.upper()} Liberty constraint")
            for row in selected:
                if not row["q_sample_matches"]:
                    ax.scatter([row["external_control_offset_ps"]],
                               [row["actual_d_margin_ps"]], color="#c42b31",
                               marker="x", s=55, zorder=5)
        ax.set_title("Setup" if kind == "setup" else "Hold")
        ax.set_xlabel("External control transition offset from CLK 50% (ps)\n"
                      "setup: positive is before edge; hold: positive is after")
        ax.set_ylabel("VALID_ACCESS_D margin to CLK 50% (ps)")
        ax.grid(True, color="#dddddd", linewidth=0.6)
        ax.legend(fontsize=7, loc="best")
    fig.suptitle("SKY130 captured-access path · transistor-level exploratory screen")
    fig.savefig(path, dpi=180, facecolor="white")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New result directory inside the repository")
    parser.add_argument("--corners", nargs="+", choices=("tt", "ss", "ff"),
                        default=["tt", "ss", "ff"])
    parser.add_argument("--setup-leads-ps", nargs="+", type=float,
                        default=[500, 300, 200, 150, 100, 50, 0, -50],
                        help="External control transition center relative to CLK edge; positive is early")
    parser.add_argument("--hold-offsets-ps", nargs="+", type=float,
                        default=[-100, -50, -25, 0, 25, 50, 100, 200],
                        help="External valid-to-invalid control transition center relative to CLK edge")
    parser.add_argument("--keep-raw", action="store_true")
    args = parser.parse_args()
    output = (ROOT / args.output_dir).resolve()
    require(output.is_relative_to(ROOT), "Output directory must remain inside the repository")
    require(not output.exists(), f"Choose a new output directory: {output}")
    require(args.corners and len(set(args.corners)) == len(args.corners),
            "Corners must be unique and nonempty")
    require(len(set(args.setup_leads_ps)) == len(args.setup_leads_ps)
            and len(set(args.hold_offsets_ps)) == len(args.hold_offsets_ps),
            "Setup and hold offsets must be unique")
    require(all(math.isfinite(x) for x in args.setup_leads_ps + args.hold_offsets_ps),
            "Offsets must be finite")
    require(MODEL_LIBRARY.is_file() and SC_LIBRARY.is_file()
            and SCHEMATIC.is_file(), "SKY130 model, standard-cell or schematic file is missing")
    output.mkdir(parents=True)
    constraints = {corner: liberty_constraints(corner) for corner in args.corners}
    scenarios = scenario_list(args.setup_leads_ps, args.hold_offsets_ps)
    xschem_dir = output / "xschem"
    xschem_dir.mkdir()
    xschem_command = ["xschem", "-s", "-n", "-q", "-o", str(xschem_dir), str(SCHEMATIC)]
    xschem = subprocess.run(xschem_command, cwd=ROOT, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=120)
    write_text(xschem_dir / "xschem.log", xschem.stdout)
    raw_netlist = xschem_dir / "valid_access_capture.spice"
    require(xschem.returncode == 0 and raw_netlist.is_file(),
            "Xschem netlisting failed; inspect xschem/xschem.log")
    require(not re.search(r"missing symbol|unresolved symbol|symbol not found|Error:",
                          xschem.stdout, re.I), "Xschem reported a netlisting problem")
    cell_netlist = xschem_dir / "valid_access_capture_cell.spice"
    isolated.to_cell_subckt(raw_netlist, cell_netlist)
    expose_data_probe(cell_netlist)
    manifest = {
        "campaign": "valid_access_capture_setup_hold_transistor_level_screen",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "complete": False,
        "status": "RUNNING",
        "scope": ("SKY130 FD SC HD valid_access_capture schematic and dfxtp_1 standard-cell SPICE subcircuits. "
                  "Independent instances share one CLK per corner; the actual VALID_ACCESS_D internal node "
                  "and VALID_ACCESS_Q are measured for external-control timing offsets."),
        "profiles": {corner: {"pm3_corner": PROFILE_MODELS[corner],
                              "vdd_v": PROFILES[corner]["vdd"],
                              "temperature_c": PROFILES[corner]["temp_c"],
                              "liberty_file": constraints[corner]["arc"]["library"],
                              "liberty_voltage_v": constraints[corner]["arc"]["voltage_v"],
                              "liberty_temperature_c": constraints[corner]["arc"]["temperature_c"],
                              "liberty_setup_table": "rise_constraint, setup_rising",
                              "liberty_hold_table": "fall_constraint, hold_rising"}
                      for corner in args.corners},
        "stimulus": {
            "primer_rising_edge_ns": PRIME_RISE_PS / 1000,
            "primer_falling_edge_ns": PRIME_FALL_PS / 1000,
            "measured_rising_edge_ns": TEST_RISE_PS / 1000,
            "measured_falling_edge_ns": TEST_FALL_PS / 1000,
            "clock_slew_ps": CLOCK_SLEW_PS,
            "external_control_slew_ps": CONTROL_SLEW_PS,
            "valid_vector_csb_oeb_web": VALID_VECTOR,
            "invalid_vector_csb_oeb_web": INVALID_VECTOR,
            "q_sample_after_measured_edge_ps": SAMPLE_AFTER_EDGE_PS,
            "q_load_ff": Q_LOAD_FF,
            "setup_external_leads_ps": args.setup_leads_ps,
            "hold_external_offsets_ps": args.hold_offsets_ps,
            "transient_step_ps": TRAN_STEP_PS,
        },
        "no_reset": ("A priming edge captures disabled vector 111 before each measured capture. "
                     "Behavior before the first clock edge is not measured."),
        "measurement_probe": ("The existing VALID_ACCESS_D wire is promoted to an extra port "
                              "in the generated simulation-only subcircuit so ngspice records it. "
                              "The source Xschem schematic is not changed."),
        "liberty_interpretation": ("Liberty constraints are interpolated at measured 10-90 CLK and D slews. "
                                   "The Liberty operating points do not exactly match all native PM3 run points; "
                                   "these values are comparative references, not accepted design limits."),
        "source_sha256": {
            "cells/control/valid_access_capture.sch": digest(SCHEMATIC),
            "sims/row_decoder/run_valid_access_setup_hold.py": digest(Path(__file__).resolve()),
            "sims/row_decoder/run_valid_access_capture_spice.py": digest(Path(isolated.__file__).resolve()),
        },
        "pdk_sha256": {"sky130.lib.spice": digest(MODEL_LIBRARY),
                       "sky130_fd_sc_hd.spice": digest(SC_LIBRARY),
                       **{value["path"].name: value["sha256"]
                          for value in constraints.values()}},
        "xschem_command": xschem_command,
        "generated_cell_netlist_sha256": digest(cell_netlist),
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
                                        stderr=subprocess.STDOUT, timeout=180)
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
        corner_rows = []
        for scenario in scenarios:
            measured = measure_scenario(raw, corner, named[scenario["label"]],
                                        constraints[corner])
            corner_rows.append(measured)
            rows.append(measured)
        manifest["results"][corner] = {
            "status": "MEASURED",
            "setup_cases": len(args.setup_leads_ps),
            "setup_q_sample_matches": sum(bool(r["q_sample_matches"])
                                           for r in corner_rows if r["kind"] == "setup"),
            "hold_cases": len(args.hold_offsets_ps),
            "hold_q_sample_matches": sum(bool(r["q_sample_matches"])
                                          for r in corner_rows if r["kind"] == "hold"),
            "min_setup_liberty_slack_ps": min(
                (r["liberty_slack_ps"] for r in corner_rows
                 if r["kind"] == "setup" and r["liberty_slack_ps"] is not None),
                default=None),
            "min_hold_liberty_slack_ps": min(
                (r["liberty_slack_ps"] for r in corner_rows
                 if r["kind"] == "hold" and r["liberty_slack_ps"] is not None),
                default=None),
            "sample_count": len(raw["time"]),
            "deck_sha256": digest(deck_path),
        }
        if not args.keep_raw:
            raw_path.unlink(missing_ok=True)
    if rows:
        path = output / "checks.csv"
        fieldnames = list(dict.fromkeys(key for row in rows for key in row))
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames,
                                    lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        plot_path = output / "setup_hold_margin.png"
        write_plot(rows, plot_path)
    else:
        plot_path = None
    manifest.update({
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "complete": not manifest["simulation_errors"] and len(rows) == len(scenarios) * len(args.corners),
        "status": "MEASURED" if not manifest["simulation_errors"]
                  and len(rows) == len(scenarios) * len(args.corners) else "INCOMPLETE",
        "row_count": len(rows),
        "summary_files": (["checks.csv", "setup_hold_margin.png"]
                          if plot_path and plot_path.is_file() else []),
    })
    write_text(output / "manifest.json", json.dumps(manifest, indent=2))
    print(f"Completed {len(rows)} setup/hold timing points across {len(args.corners)} profiles")
    print(f"Simulation errors: {len(manifest['simulation_errors'])}")
    print(f"Results: {output.relative_to(ROOT)}")
    return 0 if manifest["status"] == "MEASURED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
