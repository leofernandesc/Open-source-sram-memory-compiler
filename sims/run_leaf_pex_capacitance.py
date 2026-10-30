#!/usr/bin/env python3
"""Measure post-layout BL capacitance of the bitcell and precharge leaves."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from run_cbl_device_capacitance import MODEL_LIB, run_deck
from pex_access_nodes import bitcell_storage_nodes


def pex_text(root: Path, leaf: str, override: Path | None = None) -> tuple[str, str, Path]:
    path = (
        override.resolve()
        if override is not None
        else root / "layout" / leaf / "pex" / f"{leaf}_pex.spice"
    )
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^\.subckt\s+(\S+)\s+(.+)$", text, re.MULTILINE)
    if not match:
        raise RuntimeError(f"missing subcircuit in {path}")
    return text, match.group(1), path


def bitcell_deck(
    *, text: str, name: str, corner: str, vdd: float, temp_c: float,
    state: int, probe: str, frequency_hz: float,
) -> str:
    if probe == "BL":
        bl, blb, current = f"DC {vdd:g} AC 1", f"{vdd:g}", "VBL"
    else:
        bl, blb, current = f"{vdd:g}", f"DC {vdd:g} AC 1", "VBLB"
    q = vdd if state else 0.0
    qb = 0.0 if state else vdd
    q_node, qb_node = bitcell_storage_nodes(text)
    return f"""* Full PEX bitcell input capacitance with WL deselected.
.lib "{MODEL_LIB}" {corner}
.temp {temp_c:g}
{text}
VDD vdd 0 {vdd:g}
VWL wl 0 0
VBL bl 0 {bl}
VBLB blb 0 {blb}
XCELL vdd bl blb 0 wl {name}
.nodeset v(xcell.{q_node})={q:.12g} v(xcell.{qb_node})={qb:.12g}
.ac lin 1 {frequency_hz:.12g} {frequency_hz:.12g}
.print ac imag(i({current}))
.end
"""


def precharge_deck(
    *, text: str, name: str, corner: str, vdd: float, temp_c: float,
    probe: str, frequency_hz: float,
) -> str:
    if probe == "BL":
        bl, blb, current = f"DC {vdd:g} AC 1", f"{vdd:g}", "VBL"
    else:
        bl, blb, current = f"{vdd:g}", f"DC {vdd:g} AC 1", "VBLB"
    return f"""* Full PEX precharge input capacitance with PRECH deasserted.
.lib "{MODEL_LIB}" {corner}
.temp {temp_c:g}
{text}
VDD vdd 0 {vdd:g}
VPRE prech 0 {vdd:g}
VBL bl 0 {bl}
VBLB blb 0 {blb}
XPRE vdd bl blb prech 0 {name}
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
    p.add_argument("--frequency-hz", type=float, default=1.0e6)
    p.add_argument("--timeout-s", type=float, default=45.0)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--blocks", nargs="+", choices=("bitcell", "precharge"), default=("bitcell", "precharge"))
    p.add_argument("--precharge-pex-netlist", type=Path, default=None)
    p.add_argument("--output", type=Path, default=root / "sims" / "leaf_pex_capacitance_pvt.csv")
    args = p.parse_args()
    if args.workers < 1 or args.frequency_hz <= 0 or any(not 0 < v <= 1.8 for v in args.vdd_values):
        p.error("invalid workers/frequency/VDD")

    cell_text, cell_name, cell_path = pex_text(root, "bitcell_6t")
    pre_text, pre_name, pre_path = pex_text(
        root, "precharge", args.precharge_pex_netlist
    )
    cases: list[tuple[str, str, str, str, str]] = []
    for corner, vdd, temp_c in itertools.product(args.corners, args.vdd_values, args.temps_c):
        if "bitcell" in args.blocks:
            for state, probe in itertools.product((0, 1), ("BL", "BLB")):
                deck = bitcell_deck(
                    text=cell_text, name=cell_name, corner=corner, vdd=vdd,
                    temp_c=temp_c, state=state, probe=probe, frequency_hz=args.frequency_hz,
                )
                cases.append(("bitcell", corner, str(vdd), str(temp_c), f"q{state}:{probe}", deck))
        if "precharge" in args.blocks:
            for probe in ("BL", "BLB"):
                deck = precharge_deck(
                    text=pre_text, name=pre_name, corner=corner, vdd=vdd,
                    temp_c=temp_c, probe=probe, frequency_hz=args.frequency_hz,
                )
                cases.append(("precharge", corner, str(vdd), str(temp_c), probe, deck))

    def execute(case: tuple[str, str, str, str, str, str]) -> dict[str, object]:
        block, corner, vdd, temp_c, scenario, deck = case
        row: dict[str, object] = {
            "block": block, "corner": corner, "vdd_v": vdd, "temp_c": temp_c,
            "scenario": scenario, "frequency_hz": args.frequency_hz,
            "ceff_ff": "", "status": "ERROR", "error": "",
            "precharge_pex_path": str(pre_path),
            "precharge_pex_sha256": hashlib.sha256(pre_path.read_bytes()).hexdigest(),
            "bitcell_pex_path": str(cell_path),
            "bitcell_pex_sha256": hashlib.sha256(cell_path.read_bytes()).hexdigest(),
        }
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
        for i, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if i % 20 == 0 or i == len(futures):
                print(f"completed {i}/{len(futures)}", flush=True)

    rows.sort(key=lambda r: (str(r["block"]), str(r["corner"]), float(r["vdd_v"]), float(r["temp_c"]), str(r["scenario"])))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)

    failures = [r for r in rows if r["status"] != "PASS"]
    for block in ("bitcell", "precharge"):
        values = [(float(r["ceff_ff"]), r) for r in rows if r["block"] == block and r["status"] == "PASS"]
        if values:
            lo = min(values, key=lambda item: item[0]); hi = max(values, key=lambda item: item[0])
            r = hi[1]
            print(f"{block}: min={lo[0]:.6f} fF max={hi[0]:.6f} fF at {r['corner']}/{r['vdd_v']}V/{r['temp_c']}C {r['scenario']}")
    print(f"PASS={len(rows)-len(failures)}/{len(rows)} CSV={args.output}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
