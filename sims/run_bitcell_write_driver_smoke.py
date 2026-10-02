#!/usr/bin/env python3
"""Exploratory write switching with the transistor-level tri-state write driver."""

from __future__ import annotations

import argparse
import csv
import itertools
import re
import subprocess
import tempfile
from pathlib import Path


MEASURE_RE = re.compile(
    r"^\s*(?P<name>"
    r"q_before|qb_before|bl_prewrite|blb_prewrite|q_after|qb_after|q_cross|q_full|qb_full"
    r")\s*=\s*(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)",
    re.MULTILINE,
)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corners",
        nargs="+",
        default=["tt", "ss", "ff"],
        choices=["tt", "ff", "ss", "fs", "sf"],
    )
    parser.add_argument("--wpd-values", nargs="+", type=float, default=[0.84, 1.26])
    parser.add_argument("--wpu", type=float, default=0.42)
    parser.add_argument("--wacc", type=float, default=0.60)
    parser.add_argument("--wdriver", type=float, default=0.84)
    parser.add_argument("--vdd-values", nargs="+", type=float, default=[1.80])
    parser.add_argument("--temps-c", nargs="+", type=float, default=[27.0])
    parser.add_argument("--cbl-ff", type=float, default=50.0)
    parser.add_argument("--write-window-ns", type=float, default=10.0)
    parser.add_argument("--edge-ps", type=float, default=200.0)
    parser.add_argument("--tran-step-ps", type=float, default=50.0)
    parser.add_argument("--timeout-s", type=float, default=45.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "sims" / "bitcell_write_driver_exploratory.csv",
    )
    return parser.parse_args()


def make_driver_subckt(wdriver: float) -> str:
    return f"""
.subckt write_driver DATA DATA_B WE BL BLB VDD VSS
XMPWEB WE_B WE VDD VDD sky130_fd_pr__pfet_01v8 l=0.15 w={wdriver:g} nf=1
XMNWEB WE_B WE VSS VSS sky130_fd_pr__nfet_01v8 l=0.15 w={wdriver:g} nf=1
XMPENBL PBL_INT WE_B VDD VDD sky130_fd_pr__pfet_01v8 l=0.15 w={wdriver:g} nf=1
XMPDBL BL DATA_B PBL_INT VDD sky130_fd_pr__pfet_01v8 l=0.15 w={wdriver:g} nf=1
XMNDBL BL DATA_B NBL_INT VSS sky130_fd_pr__nfet_01v8 l=0.15 w={wdriver:g} nf=1
XMNENBL NBL_INT WE VSS VSS sky130_fd_pr__nfet_01v8 l=0.15 w={wdriver:g} nf=1
XMPENBLB PBLB_INT WE_B VDD VDD sky130_fd_pr__pfet_01v8 l=0.15 w={wdriver:g} nf=1
XMPDBLB BLB DATA PBLB_INT VDD sky130_fd_pr__pfet_01v8 l=0.15 w={wdriver:g} nf=1
XMNDBLB BLB DATA NBLB_INT VSS sky130_fd_pr__nfet_01v8 l=0.15 w={wdriver:g} nf=1
XMNENBLB NBLB_INT WE VSS VSS sky130_fd_pr__nfet_01v8 l=0.15 w={wdriver:g} nf=1
.ends write_driver
"""


