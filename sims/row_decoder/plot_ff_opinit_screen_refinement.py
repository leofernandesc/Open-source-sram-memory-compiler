#!/usr/bin/env python3
"""Plot FF terminal-magnitude maxima for the 1 ps / 0.5 ps refinement."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "sims/row_decoder/results"
FULL = RESULTS / "compact_decoder_full_fast_opinit_matrix_1ps/comparison.csv"
REFINED = RESULTS / "compact_decoder_fast_opinit_screen_refinement_0p5ps/comparison.csv"

SERIES = (
    ("baseline 1 ps", "baseline_terminal_magnitude_max_v", "#b33a3a", "", -0.21),
    ("baseline 0.5 ps", "baseline_terminal_magnitude_max_v", "#df8a24", "6 4", -0.07),
    ("PEX 1 ps", "pex_terminal_magnitude_max_v", "#356b9a", "", 0.07),
    ("PEX 0.5 ps", "pex_terminal_magnitude_max_v", "#2a8f85", "6 4", 0.21),
)


def read_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="") as stream:
        return {row["case"]: row for row in csv.DictReader(stream)}


def svg_plot(output: Path) -> None:
    full = read_rows(FULL)
    refined = read_rows(REFINED)
    cases = [case for case, row in full.items()
             if row["baseline_magnitude_result"] == "OUTSIDE_SCREEN"]
    if len(cases) != 10 or any(case not in refined for case in cases):
        raise SystemExit("Expected the 10 FF baseline screen cases in both comparison files")

    width, height = 1180, 610
    left, right, top, bottom = 110, 1140, 90, 450
    y_min, y_max = 1.85, 1.97
    x_span = (right - left) / len(cases)

    def x_at(index: int) -> float:
        return left + (index + 0.5) * x_span

    def y_at(value: float) -> float:
        return bottom - (value - y_min) * (bottom - top) / (y_max - y_min)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">FF decoder terminal-magnitude screen refinement</title>',
        '<desc id="desc">Ten FF baseline address pairs remain slightly above the 1.95 volt screen at 0.5 picosecond timestep. All matching PEX cases remain below it. The maximum change from 1 to 0.5 picoseconds is 0.037 millivolts for baseline and 0.014 millivolts for PEX.</desc>',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="590" y="34" text-anchor="middle" font-family="sans-serif" font-size="23" font-weight="700" fill="#18212b">FF operating-point matrix: timestep refinement</text>',
        '<text x="590" y="61" text-anchor="middle" font-family="sans-serif" font-size="15" fill="#46515d">10 baseline screen cases persist at 0.5 ps; every matching PEX case passes</text>',
    ]

    for tick in (1.86, 1.88, 1.90, 1.92, 1.94, 1.96):
        y = y_at(tick)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="#dce2e8"/>')
        parts.append(f'<text x="{left - 14}" y="{y + 5:.1f}" text-anchor="end" font-family="sans-serif" font-size="13" fill="#46515d">{tick:.2f}</text>')

    threshold_y = y_at(1.95)
    parts.extend([
        f'<line x1="{left}" y1="{threshold_y:.1f}" x2="{right}" y2="{threshold_y:.1f}" stroke="#9f2020" stroke-width="2" stroke-dasharray="9 6"/>',
        f'<text x="{right - 5}" y="{threshold_y - 8:.1f}" text-anchor="end" font-family="sans-serif" font-size="13" font-weight="700" fill="#9f2020">1.95 V screen</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#35404b" stroke-width="1.5"/>',
        f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#35404b" stroke-width="1.5"/>',
        f'<text x="28" y="{(top + bottom) / 2:.1f}" transform="rotate(-90 28 {(top + bottom) / 2:.1f})" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#18212b">Maximum terminal magnitude (V)</text>',
        f'<text x="{(left + right) / 2:.1f}" y="505" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#18212b">Ordered address transition</text>',
    ])

    for index, case in enumerate(cases):
        x = x_at(index)
        label = case.removeprefix("fast_").replace("_to_", "→")
        parts.append(f'<text x="{x:.1f}" y="{bottom + 24}" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#35404b">{escape(label)}</text>')

    for label, key, color, dash, offset in SERIES:
        points = []
        for index, case in enumerate(cases):
            source = full if label.endswith("1 ps") else refined
            value = float(source[case][key])
            x = x_at(index) + offset * 36
            y = y_at(value)
            points.append((x, y))
        point_string = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        parts.append(f'<polyline points="{point_string}" fill="none" stroke="{color}" stroke-width="2"{dash_attr}/>')
        for x, y in points:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}" stroke="#ffffff" stroke-width="1"/>')

    legend_y = 550
    legend_xs = (180, 425, 695, 940)
    for (label, _key, color, dash, _offset), x in zip(SERIES, legend_xs):
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        parts.append(f'<line x1="{x}" y1="{legend_y}" x2="{x + 35}" y2="{legend_y}" stroke="{color}" stroke-width="3"{dash_attr}/>')
        parts.append(f'<circle cx="{x + 17}" cy="{legend_y}" r="4" fill="{color}"/>')
        parts.append(f'<text x="{x + 44}" y="{legend_y + 5}" font-family="sans-serif" font-size="13" fill="#35404b">{escape(label)}</text>')

    parts.append('<text x="590" y="590" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#596571">Baseline maxima are VGD; the 1.95 V line is the runner screen, not a standalone reliability limit.</text>')
    parts.append("</svg>")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(parts) + "\n")
    print(f"SVG: {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs/assets/row_decoder_ff_opinit_screen_refinement.svg")
    args = parser.parse_args()
    svg_plot(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
