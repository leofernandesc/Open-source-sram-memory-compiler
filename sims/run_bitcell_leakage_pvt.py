#!/usr/bin/env python3
"""Measure pre-layout 6T hold leakage with WL low and precharged bitlines."""

from __future__ import annotations

import argparse
import csv
import itertools
import re
import subprocess
import tempfile
from pathlib import Path


MODEL_LIB = "/opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice"
MEASURE_RE = re.compile(
    r"^\s*(?P<name>idd_avg|ibl_avg|iblb_avg|q_end|qb_end)\s*=\s*"
    r"(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)",
    re.MULTILINE,
)


def deck(corner: str, vdd: float, temp_c: float, state: int, wpu: float,
         wpd: float, wacc: float) -> str:
    return f"""* Pre-layout hold leakage; WL=0, BL/BLB precharged to VDD.
.title bitcell_hold_leakage_{corner}_{vdd:g}V_{temp_c:g}C_q{state}
.lib \"{MODEL_LIB}\" {corner}
.temp {temp_c:g}
VDD vdd 0 {vdd:g}
VBL bl 0 {vdd:g}
VBLB blb 0 {vdd:g}
VWL wl 0 0
XPU_L Q QB vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w={wpu:g} nf=1
XPU_R QB Q vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w={wpu:g} nf=1
XPD_L Q QB 0 0 sky130_fd_pr__nfet_01v8 l=0.15 w={wpd:g} nf=1
XPD_R QB Q 0 0 sky130_fd_pr__nfet_01v8 l=0.15 w={wpd:g} nf=1
XACC_L Q wl bl 0 sky130_fd_pr__nfet_01v8 l=0.15 w={wacc:g} nf=1
XACC_R QB wl blb 0 sky130_fd_pr__nfet_01v8 l=0.15 w={wacc:g} nf=1
.ic V(Q)={vdd * state:g} V(QB)={vdd * (1 - state):g}
.options ngbehavior=ps method=gear reltol=1e-5 vabstol=1e-9 iabstol=1e-12
.tran 100p 100n 0 100p uic
.meas tran idd_avg AVG I(VDD) FROM=80n TO=100n
.meas tran ibl_avg AVG I(VBL) FROM=80n TO=100n
.meas tran iblb_avg AVG I(VBLB) FROM=80n TO=100n
.meas tran q_end FIND V(Q) AT=100n
.meas tran qb_end FIND V(QB) AT=100n
.control
run
quit
.endc
.end
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corners", nargs="+", default=["tt", "ff", "ss", "fs", "sf"])
    parser.add_argument("--vdd-values", nargs="+", type=float, default=[1.62, 1.8, 1.95])
    parser.add_argument("--temps-c", nargs="+", type=float, default=[-40, 27, 125])
    parser.add_argument("--wpu", type=float, default=0.42)
    parser.add_argument("--wpd", type=float, default=1.26)
    parser.add_argument("--wacc", type=float, default=0.60)
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).with_name("bitcell_leakage_pvt_wpd1p26.csv"),
    )
    args = parser.parse_args()
    if any(c not in {"tt", "ff", "ss", "fs", "sf"} for c in args.corners):
        parser.error("unsupported corner")
    if any(not 0 < v <= 1.95 for v in args.vdd_values):
        parser.error("VDD must be >0 and <=1.95 V for SKY130 01v8 models")

    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="bitcell-leakage-") as temp_dir:
        work = Path(temp_dir)
        for corner, vdd, temp_c, state in itertools.product(
            args.corners, args.vdd_values, args.temps_c, (0, 1)
        ):
            stem = f"leak_{corner}_{vdd:g}V_{temp_c:g}C_q{state}"
            path = work / f"{stem}.spice"
            path.write_text(
                deck(corner, vdd, temp_c, state, args.wpu, args.wpd, args.wacc),
                encoding="utf-8",
            )
            result = subprocess.run(
                ["ngspice", "-n", "-b", str(path)], cwd=work,
                text=True, capture_output=True, check=False,
            )
            output = f"{result.stdout}\n{result.stderr}"
            values = {m.group("name"): float(m.group("value"))
                      for m in MEASURE_RE.finditer(output)}
            if result.returncode != 0 or len(values) != 5:
                raise RuntimeError(f"leakage simulation failed for {stem}:\n{output}")
            stable = (
                values["q_end"] >= vdd / 2 and values["qb_end"] <= 0.2
                if state == 1 else
                values["q_end"] <= 0.2 and values["qb_end"] >= vdd / 2
            )
            idd_a = -values["idd_avg"]
            total_a = -(values["idd_avg"] + values["ibl_avg"] + values["iblb_avg"])
            rows.append({
                "corner": corner, "vdd_v": vdd, "temp_c": temp_c,
                "stored_q": state, "wpu_um": args.wpu, "wpd_um": args.wpd,
                "wacc_um": args.wacc, "idd_a": f"{idd_a:.12g}",
                "ibl_a": f"{-values['ibl_avg']:.12g}",
                "iblb_a": f"{-values['iblb_avg']:.12g}",
                "total_supply_a": f"{total_a:.12g}",
                "cell_vdd_power_w": f"{vdd * idd_a:.12g}",
                "q_end_v": values["q_end"], "qb_end_v": values["qb_end"],
                "state_stable": stable,
            })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    worst = max(rows, key=lambda row: float(row["total_supply_a"]))
    print(f"Stable: {sum(row['state_stable'] for row in rows)}/{len(rows)}")
    print("Worst total standby source current: "
          f"{float(worst['total_supply_a']) * 1e9:.3f} nA at "
          f"{worst['corner']}, {worst['vdd_v']} V, {worst['temp_c']} C, "
          f"Q={worst['stored_q']}")
    print(f"CSV: {args.output}")
    return 0 if all(row["state_stable"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
