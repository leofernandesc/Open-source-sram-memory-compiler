#!/usr/bin/env python3
"""Plot selected-wordline margin for the complete captured valid matrix."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
OLD_MATRIX = Path(
    "sims/row_decoder/results/"
    "captured_phase_interface_valid_3profile_fall22500_settle3800_q900_20261011"
)
REMAINING_MATRIX = Path(
    "sims/row_decoder/results/"
    "captured_phase_interface_valid_remaining_ordered_3profile_fall22500_"
    "settle3800_q900_20261013"
)
PROFILES = ("tt", "slow", "fast")
CONTROL_MARKERS = {"001": ("o", "Read 001"), "010": ("^", "Write 010")}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def collect_matrix(matrix_dir: Path) -> list[dict]:
    points = []
    actual_cases = sorted((ROOT / matrix_dir / "cases").glob("*/actual/case.json"))
    for case_path in actual_cases:
        case = json.loads(case_path.read_text(encoding="utf-8"))
        require(case.get("status") == "PASS",
                f"Case is not PASS: {case_path.relative_to(ROOT)}")
        profile = case["profile"]
        old, new = map(int, case["address_transition"].split(":"))
        vector = case["control_vector"]
        require(profile in PROFILES and vector in CONTROL_MARKERS,
                f"Unexpected profile/control vector in {case_path}")

        deck = case_path.with_name("case.spice").read_text(encoding="utf-8")
        supply = re.findall(
            r"(?im)^VDD_SRC\s+\S+\s+\S+\s+([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
            deck,
        )
        require(len(supply) == 1, f"Could not resolve one VDD source in {case_path}")
        vdd = float(supply[0])

        checks_path = case_path.with_name("checks.csv")
        with checks_path.open(newline="", encoding="utf-8") as stream:
            selected = [
                row for row in csv.DictReader(stream)
                if row["phase"] == "test"
                and row["output"] == f"WL{new}"
                and row["metric"] == "settled_min_v"
            ]
        require(len(selected) == 1,
                f"Expected one selected-WL minimum in {checks_path}, got {len(selected)}")
        points.append({
            "case": case["case"], "profile": profile, "vector": vector,
            "old": old, "new": new, "vdd": vdd,
            "margin_mv": (float(selected[0]["value"]) - 0.9 * vdd) * 1000.0,
        })
    return points


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-matrix", type=Path, default=OLD_MATRIX,
                        help="Old-address-0 valid matrix, relative to repository root")
    parser.add_argument("--remaining-matrix", type=Path, default=REMAINING_MATRIX,
                        help="Old-address-1/2/3 valid matrix, relative to repository root")
    parser.add_argument("--output", type=Path, default=None,
                        help="PNG output path, relative to repository root")
    args = parser.parse_args()

    points = collect_matrix(args.old_matrix) + collect_matrix(args.remaining_matrix)
    expected = 16 * 2 * 3
    keys = {(p["profile"], p["vector"], p["old"], p["new"]) for p in points}
    require(len(points) == expected and len(keys) == expected,
            f"Expected {expected} unique actual cases; found {len(points)}")
    require(all(p["old"] in range(4) and p["new"] in range(4) for p in points),
            "Address transition is outside the 2-to-4 range")

    output = args.output or (
        REMAINING_MATRIX / "full_valid_matrix_selected_wl_margin.png"
    )
    output_path = ROOT / output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(15, 6.2), sharex=True, sharey=True)
    colors = {"001": "#1769aa", "010": "#c45122"}
    minimum = min(points, key=lambda p: p["margin_mv"])
    for ax, profile in zip(axes, PROFILES):
        profile_points = [p for p in points if p["profile"] == profile]
        vdds = {p["vdd"] for p in profile_points}
        require(len(vdds) == 1, f"Supply varies inside {profile} profile: {vdds}")
        vdd = vdds.pop()
        for vector, (marker, label) in CONTROL_MARKERS.items():
            subset = [p for p in profile_points if p["vector"] == vector]
            xs = [p["old"] * 4 + p["new"] + (-0.12 if vector == "001" else 0.12)
                  for p in subset]
            ys = [p["margin_mv"] for p in subset]
            ax.scatter(xs, ys, marker=marker, color=colors[vector], s=34,
                       linewidths=0.8, alpha=0.92, label=label, zorder=3)
        ax.axhline(0, color="#9b332b", linestyle="--", linewidth=1.2,
                   label="0.9·VDD bench screen" if profile == PROFILES[0] else None)
        ax.set_title(f"{profile.upper()} · VDD {vdd:.2f} V")
        ax.grid(axis="y", color="#d8dee7", linewidth=0.7)
        ax.set_xlim(-0.6, 15.6)
        ax.set_xticks(range(16), [f"{i // 4}→{i % 4}" for i in range(16)],
                      rotation=45, ha="right")

    axes[0].set_ylabel("Selected WL minimum − 0.9·VDD (mV)")
    fig.supxlabel("Old row → captured target row", y=0.055)
    fig.suptitle("Captured valid-address matrix: selected wordline margin",
                 fontsize=14, y=0.98)
    axes[0].legend(loc="upper left", fontsize=8, frameon=True)
    if minimum["profile"] == "slow":
        axes[1].annotate(
            f"minimum: +{minimum['margin_mv']:.3f} mV\n"
            f"{minimum['old']}→{minimum['new']}, {minimum['vector']}",
            xy=(minimum["old"] * 4 + minimum["new"] +
                (-0.12 if minimum["vector"] == "001" else 0.12),
                minimum["margin_mv"]),
            xytext=(0.05, 0.67), textcoords="axes fraction",
            arrowprops={"arrowstyle": "->", "color": "#333333"},
            fontsize=8, bbox={"boxstyle": "round,pad=0.3", "fc": "white", "alpha": 0.9},
        )
    fig.text(
        0.5, 0.012,
        "Experimental 0.9·VDD screen at one candidate phase/window and row load; "
        "not an approved project margin or timing limit.",
        ha="center", fontsize=8, color="#444444",
    )
    fig.tight_layout(rect=(0, 0.12, 1, 0.93))
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    print(f"Cases plotted: {len(points)}")
    print(f"Minimum screen margin: {minimum['margin_mv']:.6f} mV "
          f"({minimum['profile']}, {minimum['old']}→{minimum['new']}, "
          f"control {minimum['vector']})")
    print(f"PNG: {output_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
