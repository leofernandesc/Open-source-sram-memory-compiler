#!/usr/bin/env python3
"""Plot complete SS combined-PEX capture-to-PCLK phase campaigns as SVG."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


CAMPAIGNS = (
    (1.50, "capture_combined_pex_slow_phase1500_clk20700_s3p3ns_20261009"),
    (1.80, "capture_combined_pex_slow_phase1800_clk20700_s3p3ns_20261009"),
    (1.95, "capture_combined_pex_slow_phase1950_clk20700_s3p3ns_20261009"),
    (2.10, "capture_combined_pex_slow_phase2100_clk20700_s3p3ns_20261009"),
)


def load_campaign(results_root: Path, dirname: str) -> tuple[dict, list[dict[str, str]]]:
    path = results_root / dirname
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    errors = json.loads((path / "errors.json").read_text(encoding="utf-8"))
    if not manifest.get("complete") or errors:
        raise SystemExit(f"Campaign is incomplete or has simulator errors: {path}")
    with (path / "summary.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 24:
        raise SystemExit(f"Expected 24 cases in {path}, found {len(rows)}")
    transitions = {(row["old_address"], row["new_address"], row["dff_load_label"])
                   for row in rows}
    if len(transitions) != 24:
        raise SystemExit(f"Duplicate or missing transition/load cases in {path}")
    if not all(row["logic_pass"].lower() == "true" for row in rows):
        raise SystemExit(f"Functional waveform check failed in {path}")
    if not all(row["voltage_screen_pass"].lower() == "true" for row in rows):
        raise SystemExit(f"Terminal-magnitude diagnostic failed in {path}")
    if any(int(row["ngspice_returncode"]) != 0 for row in rows):
        raise SystemExit(f"ngspice failed in {path}")
    return manifest, rows


def campaign_metrics(rows: list[dict[str, str]]) -> dict[str, float]:
    return {
        "guard_pass": sum(row["timing_contract_pass"].lower() == "true" for row in rows),
        "max_wl90_ns": max(float(row["wl_delay90_ps"]) for row in rows) / 1000,
        "min_literal_lead_ps": min(float(row["literal_settle_lead_to_pclk_ps"])
                                    for row in rows),
    }


def build_svg(results_root: Path) -> str:
    data = []
    expected_transitions = None
    common_conditions = None
    for phase_ns, dirname in CAMPAIGNS:
        manifest, rows = load_campaign(results_root, dirname)
        transitions = {(row["old_address"], row["new_address"], row["dff_load_label"])
                       for row in rows}
        if expected_transitions is None:
            expected_transitions = transitions
        elif transitions != expected_transitions:
            raise SystemExit(f"Campaign cases do not match: {dirname}")
        conditions = (manifest["actual_clk_fall_ps"], manifest["settling_allowance_ns"],
                      manifest["wordline_load"]["capacitance_per_wl_ff"],
                      manifest["literal_settling_guard_ps"])
        if common_conditions is None:
            common_conditions = conditions
        elif conditions != common_conditions:
            raise SystemExit(f"Campaign conditions do not match: {dirname}")
        metrics = campaign_metrics(rows)
        high_phases = {float(row["pclk_high_phase_ps"]) for row in rows}
        if len(high_phases) != 1:
            raise SystemExit(f"PCLK high phase varies within {dirname}")
        data.append((phase_ns, next(iter(high_phases)) / 1000, metrics))

    fall_ps, allowance_ns, row_cap_ff, guard_ps = common_conditions
    width, height = 1120, 670
    left, right = 235, 1060
    x_min, x_max = 1.45, 2.15
    x = lambda value: left + (value - x_min) / (x_max - x_min) * (right - left)
    upper = (105, 285)
    lower = (375, 555)
    count_y = lambda value: upper[1] - value / 24 * (upper[1] - upper[0])
    wl_y = lambda value: lower[1] - (value - 3.20) / 0.12 * (lower[1] - lower[0])

    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Varredura SS de fase captura para PCLK com PEX combinado</title>',
        (f'<desc id="desc">Matrizes de 24 transições e cargas em quatro fases. '
         f'A queda ideal de PCLK permanece em {fall_ps / 1000:.2f} ns. '
         f'O gráfico compara casos que passam a margem de {guard_ps:.0f} ps e o maior WL90.</desc>'),
        '<rect width="100%" height="100%" fill="#0b1220"/>',
        '<style>text{font-family:system-ui,-apple-system,Segoe UI,sans-serif;fill:#eaf0f7}.muted{fill:#aebbd0}.grid{stroke:#334258;stroke-width:1}.line{fill:none;stroke:#62e0c1;stroke-width:4}.point{fill:#62e0c1;stroke:#0b1220;stroke-width:2}.wl{fill:none;stroke:#ffcf70;stroke-width:4}.wlpoint{fill:#ffcf70;stroke:#0b1220;stroke-width:2}.threshold{stroke:#f07979;stroke-width:2;stroke-dasharray:8 6}.small{font-size:14px}.body{font-size:16px}.title{font-size:23px;font-weight:700}.axis{font-size:13px}</style>',
        '<text x="42" y="38" class="title">Fase captura → PCLK: margem dos literais e atraso da WL em SS</text>',
        (f'<text x="42" y="62" class="small muted">PEX do decoder + quatro WL drivers · '
         f'Ceff lumped {row_cap_ff:.3f} fF · queda PCLK ideal em {fall_ps / 1000:.2f} ns · '
         f'janela de settling {allowance_ns:.1f} ns</text>'),
    ]

    for value in (0, 6, 12, 18, 24):
        y = count_y(value)
        pieces.extend([
            f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" class="grid"/>',
            f'<text x="{left - 12}" y="{y + 5:.1f}" text-anchor="end" class="axis muted">{value}/24</text>',
        ])
    for value in (3.20, 3.23, 3.26, 3.29, 3.32):
        y = wl_y(value)
        pieces.extend([
            f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" class="grid"/>',
            f'<text x="{left - 12}" y="{y + 5:.1f}" text-anchor="end" class="axis muted">{value:.2f}</text>',
        ])

    for phase in (1.50, 1.65, 1.80, 1.95, 2.10):
        px = x(phase)
        pieces.extend([
            f'<line x1="{px:.1f}" y1="{upper[0]}" x2="{px:.1f}" y2="{upper[1]}" class="grid"/>',
            f'<line x1="{px:.1f}" y1="{lower[0]}" x2="{px:.1f}" y2="{lower[1]}" class="grid"/>',
            f'<text x="{px:.1f}" y="{lower[1] + 22}" text-anchor="middle" class="axis muted">{phase:.2f}</text>',
        ])

    pieces.extend([
        f'<text x="42" y="90" class="body">Casos com literal ≥ {guard_ps:.0f} ps antes do PCLK</text>',
        f'<text x="42" y="355" class="body">Maior atraso WL até 90% de VDD (ns)</text>',
    ])
    count_points = []
    wl_points = []
    for phase_ns, high_phase_ns, metrics in data:
        px = x(phase_ns)
        cy = count_y(metrics["guard_pass"])
        wy = wl_y(metrics["max_wl90_ns"])
        count_points.append(f'{px:.1f},{cy:.1f}')
        wl_points.append(f'{px:.1f},{wy:.1f}')
        pieces.extend([
            f'<circle cx="{px:.1f}" cy="{cy:.1f}" r="7" class="point"/>',
            f'<text x="{px:.1f}" y="{cy - 13:.1f}" text-anchor="middle" class="small">{metrics["guard_pass"]}/24</text>',
            f'<circle cx="{px:.1f}" cy="{wy:.1f}" r="7" class="wlpoint"/>',
            f'<text x="{px:.1f}" y="{wy + 22:.1f}" text-anchor="middle" class="small">{metrics["max_wl90_ns"]:.3f}</text>',
        ])
    pieces.append(f'<polyline points="{" ".join(count_points)}" class="line"/>')
    pieces.append(f'<polyline points="{" ".join(wl_points)}" class="wl"/>')

    count_threshold_y = count_y(24)
    settling_threshold_y = wl_y(allowance_ns)
    pieces.extend([
        f'<line x1="{left}" y1="{count_threshold_y:.1f}" x2="{right}" y2="{count_threshold_y:.1f}" class="threshold"/>',
        f'<text x="{right - 4}" y="{count_threshold_y - 7:.1f}" text-anchor="end" class="small" fill="#f07979">24/24</text>',
        f'<line x1="{left}" y1="{settling_threshold_y:.1f}" x2="{right}" y2="{settling_threshold_y:.1f}" class="threshold"/>',
        f'<text x="{right - 4}" y="{settling_threshold_y - 7:.1f}" text-anchor="end" class="small" fill="#f07979">janela {allowance_ns:.1f} ns</text>',
        f'<text x="{(left + right) / 2}" y="620" text-anchor="middle" class="body">Fase entre captura do endereço e subida do PCLK ideal (ns)</text>',
        '<line x1="315" y1="647" x2="350" y2="647" class="line"/><circle cx="332" cy="647" r="5" class="point"/><text x="360" y="652" class="small muted">Margem literal (critério experimental)</text>',
        '<line x1="690" y1="647" x2="725" y2="647" class="wl"/><circle cx="707" cy="647" r="5" class="wlpoint"/><text x="735" y="652" class="small muted">WL90 máximo</text>',
        '</svg>',
    ])
    return "\n".join(pieces) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, default=Path("sims/row_decoder/results"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_svg(args.results_root), encoding="utf-8")
    print(f"SVG: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
