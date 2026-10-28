#!/usr/bin/env python3
"""Measure dynamic word-line voltage margin for SKY130A 6T write operations."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import tempfile
from pathlib import Path


VDD = 1.8
MEASURE_RE = re.compile(
    r"^\s*(?P<name>q_before|qb_before|q_after|qb_after)\s*=\s*"
    r"(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)",
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
    parser.add_argument("--wpd-values", nargs="+", type=float, default=[0.84, 1.05])
    parser.add_argument("--wpu", type=float, default=0.42)
    parser.add_argument("--wacc", type=float, default=0.60)
    parser.add_argument("--iterations", type=int, default=7)
    parser.add_argument("--output", type=Path, default=root / "sims" / "bitcell_write_margin.csv")
    return parser.parse_args()


def make_deck(corner: str, old_q: int, wl_high: float, wpu: float, wpd: float, wacc: float) -> str:
    new_q = 1 - old_q
    bl, blb = (0.0, VDD) if new_q == 0 else (VDD, 0.0)
    return f"""* Dynamic word-line write-margin test; ideal full-swing bitline drivers.
.title bitcell_wlvm_{corner}_q{old_q}_wl{wl_high:g}
.lib "/opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice" {corner}
VDD vdd 0 {VDD:g}
VBL bl 0 {bl:g}
VBLB blb 0 {blb:g}
VWL wl 0 PULSE(0 {wl_high:g} 20n 50p 50p 10n 40n)
XPU_L Q QB vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w={wpu:g} nf=1
XPU_R QB Q vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w={wpu:g} nf=1
XPD_L Q QB 0 0 sky130_fd_pr__nfet_01v8 l=0.15 w={wpd:g} nf=1
XPD_R QB Q 0 0 sky130_fd_pr__nfet_01v8 l=0.15 w={wpd:g} nf=1
XACC_L Q wl bl 0 sky130_fd_pr__nfet_01v8 l=0.15 w={wacc:g} nf=1
XACC_R QB wl blb 0 sky130_fd_pr__nfet_01v8 l=0.15 w={wacc:g} nf=1
.ic V(Q)={VDD * old_q:g} V(QB)={VDD * (1 - old_q):g}
.options ngbehavior=ps method=gear reltol=1e-4 vabstol=1e-9 iabstol=1e-12
.tran 10p 40n 0 10p uic
.meas tran q_before FIND V(Q) AT=19.9n
.meas tran qb_before FIND V(QB) AT=19.9n
.meas tran q_after FIND V(Q) AT=35n
.meas tran qb_after FIND V(QB) AT=35n
.control
run
quit
.endc
.end
"""


def simulate(work: Path, corner: str, old_q: int, wl_high: float, args: argparse.Namespace) -> bool:
    deck = work / f"wlvm_{corner}_q{old_q}_{wl_high:.6f}.spice"
    deck.write_text(
        make_deck(corner, old_q, wl_high, args.wpu, args.current_wpd, args.wacc),
        encoding="utf-8",
    )
    result = subprocess.run(
        ["ngspice", "-n", "-b", str(deck)],
        cwd=work,
        text=True,
        capture_output=True,
        check=False,
    )
    output = result.stdout + "\n" + result.stderr
    values = {
        match.group("name"): float(match.group("value"))
        for match in MEASURE_RE.finditer(output)
    }
    if result.returncode != 0 or len(values) != 4:
        raise RuntimeError(f"ngspice failed for {corner}, Q={old_q}, WL={wl_high:g} V:\n{output}")
    initialized = (
        values["q_before"] <= 0.2 and values["qb_before"] >= 0.9
        if old_q == 0
        else values["q_before"] >= 0.9 and values["qb_before"] <= 0.2
    )
    written = (
        values["q_after"] >= 0.9 and values["qb_after"] <= 0.2
        if old_q == 0
        else values["q_after"] <= 0.2 and values["qb_after"] >= 0.9
    )
    return initialized and written


def main() -> int:
    args = parse_args()
    if args.iterations < 1:
        raise SystemExit("--iterations must be positive")
    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="bitcell-wlvm-") as temp:
        work = Path(temp)
        for wpd in args.wpd_values:
            args.current_wpd = wpd
            for corner in args.corners:
                for old_q in (0, 1):
                    lo, hi = 0.0, VDD
                    if simulate(work, corner, old_q, lo, args):
                        raise RuntimeError("write unexpectedly passed with WL=0")
                    if not simulate(work, corner, old_q, hi, args):
                        raise RuntimeError(f"full-height WL failed for {corner}, Q={old_q}, WPD={wpd:g}")
                    for _ in range(args.iterations):
                        mid = (lo + hi) / 2
                        if simulate(work, corner, old_q, mid, args):
                            hi = mid
                        else:
                            lo = mid
                    rows.append(
                        {
                            "corner": corner,
                            "stored_q_before": old_q,
                            "stored_q_after": 1 - old_q,
                            "wpu_um": args.wpu,
                            "wpd_um": wpd,
                            "wacc_um": args.wacc,
                            "write_pulse_ns": 10,
                            "wl_min_success_v": hi,
                            "wl_max_drop_v": VDD - hi,
                            "wl_drop_resolution_v": hi - lo,
                            "status": "PASS",
                        }
                    )
    fields = list(rows[0])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"WLVM measured for {len(rows)} corner/state/sizing combinations: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
