#!/usr/bin/env python3
"""Plot measured PRECH-release margin versus ideal VALID_ACCESS_Q arrival."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "sims/row_decoder/results"
DEFAULT_DELAYS_PS = (0, 900, 1000, 1250)
PROFILES = {
    "tt": ("TT · 1.80 V · 27 °C", "#1565c0"),
    "slow": ("SS · 1.62 V · −40 °C", "#ef6c00"),
    "fast": ("FF · 1.80 V · 125 °C", "#2e7d32"),
}
RELEASE_GUARD_PS = 250.0


def load_point(delay_ps: int, profile: str) -> tuple[float, str]:
    folder = RESULTS / f"phase_source_valid_access_q_guard250_{delay_ps}ps_20261009"
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if not manifest.get("complete"):
        raise SystemExit(f"Incomplete campaign: {folder}")
    if manifest["phase_assumptions"]["release_lead_screen"]["minimum_ps"] != RELEASE_GUARD_PS:
        raise SystemExit(f"Unexpected release-lead guard in {folder}")

    matches = []
    for case_path in (folder / "cases").glob("*/case.json"):
        case = json.loads(case_path.read_text(encoding="utf-8"))
        if case["profile"] == profile:
            matches.append(case)
    if len(matches) != 1:
        raise SystemExit(f"Expected one {profile} case in {folder}, found {len(matches)}")
    case = matches[0]
    if case["valid_access_q_delay_ps"] != delay_ps:
        raise SystemExit(f"Arrival-delay mismatch in {folder}: {case['valid_access_q_delay_ps']}")
    lead_ps = case["precharge_timing"]["precharge_releases"][0]["lead_ps"]
    return float(lead_ps), case["status"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-svg", type=Path,
                        default=ROOT / "docs/assets/row_decoder_valid_access_arrival_skew_20261009.svg")
    parser.add_argument("--output-png", type=Path,
                        default=ROOT / "docs/assets/row_decoder_valid_access_arrival_skew_20261009.png")
    args = parser.parse_args()

    data = {profile: [load_point(delay, profile) for delay in DEFAULT_DELAYS_PS]
            for profile in PROFILES}
    fig, ax = plt.subplots(figsize=(8.4, 4.9), constrained_layout=True)
    ax.axhspan(RELEASE_GUARD_PS, 760, color="#e8f5e9", alpha=0.7, zorder=0)
    ax.axhline(RELEASE_GUARD_PS, color="#b71c1c", linestyle="--", linewidth=1.5,
               label="250 ps experimental release guard")
    for profile, (label, color) in PROFILES.items():
        margins = [point[0] for point in data[profile]]
        ax.plot(DEFAULT_DELAYS_PS, margins, marker="o", linewidth=2,
                markersize=6, label=label, color=color)
        for delay, margin, (_, status) in zip(DEFAULT_DELAYS_PS, margins, data[profile]):
            if status != "PASS":
                ax.scatter([delay], [margin], marker="x", s=80, linewidth=2.2,
                           color=color, zorder=5)

    ax.set_title("VALID_ACCESS_Q arrival sensitivity of the PCLK/PRECH chain")
    ax.set_xlabel("Idealized VALID_ACCESS_Q delay after CLK capture (ps)")
    ax.set_ylabel("PRECH release lead before PCLK (ps)")
    ax.set_xlim(-45, 1295)
    ax.set_ylim(-80, 760)
    ax.set_xticks(DEFAULT_DELAYS_PS)
    ax.grid(True, color="#b0bec5", linewidth=0.6, alpha=0.55)
    ax.legend(loc="best", frameon=True, fontsize=8.5)
    fig.text(0.5, -0.025,
             "Measured crossings: PRECH rising at 75% VDD to PCLK rising at 50% VDD. "
             "Single 0→3 read transition; ideal qualifier arrival, not captured-control timing.",
             ha="center", va="top", fontsize=8)
    args.output_svg.parent.mkdir(parents=True, exist_ok=True)
    args.output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output_svg)
    svg_text = args.output_svg.read_text(encoding="utf-8")
    args.output_svg.write_text(
        "\n".join(line.rstrip() for line in svg_text.splitlines()) + "\n",
        encoding="utf-8",
    )
    fig.savefig(args.output_png, dpi=180)
    plt.close(fig)
    print(f"SVG: {args.output_svg}")
    print(f"PNG: {args.output_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
