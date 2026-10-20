#!/usr/bin/env python3
"""Characterize SKY130 access-transistor gate capacitance for WL load budgeting."""

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
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
AC_ROW_RE = re.compile(
    rf"^\s*0\s+(?P<frequency>{NUMBER})\s+(?P<imag>{NUMBER})\s*$",
    re.MULTILINE,
)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corners", nargs="+", default=["tt", "ff", "ss", "fs", "sf"])
    p.add_argument("--vdd-values", nargs="+", type=float, default=[1.62, 1.80])
    p.add_argument("--temps-c", nargs="+", type=float, default=[-40.0, 27.0, 125.0])
    p.add_argument("--wacc-um", type=float, default=0.60)
    p.add_argument("--frequency-hz", type=float, default=1.0e6)
    p.add_argument("--timeout-s", type=float, default=30.0)
    p.add_argument(
        "--output",
        type=Path,
        default=root / "sims" / "wordline_access_gate_capacitance_pvt.csv",
    )
    return p.parse_args()


def mos_geometry(width_um: float) -> tuple[float, float, float]:
    diffusion_um = 0.29
    area_um2 = width_um * diffusion_um
    perimeter_um = 2.0 * (width_um + diffusion_um)
    squares = diffusion_um / width_um
    return area_um2, perimeter_um, squares


def make_deck(
    *, corner: str, vdd: float, temp_c: float, q_state: int,
    orientation: str, width_um: float, frequency_hz: float,
) -> str:
    area, perimeter, squares = mos_geometry(width_um)
    q_voltage = vdd * q_state
    nodes = "q wl bl 0" if orientation == "bl_on_source" else "bl wl q 0"
    return f"""* Access-NMOS gate capacitance for pre-layout wordline budgeting.
.lib "{MODEL_LIB}" {corner}
.temp {temp_c:g}
VBL bl 0 {vdd:g}
VQ q 0 {q_voltage:g}
VWL wl 0 DC 0 AC 1
XACC {nodes} sky130_fd_pr__nfet_01v8 l=0.15 w={width_um:g} nf=1 ad={area:.9g} as={area:.9g} pd={perimeter:.9g} ps={perimeter:.9g} nrd={squares:.9g} nrs={squares:.9g} sa=0 sb=0 sd=0
.ac lin 1 {frequency_hz:.12g} {frequency_hz:.12g}
.print ac imag(i(VWL))
.end
"""


def run_deck(text: str, timeout_s: float) -> float:
    with tempfile.TemporaryDirectory(prefix="wl-cap-") as td:
        deck = Path(td) / "wl_cap.spice"
        deck.write_text(text, encoding="utf-8")
        result = subprocess.run(
            ["ngspice", "-n", "-b", str(deck)],
            cwd=td,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_s,
        )
    output = result.stdout + "\n" + result.stderr
    if result.returncode != 0:
        raise RuntimeError(output[-1000:])
    match = AC_ROW_RE.search(output)
    if not match:
        raise RuntimeError(f"could not parse AC gate current:\n{output[-1000:]}")
    frequency = float(match.group("frequency"))
    imag_current = float(match.group("imag"))
    return abs(imag_current) / (2.0 * math.pi * frequency) * 1e15


def main() -> int:
    args = parse_args()
    if args.frequency_hz <= 0 or args.wacc_um <= 0:
        raise SystemExit("frequency and WACC must be positive")
    if any(not 0.0 < v <= 1.8 for v in args.vdd_values):
        raise SystemExit("characterization is limited to the qualified VDD <= 1.8 V range")

    rows: list[dict[str, object]] = []
    for corner, vdd, temp_c, q_state, orientation in itertools.product(
        args.corners,
        args.vdd_values,
        args.temps_c,
        (0, 1),
        ("bl_on_source", "bl_on_drain"),
    ):
        row: dict[str, object] = {
            "corner": corner,
            "vdd_v": vdd,
            "temp_c": temp_c,
            "q_state": q_state,
            "orientation": orientation,
            "wacc_um": args.wacc_um,
            "frequency_hz": args.frequency_hz,
            "cgate_ff": "",
            "status": "ERROR",
            "error": "",
        }
        try:
            row["cgate_ff"] = f"{run_deck(make_deck(corner=corner, vdd=vdd, temp_c=temp_c, q_state=q_state, orientation=orientation, width_um=args.wacc_um, frequency_hz=args.frequency_hz), args.timeout_s):.9f}"
            row["status"] = "PASS"
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            row["error"] = str(exc).replace("\n", " | ")[:1000]
        rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    failures = [row for row in rows if row["status"] != "PASS"]
    values = [float(row["cgate_ff"]) for row in rows if row["status"] == "PASS"]
    if values:
        cmax = max(values)
        print(f"access gate Cmax={cmax:.9f} fF over {len(values)} cases")
        print(f"8-bit row access-gate bound (16 gates)={16*cmax:.9f} fF")
        print(f"extra load beyond selected cell (14 gates)={14*cmax:.9f} fF")
    print(f"failures={len(failures)} total={len(rows)} output={args.output}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
