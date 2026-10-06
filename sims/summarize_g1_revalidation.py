#!/usr/bin/env python3
"""Validate and consolidate per-case G1 read/write revalidation results."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--parts-dir",
        type=Path,
        default=root / "sims" / "g1_revalidation_65ff_parts",
    )
    p.add_argument(
        "--read-output",
        type=Path,
        default=root / "sims" / "bitcell_read_65ff_pvt_screen.csv",
    )
    p.add_argument(
        "--write-output",
        type=Path,
        default=root / "sims" / "bitcell_write_driver_65ff_pvt.csv",
    )
    return p.parse_args()


def load_rows(paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        with path.open(newline="", encoding="utf-8") as stream:
            row = next(csv.DictReader(stream), None)
        if row is None:
            raise RuntimeError(f"empty part CSV: {path}")
        rows.append(row)
    return rows


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    read_paths = sorted(args.parts_dir.glob("read_*.csv"))
    write_paths = sorted(args.parts_dir.glob("write_*.csv"))
    if len(read_paths) != 60 or len(write_paths) != 60:
        raise SystemExit(
            f"incomplete G1 parts: read={len(read_paths)}/60 write={len(write_paths)}/60"
        )

    reads = load_rows(read_paths)
    writes = load_rows(write_paths)
    read_fail = [row for row in reads if row.get("status") != "PASS"]
    write_fail = [
        row for row in writes
        if not (
            row.get("returncode") == "0"
            and row.get("initialized") == "True"
            and row.get("switched") == "True"
        )
    ]
    if read_fail or write_fail:
        raise SystemExit(
            f"G1 contains failures: read={len(read_fail)} write={len(write_fail)}"
        )

    reads.sort(
        key=lambda r: (
            r["corner"], float(r["vdd_v"]), float(r["temp_c"]), int(r["stored_q"])
        )
    )
    writes.sort(
        key=lambda r: (
            r["corner"], float(r["vdd_v"]), float(r["temp_c"]),
            int(r["stored_q_before"]),
        )
    )
    write_rows(args.read_output, reads)
    write_rows(args.write_output, writes)

    worst_disturb = max(reads, key=lambda r: float(r["read_disturb_peak_v"]))
    slowest_t100 = max(reads, key=lambda r: float(r["t_dv100_ns_from_wl"]))
    min_delta = min(reads, key=lambda r: float(r["delta_21n_v"]))
    worst_write = max(writes, key=lambda r: float(r["full_flip_delay_ns"]))

    print("G1 65 fF: read=60/60 PASS write=60/60 PASS")
    print(
        "worst read-disturb: "
        f"{worst_disturb['read_disturb_peak_v']} V at "
        f"{worst_disturb['corner']}/{worst_disturb['vdd_v']}V/"
        f"{worst_disturb['temp_c']}C/Q{worst_disturb['stored_q']}"
    )
    print(
        "slowest t100: "
        f"{slowest_t100['t_dv100_ns_from_wl']} ns at "
        f"{slowest_t100['corner']}/{slowest_t100['vdd_v']}V/"
        f"{slowest_t100['temp_c']}C/Q{slowest_t100['stored_q']}"
    )
    print(
        "minimum delta@21ns: "
        f"{min_delta['delta_21n_v']} V at "
        f"{min_delta['corner']}/{min_delta['vdd_v']}V/"
        f"{min_delta['temp_c']}C/Q{min_delta['stored_q']}"
    )
    print(
        "worst write full-flip: "
        f"{worst_write['full_flip_delay_ns']} ns; "
        f"WL_min_30pct={worst_write['wl_min_30pct_ns']} ns at "
        f"{worst_write['corner']}/{worst_write['vdd_v']}V/"
        f"{worst_write['temp_c']}C/Q{worst_write['stored_q_before']}"
    )
    print(f"read CSV: {args.read_output}")
    print(f"write CSV: {args.write_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
