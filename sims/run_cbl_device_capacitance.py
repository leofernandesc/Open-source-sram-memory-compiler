#!/usr/bin/env python3
"""Estimate schematic-level BL capacitance terms from SKY130 small-signal AC models."""

from __future__ import annotations

import argparse
import csv
import itertools
import math
import re
import subprocess
import tempfile
from pathlib import Path


MODEL_LIB = "/opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice"
AC_ROW_RE = re.compile(
    r"^\s*0\s+(?P<frequency>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
    r"\s+(?P<imag>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*$",
    re.MULTILINE,
)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corners",
        nargs="+",
        default=["tt", "ff", "ss", "fs", "sf"],
        choices=["tt", "ff", "ss", "fs", "sf"],
    )
    parser.add_argument("--vdd-values", nargs="+", type=float, default=[1.62, 1.80])
    parser.add_argument("--temps-c", nargs="+", type=float, default=[-40.0, 27.0, 125.0])
    parser.add_argument("--frequency-hz", type=float, default=1.0e6)
    parser.add_argument("--wacc-um", type=float, default=0.60)
    parser.add_argument("--wpre-um", type=float, default=0.42)
    parser.add_argument("--wsense-isolation-um", type=float, default=0.42)
    parser.add_argument("--timeout-s", type=float, default=30.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "sims" / "cbl_device_capacitance_pvt.csv",
    )
    return parser.parse_args()


def mos_geometry(width_um: float) -> tuple[float, float, float]:
    diffusion_um = 0.29
    area_um2 = width_um * diffusion_um
    perimeter_um = 2.0 * (width_um + diffusion_um)
    squares = diffusion_um / width_um
    return area_um2, perimeter_um, squares


def mos_instance(
    name: str,
    nodes: str,
    model: str,
    width_um: float,
) -> str:
    area, perimeter, squares = mos_geometry(width_um)
    return (
        f"X{name} {nodes} {model} l=0.15 w={width_um:g} nf=1 "
        f"ad={area:.9g} as={area:.9g} pd={perimeter:.9g} ps={perimeter:.9g} "
        f"nrd={squares:.9g} nrs={squares:.9g} sa=0 sb=0 sd=0"
    )


def ac_footer(frequency_hz: float) -> str:
    return (
        f".ac lin 1 {frequency_hz:.12g} {frequency_hz:.12g}\n"
        ".print ac imag(i(VBL))\n"
        ".end\n"
    )


def make_cell_access_deck(
    *, corner: str, vdd: float, temp_c: float, frequency_hz: float,
    width_um: float, q_state: int, orientation: str,
) -> str:
    q_voltage = vdd * q_state
    nodes = "q wl bl 0" if orientation == "bl_on_source" else "bl wl q 0"
    return (
        f".title cbl_cell_access_{corner}_{orientation}_q{q_state}\n"
        f".lib \"{MODEL_LIB}\" {corner}\n"
        f".temp {temp_c:g}\n"
        f"VBL bl 0 DC {vdd:g} AC 1\n"
        f"VQ q 0 {q_voltage:g}\n"
        "VWL wl 0 0\n"
        + mos_instance("ACC", nodes, "sky130_fd_pr__nfet_01v8", width_um)
        + "\n"
        + ac_footer(frequency_hz)
    )


def make_precharge_deck(
    *, corner: str, vdd: float, temp_c: float, frequency_hz: float, width_um: float,
) -> str:
    return (
        f".title cbl_precharge_{corner}\n"
        f".lib \"{MODEL_LIB}\" {corner}\n"
        f".temp {temp_c:g}\n"
        f"VDD vdd 0 {vdd:g}\n"
        f"VPRE prech 0 {vdd:g}\n"
        f"VBL bl 0 DC {vdd:g} AC 1\n"
        f"VBLB blb 0 {vdd:g}\n"
        + mos_instance("MPBL", "bl prech vdd vdd", "sky130_fd_pr__pfet_01v8", width_um)
        + "\n"
        + mos_instance("MPBLB", "blb prech vdd vdd", "sky130_fd_pr__pfet_01v8", width_um)
        + "\n"
        + mos_instance("MEQ", "bl prech blb vdd", "sky130_fd_pr__pfet_01v8", width_um)
        + "\n"
        + ac_footer(frequency_hz)
    )


