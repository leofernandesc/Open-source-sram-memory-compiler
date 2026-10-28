#!/usr/bin/env python3
"""Run matched decoder contract cases against schematic and Magic R-C PEX.

The PEX contains flattened Magic instance names and distributed node names, so
this runner reuses the existing contract stimulus/checks while adapting only
the netlist inspection and internal dynamic-node aliases. The Xschem source is
never modified.
"""
from __future__ import annotations

import argparse
import importlib.util
from collections import Counter
import csv
from datetime import datetime
import hashlib
import json
import math
import re
import shutil
import sys
from pathlib import Path

np = None
contract = None
screen = None
ROOT = Path(__file__).resolve().parents[2]
PEX_PATH = ROOT / "layout/row_decoder/pex/row_decoder_pex.spice"
ORIGINAL_INSPECT = None
ORIGINAL_MOS_INSTANCES = None
ORIGINAL_READ_RAW = None
ORIGINAL_MAKE_DECK = None
ORIGINAL_ANALYZE = None
SOURCE_NETLIST = ""
SOURCE_NODES = {}
SOURCE_DEVICES = {}
PEX_DYNAMIC_NODES = {}
PEX_DYNAMIC_SEGMENTS = {}
PEX_COUNTS = {}


def load_simulation_dependencies() -> None:
    """Load heavy simulation modules only after the PEX static audit passes."""
    global np, contract, screen
    global ORIGINAL_INSPECT, ORIGINAL_MOS_INSTANCES, ORIGINAL_READ_RAW
    global ORIGINAL_MAKE_DECK, ORIGINAL_ANALYZE
    import numpy as numpy_module
    import run_row_decoder_contract as contract_module
    import run_row_decoder_tt as screen_module
    np, contract, screen = numpy_module, contract_module, screen_module
    ORIGINAL_INSPECT = screen.inspect_netlist
    ORIGINAL_MOS_INSTANCES = contract.mos_instances
    ORIGINAL_READ_RAW = contract.read_raw
    ORIGINAL_MAKE_DECK = contract.make_deck
    ORIGINAL_ANALYZE = contract.analyze


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def subckt_match(text: str, name: str):
    match = re.search(
        rf"(?ims)^\.subckt\s+{re.escape(name)}\s+([^\n]+)\n(.*?)^\.ends(?:\s+{re.escape(name)})?[^\n]*",
        text,
    )
    require(match is not None, f"Missing .subckt {name}")
    return match


def pex_body_is_present(netlist: str) -> bool:
    match = re.search(r"(?ims)^\.subckt\s+row_decoder\s+[^\n]+\n(.*?)^\.ends\b", netlist)
    if not match:
        return False
    lines = screen.logical_lines(match[1])
    return (any(re.match(r"^R\d+\s", line, re.I) for line in lines)
            and any(re.match(r"^C\d+\s", line, re.I) for line in lines)
            and any(re.match(r"^X\d+\s", line, re.I) for line in lines))


def negative_capacitor_lines(text: str) -> list[str]:
    value_pattern = re.compile(
        r"^C\S+\s+\S+\s+\S+\s+"
        r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)[a-zA-Z]*\b",
        re.I,
    )
    negative = []
    for line in text.splitlines():
        stripped = line.strip()
        if not re.match(r"^C\S+\s", stripped, re.I):
            continue
        match = value_pattern.match(stripped)
        require(match is not None, f"Cannot parse extracted capacitor value: {line}")
        if float(match.group(1)) < 0:
            negative.append(stripped)
    return negative


