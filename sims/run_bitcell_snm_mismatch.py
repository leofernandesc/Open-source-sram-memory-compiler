#!/usr/bin/env python3
"""Exploratory SNM mismatch sweep with two independent SKY130 inverter instances."""

from __future__ import annotations

import argparse
import csv
import math
import subprocess
import tempfile
from pathlib import Path

import numpy as np


MODEL_LIB = "/opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice"


def deck(mode: str, corner: str, vdd: float, temp_c: float, seed: int,
         data_path: Path, wpu: float, wpd: float, wacc: float,
         step: float) -> str:
    access = ""
    if mode == "read":
        access = (
            f"XACC_L out_l vdd vdd 0 sky130_fd_pr__nfet_01v8 l=0.15 w={wacc:g} nf=1\n"
            f"XACC_R out_r vdd vdd 0 sky130_fd_pr__nfet_01v8 l=0.15 w={wacc:g} nf=1\n"
        )
    return f"""* Two independent inverter VTCs for mismatch butterfly SNM.
.title bitcell_{mode}_mismatch_{corner}_{seed}
.lib \"{MODEL_LIB}\" {corner}
.temp {temp_c:g}
VDD vdd 0 {vdd:g}
VIN in 0 0
XPU_L out_l in vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w={wpu:g} nf=1
XPD_L out_l in 0 0 sky130_fd_pr__nfet_01v8 l=0.15 w={wpd:g} nf=1
XPU_R out_r in vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w={wpu:g} nf=1
XPD_R out_r in 0 0 sky130_fd_pr__nfet_01v8 l=0.15 w={wpd:g} nf=1
{access}.options ngbehavior=ps reltol=1e-6 vabstol=1e-9 iabstol=1e-12
.dc VIN 0 {vdd:g} {step:g}
.control
setseed {seed}
run
set wr_singlescale
set wr_vecnames
wrdata {data_path} v(in) v(out_l) v(out_r)
quit
.endc
.end
"""


def paired_snm(vin: np.ndarray, left: np.ndarray, right: np.ndarray) -> float:
    root_two = math.sqrt(2.0)
    left_x = (vin - left) / root_two
    left_y = (vin + left) / root_two
    right_x = (right - vin) / root_two
    right_y = (right + vin) / root_two
    left_order = np.argsort(left_x)
    right_order = np.argsort(right_x)
    lower = max(float(np.min(left_x)), float(np.min(right_x)))
    upper = min(float(np.max(left_x)), float(np.max(right_x)))
    samples = np.linspace(lower, upper, max(4001, len(vin) * 4))
    first = np.interp(samples, left_x[left_order], left_y[left_order])
    second = np.interp(samples, right_x[right_order], right_y[right_order])
    separation = np.abs(first - second) / root_two
    negative = separation[samples < 0]
    positive = separation[samples > 0]
    if not len(negative) or not len(positive):
        raise RuntimeError("butterfly lobes could not be separated")
    return float(min(np.max(negative), np.max(positive)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corner", default="sf_mm",
                        choices=["tt_mm", "ff_mm", "ss_mm", "fs_mm", "sf_mm"])
    parser.add_argument("--mode", default="read", choices=["hold", "read"])
    parser.add_argument("--vdd", type=float, default=1.62)
    parser.add_argument("--temp-c", type=float, default=125.0)
    parser.add_argument("--samples", type=int, default=200)
    parser.add_argument("--seed-base", type=int, default=1001)
    parser.add_argument("--step", type=float, default=0.001)
    parser.add_argument("--wpu", type=float, default=0.42)
    parser.add_argument("--wpd", type=float, default=1.26)
    parser.add_argument("--wacc", type=float, default=0.60)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).with_name("bitcell_read_snm_mismatch_sf_1p62_125.csv"))
    args = parser.parse_args()
    if not 0 < args.vdd <= 1.95 or args.samples < 1 or args.step <= 0:
        parser.error("VDD must be in (0,1.95], samples and step must be positive")

    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="bitcell-snm-mismatch-") as temp_dir:
        work = Path(temp_dir)
        for sample in range(args.samples):
            seed = args.seed_base + sample
            stem = f"{args.mode}_{args.corner}_{args.vdd:g}V_{args.temp_c:g}C_{seed}"
            deck_path = work / f"{stem}.spice"
            data_path = work / f"{stem}.dat"
            deck_path.write_text(
                deck(args.mode, args.corner, args.vdd, args.temp_c, seed,
                     data_path, args.wpu, args.wpd, args.wacc, args.step),
                encoding="utf-8",
            )
            result = subprocess.run(
                ["ngspice", "-n", "-b", str(deck_path)], cwd=work,
                text=True, capture_output=True, check=False,
            )
            if result.returncode != 0 or not data_path.exists():
                raise RuntimeError(
                    f"mismatch simulation failed for {stem}:\n"
                    f"{result.stdout}\n{result.stderr}"
                )
            data = np.loadtxt(data_path, skiprows=1)
            if data.ndim != 2 or data.shape[1] != 4:
                raise RuntimeError(f"unexpected VTC trace shape {data.shape} for {stem}")
            snm = paired_snm(data[:, 1], data[:, 2], data[:, 3])
            rows.append({
                "sample": sample + 1, "seed": seed, "corner": args.corner,
                "mode": args.mode, "vdd_v": args.vdd, "temp_c": args.temp_c,
                "wpu_um": args.wpu, "wpd_um": args.wpd, "wacc_um": args.wacc,
                "snm_v": f"{snm:.9f}", "snm_mv": f"{snm * 1000:.3f}",
            })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    values = np.asarray([float(row["snm_mv"]) for row in rows])
    print(f"N={len(rows)}, SNM min/mean/max="
          f"{values.min():.3f}/{values.mean():.3f}/{values.max():.3f} mV, "
          f"std={values.std(ddof=1) if len(values)>1 else 0:.3f} mV")
    print(f"CSV: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
