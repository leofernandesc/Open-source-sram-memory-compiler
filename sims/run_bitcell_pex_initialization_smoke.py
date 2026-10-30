#!/usr/bin/env python3
"""Check both stored states at the extracted bitcell latch outputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import subprocess
import tempfile
from pathlib import Path

from pex_access_nodes import bitcell_storage_nodes
from run_cbl_device_capacitance import MODEL_LIB


MEASURE_RE = re.compile(
    r"^\s*(q_init|qb_init|q_min|q_max|qb_min|qb_max|q_final|qb_final)\s*=\s*"
    r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)",
    re.MULTILINE | re.IGNORECASE,
)


def make_deck(
    *, pex_text: str, subckt: str, q_node: str, qb_node: str,
    corner: str, vdd: float, temp_c: float, state: int,
) -> str:
    q = vdd if state else 0.0
    qb = 0.0 if state else vdd
    q_ref = f"v(xcell.{q_node})"
    qb_ref = f"v(xcell.{qb_node})"
    return f"""* Extracted 6T latch initialization and retention smoke.
.lib "{MODEL_LIB}" {corner}
.temp {temp_c:g}
{pex_text}
VDD vdd 0 {vdd:.12g}
VBL bl 0 {vdd:.12g}
VBLB blb 0 {vdd:.12g}
VWL wl 0 0
XCELL vdd bl blb 0 wl {subckt}
.nodeset {q_ref}={q:.12g} {qb_ref}={qb:.12g}
.ic {q_ref}={q:.12g} {qb_ref}={qb:.12g}
.options ngbehavior=ps method=gear reltol=1e-5
.tran 1p 5n
.meas tran q_init find {q_ref} at=1p
.meas tran qb_init find {qb_ref} at=1p
.meas tran q_min min {q_ref} from=1p to=5n
.meas tran q_max max {q_ref} from=1p to=5n
.meas tran qb_min min {qb_ref} from=1p to=5n
.meas tran qb_max max {qb_ref} from=1p to=5n
.meas tran q_final find {q_ref} at=5n
.meas tran qb_final find {qb_ref} at=5n
.end
"""


def run_case(deck: str, timeout_s: float) -> tuple[int, str]:
    with tempfile.TemporaryDirectory(prefix="bitcell-init-") as temp_dir:
        deck_path = Path(temp_dir) / "init_smoke.spice"
        deck_path.write_text(deck, encoding="utf-8")
        result = subprocess.run(
            ["ngspice", "-n", "-b", str(deck_path)],
            cwd=temp_dir,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_s,
        )
    return result.returncode, result.stdout + "\n" + result.stderr


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pex-netlist", type=Path,
        default=root / "layout/bitcell_6t/pex/bitcell_6t_pex.spice",
    )
    parser.add_argument("--corner", choices=("tt", "ff", "ss", "fs", "sf"), default="tt")
    parser.add_argument("--vdd", type=float, default=1.80)
    parser.add_argument("--temp-c", type=float, default=27.0)
    parser.add_argument("--timeout-s", type=float, default=60.0)
    parser.add_argument(
        "--output", type=Path,
        default=root / "sims/bitcell_pex_initialization_smoke.csv",
    )
    args = parser.parse_args()
    if not 0 < args.vdd <= 1.8 or args.timeout_s <= 0:
        parser.error("VDD must be in (0, 1.8] and timeout must be positive")

    pex_path = args.pex_netlist.resolve()
    pex_text = pex_path.read_text(encoding="utf-8")
    header = re.search(r"^\.subckt\s+(\S+)\s+(.+)$", pex_text, re.MULTILINE)
    if not header or tuple(header.group(2).split()) != ("VDD", "BL", "BLB", "VSS", "WL"):
        raise SystemExit(f"unexpected or missing bitcell PEX header: {pex_path}")
    subckt = header.group(1)
    q_node, qb_node = bitcell_storage_nodes(pex_text)
    pex_sha256 = hashlib.sha256(pex_path.read_bytes()).hexdigest()
    rows: list[dict[str, object]] = []

    for state in (0, 1):
        deck = make_deck(
            pex_text=pex_text, subckt=subckt, q_node=q_node, qb_node=qb_node,
            corner=args.corner, vdd=args.vdd, temp_c=args.temp_c, state=state,
        )
        row: dict[str, object] = {
            "corner": args.corner,
            "vdd_v": args.vdd,
            "temp_c": args.temp_c,
            "stored_q": state,
            "q_storage_node": q_node,
            "qb_storage_node": qb_node,
            "q_expected_v": args.vdd if state else 0.0,
            "qb_expected_v": 0.0 if state else args.vdd,
            "q_init_v": "",
            "qb_init_v": "",
            "q_min_v": "",
            "q_max_v": "",
            "qb_min_v": "",
            "qb_max_v": "",
            "q_final_v": "",
            "qb_final_v": "",
            "pex_netlist_path": str(pex_path),
            "pex_netlist_sha256": pex_sha256,
            "status": "ERROR",
            "error": "",
        }
        try:
            returncode, output = run_case(deck, args.timeout_s)
            if returncode != 0:
                raise RuntimeError(output.strip()[-1500:])
            measured = {key.lower(): float(value) for key, value in MEASURE_RE.findall(output)}
            required = {
                "q_init", "qb_init", "q_min", "q_max", "qb_min", "qb_max",
                "q_final", "qb_final",
            }
            if set(measured) != required:
                raise RuntimeError(f"missing transient measurements: {output.strip()[-1500:]}")
            for key, value in measured.items():
                row[f"{key}_v"] = f"{value:.9g}"
            low, high = 0.1 * args.vdd, 0.9 * args.vdd
            expected_high = state == 1
            valid = (
                all(measured[key] >= high for key in ("q_init", "q_min", "q_final"))
                and all(measured[key] <= low for key in ("qb_init", "qb_max", "qb_final"))
                if expected_high
                else all(measured[key] <= low for key in ("q_init", "q_max", "q_final"))
                and all(measured[key] >= high for key in ("qb_init", "qb_min", "qb_final"))
            )
            row["status"] = "PASS" if valid else "FAIL"
            if not valid:
                row["error"] = "latch outputs crossed the 10/90 percent rail limits during initialization or retention"
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            row["error"] = str(exc).replace("\n", " | ")[:1500]
        rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    passed = sum(row["status"] == "PASS" for row in rows)
    print(f"PASS={passed}/{len(rows)} CSV={args.output}")
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
