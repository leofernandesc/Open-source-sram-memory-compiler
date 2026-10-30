#!/usr/bin/env python3
"""Sweep dynamic input setup relative to SCLK for the selected sense amplifier."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
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
    setup_ps: float
    polarity: int


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corners", nargs="+", default=["tt", "ff", "ss", "fs", "sf"])
    p.add_argument("--vdd-values", nargs="+", type=float, default=[1.62, 1.80])
    p.add_argument("--temps-c", nargs="+", type=float, default=[-40.0, 27.0, 125.0])
    p.add_argument("--setup-ps", nargs="+", type=float, default=[-100, -50, 0, 25, 50, 100, 200])
    p.add_argument("--delta-mv", type=float, default=150.0)
    p.add_argument("--input-slew-ps", type=float, default=50.0)
    p.add_argument("--sclk-at-ns", type=float, default=2.0)
    p.add_argument("--sclk-rise-ps", type=float, default=50.0)
    p.add_argument("--eval-delay-ns", type=float, default=1.0)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--timeout-s", type=float, default=90.0)
    p.add_argument("--schematic", type=Path, default=root / "cells" / "sense_amp.sch")
    p.add_argument("--output", type=Path, default=root / "sims" / "sense_amp_sclk_setup_pvt.csv")
    return p.parse_args()


def sense_subckt(schematic: Path) -> str:
    schematic = schematic.resolve()
    with tempfile.TemporaryDirectory(prefix="sense-setup-xschem-") as td:
        result = subprocess.run(
            ["xschem", "-x", "-q", "-n", "-o", td, str(schematic)],
            cwd=schematic.parent.parent, text=True, capture_output=True,
            check=False, timeout=30,
        )
        netlist = Path(td) / f"{schematic.stem}.spice"
        if result.returncode != 0 or not netlist.exists():
            raise RuntimeError(f"Xschem netlist failed:\n{result.stdout}\n{result.stderr}")
        lines = netlist.read_text(encoding="utf-8").splitlines()
    body = [line for line in lines if line.startswith(("X", "+"))]
    devices = {line.split()[0] for line in body if line.startswith("X")}
    expected = {"XMP1", "XMP2", "XMN1", "XMN2", "XMSAMPBL", "XMSAMPBLB", "XMTAIL"}
    if devices != expected:
        raise RuntimeError(f"unexpected sense-amplifier devices: {devices}")
    return ".subckt sense_amp_core BL BLB SA_OUT SA_OUTB SCLK VDD VSS\n" + "\n".join(body) + "\n.ends sense_amp_core\n"


def make_pwl(vdd: float, final_v: float, start_ns: float, end_ns: float, stop_ns: float) -> str:
    return (
        f"PWL(0 {vdd:.12g} {max(0.0,start_ns):.12g}n {vdd:.12g} "
        f"{max(0.0,end_ns):.12g}n {final_v:.12g} {stop_ns:.12g}n {final_v:.12g})"
    )


def make_deck(cases: list[Case], *, subckt: str, corner: str, vdd: float, temp_c: float, args: argparse.Namespace) -> str:
    sclk50_ns = args.sclk_at_ns + args.sclk_rise_ps * 1e-3 / 2.0
    eval_ns = sclk50_ns + args.eval_delay_ns
    stop_ns = eval_ns + 0.5
    lines = [
        "* Dynamic BL setup sweep for sense amplifier.",
        f'.lib "{MODEL_LIB}" {corner}',
        f".temp {temp_c:g}", subckt, f"VDD vdd 0 {vdd:g}",
        f"VSCLK sclk 0 PULSE(0 {vdd:g} {args.sclk_at_ns:g}n {args.sclk_rise_ps:g}p {args.sclk_rise_ps:g}p 2n 10n)",
    ]
    for i, case in enumerate(cases):
        end_ns = sclk50_ns - case.setup_ps * 1e-3
        start_ns = end_ns - args.input_slew_ps * 1e-3
        low = vdd - args.delta_mv * 1e-3
        if case.polarity > 0:
            bl_src = f"{vdd:.12g}"
            blb_src = make_pwl(vdd, low, start_ns, end_ns, stop_ns)
            diff = f"v(sa_{i})-v(sab_{i})"
        else:
            bl_src = make_pwl(vdd, low, start_ns, end_ns, stop_ns)
            blb_src = f"{vdd:.12g}"
            diff = f"v(sab_{i})-v(sa_{i})"
        lines.extend([
            f"VBL_{i} bl_{i} 0 {bl_src}", f"VBLB_{i} blb_{i} 0 {blb_src}",
            f"XSA_{i} bl_{i} blb_{i} sa_{i} sab_{i} sclk vdd 0 sense_amp_core",
            f".ic v(sa_{i})={vdd/2:.12g} v(sab_{i})={vdd/2:.12g}",
            f".meas tran sa_eval_{i} find v(sa_{i}) at={eval_ns:.12g}n",
            f".meas tran sab_eval_{i} find v(sab_{i}) at={eval_ns:.12g}n",
            f".meas tran t_res_{i} when par('{diff}')={0.8*vdd:.12g} rise=1 td={args.sclk_at_ns:g}n",
        ])
    lines.extend([
        ".options ngbehavior=ps method=gear reltol=1e-4 vabstol=1e-7 iabstol=1e-10",
        f".tran 5p {stop_ns:.12g}n 0 5p uic", ".end",
    ])
    return "\n".join(lines) + "\n"


def run_batch(corner: str, vdd: float, temp_c: float, *, args: argparse.Namespace, subckt: str) -> list[dict[str, object]]:
    cases = [Case(setup, polarity) for setup, polarity in itertools.product(args.setup_ps, (1, -1))]
    deck_text = make_deck(cases, subckt=subckt, corner=corner, vdd=vdd, temp_c=temp_c, args=args)
    with tempfile.TemporaryDirectory(prefix="sense-setup-") as td:
        deck = Path(td) / "sense_setup.spice"; deck.write_text(deck_text, encoding="utf-8")
        try:
            result = subprocess.run(["ngspice", "-n", "-b", str(deck)], cwd=td, text=True, capture_output=True, check=False, timeout=args.timeout_s)
            rc = result.returncode; output = result.stdout + "\n" + result.stderr
        except subprocess.TimeoutExpired as exc:
            rc = 124
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            output = stdout + "\n" + stderr
    measures = {m.group("name"): float(m.group("value")) for m in MEASURE_RE.finditer(output)}
    sclk50_s = (args.sclk_at_ns + args.sclk_rise_ps*1e-3/2.0) * 1e-9
    rows = []
    for i, case in enumerate(cases):
        sa = measures.get(f"sa_eval_{i}"); sab = measures.get(f"sab_eval_{i}"); tres = measures.get(f"t_res_{i}")
        if case.polarity > 0:
            decision_ok = sa is not None and sab is not None and sa >= 0.9*vdd and sab <= 0.1*vdd
        else:
            decision_ok = sa is not None and sab is not None and sab >= 0.9*vdd and sa <= 0.1*vdd
        passed = rc == 0 and decision_ok and tres is not None
        rows.append({
            "schematic_sha256": args.schematic_sha256, "corner": corner, "vdd_v": vdd,
            "temp_c": temp_c, "delta_mv": args.delta_mv, "input_slew_ps": args.input_slew_ps,
            "setup_ps_to_sclk50": case.setup_ps, "polarity": "BL>BLB" if case.polarity > 0 else "BLB>BL",
            "sa_eval_v": "" if sa is None else sa, "sab_eval_v": "" if sab is None else sab,
            "t_res_from_sclk50_ns": "" if tres is None else (tres-sclk50_s)*1e9,
            "status": "PASS" if passed else "FAIL", "returncode": rc,
            "error": "" if rc == 0 else output[-500:].replace("\n", " | "),
        })
    return rows


def main() -> int:
    args = parse_args()
    if args.workers < 1 or args.input_slew_ps <= 0 or args.delta_mv <= 0:
        raise SystemExit("invalid workers/input slew/delta")
    args.schematic_sha256 = hashlib.sha256(args.schematic.read_bytes()).hexdigest()
    subckt = sense_subckt(args.schematic)
    batches = list(itertools.product(args.corners, args.vdd_values, args.temps_c))
    rows: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(run_batch, c, v, t, args=args, subckt=subckt) for c, v, t in batches]
        for done, fut in enumerate(as_completed(futures), 1):
            rows.extend(fut.result()); print(f"completed batches: {done}/{len(futures)}", flush=True)
    rows.sort(key=lambda r: (str(r["corner"]), float(r["vdd_v"]), float(r["temp_c"]), float(r["setup_ps_to_sclk50"]), str(r["polarity"])))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n"); w.writeheader(); w.writerows(rows)
    failures = [r for r in rows if r["status"] != "PASS"]
    print(f"sense SCLK setup: {len(rows)-len(failures)}/{len(rows)} PASS")
    for setup in args.setup_ps:
        subset=[r for r in rows if float(r["setup_ps_to_sclk50"])==setup]
        passed=sum(r["status"]=="PASS" for r in subset)
        delays=[float(r["t_res_from_sclk50_ns"]) for r in subset if r["t_res_from_sclk50_ns"]!=""]
        print(f"setup={setup:g}ps: {passed}/{len(subset)} PASS; worst_t={max(delays) if delays else float('nan'):.4f}ns")
    print(f"CSV: {args.output}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
