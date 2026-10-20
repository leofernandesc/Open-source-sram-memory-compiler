#!/usr/bin/env python3
"""Automate the SKY130A 6T read-disturb sweep using provisional project limits."""

from __future__ import annotations

import argparse
import csv
import itertools
import re
import subprocess
import tempfile
from pathlib import Path


BITLINE_DELTA_MIN_V = 0.100
STORED_LOW_MAX_V = 0.2


MEASURE_RE = re.compile(
    r"^\s*(?P<name>bl_pre|blb_pre|bl_read_min|blb_read_min|bl_21n|blb_21n|"
    r"q_read_min|qb_read_min|q_read_max|qb_read_max|q_post_read|qb_post_read|t_dv100)\s*=\s*"
    r"(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)",
    re.MULTILINE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--deck",
        type=Path,
        default=Path(__file__).with_name("tb_bitcell_6t_read.spice"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("bitcell_read_sweep.csv"),
    )
    parser.add_argument(
        "--cap-f",
        nargs="+",
        type=float,
        default=[5.0, 10.0, 20.0, 50.0, 60.0],
        help="Bitline capacitances in fF.",
    )
    parser.add_argument(
        "--corners",
        nargs="+",
        default=["tt", "ff", "ss", "fs", "sf"],
        choices=["tt", "ff", "ss", "fs", "sf"],
        help="SKY130A model corners.",
    )
    parser.add_argument("--wpu", type=float, default=0.42, help="Pull-up width in um.")
    parser.add_argument("--wpd", type=float, default=1.26, help="Pull-down width in um.")
    parser.add_argument("--wacc", type=float, default=0.60, help="Access width in um.")
    parser.add_argument("--vdd-values", nargs="+", type=float, default=[1.8])
    parser.add_argument("--temps-c", nargs="+", type=float, default=[27.0])
    parser.add_argument("--states", nargs="+", type=int, choices=[0, 1], default=[1, 0])
    parser.add_argument("--tran-step-ps", type=float, default=10.0)
    parser.add_argument("--timeout-s", type=float, default=45.0)
    return parser.parse_args()


def replace_once(text: str, pattern: str, replacement: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"expected one match for {pattern!r}, found {count}")
    return updated


def make_deck(
    template: str,
    corner: str,
    cap_f: float,
    state: int,
    raw_name: str,
    wpu: float,
    wpd: float,
    wacc: float,
    vdd: float = 1.8,
    temp_c: float = 27.0,
    tran_step_ps: float = 10.0,
) -> str:
    updated = replace_once(
        template,
        r"^CBL\s+bl\s+0\s+\S+\s*$",
        f"CBL  bl  0 {cap_f:g}f",
    )
    updated = replace_once(
        updated,
        r"^CBLB\s+blb\s+0\s+\S+\s*$",
        f"CBLB blb 0 {cap_f:g}f",
    )
    if state == 1:
        initial = f".ic V(Q)={vdd:g} V(QB)=0 V(bl)={vdd:g} V(blb)={vdd:g}"
    else:
        initial = f".ic V(Q)=0 V(QB)={vdd:g} V(bl)={vdd:g} V(blb)={vdd:g}"
    updated = replace_once(updated, r"^\.ic\s+.*$", initial)
    updated = replace_once(updated, r"^VDD vdd 0 \S+\s*$", f"VDD vdd 0 {vdd:g}")
    updated = replace_once(
        updated, r"^VPRE pre 0 PULSE\(\S+ 0 ", f"VPRE pre 0 PULSE({vdd:g} 0 "
    )
    updated = replace_once(
        updated, r"^VWL wl 0 PULSE\(0 \S+ ", f"VWL wl 0 PULSE(0 {vdd:g} "
    )
    for instance_group, width in (("XPU", wpu), ("XPD", wpd), ("XACC", wacc)):
        updated, count = re.subn(
            rf"^({instance_group}_[LR].*\bw=)\S+(\s+nf=1\s*)$",
            rf"\g<1>{width:g}\g<2>",
            updated,
            flags=re.MULTILINE,
        )
        if count != 2:
            raise RuntimeError(
                f"expected two {instance_group} devices, found {count}"
            )
    updated = replace_once(
        updated,
        r"^\.title\s+.*$",
        f".title bitcell_6t_read_{corner}_{cap_f:g}f_q{state}_{vdd:g}V_{temp_c:g}C",
    )
    updated = replace_once(
        updated,
        r'^\.lib\s+"[^" ]+sky130\.lib\.spice"\s+\w+\s*$',
        f'.lib "/opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice" {corner}',
    )
    updated = replace_once(
        updated,
        r"^write\s+\S+\s+all\s*$",
        f"write {raw_name} all",
    )
    updated = replace_once(
        updated,
        r"^(\.lib\s+\S+\s+\w+\s*)$",
        rf"\g<1>\n.temp {temp_c:g}",
    )
    updated = replace_once(
        updated,
        r"^\.tran\s+\S+\s+40n\s+0\s+\S+\s+uic\s*$",
        f".tran {tran_step_ps:g}p 40n 0 {tran_step_ps:g}p uic",
    )
    bitline_pair = "bl,blb" if state == 1 else "blb,bl"
    updated = replace_once(
        updated,
        r"^\.control$",
        f".meas tran t_dv100 WHEN par('v({bitline_pair.split(',')[0]})-v({bitline_pair.split(',')[1]})')=0.1 CROSS=1 TD=20n\n.control",
    )
    return updated


def parse_measurements(output: str) -> dict[str, float]:
    measurements = {
        match.group("name"): float(match.group("value"))
        for match in MEASURE_RE.finditer(output)
    }
    required = {
        "bl_pre", "blb_pre", "bl_read_min", "blb_read_min", "bl_21n", "blb_21n",
        "q_read_min", "qb_read_min", "q_read_max", "qb_read_max",
        "q_post_read", "qb_post_read",
    }
    missing = required - measurements.keys()
    if missing:
        raise RuntimeError(f"missing measurements: {', '.join(sorted(missing))}")
    return measurements


def main() -> int:
    args = parse_args()
    if any(not 0 < voltage <= 1.95 for voltage in args.vdd_values):
        raise SystemExit("VDD must be >0 and <=1.95 V for the SKY130 01v8 models")
    template = args.deck.read_text(encoding="utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory(prefix="bitcell-read-sweep-") as temp_dir:
        workdir = Path(temp_dir)
        for corner in args.corners:
            for vdd, temp_c, cap_f, state in itertools.product(
                args.vdd_values, args.temps_c, args.cap_f, args.states
            ):
                    suffix = f"{corner}_{vdd:g}V_{temp_c:g}C_{cap_f:g}f_q{state}"
                    deck_path = workdir / f"tb_{suffix}.spice"
                    raw_path = workdir / f"tb_{suffix}.raw"
                    deck_path.write_text(
                        make_deck(
                            template,
                            corner,
                            cap_f,
                            state,
                            str(raw_path),
                            args.wpu,
                            args.wpd,
                            args.wacc,
                            vdd,
                            temp_c,
                            args.tran_step_ps,
                        ),
                        encoding="utf-8",
                    )
                    timed_out = False
                    try:
                        result = subprocess.run(
                            ["ngspice", "-n", "-b", str(deck_path)],
                            cwd=workdir,
                            text=True,
                            capture_output=True,
                            check=False,
                            timeout=args.timeout_s,
                        )
                        returncode = result.returncode
                        output = f"{result.stdout}\n{result.stderr}"
                    except subprocess.TimeoutExpired as exc:
                        timed_out = True
                        returncode = 124
                        stdout = (
                            exc.stdout.decode()
                            if isinstance(exc.stdout, bytes)
                            else (exc.stdout or "")
                        )
                        stderr = (
                            exc.stderr.decode()
                            if isinstance(exc.stderr, bytes)
                            else (exc.stderr or "")
                        )
                        output = f"{stdout}\n{stderr}"
                    row: dict[str, object] = {
                        "corner": corner,
                        "vdd_v": vdd,
                        "temp_c": temp_c,
                        "cap_f": cap_f,
                        "stored_q": state,
                        "wpu_um": args.wpu,
                        "wpd_um": args.wpd,
                        "wacc_um": args.wacc,
                        "tran_step_ps": args.tran_step_ps,
                        "returncode": returncode,
                        "status": "FAIL",
                        "selected_bitline": "",
                        "blb_read_min_v": "",
                        "bl_read_min_v": "",
                        "delta_max_v": "",
                        "delta_21n_v": "",
                        "bl_pre_v": "",
                        "blb_pre_v": "",
                        "q_read_min_v": "",
                        "qb_read_min_v": "",
                        "q_read_max_v": "",
                        "qb_read_max_v": "",
                        "q_post_read_v": "",
                        "qb_post_read_v": "",
                        "read_disturb_peak_v": "",
                        "t_dv100_ns_from_wl": "",
                    }
                    if returncode == 0:
                        try:
                            measurements = parse_measurements(output)
                            selected_bitline = "BLB" if state == 1 else "BL"
                            selected_min = (
                                measurements["blb_read_min"]
                                if state == 1
                                else measurements["bl_read_min"]
                            )
                            delta_max = vdd - selected_min
                            delta_21n = (
                                measurements["bl_21n"] - measurements["blb_21n"]
                                if state == 1
                                else measurements["blb_21n"] - measurements["bl_21n"]
                            )
                            row["selected_bitline"] = selected_bitline
                            row["blb_read_min_v"] = measurements["blb_read_min"]
                            row["bl_read_min_v"] = measurements["bl_read_min"]
                            row["delta_max_v"] = delta_max
                            row["delta_21n_v"] = delta_21n
                            if "t_dv100" in measurements:
                                row["t_dv100_ns_from_wl"] = (
                                    measurements["t_dv100"] - 20e-9
                                ) * 1e9
                            row["bl_pre_v"] = measurements["bl_pre"]
                            row["blb_pre_v"] = measurements["blb_pre"]
                            row["q_read_min_v"] = measurements["q_read_min"]
                            row["qb_read_min_v"] = measurements["qb_read_min"]
                            row["q_read_max_v"] = measurements["q_read_max"]
                            row["qb_read_max_v"] = measurements["qb_read_max"]
                            row["q_post_read_v"] = measurements["q_post_read"]
                            row["qb_post_read_v"] = measurements["qb_post_read"]
                            stored_high_min = (
                                measurements["q_read_min"]
                                if state == 1
                                else measurements["qb_read_min"]
                            )
                            stored_low_max = (
                                measurements["qb_read_max"]
                                if state == 1
                                else measurements["q_read_max"]
                            )
                            stored_high_post = (
                                measurements["q_post_read"]
                                if state == 1
                                else measurements["qb_post_read"]
                            )
                            stored_low_post = (
                                measurements["qb_post_read"]
                                if state == 1
                                else measurements["q_post_read"]
                            )
                            row["read_disturb_peak_v"] = stored_low_max
                            row["status"] = (
                                "PASS"
                                if (
                                    measurements["bl_pre"] >= vdd - 0.1
                                    and measurements["blb_pre"] >= vdd - 0.1
                                    and delta_21n >= BITLINE_DELTA_MIN_V
                                    and stored_high_min >= vdd / 2
                                    and stored_low_max <= STORED_LOW_MAX_V
                                    and stored_high_post >= vdd / 2
                                    and stored_low_post <= STORED_LOW_MAX_V
                                )
                                else "MARGIN_FAIL"
                            )
                        except RuntimeError as error:
                            row["error"] = str(error)
                    elif timed_out:
                        row["error"] = f"ngspice timeout after {args.timeout_s:g} s"
                    else:
                        row["error"] = "ngspice failed"
                    rows.append(row)

    fieldnames = [
        "corner",
        "vdd_v",
        "temp_c",
        "cap_f",
        "stored_q",
        "wpu_um",
        "wpd_um",
        "wacc_um",
        "tran_step_ps",
        "returncode",
        "status",
        "selected_bitline",
        "bl_read_min_v",
        "blb_read_min_v",
        "delta_max_v",
        "delta_21n_v",
        "bl_pre_v",
        "blb_pre_v",
        "q_read_min_v",
        "qb_read_min_v",
        "q_read_max_v",
        "qb_read_max_v",
        "q_post_read_v",
        "qb_post_read_v",
        "read_disturb_peak_v",
        "t_dv100_ns_from_wl",
        "error",
    ]
    with args.output.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)

    print("corner  cap_f  Q  line  line_min(V)  delta_21n(V)  low_peak(V)  status")
    for row in rows:
        print(
            f"{row['corner']:>6}  {row['cap_f']:>5}  {row['stored_q']}  "
            f"{row['selected_bitline']:>4}  "
            f"{str(row['bl_read_min_v'] if row['selected_bitline'] == 'BL' else row['blb_read_min_v']):>11}  "
            f"{str(row['delta_21n_v']):>12}  "
            f"{str(row['read_disturb_peak_v']):>11}  {str(row['t_dv100_ns_from_wl']):>12}  {row['status']}"
        )
    print(f"CSV: {args.output}")
    return 0 if all(row["status"] == "PASS" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
