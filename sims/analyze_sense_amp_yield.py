#!/usr/bin/env python3
"""Summarize sense-amplifier mismatch evidence against a zero-failure yield gate."""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="+", type=Path)
    parser.add_argument(
        "--target-fail-rate",
        type=float,
        default=1e-3,
        help="Maximum accepted failure probability (default: 0.001 = 0.1%%).",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.95,
        help="One-sided confidence level for zero-failure upper bound.",
    )
    return parser.parse_args()


def zero_fail_upper_bound(n: int, confidence: float) -> float:
    """Exact one-sided binomial upper bound when zero failures are observed."""
    return 1.0 - (1.0 - confidence) ** (1.0 / n)


def required_zero_fail_samples(target_fail_rate: float, confidence: float) -> int:
    return math.ceil(
        math.log(1.0 - confidence) / math.log(1.0 - target_fail_rate)
    )


def main() -> int:
    args = parse_args()
    if not 0.0 < args.target_fail_rate < 1.0:
        raise SystemExit("--target-fail-rate must be between 0 and 1")
    if not 0.0 < args.confidence < 1.0:
        raise SystemExit("--confidence must be between 0 and 1")

    required = required_zero_fail_samples(args.target_fail_rate, args.confidence)
    print(
        f"acceptance: zero failures, one-sided confidence={args.confidence:.3f}, "
        f"target p_fail<={args.target_fail_rate:.6g}; required N={required}"
    )

    groups: dict[tuple[str, float], list[dict[str, str]]] = defaultdict(list)
    for path in args.csv:
        with path.open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                groups[(row["corner"], float(row["delta_mv"]))].append(row)

    any_reject = False
    for (corner, delta_mv), rows in sorted(groups.items()):
        failures = sum(row["status"] != "PASS" for row in rows)
        n = len(rows)
        delays = [
            float(row["t_res_from_sclk50_ns"])
            for row in rows
            if row.get("t_res_from_sclk50_ns")
        ]
        worst = max(delays) if delays else float("nan")
        if failures:
            status = "REJECT"
            bound_text = "n/a (observed failures)"
            any_reject = True
        else:
            upper = zero_fail_upper_bound(n, args.confidence)
            status = "ACCEPT" if n >= required else "INSUFFICIENT_N"
            bound_text = f"{upper:.6g}"
            any_reject |= status != "ACCEPT"
        print(
            f"{corner:5s} delta={delta_mv:7.1f} mV "
            f"PASS={n-failures}/{n} worst_t={worst:.5f} ns "
            f"p_fail_upper={bound_text} {status}"
        )

    return 1 if any_reject else 0


if __name__ == "__main__":
    raise SystemExit(main())
