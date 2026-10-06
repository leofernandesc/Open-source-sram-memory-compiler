#!/usr/bin/env python3
"""Run a nominal TT functional screen of the Xschem dynamic row decoder."""

from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import tempfile
from pathlib import Path


NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
MEASURE_RE = re.compile(rf"^\s*(\S+)\s*=\s*({NUMBER})", re.MULTILINE)
OUTPUTS = ("DEC0", "DEC1", "DEC2", "DEC3")
EVALUATION_SAMPLES = (("00", 15), ("01", 35), ("10", 55), ("11", 75))
PRECHARGE_SAMPLES_NS = (5, 25, 45, 65, 85)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "sims/row_decoder/row_decoder_tt.csv",
        help="CSV path for sampled output voltages and screening results.",
    )
    return parser.parse_args()


def make_deck(netlist: str, model_lib: Path) -> str:
    body = re.sub(r"(?im)^\s*\.end\s*$", "", netlist).rstrip()
    lines = [
        '* Generated TT row-decoder screen; source schematic is tb_row_decoder.sch.',
        f'.lib "{model_lib}" tt',
        ".temp 27",
        ".options ngbehavior=ps method=gear reltol=1e-4 vabstol=1e-9 iabstol=1e-12",
        body,
        ".tran 10p 90n 0 10p uic",
    ]

    for address, sample_ns in EVALUATION_SAMPLES:
        for index, output in enumerate(OUTPUTS):
            lines.append(
                f".meas tran eval_{address}_{output.lower()} "
                f"find v({output}) at={sample_ns}n"
            )
    for sample_ns in PRECHARGE_SAMPLES_NS:
        for output in OUTPUTS:
            lines.append(
                f".meas tran pre_{sample_ns}_{output.lower()} "
                f"find v({output}) at={sample_ns}n"
            )
    lines.append(".end")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[2]
    schematic = root / "sims/row_decoder/tb_row_decoder.sch"
    symbol_dir = root / "cells/row_decoder"
    pdk_root = Path(os.environ.get("PDK_ROOT", "/opt/pdks"))
    model_lib = pdk_root / "sky130A/libs.tech/combined/continuous/sky130.lib.spice"
    if not model_lib.is_file():
        raise SystemExit(f"SKY130A model library not found: {model_lib}")

    library_path = ":".join(
        (
            "/usr/local/share/xschem/xschem_library/devices",
            str(pdk_root / "sky130A/libs.tech/xschem"),
            str(symbol_dir),
        )
    )

    with tempfile.TemporaryDirectory(prefix="row-decoder-tt-") as temp_name:
        temp = Path(temp_name)
        xschem = subprocess.run(
            [
                "xschem", "-x", "-q", "-n", "--tcl",
                f"set XSCHEM_LIBRARY_PATH {{{library_path}}}",
                "-o", str(temp), str(schematic),
            ],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=45,
        )
        generated_netlist = temp / "tb_row_decoder.spice"
        if not generated_netlist.is_file():
            print(xschem.stdout, end="")
            print(xschem.stderr, end="")
            raise SystemExit(f"Xschem did not generate {generated_netlist.name}.")

        deck = make_deck(generated_netlist.read_text(encoding="utf-8"), model_lib)
        deck_path = temp / "row_decoder_tt.spice"
        deck_path.write_text(deck, encoding="utf-8")
        ngspice = subprocess.run(
            ["ngspice", "-n", "-b", str(deck_path)],
            cwd=temp,
            text=True,
            capture_output=True,
            check=False,
            timeout=90,
        )

    simulator_output = ngspice.stdout + "\n" + ngspice.stderr
    values = {name.lower(): float(value) for name, value in MEASURE_RE.findall(simulator_output)}
    expected_names = {
        f"eval_{address}_{output.lower()}"
        for address, _ in EVALUATION_SAMPLES
        for output in OUTPUTS
    } | {
        f"pre_{sample_ns}_{output.lower()}"
        for sample_ns in PRECHARGE_SAMPLES_NS
        for output in OUTPUTS
    }
    missing = sorted(expected_names - values.keys())
    if ngspice.returncode or missing:
        print(simulator_output)
        raise SystemExit(
            f"ngspice failed (return code {ngspice.returncode}); "
            f"missing measurements: {missing}"
        )

    xschem_text = xschem.stdout + "\n" + xschem.stderr
    xschem_structural_ok = xschem.returncode == 0 and "Error:" not in xschem_text
    rows: list[dict[str, object]] = []
    low_limit_v = 0.1 * 1.8
    high_limit_v = 0.9 * 1.8

    for address, sample_ns in EVALUATION_SAMPLES:
        selected = int(address, 2)
        for index, output in enumerate(OUTPUTS):
            measured = values[f"eval_{address}_{output.lower()}"]
            expected = 1 if index == selected else 0
            passed = measured >= high_limit_v if expected else measured <= low_limit_v
            rows.append(
                {
                    "corner": "tt",
                    "vdd_v": 1.8,
                    "temperature_c": 27,
                    "phase": "evaluate",
                    "address": address,
                    "sample_time_ns": sample_ns,
                    "output": output,
                    "voltage_v": measured,
                    "expected_logic": expected,
                    "criterion": f">={high_limit_v:g} V" if expected else f"<={low_limit_v:g} V",
                    "result": "PASS" if passed else "FAIL",
                    "xschem_returncode": xschem.returncode,
                    "xschem_structural_status": "PASS" if xschem_structural_ok else "FAIL",
                    "ngspice_returncode": ngspice.returncode,
                }
            )

    for sample_ns in PRECHARGE_SAMPLES_NS:
        for output in OUTPUTS:
            measured = values[f"pre_{sample_ns}_{output.lower()}"]
            passed = measured <= low_limit_v
            rows.append(
                {
                    "corner": "tt",
                    "vdd_v": 1.8,
                    "temperature_c": 27,
                    "phase": "precharge",
                    "address": "x",
                    "sample_time_ns": sample_ns,
                    "output": output,
                    "voltage_v": measured,
                    "expected_logic": 0,
                    "criterion": f"<={low_limit_v:g} V",
                    "result": "PASS" if passed else "FAIL",
                    "xschem_returncode": xschem.returncode,
                    "xschem_structural_status": "PASS" if xschem_structural_ok else "FAIL",
                    "ngspice_returncode": ngspice.returncode,
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    passed = sum(row["result"] == "PASS" for row in rows)
    failed = len(rows) - passed
    print(f"Xschem return code: {xschem.returncode}")
    diagnostics = [line for line in xschem_text.splitlines() if "Error:" in line]
    for line in diagnostics:
        print(f"Xschem: {line.strip()}")
    print(f"ngspice return code: {ngspice.returncode}")
    print(f"Voltage samples: {passed} PASS, {failed} FAIL")
    print(f"CSV: {args.output}")

    return 0 if xschem_structural_ok and failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