def pex_components(text: str):
    pins_match = subckt_match(text, "row_decoder_flat")
    pins = pins_match[1].split()
    lines = screen.logical_lines(pins_match[2])
    mos = [line for line in lines
           if re.match(r"^X\d+\s", line, re.I)
           and re.search(r"\bsky130_fd_pr__(?:n|p)fet_01v8\b", line, re.I)]
    resistors = [line for line in lines if re.match(r"^R\d+\s", line, re.I)]
    capacitors = [line for line in lines if re.match(r"^C\d+\s", line, re.I)]
    require(len(mos) == 29, f"PEX has {len(mos)} MOS devices; expected 29")
    require(resistors and capacitors,
            f"PEX needs R and C; found {len(resistors)} R and {len(capacitors)} C")
    negative_caps = negative_capacitor_lines("\n".join(capacitors))
    require(not negative_caps,
            "Refusing electrical simulation: PEX contains negative capacitor values: "
            + "; ".join(negative_caps))

    dynamic_segments = {i: set() for i in range(4)}
    for line in lines:
        parts = line.split()
        if not parts:
            continue
        if parts[0][0].upper() in {"R", "C"}:
            candidates = parts[1:3]
        elif re.fullmatch(r"X\d+", parts[0], re.I) and len(parts) >= 6:
            candidates = parts[1:5]
        else:
            continue
        for node in candidates:
            # Newer Magic releases may keep a named dynamic net as a single
            # node (for example N0) when extresist does not split that net.
            # Older extractions can still expose distributed N0.<segment>
            # nodes, so retain both forms for probing and aliasing.
            match = re.fullmatch(r"N([0-3])(?:\.([A-Za-z0-9_]+))?", node, re.I)
            if match:
                dynamic_segments[int(match[1])].add(node)

    dynamic_gate_nodes = {}
    for row in range(4):
        candidates = []
        for line in mos:
            parts = line.split()
            if "pfet_01v8" not in parts[5].lower():
                continue
            if not any(re.match(rf"DEC{row}(?:\.|$)", node, re.I)
                       for node in (parts[1], parts[3])):
                continue
            gate = parts[2]
            if re.match(rf"N{row}(?:\.|$)", gate, re.I):
                candidates.append(gate)
        require(len(candidates) == 1,
                f"Could not uniquely map decoder row {row} dynamic node to its output PFET gate")
        dynamic_gate_nodes[row] = candidates[0]

    counts = dict(mos=len(mos), resistors=len(resistors), capacitors=len(capacitors))
    return pins, lines, counts, dynamic_gate_nodes, dynamic_segments


def inject_pex(source: str, pex_text: str):
    source_match = subckt_match(source, "row_decoder")
    pex_match = subckt_match(pex_text, "row_decoder_flat")
    source_pins = source_match[1].split()
    pex_pins, _, counts, dynamic_gates, dynamic_segments = pex_components(pex_text)
    require([pin.upper() for pin in source_pins] == [pin.upper() for pin in pex_pins],
            f"PEX pin order differs from Xschem: {pex_pins} != {source_pins}")
    expected_devices = mos_signatures(source_match[2])
    extracted_devices = mos_signatures(pex_match[2])
    require(expected_devices == extracted_devices,
            "PEX device sizing/connectivity differs from the schematic; "
            f"missing={list((expected_devices - extracted_devices).elements())}; "
            f"unexpected={list((extracted_devices - expected_devices).elements())}")
    replacement = (f".subckt row_decoder {' '.join(source_pins)}\n"
                   + pex_match[2].rstrip() + "\n.ends row_decoder")
    result = source[:source_match.start()] + replacement + source[source_match.end():]
    require(pex_body_is_present(result), "R-C PEX was not inserted into the decoder testbench")
    return result, counts, dynamic_gates, dynamic_segments


