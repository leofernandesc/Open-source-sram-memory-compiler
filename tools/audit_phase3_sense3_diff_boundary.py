#!/usr/bin/env python3
"""Audit the column-3 differential replay boundaries using existing TT evidence."""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import re

import numpy as np

from analyze_phase3_data3_tt import load
from phase3_rc_probe import rc_node_map
from phase3_sense3_diff_advance import ADVANCE_NS, HISTORY, reconstruct
from phase3_sense3_precondition import validate_authorization
from run_phase3_sense3_isolation import BUILD, PEX, REFERENCE, ResistanceGraph, pinned, sha256


SAMPLERS = ("rc8210", "rc8222")
# In the raw extraction each line is write_driver_3.BL or BLB with a route suffix.
PAIRS = (
    ("row3_access", "rc8202", "rc8216", "X1592/X663"),
    ("row0_access", "rc8203", "rc8217", "X1570/X631"),
    ("row1_access", "rc8204", "rc8218", "X637/X1416"),
    ("row2_access", "rc8205", "rc8219", "X1511/X581"),
    ("array_junction", "rc8199", "rc8211", "n0"),
    ("coupled_junction", "rc8200", "rc8212", "n1"),
    ("write_junction", "rc8201", "rc8213", "n2"),
    ("write_pmos", "rc8206", "rc8215", "X1619/X442"),
    ("write_nmos", "rc8207", "rc8214", "X323/X1081"),
    ("precharge", "rc8208", "rc8220", "X1352/X1645"),
    ("equalizer", "rc8209", "rc8221", "X374"),
    ("sampler", *SAMPLERS, "X235/X521"),
)


def extract_cards(text):
    return {parts[0]: parts[1:] for line in text.splitlines()
            if re.match(r"^[XRC]\d+\s", line) and (parts := line.split(" ;", 1)[0].split())}


def column_graph(original, bound, names):
    graph = ResistanceGraph(bound)
    groups = tuple(graph.group(node) for node in SAMPLERS)
    if any({row[i] for row in PAIRS} != group for i, group in enumerate(groups, 1)) or groups[0] & groups[1]:
        raise ValueError("Candidate inventory no longer matches the extracted column")
    column = groups[0] | groups[1]
    devices = {}
    for name, fields in bound.items():
        count = 4 if name.startswith("X") else 2
        if column.intersection(fields[:count]):
            raw = original[name]
            if [names[n] for n in raw[:count]] + raw[count:] != fields:
                raise ValueError(f"Binding changed extracted card {name}")
            devices[name] = fields
    return graph, groups, devices


def capacitor_role(u, v, groups, physical):
    left, right = groups
    if (u in left and v in right) or (u in right and v in left):
        return "BLxBLB"
    if {u, v} <= left | right:
        return "same_bitline"
    external = physical[v if u in left | right else u]
    if external.split(".")[0] in {"VDD", "VSS"}:
        return external.split(".")[0]
    for substring, role in (("precharge_drive", "PRECH"), ("sense_drive", "SCLK"),
                            ("write_drive", "write_control"), (".WL.", "WL")):
        if substring in external:
            return role
    return "other"


def evaluate(time, bl, blb, vdd, case):
    start, stop = case["low_ns"], case["capture_ns"]
    points = np.unique(np.r_[time, time - ADVANCE_NS, start, stop, case["tail20_ns"], case["high_ns"],
                             case["early_input_window_ns"]])
    points = points[(points >= start) & (points <= stop)]
    a, b, supply = (np.interp(points, time, signal) for signal in (bl, blb, vdd))
    target = np.interp(points + ADVANCE_NS, time, blb) - np.interp(points + ADVANCE_NS, time, bl)
    result = reconstruct(a, b, target, supply)

    def at(event):
        i = np.searchsorted(points, event)
        return {key: float(value[i]) for key, value in result.items()}

    return {
        "cycle": case["cycle"], "reference_ns": points, **result,
        "summary": {
            "cycle": case["cycle"], "reference_tail20_ns": case["tail20_ns"],
            "tail20": at(case["tail20_ns"]),
            "observed_min_v": [float(min(a)), float(min(b))],
            "observed_max_v": [float(max(a)), float(max(b))],
            "peak_observed_b_above_vdd_v": float(max(b - supply)),
            "peak_target_v": [float(max(result[key])) for key in ("bl_required_v", "blb_required_v")],
            "cm_range_v": [float(min(result["common_v"])), float(max(result["common_v"]))],
            "hard_splice_b_jump_v": {
                label: (at(when)["delta_advanced_v"] - at(when)["delta_control_v"]) * polarity / 2
                for label, when, polarity in (("enable", start, 1), ("disable", case["high_ns"], -1),
                                             ("late_enable", case["early_input_window_ns"][0], 1))
            },
        },
    }


