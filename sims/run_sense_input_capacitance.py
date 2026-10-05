#!/usr/bin/env python3
"""Measure BL/BLB input capacitance of the Xschem sense amp during sampling."""

from __future__ import annotations

import argparse
import csv
import itertools
import subprocess
from pathlib import Path

from run_cbl_device_capacitance import run_deck
from run_sense_amp_characterization import MODEL_LIB, sense_pex_subckt, sense_subckt


def make_deck(
    *, subckt: str, corner: str, vdd: float, temp_c: float,
    probe: str, frequency_hz: float, discharge: str, delta_mv: float,
) -> str:
    bl_ac, blb_ac = (1, 0) if probe == "BL" else (0, 1)
    bl_dc = vdd - delta_mv / 1000 if discharge == "BL" else vdd
    blb_dc = vdd - delta_mv / 1000 if discharge == "BLB" else vdd
    return f"""* Sense input small-signal capacitance, sampling phase SCLK=0.
.lib "{MODEL_LIB}" {corner}
.temp {temp_c:g}
{subckt}
VDD vdd 0 {vdd:g}
VSCLK sclk 0 0
VBL bl 0 DC {bl_dc:g} AC {bl_ac}
VBLB blb 0 DC {blb_dc:g} AC {blb_ac}
XSA bl blb sa sab sclk vdd 0 sense_amp_core
.options ngbehavior=ps reltol=1e-5 vabstol=1e-9 iabstol=1e-12
.ac lin 1 {frequency_hz:.12g} {frequency_hz:.12g}
.print ac imag(i(V{probe}))
.end
"""


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corners", nargs="+", default=["tt", "ff", "ss", "fs", "sf"])
    parser.add_argument("--vdd-values", nargs="+", type=float, default=[1.62, 1.80])
    parser.add_argument("--temps-c", nargs="+", type=float, default=[-40, 27, 125])
    parser.add_argument("--frequency-hz", type=float, default=1e6)
    parser.add_argument("--delta-mv", nargs="+", type=float, default=[0.0])
    parser.add_argument("--timeout-s", type=float, default=45.0)
    parser.add_argument("--pex", action="store_true", help="Use the canonical Magic RC-extracted sense-amplifier netlist.")
    parser.add_argument(
        "--pex-netlist",
        type=Path,
        default=None,
        help="Optional sense PEX override; implies --pex.",
    )
    parser.add_argument("--schematic", type=Path, default=root / "cells" / "sense_amp.sch")
    parser.add_argument(
        "--output", type=Path,
        default=root / "sims" / "sense_input_capacitance_pvt.csv",
    )
    args = parser.parse_args()
    if any(not 0 < voltage <= 1.80 for voltage in args.vdd_values):
        parser.error("VDD must be within the 1.80 V qualification ceiling")
    if any(delta < 0 or delta >= 1000 * min(args.vdd_values) for delta in args.delta_mv):
        parser.error("each discharge delta must be >=0 and below the minimum VDD")
    if args.pex or args.pex_netlist is not None:
        subckt, _ = sense_pex_subckt(root, args.pex_netlist)
    else:
        subckt = sense_subckt(args.schematic)
    rows: list[dict[str, object]] = []
    for corner, vdd, temp_c, delta_mv, discharge, probe in itertools.product(
        args.corners, args.vdd_values, args.temps_c, args.delta_mv,
        ("BL", "BLB"), ("BL", "BLB")
    ):
        row: dict[str, object] = {
            "corner": corner, "vdd_v": vdd, "temp_c": temp_c,
            "probe": probe, "discharge": discharge, "delta_mv": delta_mv,
            "frequency_hz": args.frequency_hz,
            "ceff_ff": "", "status": "ERROR", "error": "",
        }
        try:
            ceff_ff, _ = run_deck(
                "ngspice",
                make_deck(
                    subckt=subckt, corner=corner, vdd=vdd, temp_c=temp_c,
                    probe=probe, frequency_hz=args.frequency_hz,
                    discharge=discharge, delta_mv=delta_mv,
                ),
                args.timeout_s,
            )
            row["ceff_ff"] = f"{ceff_ff:.9f}"
            row["status"] = "PASS"
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            row["error"] = str(exc).replace("\n", " | ")[:1000]
        rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    values = [float(row["ceff_ff"]) for row in rows if row["status"] == "PASS"]
    failures = len(rows) - len(values)
    print(f"sense input Ceff: {len(values)}/{len(rows)} PASS")
    if values:
        print(f"range: {min(values):.6f}..{max(values):.6f} fF; CSV: {args.output}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
