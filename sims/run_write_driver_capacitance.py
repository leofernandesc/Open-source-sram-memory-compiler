#!/usr/bin/env python3
"""Characterize off-state write-driver capacitance seen by BL/BLB in PVT."""

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
AC_ROW_RE = re.compile(rf"^\s*0\s+(?P<frequency>{NUMBER})\s+(?P<imag>{NUMBER})\s*$", re.MULTILINE)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corners", nargs="+", default=["tt", "ff", "ss", "fs", "sf"])
    p.add_argument("--vdd-values", nargs="+", type=float, default=[1.62, 1.80])
    p.add_argument("--temps-c", nargs="+", type=float, default=[-40.0, 27.0, 125.0])
    p.add_argument("--data", nargs="+", type=int, choices=[0, 1], default=[0, 1])
    p.add_argument("--frequency-hz", type=float, default=1.0e6)
    p.add_argument("--timeout-s", type=float, default=30.0)
    p.add_argument("--pex", action="store_true", help="Use the canonical Magic RC-extracted write-driver netlist.")
    p.add_argument("--schematic", type=Path, default=root / "cells" / "write_driver" / "write_driver.sch")
    p.add_argument("--output", type=Path, default=root / "sims" / "write_driver_capacitance_pvt.csv")
    return p.parse_args()


