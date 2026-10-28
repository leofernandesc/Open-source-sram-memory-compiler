#!/usr/bin/env python3
"""Measure actual inverter DC trip points for interpreting decoder node margins.

This is a static transfer reference, not dynamic SNM or mismatch qualification.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import numpy as np
import run_row_decoder_contract as contract
import run_row_decoder_tt as screen
from plot_row_decoder_review import read_raw


def pair(netlist, circuit, names):
    _, lines = screen.subcircuit(netlist, circuit)
    result = []
    for index, name in enumerate(names):
        found = next(line for line in lines if line.split() and line.split()[0].upper() == name)
        tokens = found.split()
        rail = "VDD" if index == 0 else "0"
        tokens[:5] = ["XP" if index == 0 else "XN", "OUT", "IN", rail, rail]
        result.append(" ".join(tokens))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--netlist", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    screen.require(not args.output_dir.exists(), "Use a new output directory")
    args.output_dir.mkdir(parents=True)
    netlist = args.netlist.read_text()
    screen.inspect_netlist(netlist, True)
    (args.output_dir / "input_netlist.spice").write_text(netlist)
    families = {"decoder_output": ("row_decoder", ("XM9", "XM10")),
                "address_complement": ("row_decoder", ("XM1", "XM2")),
                "wl_first": ("wl_driver", ("XMP1", "XMN1")),
                "wl_second": ("wl_driver", ("XMP2", "XMN2"))}
    conditions = {**contract.PROFILES, "sf": ("sf", 1.8, 27), "fs": ("fs", 1.8, 27)}
    model = Path(os.environ.get("PDK_ROOT", "/opt/pdks")) / "sky130A/libs.tech/combined/continuous/sky130.lib.spice"
    rows = []
    with tempfile.TemporaryDirectory(prefix="decoder-trip-") as temp:
        folder = Path(temp)
        for profile, (corner, vdd, temperature) in conditions.items():
            for family, (circuit, names) in families.items():
                deck = (f'Inverter DC reference {family} {profile}\n.lib "{model}" {corner}\n'
                        f'.temp {temperature:g}\nVDD_SRC VDD 0 {vdd:g}\nVIN IN 0 0\n' +
                        "\n".join(pair(netlist, circuit, names)) +
                        f'\n.save v(IN) v(OUT) i(VDD_SRC)\n.dc VIN 0 {vdd:g} .001\n'
                        '.control\nset num_threads=1\nrun\nwrite dc.raw\nquit 0\n.endc\n.end\n')
                (folder / "dc.spice").write_text(deck)
                (folder / "dc.raw").unlink(missing_ok=True)
                result = subprocess.run(["ngspice", "-n", "-b", "dc.spice"], cwd=folder,
                                        capture_output=True, text=True, timeout=60)
                screen.require(result.returncode == 0 and (folder / "dc.raw").is_file()
                               and not re.search(r"Error:|aborted|failed!", result.stdout+result.stderr, re.I), result.stdout+result.stderr)
                raw = read_raw(folder / "dc.raw")
                x, y, current = raw["v(in)"], raw["v(out)"], raw["i(vdd_src)"]
                screen.require(np.isfinite(x).all() and np.isfinite(y).all() and np.isfinite(current).all()
                               and np.all(np.diff(x) > 0) and abs(x[0]) < 1e-9
                               and x[-1] >= vdd-.0005 and y[0] >= .9*vdd
                               and -.1*vdd <= y[-1] <= .1*vdd, "Invalid or incomplete DC curve")
                delta = y-x
                indexes = np.where((delta[:-1] >= 0) & (delta[1:] < 0))[0]
                screen.require(len(indexes) == 1, "Expected one inverter trip crossing")
                i = indexes[0]
                trip = x[i] + delta[i]/(delta[i]-delta[i+1])*(x[i+1]-x[i])
                gain = np.gradient(y, x)
                # Differential gain = -1 intersections define an auxiliary DC
                # transfer reference; this is not a static cell noise margin.
                high_gain = np.where(gain < -1)[0]
                screen.require(len(high_gain) > 0, "Missing inverter gain region")
                rows.append(dict(profile=profile, corner=corner, vdd_v=vdd, temperature_c=temperature,
                                 family=family, trip_v=float(trip), vil_gain_minus1_v=float(x[high_gain[0]]),
                                 vih_gain_minus1_v=float(x[high_gain[-1]]),
                                 max_gain_magnitude=float(-gain.min()), vol_v=float(y[-1]), voh_v=float(y[0]),
                                 current_input_low_a=float(-current[0]), current_input_high_a=float(-current[-1]),
                                 current_trip_a=float(np.interp(trip, x, -current))))
                screen.write_csv(args.output_dir / f"{profile}_{family}_transfer.csv",
                                 [dict(input_v=float(a), output_v=float(b), vdd_current_a=float(-c))
                                  for a, b, c in zip(x, y, current)])
        screen.write_csv(args.output_dir / "summary.csv", rows)
    manifest = dict(stage="pre-layout DC reference", netlist_sha256=hashlib.sha256(netlist.encode()).hexdigest(),
                    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    conditions=conditions, families=families, dc_step_v=.001,
                    model_sha256=hashlib.sha256(model.read_bytes()).hexdigest(), model_hash_scope="top-level library only",
                    tools={"ngspice": screen.tool_version("ngspice")},
                    note="VOUT=VIN interpolated trip; gain thresholds from 1 mV grid. Neither bitcell SNM nor dynamic noise/mismatch sign-off.")
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print(f"DC curves measured: {len(rows)}")


if __name__ == "__main__":
    main()