def make_deck(
    *,
    corner: str,
    old_q: int,
    wpu: float,
    wpd: float,
    wacc: float,
    wdriver: float,
    vdd: float,
    temp_c: float,
    cbl_ff: float,
    write_window_ns: float,
    edge_ps: float,
    tran_step_ps: float,
) -> str:
    new_q = 1 - old_q
    data = float(new_q) * vdd
    data_b = float(old_q) * vdd
    wl_on_ns = 20.0
    wl_off_ns = wl_on_ns + write_window_ns
    we_on_ns = wl_on_ns - 2.0
    we_off_ns = wl_off_ns + 1.0
    stop_ns = wl_off_ns + 6.0
    crossing = "RISE=1" if new_q == 1 else "FALL=1"
    q_full_crossing = "RISE=1" if new_q == 1 else "FALL=1"
    qb_full_crossing = "FALL=1" if new_q == 1 else "RISE=1"
    q_full_level = 0.9 * vdd if new_q == 1 else 0.1 * vdd
    qb_full_level = 0.1 * vdd if new_q == 1 else 0.9 * vdd
    driver = make_driver_subckt(wdriver)
    return f"""* Exploratory SKY130A 6T write with transistor-level write driver.
* CBL={cbl_ff:g} fF and WL window={write_window_ns:g} ns are screening assumptions.
.title bitcell_write_driver_{corner}_q{old_q}_wpd{wpd:g}
.lib "/opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice" {corner}
.temp {temp_c:g}
VDD vdd 0 {vdd:g}
VDATA data 0 {data:g}
VDATAB data_b 0 {data_b:g}
VWE we 0 PULSE(0 {vdd:g} {we_on_ns:g}n {edge_ps:g}p {edge_ps:g}p {we_off_ns - we_on_ns:g}n {stop_ns + 20:g}n)
VWL wl 0 PULSE(0 {vdd:g} {wl_on_ns:g}n {edge_ps:g}p {edge_ps:g}p {write_window_ns:g}n {stop_ns + 20:g}n)
{driver}
XWR data data_b we bl blb vdd 0 write_driver
XPU_L Q QB vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w={wpu:g} nf=1
XPU_R QB Q vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w={wpu:g} nf=1
XPD_L Q QB 0 0 sky130_fd_pr__nfet_01v8 l=0.15 w={wpd:g} nf=1
XPD_R QB Q 0 0 sky130_fd_pr__nfet_01v8 l=0.15 w={wpd:g} nf=1
XACC_L Q wl bl 0 sky130_fd_pr__nfet_01v8 l=0.15 w={wacc:g} nf=1
XACC_R QB wl blb 0 sky130_fd_pr__nfet_01v8 l=0.15 w={wacc:g} nf=1
CBL bl 0 {cbl_ff:g}f
CBLB blb 0 {cbl_ff:g}f
.ic V(Q)={vdd * old_q:g} V(QB)={vdd * (1 - old_q):g} V(BL)={data:g} V(BLB)={data_b:g}
.options ngbehavior=ps method=gear reltol=1e-4 vabstol=1e-9 iabstol=1e-12
.tran {tran_step_ps:g}p {stop_ns:g}n 0 {tran_step_ps:g}p uic
.meas tran q_before FIND V(Q) AT={wl_on_ns - 0.1:g}n
.meas tran qb_before FIND V(QB) AT={wl_on_ns - 0.1:g}n
.meas tran bl_prewrite FIND V(BL) AT={wl_on_ns - 0.1:g}n
.meas tran blb_prewrite FIND V(BLB) AT={wl_on_ns - 0.1:g}n
.meas tran q_cross WHEN V(Q)={vdd / 2:g} {crossing}
.meas tran q_full WHEN V(Q)={q_full_level:g} {q_full_crossing}
.meas tran qb_full WHEN V(QB)={qb_full_level:g} {qb_full_crossing}
.meas tran q_after FIND V(Q) AT={wl_off_ns + 3:g}n
.meas tran qb_after FIND V(QB) AT={wl_off_ns + 3:g}n
.control
run
quit
.endc
.end
"""


