#!/usr/bin/env python3
"""Monte Carlo screening of the selected SRAM sense amplifier under SKY130 mismatch."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path


MODEL_LIB = "/opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice"
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
MEASURE_RE = re.compile(
    rf"^\s*(?P<name>(?:sa_eval|sab_eval|t_res)_\d+)\s*=\s*(?P<value>{NUMBER})",
    re.MULTILINE,
)


@dataclass(frozen=True)
class Case:
    sample: int
    delta_mv: float
    polarity: int


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corners",
        nargs="+",
        default=["tt_mm", "ff_mm", "ss_mm", "fs_mm", "sf_mm"],
        choices=["tt_mm", "ff_mm", "ss_mm", "fs_mm", "sf_mm"],
    )
    parser.add_argument("--vdd", type=float, default=1.62)
    parser.add_argument("--temp-c", type=float, default=125.0)
    parser.add_argument("--delta-mv", nargs="+", type=float, default=[25, 50, 75, 100])
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout-s", type=float, default=90.0)
    parser.add_argument("--seed-base", type=int, default=5001)
    parser.add_argument("--sclk-at-ns", type=float, default=2.0)
    parser.add_argument("--eval-at-ns", type=float, default=3.5)
    parser.add_argument(
        "--schematic", type=Path, default=root / "cells" / "sense_amp.sch"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "sims" / "sense_amp_mismatch_pvt.csv",
    )
    return parser.parse_args()


def sense_subckt(schematic: Path) -> str:
    schematic = schematic.resolve()
    with tempfile.TemporaryDirectory(prefix="sense-mm-xschem-") as temp_dir:
        result = subprocess.run(
            ["xschem", "-x", "-q", "-n", "-o", temp_dir, str(schematic)],
            cwd=schematic.parent.parent,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        netlist = Path(temp_dir) / f"{schematic.stem}.spice"
        if result.returncode != 0 or not netlist.exists():
            raise RuntimeError(f"Xschem netlist failed:\n{result.stdout}\n{result.stderr}")
        lines = netlist.read_text(encoding="utf-8").splitlines()
    body = [line for line in lines if line.startswith(("X", "+"))]
    devices = {line.split()[0] for line in body if line.startswith("X")}
    expected = {"XMP1", "XMP2", "XMN1", "XMN2", "XMSAMPBL", "XMSAMPBLB", "XMTAIL"}
    if devices != expected:
        raise RuntimeError(f"unexpected sense-amplifier devices: {devices}")
    return ".subckt sense_amp_core BL BLB SA_OUT SA_OUTB SCLK VDD VSS\n" + "\n".join(body) + "\n.ends sense_amp_core\n"


def make_deck(
    cases: list[Case], *, subckt: str, corner: str, vdd: float, temp_c: float,
    seed: int, sclk_at_ns: float, eval_at_ns: float
) -> str:
    lines = [
        "* SKY130 sense-amplifier local-mismatch screening.",
        f".options seed={seed} seedinfo",
        f'.lib "{MODEL_LIB}" {corner}',
        f".temp {temp_c:g}",
        subckt,
        f"VDD vdd 0 {vdd:g}",
        f"VSCLK sclk 0 PULSE(0 {vdd:g} {sclk_at_ns:g}n 50p 50p 2n 10n)",
    ]
    for index, case in enumerate(cases):
        delta_v = case.delta_mv * 1e-3
        if case.polarity > 0:
            bl, blb = vdd, vdd - delta_v
            diff = f"v(sa_{index})-v(sab_{index})"
        else:
            bl, blb = vdd - delta_v, vdd
            diff = f"v(sab_{index})-v(sa_{index})"
        lines.extend([
            f"VBL_{index} bl_{index} 0 {bl:.12g}",
            f"VBLB_{index} blb_{index} 0 {blb:.12g}",
            f"XSA_{index} bl_{index} blb_{index} sa_{index} sab_{index} sclk vdd 0 sense_amp_core",
            f".ic v(sa_{index})={vdd/2:.12g} v(sab_{index})={vdd/2:.12g}",
            f".meas tran sa_eval_{index} find v(sa_{index}) at={eval_at_ns:g}n",
            f".meas tran sab_eval_{index} find v(sab_{index}) at={eval_at_ns:g}n",
            f".meas tran t_res_{index} when par('{diff}')={0.8*vdd:.12g} rise=1",
        ])
    stop_ns = max(eval_at_ns + 0.5, sclk_at_ns + 2.0)
    lines.extend([
        ".options ngbehavior=ps method=gear reltol=1e-4 vabstol=1e-7 iabstol=1e-10",
        f".tran 5p {stop_ns:g}n 0 5p uic",
        ".control",
        "run",
        "quit",
        ".endc",
        ".end",
    ])
    return "\n".join(lines) + "\n"


def run_batch(
    batch_id: int, cases: list[Case], *, args: argparse.Namespace, subckt: str,
    corner: str, delta_mv: float
) -> list[dict[str, object]]:
    seed = args.seed_base + batch_id * 1009
    deck_text = make_deck(
        cases, subckt=subckt, corner=corner, vdd=args.vdd, temp_c=args.temp_c,
        seed=seed, sclk_at_ns=args.sclk_at_ns, eval_at_ns=args.eval_at_ns,
    )
    with tempfile.TemporaryDirectory(prefix="sense-mm-") as temp_dir:
        deck = Path(temp_dir) / "sense_mm.spice"
        deck.write_text(deck_text, encoding="utf-8")
        try:
            result = subprocess.run(
                ["ngspice", "-n", "-b", str(deck)], cwd=temp_dir,
                text=True, capture_output=True, check=False, timeout=args.timeout_s,
            )
            returncode = result.returncode
            output = result.stdout + "\n" + result.stderr
        except subprocess.TimeoutExpired as exc:
            returncode = 124
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            output = stdout + "\n" + stderr
    measures = {m.group("name"): float(m.group("value")) for m in MEASURE_RE.finditer(output)}
    sclk_50_s = args.sclk_at_ns * 1e-9 + 25e-12
    rows: list[dict[str, object]] = []
    for index, case in enumerate(cases):
        sa = measures.get(f"sa_eval_{index}")
        sab = measures.get(f"sab_eval_{index}")
        tres = measures.get(f"t_res_{index}")
        if case.polarity > 0:
            decision_ok = sa is not None and sab is not None and sa >= 0.9*args.vdd and sab <= 0.1*args.vdd
        else:
            decision_ok = sa is not None and sab is not None and sab >= 0.9*args.vdd and sa <= 0.1*args.vdd
        passed = returncode == 0 and decision_ok and tres is not None
        rows.append({
            "schematic_sha256": args.schematic_sha256,
            "corner": corner,
            "vdd_v": args.vdd,
            "temp_c": args.temp_c,
            "delta_mv": delta_mv,
            "sample": case.sample,
            "polarity": "BL>BLB" if case.polarity > 0 else "BLB>BL",
            "seed_batch": seed,
            "sa_eval_v": "" if sa is None else sa,
            "sab_eval_v": "" if sab is None else sab,
            "t_res_from_sclk50_ns": "" if tres is None else (tres-sclk_50_s)*1e9,
            "status": "PASS" if passed else "FAIL",
            "returncode": returncode,
            "error": "" if returncode == 0 else output[-500:].replace("\n", " | "),
        })
    return rows


def main() -> int:
    args = parse_args()
    if not 0 < args.vdd <= 1.8 or args.samples < 1 or args.batch_size < 1 or args.workers < 1:
        raise SystemExit("invalid VDD/samples/batch-size/workers")
    if any(delta <= 0 or delta >= args.vdd * 1000 for delta in args.delta_mv):
        raise SystemExit("delta values must be positive and below VDD")
    args.schematic_sha256 = hashlib.sha256(args.schematic.read_bytes()).hexdigest()
    subckt = sense_subckt(args.schematic)
    jobs = []
    batch_id = 0
    for corner in args.corners:
        for delta_mv in args.delta_mv:
            all_cases = [Case(sample, delta_mv, polarity) for sample in range(1, args.samples+1) for polarity in (1, -1)]
            for start in range(0, len(all_cases), args.batch_size * 2):
                jobs.append((batch_id, all_cases[start:start + args.batch_size * 2], corner, delta_mv))
                batch_id += 1
    rows: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(run_batch, i, cases, args=args, subckt=subckt, corner=corner, delta_mv=delta) for i, cases, corner, delta in jobs]
        for done, future in enumerate(as_completed(futures), start=1):
            rows.extend(future.result())
            print(f"completed batches: {done}/{len(futures)}", flush=True)
    rows.sort(key=lambda r: (str(r["corner"]), float(r["delta_mv"]), int(r["sample"]), str(r["polarity"])))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    failures = [r for r in rows if r["status"] != "PASS"]
    print(f"sense mismatch total: {len(rows)-len(failures)}/{len(rows)} PASS")
    for corner in args.corners:
        for delta in args.delta_mv:
            subset = [r for r in rows if r["corner"] == corner and float(r["delta_mv"]) == delta]
            passed = sum(r["status"] == "PASS" for r in subset)
            delays = [float(r["t_res_from_sclk50_ns"]) for r in subset if r["t_res_from_sclk50_ns"] != ""]
            worst = max(delays) if delays else float("nan")
            print(f"{corner} delta={delta:g}mV: {passed}/{len(subset)} PASS worst_t={worst:.4f}ns")
    print(f"CSV: {args.output}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
