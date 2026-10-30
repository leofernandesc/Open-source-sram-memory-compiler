#!/usr/bin/env python3
"""Pre-layout SKY130A 6T hold/read SNM over a process/voltage/temp grid."""

from __future__ import annotations

import argparse
import csv
import itertools
import subprocess
import tempfile
from pathlib import Path

from run_bitcell_snm import DEFAULT_MODEL_LIB, make_deck, measure_snm, read_wrdata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corners", nargs="+", default=["tt", "ff", "ss", "fs", "sf"])
    parser.add_argument("--vdd-values", nargs="+", type=float, default=[1.62, 1.8, 1.95])
    parser.add_argument("--temps-c", nargs="+", type=float, default=[-40, 27, 125])
    parser.add_argument("--step", type=float, default=0.001)
    parser.add_argument("--wpu", type=float, default=0.42)
    parser.add_argument("--wpd", type=float, default=1.05)
    parser.add_argument("--wacc", type=float, default=0.60)
    parser.add_argument("--length", type=float, default=0.15)
    parser.add_argument("--model-lib", type=Path, default=DEFAULT_MODEL_LIB)
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).with_name("bitcell_snm_pvt_wpd1p05.csv")
    )
    args = parser.parse_args()
    if any(corner not in {"tt", "ff", "ss", "fs", "sf"} for corner in args.corners):
        parser.error("unsupported process corner")
    if any(not 0 < voltage <= 1.95 for voltage in args.vdd_values):
        parser.error("VDD must be >0 and <=1.95 V for the SKY130 01v8 models")
    if args.step <= 0:
        parser.error("step must be positive")

    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="bitcell-snm-pvt-") as temp_dir:
        workdir = Path(temp_dir)
        for corner, vdd, temp_c, mode in itertools.product(
            args.corners, args.vdd_values, args.temps_c, ("hold", "read")
        ):
            stem = f"{corner}_{vdd:g}V_{temp_c:g}C_{mode}"
            deck_path = workdir / f"{stem}.spice"
            data_path = workdir / f"{stem}.dat"
            deck_path.write_text(
                make_deck(
                    corner=corner,
                    mode=mode,
                    output_path=data_path,
                    model_lib=args.model_lib,
                    vdd=vdd,
                    step=args.step,
                    length=args.length,
                    wpu=args.wpu,
                    wpd=args.wpd,
                    wacc=args.wacc,
                    temp_c=temp_c,
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                ["ngspice", "-n", "-b", str(deck_path)],
                cwd=workdir,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0 or not data_path.exists():
                raise RuntimeError(
                    f"SNM simulation failed for {stem}:\n{result.stdout}\n{result.stderr}"
                )
            vin, vout = read_wrdata(data_path)
            snm = measure_snm(vin, vout)
            rows.append(
                {
                    "corner": corner,
                    "vdd_v": vdd,
                    "temp_c": temp_c,
                    "mode": mode,
                    "snm_v": f"{snm:.9f}",
                    "snm_mv": f"{snm * 1000:.3f}",
                    "wpu_um": args.wpu,
                    "wpd_um": args.wpd,
                    "wacc_um": args.wacc,
                    "length_um": args.length,
                    "dc_step_v": args.step,
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"SNM points: {len(rows)}")
    for mode in ("hold", "read"):
        worst = min((row for row in rows if row["mode"] == mode), key=lambda row: row["snm_v"])
        print(f"Worst {mode}: {worst['snm_mv']} mV at {worst['corner']}, "
              f"{worst['vdd_v']} V, {worst['temp_c']} C")
    print(f"CSV: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