def main() -> int:
    args = parse_args()
    if any(not 0 < voltage <= 1.8 for voltage in args.vdd_values):
        raise SystemExit(
            "This exploratory driver sweep is intentionally limited to VDD <= 1.8 V; "
            "the project has not qualified the 1.95 V point."
        )
    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="bitcell-write-driver-") as temp:
        work = Path(temp)
        for wpd, corner, vdd, temp_c, old_q in itertools.product(
            args.wpd_values, args.corners, args.vdd_values, args.temps_c, (0, 1)
        ):
            deck = work / (
                f"write_driver_{corner}_{vdd:g}V_{temp_c:g}C_q{old_q}_wpd{wpd:g}.spice"
            )
            deck.write_text(
                make_deck(
                    corner=corner,
                    old_q=old_q,
                    wpu=args.wpu,
                    wpd=wpd,
                    wacc=args.wacc,
                    wdriver=args.wdriver,
                    vdd=vdd,
                    temp_c=temp_c,
                    cbl_ff=args.cbl_ff,
                    write_window_ns=args.write_window_ns,
                    edge_ps=args.edge_ps,
                    tran_step_ps=args.tran_step_ps,
                )
            )
            timed_out = False
            try:
                result = subprocess.run(
                    ["ngspice", "-n", "-b", str(deck)],
                    cwd=work,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=args.timeout_s,
                )
                returncode = result.returncode
                output = result.stdout + "\n" + result.stderr
            except subprocess.TimeoutExpired as exc:
                timed_out = True
                returncode = 124
                stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
                stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
                output = stdout + "\n" + stderr
            values = {
                match.group("name"): float(match.group("value"))
                for match in MEASURE_RE.finditer(output)
            }
            threshold = vdd / 2
            initialized = False
            switched = False
            if returncode == 0 and all(
                key in values
                for key in (
                    "q_before",
                    "qb_before",
                    "bl_prewrite",
                    "blb_prewrite",
                    "q_after",
                    "qb_after",
                )
            ):
                initialized = (
                    values["q_before"] <= 0.2 and values["qb_before"] >= threshold
                    if old_q == 0
                    else values["q_before"] >= threshold and values["qb_before"] <= 0.2
                )
                switched = (
                    values["q_after"] >= threshold and values["qb_after"] <= 0.2
                    if old_q == 0
                    else values["q_after"] <= 0.2 and values["qb_after"] >= threshold
                )
            cross_s = values.get("q_cross")
            q_full_s = values.get("q_full")
            qb_full_s = values.get("qb_full")
            full_flip_s = (
                max(q_full_s, qb_full_s)
                if q_full_s is not None and qb_full_s is not None
                else None
            )
            row: dict[str, object] = {
                "corner": corner,
                "vdd_v": vdd,
                "temp_c": temp_c,
                "stored_q_before": old_q,
                "stored_q_after": 1 - old_q,
                "wpu_um": args.wpu,
                "wpd_um": wpd,
                "wacc_um": args.wacc,
                "wdriver_um": args.wdriver,
                "cbl_ff": args.cbl_ff,
                "write_window_ns": args.write_window_ns,
                "edge_ps": args.edge_ps,
                "tran_step_ps": args.tran_step_ps,
                "returncode": returncode,
                "initialized": initialized,
                "switched": switched,
                "q_before_v": values.get("q_before", ""),
                "qb_before_v": values.get("qb_before", ""),
                "bl_prewrite_v": values.get("bl_prewrite", ""),
                "blb_prewrite_v": values.get("blb_prewrite", ""),
                "q_cross_s": cross_s if cross_s is not None else "",
                "write_delay_ns": (
                    (cross_s - 20e-9) * 1e9 if cross_s is not None else ""
                ),
                "q_full_s": q_full_s if q_full_s is not None else "",
                "qb_full_s": qb_full_s if qb_full_s is not None else "",
                "full_flip_delay_ns": (
                    (full_flip_s - 20e-9) * 1e9 if full_flip_s is not None else ""
                ),
                "wl_min_30pct_ns": (
                    (full_flip_s - 20e-9) * 1e9 * 1.30 if full_flip_s is not None else ""
                ),
                "q_after_v": values.get("q_after", ""),
                "qb_after_v": values.get("qb_after", ""),
            }
            if timed_out:
                row["error"] = f"ngspice timeout after {args.timeout_s:g} s"
            elif returncode != 0:
                row["error"] = "ngspice failed"
            elif "q_cross" not in values:
                row["error"] = "Q threshold crossing not measured"
            rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    switched = sum(bool(row["switched"]) for row in rows)
    measured = [float(row["write_delay_ns"]) for row in rows if row["write_delay_ns"] != ""]
    full_flip = [
        float(row["full_flip_delay_ns"])
        for row in rows
        if row["full_flip_delay_ns"] != ""
    ]
    print(
        f"driver-integrated exploratory switching: {switched}/{len(rows)} switched "
        f"within {args.write_window_ns:g} ns; CSV: {args.output}"
    )
    if measured:
        print(
            f"Q threshold delay from WL rise: min={min(measured):.3f} ns, "
            f"max={max(measured):.3f} ns"
        )
    if full_flip:
        worst_full = max(full_flip)
        print(
            f"90/10% full-flip delay: min={min(full_flip):.3f} ns, "
            f"max={worst_full:.3f} ns; +30% WL lower bound={worst_full * 1.30:.3f} ns"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