def mos_signatures(body: str) -> Counter:
    """Compare MOS topology and dimensions across Magic's distributed aliases.

    Drain/source ordering may reverse during extraction. Instance identifiers
    change too, so compare labeled nets, gate, bulk, model and sizing instead.
    This rejects a cached PEX from a different sizing even when pins match.
    """
    signatures = Counter()
    for line in screen.logical_lines(body):
        tokens = line.split()
        if len(tokens) < 6 or not re.fullmatch(
                r"sky130_fd_pr__(?:n|p)fet_01v8", tokens[5], re.I):
            continue
        parameters = {key.lower(): value for key, value in
                      re.findall(r"\b(\w+)\s*=\s*([^\s]+)", line)}
        require("w" in parameters and "l" in parameters,
                f"MOS dimensions missing: {line}")
        dimension = tuple(round(float(parameters[key]), 6) for key in ("w", "l"))
        multiplicity = float(parameters.get("m", parameters.get("mult", "1")))
        fingers = float(parameters.get("nf", "1"))
        nodes = [node.split(".", 1)[0].upper() for node in tokens[1:5]]
        signature = (tokens[5].upper(), tuple(sorted((nodes[0], nodes[2]))),
                     nodes[1], nodes[3], dimension, multiplicity, fingers)
        signatures[signature] += 1
    require(sum(signatures.values()) == 29, "Expected 29 decoder MOS signatures")
    return signatures


def inspect_netlist(netlist: str, loaded: bool):
    if not pex_body_is_present(netlist):
        return ORIGINAL_INSPECT(netlist, loaded)
    pins, body = screen.subcircuit(netlist, "row_decoder")
    require([pin.upper() for pin in pins] == [pin.upper() for pin in SOURCE_DEVICES["__pins__"]],
            "PEX subcircuit interface changed after insertion")
    mos = [line for line in body if re.match(r"^X\d+\s", line, re.I)
           and re.search(r"\bsky130_fd_pr__(?:n|p)fet_01v8\b", line, re.I)]
    resistors = [line for line in body if re.match(r"^R\d+\s", line, re.I)]
    capacitors = [line for line in body if re.match(r"^C\d+\s", line, re.I)]
    require(len(mos) == 29 and resistors and capacitors,
            "Inserted decoder subcircuit is not a complete 29-MOS R-C PEX")
    return SOURCE_NODES, {k: v for k, v in SOURCE_DEVICES.items() if k != "__pins__"}


def mos_instances(netlist: str, decoder_count: int = 25):
    if not pex_body_is_present(netlist):
        return ORIGINAL_MOS_INSTANCES(netlist, decoder_count)
    top = screen.logical_lines(netlist.split("* expanding", 1)[0])
    result = {}
    for line in top:
        parts = line.split()
        if not parts or not parts[0].lower().startswith("x"):
            continue
        subckt = parts[-1].lower()
        if subckt not in {"row_decoder", "wl_driver"}:
            continue
        pins, body = screen.subcircuit(netlist, subckt)
        port_map = {pin.upper(): node.lower() for pin, node in zip(pins, parts[1:-1])}
        for instance in body:
            tok = instance.split()
            if len(tok) < 6 or not re.search(r"\bsky130_fd_pr__(?:n|p)fet_01v8\b", tok[5], re.I):
                continue
            is_pex_mos = subckt == "row_decoder" and re.fullmatch(r"X\d+", tok[0], re.I)
            is_driver_mos = subckt == "wl_driver" and tok[0].upper().startswith("XM")
            if not (is_pex_mos or is_driver_mos):
                continue
            terminals = []
            for node in tok[1:5]:
                terminals.append(port_map.get(node.upper(), f"{parts[0].lower()}.{node.lower()}"))
            result[parts[0].lower() + "." + tok[0][1:].lower()] = terminals
    screen.require(len(result) == decoder_count + 16,
                   f"Unexpected decoder/WL-driver MOS count in PEX deck: {len(result)}")
    return result