def make_sense_input_deck(
    *, corner: str, vdd: float, temp_c: float, frequency_hz: float,
    width_um: float, latch_state: int, orientation: str,
) -> str:
    sa_voltage = vdd * latch_state
    nodes = "sa sclk bl 0" if orientation == "bl_on_source" else "bl sclk sa 0"
    return (
        f".title cbl_sense_{corner}_{orientation}_sa{latch_state}\n"
        f".lib \"{MODEL_LIB}\" {corner}\n"
        f".temp {temp_c:g}\n"
        f"VBL bl 0 DC {vdd:g} AC 1\n"
        f"VSA sa 0 {sa_voltage:g}\n"
        "VSCLK sclk 0 0\n"
        + mos_instance("ISO", nodes, "sky130_fd_pr__nfet_01v8", width_um)
        + "\n"
        + ac_footer(frequency_hz)
    )


def run_deck(ngspice: str, deck_text: str, timeout_s: float) -> tuple[float, str]:
    with tempfile.TemporaryDirectory(prefix="cbl-cap-") as temp_dir:
        deck = Path(temp_dir) / "cap.spice"
        deck.write_text(deck_text)
        result = subprocess.run(
            [ngspice, "-n", "-b", str(deck)],
            cwd=temp_dir,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_s,
        )
    output = result.stdout + "\n" + result.stderr
    if result.returncode != 0:
        raise RuntimeError(output.strip())
    match = AC_ROW_RE.search(output)
    if not match:
        raise RuntimeError(f"could not parse AC current from ngspice output:\n{output}")
    frequency = float(match.group("frequency"))
    imag_current = float(match.group("imag"))
    ceff_f = abs(imag_current) / (2.0 * math.pi * frequency)
    return ceff_f * 1.0e15, output


def main() -> int:
    args = parse_args()
    if args.frequency_hz <= 0:
        raise SystemExit("--frequency-hz must be positive")
    if any(not 0 < voltage <= 1.8 for voltage in args.vdd_values):
        raise SystemExit("This pre-layout characterization is limited to qualified VDD <= 1.8 V")

    rows: list[dict[str, object]] = []
    ngspice = "ngspice"
    for corner, vdd, temp_c in itertools.product(args.corners, args.vdd_values, args.temps_c):
        scenarios: list[tuple[str, str, str, str]] = []
        for q_state, orientation in itertools.product((0, 1), ("bl_on_source", "bl_on_drain")):
            scenarios.append((
                "cell_access",
                orientation,
                str(q_state),
                make_cell_access_deck(
                    corner=corner, vdd=vdd, temp_c=temp_c,
                    frequency_hz=args.frequency_hz, width_um=args.wacc_um,
                    q_state=q_state, orientation=orientation,
                ),
            ))
        scenarios.append((
            "precharge",
            "three_pmos_off",
            "na",
            make_precharge_deck(
                corner=corner, vdd=vdd, temp_c=temp_c,
                frequency_hz=args.frequency_hz, width_um=args.wpre_um,
            ),
        ))
        for latch_state, orientation in itertools.product((0, 1), ("bl_on_source", "bl_on_drain")):
            scenarios.append((
                "sense_input",
                orientation,
                str(latch_state),
                make_sense_input_deck(
                    corner=corner, vdd=vdd, temp_c=temp_c,
                    frequency_hz=args.frequency_hz,
                    width_um=args.wsense_isolation_um,
                    latch_state=latch_state, orientation=orientation,
                ),
            ))

        for block, orientation, state, deck_text in scenarios:
            row: dict[str, object] = {
                "block": block,
                "corner": corner,
                "vdd_v": vdd,
                "temp_c": temp_c,
                "orientation": orientation,
                "state": state,
                "frequency_hz": args.frequency_hz,
                "ceff_ff": "",
                "status": "ERROR",
                "error": "",
            }
            try:
                ceff_ff, _ = run_deck(ngspice, deck_text, args.timeout_s)
                row["ceff_ff"] = f"{ceff_ff:.9f}"
                row["status"] = "PASS"
            except (RuntimeError, subprocess.TimeoutExpired) as exc:
                row["error"] = str(exc).replace("\n", " | ")[:1000]
            rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "block", "corner", "vdd_v", "temp_c", "orientation", "state",
        "frequency_hz", "ceff_ff", "status", "error",
    ]
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    failures = [row for row in rows if row["status"] != "PASS"]
    for block in ("cell_access", "precharge", "sense_input"):
        values = [float(row["ceff_ff"]) for row in rows if row["block"] == block and row["status"] == "PASS"]
        if values:
            print(f"{block}: min={min(values):.6f} fF max={max(values):.6f} fF n={len(values)}")
    print(f"output={args.output}")
    print(f"failures={len(failures)} total={len(rows)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
