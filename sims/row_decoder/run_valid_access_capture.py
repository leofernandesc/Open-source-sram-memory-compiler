#!/usr/bin/env python3
"""Netlist and functionally check the captured valid-access qualifier."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
SCHEMATIC = ROOT / "cells/control/valid_access_capture.sch"
SYMBOL = ROOT / "cells/control/valid_access_capture.sym"
TESTBENCH = ROOT / "sims/row_decoder/tb_valid_access_capture.v"
PHASE_WRAPPER = ROOT / "cells/control/captured_pclk_phase_source.sch"
PHASE_WRAPPER_SYMBOL = ROOT / "cells/control/captured_pclk_phase_source.sym"
PHASE_SOURCE = ROOT / "cells/control/pclk_phase_source.sch"
PHASE_SOURCE_SYMBOL = ROOT / "cells/control/pclk_phase_source.sym"
CONTROL_DIR = ROOT / "cells/control"
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
    parser.add_argument(
        "--output-dir",
        help="New result directory; by default a unique UTC-stamped directory is used")
    args = parser.parse_args()
    if args.output_dir:
        output = (ROOT / args.output_dir).resolve()
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output = ROOT / "sims/row_decoder/results" / f"valid_access_capture_integrated_{stamp}"
    if output.exists():
        parser.error(f"output directory already exists: {output}")
    output.mkdir(parents=True)

    for path in (SCHEMATIC, SYMBOL, TESTBENCH, PHASE_WRAPPER,
                 PHASE_WRAPPER_SYMBOL, PHASE_SOURCE, PHASE_SOURCE_SYMBOL,
                 CELL_VERILOG, CELL_PRIMITIVES):
        if not path.is_file():
            print(f"ERROR: required file is unavailable: {path}", file=sys.stderr)
            return 2

    manifest: dict[str, object] = {
        "campaign": "valid_access_capture_functional",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "complete": False,
        "scope": ("Xschem-generated structural Verilog with SKY130 FD SC HD functional models; "
                  "checks control truth table and rising-edge capture/hold only; no analog timing, "
                  "setup/hold, metastability, or transistor-level standard-cell simulation."),
        "control_equation": "VALID_ACCESS_D = !CSb AND (OEb XOR WEb)",
        "capture_edge": "rising edge of CLK",
        "reset": "none; Q is unspecified until first rising edge",
        "generated_output_postprocess": "trailing whitespace stripped from generated Verilog lines; trailing blank lines stripped from tool logs",
        "checks": {
            "control_vectors_covered": 8,
            "rising_edge_capture_passes": 8,
            "hold_while_high_after_live_input_change": 8,
            "hold_after_falling_edge": 8,
        },
        "source_sha256": {
            str(p.relative_to(ROOT)): sha256(p)
            for p in (SCHEMATIC, SYMBOL, TESTBENCH, PHASE_WRAPPER,
                      PHASE_WRAPPER_SYMBOL, PHASE_SOURCE, PHASE_SOURCE_SYMBOL,
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
    netlist = output / "valid_access_capture.v"
    if xschem_result.returncode != 0 or not netlist.is_file():
        print(f"Xschem failed; inspect {xschem_log}", file=sys.stderr)
        return 1
    # Xschem emits trailing spaces on standard-cell instance lines. Strip only
    # line-ending whitespace so the archived generated netlist passes diff checks.
    netlist.write_text(
        "\n".join(line.rstrip() for line in netlist.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
    )
    xschem_text = xschem_log.read_text(encoding="utf-8").lower()
    if "missing symbol" in xschem_text or "unresolved symbol" in xschem_text:
        print(f"Xschem reported a missing symbol; inspect {xschem_log}", file=sys.stderr)
        return 1
    required_cells = (
        "sky130_fd_sc_hd__inv_1", "sky130_fd_sc_hd__xor2_1",
        "sky130_fd_sc_hd__and2_1", "sky130_fd_sc_hd__dfxtp_1",
    )
    if not all(cell in netlist.read_text(encoding="utf-8") for cell in required_cells):
        print("Xschem netlist does not contain all intended SKY130 cells", file=sys.stderr)
        return 1

    integration_output = output / "phase_source"
    integration_output.mkdir()
    integration_log = output / "phase_source_xschem.log"
    integration_cmd = [
        "xschem", "--tcl", f"append XSCHEM_LIBRARY_PATH :{CONTROL_DIR}",
        "-n", "-q", "-o", str(integration_output), str(PHASE_WRAPPER),
    ]
    integration_result = run(integration_cmd, ROOT, integration_log)
    integration_netlist = integration_output / "captured_pclk_phase_source.spice"
    if integration_result.returncode != 0 or not integration_netlist.is_file():
        print(f"Integrated Xschem netlisting failed; inspect {integration_log}",
              file=sys.stderr)
        return 1
    integration_text = integration_netlist.read_text(encoding="utf-8")
    integration_log_text = integration_log.read_text(encoding="utf-8").lower()
    if "symbol not found" in integration_log_text or "missing symbol" in integration_log_text:
        print(f"Integrated Xschem netlist has missing symbols; inspect {integration_log}",
              file=sys.stderr)
        return 1
    required_hierarchy = (
        ".subckt captured_pclk_phase_source CLK CSb OEb WEb VDD VSS VALID_ACCESS_Q PCLK PRECH",
        "XACCESS CLK CSb OEb WEb VDD VSS VALID_ACCESS_Q valid_access_capture",
        "XPHASE VDD CLK VSS VALID_ACCESS_Q PCLK PRECH pclk_phase_source",
        ".subckt pclk_phase_source",
    )
    if not all(token in integration_text for token in required_hierarchy):
        print("Integrated netlist does not preserve the intended captured-control/phase hierarchy",
              file=sys.stderr)
        return 1

    executable = output / "simv"
    compile_log = output / "iverilog.log"
    compile_cmd = [
        "iverilog", "-g2012", "-DFUNCTIONAL", "-DUNIT_DELAY=#0",
        "-s", "tb_valid_access_capture",
        "-o", str(executable), str(CELL_PRIMITIVES), str(CELL_VERILOG),
        str(netlist), str(TESTBENCH),
    ]
    compiled = run(compile_cmd, ROOT, compile_log)
    if compiled.returncode != 0:
        print(f"Icarus compilation failed; inspect {compile_log}", file=sys.stderr)
        return 1

    simulation_log = output / "simulation.log"
    simulated = run(["vvp", str(executable)], output, simulation_log)
    executable.unlink(missing_ok=True)
    simulation_text = simulated.stdout
    if simulated.returncode != 0 or "PASS: 8/8 control-vector captures" not in simulation_text:
        print(f"Icarus simulation failed; inspect {simulation_log}", file=sys.stderr)
        return 1

    manifest.update({
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "complete": True,
        "xschem_command": xschem,
        "phase_source_xschem_command": integration_cmd,
        "iverilog_command": compile_cmd,
        "vvp_command": ["vvp", str(executable)],
        "results": {"status": "PASS", "failures": 0},
        "artifacts": [
            "valid_access_capture.v", "xschem.log", "iverilog.log",
            "simulation.log", "capture.vcd", "vectors.csv",
            "phase_source/captured_pclk_phase_source.spice",
            "phase_source_xschem.log",
        ],
    })
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                           encoding="utf-8")
    print(simulation_text, end="")
    print(f"Xschem netlist: {netlist.relative_to(ROOT)}")
    print(f"Results: {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
