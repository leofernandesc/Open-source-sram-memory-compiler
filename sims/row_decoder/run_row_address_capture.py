#!/usr/bin/env python3
"""Netlist and functionally check the two-bit captured row-address cell."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
SCHEMATIC = ROOT / "cells/control/row_address_capture.sch"
SYMBOL = ROOT / "cells/control/row_address_capture.sym"
TESTBENCH = ROOT / "sims/row_decoder/tb_row_address_capture.v"
CONTROL_WRAPPER = ROOT / "cells/control/captured_row_decoder_control.sch"
CONTROL_WRAPPER_SYMBOL = ROOT / "cells/control/captured_row_decoder_control.sym"
CONTROL_DIR = ROOT / "cells/control"
CONTROL_HIERARCHY = (
    ROOT / "cells/control/captured_pclk_phase_source.sch",
    ROOT / "cells/control/captured_pclk_phase_source.sym",
    ROOT / "cells/control/valid_access_capture.sch",
    ROOT / "cells/control/valid_access_capture.sym",
    ROOT / "cells/control/pclk_phase_source.sch",
    ROOT / "cells/control/pclk_phase_source.sym",
    ROOT / "cells/control/phase_delay_inv.sch",
    ROOT / "cells/control/phase_delay_inv.sym",
    ROOT / "cells/control/phase_and3.sch",
    ROOT / "cells/control/phase_and3.sym",
    ROOT / "cells/control/phase_or2.sch",
    ROOT / "cells/control/phase_or2.sym",
)
PDK_ROOT = Path("/opt/pdks/sky130A")
CELL_VERILOG = PDK_ROOT / "libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v"
CELL_PRIMITIVES = PDK_ROOT / "libs.ref/sky130_fd_sc_hd/verilog/primitives.v"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], cwd: Path, log: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    captured = result.stdout.rstrip()
    log.write_text(captured + ("\n" if captured else ""), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", help="New result directory; defaults to a UTC-stamped name")
    args = parser.parse_args()
    if args.output_dir:
        output = (ROOT / args.output_dir).resolve()
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output = ROOT / "sims/row_decoder/results" / f"row_address_capture_{stamp}"
    if not output.is_relative_to(ROOT):
        parser.error("output directory must remain inside the repository")
    if output.exists():
        parser.error(f"output directory already exists: {output}")
    output.mkdir(parents=True)

    required = (SCHEMATIC, SYMBOL, TESTBENCH, CONTROL_WRAPPER,
                CONTROL_WRAPPER_SYMBOL, *CONTROL_HIERARCHY,
                CELL_VERILOG, CELL_PRIMITIVES)
    for path in required:
        if not path.is_file():
            print(f"ERROR: required file is unavailable: {path}", file=sys.stderr)
            return 2

    manifest: dict[str, object] = {
        "campaign": "row_address_capture_functional",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "complete": False,
        "scope": ("Xschem-generated SKY130 FD SC HD structural Verilog with functional models; "
                  "checks all two-bit address values at rising CLK edges and output hold only."),
        "interface": "CLK, A0, A1, VDD, VSS -> A0_Q, A1_Q",
        "capture_edge": "rising edge of CLK",
        "reset": "none; outputs are unspecified until first rising edge",
        "checks": {
            "address_values_captured": 4,
            "capture_checks_passed": 4,
            "hold_while_high_checks_passed": 4,
            "hold_after_falling_edge_checks_passed": 4,
        },
        "source_sha256": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (SCHEMATIC, SYMBOL, TESTBENCH, CONTROL_WRAPPER,
                         CONTROL_WRAPPER_SYMBOL, *CONTROL_HIERARCHY,
                         Path(__file__).resolve())
        },
        "pdk_model_sha256": {
            "sky130_fd_sc_hd.v": sha256(CELL_VERILOG),
            "primitives.v": sha256(CELL_PRIMITIVES),
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                           encoding="utf-8")

    xschem_log = output / "xschem.log"
    xschem = ["xschem", "-w", "-n", "-q", "-o", str(output), str(SCHEMATIC)]
    xschem_result = run(xschem, ROOT, xschem_log)
    netlist = output / "row_address_capture.v"
    if xschem_result.returncode != 0 or not netlist.is_file():
        print(f"Xschem failed; inspect {xschem_log}", file=sys.stderr)
        return 1
    netlist_text = "\n".join(
        line.rstrip() for line in netlist.read_text(encoding="utf-8").splitlines()) + "\n"
    netlist.write_text(netlist_text, encoding="utf-8")
    xschem_text = xschem_log.read_text(encoding="utf-8").lower()
    if "missing symbol" in xschem_text or "unresolved symbol" in xschem_text:
        print(f"Xschem reported a missing symbol; inspect {xschem_log}", file=sys.stderr)
        return 1
    if netlist_text.count("sky130_fd_sc_hd__dfxtp_1") != 2:
        print("Xschem netlist must contain exactly two dfxtp_1 address registers",
              file=sys.stderr)
        return 1
    if not all(token in netlist_text for token in (
            "XA0_FF", "XA1_FF", "A0_Q", "A1_Q")):
        print("Xschem netlist does not preserve both address register outputs",
              file=sys.stderr)
        return 1

    expected_symbol_ports = [
        "CLK", "A0", "A1", "CSb", "OEb", "WEb", "VDD", "VSS",
        "A0_Q", "A1_Q", "VALID_ACCESS_Q", "PCLK", "PRECH",
    ]
    symbol_text = CONTROL_WRAPPER_SYMBOL.read_text(encoding="utf-8")
    symbol_ports = re.findall(
        r"(?m)^B\s+\d+\s+[^\{]+\{name=(\w+)\s+dir=",
        symbol_text,
    )
    if symbol_ports != expected_symbol_ports:
        print(f"Control-wrapper symbol pin order differs: {symbol_ports}",
              file=sys.stderr)
        return 1

    wrapper_dir = output / "control_wrapper"
    wrapper_dir.mkdir()
    wrapper_log = output / "control_wrapper_xschem.log"
    wrapper_cmd = [
        "xschem", "--tcl", f"append XSCHEM_LIBRARY_PATH :{CONTROL_DIR}",
        "-n", "-q", "-o", str(wrapper_dir), str(CONTROL_WRAPPER),
    ]
    wrapper_result = run(wrapper_cmd, ROOT, wrapper_log)
    wrapper_netlist = wrapper_dir / "captured_row_decoder_control.spice"
    if wrapper_result.returncode != 0 or not wrapper_netlist.is_file():
        print(f"Xschem control-wrapper netlisting failed; inspect {wrapper_log}",
              file=sys.stderr)
        return 1
    wrapper_log_text = wrapper_log.read_text(encoding="utf-8").lower()
    wrapper_text = wrapper_netlist.read_text(encoding="utf-8")
    if "missing symbol" in wrapper_log_text or "symbol not found" in wrapper_log_text:
        print(f"Xschem reported a missing wrapper symbol; inspect {wrapper_log}",
              file=sys.stderr)
        return 1
    required_wrapper = (
        ".subckt captured_row_decoder_control CLK A0 A1 CSb OEb WEb VDD VSS A0_Q A1_Q VALID_ACCESS_Q PCLK PRECH",
        "XADDR CLK A0 A1 VDD VSS A0_Q A1_Q row_address_capture",
        "XPHASE CLK CSb OEb WEb VDD VSS VALID_ACCESS_Q PCLK PRECH captured_pclk_phase_source",
        "XA0_FF CLK A0 VSS VSS VDD VDD A0_Q sky130_fd_sc_hd__dfxtp_1",
        "XA1_FF CLK A1 VSS VSS VDD VDD A1_Q sky130_fd_sc_hd__dfxtp_1",
        "XACCESS CLK CSb OEb WEb VDD VSS VALID_ACCESS_Q valid_access_capture",
    )
    if not all(token in wrapper_text for token in required_wrapper):
        print("Captured address/control/phase hierarchy has unexpected net connections",
              file=sys.stderr)
        return 1

    executable = output / "simv"
    compile_log = output / "iverilog.log"
    compile_cmd = [
        "iverilog", "-g2012", "-DFUNCTIONAL", "-DUNIT_DELAY=#0",
        "-s", "tb_row_address_capture", "-o", str(executable),
        str(CELL_PRIMITIVES), str(CELL_VERILOG), str(netlist), str(TESTBENCH),
    ]
    compiled = run(compile_cmd, ROOT, compile_log)
    if compiled.returncode != 0:
        print(f"Icarus compilation failed; inspect {compile_log}", file=sys.stderr)
        return 1

    simulation_log = output / "simulation.log"
    simulated = run(["vvp", str(executable)], output, simulation_log)
    executable.unlink(missing_ok=True)
    simulation_text = simulated.stdout
    if simulated.returncode != 0 or "PASS: 4/4 row-address captures and 8/8 hold checks" not in simulation_text:
        print(f"Icarus simulation failed; inspect {simulation_log}", file=sys.stderr)
        return 1

    manifest.update({
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "complete": True,
        "xschem_command": xschem,
        "iverilog_command": compile_cmd,
        "results": {"status": "PASS", "failures": 0},
        "structural_integration": {
            "status": "PASS",
            "captured_row_address_outputs": ["A0_Q", "A1_Q"],
            "phase_outputs": ["PCLK", "PRECH"],
            "valid_access_output": "VALID_ACCESS_Q",
            "decoder_and_bitcell_row_included": False,
        },
        "limitations": [
            "No transistor-level timing, setup/hold, metastability, startup, or PVT screen.",
            "This leaf is not yet integrated into the captured decoder/PCLK/bitcell-row path.",
        ],
        "artifacts": ["row_address_capture.v", "xschem.log", "iverilog.log",
                      "simulation.log", "row_address_capture.vcd",
                      "control_wrapper_xschem.log",
                      "control_wrapper/captured_row_decoder_control.spice"],
    })
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                           encoding="utf-8")
    print(simulation_text, end="")
    print(f"Xschem netlist: {netlist.relative_to(ROOT)}")
    print(f"Results: {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
