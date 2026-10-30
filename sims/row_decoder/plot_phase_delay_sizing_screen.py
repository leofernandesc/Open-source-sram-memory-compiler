#!/usr/bin/env python3
"""Plot the PCLK delay-chain width screen's margin/area trade-off."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "sims/row_decoder/results/phase_delay_sizing_20261009/summary.csv"
DEFAULT_PNG = ROOT / "docs/assets/phase_delay_sizing_screen_20261009.png"
DEFAULT_SVG = ROOT / "docs/assets/phase_delay_sizing_screen_20261009.svg"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-png", type=Path, default=DEFAULT_PNG)
    parser.add_argument("--output-svg", type=Path, default=DEFAULT_SVG)
    args = parser.parse_args()
    with args.input.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        parser.error(f"no candidate rows in {args.input}")

    figure, axes = plt.subplots(2, 1, figsize=(9.2, 8.0), sharex=True,
                                constrained_layout=True)
    selected_name = "p_stronger"
    label_offsets = (
        {"reference": (10, 45), "n_stronger": (10, 7),
         "p_stronger": (10, -37)},
        {"min_balanced": (10, -34), "reference": (10, 10),
         "n_stronger": (10, -30)},
    )
    for row in rows:
        area = float(row["chain_channel_area_proxy_um2"])
        label = f"{row['name']}\nWp/Wn={float(row['pfet_width_um']):g}/{float(row['nfet_width_um']):g} µm"
        selected = row["name"] == selected_name
        marker = "*" if selected else "o"
        size = 190 if selected else 65
        color = "#d1495b" if selected else "#2878a5"
        metrics = (
            float(row["selected_wl_off_clearance_min_ps"]),
            float(row["capture_to_pclk_max_ps"]),
        )
        for axis_index, (axis, value) in enumerate(zip(axes, metrics)):
            axis.scatter(area, value, s=size, marker=marker, color=color,
                         edgecolor="#222222", linewidth=0.6, zorder=3)
            axis.annotate(label, (area, value),
                          xytext=label_offsets[axis_index].get(row["name"], (6, 7)),
                          textcoords="offset points", fontsize=8)

    axes[0].set_title("Worst-corner wordline-off margin")
    axes[0].set_ylabel("Minimum WL-off → precharge conduction (ps)")
    axes[1].set_title("Worst-corner access timing")
    axes[1].set_ylabel("Maximum capture → PCLK rise (ps)")
    axes[1].set_xlabel("80-stage inverter-chain channel-area proxy (µm²)")
    for axis in axes:
        axis.grid(True, alpha=0.3)
        axis.set_axisbelow(True)
    figure.suptitle("PCLK phase-chain inverter sizing screen — 3 PVT cases per candidate",
                    fontsize=13)
    figure.text(0.5, -0.015,
                "Area is 80 × L × (Wp + Wn), chain only; it is not layout area. "
                "The highlighted pair is a provisional working candidate.",
                ha="center", fontsize=8)
    for path in (args.output_png, args.output_svg):
        path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output_png, dpi=180, bbox_inches="tight")
    figure.savefig(args.output_svg, bbox_inches="tight")
    svg_lines = args.output_svg.read_text(encoding="utf-8").splitlines()
    args.output_svg.write_text("\n".join(line.rstrip() for line in svg_lines) + "\n",
                               encoding="utf-8")
    print(f"PNG: {args.output_png}")
    print(f"SVG: {args.output_svg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
