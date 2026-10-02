#!/usr/bin/env python3
"""Audit six MOS terminal-voltage magnitudes during pre-layout read pulses."""

from __future__ import annotations

import argparse
import csv
import itertools
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from run_bitcell_read_sweep import make_deck


DEVICE_NODES = {
    "PU_L": ("q", "qb", "vdd", "vdd"),
    "PU_R": ("qb", "q", "vdd", "vdd"),
    "PD_L": ("q", "qb", "0", "0"),
    "PD_R": ("qb", "q", "0", "0"),
    "ACC_L": ("q", "wl", "bl", "0"),
    "ACC_R": ("qb", "wl", "blb", "0"),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deck", type=Path,
                        default=Path(__file__).with_name("tb_bitcell_6t_read.spice"))
    parser.add_argument("--corners", nargs="+", default=["tt", "ff", "ss", "fs", "sf"])
    parser.add_argument("--vdd-values", nargs="+", type=float, default=[1.95])
    parser.add_argument("--temps-c", nargs="+", type=float, default=[-40, 27, 125])
    parser.add_argument("--cap-f", type=float, default=50.0)
    parser.add_argument("--wl-edge-ps", type=float, default=50.0,
                        help="Ideal WL rise/fall edge duration in ps.")
    parser.add_argument("--wpu", type=float, default=0.42)
    parser.add_argument("--wpd", type=float, default=1.26)
    parser.add_argument("--wacc", type=float, default=0.60)
    parser.add_argument("--limit-v", type=float, default=1.95)
    parser.add_argument("--start-ns", type=float, default=1.0,
                        help="Ignore UIC startup before this time; default 1 ns.")
    parser.add_argument("--debug-trace", action="store_true")
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).with_name("bitcell_read_terminal_audit.csv"))
    args = parser.parse_args()
    if any(c not in {"tt", "ff", "ss", "fs", "sf"} for c in args.corners):
        parser.error("unsupported corner")
    if any(not 0 < v <= 1.95 for v in args.vdd_values):
        parser.error("VDD must be >0 and <=1.95 V for SKY130 01v8 models")
    if args.wl_edge_ps <= 0:
        parser.error("WL edge duration must be positive")

    template = args.deck.read_text(encoding="utf-8")
    template, edge_count = re.subn(
        r"^(VWL wl 0 PULSE\(0 \S+ 20n) \S+ \S+( 10n 40n\))$",
        rf"\g<1> {args.wl_edge_ps:g}p {args.wl_edge_ps:g}p\g<2>",
        template, count=1, flags=re.MULTILINE,
    )
    if edge_count != 1:
        raise RuntimeError("could not set WL edge duration in read template")
    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="bitcell-terminal-audit-") as temp_dir:
        work = Path(temp_dir)
        for corner, vdd, temp_c, state in itertools.product(
            args.corners, args.vdd_values, args.temps_c, (0, 1)
        ):
            stem = f"read_{corner}_{vdd:g}V_{temp_c:g}C_q{state}"
            path = work / f"{stem}.spice"
            data_path = work / f"{stem}.dat"
            deck_text = make_deck(
                template, corner, args.cap_f, state, str(work / f"{stem}.raw"),
                args.wpu, args.wpd, args.wacc, vdd, temp_c,
            )
            deck_text, count = re.subn(
                r"^write\s+\S+\s+all\s*$",
                "set wr_singlescale\nset wr_vecnames\n"
                f"wrdata {data_path} v(Q) v(QB) v(bl) v(blb) v(wl) v(vdd)",
                deck_text, count=1, flags=re.MULTILINE,
            )
            if count != 1:
                raise RuntimeError("could not replace raw writer with terminal trace")
            path.write_text(deck_text, encoding="utf-8")
            result = subprocess.run(
                ["ngspice", "-n", "-b", str(path)], cwd=work,
                capture_output=True, text=True, check=False,
            )
            if result.returncode != 0 or not data_path.exists():
                raise RuntimeError(
                    f"terminal trace failed for {stem}:\n{result.stdout}\n{result.stderr}"
                )
            data = np.loadtxt(data_path, skiprows=1)
            if data.ndim != 2 or data.shape[1] != 7:
                raise RuntimeError(f"unexpected trace shape {data.shape} for {stem}")
            if args.debug_trace:
                print(f"{stem}: {data_path.read_text(encoding='utf-8').splitlines()[0]}")
                print(f"ranges: min={data.min(axis=0)}, max={data.max(axis=0)}")
            data = data[data[:, 0] >= args.start_ns * 1e-9]
            if not len(data):
                raise RuntimeError(f"no trace samples after {args.start_ns} ns")
            time = data[:, 0]
            voltages = dict(zip(("q", "qb", "bl", "blb", "wl", "vdd"),
                                (data[:, i] for i in range(1, 7)), strict=True))
            voltages["0"] = np.zeros_like(time)
            for device, (drain, gate, source, bulk) in DEVICE_NODES.items():
                metrics = {
                    "vgs": voltages[gate] - voltages[source],
                    "vgd": voltages[gate] - voltages[drain],
                    "vds": voltages[drain] - voltages[source],
                    "vbs": voltages[bulk] - voltages[source],
                }
                for metric, values in metrics.items():
                    index = int(np.argmax(np.abs(values)))
                    max_abs = float(abs(values[index]))
                    rows.append({
                        "corner": corner, "vdd_v": vdd, "temp_c": temp_c,
                        "cap_f": args.cap_f, "stored_q": state, "device": device,
                        "wl_edge_ps": args.wl_edge_ps,
                        "metric": metric, "max_abs_v": f"{max_abs:.9f}",
                        "signed_at_peak_v": f"{values[index]:.9f}",
                        "peak_time_ns": f"{time[index] * 1e9:.6f}",
                        "analysis_start_ns": args.start_ns,
                        "limit_v": args.limit_v,
                        "above_limit": max_abs > args.limit_v + 1e-6,
                    })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    worst = max(rows, key=lambda row: float(row["max_abs_v"]))
    count = sum(row["above_limit"] for row in rows)
    print(f"Terminal metric limit flags: {count}/{len(rows)}")
    print(f"Worst magnitude: {worst['max_abs_v']} V, {worst['device']} {worst['metric']}, "
          f"{worst['corner']}, {worst['vdd_v']} V, {worst['temp_c']} C")
    print(f"CSV: {args.output}")
    return 0 if count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
