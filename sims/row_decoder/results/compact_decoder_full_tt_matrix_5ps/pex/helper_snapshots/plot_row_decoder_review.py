#!/usr/bin/env python3
"""Plot an archived binary real ngspice waveform and its decoder run manifest."""
import argparse
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def read_raw(path):
    header, binary = path.read_bytes().split(b"Binary:\n", 1)
    text = header.decode()
    if "Flags: real" not in text or "fastaccess" in text.lower():
        raise ValueError("Expected a real, point-major binary ngspice raw file")
    nv = int(re.search(r"No. Variables:\s*(\d+)", text)[1])
    count = int(re.search(r"No. Points:\s*(\d+)", text)[1])
    names = [line.split()[1].lower() for line in text.split("Variables:\n")[1].splitlines()
             if line.strip()]
    if len(names) != nv or len(binary) != count * nv * 8:
        raise ValueError("Raw header and data dimensions disagree")
    data = np.frombuffer(binary, dtype=np.float64).reshape(count, nv)
    return {name: data[:, i] for i, name in enumerate(names)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    traces = read_raw(args.raw)
    manifest = json.loads(args.manifest.read_text())
    time = traces["time"] * 1e9
    nodes = manifest["node_mapping"]
    fig, axes = plt.subplots(3, 1, figsize=(11, 9), constrained_layout=True)
    axes[0].plot(time, traces[f"v({nodes['PCLK'].lower()})"], label="PCLK")
    # Inputs in the preserved testbench schedule.
    axes[0].plot(time, traces["v(net3)"], label="A0", linestyle="--")
    axes[0].plot(time, traces["v(net4)"], label="A1", linestyle=":")
    axes[0].set_title("Stimulus and address history")
    axes[0].legend(ncol=3, loc="upper left")
    for i in range(4):
        axes[1].plot(time, traces[f"v(x1.n{i})"], label=f"N{i}", linewidth=1.3)
    axes[1].axhline(manifest["output_nmos_vgs_upper_screen_v"], color="firebrick",
                    linestyle="--", label="1.95 V model VGS upper envelope")
    axes[1].axhline(manifest["vdd_v"], color="gray", linestyle=":", label="VDD")
    axes[1].set_title("Dynamic nodes and output NMOS VGS (sources at VSS)")
    axes[1].legend(ncol=3, loc="lower right", fontsize=9)
    axes[2].plot(time, traces[f"v({nodes['PCLK'].lower()})"], label="PCLK", color="gray")
    for output in ("DEC0", "WL0"):
        axes[2].plot(time, traces[f"v({nodes[output].lower()})"], label=output)
    axes[2].set_title("Selected row 00: decoder and loaded wordline rise")
    axes[2].set_xlim(9.95, 10.8)
    axes[2].legend(ncol=3, loc="lower right")
    for ax in axes[:2]:
        ax.set_xlim(0, 90)
        for start in (10, 30, 50, 70):
            ax.axvspan(start, start + 10, color="seagreen", alpha=0.05)
    for ax in axes:
        ax.set_ylabel("Voltage (V)")
        ax.set_xlabel("Time (ns)")
        ax.grid(alpha=0.2)
    caption = (f"Pre-layout {manifest['candidate']}, {manifest['corner'].upper()}, "
               f"VDD={manifest['vdd_v']:g} V, T={manifest['temperature_c']:g} C; "
               f"M8 W={manifest['decoder_devices']['M8']['W']:g} um; "
               f"PCLK edges={manifest['clock_rise_ps']:g} ps; "
               f"WL loads={manifest['wl_capacitance_ff'][0]:g} fF each")
    fig.suptitle(caption, fontsize=11)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=160)
    plt.close(fig)
    print(args.output)


if __name__ == "__main__":
    main()
