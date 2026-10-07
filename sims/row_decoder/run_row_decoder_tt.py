#!/usr/bin/env python3
"""Screen the dynamic decoder, with an optional loaded sizing testbench.

Stimulus overrides affect the generated deck, never the source schematic.
Results are pre-layout experiments, not macro timing or physical sign-off.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
MEASURE_RE = re.compile(rf"^\s*(\S+)\s*=\s*({NUMBER})", re.MULTILINE)
OUTPUTS = ("DEC0", "DEC1", "DEC2", "DEC3")
EVALUATION_SAMPLES = (("00", 15), ("01", 35), ("10", 55), ("11", 75))
PRECHARGE_SAMPLES_NS = (5, 25, 45, 65, 85)
# Published nfet_01v8 model-validity bound, not a foundry reliability rating.
NFET_MODEL_VGS_MAX = 1.95
MODEL_CATEGORIES = {"output_nmos_vgs_upper", "full_dynamic_node_vgs_upper",
                    "address_nmos_vds_upper"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def positive(text: str) -> float:
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("must be finite and positive")
    return value


def logic_limits(expected_high: bool, vdd: float) -> tuple[float, float]:
    return ((0.9 if expected_high else -0.1) * vdd,
            (1.1 if expected_high else 0.1) * vdd)


def passes_voltage(value: float, expected_high: bool, vdd: float) -> bool:
    low, high = logic_limits(expected_high, vdd)
    return math.isfinite(value) and low <= value <= high


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bench", choices=("functional", "sizing"), default="functional")
    parser.add_argument("--candidate", default="current")
    parser.add_argument("--corner", choices=("tt", "ss", "ff", "sf", "fs"), default="tt")
    parser.add_argument("--vdd", type=positive, default=1.8)
    parser.add_argument("--temp-c", type=float, default=27,
                        help="Experimental condition; project nominal temperature remains open.")
    parser.add_argument("--wl-cap-ff", type=positive)
    parser.add_argument("--clock-slew-ps", type=positive)
    parser.add_argument("--address-slew-ps", type=positive)
    parser.add_argument("--max-step-ps", type=positive, default=10)
    parser.add_argument("--method", choices=("gear", "trap"), default="gear")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--metrics-output", type=Path)
    parser.add_argument("--artifacts-dir", type=Path,
                        help="Keep generated netlist, deck, logs and raw waveform here.")
    args = parser.parse_args()
    if not math.isfinite(args.temp_c):
        parser.error("--temp-c must be finite")
    if args.wl_cap_ff is not None and args.bench != "sizing":
        parser.error("--wl-cap-ff requires --bench sizing")
    args.output = args.output or ROOT / "sims/row_decoder" / (
        "row_decoder_tt.csv" if args.bench == "functional" else "row_decoder_sizing.csv")
    args.metrics_output = args.metrics_output or args.output.with_name(args.output.stem + "_metrics.csv")
    if args.output.resolve() == args.metrics_output.resolve():
        parser.error("sample and metric CSV paths must differ")
    return args


def spice_number(text: str) -> float:
    match = re.fullmatch(rf"({NUMBER})([a-z]*)", text.lower())
    scales = {"": 1, "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6,
              "m": 1e-3, "k": 1e3, "meg": 1e6, "g": 1e9}
    require(match is not None and match[2] in scales, f"Unsupported SPICE value {text!r}")
    return float(match[1]) * scales[match[2]]


def logical_lines(text: str) -> list[str]:
    return re.sub(r"\n\s*\+\s*", " ", text).splitlines()


def subcircuit(netlist: str, name: str) -> tuple[list[str], list[str]]:
    match = re.search(rf"(?ims)^\.subckt\s+{name}\s+([^\n]+)\n(.*?)^\.ends\b", netlist)
    require(match is not None, f"Missing .subckt {name}")
    return match[1].upper().split(), logical_lines(match[2])


def inspect_netlist(netlist: str, loaded: bool) -> tuple[dict, dict]:
    pins, lines = subcircuit(netlist, "row_decoder")
    require(set(pins) == {"VDD", "VSS", "PCLK", "A0", "A1", *OUTPUTS}
            and len(pins) == 9, "Unexpected decoder interface")
    devices = {}
    for line in lines:
        parts = line.upper().split()
        if parts and parts[0].startswith("XM"):
            require(len(parts) >= 6, "Malformed MOS instance")
            name = parts[0][1:]
            require(name not in devices, f"Duplicate device {name}")
            params = {}
            for key in ("W", "L", "NF"):
                match = re.search(rf"\b{key}=({NUMBER})(?=\s|$)", line, re.I)
                require(match is not None, f"{name}: missing numeric {key}")
                params[key] = float(match[1])
            devices[name] = dict(nodes=parts[1:5], model=parts[5], **params)
    require(set(devices) == {f"M{i}" for i in range(1, 26)}, "Expected exactly M1..M25")
    pm = {1, 3, 5, 9, 11, 14, 16, 19, 21, 24}
    for i in range(1, 26):
        device = devices[f"M{i}"]
        kind = "PFET" if i in pm else "NFET"
        require(device["model"] == f"SKY130_FD_PR__{kind}_01V8", f"M{i}: wrong model")
        require(device["nodes"][3] == ("VDD" if i in pm else "VSS"), f"M{i}: wrong bulk")
        require(device["NF"] >= 1 and device["NF"].is_integer()
                and device["W"] / device["NF"] >= 0.42
                and device["L"] >= 0.15, f"M{i}: below ordinary W/finger=0.42 or L=0.15 um screen")
    expected = {"M1": ["A0B", "A0", "VDD", "VDD"], "M2": ["A0B", "A0", "VSS", "VSS"],
                "M3": ["A1B", "A1", "VDD", "VDD"], "M4": ["A1B", "A1", "VSS", "VSS"],
                "M8": ["EVAL_GND", "PCLK", "VSS", "VSS"]}
    middle_nodes = []
    for row, group in enumerate(((5, 6, 7, 9, 10), (11, 12, 13, 14, 15),
                                  (16, 17, 18, 19, 20), (21, 22, 23, 24, 25))):
        pre, upper, lower, p_out, n_out = group
        middle = devices[f"M{upper}"]["nodes"][2]
        require(middle not in {"VDD", "VSS", "EVAL_GND", "PCLK", "A0", "A1", "A0B", "A1B",
                              *OUTPUTS, "N0", "N1", "N2", "N3"}, f"Row {row}: shorted stack node")
        middle_nodes.append(middle)
        expected.update({
            f"M{pre}": [f"N{row}", "PCLK", "VDD", "VDD"],
            f"M{upper}": [f"N{row}", "A1B" if row < 2 else "A1", middle, "VSS"],
            f"M{lower}": [middle, "A0B" if row % 2 == 0 else "A0", "EVAL_GND", "VSS"],
            f"M{p_out}": [f"DEC{row}", f"N{row}", "VDD", "VDD"],
            f"M{n_out}": [f"DEC{row}", f"N{row}", "VSS", "VSS"]})
    require(len(set(middle_nodes)) == 4, "Stack nodes are incorrectly shared")
    for name, nodes in expected.items():
        require(devices[name]["nodes"] == nodes,
                f"{name}: expected D/G/S/B={nodes}, got {devices[name]['nodes']}")

    top = logical_lines(netlist.split("* expanding", 1)[0])
    instance = next((line.split() for line in top if line.lower().startswith("x1 ")), None)
    require(instance is not None and len(instance) == 11 and instance[-1].lower() == "row_decoder",
            "Unsupported decoder testbench instance x1")
    mapping = dict(zip(pins, instance[1:-1]))
    require(len({node.upper() for node in mapping.values()}) == 9, "Top decoder pins are shorted")
    require(mapping["VSS"].upper() in {"GND", "0"}, "This screen requires VSS at simulation ground")
    nodes = {output: mapping[output] for output in OUTPUTS}
    if loaded:
        driver_pins, _ = subcircuit(netlist, "wl_driver")
        require(set(driver_pins) == {"VDD", "VSS", "WL_IN", "WL"}, "Unexpected WL-driver pins")
        drivers = {}
        for line in top:
            parts = line.split()
            if parts and parts[0].lower().startswith("x") and parts[-1].lower() == "wl_driver":
                require(len(parts) == 6, "Unsupported WL instance")
                connection = dict(zip(driver_pins, parts[1:-1]))
                require(connection["VDD"] == mapping["VDD"] and connection["VSS"] == mapping["VSS"],
                        "Incorrect driver rails")
                require(connection["WL_IN"] not in drivers, "Duplicated driver input")
                drivers[connection["WL_IN"]] = connection["WL"]
        require(set(drivers) == {mapping[out] for out in OUTPUTS}, "Need one driver per DEC")
        wl_nodes = [drivers[mapping[out]] for out in OUTPUTS]
        require(len(set(wl_nodes)) == 4 and not set(wl_nodes) & set(mapping.values()), "Shorted WL")
        for i, node in enumerate(wl_nodes):
            nodes[f"WL{i}"] = node
            cap = next((line.split() for line in top if line.upper().startswith(f"C_WL{i} ")), None)
            require(cap is not None and cap[1:3] == [node, mapping["VSS"]], f"Wrong C_WL{i} connection")
    nodes["PCLK"] = mapping["PCLK"]
    return nodes, devices


def prepare_stimulus(netlist: str, args: argparse.Namespace) -> tuple[str, float, float]:
    source = re.search(r"(?im)^VDD_SRC\s+\S+\s+\S+\s+(\S+)\s*$", netlist)
    require(source is not None, "Missing VDD_SRC")
    original_vdd = spice_number(source[1])
    netlist = re.sub(r"(?im)^(VDD_SRC\s+\S+\s+\S+)\s+\S+\s*$", rf"\g<1> {args.vdd:.12g}", netlist)
    schedule = {"VPCLK": (10e-9, 10e-9, 20e-9), "VA0": (22e-9, 20e-9, 40e-9),
                "VA1": (42e-9, 40e-9, 80e-9)}
    rise = fall = 0.0
    for name, times in schedule.items():
        pattern = rf"(?im)^({name}\s+\S+\s+\S+)\s+PULSE\(([^)]+)\)\s*$"
        match = re.search(pattern, netlist)
        require(match is not None, f"Missing {name}")
        values = [spice_number(part) for part in match[2].split()]
        require(len(values) == 7 and values[0] == 0 and math.isclose(values[1], original_vdd)
                and all(math.isclose(values[i], t, rel_tol=1e-9, abs_tol=1e-15)
                        for i, t in zip((2, 5, 6), times)), f"{name}: unsupported address/clock schedule")
        override = args.clock_slew_ps if name == "VPCLK" else args.address_slew_ps
        values[1] = args.vdd
        if override is not None:
            values[3] = values[4] = override * 1e-12
        require(values[3] > 0 and values[4] > 0 and values[3] + values[4] < 4e-9,
                f"{name}: slew is outside this fixed-schedule bench")
        if name == "VPCLK":
            rise, fall = values[3:5]
        replacement = match[1] + " PULSE(" + " ".join(f"{v:.12g}" for v in values) + ")"
        netlist = re.sub(pattern, lambda _: replacement, netlist)
    if args.wl_cap_ff is not None:
        netlist, count = re.subn(r"(?im)^(C_WL[0-3]\s+\S+\s+\S+)\s+\S+",
                                rf"\g<1> {args.wl_cap_ff * 1e-15:.12g}", netlist)
        require(count == 4, "Need four WL capacitors")
    return netlist, rise, fall


def make_deck(netlist: str, model_lib: Path, nodes: dict, args: argparse.Namespace,
              rise: float, fall: float) -> tuple[str, list[dict]]:
    body = re.sub(r"(?im)^\s*\.end\s*$", "", netlist).rstrip()
    lines = [f"* Dynamic decoder {args.bench} screen",
             f'.lib "{model_lib}" {args.corner}', f".temp {args.temp_c:g}",
             f".options ngbehavior=ps method={args.method} reltol=1e-4 vabstol=1e-9 iabstol=1e-12",
             body, f".tran {args.max_step_ps:g}p 90n 0 {args.max_step_ps:g}p uic"]
    metrics = []
    outputs = {key: value for key, value in nodes.items() if key != "PCLK"}

    def measure(name, expression, category, unit, address="x", output="", low=None, high=None):
        lines.append(f".meas tran {name} {expression}")
        metrics.append(dict(name=name, category=category, unit=unit, address=address,
                            output=output, low=low, high=high))

    for cycle, (address, sample_ns) in enumerate(EVALUATION_SAMPLES):
        start = (10 + 20 * cycle) * 1e-9
        falling = start + rise + 10e-9
        for output, node in outputs.items():
            lines.append(f".meas tran eval_{address}_{output.lower()} FIND v({node}) AT={sample_ns}n")
            selected = int(output[-1]) == int(address, 2)
            begin = start + rise + 1e-9 if selected else start
            measure(f"win_{address}_{output.lower()}_min",
                    f"MIN v({node}) FROM={begin:.12g} TO={falling:.12g}", "evaluate_window", "V",
                    address, output, low=(0.9 if selected else -0.1) * args.vdd)
            measure(f"win_{address}_{output.lower()}_max",
                    f"MAX v({node}) FROM={begin:.12g} TO={falling:.12g}", "evaluate_window", "V",
                    address, output, high=(1.1 if selected else 0.1) * args.vdd)
        # TD selects crossings in this cycle rather than UIC startup events.
        for edge, time, direction, slew in (("rise", start, "RISE", rise),
                                            ("fall", falling, "FALL", fall)):
            clock = f"clk_{cycle}_{edge}"
            measure(clock, f"WHEN v({nodes['PCLK']})={0.5*args.vdd:.12g} {direction}=1 TD={time-1e-9:.12g}",
                    "crossing", "s", address, "PCLK", low=time-1e-15, high=time+slew+1e-15)
            for family in (("DEC", "WL") if args.bench == "sizing" else ("DEC",)):
                output = family + str(int(address, 2))
                target_names = {}
                for percent in (10, 50, 90):
                    name = f"t_{address}_{output.lower()}_{edge}{percent}"
                    target_names[percent] = name
                    measure(name, f"WHEN v({outputs[output]})={percent*.01*args.vdd:.12g} "
                            f"{direction}=1 TD={time-1e-9:.12g}", "crossing", "s", address, output,
                            low=time, high=falling if edge == "rise" else start+20e-9)
                endpoint = 50 if edge == "rise" else 10
                measure(f"delay_{address}_{output.lower()}_{edge}",
                        f"PARAM='{target_names[endpoint]} - {clock}'",
                        "evaluation_delay" if edge == "rise" else "precharge_delay",
                        "s", address, output, low=0)
                expression = (f"{target_names[90]} - {target_names[10]}" if edge == "rise"
                              else f"{target_names[10]} - {target_names[90]}")
                measure(f"slew_{address}_{output.lower()}_{edge}", f"PARAM='{expression}'",
                        "output_slew", "s", address, output, low=0)
        for row in range(4):
            measure(f"internal_{address}_n{row}", f"FIND v(x1.N{row}) AT={sample_ns}n",
                    "dynamic_node_sample", "V", address, f"N{row}")
            # Each dynamic node drives an output NMOS whose source is grounded,
            # so its node voltage is exactly that device's external VGS here.
            output_nmos = (10, 15, 20, 25)[row]
            measure(f"vgs_peak_{address}_m{output_nmos}",
                    f"MAX v(x1.N{row}) FROM={start:.12g} TO={falling:.12g}",
                    "output_nmos_vgs_upper", "V", address, f"M{output_nmos}",
                    high=NFET_MODEL_VGS_MAX)
            if row != int(address, 2):
                measure(f"internal_min_{address}_n{row}",
                        f"MIN v(x1.N{row}) FROM={start:.12g} TO={falling:.12g}",
                        "dynamic_node_min", "V", address, f"N{row}")
        measure(f"footer_{address}", f"FIND v(x1.EVAL_GND) AT={sample_ns}n",
                "footer_voltage", "V", address, "EVAL_GND")
        for phase, begin, end in (("evaluate", start, falling+fall),
                                   ("precharge", falling+fall, start+20e-9)):
            measure(f"charge_{address}_{phase}", f"INTEG i(VDD_SRC) FROM={begin:.12g} TO={end:.12g}",
                    "supply_charge", "C", address)
            measure(f"energy_{address}_{phase}", f"PARAM='-{args.vdd:.12g} * charge_{address}_{phase}'",
                    "supply_energy", "J", address)
        measure(f"supply_{address}", f"FIND i(VDD_SRC) AT={sample_ns}n", "settled_supply_current", "A", address)

    for phase, sample_ns in enumerate(PRECHARGE_SAMPLES_NS):
        begin = 1e-9 if phase == 0 else (20 + 20*(phase-1))*1e-9 + rise + fall + 1e-9
        end = (10 + 20*phase)*1e-9
        for output, node in outputs.items():
            lines.append(f".meas tran pre_{sample_ns}_{output.lower()} FIND v({node}) AT={sample_ns}n")
            for kind, low, high in (("MIN", -0.1*args.vdd, None), ("MAX", None, 0.1*args.vdd)):
                measure(f"prewin_{phase}_{output.lower()}_{kind.lower()}",
                        f"{kind} v({node}) FROM={begin:.12g} TO={end:.12g}", "precharge_window", "V",
                        output=output, low=low, high=high)
        for row in range(4):
            measure(f"prenode_{phase}_n{row}", f"FIND v(x1.N{row}) AT={sample_ns}n",
                    "internal_precharge", "V", output=f"N{row}", low=.9*args.vdd, high=1.1*args.vdd)
    # Address transitions occur in precharge, so evaluation-only checks cannot
    # detect the inverter drain excursion. These NMOS sources are at VSS.
    for device, node in ((2, "A0B"), (4, "A1B")):
        measure(f"vds_peak_m{device}", f"MAX v(x1.{node}) FROM=0 TO=90n",
                "address_nmos_vds_upper", "V", output=f"M{device}", high=NFET_MODEL_VGS_MAX)
    for row, device in enumerate((10, 15, 20, 25)):
        measure(f"vgs_full_peak_m{device}", f"MAX v(x1.N{row}) FROM=0 TO=90n",
                "full_dynamic_node_vgs_upper", "V", output=f"M{device}", high=NFET_MODEL_VGS_MAX)
    return "\n".join([*lines, ".end", ""]), metrics


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def tool_version(tool: str) -> str:
    result = subprocess.run([tool, "--version"], capture_output=True, text=True, timeout=10)
    return (result.stdout + "\n" + result.stderr).strip()


def run(args: argparse.Namespace, temp: Path) -> int:
    schematic = ROOT / "sims/row_decoder" / (
        "tb_row_decoder.sch" if args.bench == "functional" else "tb_row_decoder_sizing.sch")
    pdk = Path(os.environ.get("PDK_ROOT", "/opt/pdks"))
    model_lib = pdk / "sky130A/libs.tech/combined/continuous/sky130.lib.spice"
    require(model_lib.is_file(), f"SKY130A library not found: {model_lib}")
    # Resolve the installation directory in Tcl, without a fixed prefix or version.
    paths = [pdk / "sky130A/libs.tech/xschem", ROOT / "cells/row_decoder", ROOT / "cells/wordline_driver"]
    literal_paths = ["{" + str(p).replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}") + "}" for p in paths]
    tcl = ('set XSCHEM_LIBRARY_PATH [join [list "$XSCHEM_SHAREDIR/xschem_library" '
           '"$XSCHEM_SHAREDIR/xschem_library/devices" ' + " ".join(literal_paths) + '] ":"]')
    xs = subprocess.run(["xschem", "-x", "-q", "-n", "--tcl", tcl, "-o", str(temp), str(schematic)],
                        cwd=ROOT, capture_output=True, text=True, timeout=45)
    xs_text = xs.stdout + "\n" + xs.stderr
    (temp / "xschem.log").write_text(xs_text)
    print(f"Xschem return code: {xs.returncode}")
    require(xs.returncode == 0 and not re.search(r"Error:|symbol not found|IS MISSING", xs_text, re.I),
            "Xschem structure/symbol failure; ngspice was not run:\n" + xs_text)
    generated = temp / (schematic.stem + ".spice")
    require(generated.is_file(), "Xschem did not generate a netlist")
    netlist = generated.read_text()
    require("IS MISSING" not in netlist.upper(), "Missing symbols in generated netlist")
    nodes, devices = inspect_netlist(netlist, args.bench == "sizing")
    netlist, rise, fall = prepare_stimulus(netlist, args)
    deck, metrics = make_deck(netlist, model_lib, nodes, args, rise, fall)
    # Small leaf circuits do not benefit from parallel BSIM evaluation. A control
    # run also permits both .meas and waveform export, unlike batch mode with -r.
    control = [".control", "set num_threads=1", "run"]
    if args.artifacts_dir:
        control.append("write row_decoder.raw")
    control.extend(["quit 0", ".endc", ".end"])
    deck = re.sub(r"(?im)^\.end\s*$", "\n".join(control), deck)
    deck_path = temp / "row_decoder_screen.spice"
    deck_path.write_text(deck)
    command = ["ngspice", "-n", "-b", str(deck_path)]
    ng = subprocess.run(command, cwd=temp, capture_output=True, text=True, timeout=90)
    ng_text = ng.stdout + "\n" + ng.stderr
    (temp / "ngspice.log").write_text(ng_text)
    print(f"ngspice return code: {ng.returncode}")
    values = {name.lower(): float(value) for name, value in MEASURE_RE.findall(ng_text)}
    outputs = [key for key in nodes if key != "PCLK"]
    expected = {f"eval_{a}_{out.lower()}" for a, _ in EVALUATION_SAMPLES for out in outputs}
    expected |= {f"pre_{ns}_{out.lower()}" for ns in PRECHARGE_SAMPLES_NS for out in outputs}
    expected |= {m["name"] for m in metrics}
    missing = sorted(expected - values.keys())
    require(ng.returncode == 0 and not missing and not re.search(r"Error:|failed!|simulation.*aborted", ng_text, re.I),
            f"ngspice failure or missing measurements {missing}:\n{ng_text}")
    require(all(math.isfinite(values[name]) for name in expected), "Nonfinite measurement")
    context = dict(bench=args.bench, candidate=args.candidate, corner=args.corner, vdd_v=args.vdd, temperature_c=args.temp_c)
    rows = []
    for phase, samples in (("evaluate", EVALUATION_SAMPLES), ("precharge", tuple(("x", ns) for ns in PRECHARGE_SAMPLES_NS))):
        for address, ns in samples:
            for output in outputs:
                high = phase == "evaluate" and int(output[-1]) == int(address, 2)
                name = f"eval_{address}_{output.lower()}" if phase == "evaluate" else f"pre_{ns}_{output.lower()}"
                voltage = values[name]
                lo, hi = logic_limits(high, args.vdd)
                rows.append({**context, "phase": phase, "address": address, "sample_time_ns": ns,
                             "output": output, "voltage_v": voltage, "expected_logic": int(high),
                             "criterion": f"{lo:g} <= V <= {hi:g}",
                             "result": "PASS" if passes_voltage(voltage, high, args.vdd) else "FAIL",
                             "xschem_returncode": xs.returncode, "xschem_structural_status": "PASS", "ngspice_returncode": ng.returncode})
    metric_rows = []
    for m in metrics:
        value, low, high = values[m["name"]], m["low"], m["high"]
        constrained = low is not None or high is not None
        passed = (low is None or value >= low) and (high is None or value <= high)
        metric_rows.append({**context, "category": m["category"], "address": m["address"], "output": m["output"],
                            "measurement": m["name"], "value": value, "unit": m["unit"],
                            "low_limit": "" if low is None else low, "high_limit": "" if high is None else high,
                            "result": (("PASS" if passed else "OUTSIDE_MODEL_RANGE")
                                       if m["category"] in MODEL_CATEGORIES else
                                       ("PASS" if passed else "FAIL")) if constrained else "MEASURED"})
    write_csv(args.output, rows)
    write_csv(args.metrics_output, metric_rows)
    sources = [schematic, ROOT/"cells/row_decoder/row_decoder.sch", ROOT/"cells/row_decoder/row_decoder.sym", Path(__file__), model_lib]
    if args.bench == "sizing":
        sources += [ROOT/"cells/wordline_driver/wl_driver.sch", ROOT/"cells/wordline_driver/wl_driver.sym"]
    manifest = {**context, "scope": "pre-layout, fixed four-address sequence, 1 ns settling guard",
                "method": args.method, "max_step_ps": args.max_step_ps, "num_threads": 1,
                "output_nmos_vgs_upper_screen_v": NFET_MODEL_VGS_MAX,
                "model_screen_scope": "Output-NMOS upper VGS per cycle and full transient, address-inverter NMOS upper VDS. Not the complete signed model domain.",
                "model_bound_source": "https://skywater-pdk.readthedocs.io/en/main/rules/device-details.html#v-nmos-fet",
                "node_mapping": nodes, "decoder_devices": devices,
                "decoder_channel_area_proxy_um2": sum(d["W"] * d["L"] for d in devices.values()),
                "clock_rise_ps": rise * 1e12, "clock_fall_ps": fall * 1e12,
                "wl_capacitance_ff": [spice_number(line.split()[3]) * 1e15
                                      for line in netlist.splitlines() if line.startswith("C_WL")],
                "overrides": {"wl_cap_ff": args.wl_cap_ff, "clock_slew_ps": args.clock_slew_ps, "address_slew_ps": args.address_slew_ps},
                "source_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                "model_hash_scope": "top-level library only, not recursive includes",
                "tool_versions": {tool: tool_version(tool) for tool in ("xschem", "ngspice")}}
    args.output.with_suffix(".json").write_text(json.dumps(manifest, indent=2) + "\n")
    passed = sum(row["result"] == "PASS" for row in rows)
    failures = [row for row in metric_rows if row["result"] == "FAIL"]
    model_exceeded = [row for row in metric_rows if row["result"] == "OUTSIDE_MODEL_RANGE"]
    print(f"Voltage samples: {passed} PASS, {len(rows)-passed} FAIL")
    print(f"Additional window/internal/timing checks: {sum(r['result']=='PASS' and r['category'] not in MODEL_CATEGORIES for r in metric_rows)} PASS, {len(failures)} FAIL")
    print(f"Output NMOS VGS upper model-envelope screen: {sum(r['category']=='output_nmos_vgs_upper' for r in model_exceeded)} OUTSIDE_MODEL_RANGE")
    print(f"Full-transient dynamic VGS/address inverter VDS screen: {sum(r['category']!='output_nmos_vgs_upper' for r in model_exceeded)} OUTSIDE_MODEL_RANGE")
    print(f"M8 W={devices['M8']['W']:g} um; decoder topology audit PASS")
    for category in ("evaluation_delay", "precharge_delay", "output_slew"):
        for family in (("DEC", "WL") if args.bench == "sizing" else ("DEC",)):
            vals = [r["value"]*1e12 for r in metric_rows if r["category"] == category and r["output"].startswith(family)]
            print(f"{family} {category}: {min(vals):.2f}..{max(vals):.2f} ps")
    for row in failures:
        print(f"FAIL: {row['measurement']} = {row['value']:.8g} {row['unit']}")
    if model_exceeded:
        peak = max(row["value"] for row in model_exceeded)
        print(f"MODEL_RANGE_REVIEW_REQUIRED: peak screened terminal voltage={peak:.6g} V exceeds {NFET_MODEL_VGS_MAX:g} V; "
              "logic PASS does not close model validity or device reliability")
    print(f"CSV: {args.output}\nMetrics: {args.metrics_output}\nManifest: {args.output.with_suffix('.json')}")
    return 0 if passed == len(rows) and not failures and not model_exceeded else 1


def main() -> int:
    args = parse_args()
    try:
        if args.artifacts_dir:
            args.artifacts_dir.mkdir(parents=True, exist_ok=True)
            return run(args, args.artifacts_dir.resolve())
        with tempfile.TemporaryDirectory(prefix="row-decoder-screen-") as name:
            return run(args, Path(name))
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        print(f"ERROR: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
