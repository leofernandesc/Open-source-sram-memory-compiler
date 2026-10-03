#!/usr/bin/env python3
"""Run the G1 60 fF read/write revalidation in bounded parallel batches."""

from __future__ import annotations

import argparse
import csv
import itertools
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corners",
        nargs="+",
        default=["tt", "ff", "ss", "fs", "sf"],
        choices=["tt", "ff", "ss", "fs", "sf"],
    )
    parser.add_argument("--vdd-values", nargs="+", type=float, default=[1.62, 1.80])
    parser.add_argument("--temps-c", nargs="+", type=float, default=[-40.0, 27.0, 125.0])
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Concurrent ngspice jobs; keep 1 unless the host has been benchmarked for parallel runs.",
    )
    parser.add_argument("--read-timeout-s", type=float, default=45.0)
    parser.add_argument("--write-timeout-s", type=float, default=45.0)
    parser.add_argument("--read-tran-step-ps", type=float, default=100.0)
    parser.add_argument(
        "--parts-dir",
        type=Path,
        default=Path(__file__).with_name("g1_revalidation_parts"),
    )
    return parser.parse_args()


def run_command(command: list[str], timeout_s: float) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_s,
        )
        return result.returncode, f"{result.stdout}\n{result.stderr}"
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return 124, f"{stdout}\n{stderr}"


def first_row(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as stream:
        return next(csv.DictReader(stream), {})


def main() -> int:
    args = parse_args()
    if args.jobs <= 0 or args.read_timeout_s <= 0 or args.write_timeout_s <= 0:
        raise SystemExit("jobs and timeouts must be positive")
    if args.read_tran_step_ps <= 0:
        raise SystemExit("read-tran-step-ps must be positive")

    sims = Path(__file__).resolve().parent
    args.parts_dir.mkdir(parents=True, exist_ok=True)
    tasks: list[tuple[str, str, float]] = []

    for corner, vdd, temp_c, state in itertools.product(
        args.corners, args.vdd_values, args.temps_c, (0, 1)
    ):
        stem = f"{corner}_{vdd:g}V_{temp_c:g}C_q{state}"
        read_output = args.parts_dir / f"read_{stem}.csv"
        write_output = args.parts_dir / f"write_{stem}.csv"
        read_command = [
            sys.executable,
            str(sims / "run_bitcell_read_sweep.py"),
            "--corners", corner,
            "--vdd-values", f"{vdd:g}",
            "--temps-c", f"{temp_c:g}",
            "--cap-f", "60",
            "--states", str(state),
            "--wpu", "0.42",
            "--wpd", "1.26",
            "--wacc", "0.60",
            "--tran-step-ps", f"{args.read_tran_step_ps:g}",
            "--timeout-s", f"{args.read_timeout_s:g}",
            "--output", str(read_output),
        ]
        write_command = [
            sys.executable,
            str(sims / "run_bitcell_write_driver_smoke.py"),
            "--corners", corner,
            "--vdd-values", f"{vdd:g}",
            "--temps-c", f"{temp_c:g}",
            "--states", str(state),
            "--wpd-values", "1.26",
            "--wpu", "0.42",
            "--wacc", "0.60",
            "--cbl-ff", "60",
            "--timeout-s", f"{args.write_timeout_s:g}",
            "--output", str(write_output),
        ]
        tasks.append((f"read:{stem}", "\0".join(read_command), args.read_timeout_s + 5.0))
        tasks.append((f"write:{stem}", "\0".join(write_command), args.write_timeout_s + 5.0))

    def execute(task: tuple[str, str, float]) -> tuple[str, int, str]:
        name, encoded, timeout_s = task
        return name, *run_command(encoded.split("\0"), timeout_s)

    with ThreadPoolExecutor(max_workers=min(args.jobs, len(tasks))) as executor:
        results = list(executor.map(execute, tasks))

    failures = 0
    for name, returncode, output in results:
        kind, stem = name.split(":", 1)
        row = first_row(args.parts_dir / f"{kind}_{stem}.csv")
        if kind == "read":
            passed = returncode == 0 and row.get("status") == "PASS"
            detail = row.get("status") or row.get("error") or f"rc={returncode}"
        else:
            passed = (
                returncode == 0
                and row.get("returncode") == "0"
                and row.get("initialized") == "True"
                and row.get("switched") == "True"
            )
            detail = (
                f"initialized={row.get('initialized', '')} "
                f"switched={row.get('switched', '')} rc={row.get('returncode', returncode)}"
            )
        print(f"{name} {'PASS' if passed else 'FAIL'} {detail}")
        if not passed:
            failures += 1
            if not row and output.strip():
                print(output.strip().splitlines()[-1])

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