def make_deck(netlist, case, model):
    deck, nodes, devices, terminals, schedule = ORIGINAL_MAKE_DECK(netlist, case, model)
    if pex_body_is_present(netlist):
        probes = sorted({f"v(x1.{node.lower()})"
                         for segments in PEX_DYNAMIC_SEGMENTS.values() for node in segments}
                        | {f"v({node.lower()})" for node in schedule["ports"].values()
                           if node.lower() not in {"0", "gnd"}})
        require(probes, "No distributed dynamic-node segments found in PEX")
        save_line, count = re.subn(r"(?im)^\.save\s+([^\n]+)$",
                                  lambda m: ".save " + m[1] + " " + " ".join(probes), deck, count=1)
        require(count == 1, "Could not add distributed dynamic-node probes to the PEX deck")
        deck = save_line
    return deck, nodes, devices, terminals, schedule


def read_raw(path):
    raw = ORIGINAL_READ_RAW(path)
    for row, node in PEX_DYNAMIC_NODES.items():
        physical = f"v(x1.{node.lower()})"
        if physical in raw:
            raw[f"v(x1.n{row})"] = raw[physical]
    return raw


def analyze(raw, case, nodes, devices, terminals, schedule):
    result, checks, extrema = ORIGINAL_ANALYZE(raw, case, nodes, devices, terminals, schedule)
    time = raw["time"]
    vdd = schedule["vdd"]
    for family in ("DEC", "WL"):
        output = f"{family}{case['new']}"
        node = nodes[output]
        signal = raw[f"v({node.lower()})"]
        rise_10 = contract.crossing(time, signal, schedule["second_rise"],
                                    schedule["second_fall"] - schedule["fall"] / 2,
                                    .1 * vdd, True)
        rise_90 = contract.crossing(time, signal, schedule["second_rise"],
                                    schedule["second_fall"] - schedule["fall"] / 2,
                                    .9 * vdd, True)
        fall_90 = contract.crossing(time, signal, schedule["second_fall"],
                                    schedule["stop"], .9 * vdd, False)
        fall_10 = contract.crossing(time, signal, schedule["second_fall"],
                                    schedule["stop"], .1 * vdd, False)
        result[family.lower() + "_selected_rise_slew10_90_ps"] = (
            (rise_90 - rise_10) * 1e12 if rise_10 is not None and rise_90 is not None else "")
        result[family.lower() + "_selected_fall_slew90_10_ps"] = (
            (fall_10 - fall_90) * 1e12 if fall_90 is not None and fall_10 is not None else "")

    if any("." in node and f"v(x1.{node.lower()})" in raw
           for segments in PEX_DYNAMIC_SEGMENTS.values() for node in segments):
        pre_end = schedule["second_rise"] - schedule["rise"] / 2
        final_time = min(schedule["stop"], time[-1])
        recovery_values = []
        final_values = []
        unselected_minima = []
        for row, segments in PEX_DYNAMIC_SEGMENTS.items():
            for node in segments:
                key = f"v(x1.{node.lower()})"
                require(key in raw, f"Missing distributed dynamic-node probe: {key}")
                signal = raw[key]
                recovery = float(np.interp(pre_end, time, signal))
                final = float(np.interp(final_time, time, signal))
                recovery_values.append(recovery)
                final_values.append(final)
                if row != case["new"]:
                    mask = (time >= schedule["second_rise"])
                    mask &= time <= schedule["second_fall"] - schedule["fall"] / 2
                    if mask.any():
                        unselected_minima.append(float(signal[mask].min()))
                for phase, value in (("pex_recovery", recovery), ("pex_final_precharge", final)):
                    passed = .9 * vdd <= value <= 1.1 * vdd
                    checks.append(dict(case=case["label"], phase=phase, output=f"N{row}.{node}",
                                       metric="dynamic_segment_level_v", value=value,
                                       low=.9*vdd, high=1.1*vdd,
                                       result="PASS" if passed else "FAIL",
                                       settling_allowance_only=False))
        extra_failures = sum(check["result"] == "FAIL" and check["phase"].startswith("pex_")
                             for check in checks)
        result["check_pass"] += sum(check["phase"].startswith("pex_") and check["result"] == "PASS"
                                    for check in checks)
        result["check_fail"] += extra_failures
        result["other_check_fail"] += extra_failures
        if extra_failures:
            result["result"] = "FAIL"
        result["pex_dynamic_segment_count"] = sum(len(v) for v in PEX_DYNAMIC_SEGMENTS.values())
        result["pex_dynamic_recovery_min_v"] = min(recovery_values) if recovery_values else ""
        result["pex_dynamic_recovery_max_v"] = max(recovery_values) if recovery_values else ""
        result["pex_dynamic_final_min_v"] = min(final_values) if final_values else ""
        result["pex_dynamic_final_max_v"] = max(final_values) if final_values else ""
        result["pex_unselected_dynamic_min_v"] = min(unselected_minima) if unselected_minima else ""
    return result, checks, extrema