def write_csv(path, rows):
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def audit(output):
    pex = PEX / "extracted_rc.spice"
    source, receipt, trace = load(REFERENCE, True)
    raw = pinned(pex, source["pex_sha256"]).read_text()
    binding = REFERENCE / "binding.spice"
    names = rc_node_map(raw)
    physical = {value: key for key, value in names.items()}
    bound = extract_cards(binding.read_text())
    graph, groups, devices = column_graph(extract_cards(raw), bound, names)
    control_gate = validate_authorization(HISTORY)
    historical = json.loads((HISTORY / "manifest.json").read_text())
    if historical["reference_waveform_sha256"] != receipt["waveform_sha256"]:
        raise ValueError("Reduced control and physical replay reference no longer match")
    slice_cards = extract_cards((HISTORY / "control/slice.spice").read_text())
    inventory = []
    for key, fields in devices.items():
        kind = key[0]
        nodes = fields[:4] if kind == "X" else fields[:2]
        if key in slice_cards and fields != slice_cards[key]:
            raise ValueError(f"Retained card differs from the PEX for {key}")
        inventory.append({
            "card": key, "kind": kind, "role": capacitor_role(*nodes, groups, physical) if kind == "C" else "",
            "nodes_dgsb_or_ab": " ".join(nodes), "physical_nodes": " ".join(physical[n] for n in nodes),
            "parameters": " ".join(fields[len(nodes):]), "retained_card_in_slice": key in slice_cards,
        })
    candidates, curves = [], []
    times = np.asarray(trace.times)
    vdd = np.asarray([row[10] for row in trace.rows])  # read_waveform public columns
    for role, a, b, devices_ref in PAIRS:
        measured = a in trace.cols and b in trace.cols
        paths = [graph.shortest(p, {q}) for p, q in zip((a, b), SAMPLERS, strict=True)]
        records = []
        if measured:
            for case in historical["criteria"]["cases"]:
                waves = ([row[trace.cols[n]] for row in trace.rows] for n in (a, b))
                values = evaluate(times, *waves, vdd, case)
                records.append(values.pop("summary"))
                cycle = values.pop("cycle")
                curves.extend(dict(pair=role, cycle=cycle, **dict(zip(values, row, strict=True)))
                              for row in zip(*values.values(), strict=True))
        candidates.append({
            "role": role, "nodes": [a, b], "physical_nodes": [physical[a], physical[b]],
            "device_or_junction": devices_ref, "shortest_resistor_path_to_sampler": paths,
            "waveform": "OBSERVED" if measured else "NOT_OBSERVED", "measurements": records,
            "voltage_replay_disposition": "DIRECT_CLAMP_REPLACES_SAMPLER_INPUT" if role == "sampler" else
            "NO_CURRENT_OR_IMPEDANCE_EQUIVALENT" if measured else "NO_NODE_LEVEL_TRAJECTORY",
        })
    write_csv(output / "column_cards.csv", inventory)
    write_csv(output / "observed_and_calculated.csv", curves)
    caps = Counter()
    for row in inventory:
        if row["kind"] == "C":
            caps[row["role"]] += float(row["parameters"].removesuffix("f"))
    result = {
        "verdict": "NO_DEFENSIBLE_BOUNDARY", "scope": "Existing voltage replay in column 3",
        "spice_runs": 0, "contrast": "NOT_RUN", "differential_sufficiency": "INCONCLUSIVE",
        "advance_ps": ADVANCE_NS * 1000, "candidates": candidates,
        "card_counts": dict(Counter(row["kind"] for row in inventory)),
        "cap_ff_by_group": dict(caps), "conditions": source["conditions"],
        "sha256": {str(path.relative_to(BUILD.parent.parent)): sha256(path) for path in
                   (pex, binding, REFERENCE / "probes.json", REFERENCE / "waveform.dat",
                    HISTORY / "manifest.json", HISTORY / "control/slice.spice", control_gate)},
    }
    with (output / "manifest.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(f"{result['verdict']} · {len(candidates)} pares · "
          f"{sum(c['waveform']=='OBSERVED' for c in candidates)} observados")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    audit(parser.parse_args().output)
