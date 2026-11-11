#!/usr/bin/env python3
"""Measure observed BL/BLB differential crossing times from the archived 4x8 edge windows.

Source: 2026-11-11 new-abutment, nominal TT 1.8V 27C without distributed wire RC.
This script DOES NOT estimate a true bitcell minimum differential, Fmax, or SCLK safety.
The archived windows cover -0.3..+0.7 ns around SCLK20; events before their start
are left-censored. Use the full raw + new simulations for a real SCLK sweep.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "reports/phase1/sense_pex_small_signal_20261111/top_context_v1"
QUAL = ROOT / "reports/phase2/direct_abutment_20261111/qualification_v1/results.json"
TIMING = ROOT / "reports/phase2/direct_abutment_20261111/audit_v1/timing.json"
THRESHOLDS_MV = (5, 10, 20, 50, 100, 200)
EXPECTED_NPZ_SHA256 = "4d6ade65704dc0be161190abeb9ce97d6607d45b8b996d572885408ee2e"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def first_cross(t: np.ndarray, delta: np.ndarray, target_v: float):
    """Return status and first upward interpolated crossing within the recorded window."""
    if delta[0] >= target_v:
        return "ALREADY_ABOVE_AT_WINDOW_START", None
    for i in range(1, len(t)):
        if delta[i - 1] < target_v <= delta[i]:
            crossing = float(t[i - 1] + (target_v - delta[i - 1]) *
                             (t[i] - t[i - 1]) / (delta[i] - delta[i - 1]))
            return "CROSSED_IN_WINDOW", crossing
    return "NOT_REACHED_BEFORE_SCLK20", None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="New output directory; refuses overwrites")
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        parser.error("Use a NEW output directory to preserve previous evidence")
    file = BASE / "top_edge_windows.npz"
    if sha256(file) != EXPECTED_NPZ_SHA256:
        raise ValueError("Published NPZ hash mismatch")
    qualified = json.loads(QUAL.read_text())
    timings = json.loads(TIMING.read_text())
    if qualified["condition"] != {"corner": "tt", "vdd_v": 1.8, "temp_c": 27}:
        raise ValueError("Unexpected qualification conditions")
    if timings["source_receipt_sha256"] != sha256(QUAL):
        raise ValueError("Timing table is not bound to the qualification receipt")
    windows = np.load(file)["data"]
    if windows.ndim != 2 or windows.shape[1] != 18 or not np.all(np.isfinite(windows)):
        raise ValueError("Unexpected or non-finite waveform")
    if np.any(np.diff(windows[:, 0]) <= 0):
        raise ValueError("Waveform time is not strictly ascending")
    with (BASE / "clock_edges.csv").open(newline="") as f:
        edge_rows = {int(row["cycle"]): row for row in csv.DictReader(f)}
    phase_rows = {int(row["cycle"]): row for row in timings["phase"]}
    cycles = [c for c in qualified["cycles"] if c["operation"] == "read"]
    if len(cycles) != 9:
        raise ValueError("Expected 9 documented read cycles")
    records = []
    traces = []
    for c in cycles:
        cycle_id = int(c["cycle"])
        t_sclk20 = float(edge_rows[cycle_id]["t20"])
        t_wl80 = float(phase_rows[cycle_id]["wordline_active80_ns"])
        window = windows[(windows[:, 0] >= t_sclk20 - 0.3) &
                         (windows[:, 0] <= t_sclk20)]
        if len(window) < 7 or window[0, 0] > t_sclk20 - 0.27:
            raise ValueError(f"Missing preceding edge samples for read {cycle_id}")
        if np.max(np.diff(window[:, 0])) > 0.025:
            raise ValueError(f"Missing samples within read {cycle_id}")
        t = window[:, 0]
        for bit in range(8):
            sign = 1 if int(c["expected"]) & (1 << bit) else -1
            delta = sign * (window[:, 2 + 2 * bit] - window[:, 3 + 2 * bit])
            traces.append((cycle_id, bit, t - t_wl80, delta * 1000))
            for target_mv in THRESHOLDS_MV:
                status, crossing = first_cross(t, delta, target_mv / 1000)
                records.append({
                    "cycle": cycle_id, "row": int(c["row"]), "bit": bit,
                    "expected_bit": int(bool(int(c["expected"]) & (1 << bit))),
                    "threshold_mv": target_mv, "status": status,
                    "first_window_time_ns": float(t[0]),
                    "signed_delta_at_window_start_mv": float(delta[0] * 1000),
                    "t_wl80_ns": t_wl80, "t_sclk20_ns": t_sclk20,
                    "crossing_ns": crossing,
                    "relative_wl80_ps": ((crossing - t_wl80) * 1000) if crossing is not None else None,
                    "lead_before_sclk20_ps": ((t_sclk20 - crossing) * 1000) if crossing is not None else None,
                })
    out.mkdir(parents=True)
    columns = list(records[0])
    with (out / "threshold_crossings.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)
    summary = {}
    for threshold_mv in THRESHOLDS_MV:
        group = [r for r in records if r["threshold_mv"] == threshold_mv]
        crossed = [r for r in group if r["status"] == "CROSSED_IN_WINDOW"]
        relative = [r["relative_wl80_ps"] for r in crossed]
        lead = [r["lead_before_sclk20_ps"] for r in crossed]
        summary[str(threshold_mv) + "mV"] = {
            "crossed_in_window": len(crossed),
            "already_above_at_window_start": sum(
                r["status"] == "ALREADY_ABOVE_AT_WINDOW_START" for r in group),
            "not_reached_before_sclk20": sum(
                r["status"] == "NOT_REACHED_BEFORE_SCLK20" for r in group),
            "relative_wl80_ps_min": min(relative) if relative else None,
            "relative_wl80_ps_max": max(relative) if relative else None,
            "lead_before_sclk20_ps_min": min(lead) if lead else None,
            "lead_before_sclk20_ps_max": max(lead) if lead else None,
        }
    report = {
        "status": "PASS_ARCHIVED_WINDOW_REANALYSIS",
        "scope": "72 observations; nominal TT/1.8V/27C; no wire/leaf distributed RC",
        "raw_scope": "only 0.3 ns before SCLK20, not full WL-to-sense transient",
        "reference": "WL80 at selected wordline, from timing.json",
        "threshold_crossing_definition": "first upward crossing of EXPECTED-POLARITY signed BL minus BLB",
        "unresolved": [
            "5/10/20mV in left-censored observations cannot be timed precisely",
            "initial differential can preexist the recorded read window",
            "SCLK timing optimization requires actual re-simulation, not moving a marker",
            "results do not establish minimum bitcell differential, PVT, offset, Fmax or read yield",
        ],
        "source_sha256": {
            str(file.relative_to(ROOT)): sha256(file),
            str(QUAL.relative_to(ROOT)): sha256(QUAL),
            str(TIMING.relative_to(ROOT)): sha256(TIMING),
            str((BASE / "clock_edges.csv").relative_to(ROOT)): sha256(BASE / "clock_edges.csv"),
        },
        "read_cycles": 9, "bit_observations": 72, "threshold_observations": len(records),
        "summary": summary
    }
    (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(9, 5))
        for _, _, dt_ps, delta_mv in traces:
            ax.plot(dt_ps * 1000, delta_mv, alpha=0.14, linewidth=0.8)
        for threshold in THRESHOLDS_MV:
            ax.axhline(threshold, linewidth=0.65, linestyle=":")
        ax.axvline(0, linewidth=1.0, linestyle="--", label="WL reaches 80% VDD")
        ax.set(xlim=(-65, 80), ylim=(-40, 260),
               xlabel="Time relative to WL80 (ps)", ylabel="Signed BL-BLB differential (mV)",
               title="SRAM 4x8: 72 observed nominal read traces (early portion)")
        ax.grid(alpha=0.2)
        ax.legend()
        fig.tight_layout()
        fig.savefig(out / "bitline_differential_curves.png", dpi=180)
        plt.close(fig)
    except ImportError:
        report["plot_status"] = "SKIPPED_NO_MATPLOTLIB"
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "read_cycles": 9,
                      "bit_observations": 72, "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
