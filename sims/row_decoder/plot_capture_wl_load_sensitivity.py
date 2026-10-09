#!/usr/bin/env python3
"""Render a matched capture-to-PCLK WL-load comparison as a standalone SVG."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


PROFILES = ("tt", "slow", "fast")


def load_campaign(path: Path) -> tuple[dict, list[dict[str, str]]]:
    manifest = json.loads(path.with_name("manifest.json").read_text(encoding="utf-8"))
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not manifest.get("complete") or manifest.get("errors"):
        raise SystemExit(f"Campaign is incomplete or contains errors: {path}")
    if len(rows) != 72:
        raise SystemExit(f"Expected 72 cases in {path}, found {len(rows)}")
    keys = {(r["profile"], r["old_address"], r["new_address"], r["dff_load_label"]) for r in rows}
    if len(keys) != 72:
        raise SystemExit(f"Duplicate or missing comparison cases in {path}")
    if not all(r["logic_pass"].lower() == "true" for r in rows):
        raise SystemExit(f"At least one functional waveform check failed in {path}")
    if any(int(r["ngspice_returncode"]) != 0 for r in rows):
        raise SystemExit(f"At least one ngspice execution failed in {path}")
    return manifest, rows


def campaign_maxima(rows: list[dict[str, str]]) -> dict[str, float]:
    result = {}
    for profile in PROFILES:
        values = [float(row["wl_delay90_ps"]) / 1000 for row in rows
                  if row["profile"] == profile]
        if len(values) != 24:
            raise SystemExit(f"Expected 24 cases for profile {profile}, found {len(values)}")
        result[profile] = max(values)
    return result


def svg(reference: dict[str, float], loaded: dict[str, float],
        reference_ff: float, loaded_ff: float) -> str:
    width, height = 1000, 420
    left, right, top, bottom = 190, 860, 78, 340
    max_ns = 3.2
    scale = (right - left) / max_ns
    profile_names = {"tt": "TT · 1.80 V · 27 °C",
                     "slow": "SS · 1.62 V · −40 °C",
                     "fast": "FF · 1.80 V · 125 °C"}
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Atraso WL90 conforme a carga capacitiva da wordline</title>',
        '<desc id="desc">Comparação entre 17,4 fF e 102,874 fF no mesmo decoder, fase captura para PCLK de 1,25 ns e allowance de estabilização de 3 ns.</desc>',
        '<rect width="100%" height="100%" fill="#0b1220"/>',
        '<style>text{font-family:system-ui,-apple-system,Segoe UI,sans-serif;fill:#eaf0f7}.muted{fill:#aebbd0}.grid{stroke:#334258;stroke-width:1}.small{font-size:14px}.body{font-size:16px}.title{font-size:23px;font-weight:700}.axis{font-size:13px}</style>',
        '<text x="42" y="38" class="title">A carga de linha altera o atraso máximo da WL</text>',
        '<text x="42" y="61" class="small muted">Mesmo netlist atual · captura→PCLK 1,25 ns · máximos entre 12 transições × 2 cargas Liberty de Q</text>',
    ]
    for tick in range(0, 7):
        ns = tick * .5
        x = left + ns * scale
        pieces.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}" class="grid"/>')
        pieces.append(f'<text x="{x:.1f}" y="{bottom + 23}" text-anchor="middle" class="axis muted">{ns:.1f}</text>')
    bar_colors = ("#62e0c1", "#ffcf70")
    labels = (f"{reference_ff:g} fF", f"{loaded_ff:.3f} fF")
    for i, profile in enumerate(PROFILES):
        center = top + 42 + i * 88
        pieces.append(f'<text x="42" y="{center + 6}" class="body">{profile_names[profile]}</text>')
        for j, value in enumerate((reference[profile], loaded[profile])):
            y = center - 22 + j * 27
            bar_width = value * scale
            pieces.append(f'<rect x="{left}" y="{y}" width="{bar_width:.1f}" height="18" rx="4" fill="{bar_colors[j]}"/>')
            pieces.append(f'<text x="{left - 10}" y="{y + 14}" text-anchor="end" class="small muted">{labels[j]}</text>')
            pieces.append(f'<text x="{left + bar_width + 8:.1f}" y="{y + 14}" class="small">{value:.3f} ns</text>')
    pieces.extend([
        f'<text x="{(left + right) / 2}" y="390" text-anchor="middle" class="body">Atraso da WL até 90% de VDD (ns)</text>',
        '<rect x="585" y="401" width="13" height="13" rx="2" fill="#62e0c1"/><text x="605" y="413" class="small muted">carga de referência</text>',
        '<rect x="770" y="401" width="13" height="13" rx="2" fill="#ffcf70"/><text x="790" y="413" class="small muted">Ceff máximo da linha</text>',
        '</svg>',
    ])
    return "\n".join(pieces) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True,
                        help="summary.csv for the reference WL capacitance")
    parser.add_argument("--loaded", type=Path, required=True,
                        help="summary.csv for the measured maximum row Ceff")
    parser.add_argument("--output", type=Path, required=True, help="output SVG")
    args = parser.parse_args()

    reference_manifest, reference_rows = load_campaign(args.reference)
    loaded_manifest, loaded_rows = load_campaign(args.loaded)
    reference_keys = {(r["profile"], r["old_address"], r["new_address"], r["dff_load_label"])
                      for r in reference_rows}
    loaded_keys = {(r["profile"], r["old_address"], r["new_address"], r["dff_load_label"])
                   for r in loaded_rows}
    if reference_keys != loaded_keys:
        raise SystemExit("Reference and loaded campaigns do not contain identical cases")
    if reference_manifest.get("netlist_sha256") != loaded_manifest.get("netlist_sha256"):
        raise SystemExit("Cannot compare load sensitivity across different decoder netlists")
    if reference_manifest.get("actual_clk_fall_ps") != loaded_manifest.get("actual_clk_fall_ps"):
        raise SystemExit("The campaigns use different CLK/PCLK falling edges")
    if reference_manifest.get("settling_allowance_ns") != loaded_manifest.get("settling_allowance_ns"):
        raise SystemExit("The campaigns use different settling allowances")
    reference_ff = float(reference_manifest["wordline_load"]["capacitance_per_wl_ff"])
    loaded_ff = float(loaded_manifest["wordline_load"]["capacitance_per_wl_ff"])
    if reference_ff == loaded_ff:
        raise SystemExit("The WL capacitance values must differ")
    for rows in (reference_rows, loaded_rows):
        if {float(row["capture_to_pclk_target_ps"]) for row in rows} != {1250.0}:
            raise SystemExit("The comparison is defined for a 1.25 ns capture-to-PCLK phase")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(svg(campaign_maxima(reference_rows), campaign_maxima(loaded_rows),
                               reference_ff, loaded_ff), encoding="utf-8")
    print(f"SVG: {args.output}")
    print(f"Decoder netlist SHA-256: {loaded_manifest['netlist_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
