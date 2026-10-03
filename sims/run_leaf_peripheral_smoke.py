#!/usr/bin/env python3
"""Transient PVT smoke for the Xschem precharge and wordline-driver leaves."""

from __future__ import annotations

import argparse
import csv
import itertools
import re
import subprocess
import tempfile
from pathlib import Path

from run_sense_amp_characterization import MODEL_LIB, NUMBER


MEASURE_RE = re.compile(rf"^\s*([a-z][a-z0-9_]*)\s*=\s*({NUMBER})", re.MULTILINE)


def netlist_leaf(root: Path, name: str, pins: set[str], devices: set[str]) -> str:
    schematic = root / "cells" / f"{name}.sch"
    with tempfile.TemporaryDirectory(prefix=f"{name}-xschem-") as temp_dir:
        result = subprocess.run(
            ["xschem", "-x", "-q", "-n", "-o", temp_dir, str(schematic)],
            cwd=root, text=True, capture_output=True, check=False, timeout=30,
        )
        netlist = Path(temp_dir) / f"{name}.spice"
        if result.returncode or not netlist.exists():
            raise RuntimeError(f"Xschem netlist failed for {name}: {result.stdout} {result.stderr}")
        lines = netlist.read_text(encoding="utf-8").splitlines()
    header = next((line for line in lines if line.startswith("**.subckt ")), "")
    if set(header.split()[2:]) != pins:
        raise RuntimeError(f"Wrong pin contract for {name}: {header}")
    body = [line for line in lines if line.startswith(("X", "+"))]
    actual = {line.split()[0] for line in body if line.startswith("X")}
    if actual != devices or any(re.search(r"\bnet\d+\b", line) for line in body):
        raise RuntimeError(f"Open or unexpected devices in {name}: {actual}")
    return f".subckt {name} {' '.join(header.split()[2:])}\n" + "\n".join(body) + f"\n.ends {name}\n"


def precharge_deck(subckt: str, corner: str, vdd: float, temp_c: float, cap_ff: float) -> str:
    return f"""* Precharge/equalization with two unequal initial bitline voltages.
.lib "{MODEL_LIB}" {corner}
.temp {temp_c:g}
{subckt}
VDD vdd 0 {vdd:g}
VPRE prech 0 PULSE({vdd:g} 0 1n 50p 50p 4n 10n)
CBL bl 0 {cap_ff:g}f
CBLB blb 0 {cap_ff:g}f
XPRE vdd bl blb prech 0 precharge
.ic v(bl)={0.2*vdd:.12g} v(blb)={0.7*vdd:.12g}
.options ngbehavior=ps method=gear reltol=1e-4 vabstol=1e-9 iabstol=1e-12
.tran 10p 7n 0 10p uic
.meas tran bl_before find v(bl) at=0.9n
.meas tran blb_before find v(blb) at=0.9n
.meas tran bl_charged find v(bl) at=4.9n
.meas tran blb_charged find v(blb) at=4.9n
.meas tran bl_released find v(bl) at=6.5n
.meas tran blb_released find v(blb) at=6.5n
.end
"""


def wl_deck(subckt: str, corner: str, vdd: float, temp_c: float, cap_ff: float) -> str:
    return f"""* Two-stage WL driver with a capacitive wordline screening load.
.lib "{MODEL_LIB}" {corner}
.temp {temp_c:g}
{subckt}
VDD vdd 0 {vdd:g}
VIN wl_in 0 PULSE(0 {vdd:g} 1n 100p 100p 2n 10n)
CWL wl 0 {cap_ff:g}f
XWL vdd 0 wl_in wl wl_driver
.options ngbehavior=ps method=gear reltol=1e-4 vabstol=1e-9 iabstol=1e-12
.tran 10p 5n 0 10p
.meas tran wl_before find v(wl) at=0.9n
.meas tran wl_high find v(wl) at=2.9n
.meas tran wl_low find v(wl) at=4.0n
.meas tran t_in_50 when v(wl_in)={0.5*vdd:.12g} rise=1
.meas tran t_wl_50 when v(wl)={0.5*vdd:.12g} rise=1
.end
"""


