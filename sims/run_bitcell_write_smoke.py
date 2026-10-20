#!/usr/bin/env python3
"""Run full-swing write switching checks for SKY130A 6T sizing candidates."""

from __future__ import annotations

import argparse
import csv
import itertools
import re
import subprocess
import tempfile
from pathlib import Path


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
    parser.add_argument("--wpd-values", nargs="+", type=float, default=[0.84, 1.05, 1.26])
    parser.add_argument("--wpu", type=float, default=0.42)
    parser.add_argument("--wacc", type=float, default=0.60)
    parser.add_argument("--vdd-values", nargs="+", type=float, default=[1.8])
    parser.add_argument("--temps-c", nargs="+", type=float, default=[27.0])
    parser.add_argument(
        "--output", type=Path, default=root / "sims" / "bitcell_write_smoke_sweep.csv"
    )
    return parser.parse_args()


def make_deck(
    corner: str, old_q: int, wpu: float, wpd: float, wacc: float,
    vdd: float = 1.8, temp_c: float = 27.0,
) -> str:
    new_q = 1 - old_q
    bl, blb = (0.0, vdd) if new_q == 0 else (vdd, 0.0)
    return f"""* SKY130A 6T full-swing write switching check; not a write-margin measurement.
.title bitcell_write_{corner}_q{old_q}_wpd{wpd:g}
.lib "/opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice" {corner}
.temp {temp_c:g}
VDD vdd 0 {vdd:g}
VBL bl 0 {bl:g}
VBLB blb 0 {blb:g}
VWL wl 0 PULSE(0 {vdd:g} 20n 50p 50p 10n 40n)
XPU_L Q QB vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w={wpu:g} nf=1
XPU_R QB Q vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w={wpu:g} nf=1
XPD_L Q QB 0 0 sky130_fd_pr__nfet_01v8 l=0.15 w={wpd:g} nf=1
XPD_R QB Q 0 0 sky130_fd_pr__nfet_01v8 l=0.15 w={wpd:g} nf=1
XACC_L Q wl bl 0 sky130_fd_pr__nfet_01v8 l=0.15 w={wacc:g} nf=1
XACC_R QB wl blb 0 sky130_fd_pr__nfet_01v8 l=0.15 w={wacc:g} nf=1
.ic V(Q)={vdd * old_q:g} V(QB)={vdd * (1 - old_q):g}
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


def main() -> int:
    args = parse_args()
    if any(not 0 < voltage <= 1.95 for voltage in args.vdd_values):
        raise SystemExit("VDD must be >0 and <=1.95 V for the SKY130 01v8 models")
    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="bitcell-write-smoke-") as temp:
        work = Path(temp)
        for wpd in args.wpd_values:
            for corner, vdd, temp_c, old_q in itertools.product(
                args.corners, args.vdd_values, args.temps_c, (0, 1)
            ):
                    deck = work / f"write_{corner}_{vdd:g}V_{temp_c:g}C_q{old_q}_wpd{wpd:g}.spice"
                    deck.write_text(
                        make_deck(corner, old_q, args.wpu, wpd, args.wacc, vdd, temp_c)
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
                    row: dict[str, object] = {
                        "corner": corner,
                        "vdd_v": vdd,
                        "temp_c": temp_c,
                        "stored_q_before": old_q,
                        "stored_q_after": 1 - old_q,
                        "wpu_um": args.wpu,
                        "wpd_um": wpd,
                        "wacc_um": args.wacc,
                        "returncode": result.returncode,
                        "q_before_v": values.get("q_before", ""),
                        "qb_before_v": values.get("qb_before", ""),
                        "q_after_v": values.get("q_after", ""),
                        "qb_after_v": values.get("qb_after", ""),
                        "status": "FAIL",
                    }
                    if result.returncode == 0 and len(values) == 4:
                        initialized = (
                            values["q_before"] <= 0.2 and values["qb_before"] >= vdd / 2
                            if old_q == 0
                            else values["q_before"] >= vdd / 2 and values["qb_before"] <= 0.2
                        )
                        target = values["q_after"] >= vdd / 2 if old_q == 0 else values["q_after"] <= 0.2
                        complement = values["qb_after"] <= 0.2 if old_q == 0 else values["qb_after"] >= vdd / 2
                        row["status"] = (
                            "PASS" if initialized and target and complement else "WRITE_FAIL"
                        )
                    else:
                        row["error"] = "ngspice failed or measurements missing"
                    rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    passed = sum(row["status"] == "PASS" for row in rows)
    print(f"full-swing write switching: {passed}/{len(rows)} PASS; CSV: {args.output}")
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
