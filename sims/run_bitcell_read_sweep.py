#!/usr/bin/env python3
"""Automate the SKY130A 6T bitcell read-disturb sweep."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import tempfile
from pathlib import Path


MEASURE_RE = re.compile(
    r"^\s*(?P<name>bl_read_min|blb_read_min|q_read_min|qb_read_min)\s*=\s*"
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
        default=[5.0, 10.0, 20.0, 50.0],
        help="Bitline capacitances in fF.",
    )
    parser.add_argument(
        "--corners",
        nargs="+",
        default=["tt", "ff", "ss"],
        choices=["tt", "ff", "ss", "fs", "sf"],
        help="SKY130A model corners.",
    )
    return parser.parse_args()


def replace_once(text: str, pattern: str, replacement: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"expected one match for {pattern!r}, found {count}")
    return updated


def make_deck(
    template: str, corner: str, cap_f: float, state: int, raw_name: str
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
        initial = ".ic V(Q)=1.8 V(QB)=0 V(bl)=1.8 V(blb)=1.8"
    else:
        initial = ".ic V(Q)=0 V(QB)=1.8 V(bl)=1.8 V(blb)=1.8"
    updated = replace_once(updated, r"^\.ic\s+.*$", initial)
    updated = replace_once(
        updated,
        r"^\.title\s+.*$",
        f".title bitcell_6t_read_{corner}_{cap_f:g}f_q{state}",
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
    return updated


def parse_measurements(output: str) -> dict[str, float]:
    measurements = {
        match.group("name"): float(match.group("value"))
        for match in MEASURE_RE.finditer(output)
    }
    missing = {"bl_read_min", "blb_read_min", "q_read_min", "qb_read_min"} - measurements.keys()
    if missing:
        raise RuntimeError(f"missing measurements: {', '.join(sorted(missing))}")
    return measurements


def main() -> int:
    args = parse_args()
    template = args.deck.read_text(encoding="utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory(prefix="bitcell-read-sweep-") as temp_dir:
        workdir = Path(temp_dir)
        for corner in args.corners:
            for cap_f in args.cap_f:
                for state in (1, 0):
                    suffix = f"{corner}_{cap_f:g}f_q{state}"
                    deck_path = workdir / f"tb_{suffix}.spice"
                    raw_path = workdir / f"tb_{suffix}.raw"
                    deck_path.write_text(
                        make_deck(template, corner, cap_f, state, str(raw_path)),
                        encoding="utf-8",
                    )
                    result = subprocess.run(
                        ["ngspice", "-n", "-b", str(deck_path)],
                        cwd=workdir,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    output = f"{result.stdout}\n{result.stderr}"
                    row: dict[str, object] = {
                        "corner": corner,
                        "cap_f": cap_f,
                        "stored_q": state,
                        "returncode": result.returncode,
                        "status": "FAIL",
                        "selected_bitline": "",
                        "blb_read_min_v": "",
                        "bl_read_min_v": "",
                        "delta_max_v": "",
                        "q_read_min_v": "",
                        "qb_read_min_v": "",
                    }
                    if result.returncode == 0:
                        try:
                            measurements = parse_measurements(output)
                            selected_bitline = "BLB" if state == 1 else "BL"
                            selected_min = (
                                measurements["blb_read_min"]
                                if state == 1
                                else measurements["bl_read_min"]
                            )
                            delta_max = 1.8 - selected_min
                            row["selected_bitline"] = selected_bitline
                            row["blb_read_min_v"] = measurements["blb_read_min"]
                            row["bl_read_min_v"] = measurements["bl_read_min"]
                            row["delta_max_v"] = delta_max
                            row["q_read_min_v"] = measurements["q_read_min"]
                            row["qb_read_min_v"] = measurements["qb_read_min"]
                            stored_high_min = (
                                measurements["q_read_min"]
                                if state == 1
                                else measurements["qb_read_min"]
                            )
                            row["status"] = (
                                "PASS"
                                if delta_max >= 0.050 and stored_high_min >= 0.9
                                else "MARGIN_FAIL"
                            )
                        except RuntimeError as error:
                            row["error"] = str(error)
                    else:
                        row["error"] = "ngspice failed"
                    rows.append(row)

    fieldnames = [
        "corner",
        "cap_f",
        "stored_q",
        "returncode",
        "status",
        "selected_bitline",
        "bl_read_min_v",
        "blb_read_min_v",
        "delta_max_v",
        "q_read_min_v",
        "qb_read_min_v",
        "error",
    ]
    with args.output.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print("corner  cap_f  Q  line  line_min(V)  delta_max(V)  q_min(V)  status")
    for row in rows:
        print(
            f"{row['corner']:>6}  {row['cap_f']:>5}  {row['stored_q']}  "
            f"{row['selected_bitline']:>4}  "
            f"{str(row['bl_read_min_v'] if row['selected_bitline'] == 'BL' else row['blb_read_min_v']):>11}  "
            f"{str(row['delta_max_v']):>12}  "
            f"{str(row['q_read_min_v']):>8}  {row['status']}"
        )
    print(f"CSV: {args.output}")
    return 0 if all(row["status"] == "PASS" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