def extract_write_driver(schematic: Path) -> str:
    schematic = schematic.resolve()
    with tempfile.TemporaryDirectory(prefix="write-driver-xschem-") as td:
        result = subprocess.run(
            ["xschem", "-x", "-q", "-n", "-o", td, str(schematic)],
            cwd=Path(__file__).resolve().parent.parent,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        netlist = Path(td) / f"{schematic.stem}.spice"
        if result.returncode != 0 or not netlist.exists():
            raise RuntimeError(f"Xschem netlist failed:\n{result.stdout}\n{result.stderr}")
        lines = netlist.read_text(encoding="utf-8").splitlines()

    header = next((line for line in lines if line.startswith("**.subckt ")), "")
    expected_pins = {"DATA", "DATA_B", "WE", "BL", "BLB", "VDD", "VSS"}
    if set(header.split()[2:]) != expected_pins:
        raise RuntimeError(f"unexpected write-driver pin set: {header}")
    body = [line for line in lines if line.startswith(("X", "+"))]
    expected_devices = {
        "XMPWEB", "XMNWEB", "XMPENBL", "XMPDBL", "XMNDBL", "XMNENBL",
        "XMPENBLB", "XMPDBLB", "XMNDBLB", "XMNENBLB",
    }
    devices = {line.split()[0] for line in body if line.startswith("X")}
    if devices != expected_devices:
        raise RuntimeError(f"unexpected write-driver devices: {sorted(devices)}")
    return ".subckt write_driver_core DATA DATA_B WE BL BLB VDD VSS\n" + "\n".join(body) + "\n.ends write_driver_core\n"


def extract_write_driver_pex(root: Path) -> str:
    netlist = root / "layout" / "write_driver" / "pex" / "write_driver_pex.spice"
    text = netlist.read_text(encoding="utf-8")
    match = re.search(r"^\.subckt\s+(\S+)\s+(.+)$", text, re.MULTILINE)
    if not match:
        raise RuntimeError(f"missing write-driver PEX subcircuit: {netlist}")
    name = match.group(1)
    pins = tuple(match.group(2).split())
    expected = ("DATA", "DATA_B", "WE", "BL", "BLB", "VDD", "VSS")
    if pins != expected:
        raise RuntimeError(f"unexpected write-driver PEX pins: {pins}")
    wrapper = (
        ".subckt write_driver_core DATA DATA_B WE BL BLB VDD VSS\n"
        f"XPEX DATA DATA_B WE BL BLB VDD VSS {name}\n"
        ".ends write_driver_core\n"
    )
    return text + "\n" + wrapper


def make_deck(*, subckt: str, corner: str, vdd: float, temp_c: float, data: int, probe: str, frequency_hz: float) -> str:
    data_v = vdd * data
    data_b_v = vdd * (1 - data)
    if probe == "BL":
        bl_src = f"DC {vdd:g} AC 1"
        blb_src = f"{vdd:g}"
        current_source = "VBL"
    elif probe == "BLB":
        bl_src = f"{vdd:g}"
        blb_src = f"DC {vdd:g} AC 1"
        current_source = "VBLB"
    else:
        raise ValueError(probe)
    return f"""* Off-state write-driver BL capacitance.
.lib "{MODEL_LIB}" {corner}
.temp {temp_c:g}
{subckt}
VDD vdd 0 {vdd:g}
VDATA data 0 {data_v:g}
VDATAB data_b 0 {data_b_v:g}
VWE we 0 0
VBL bl 0 {bl_src}
VBLB blb 0 {blb_src}
XWR data data_b we bl blb vdd 0 write_driver_core
.ac lin 1 {frequency_hz:.12g} {frequency_hz:.12g}
.print ac imag(i({current_source}))
.end
"""


def run_deck(text: str, timeout_s: float) -> float:
    with tempfile.TemporaryDirectory(prefix="write-driver-cap-") as td:
        deck = Path(td) / "cap.spice"
        deck.write_text(text, encoding="utf-8")
        result = subprocess.run(
            ["ngspice", "-n", "-b", str(deck)], cwd=td, text=True,
            capture_output=True, check=False, timeout=timeout_s,
        )
    output = result.stdout + "\n" + result.stderr
    if result.returncode != 0:
        raise RuntimeError(output[-1000:])
    match = AC_ROW_RE.search(output)
    if not match:
        raise RuntimeError(f"could not parse AC current:\n{output[-1000:]}")
    frequency = float(match.group("frequency"))
    imag_current = float(match.group("imag"))
    return abs(imag_current) / (2.0 * math.pi * frequency) * 1e15


def main() -> int:
    args = parse_args()
    if args.frequency_hz <= 0 or any(not 0 < v <= 1.8 for v in args.vdd_values):
        raise SystemExit("invalid frequency/VDD; characterization is limited to VDD <= 1.8 V")
    root = Path(__file__).resolve().parent.parent
    subckt = extract_write_driver_pex(root) if args.pex else extract_write_driver(args.schematic)
    rows: list[dict[str, object]] = []
    for corner, vdd, temp_c, data, probe in itertools.product(
        args.corners, args.vdd_values, args.temps_c, args.data, ("BL", "BLB")
    ):
        row: dict[str, object] = {
            "corner": corner, "vdd_v": vdd, "temp_c": temp_c, "data": data,
            "probe": probe, "we": 0, "frequency_hz": args.frequency_hz,
            "ceff_ff": "", "status": "ERROR", "error": "",
        }
        try:
            row["ceff_ff"] = f"{run_deck(make_deck(subckt=subckt, corner=corner, vdd=vdd, temp_c=temp_c, data=data, probe=probe, frequency_hz=args.frequency_hz), args.timeout_s):.9f}"
            row["status"] = "PASS"
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            row["error"] = str(exc).replace("\n", " | ")[:1000]
        rows.append(row)
        if len(rows) % 20 == 0:
            print(f"completed cases: {len(rows)}/120", flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    failures = [r for r in rows if r["status"] != "PASS"]
    values = [(float(r["ceff_ff"]), r) for r in rows if r["status"] == "PASS"]
    if values:
        lo = min(values, key=lambda x: x[0]); hi = max(values, key=lambda x: x[0])
        print(f"write-driver off-state Ceff: min={lo[0]:.6f} fF max={hi[0]:.6f} fF")
        r = hi[1]
        print(f"max at {r['corner']}/{r['vdd_v']}V/{r['temp_c']}C DATA={r['data']} {r['probe']}")
    print(f"PASS={len(rows)-len(failures)}/{len(rows)} CSV={args.output}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
