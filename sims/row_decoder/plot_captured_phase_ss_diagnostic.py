#!/usr/bin/env python3
"""Plot the SS captured-phase row-3 transient and export its edge metrics."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from plot_row_decoder_review import read_raw  # noqa: E402

DEFAULT_CASE = (
    ROOT / "sims/row_decoder/results/captured_phase_interface_ss_waveform_diag_20261010"
    / "cases/slow_ctl001_a0_to_3_p2100"
)
DEFAULT_WAVEFORM_CSV = (
    ROOT / "sims/row_decoder/results/captured_phase_interface_ss_waveform_diag_20261010"
    / "ss_row3_selected_waveforms.csv"
)
CAPTURE_NS = 15.0
PCLK_NODE = "v(net2)"
N3_NODE = "v(x1.n3.t3)"
DEC3_NODE = "v(dec3)"
WL3_NODE = "v(net8)"


def crossing(time: np.ndarray, signal: np.ndarray, level: float,
             rising: bool, start_s: float, end_s: float) -> float:
    mask = (time[:-1] >= start_s) & (time[1:] <= end_s)
    if rising:
        hits = np.flatnonzero(mask & (signal[:-1] < level) & (signal[1:] >= level))
    else:
        hits = np.flatnonzero(mask & (signal[:-1] > level) & (signal[1:] <= level))
    if not len(hits):
        raise ValueError(f"Missing {'rising' if rising else 'falling'} crossing at {level:g} V")
    index = int(hits[0])
    delta = signal[index + 1] - signal[index]
    if delta == 0:
        return float(time[index])
    return float(time[index] + (level - signal[index])
                 * (time[index + 1] - time[index]) / delta)


def get_trace(raw: dict[str, np.ndarray], node: str) -> np.ndarray:
    if node not in raw:
        raise ValueError(f"Missing waveform vector {node}")
    return raw[node]


def read_waveform_csv(path: Path) -> dict[str, dict[str, np.ndarray]]:
    """Load retained actual/reference waveforms without requiring ngspice RAW files."""
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"No waveform samples in {path}")

    def vector(column: str) -> np.ndarray:
        return np.asarray([float(row[column]) for row in rows], dtype=float)

    time = (vector("time_after_capture_ns") + CAPTURE_NS) * 1e-9
    columns = {
        "actual": {
            PCLK_NODE: "pclk_actual_v",
            N3_NODE: "n3_gate_actual_v",
            DEC3_NODE: "dec3_actual_v",
            WL3_NODE: "wl3_actual_v",
        },
        "liberty_reference": {
            PCLK_NODE: "pclk_liberty_reference_v",
            N3_NODE: "n3_gate_liberty_reference_v",
            DEC3_NODE: "dec3_liberty_reference_v",
            WL3_NODE: "wl3_liberty_reference_v",
        },
    }
    return {
        mode: {"time": time, **{node: vector(column) for node, column in mapping.items()}}
        for mode, mapping in columns.items()
    }


def summarize(mode: str, raw: dict[str, np.ndarray], vdd: float) -> dict:
    time = raw["time"]
    pclk = get_trace(raw, PCLK_NODE)
    wl3 = get_trace(raw, WL3_NODE)
    window_start, window_end = (CAPTURE_NS + 2.0) * 1e-9, 24e-9
    pclk_rise50 = crossing(time, pclk, 0.5*vdd, True, window_start, window_end)
    pclk_rise90 = crossing(time, pclk, 0.9*vdd, True, window_start, window_end)
    pclk_fall90 = crossing(time, pclk, 0.9*vdd, False, pclk_rise50, window_end)
    pclk_fall50 = crossing(time, pclk, 0.5*vdd, False, pclk_fall90, window_end)
    wl3_rise90 = crossing(time, wl3, 0.9*vdd, True, pclk_rise50, window_end)
    pclk_fall90_to_wl3_90_ps = (wl3_rise90 - pclk_fall90) * 1e12
    return {
        "mode": mode,
        "pclk_rise_50_ns_after_capture": (pclk_rise50 - CAPTURE_NS*1e-9) * 1e9,
        "pclk_rise_90_ns_after_capture": (pclk_rise90 - CAPTURE_NS*1e-9) * 1e9,
        "pclk_fall_90_ns_after_capture": (pclk_fall90 - CAPTURE_NS*1e-9) * 1e9,
        "pclk_fall_50_ns_after_capture": (pclk_fall50 - CAPTURE_NS*1e-9) * 1e9,
        "wl3_rise_90_ns_after_capture": (wl3_rise90 - CAPTURE_NS*1e-9) * 1e9,
        "wl3_90_after_pclk_fall_90_ps": pclk_fall90_to_wl3_90_ps,
        "wl3_v_at_pclk_fall_90": float(np.interp(pclk_fall90, time, wl3)),
        "wl3_v_at_pclk_fall_50": float(np.interp(pclk_fall50, time, wl3)),
    }


def write_waveform_csv(path: Path, actual: dict[str, np.ndarray],
                       reference: dict[str, np.ndarray]) -> None:
    time = actual["time"]
    mask = (time >= 17e-9) & (time <= 24e-9)
    selected_time = time[mask]
    columns = {
        "time_after_capture_ns": (selected_time - CAPTURE_NS*1e-9) * 1e9,
        "pclk_actual_v": np.interp(selected_time, time, actual[PCLK_NODE]),
        "n3_gate_actual_v": np.interp(selected_time, time, actual[N3_NODE]),
        "dec3_actual_v": np.interp(selected_time, time, actual[DEC3_NODE]),
        "wl3_actual_v": np.interp(selected_time, time, actual[WL3_NODE]),
    }
    ref_time = reference["time"]
    columns.update({
        "pclk_liberty_reference_v": np.interp(selected_time, ref_time, reference[PCLK_NODE]),
        "n3_gate_liberty_reference_v": np.interp(selected_time, ref_time, reference[N3_NODE]),
        "dec3_liberty_reference_v": np.interp(selected_time, ref_time, reference[DEC3_NODE]),
        "wl3_liberty_reference_v": np.interp(selected_time, ref_time, reference[WL3_NODE]),
    })
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(zip(*(columns[name] for name in columns)))


def plot_waveforms(path: Path, actual: dict[str, np.ndarray],
                   reference: dict[str, np.ndarray], vdd: float,
                   actual_metrics: dict, reference_metrics: dict) -> None:
    colors = {"pclk": "#1464a5", "n3": "#e07a19",
              "dec3": "#7c4d9e", "wl3": "#218c5b"}
    signals = (("PCLK", PCLK_NODE, "pclk"),
               ("N3 gate segment", N3_NODE, "n3"),
               ("DEC3", DEC3_NODE, "dec3"),
               ("WL3", WL3_NODE, "wl3"))
    fig, (full, zoom) = plt.subplots(
        2, 1, figsize=(11.5, 8), gridspec_kw={"height_ratios": [2.0, 1.1]},
        constrained_layout=True)
    for label, node, key in signals:
        for mode, raw, style in (("actual", actual, "-"),
                                 ("Liberty reference", reference, "--")):
            x_ns = (raw["time"] - CAPTURE_NS*1e-9) * 1e9
            y = raw[node] / vdd
            full.plot(x_ns, y, style, color=colors[key], lw=1.75,
                      label=f"{label} · {mode}")
            if key in ("pclk", "wl3"):
                zoom.plot(x_ns, y, style, color=colors[key], lw=2.0,
                          label=f"{label} · {mode}")

    pclk_fall_ns = actual_metrics["pclk_fall_90_ns_after_capture"]
    wl3_rise_ns = actual_metrics["wl3_rise_90_ns_after_capture"]
    for axis in (full, zoom):
        axis.axhline(0.9, color="#555555", lw=1, ls=":", label="90% VDD")
        axis.axvline(pclk_fall_ns, color="#b23b3b", lw=1.2, ls="-.")
        axis.axvline(wl3_rise_ns, color="#218c5b", lw=1.2, ls="-.")
        axis.axvspan(pclk_fall_ns, wl3_rise_ns, color="#c94c4c", alpha=0.12)
        axis.set_ylim(-0.08, 1.08)
        axis.set_ylabel("Voltage / VDD")
        axis.grid(True, alpha=0.22)
    full.set_xlim(2.0, 9.2)
    full.set_title("SKY130A SS (1.62 V, −40 °C): row 3 at 102.87 fF")
    full.set_xlabel("Time after rising CLK capture edge (ns)")
    full.legend(ncol=2, fontsize=8, loc="upper right")
    zoom.set_xlim(6.8, 7.55)
    zoom.set_xlabel("Time after rising CLK capture edge (ns), WL evaluation detail")
    zoom.legend(ncol=2, fontsize=8, loc="lower left")
    zoom.annotate(
        f"WL3 reaches 90% about {actual_metrics['wl3_90_after_pclk_fall_90_ps']:.0f} ps\n"
        "after PCLK begins falling",
        xy=((pclk_fall_ns + wl3_rise_ns)/2, 0.82), xytext=(7.06, 0.42),
        arrowprops={"arrowstyle": "->", "color": "#7c2828"},
        fontsize=9, ha="center")
    fig.savefig(path, dpi=160)
    svg = path.with_suffix(".svg")
    fig.savefig(svg)
    plt.close(fig)
    # Matplotlib's SVG path commands end with spaces; they are insignificant
    # to the renderer but make `git diff --check` report trailing whitespace.
    normalized_svg = "\n".join(
        line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()
    ) + "\n"
    svg.write_text(normalized_svg, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", type=Path, default=DEFAULT_CASE)
    parser.add_argument("--waveform-csv", type=Path,
                        help="Retained CSV with actual and Liberty-reference traces")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    case_dir = args.case_dir.resolve()
    output = (args.output_dir or case_dir.parent.parent).resolve()
    output.mkdir(parents=True, exist_ok=True)
    modes = ("actual", "liberty_reference")
    csv_path = args.waveform_csv.resolve() if args.waveform_csv else None
    if csv_path is None and case_dir == DEFAULT_CASE.resolve():
        csv_path = DEFAULT_WAVEFORM_CSV
    if csv_path is not None:
        raw = read_waveform_csv(csv_path)
    else:
        raw_paths = {mode: case_dir / mode / "waveform.raw" for mode in modes}
        missing = [str(path) for path in raw_paths.values() if not path.exists()]
        if missing:
            raise FileNotFoundError(
                "No RAW waveform files. Supply --waveform-csv with retained traces; missing: "
                + ", ".join(missing)
            )
        raw = {mode: read_raw(path) for mode, path in raw_paths.items()}
    netlist_text = (case_dir / "actual" / "case.spice").read_text(encoding="utf-8")
    import re
    supply = re.search(r"(?im)^VDD_SRC\s+\S+\s+\S+\s+([0-9.eE+-]+)", netlist_text)
    if supply is None:
        raise ValueError("Could not read VDD from actual simulation deck")
    vdd = float(supply.group(1))
    metrics = {mode: summarize(mode, raw[mode], vdd) for mode in modes}
    result = {
        "case": case_dir.name,
        "profile": "SS",
        "corner": "ss",
        "vdd_v": vdd,
        "temperature_c": -40,
        "row_load_ff": 102.873935496,
        "note": "Measured WL90 timing is a diagnostic, not a specification limit.",
        "results": metrics,
    }
    summary_path = output / "ss_row3_wl_timing_summary.json"
    summary_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    csv_path = output / "ss_row3_selected_waveforms.csv"
    write_waveform_csv(csv_path, raw["actual"], raw["liberty_reference"])
    png_path = output / "ss_row3_pclk_wl3_timing.png"
    plot_waveforms(png_path, raw["actual"], raw["liberty_reference"], vdd,
                   metrics["actual"], metrics["liberty_reference"])
    for mode in modes:
        m = metrics[mode]
        print(f"{mode}: PCLK fall-90={m['pclk_fall_90_ns_after_capture']:.6f} ns after capture; "
              f"WL3 rise-90={m['wl3_rise_90_ns_after_capture']:.6f} ns; "
              f"WL3_90 minus PCLK fall-90={m['wl3_90_after_pclk_fall_90_ps']:.3f} ps")
    print(f"Summary: {summary_path.relative_to(ROOT)}")
    print(f"Waveforms: {csv_path.relative_to(ROOT)}")
    print(f"Plot: {png_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
