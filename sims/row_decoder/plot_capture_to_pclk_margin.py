#!/usr/bin/env python3
"""Render the measured slow/stress capture-to-PCLK phase grid as SVG."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from html import escape
from pathlib import Path


WIDTH = 1280
HEIGHT = 800
LEFT = 125
RIGHT = 70
TOP = 90
BOTTOM = 220
Y_MIN = -1200.0
Y_MAX = 1200.0
GUARD_PS = 250.0


def render(source: Path, output: Path) -> None:
    by_phase: dict[float, list[tuple[str, float]]] = defaultdict(list)
    with source.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["profile"] != "slow" or row["dff_load_label"] != "stress":
                continue
            phase = float(row["capture_to_pclk_target_ps"])
            lead = float(row["literal_settle_lead_to_pclk_ps"])
            by_phase[phase].append((row["case"], lead))

    phases = sorted(by_phase)
    if not phases or any(len(by_phase[phase]) != 12 for phase in phases):
        raise SystemExit("Expected twelve address transitions at every plotted phase")

    x0, x1 = LEFT, WIDTH - RIGHT
    y0, y1 = TOP, HEIGHT - BOTTOM

    def px(index: int, offset: float = 0.0) -> float:
        return x0 + index * (x1 - x0) / max(1, len(phases) - 1) + offset

    def py(value: float) -> float:
        return y1 - (value - Y_MIN) * (y1 - y0) / (Y_MAX - Y_MIN)

    lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
        '<title id="title">Margem medida entre estabilização dos literais e PCLK</title>',
        '<desc id="desc">Grade de 96 casos no perfil SS, 1,62 volts e menos 40 graus Celsius, com doze transições de endereço por fase. A linha mostra a menor margem medida. A linha tracejada em 250 ps indica o guard experimental.</desc>',
        '<rect width="100%" height="100%" fill="#101827"/>',
        '<style>text{font-family:system-ui,-apple-system,Segoe UI,sans-serif;fill:#e9eef5}.muted{fill:#aebbd0}.grid{stroke:#334258;stroke-width:1}.axis{stroke:#8190a7;stroke-width:1.5}.point{fill:#9ab0c9;fill-opacity:.48}.minline{fill:none;stroke:#62e0c1;stroke-width:4;stroke-linejoin:round;stroke-linecap:round}.minpoint{fill:#62e0c1;stroke:#101827;stroke-width:2}.guard{stroke:#ffcf70;stroke-width:3;stroke-dasharray:10 8}.recommended{stroke:#ffcf70;stroke-width:2;stroke-dasharray:6 7;opacity:.8}</style>',
        '<text x="125" y="43" font-size="27" font-weight="750">Captura → PCLK: menor margem de estabilização dos literais</text>',
        '<text x="125" y="70" class="muted" font-size="16">B7 pré-layout · SS / 1,62 V / −40 °C · carga stress de 9,00 fF no Q do registrador · 12 transições por fase</text>',
    ]

    # The positive region above the engineering guard is visually distinct.
    lines.append(f'<rect x="{x0}" y="{py(Y_MAX):.1f}" width="{x1-x0}" height="{py(GUARD_PS)-py(Y_MAX):.1f}" fill="#62e0c1" fill-opacity=".075"/>')
    lines.append(f'<rect x="{x0}" y="{py(GUARD_PS):.1f}" width="{x1-x0}" height="{py(Y_MIN)-py(GUARD_PS):.1f}" fill="#ff8e8e" fill-opacity=".045"/>')

    for tick in (-1000, -500, 0, 250, 500, 1000):
        y = py(float(tick))
        lines.append(f'<line class="grid" x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}"/>')
        lines.append(f'<text x="{x0-16}" y="{y+6:.1f}" text-anchor="end" class="muted" font-size="15">{tick}</text>')
    lines.append(f'<line class="guard" x1="{x0}" y1="{py(GUARD_PS):.1f}" x2="{x1}" y2="{py(GUARD_PS):.1f}"/>')
    lines.append(f'<text x="{x1-8}" y="{py(GUARD_PS)-10:.1f}" text-anchor="end" fill="#ffcf70" font-size="15">guard experimental: 250 ps</text>')

    recommended_phase = 1500.0
    if recommended_phase in phases:
        idx = phases.index(recommended_phase)
        lines.append(f'<line class="recommended" x1="{px(idx):.1f}" y1="{y0}" x2="{px(idx):.1f}" y2="{y1}"/>')

    minima: list[tuple[float, float]] = []
    for i, phase in enumerate(phases):
        rows = by_phase[phase]
        # Keep all observations visible; horizontal offsets distinguish the twelve pairs.
        for j, (case, lead) in enumerate(rows):
            offset = (j - 5.5) * 3.1
            lines.append(f'<circle class="point" cx="{px(i, offset):.1f}" cy="{py(lead):.1f}" r="5"><title>{escape(case)}: {lead:.1f} ps</title></circle>')
        minimum = min(lead for _, lead in rows)
        minima.append((phase, minimum))
        lines.append(f'<text x="{px(i):.1f}" y="{y1+30}" text-anchor="middle" class="muted" font-size="14">{phase/1000:g}</text>')

    path = " ".join(
        f'{"M" if i == 0 else "L"}{px(i):.1f},{py(value):.1f}'
        for i, (_, value) in enumerate(minima)
    )
    lines.append(f'<path class="minline" d="{path}"/>')
    for i, (phase, value) in enumerate(minima):
        lines.append(f'<circle class="minpoint" cx="{px(i):.1f}" cy="{py(value):.1f}" r="7"><title>Fase {phase:g} ps: pior lead {value:.1f} ps</title></circle>')
        if phase in (1250.0, 1500.0):
            dy = -14 if value >= 0 else 20
            lines.append(f'<text x="{px(i):.1f}" y="{py(value)+dy:.1f}" text-anchor="middle" fill="#62e0c1" font-size="14" font-weight="700">{value:.0f} ps</text>')

    lines.extend([
        f'<line class="axis" x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}"/>',
        f'<line class="axis" x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}"/>',
        f'<text x="{(x0+x1)/2:.1f}" y="{HEIGHT-110}" text-anchor="middle" font-size="17">Atraso captura → cruzamento de 50% de PCLK (ns)</text>',
        f'<text x="38" y="{(y0+y1)/2:.1f}" text-anchor="middle" font-size="17" transform="rotate(-90 38 {(y0+y1)/2:.1f})">Lead do último literal estabilizado até PCLK (ps)</text>',
        '<circle cx="152" cy="735" r="5" class="point"/><text x="168" y="741" class="muted" font-size="14">12 transições por fase</text>',
        '<line x1="380" y1="735" x2="430" y2="735" class="minline"/><text x="441" y="741" class="muted" font-size="14">pior caso por fase</text>',
        '<text x="720" y="741" fill="#ffcf70" font-size="14">fase de 1,50 ns selecionada para os próximos testes</text>',
        '<text x="125" y="784" class="muted" font-size="12">Fonte: capture_to_pclk_slow_coarse/summary.csv · 96 medições · o guard é uma margem experimental, não setup/hold nem Fmax.</text>',
        '</svg>',
    ])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_png(source: Path, output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    by_phase: dict[float, list[float]] = defaultdict(list)
    with source.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["profile"] == "slow" and row["dff_load_label"] == "stress":
                by_phase[float(row["capture_to_pclk_target_ps"])].append(
                    float(row["literal_settle_lead_to_pclk_ps"])
                )
    phases = sorted(by_phase)
    minima = [min(by_phase[phase]) for phase in phases]
    if not phases or any(len(by_phase[phase]) != 12 for phase in phases):
        raise SystemExit("Expected twelve address transitions at every plotted phase")

    plt.rcParams.update({
        "figure.facecolor": "#101827", "axes.facecolor": "#101827",
        "axes.edgecolor": "#8190a7", "axes.labelcolor": "#e9eef5",
        "xtick.color": "#aebbd0", "ytick.color": "#aebbd0",
        "text.color": "#e9eef5", "font.family": "DejaVu Sans",
    })
    fig, ax = plt.subplots(figsize=(12.8, 8), constrained_layout=True)
    x = [phase / 1000 for phase in phases]
    ax.axhspan(GUARD_PS, Y_MAX, color="#62e0c1", alpha=0.08, zorder=0)
    ax.axhline(GUARD_PS, color="#ffcf70", linestyle="--", linewidth=2.2,
               label="Guard experimental: 250 ps")
    if 1500.0 in phases:
        ax.axvline(1.5, color="#ffcf70", linestyle=":", linewidth=2,
                   label="Fase selecionada: 1,50 ns")
    for phase, values in zip(x, (by_phase[p] for p in phases)):
        ax.scatter([phase] * len(values), values, s=34, color="#9ab0c9",
                   alpha=0.58, edgecolors="none", zorder=2)
    ax.plot(x, minima, color="#62e0c1", marker="o", markersize=8,
            linewidth=3, label="Pior caso por fase", zorder=3)
    for phase_ps, phase_ns, value in zip(phases, x, minima):
        if phase_ps in (1250.0, 1500.0):
            ax.annotate(f"{value:.0f} ps", (phase_ns, value), xytext=(0, -19),
                        textcoords="offset points", ha="center", color="#62e0c1",
                        fontweight="bold")
    ax.set_title("Captura → PCLK: menor margem de estabilização dos literais\n"
                 "B7 pré-layout · SS / 1,62 V / −40 °C · carga stress de 9,00 fF no Q · 12 transições por fase",
                 loc="left", pad=18, fontweight="bold")
    ax.set_xlabel("Atraso captura → cruzamento de 50% de PCLK (ns)")
    ax.set_ylabel("Lead do último literal estabilizado até PCLK (ps)")
    ax.set_xticks(x, [f"{phase:g}" for phase in x])
    ax.set_ylim(Y_MIN, Y_MAX)
    ax.set_yticks([-1000, -500, 0, 250, 500, 1000])
    ax.grid(True, color="#334258", linewidth=0.8, alpha=0.9)
    ax.legend(loc="upper left", frameon=True, facecolor="#172337", edgecolor="#334258")
    fig.text(0.01, -0.01,
             "Fonte: capture_to_pclk_slow_coarse/summary.csv · 96 medições · "
             "guard experimental, não setup/hold nem Fmax.",
             color="#aebbd0", fontsize=9)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Capture-to-PCLK summary.csv")
    parser.add_argument("--output", type=Path, required=True, help="Destination SVG path")
    parser.add_argument("--png-output", type=Path, help="Optional PNG export (requires matplotlib)")
    args = parser.parse_args()
    render(args.input, args.output)
    if args.png_output:
        render_png(args.input, args.png_output)


if __name__ == "__main__":
    main()
