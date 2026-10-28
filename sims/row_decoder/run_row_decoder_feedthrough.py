#!/usr/bin/env python3
"""Reproduce feedthrough experiments on an explicitly selected decoder netlist.

Width and separated-clock overrides are diagnostic changes to disposable decks.
The source schematic is never edited. Each case records its actual device widths.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile

import numpy as np
import run_row_decoder_tt as screen
from plot_row_decoder_review import read_raw

PRECHARGE = (5, 11, 16, 21)
OUTPUT_INVERTERS = (9, 10, 14, 15, 19, 20, 24, 25)
EXECUTED_SCRIPT_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
SCREEN_SHA256 = hashlib.sha256(Path(screen.__file__).read_bytes()).hexdigest()


def modify(netlist, pre_width=None, out_width=None, isolated=None, address_width=None):
    """Audit the original hierarchy, then apply identified diagnostic overrides."""
    screen.inspect_netlist(netlist, True)
    for members, width in ((PRECHARGE, pre_width), (OUTPUT_INVERTERS, out_width),
                           ((1, 2, 3, 4), address_width)):
        if width is not None:
            for device in members:
                netlist, count = re.subn(rf"(?im)^(XM{device}\s+[^\n]*?\bW=)\S+",
                                         rf"\g<1>{width:g}", netlist)
                screen.require(count == 1, f"Expected one XM{device}")
    nodes, devices = screen.inspect_netlist(netlist, True)
    if isolated:
        targets = PRECHARGE if isolated == "precharge_slow" else (8,)
        for device in targets:
            netlist, count = re.subn(rf"(?im)^(XM{device}\s+\S+\s+)PCLK\b",
                                     r"\g<1>DIAG_CLK", netlist)
            screen.require(count == 1, f"Cannot separate XM{device} clock")
            devices[f"M{device}"]["nodes"][1] = "DIAG_CLK"
        pulse = "0" if isolated == "footer_off" else "PULSE(0 1.8 10n 250p 250p 10n 20n)"
        netlist = re.sub(r"(?im)^\.subckt row_decoder[^\n]*\n",
                         lambda m: m[0] + f"VDIAG DIAG_CLK VSS {pulse}\n", netlist)
    return netlist, nodes, devices


def matrix(campaign):
    if campaign == "refine":
        return [dict(label=f"{corner}_{temp}_{method}1", corner=corner, vdd=1.8,
                     temp=temp, slew=25, step=1, method=method)
                for corner, temp in (("ss", -40), ("ff", 125)) for method in ("gear", "trap")]
    if campaign == "address":
        return [dict(label=f"addr{width:g}", pre=.42, address=width,
                     corner="ss", vdd=1.8, temp=-40, slew=50)
                for width in (.42, .5, .75, 1, 1.5)]
    if campaign == "explore":
        cases = [dict(label=f"B5_clock{slew:g}", slew=slew)
                 for slew in (25, 50, 100, 250, 500, 1000)]
        cases += [dict(label=label, pre=p, out=o, slew=50) for label, p, o in
                  (("pre042", .42, 1), ("pre050", .5, 1), ("pre075", .75, 1),
                   ("out150", 1, 1.5), ("out200", 1, 2), ("pre042_out150", .42, 1.5))]
        cases += [dict(label=key, isolated=key, slew=50)
                  for key in ("precharge_slow", "footer_slow", "footer_off")]
        return cases
    if campaign == "qualify":
        return [dict(label=f"{corner}_{vdd:g}_{temp:g}_{slew:g}", corner=corner,
                     vdd=vdd, temp=temp, slew=slew)
                for corner in ("tt", "ss", "ff") for vdd in (1.62, 1.8)
                for temp in (-40, 27, 125) for slew in (25, 50, 250)]
    return [dict(label=f"{method}{step:g}", method=method, step=step, slew=50)
            for method, step in (("gear", 10), ("gear", 5), ("trap", 5))]


def simulate(case, netlist, root, keep_raw):
    label = case["label"]
    folder = root / label
    folder.mkdir(parents=True, exist_ok=True)
    netlist, nodes, devices = modify(netlist, case.get("pre"), case.get("out"),
                                     case.get("isolated"), case.get("address"))
    args = argparse.Namespace(bench="sizing", candidate=label, corner=case.get("corner", "tt"),
                             vdd=case.get("vdd", 1.8), temp_c=case.get("temp", 27),
                             method=case.get("method", "gear"), max_step_ps=case.get("step", 5),
                             clock_slew_ps=case["slew"], address_slew_ps=None, wl_cap_ff=17.4)
    netlist, rise, fall = screen.prepare_stimulus(netlist, args)
    model = Path("/opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice")
    deck, metrics = screen.make_deck(netlist, model, nodes, args, rise, fall)
    if case.get("isolated") == "footer_off":
        omitted = {m["name"] for m in metrics if m["category"] in
                   {"evaluation_delay", "precharge_delay", "output_slew"}
                   or (m["category"] == "crossing" and m["output"] != "PCLK")}
        deck = "\n".join(line for line in deck.splitlines()
                         if not any(line.startswith(f".meas tran {name} ") for name in omitted)) + "\n"
        metrics = [m for m in metrics if m["name"] not in omitted]
    pins, _ = screen.subcircuit(netlist, "row_decoder")
    instance = next(line.split() for line in netlist.splitlines() if line.startswith("x1 "))
    ports = dict(zip(pins, instance[1:-1]))

    def node_vector(node):
        return "0" if node == "VSS" else ports.get(node, "x1." + node).lower()

    needed = {n.lower() for n in nodes.values()} | {node_vector(n) for d in devices.values() for n in d["nodes"]}
    needed.discard("0")
    deck = deck.replace(".tran ", ".save " + " ".join(f"v({n})" for n in sorted(needed)) +
                        " i(VDD_SRC) i(VPCLK) i(VA0) i(VA1)\n.tran ", 1)
    deck = re.sub(r"(?im)^\.end\s*$",
                  ".control\nset num_threads=1\nrun\nwrite waveform.raw\nquit 0\n.endc\n.end", deck)
    (folder / "case.spice").write_text(deck)
    ng = subprocess.run(["ngspice", "-n", "-b", str(folder / "case.spice")],
                        cwd=folder, capture_output=True, text=True, timeout=120)
    log = ng.stdout + ng.stderr
    (folder / "ngspice.log").write_text(log)
    values = {name.lower(): float(value) for name, value in screen.MEASURE_RE.findall(log)}
    required = {m["name"] for m in metrics}
    outputs = [n for n in nodes if n != "PCLK"]
    required |= {f"eval_{a}_{o.lower()}" for a, _ in screen.EVALUATION_SAMPLES for o in outputs}
    required |= {f"pre_{ns}_{o.lower()}" for ns in screen.PRECHARGE_SAMPLES_NS for o in outputs}
    screen.require(ng.returncode == 0 and not required-values.keys()
                   and not re.search(r"Error:|failed!|simulation.*aborted", log, re.I),
                   f"{label}: ngspice failure or incomplete measurements; see {folder}")
    screen.require(all(math.isfinite(values[k]) for k in required), f"{label}: nonfinite value")
    voltage_pass = []
    for a, _ in screen.EVALUATION_SAMPLES:
        voltage_pass += [screen.passes_voltage(values[f"eval_{a}_{o.lower()}"],
                                             int(a, 2) == int(o[-1]), args.vdd) for o in outputs]
    for ns in screen.PRECHARGE_SAMPLES_NS:
        voltage_pass += [screen.passes_voltage(values[f"pre_{ns}_{o.lower()}"], False, args.vdd)
                        for o in outputs]
    checks = [m for m in metrics if m["category"] not in screen.MODEL_CATEGORIES
              and (m["low"] is not None or m["high"] is not None)]
    failed = [m["name"] for m in checks if (m["low"] is not None and values[m["name"]] < m["low"])
              or (m["high"] is not None and values[m["name"]] > m["high"])]
    peaks = [values[m["name"]] for m in metrics if m["category"] == "output_nmos_vgs_upper"]
    raw = read_raw(folder / "waveform.raw")
    time = raw["time"]

    def trace(node):
        v = node_vector(node)
        return np.zeros_like(time) if v == "0" else raw[f"v({v})"]

    terminals = []
    for name, dev in devices.items():
        d, g, s, b = map(trace, dev["nodes"])
        for voltage, arr in (("VGS", g-s), ("VGD", g-d), ("VDS", d-s), ("VBS", b-s)):
            terminals.append(dict(case=label, device=name, voltage=voltage,
                                  min_v=float(arr.min()), max_v=float(arr.max()),
                                  min_time_ns=float(time[int(arr.argmin())]*1e9),
                                  max_time_ns=float(time[int(arr.argmax())]*1e9)))
    node_peaks = [dict(case=label, node=f"N{i}", peak_v=float(trace(f"N{i}").max()),
                       peak_time_ns=float(time[int(trace(f"N{i}").argmax())]*1e9)) for i in range(4)]
    result = dict(case=label, corner=args.corner, vdd_v=args.vdd, temperature_c=args.temp_c,
                  clock_slew_ps=case["slew"], method=args.method, max_step_ps=args.max_step_ps,
                  precharge_width_um=devices["M5"]["W"], output_width_um=devices["M9"]["W"],
                  address_width_um=devices["M1"]["W"],
                  footer_width_um=devices["M8"]["W"], voltage_pass=sum(voltage_pass),
                  voltage_fail=72-sum(voltage_pass), window_check_fail=len(failed),
                  output_vgs_evaluate_max_v=max(peaks), output_vgs_full_transient_max_v=max(p["peak_v"] for p in node_peaks),
                  output_vgs_outside=sum(v > screen.NFET_MODEL_VGS_MAX for v in peaks),
                  vdd_cycle_energy_mean_fj=sum(values[m["name"]]*1e15 for m in metrics if m["category"] == "supply_energy")/4,
                  intentional_isolation=case.get("isolated", ""))
    stresses = [max(abs(r["min_v"]), abs(r["max_v"])) for r in terminals
                if r["voltage"] in ("VGS", "VGD", "VDS")]
    result["terminal_magnitude_max_v"] = max(stresses)
    result["terminal_magnitude_above_1p95_count"] = sum(v > 1.95 for v in stresses)
    for category in ("evaluation_delay", "precharge_delay"):
        for family in ("DEC", "WL"):
            delays = [values[m["name"]]*1e12 for m in metrics
                      if m["category"] == category and m["output"].startswith(family)]
            result[f"{family.lower()}_{category}_max_ps"] = max(delays) if delays else ""
    context = dict(case=label, corner=args.corner, vdd_v=args.vdd, temperature_c=args.temp_c)
    detail = [dict(**context, **{k: m[k] for k in ("name", "category", "output", "low", "high")}, value=values[m["name"]])
              for m in metrics]
    if not keep_raw:
        (folder / "waveform.raw").unlink()
    print(json.dumps(result), flush=True)
    return result, terminals, node_peaks, detail


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", choices=("explore", "address", "qualify", "numeric", "refine"), default="explore")
    parser.add_argument("--netlist", type=Path, default=Path(__file__).parent/"results/b5_review_tt_netlist.spice")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--artifacts-dir", type=Path)
    parser.add_argument("--workers", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    netlist = args.netlist.read_text()
    cases = matrix(args.campaign)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir/"input_netlist.spice").write_text(netlist)
    with tempfile.TemporaryDirectory(prefix="decoder-feedthrough-") as tmp:
        folder = args.artifacts_dir.resolve() if args.artifacts_dir else Path(tmp)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            runs = list(pool.map(lambda c: simulate(c, netlist, folder, args.artifacts_dir is not None), cases))
        for name, index in (("summary", 0), ("terminals", 1), ("node_peaks", 2), ("metrics", 3)):
            rows = [r[index] for r in runs] if index == 0 else [v for r in runs for v in r[index]]
            screen.write_csv(args.output_dir/(name+".csv"), rows)
        manifest = dict(campaign=args.campaign, netlist=str(args.netlist),
                        netlist_sha256=hashlib.sha256(netlist.encode()).hexdigest(),
                        script_sha256=EXECUTED_SCRIPT_SHA256, cases=cases,
                        input_devices=screen.inspect_netlist(netlist, True)[1],
                        helper_sha256={str(Path(screen.__file__)): SCREEN_SHA256},
                        model_sha256=hashlib.sha256(Path("/opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice").read_bytes()).hexdigest(),
                        model_hash_scope="Top-level library only, not recursive includes",
                        tools={"ngspice": screen.tool_version("ngspice")},
                        note="Simulation-only overrides. |VGS|/|VGD|/|VDS| <= 1.95 V is a magnitude diagnostic, not the full signed published model envelope or reliability sign-off.")
        (args.output_dir/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    failed = [r[0] for r in runs if not r[0]["intentional_isolation"] and
              (r[0]["voltage_fail"] or r[0]["window_check_fail"] or r[0]["output_vgs_outside"]
               or r[0]["output_vgs_full_transient_max_v"] > screen.NFET_MODEL_VGS_MAX)]
    magnitude = [r[0] for r in runs if not r[0]["intentional_isolation"]
                 and r[0]["terminal_magnitude_above_1p95_count"]]
    failed = list({r["case"]: r for r in [*failed, *magnitude]}.values())
    print(f"Cases: {len(runs)}; unclosed output-VGS/logic screens: {len(failed)}")
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
