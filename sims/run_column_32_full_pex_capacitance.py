#!/usr/bin/env python3
"""Measure full post-layout BL/BLB capacitance of the 32-row physical column."""

from __future__ import annotations

import argparse
import csv
import itertools
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from run_cbl_device_capacitance import MODEL_LIB, run_deck
from pex_access_nodes import storage_output_node


ACCESS_RE = re.compile(
    r"^X\S+\s+(\S+)\s+(WLOFF(?:\.t\d+)?)\s+(\S+)\s+\S+\s+"
    r"sky130_fd_pr__nfet_01v8\b[^\n]*\bw=0\.6\b",
    re.MULTILINE,
)
COORD_RE = re.compile(r"^a_\d+_(-?\d+)(?:\.t\d+)?$")


def load_full_column_pex(
    root: Path, pex_netlist: Path | None = None
) -> tuple[str, str, list[tuple[str, str]]]:
    path = (
        pex_netlist.resolve()
        if pex_netlist is not None
        else root / "layout" / "column_32_full" / "pex" / "column_32_full_v2_pex.spice"
    )
    text = path.read_text(encoding="utf-8")
    header = re.search(r"^\.subckt\s+(\S+)\s+(.+?)(?=\n[^+])", text, re.MULTILINE | re.DOTALL)
    if not header:
        raise RuntimeError(f"missing subcircuit header: {path}")
    pins = tuple(re.sub(r"\n\+\s*", " ", header.group(2)).split())
    expected = ("BL", "BLB", "VSS", "VDD", "WLOFF", "PRECH", "SCLK", "WE", "DATA_B", "DATA")
    if pins != expected:
        raise RuntimeError(f"unexpected full-column PEX pins: {pins}")

    q_nodes: list[tuple[int, str]] = []
    qb_nodes: list[tuple[int, str]] = []
    for match in ACCESS_RE.finditer(text):
        first, _, third = match.groups()
        if re.fullmatch(r"BLB?(?:\.t\d+)?", first):
            bitline, storage = first, third
        elif re.fullmatch(r"BLB?(?:\.t\d+)?", third):
            bitline, storage = third, first
        else:
            continue
        coord = COORD_RE.match(storage)
        if not coord:
            raise RuntimeError(f"cannot infer row coordinate from storage node {storage}")
        item = (int(coord.group(1)), storage_output_node(storage))
        if bitline.startswith("BLB"):
            qb_nodes.append(item)
        else:
            q_nodes.append(item)

    q_nodes.sort()
    qb_nodes.sort()
    if len(q_nodes) != 32 or len(qb_nodes) != 32:
        raise RuntimeError(f"expected 32 access nodes per side, got BL={len(q_nodes)} BLB={len(qb_nodes)}")

    pairs: list[tuple[str, str]] = []
    for (qy, q), (qby, qb) in zip(q_nodes, qb_nodes):
        if abs(qy - qby) > 200:
            raise RuntimeError(f"row pairing mismatch: {q}@{qy} vs {qb}@{qby}")
        pairs.append((q, qb))
    return text, header.group(1), pairs


def make_deck(
    *, text: str, name: str, pairs: list[tuple[str, str]], corner: str,
    vdd: float, temp_c: float, state: int, probe: str, frequency_hz: float,
) -> str:
    if probe == "BL":
        bl_src, blb_src, current = f"DC {vdd:g} AC 1", f"{vdd:g}", "VBL"
    else:
        bl_src, blb_src, current = f"{vdd:g}", f"DC {vdd:g} AC 1", "VBLB"

    q_v = vdd if state else 0.0
    qb_v = 0.0 if state else vdd
    data_v = q_v
    data_b_v = qb_v
    nodesets = "\n".join(
        f".nodeset v(xcol.{q})={q_v:.12g} v(xcol.{qb})={qb_v:.12g}"
        for q, qb in pairs
    )
    return f"""* Full physical 32-row column PEX input capacitance.
.lib "{MODEL_LIB}" {corner}
.temp {temp_c:g}
{text}
VDD vdd 0 {vdd:g}
VWLOFF wloff 0 0
VPRECH prech 0 {vdd:g}
VSCLK sclk 0 0
VWE we 0 0
VDATA data 0 {data_v:.12g}
VDATAB data_b 0 {data_b_v:.12g}
VBL bl 0 {bl_src}
VBLB blb 0 {blb_src}
XCOL bl blb 0 vdd wloff prech sclk we data_b data {name}
{nodesets}
.ac lin 1 {frequency_hz:.12g} {frequency_hz:.12g}
.print ac imag(i({current}))
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
    p.add_argument("--pex-netlist", type=Path, default=None)
    p.add_argument("--output", type=Path, default=root / "sims" / "column_32_full_pex_capacitance_pvt.csv")
    args = p.parse_args()
    if args.workers < 1 or args.frequency_hz <= 0 or any(not 0 < v <= 1.8 for v in args.vdd_values):
        p.error("invalid workers/frequency/VDD")

    text, name, pairs = load_full_column_pex(root, args.pex_netlist)
    cases = list(itertools.product(args.corners, args.vdd_values, args.temps_c, args.states, ("BL", "BLB")))

    def execute(case: tuple[str, float, float, int, str]) -> dict[str, object]:
        corner, vdd, temp_c, state, probe = case
        row: dict[str, object] = {
            "corner": corner, "vdd_v": vdd, "temp_c": temp_c, "state": state,
            "probe": probe, "frequency_hz": args.frequency_hz, "ceff_ff": "",
            "status": "ERROR", "error": "",
        }
        deck = make_deck(
            text=text, name=name, pairs=pairs, corner=corner, vdd=vdd,
            temp_c=temp_c, state=state, probe=probe, frequency_hz=args.frequency_hz,
        )
        try:
            ceff_ff, _ = run_deck("ngspice", deck, args.timeout_s)
            row["ceff_ff"] = f"{ceff_ff:.9f}"
            row["status"] = "PASS"
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            row["error"] = str(exc).replace("\n", " | ")[:1000]
        return row

    rows: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(execute, case) for case in cases]
        for index, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if index % 20 == 0 or index == len(futures):
                print(f"completed {index}/{len(futures)}", flush=True)

    rows.sort(key=lambda r: (str(r["corner"]), float(r["vdd_v"]), float(r["temp_c"]), int(r["state"]), str(r["probe"])))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    failures = [row for row in rows if row["status"] != "PASS"]
    values = [(float(row["ceff_ff"]), row) for row in rows if row["status"] == "PASS"]
    if values:
        lo = min(values, key=lambda item: item[0])
        hi = max(values, key=lambda item: item[0])
        worst = hi[1]
        print(f"column_32_full: min={lo[0]:.6f} fF max={hi[0]:.6f} fF at {worst['corner']}/{worst['vdd_v']}V/{worst['temp_c']}C q={worst['state']} {worst['probe']}")
        print(f"column_32_full +15% ceiling={hi[0] * 1.15:.6f} fF")
    print(f"PASS={len(rows)-len(failures)}/{len(rows)} CSV={args.output}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