def case_matrix():
    cases = []
    by_profile = {
        "tt": ((0, 0), (0, 1), (1, 0), (0, 2), (2, 0), (0, 3), (3, 0), (1, 2), (2, 1)),
        "slow": ((0, 3), (3, 0), (1, 2), (2, 1)),
    }
    for profile, pairs in by_profile.items():
        for old, new in pairs:
            cases.append(dict(
                label=f"{profile}_{old:02b}_to_{new:02b}", campaign="history",
                profile=profile, old=old, new=new, skew_ps=0, load_ff=17.4,
                rise_ps=50, fall_ps=50, address_ps=50, step_ps=5, method="gear",
            ))
    return cases


def run_campaign(netlist_path: Path, case_path: Path, output: Path, artifacts: Path,
                 workers: int, stage: str, timeout_s: int):
    sys.argv = [str(contract.__file__), "--campaign", "selected", "--case-file", str(case_path),
                "--netlist", str(netlist_path), "--output-dir", str(output),
                "--artifacts-dir", str(artifacts), "--workers", str(workers),
                "--timeout-s", str(timeout_s)]
    status = contract.main()
    manifest_path = output / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text())
        manifest["stage"] = stage
        manifest["pex_sha256"] = (hashlib.sha256(PEX_PATH.read_bytes()).hexdigest()
                                  if stage.startswith("post-layout") else "")
        manifest["pex_components"] = PEX_COUNTS if stage.startswith("post-layout") else {}
        manifest["pex_dynamic_gate_nodes"] = PEX_DYNAMIC_NODES if stage.startswith("post-layout") else {}
        manifest["pex_dynamic_segment_nodes"] = {str(k): sorted(v) for k, v in PEX_DYNAMIC_SEGMENTS.items()} \
            if stage.startswith("post-layout") else {}
        manifest["matched_case_setup"] = dict(load_ff=17.4,
                                              max_step_ps=manifest["cases"][0]["step_ps"], method="gear",
                                              clock_rise_ps=50, clock_fall_ps=50,
                                              address_slew_ps=50)
        manifest["post_layout_scope"] = (
            "Decoder only: Magic distributed R-C network replaces the decoder subcircuit; "
            "four unchanged pre-layout WL buffers and their 17.4 fF loads remain in the testbench."
        )
        manifest["ngspice_timeout_s"] = timeout_s
        manifest["screen_definitions"] = {
            "model_upper_result": "Experimental upper bound on gate-side dynamic-node voltage: 1.95 V; not signed model-domain clearance.",
            "magnitude_result": "Experimental maximum absolute VGS/VGD/VDS: 1.95 V. VBS extrema are reported separately.",
        }
        manifest["energy_definition"] = (
            "Net energy delivered by each ideal source from first_fall to second_fall "
            "(falling-edge midpoints), trapezoidal integration with interpolated endpoints. "
            "Includes returned energy; not upstream-driver dissipation. "
            "Requires separate timestep convergence assessment."
        )
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return status