def run_deck(text: str, timeout_s: float) -> tuple[int, dict[str, float], str]:
    with tempfile.TemporaryDirectory(prefix="leaf-peripheral-") as temp_dir:
        deck = Path(temp_dir) / "leaf.spice"
        deck.write_text(text, encoding="utf-8")
        try:
            result = subprocess.run(
                ["ngspice", "-n", "-b", str(deck)],
                cwd=temp_dir, text=True, capture_output=True,
                check=False, timeout=timeout_s,
            )
            output = result.stdout + "\n" + result.stderr
            returncode = result.returncode
        except subprocess.TimeoutExpired as exc:
            output = str(exc)
            returncode = 124
    measures = {m.group(1): float(m.group(2)) for m in MEASURE_RE.finditer(output)}
    return returncode, measures, output


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corners", nargs="+", default=["tt", "ff", "ss", "fs", "sf"])
    parser.add_argument("--vdd-values", nargs="+", type=float, default=[1.62, 1.80])
    parser.add_argument("--temps-c", nargs="+", type=float, default=[-40, 27, 125])
    parser.add_argument("--precharge-cap-ff", nargs="+", type=float, default=[16, 60])
    parser.add_argument("--wl-cap-ff", nargs="+", type=float, default=[10, 30, 50])
    parser.add_argument("--timeout-s", type=float, default=45)
    parser.add_argument("--output", type=Path, default=root / "sims" / "leaf_peripheral_smoke_pvt.csv")
    args = parser.parse_args()
    precharge = netlist_leaf(
        root, "precharge", {"VDD", "BL", "BLB", "PRECH", "VSS"},
        {"XMPBL", "XMPBLB", "XMEQ"},
    )
    wl = netlist_leaf(
        root, "wl_driver", {"VDD", "VSS", "WL_IN", "WL"},
        {"XMP1", "XMN1", "XMP2", "XMN2"},
    )
    rows: list[dict[str, object]] = []
    for corner, vdd, temp_c in itertools.product(args.corners, args.vdd_values, args.temps_c):
        for block, caps in (("precharge", args.precharge_cap_ff), ("wl_driver", args.wl_cap_ff)):
            for cap_ff in caps:
                deck = (
                    precharge_deck(precharge, corner, vdd, temp_c, cap_ff)
                    if block == "precharge" else
                    wl_deck(wl, corner, vdd, temp_c, cap_ff)
                )
                returncode, values, output = run_deck(deck, args.timeout_s)
                if block == "precharge":
                    required = (
                        "bl_before", "blb_before", "bl_charged", "blb_charged",
                        "bl_released", "blb_released",
                    )
                    pass_logic = all(key in values for key in required) and (
                        values["bl_charged"] >= 0.95 * vdd
                        and values["blb_charged"] >= 0.95 * vdd
                        and abs(values["bl_charged"] - values["blb_charged"]) <= 0.02 * vdd
                        and abs(values["bl_released"] - values["bl_charged"]) <= 0.02 * vdd
                        and abs(values["blb_released"] - values["blb_charged"]) <= 0.02 * vdd
                    )
                    delay_ns = ""
                else:
                    required = ("wl_before", "wl_high", "wl_low", "t_in_50", "t_wl_50")
                    pass_logic = all(key in values for key in required) and (
                        values["wl_before"] <= 0.1 * vdd
                        and values["wl_high"] >= 0.9 * vdd
                        and values["wl_low"] <= 0.1 * vdd
                    )
                    delay_ns = (values["t_wl_50"] - values["t_in_50"]) * 1e9 if all(
                        key in values for key in ("t_wl_50", "t_in_50")
                    ) else ""
                rows.append({
                    "block": block, "corner": corner, "vdd_v": vdd,
                    "temp_c": temp_c, "cap_ff": cap_ff,
                    "status": "PASS" if returncode == 0 and pass_logic else "FAIL",
                    "returncode": returncode, "delay_50_ns": delay_ns,
                    "bl_charged_v": values.get("bl_charged", ""),
                    "blb_charged_v": values.get("blb_charged", ""),
                    "bl_released_v": values.get("bl_released", ""),
                    "blb_released_v": values.get("blb_released", ""),
                    "wl_high_v": values.get("wl_high", ""),
                    "wl_low_v": values.get("wl_low", ""),
                    "error": "" if returncode == 0 else output[-500:].replace("\n", " | "),
                })
        print(f"completed {corner} VDD={vdd:g} T={temp_c:g} C", flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    failures = [row for row in rows if row["status"] != "PASS"]
    print(f"leaf peripheral smoke: {len(rows)-len(failures)}/{len(rows)} PASS; CSV: {args.output}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
