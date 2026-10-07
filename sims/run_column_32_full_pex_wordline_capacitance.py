#!/usr/bin/env python3
"""Measure extracted WLOFF capacitance of the physical 32-row full column."""

from __future__ import annotations

import argparse
import csv
import itertools
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from run_cbl_device_capacitance import MODEL_LIB, run_deck


def load_pex(root: Path) -> tuple[str, str]:
    path = root / "layout" / "column_32_full" / "pex" / "column_32_full_v2_pex.spice"
    text = path.read_text(encoding="utf-8")
    header = re.search(r"^\.subckt\s+(\S+)\s+(.+)$", text, re.MULTILINE)
    if not header:
        raise RuntimeError(f"missing subcircuit header: {path}")
    pins = tuple(header.group(2).split())
    expected = ("BL", "BLB", "VSS", "VDD", "WLOFF", "PRECH", "SCLK", "WE", "DATA_B", "DATA")
    if pins != expected:
        raise RuntimeError(f"unexpected full-column PEX pins: {pins}")
    return text, header.group(1)


def make_deck(
    text: str, name: str, corner: str, vdd: float, temp_c: float,
    state: int, frequency_hz: float,
) -> str:
    q = vdd if state else 0.0
    qb = 0.0 if state else vdd
    return f"""* Full-column extracted wordline capacitance.
.lib "{MODEL_LIB}" {corner}
.temp {temp_c:g}
{text}
VDD vdd 0 {vdd:g}
VBL bl 0 {q:.12g}
VBLB blb 0 {qb:.12g}
VWLOFF wloff 0 DC 0 AC 1
VPRECH prech 0 {vdd:g}
VSCLK sclk 0 0
VWE we 0 0
VDATA data 0 {q:.12g}
VDATAB data_b 0 {qb:.12g}
XCOL bl blb 0 vdd wloff prech sclk we data_b data {name}
.ac lin 1 {frequency_hz:.12g} {frequency_hz:.12g}
.print ac imag(i(VWLOFF))
.end
"""


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corners", nargs="+", default=["tt", "ff", "ss", "fs", "sf"])
    p.add_argument("--vdd-values", nargs="+", type=float, default=[1.62, 1.80])
    p.add_argument("--temps-c", nargs="+", type=float, default=[-40.0, 27.0, 125.0])
    p.add_argument("--states", nargs="+", type=int, choices=[0, 1], default=[0, 1])
    p.add_argument("--frequency-hz", type=float, default=1.0e6)
    p.add_argument("--timeout-s", type=float, default=60.0)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument(
        "--output",
        type=Path,
        default=root / "sims" / "column_32_full_pex_wordline_capacitance_pvt.csv",
    )
    args = p.parse_args()
    text, name = load_pex(root)
    cases = list(itertools.product(args.corners, args.vdd_values, args.temps_c, args.states))

    def execute(case: tuple[str, float, float, int]) -> dict[str, object]:
        corner, vdd, temp_c, state = case
        row: dict[str, object] = {
            "corner": corner, "vdd_v": vdd, "temp_c": temp_c, "state": state,
            "frequency_hz": args.frequency_hz, "cwl_pex_ff": "", "status": "ERROR", "error": "",
        }
        try:
            ceff_ff, _ = run_deck(
                "ngspice",
                make_deck(text, name, corner, vdd, temp_c, state, args.frequency_hz),
                args.timeout_s,
            )
            row["cwl_pex_ff"] = f"{ceff_ff:.9f}"
            row["status"] = "PASS"
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            row["error"] = str(exc).replace("\n", " | ")[:1000]
        return row

    rows: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(execute, case) for case in cases]
        for future in as_completed(futures):
            rows.append(future.result())

    rows.sort(key=lambda r: (str(r["corner"]), float(r["vdd_v"]), float(r["temp_c"]), int(r["state"])))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    failures = [row for row in rows if row["status"] != "PASS"]
    values = [(float(row["cwl_pex_ff"]), row) for row in rows if row["status"] == "PASS"]
    if values:
        worst = max(values, key=lambda item: item[0])
        print(
            f"C_WL_PEX,max={worst[0]:.6f} fF at "
            f"{worst[1]['corner']}/{worst[1]['vdd_v']}V/{worst[1]['temp_c']}C/q{worst[1]['state']}"
        )
    print(f"PASS={len(rows)-len(failures)}/{len(rows)} CSV={args.output}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
