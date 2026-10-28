#!/usr/bin/env python3
"""Characterize the captured valid-access cell with SKY130 transistor models."""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
SCHEMATIC = ROOT / "cells/control/valid_access_capture.sch"
PDK = Path("/opt/pdks/sky130A")
SC_LIBRARY = PDK / "libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice"
MODEL_LIBRARY = PDK / "libs.tech/ngspice/sky130.lib.spice"
PROFILES = {
    "tt": {"vdd": 1.8, "temp_c": 27},
    "ss": {"vdd": 1.62, "temp_c": -40},
    "ff": {"vdd": 1.8, "temp_c": 125},
}
EDGE_PS = 1000.0
PERIOD_PS = 2000.0
CONTROL_SETUP_PS = 500.0
LIVE_CHANGE_PS = 800.0
CONTROL_SLEW_PS = 50.0
Q_CAPTURE_SAMPLE_PS = 700.0
Q_HIGH_HOLD_SAMPLE_PS = 1000.0
Q_FALL_HOLD_SAMPLE_PS = 1250.0
Q_LOAD_FF = 3.434554


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], cwd: Path, log: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = result.stdout.rstrip()
    log.write_text(output + ("\n" if output else ""), encoding="utf-8")
    return result


def normalize_text_file(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    normalized = [line.rstrip() for line in lines]
    text = "\n".join(normalized) + ("\n" if normalized else "")
    if path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")
    return text


def make_control_pwl(bit_index: int, vdd: float) -> str:
    events: list[tuple[float, int]] = [(0.0, 1)]
    current = 1
    for vector in range(8):
        edge = EDGE_PS + PERIOD_PS * vector
        bits = ((vector >> 2) & 1, (vector >> 1) & 1, vector & 1)
        bit = bits[bit_index]
        setup_start = edge - CONTROL_SETUP_PS - CONTROL_SLEW_PS
        events.append((setup_start, current))
        events.append((setup_start + CONTROL_SLEW_PS, bit))
        current = bit
        live_change_start = edge + LIVE_CHANGE_PS
        events.append((live_change_start, current))
        events.append((live_change_start + CONTROL_SLEW_PS, 1 - bit))
        current = 1 - bit
    events.sort(key=lambda event: event[0])
    pairs = " ".join(f"{time_ps * 1e-12:.12g} {value * vdd:.6g}"
                     for time_ps, value in events)
    return f"PWL({pairs})"


def to_cell_subckt(source: Path, destination: Path) -> None:
    lines = source.read_text(encoding="utf-8").splitlines()
    converted: list[str] = []
    found_start = False
    found_end = False
    for line in lines:
        if line.startswith("**.subckt valid_access_capture "):
            line = line[2:]
            found_start = True
        elif line.strip() == "**.ends":
            line = ".ends"
            found_end = True
        elif line.strip() == ".end":
            continue
        converted.append(line)
    text = "\n".join(converted) + "\n"
    required = (
        ".subckt valid_access_capture CLK CSb OEb WEb VDD VSS VALID_ACCESS_Q",
        "XCSB_INV CSb VSS VSS VDD VDD",
        "XOE_WE_XOR OEb WEb VSS VSS VDD VDD",
        "XVALID_AND",
        "XVALID_FF CLK",
    )
    if not found_start or not found_end or not all(item in text for item in required):
        raise RuntimeError("Xschem SPICE output does not match the qualifier interface/topology")
    destination.write_text(text, encoding="utf-8")


def make_deck(corner: str, profile: dict[str, float | int],
              cell_netlist: Path, output: Path, csv_path: Path) -> None:
    vdd = float(profile["vdd"])
    temp = int(profile["temp_c"])
    lines = [
        f"* valid_access_capture transistor-level check: {corner}",
        f'.lib "{MODEL_LIBRARY}" {corner}',
        f'.include "{SC_LIBRARY}"',
        f'.include "{cell_netlist}"',
        f".temp {temp}",
        ".options method=gear reltol=1e-4 vabstol=1e-9 iabstol=1e-12",
        "VSS_SRC VSS 0 0",
        f"VDD_SRC VDD VSS {vdd}",
        f"VCLK CLK VSS PULSE(0 {vdd} 1n 50p 50p 1n 2n)",
        f"VCSB CSb VSS {make_control_pwl(0, vdd)}",
        f"VOEB OEb VSS {make_control_pwl(1, vdd)}",
        f"VWEB WEb VSS {make_control_pwl(2, vdd)}",
        "XACCESS CLK CSb OEb WEb VDD VSS VALID_ACCESS_Q valid_access_capture",
        f"CLOAD VALID_ACCESS_Q VSS {Q_LOAD_FF}f",
        ".control",
        "set ngbehavior=hsa",
        "set ng_nomodcheck",
        "set noaskquit",
        "tran 5p 17n 0 5p",
        # ngspice treats quote characters as literal filename characters in
        # wrdata, unlike .include. Keep the generated path unquoted.
        f"wrdata {csv_path} v(VALID_ACCESS_Q)",
        ".endc",
        ".end",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_trace(path: Path) -> tuple[list[float], list[float]]:
    times: list[float] = []
    values: list[float] = []
    for line in normalize_text_file(path).splitlines():
        fields = [float(value) for value in line.split()]
        if len(fields) < 2:
            continue
        # ngspice wrdata emits one time/value pair for each requested vector.
        times.append(fields[-2])
        values.append(fields[-1])
    if len(times) < 100 or any(b <= a for a, b in zip(times, times[1:])):
        raise RuntimeError(f"waveform is empty or malformed: {path}")
    return times, values


def sample(times: list[float], values: list[float], time_s: float) -> float:
    index = bisect.bisect_left(times, time_s)
    if index == 0:
        return values[0]
    if index >= len(times):
        return values[-1]
    t0, t1 = times[index - 1], times[index]
    v0, v1 = values[index - 1], values[index]
    if t1 == t0:
        return v1
    ratio = (time_s - t0) / (t1 - t0)
    return v0 + ratio * (v1 - v0)


def first_threshold_crossing(times: list[float], values: list[float],
                             start_s: float, expected: int,
                             vdd: float) -> float | None:
    threshold = 0.9 * vdd if expected else 0.1 * vdd
    index = bisect.bisect_left(times, start_s)
    while index < len(times):
        reached = values[index] >= threshold if expected else values[index] <= threshold
        if reached:
            if index == 0:
                return times[index]
            t0, t1 = times[index - 1], times[index]
            v0, v1 = values[index - 1], values[index]
            if v1 == v0:
                return t1
            return t0 + (threshold - v0) * (t1 - t0) / (v1 - v0)
        index += 1
    return None


def logic_level(value: float, vdd: float) -> int | None:
    if value >= 0.9 * vdd:
        return 1
    if value <= 0.1 * vdd:
        return 0
    return None


def write_capture_plot(output: Path, results: dict[str, object],
                       corners: list[str]) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(len(corners), 1,
                             figsize=(10, max(3.5, 2.45 * len(corners))),
                             sharex=True, layout="constrained", squeeze=False)
    axes = list(axes[:, 0])
    stop_s = 9e-9
    for ax, corner in zip(axes, corners):
        profile = PROFILES[corner]
        vdd = float(profile["vdd"])
        times, values = read_trace(output / corner / "valid_access_q.dat")
        selected = [(t, q) for t, q in zip(times, values) if t <= stop_s]
        ax.plot([t * 1e9 for t, _ in selected], [q for _, q in selected],
                color="#174a7e", linewidth=1.45, label="VALID_ACCESS_Q")
        ax.axhline(0.9 * vdd, color="#397c57", linestyle="--", linewidth=0.9,
                   label="0.9 × VDD")
        ax.axhline(0.1 * vdd, color="#a85b48", linestyle="--", linewidth=0.9,
                   label="0.1 × VDD")
        for edge in (1, 3, 5, 7):
            ax.axvline(edge, color="#8c8c8c", linestyle=":", linewidth=0.7)
        corner_result = results[corner]
        rise = corner_result["clock_to_q_rise_90_percent_ps"][0]
        fall = corner_result["clock_to_q_fall_10_percent_ps"][0]
        ax.set_title(
            f"{corner.upper()} · {vdd:g} V · {profile['temp_c']} °C · "
            f"tCQ90/10 rise/fall: {rise:.1f}/{fall:.1f} ps",
            loc="left", fontsize=10)
        ax.set_ylim(-0.12 * vdd, 1.12 * vdd)
        ax.set_ylabel("Q (V)")
        ax.set_yticks((0, vdd / 2, vdd), labels=("0", f"{vdd/2:g}", f"{vdd:g}"))
        ax.grid(axis="y", color="#dddddd", linewidth=0.6)
        ax.legend(loc="center right", fontsize=8, framealpha=0.9, ncol=3)
    axes[-1].set_xlim(0, stop_s * 1e9)
    axes[-1].set_xticks(range(10))
    axes[-1].set_xlabel("Time (ns); dotted lines mark rising clock edges")
    fig.suptitle("SKY130 FD SC HD captured valid-access output · transistor-level SPICE",
                 fontsize=12)
    path = output / "capture_q_pvt.png"
    fig.savefig(path, dpi=180, facecolor="white")
    plt.close(fig)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        help="New result directory; by default a unique UTC-stamped directory is used")
    parser.add_argument(
        "--corners", nargs="+", choices=tuple(PROFILES), default=["tt", "ss", "ff"],
        help="PDK native SPICE model corners to run (default: tt ss ff)")
    args = parser.parse_args()

    if args.output_dir:
        output = (ROOT / args.output_dir).resolve()
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output = ROOT / "sims/row_decoder/results" / f"valid_access_capture_spice_{stamp}"
    if output.exists():
        parser.error(f"output directory already exists: {output}")
    output.mkdir(parents=True)

    for path in (SCHEMATIC, SC_LIBRARY, MODEL_LIBRARY):
        if not path.is_file():
            print(f"ERROR: required file is unavailable: {path}", file=sys.stderr)
            return 2

    manifest: dict[str, object] = {
        "campaign": "valid_access_capture_spice_functional",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "complete": False,
        "model_family": "SKY130 native ngspice PM3 models; separate from the continuous model library used by decoder campaigns",
        "scope": "Transistor-level SPICE of the SKY130 FD SC HD standard-cell qualifier; checks sampled capture/hold behavior and measures Q threshold-crossing delay for one rising and one falling transition.",
        "control_equation": "VALID_ACCESS_D = !CSb AND (OEb XOR WEb)",
        "capture_edge": "rising edge of CLK",
        "control_setup_before_edge_ps": CONTROL_SETUP_PS,
        "live_control_change_after_edge_ps": LIVE_CHANGE_PS,
        "control_transition_slew_ps": CONTROL_SLEW_PS,
        "sample_times_after_rising_edge_ps": {
            "capture": Q_CAPTURE_SAMPLE_PS,
            "hold_while_high": Q_HIGH_HOLD_SAMPLE_PS,
            "hold_after_falling_edge": Q_FALL_HOLD_SAMPLE_PS,
        },
        "clock_to_q_thresholds": "first Q crossing of 0.9*VDD on a rising transition or 0.1*VDD on a falling transition, relative to the 50% clock crossing",
        "output_load_ff": Q_LOAD_FF,
        "output_load_basis": "Nominal dfxtp_1 Liberty table load; the actual phase-source fanout has not been extracted or included in this isolated-cell check.",
        "reset": "none; initial Q before first capture is not checked",
        "corners": args.corners,
        "source_sha256": {
            "cells/control/valid_access_capture.sch": digest(SCHEMATIC),
            "sims/row_decoder/run_valid_access_capture_spice.py": digest(Path(__file__).resolve()),
        },
        "pdk_sha256": {
            "sky130_fd_sc_hd.spice": digest(SC_LIBRARY),
            "sky130.lib.spice": digest(MODEL_LIBRARY),
        },
        "results": {},
        "warnings": {},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                           encoding="utf-8")

    xschem_log = output / "xschem.log"
    xschem_cmd = ["xschem", "-s", "-n", "-q", "-o", str(output), str(SCHEMATIC)]
    xschem = run(xschem_cmd, ROOT, xschem_log)
    raw_netlist = output / "valid_access_capture.spice"
    cell_netlist = output / "valid_access_capture_cell.spice"
    if xschem.returncode or not raw_netlist.is_file():
        print(f"Xschem SPICE netlisting failed; inspect {xschem_log}", file=sys.stderr)
        return 1
    xlog = xschem_log.read_text(encoding="utf-8").lower()
    if any(word in xlog for word in ("missing symbol", "unresolved symbol", "symbol not found")):
        print(f"Xschem reported a missing symbol; inspect {xschem_log}", file=sys.stderr)
        return 1
    to_cell_subckt(raw_netlist, cell_netlist)
    manifest["xschem_command"] = xschem_cmd
    manifest["generated_cell_netlist_sha256"] = digest(cell_netlist)

    all_rows: list[dict[str, object]] = []
    failures: list[str] = []
    for corner in args.corners:
        profile = PROFILES[corner]
        case_dir = output / corner
        case_dir.mkdir()
        deck = case_dir / "case.spice"
        wave = case_dir / "valid_access_q.dat"
        log = case_dir / "ngspice.log"
        make_deck(corner, profile, cell_netlist, deck, wave)
        command = ["ngspice", "-b", "-o", str(log), str(deck)]
        result = run(command, ROOT, case_dir / "ngspice_command.log")
        log_text = normalize_text_file(log) if log.exists() else ""
        missing_osdi = re.findall(r'Error opening osdi lib "([^"]+)"', log_text)
        fatal_markers = ("could not find a valid modelname", "ERROR: fatal error in ngspice",
                         "Simulation interrupted due to error", "Error on line")
        fatal = result.returncode != 0 or any(marker.lower() in log_text.lower()
                                               for marker in fatal_markers)
        manifest["warnings"][corner] = {
            "missing_osdi_libraries": sorted(set(missing_osdi)),
            "no_compatibility_mode_notice": "No compatibility mode selected!" in log_text,
        }
        if fatal or not wave.is_file():
            failures.append(f"{corner}: ngspice failed or did not create waveform data")
            continue

        times, values = read_trace(wave)
        vdd = float(profile["vdd"])
        corner_rows: list[dict[str, object]] = []
        previous_expected: int | None = None
        transition_delays_ps: dict[str, list[float]] = {"rise": [], "fall": []}
        for vector in range(8):
            csb, oeb, web = ((vector >> 2) & 1, (vector >> 1) & 1, vector & 1)
            expected = int((not csb) and (oeb ^ web))
            edge_ps = EDGE_PS + PERIOD_PS * vector
            q_capture = sample(times, values, (edge_ps + Q_CAPTURE_SAMPLE_PS) * 1e-12)
            q_high = sample(times, values, (edge_ps + Q_HIGH_HOLD_SAMPLE_PS) * 1e-12)
            q_fall = sample(times, values, (edge_ps + Q_FALL_HOLD_SAMPLE_PS) * 1e-12)
            logic_capture = logic_level(q_capture, vdd)
            logic_high = logic_level(q_high, vdd)
            logic_fall = logic_level(q_fall, vdd)
            transition = None
            transition_delay_ps = None
            if previous_expected is not None and expected != previous_expected:
                transition = "rise" if expected else "fall"
                crossing = first_threshold_crossing(
                    times, values, (edge_ps + 25.0) * 1e-12, expected, vdd)
                if crossing is not None:
                    transition_delay_ps = (crossing - (edge_ps + 25.0) * 1e-12) * 1e12
                    transition_delays_ps[transition].append(transition_delay_ps)
            row = {
                "corner": corner,
                "vector": f"{vector:03b}",
                "CSb": csb,
                "OEb": oeb,
                "WEb": web,
                "expected_Q": expected,
                "Q_transition": transition or "",
                "clock_to_Q_90_10_delay_ps": transition_delay_ps,
                "Q_capture_V": q_capture,
                "Q_high_hold_V": q_high,
                "Q_falling_hold_V": q_fall,
                "capture_pass": logic_capture == expected,
                "high_hold_pass": logic_high == expected,
                "falling_hold_pass": logic_fall == expected,
            }
            corner_rows.append(row)
            all_rows.append(row)
            previous_expected = expected
        corner_failures = sum(
            not row[key]
            for row in corner_rows
            for key in ("capture_pass", "high_hold_pass", "falling_hold_pass"))
        corner_failures += sum(
            row["Q_transition"] != "" and row["clock_to_Q_90_10_delay_ps"] is None
            for row in corner_rows)
        min_index = min(range(len(values)), key=values.__getitem__)
        max_index = max(range(len(values)), key=values.__getitem__)
        manifest["results"][corner] = {
            "status": "PASS" if corner_failures == 0 else "FAIL",
            "control_vector_captures": sum(bool(row["capture_pass"]) for row in corner_rows),
            "hold_after_live_change_while_high": sum(bool(row["high_hold_pass"]) for row in corner_rows),
            "hold_after_falling_edge": sum(bool(row["falling_hold_pass"]) for row in corner_rows),
            "failures": corner_failures,
            "supply_v": vdd,
            "temperature_c": int(profile["temp_c"]),
            "sample_count": len(times),
            "clock_to_q_rise_90_percent_ps": transition_delays_ps["rise"],
            "clock_to_q_fall_10_percent_ps": transition_delays_ps["fall"],
            "q_min_v": values[min_index],
            "q_min_time_ns": times[min_index] * 1e9,
            "q_max_v": values[max_index],
            "q_max_time_ns": times[max_index] * 1e9,
            "peak_below_vss_v": max(0.0, -values[min_index]),
            "peak_above_vdd_v": max(0.0, values[max_index] - vdd),
        }
        if corner_failures:
            failures.append(f"{corner}: {corner_failures} sampled logic/hold checks failed")

    if all_rows:
        with (output / "checks.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(all_rows[0]),
                                    lineterminator="\n")
            writer.writeheader()
            writer.writerows(all_rows)
    plot_path = None
    if not failures and all(corner in manifest["results"] for corner in args.corners):
        plot_path = write_capture_plot(output, manifest["results"], args.corners)
    manifest.update({
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "complete": not failures,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "artifacts": [
            "valid_access_capture.spice", "valid_access_capture_cell.spice",
            "xschem.log", "checks.csv", *[f"{c}/case.spice" for c in args.corners],
            *[f"{c}/ngspice.log" for c in args.corners],
            *[f"{c}/valid_access_q.dat" for c in args.corners],
            *([plot_path.name] if plot_path else []),
        ],
    })
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                           encoding="utf-8")
    if failures:
        print("FAIL: " + "; ".join(failures), file=sys.stderr)
        print(f"Results: {output.relative_to(ROOT)}")
        return 1
    for corner in args.corners:
        result = manifest["results"][corner]
        print(f"{corner.upper()}: captures {result['control_vector_captures']}/8, "
              f"high holds {result['hold_after_live_change_while_high']}/8, "
              f"fall holds {result['hold_after_falling_edge']}/8 PASS")
    if any(warning["missing_osdi_libraries"]
           for warning in manifest["warnings"].values()):
        print("NOTE: native PM3 simulation completed, but PDK OSDI startup warnings remain; "
              "review manifest/logs before broader model qualification.")
    if any(manifest["results"][corner]["peak_above_vdd_v"] > 0
           or manifest["results"][corner]["peak_below_vss_v"] > 0
           for corner in args.corners):
        print("NOTE: Q excursions beyond VSS/VDD were measured; no rail-excursion "
              "acceptance limit is defined by this sampled logic check.")
    if plot_path:
        print(f"Waveform plot: {plot_path.relative_to(ROOT)}")
    print(f"Results: {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
