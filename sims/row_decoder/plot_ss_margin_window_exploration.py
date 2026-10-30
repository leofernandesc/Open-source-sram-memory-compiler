#!/usr/bin/env python3
"""Plot the critical SS selected-WL minimum across exploratory windows."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
CAMPAIGNS = (
    (22.5, 3.8, Path(
        "sims/row_decoder/results/"
        "captured_phase_interface_valid_remaining_ordered_3profile_"
        "fall22500_settle3800_q900_20261013")),
    (24.0, 3.8, Path(
        "sims/row_decoder/results/captured_phase_interface_ss_margin_"
        "fall24000_20261014")),
    (25.0, 3.8, Path(
        "sims/row_decoder/results/captured_phase_interface_ss_margin_"
        "fall25000_settle3800_20261014")),
    (24.0, 5.5, Path(
        "sims/row_decoder/results/captured_phase_interface_ss_margin_"
        "fall24000_settle5500_20261014_retest")),
    (25.0, 5.5, Path(
        "sims/row_decoder/results/captured_phase_interface_ss_margin_"
        "fall25000_settle5500_20261014")),
)
FLOOR_RATIO = 0.9
OUTPUT = Path(
    "sims/row_decoder/results/captured_phase_interface_ss_margin_"
    "fall25000_settle5500_20261014/ss_selected_wl_window_comparison.png"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def collect() -> list[dict]:
    points = []
    for clk_fall_ns, settle_ns, relative in CAMPAIGNS:
        directory = ROOT / relative
        for control in ("001", "010"):
            case_label = f"slow_ctl{control}_a1_to_2_p2100"
            case_dir = directory / "cases" / case_label
            for mode in ("actual", "liberty_reference"):
                mode_dir = case_dir / mode
                case_path = mode_dir / "case.json"
                require(case_path.is_file(), f"Missing case result: {case_path}")
                case = json.loads(case_path.read_text(encoding="utf-8"))
                require(case.get("status") == "PASS",
                        f"Non-passing result in {case_path}")
                require(case.get("profile") == "slow"
                        and case.get("control_vector") == control
                        and case.get("address_transition") == "1:2",
                        f"Unexpected case identity in {case_path}")
                checks_path = mode_dir / "checks.csv"
                with checks_path.open(newline="", encoding="utf-8") as stream:
                    rows = [row for row in csv.DictReader(stream)
                            if row["phase"] == "test"
                            and row["output"] == "WL2"
                            and row["metric"] == "settled_min_v"]
                require(len(rows) == 1,
                        f"Expected one selected-WL settled minimum in {checks_path}")
                deck = (mode_dir / "case.spice").read_text(encoding="utf-8")
                supplies = re.findall(
                    r"(?im)^VDD_SRC\s+\S+\s+\S+\s+([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                    deck)
                require(len(supplies) == 1, f"Could not read VDD in {mode_dir}")
                vdd = float(supplies[0])
                minimum_v = float(rows[0]["value"])
                points.append({
                    "clk_fall_ns": clk_fall_ns, "settle_ns": settle_ns,
                    "control": control, "mode": mode,
                    "minimum_v": minimum_v,
                    "margin_mv": (minimum_v - FLOOR_RATIO*vdd)*1000,
                    "vdd": vdd,
                })
    return points


def main() -> int:
    points = collect()
    require(len(points) == 20, f"Expected 20 paired samples, got {len(points)}")
    actual = [point for point in points if point["mode"] == "actual"]

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.1), sharey=True)
    colors = {"001": "#1769aa", "010": "#c45122"}
    labels = {"001": "Valid read 001", "010": "Valid write 010"}
    markers = {"001": "o", "010": "^"}
    offsets_ns = {"001": -0.08, "010": 0.08}
    for ax, settle_ns in zip(axes, (3.8, 5.5)):
        schedule_falls = sorted({point["clk_fall_ns"] for point in actual
                                 if point["settle_ns"] == settle_ns})
        for control in ("001", "010"):
            subset = sorted(
                (point for point in actual if point["control"] == control
                 and point["settle_ns"] == settle_ns),
                key=lambda point: point["clk_fall_ns"])
            xs = [point["clk_fall_ns"] + offsets_ns[control]
                  for point in subset]
            ys = [point["margin_mv"] for point in subset]
            ax.plot(xs, ys, marker=markers[control], color=colors[control], linewidth=1.8,
                    markersize=7, label=labels[control], zorder=3)
            for px, py in zip(xs, ys):
                ax.annotate(f"{py:.2f}", (px, py), xytext=(0, 8),
                            textcoords="offset points", ha="center", fontsize=8,
                            color=colors[control])
        ax.axhline(0, color="#9b332b", linestyle="--", linewidth=1.2,
                   label="Experimental 0.9·VDD screen" if settle_ns == 3.8 else None)
        ax.set_xticks(schedule_falls, [f"{value:g}" for value in schedule_falls])
        ax.set_xlabel("External CLK fall (ns)")
        ax.set_title(f"Settling allowance: {settle_ns:g} ns")
        ax.grid(axis="y", color="#d8dee7", linewidth=0.7)
    axes[0].set_ylabel("Minimum selected WL2 − 0.9·VDD (mV)")
    axes[0].legend(loc="upper left", fontsize=8)
    fig.suptitle("Critical SS transition 1→2: window minimum vs. clock fall")
    fig.text(
        0.5, 0.012,
        "Actual transistor-level path. Paired Liberty-reference deltas: 1.406 mV "
        "at 3.8 ns and 0.177 mV at 5.5 ns. At fixed settling allowance the "
        "minimum is nearly independent of clock fall; the higher 5.5 ns value "
        "reflects a later measurement window, not bitcell access margin.",
        ha="center", fontsize=8, color="#444444", wrap=True)
    fig.tight_layout(rect=(0, 0.09, 1, 0.94))

    output_path = ROOT / OUTPUT
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)

    manifest_path = output_path.parent / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    relative_output = str(output_path.relative_to(ROOT))
    summary_files = manifest.setdefault("summary_files", [])
    if relative_output.split("/")[-1] not in summary_files:
        summary_files.append(relative_output.split("/")[-1])
    evidence = manifest.setdefault("derived_evidence", [])
    evidence[:] = [item for item in evidence
                   if item.get("artifact") != relative_output.split("/")[-1]]
    evidence.append({
        "artifact": relative_output.split("/")[-1],
        "generator": "sims/row_decoder/plot_ss_margin_window_exploration.py",
        "source_campaigns": [str(path) for _, _, path in CAMPAIGNS],
        "plotted_samples": len(points),
        "metric": "SS selected WL2 test-phase minimum minus 0.9*VDD, in mV",
        "scope": "1->2 valid read/write; actual transistor-level and Liberty reference",
        "not_signoff": True,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    })
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n",
                             encoding="utf-8")
    minimum = min(actual, key=lambda point: point["margin_mv"])
    maximum = max(actual, key=lambda point: point["margin_mv"])
    print(f"Paired samples plotted: {len(points)}")
    print(f"Actual path margin range: {minimum['margin_mv']:.6f}.."
          f"{maximum['margin_mv']:.6f} mV")
    print(f"PNG: {relative_output}")
    print(f"Updated manifest: {manifest_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
