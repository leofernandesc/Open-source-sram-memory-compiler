#!/usr/bin/env python3
"""Measure hold/read SNM for the SKY130A 6T bitcell butterfly curves."""

from __future__ import annotations

import argparse
import csv
import math
import subprocess
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


DEFAULT_MODEL_LIB = Path(
    "/opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice"
)


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corners",
        nargs="+",
        default=["tt", "ff", "ss", "fs", "sf"],
        choices=["tt", "ff", "ss", "fs", "sf"],
    )
    parser.add_argument("--vdd", type=float, default=1.8)
    parser.add_argument("--step", type=float, default=0.001)
    parser.add_argument("--wpu", type=float, default=0.42)
    parser.add_argument("--wpd", type=float, default=1.26)
    parser.add_argument("--wacc", type=float, default=0.60)
    parser.add_argument("--length", type=float, default=0.15)
    parser.add_argument("--model-lib", type=Path, default=DEFAULT_MODEL_LIB)
    parser.add_argument(
        "--summary",
        type=Path,
        default=project_root / "sims" / "bitcell_snm_summary.csv",
    )
    parser.add_argument(
        "--curves",
        type=Path,
        default=project_root / "sims" / "bitcell_snm_curves.csv",
    )
    parser.add_argument(
        "--plot",
        type=Path,
        default=project_root / "docs" / "assets" / "bitcell_6t_snm_butterfly.png",
    )
    return parser.parse_args()


def make_deck(
    *,
    corner: str,
    mode: str,
    output_path: Path,
    model_lib: Path,
    vdd: float,
    step: float,
    length: float,
    wpu: float,
    wpd: float,
    wacc: float,
    temp_c: float = 27.0,
) -> str:
    access_device = ""
    if mode == "read":
        access_device = (
            "XACC OUT VDD VDD 0 sky130_fd_pr__nfet_01v8 "
            f"l={length:g} w={wacc:g} nf=1\n"
        )
    return f"""* SKY130A 6T SRAM {mode} SNM inverter VTC.
.title bitcell_6t_{mode}_snm_{corner}
.lib \"{model_lib}\" {corner}
.temp {temp_c:g}

VDD VDD 0 {vdd:g}
VIN IN 0 0
XPU OUT IN VDD VDD sky130_fd_pr__pfet_01v8 l={length:g} w={wpu:g} nf=1
XPD OUT IN 0 0 sky130_fd_pr__nfet_01v8 l={length:g} w={wpd:g} nf=1
{access_device}.options ngbehavior=ps reltol=1e-6 vabstol=1e-9 iabstol=1e-12
.dc VIN 0 {vdd:g} {step:g}

.control
run
set wr_singlescale
set wr_vecnames
wrdata {output_path} v(IN) v(OUT)
quit
.endc
.end
"""


