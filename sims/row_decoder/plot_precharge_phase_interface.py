#!/usr/bin/env python3
"""Plot a saved decoder/precharge phase-interface transient."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sims/row_decoder"))
from plot_row_decoder_review import read_raw


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--output-svg", type=Path, required=True)
    parser.add_argument("--output-png", type=Path, required=True)
    args = parser.parse_args()
    case_dir = args.case_dir.resolve()
    metadata = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    raw_path = case_dir / "waveform.raw"
    if not raw_path.is_file():
        raise SystemExit(f"waveform.raw not found: {raw_path}; rerun with --keep-raw")
    raw = read_raw(raw_path)
    t_ns = raw["time"] * 1e9
    nodes = metadata["signal_nodes"]

    def v(name: str) -> np.ndarray:
        key = name.lower()
        if not key.startswith("v("):
            key = f"v({key})"
        if key not in raw:
            raise SystemExit(f"Saved waveform is missing {key}")
        return raw[key]

    vdd = 1.62 if metadata["profile"] == "slow" else 1.8
    pclk = v(nodes["PCLK"])
    prech = v(nodes["PRECH"])
    selected = int(metadata["selected_row"])
    wl = v(nodes[f"WL{selected}"])
    bl, blb = v(nodes["BL0"]), v(nodes["BLB0"])
    timing = metadata["precharge_timing"]
    phase_source = metadata.get("phase_source", "ideal")
    pre_release = timing["precharge_releases"][-1]["precharge_release_s"] * 1e9
    pclk_rise = timing["precharge_releases"][-1]["pclk_rise_s"] * 1e9
    pclk_fall = timing["precharge_reassertions"][-1]["pclk_fall_s"] * 1e9
    pre_assert = timing["precharge_reassertions"][-1]["precharge_assert_s"] * 1e9

    fig, axes = plt.subplots(4, 1, figsize=(10.8, 8.4), sharex=True,
                             gridspec_kw={"height_ratios": [0.8, 0.8, 1.2, 1.2]})
    axes[0].plot(t_ns, pclk, color="#2458a6", lw=1.7)
    axes[0].set_ylabel("PCLK (V)")
    axes[1].step(t_ns, (prech < 0.5*vdd).astype(float), where="post",
                 color="#bf5b17", lw=1.7)
    axes[1].set_ylabel("PRECH active")
    axes[1].set_yticks([0, 1], labels=["off", "on"])
    axes[2].plot(t_ns, wl, color="#14834b", lw=1.5)
    axes[2].axhline(0.1*vdd, color="#777777", ls="--", lw=0.9,
                    label="10% VDD threshold")
    axes[2].set_ylabel(f"WL{selected} (V)")
    axes[2].legend(loc="upper right", frameon=False)
    axes[3].plot(t_ns, bl, label="BL0", color="#7c3c8c", lw=1.4)
    axes[3].plot(t_ns, blb, label="BLB0", color="#d28b00", lw=1.4)
    axes[3].axhline(0.9*vdd, color="#777777", ls="--", lw=0.9,
                    label="90% VDD threshold")
    axes[3].set_ylabel("Bitline (V)")
    axes[3].legend(loc="lower right", frameon=False, ncol=3)
    axes[3].set_xlabel("Time (ns)")

    for axis in axes:
        axis.grid(True, alpha=0.22)
        axis.axvline(pre_release, color="#bf5b17", ls=":", lw=1.0)
        axis.axvline(pclk_rise, color="#2458a6", ls=":", lw=1.0)
        axis.axvline(pclk_fall, color="#2458a6", ls="--", lw=1.0)
        axis.axvline(pre_assert, color="#bf5b17", ls="--", lw=1.0)
    axes[0].text(pre_release, 0.98*vdd,
                 f" PRECH release {pre_release:.2f} ns", va="top", fontsize=8)
    axes[0].text(pclk_rise, 0.70*vdd,
                 f" PCLK eval {pclk_rise:.2f} ns", va="top", fontsize=8)
    axes[0].text(pclk_fall, 0.98*vdd,
                 f" PCLK fall {pclk_fall:.2f} ns", va="top", fontsize=8)
    axes[0].text(pre_assert, 0.70*vdd,
                 f" PRECH reassert {pre_assert:.2f} ns", va="top", fontsize=8)
    axes[0].set_xlim(0, t_ns[-1])
    if phase_source == "xschem-tapped-delay-chain":
        source_label = "hierarchical Xschem SKY130 transistor phase source"
        source_note = ("Hierarchical Xschem phase logic; ideal CLK/VALID_ACCESS_Q. Decoder, WL and 8 precharge use PEX; "
                       "lumped BL loads; no 6T read/write path.")
    elif phase_source == "tapped-delay-chain":
        source_label = "generated-deck transistor-level tapped phase candidate"
        source_note = ("Generated transistor phase logic; ideal CLK/VALID_ACCESS_Q. Decoder, WL and 8 precharge use PEX; "
                       "lumped BL loads; no 6T read/write path.")
    else:
        source_label = "ideal PCLK/PRECH"
        source_note = ("Ideal PCLK/PRECH sources; decoder, WL driver and eight precharge leaves use SKY130A PEX. "
                       "Bitlines use capacitive loads; no 6T array/read/write path is included.")
    fig.suptitle("Dynamic row decoder and precharge phase interface\n"
                 f"{metadata['profile']} · {metadata['operation']} · address {metadata['old_address']}→{metadata['new_address']} · {source_label}",
                 y=0.99)
    fig.text(0.5, 0.005,
             source_note,
             ha="center", fontsize=7)
    fig.tight_layout(rect=(0, 0.035, 1, 0.94))
    args.output_svg.parent.mkdir(parents=True, exist_ok=True)
    args.output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output_svg)
    svg_lines = args.output_svg.read_text(encoding="utf-8").splitlines()
    args.output_svg.write_text("\n".join(line.rstrip() for line in svg_lines) + "\n",
                               encoding="utf-8")
    fig.savefig(args.output_png, dpi=180)
    print(args.output_svg)
    print(args.output_png)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