def compare_runs(root: Path):
    paths = {name: root / name / "summary.csv" for name in ("baseline", "pex")}
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        print("Comparison not produced; missing completed summary for: " + ", ".join(missing))
        return []
    with paths["baseline"].open(newline="") as stream:
        baseline = {row["case"]: row for row in csv.DictReader(stream)}
    with paths["pex"].open(newline="") as stream:
        pex = {row["case"]: row for row in csv.DictReader(stream)}
    require(set(baseline) == set(pex), "Baseline and PEX campaigns do not contain the same cases")
    fields = ("dec_delay50_ps", "dec_delay90_ps", "dec_precharge10_ps",
              "wl_delay50_ps", "wl_delay90_ps", "wl_precharge10_ps",
              "dec_selected_rise_slew10_90_ps", "dec_selected_fall_slew90_10_ps",
              "wl_selected_rise_slew10_90_ps", "wl_selected_fall_slew90_10_ps",
              "wrong_row_peak_v", "unselected_dynamic_min_v", "output_vgs_peak_v",
              "terminal_magnitude_max_v", "check_fail",
              "vdd_src_cycle_energy_fj", "vpclk_cycle_energy_fj",
              "va0_cycle_energy_fj", "va1_cycle_energy_fj")
    rows = []
    for case in sorted(baseline):
        row = dict(case=case, baseline_result=baseline[case]["result"], pex_result=pex[case]["result"])
        for stage, entries in (("baseline", baseline), ("pex", pex)):
            for criterion in ("model_upper_result", "magnitude_result"):
                row[f"{stage}_{criterion}"] = entries[case][criterion]
            row[f"{stage}_accepted"] = all(entries[case][criterion] == "PASS"
                                             for criterion in ("result", "model_upper_result", "magnitude_result"))
        for field in fields:
            a, b = baseline[case].get(field, ""), pex[case].get(field, "")
            row["baseline_" + field] = a
            row["pex_" + field] = b
            try:
                row["delta_" + field] = float(b) - float(a)
            except (TypeError, ValueError):
                row["delta_" + field] = ""
        for field in ("pex_dynamic_segment_count", "pex_dynamic_recovery_min_v",
                      "pex_dynamic_recovery_max_v", "pex_dynamic_final_min_v",
                      "pex_dynamic_final_max_v", "pex_unselected_dynamic_min_v"):
            row["pex_" + field] = pex[case].get(field, "")
        rows.append(row)
    with (root / "comparison.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def require_current_pex():
    path = ROOT / 'layout/row_decoder/layout_provenance.py'
    spec = importlib.util.spec_from_file_location('decoder_layout_provenance', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.require_current_pex()



def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path,
                        default=ROOT / "sims/row_decoder/results" /
                        ("row_decoder_pex_" + datetime.now().strftime("%Y%m%d_%H%M%S")))
    parser.add_argument("--workers", type=int, choices=(1, 2, 4), default=2)
    parser.add_argument("--timeout-s", type=int, default=180,
                        help="Maximum seconds per ngspice case (default: 180)")
    parser.add_argument("--limit", type=int,
                        help="Run the first N matched cases, for a small smoke check.")
    parser.add_argument("--cases", nargs="+", choices=[case["label"] for case in case_matrix()],
                        help="Select named cases for targeted numerical rechecks.")
    parser.add_argument("--max-step-ps", type=float, default=5,
                        help="Maximum transient timestep in ps (default: 5).")
    args = parser.parse_args()
    require_current_pex()
    require(args.timeout_s > 0, "--timeout-s must be a positive integer")
    require(math.isfinite(args.max_step_ps) and args.max_step_ps > 0,
            "--max-step-ps must be finite and positive")
    pex_text = PEX_PATH.read_text(encoding="utf-8")
    negative_caps = negative_capacitor_lines(pex_text)
    require(not negative_caps,
            "Refusing electrical simulation: PEX contains negative capacitor values: "
            + "; ".join(negative_caps))
    metadata_path = PEX_PATH.with_name("extraction_manifest.json")
    require(metadata_path.is_file(), "Missing extraction manifest; regenerate with build_layout.py --extract")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    require(metadata["pex_sha256"] == hashlib.sha256(PEX_PATH.read_bytes()).hexdigest(),
            "PEX hash differs from extraction manifest; regenerate the extraction")
    schematic = ROOT / "cells/row_decoder/row_decoder.sch"
    require(metadata.get("source_text_sha256") == hashlib.sha256(
                schematic.read_text(encoding="utf-8").encode()).hexdigest(),
            "Schematic changed after PEX extraction; regenerate the extraction")
    require(not metadata["negative_capacitors"] and len(metadata["resistance_networks"]) == 22,
            "Extraction manifest is not qualified for all 22 resistance networks")
    load_simulation_dependencies()
    root = args.output_root.resolve()
    require(not root.exists() or not any(root.iterdir()), f"Output directory is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(metadata_path, root / metadata_path.name)
    source_dir = root / "netlist_source"
    source_dir.mkdir()
    baseline = contract.netlist_current(source_dir)
    global SOURCE_NETLIST, SOURCE_NODES, SOURCE_DEVICES
    SOURCE_NETLIST = baseline
    SOURCE_NODES, SOURCE_DEVICES = ORIGINAL_INSPECT(baseline, True)
    SOURCE_DEVICES["__pins__"] = screen.subcircuit(baseline, "row_decoder")[0]
    pex_netlist, counts, gate_nodes, dynamic_segments = inject_pex(baseline, pex_text)
    global PEX_COUNTS, PEX_DYNAMIC_NODES, PEX_DYNAMIC_SEGMENTS
    PEX_COUNTS, PEX_DYNAMIC_NODES, PEX_DYNAMIC_SEGMENTS = counts, gate_nodes, dynamic_segments
    baseline_path = root / "baseline_input_netlist.spice"
    pex_netlist_path = root / "pex_input_netlist.spice"
    baseline_path.write_text(baseline, encoding="utf-8")
    pex_netlist_path.write_text(pex_netlist, encoding="utf-8")
    case_path = root / "cases.json"
    cases = case_matrix()
    if args.cases:
        require(len(args.cases) == len(set(args.cases)), "--cases must not contain duplicates")
        cases = [case for case in cases if case["label"] in args.cases]
    for case in cases:
        case["step_ps"] = args.max_step_ps
    if args.limit is not None:
        require(1 <= args.limit <= len(cases), f"--limit must be between 1 and {len(cases)}")
        cases = cases[:args.limit]
    case_path.write_text(json.dumps(cases, indent=2) + "\n", encoding="utf-8")
    shutil.copyfile(__file__, root / Path(__file__).name)
    (root / "pex.sha256").write_text(hashlib.sha256(PEX_PATH.read_bytes()).hexdigest() + "  "
                                     + PEX_PATH.name + "\n", encoding="utf-8")

    screen.inspect_netlist = inspect_netlist
    contract.mos_instances = mos_instances
    contract.make_deck = make_deck
    contract.read_raw = read_raw
    contract.analyze = analyze
    baseline_status = run_campaign(baseline_path, case_path, root / "baseline",
                                   root / "artifacts/baseline", args.workers,
                                   "pre-layout Xschem baseline", args.timeout_s)
    pex_status = run_campaign(pex_netlist_path, case_path, root / "pex",
                              root / "artifacts/pex", args.workers,
                              "post-layout extracted R-C PEX", args.timeout_s)
    rows = compare_runs(root)
    print(f"Matched cases: {len(rows)}; baseline exit={baseline_status}; PEX exit={pex_status}")
    print(f"PEX components: {counts['mos']} MOS, {counts['resistors']} R, {counts['capacitors']} C")
    print(f"Distributed dynamic nodes: {sum(len(v) for v in dynamic_segments.values())} across four rows")
    if rows:
        print(f"Comparison: {root / 'comparison.csv'}")
    else:
        print("No paired comparison was written because one campaign did not complete.")
    return 0 if baseline_status == 0 and pex_status == 0 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
