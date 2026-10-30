#!/usr/bin/env python3
"""Plot selected-row WL90 ranges for the distributed physical-row PEX screen."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MATRIX = ROOT / "sims/row_decoder/results/distributed_row_pex_full_transition_matrix_20261009"
DEFAULT_REFINE = ROOT / "sims/row_decoder/results/distributed_row_pex_slow_row3_refine_1ps_20261009"
DEFAULT_OUTPUT = ROOT / "docs/assets/row_decoder_distributed_row_full_transition_pex_20261009.svg"
PROFILE_LABELS = {"tt": "TT · 1.80 V / 27 °C",
                  "slow": "SS · 1.62 V / −40 °C",
                  "fast": "FF · 1.80 V / 125 °C"}
COLORS = {"tt": "#157a6e", "slow": "#c44848", "fast": "#3867a8"}
MARKERS = {"tt": "o", "slow": "s", "fast": "^"}


def rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix-dir", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--refine-dir", type=Path, default=DEFAULT_REFINE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    matrix = rows(args.matrix_dir / "summary.csv")
    refine = rows(args.refine_dir / "summary.csv")
    if len(matrix) != 48 or any(row.get("status") != "PASS" for row in matrix):
        raise SystemExit("Expected the complete 48-case all-transition PASS matrix")
    if len(refine) != 1 or refine[0].get("status") != "PASS":
        raise SystemExit("Expected the one-case 1 ps slow/WL3 refinement to pass")

    fig, ax = plt.subplots(figsize=(9.4, 4.8), dpi=140)
    x = [0, 1, 2, 3]
    for profile in ("tt", "slow", "fast"):
        profile_rows = [row for row in matrix if row["profile"] == profile]
        selected = [[row for row in profile_rows
                     if int(row["selected_physical_row"]) == target] for target in x]
        if any(len(group) != 4 for group in selected):
            raise SystemExit(f"Expected four old-address values per selected row in {profile}")
        low = [min(float(row["selected_row_wl90_delay_min_ps"]) for row in group) / 1000
               for group in selected]
        high = [max(float(row["selected_row_wl90_delay_max_ps"]) for row in group) / 1000
                for group in selected]
        center = [(lo + hi) / 2 for lo, hi in zip(low, high)]
        errors = [[mid - lo for mid, lo in zip(center, low)],
                  [hi - mid for mid, hi in zip(center, high)]]
        ax.errorbar(x, center, yerr=errors, color=COLORS[profile],
                    marker=MARKERS[profile], markersize=7, linewidth=2,
                    capsize=4, label=PROFILE_LABELS[profile])

    refine_row = refine[0]
    refine_low = float(refine_row["selected_row_wl90_delay_min_ps"]) / 1000
    refine_high = float(refine_row["selected_row_wl90_delay_max_ps"]) / 1000
    refine_center = (refine_low + refine_high) / 2
    ax.errorbar([3], [refine_center],
                yerr=[[refine_center - refine_low], [refine_high - refine_center]],
                color="#842b36", marker="D", markersize=5, linewidth=1.4,
                capsize=3, label="SS · WL3 refined at 1 ps", zorder=5)

    ax.axhline(3.3, color="#bf7c16", linestyle="--", linewidth=1.6,
               label="3.3 ns experimental settling screen")
    ax.set_xticks(x, [f"WL{i}" for i in x])
    ax.set_xlim(-0.25, 3.25)
    ax.set_ylim(0, 3.72)
    ax.set_ylabel("Time from PCLK rise to WL tap at 90% (ns)")
    ax.set_xlabel("Selected physical row; range spans all 16 extracted WL taps")
    ax.set_title("Decoder → WL driver → distributed 8-bit row PEX")
    ax.grid(axis="y", color="#d8dee8", alpha=0.65, linewidth=0.8)
    ax.legend(frameon=False, ncols=2, loc="upper left", fontsize=8.5)
    fig.text(0.01, 0.015,
             "48 cases: all 16 address pairs in TT/SS/FF at 5 ps; prior SS/WL3 subset refined at 1 ps. "
             "BL/BLB held at ideal VDD throughout. Experimental screen, not macro timing signoff.",
             ha="left", va="bottom", fontsize=8.5, color="#465365")
    fig.tight_layout(rect=(0, 0.055, 1, 1))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, format="svg", metadata={"Title": "Distributed physical row PEX WL timing screen"})
    # Matplotlib emits trailing spaces on multiline SVG path data. They are
    # valid SVG whitespace, but make `git diff --check` noisy on this artifact.
    svg = args.output.read_text(encoding="utf-8")
    args.output.write_text("\n".join(line.rstrip() for line in svg.splitlines()) + "\n",
                           encoding="utf-8")
    print(f"SVG: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