def read_wrdata(path: Path) -> tuple[np.ndarray, np.ndarray]:
    rows: list[list[float]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            values = [float(token) for token in line.split()]
        except ValueError:
            continue
        if len(values) >= 2:
            rows.append(values)
    if not rows:
        raise RuntimeError(f"ngspice did not write numeric VTC data to {path}")
    data = np.asarray(rows, dtype=float)
    return data[:, 0], data[:, -1]


def measure_snm(vin: np.ndarray, vout: np.ndarray) -> float:
    root_two = math.sqrt(2.0)
    rotated_x = (vin - vout) / root_two
    rotated_y = (vin + vout) / root_two

    order = np.argsort(rotated_x)
    first_x = rotated_x[order]
    first_y = rotated_y[order]
    mirror_x = -rotated_x
    mirror_order = np.argsort(mirror_x)
    second_x = mirror_x[mirror_order]
    second_y = rotated_y[mirror_order]

    x_min = max(float(np.min(first_x)), float(np.min(second_x)))
    x_max = min(float(np.max(first_x)), float(np.max(second_x)))
    sample_count = max(4001, len(vin) * 4)
    x_queries = np.linspace(x_min, x_max, sample_count)
    first_curve = np.interp(x_queries, first_x, first_y)
    second_curve = np.interp(x_queries, second_x, second_y)
    square_side = np.abs(first_curve - second_curve) / root_two
    negative_lobe = square_side[x_queries < 0]
    positive_lobe = square_side[x_queries > 0]
    if not len(negative_lobe) or not len(positive_lobe):
        raise RuntimeError("could not separate both butterfly lobes")
    best_side = float(min(np.max(negative_lobe), np.max(positive_lobe)))
    if best_side <= 0:
        raise RuntimeError("could not locate both butterfly lobes")
    return best_side


def simulate_vtc(
    workdir: Path, corner: str, mode: str, args: argparse.Namespace
) -> tuple[np.ndarray, np.ndarray]:
    stem = f"snm_{mode}_{corner}"
    data_path = workdir / f"{stem}.dat"
    deck_path = workdir / f"{stem}.spice"
    deck_path.write_text(
        make_deck(
            corner=corner,
            mode=mode,
            output_path=data_path,
            model_lib=args.model_lib,
            vdd=args.vdd,
            step=args.step,
            length=args.length,
            wpu=args.wpu,
            wpd=args.wpd,
            wacc=args.wacc,
            temp_c=27.0,
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        ["ngspice", "-n", "-b", str(deck_path)],
        cwd=workdir,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 or not data_path.exists():
        output = f"{result.stdout}\n{result.stderr}".strip()
        raise RuntimeError(f"ngspice failed for {corner}/{mode}:\n{output}")
    return read_wrdata(data_path)


def write_outputs(
    results: dict[tuple[str, str], tuple[np.ndarray, np.ndarray, float]],
    args: argparse.Namespace,
) -> None:
    for path in (args.summary, args.curves, args.plot):
        path.parent.mkdir(parents=True, exist_ok=True)

    with args.summary.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "corner",
                "mode",
                "snm_v",
                "snm_mv",
                "vdd_v",
                "wpu_um",
                "wpd_um",
                "wacc_um",
                "length_um",
                "dc_step_v",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for corner in args.corners:
            for mode in ("hold", "read"):
                snm = results[(corner, mode)][2]
                writer.writerow(
                    {
                        "corner": corner,
                        "mode": mode,
                        "snm_v": f"{snm:.9f}",
                        "snm_mv": f"{snm * 1000:.3f}",
                        "vdd_v": args.vdd,
                        "wpu_um": args.wpu,
                        "wpd_um": args.wpd,
                        "wacc_um": args.wacc,
                        "length_um": args.length,
                        "dc_step_v": args.step,
                    }
                )

    with args.curves.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file, lineterminator="\n")
        writer.writerow(("corner", "mode", "vin_v", "vout_v"))
        for corner in args.corners:
            for mode in ("hold", "read"):
                vin, vout, _ = results[(corner, mode)]
                writer.writerows(
                    (corner, mode, f"{x:.9f}", f"{y:.9f}")
                    for x, y in zip(vin, vout, strict=True)
                )

    figure, axes = plt.subplots(
        len(args.corners), 2, figsize=(12, 4 * len(args.corners)), squeeze=False
    )
    for row, corner in enumerate(args.corners):
        for column, mode in enumerate(("hold", "read")):
            vin, vout, snm = results[(corner, mode)]
            axis = axes[row][column]
            axis.plot(vin, vout, label="VTC", linewidth=1.5)
            axis.plot(vout, vin, label="VTC espelhada", linewidth=1.5)
            axis.plot((0, args.vdd), (0, args.vdd), "--", color="0.7", linewidth=0.8)
            axis.set(
                title=f"{corner.upper()} / {mode.upper()} — SNM={snm * 1000:.1f} mV",
                xlabel="Vin (V)",
                ylabel="Vout (V)",
                xlim=(0, args.vdd),
                ylim=(0, args.vdd),
                aspect="equal",
            )
            axis.grid(True, alpha=0.25)
            axis.legend(loc="best")
    figure.suptitle(
        "SKY130A SRAM 6T — curvas borboleta\n"
        f"WPU={args.wpu:g} µm, WPD={args.wpd:g} µm, "
        f"WACC={args.wacc:g} µm, L={args.length:g} µm",
        fontsize=14,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.98))
    figure.savefig(args.plot, dpi=180)
    plt.close(figure)


def main() -> int:
    args = parse_args()
    results: dict[tuple[str, str], tuple[np.ndarray, np.ndarray, float]] = {}
    with tempfile.TemporaryDirectory(prefix="bitcell-snm-") as temp_dir:
        workdir = Path(temp_dir)
        for corner in args.corners:
            for mode in ("hold", "read"):
                vin, vout = simulate_vtc(workdir, corner, mode, args)
                results[(corner, mode)] = (vin, vout, measure_snm(vin, vout))

    write_outputs(results, args)
    print("corner  hold_snm(mV)  read_snm(mV)")
    for corner in args.corners:
        hold_snm = results[(corner, "hold")][2] * 1000
        read_snm = results[(corner, "read")][2] * 1000
        print(f"{corner:>6}  {hold_snm:>12.3f}  {read_snm:>12.3f}")
    print(f"Summary: {args.summary}")
    print(f"Curves:  {args.curves}")
    print(f"Plot:    {args.plot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
