#!/usr/bin/env python3
"""Measure the pre-layout decoder's address and phase timing contract.

Fresh Xschem netlisting is the default. Disposable PWL decks preserve the leaf
schematics. Boundary failures are characterization results, never silent passes.
The internal address lead is not the external SRAM register setup time.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile

import numpy as np
import run_row_decoder_tt as screen
from plot_row_decoder_review import read_raw

ROOT = screen.ROOT
PROFILES = {"tt": ("tt", 1.8, 27), "slow": ("ss", 1.62, -40),
            "fast": ("ff", 1.8, 125), "ss_cold": ("ss", 1.8, -40)}
SCRIPT_TEXT = Path(__file__).read_text()
SCRIPT_HASH = hashlib.sha256(SCRIPT_TEXT.encode()).hexdigest()


def netlist_current(folder):
    pdk = Path(os.environ.get("PDK_ROOT", "/opt/pdks")) / "sky130A"
    paths = [pdk / "libs.tech/xschem", ROOT / "cells/row_decoder", ROOT / "cells/wordline_driver"]
    tcl = ('set XSCHEM_LIBRARY_PATH [join [list "$XSCHEM_SHAREDIR/xschem_library" '
           '"$XSCHEM_SHAREDIR/xschem_library/devices" ' +
           " ".join("{" + str(p) + "}" for p in paths) + '] ":"]')
    result = subprocess.run(["xschem", "-x", "-q", "-n", "--tcl", tcl,
                             "-o", str(folder), str(ROOT / "sims/row_decoder/tb_row_decoder_sizing.sch")],
                            cwd=ROOT, capture_output=True, text=True, timeout=60)
    log = result.stdout + result.stderr
    (folder / "xschem.log").write_text(log)
    screen.require(result.returncode == 0 and not re.search(r"Error:|symbol not found|IS MISSING", log, re.I),
                   "Xschem netlist/symbol failure: " + log)
    netlist = (folder / "tb_row_decoder_sizing.spice").read_text()
    screen.inspect_netlist(netlist, True)
    return netlist


def matrix(campaign, profiles):
    cases = []
    def add(**kw):
        label = "_".join(f"{k}{v:g}" if isinstance(v, (int, float)) else f"{k}{v}"
                         for k, v in kw.items())
        cases.append(dict(label=campaign+"_"+label, campaign=campaign, **kw))
    for profile in profiles:
        if campaign == "sizing":
            defaults = dict(footer_um=.5, stack_um=1, precharge_um=.42,
                            out_n_um=1, out_p_um=1, addr_n_um=.42, addr_p_um=.42)
            settings = [("B6", defaults)]
            seen = {tuple(defaults.items())}
            alternatives = [(f"footer{w:g}", dict(footer_um=w)) for w in (.42, .5, .75, 1, 1.25, 1.5, 2, 3)]
            alternatives += [(f"stack{w:g}", dict(stack_um=w)) for w in (.42, .5, .75, 1, 1.25, 1.5, 2)]
            alternatives += [(f"pre{w:g}", dict(precharge_um=w)) for w in (.42, .5, .75, 1, 1.5, 2)]
            alternatives += [(f"out{n:g}r{ratio:g}", dict(out_n_um=n, out_p_um=n*ratio))
                             for n in (.42, .75, 1) for ratio in (1, 1.5, 2, 3)]
            alternatives += [(f"addr{n:g}r{ratio:g}", dict(addr_n_um=n, addr_p_um=n*ratio))
                             for n in (.42, .75, 1) for ratio in (1, 1.5, 2)]
            for label, delta in alternatives:
                setting = {**defaults, **delta}
                key = tuple(setting.items())
                if key not in seen:
                    seen.add(key)
                    settings.append((label, setting))
            for candidate, setting in settings:
                for old, new in ((0, 3), (1, 2), (2, 1), (3, 0)):
                    add(profile=profile, old=old, new=new, candidate=candidate, **setting)
        elif campaign == "history":
            for load in (17.4, 50):
                for old in range(4):
                    for new in range(4):
                        for skew in ((-100, 0, 100) if old ^ new == 3 else (0,)):
                            add(profile=profile, old=old, new=new, skew_ps=skew, load_ff=load)
        elif campaign in {"timing", "timing_refine"}:
            leads = (1000, 250, 100, 50, 0, -100, -500) if campaign == "timing" else (200, 175, 150, 125, 100, 75, 50, 25, 0)
            for old in range(4):
                for new in range(4):
                    if old == new:
                        continue
                    for lead in leads:
                        add(profile=profile, old=old, new=new, lead_ps=lead)
        elif campaign in {"low_phase", "high_phase"}:
            for row in range(4):
                for duration in (.05, .1, .15, .2, .25, .3, .4, .5, .6, .75, 1, 1.5, 2, 5):
                    add(profile=profile, old=row, new=row,
                        **{("low_ns" if campaign == "low_phase" else "high_ns"): duration})
        elif campaign == "retention":
            for row in range(4):
                for hold in (10, 100, 1000):
                    add(profile=profile, old=row ^ 3, new=row, high_ns=hold,
                        step_ps=5 if hold <= 100 else 25)
        elif campaign == "edges":
            for old, new in ((0, 3), (1, 2), (2, 1), (3, 0)):
                for rise, fall in ((25, 250), (250, 25), (50, 1000), (1000, 50)):
                    add(profile=profile, old=old, new=new, rise_ps=rise, fall_ps=fall)
        elif campaign == "address_edges":
            for old, new in ((0, 3), (1, 2), (2, 1), (3, 0)):
                for slew in (25, 50, 100, 250, 1000):
                    add(profile=profile, old=old, new=new, address_ps=slew)
        elif campaign == "charge":
            for target in (1, 3):
                for charge in (0, .25, .5, 1, 2, 4, 8):
                    add(profile=profile, old=0, new=0, noise_node=target, charge_fc=charge)
        elif campaign == "negative":
            for old in range(4):
                for new in range(4):
                    if old != new:
                        add(profile=profile, old=old, new=new, lead_ps=-2000)
        else:
            raise ValueError("Unknown campaign " + campaign)
    return cases


def pwl(initial, transitions, stop):
    """Transitions are (start, end, target); overlapping ramps are rejected."""
    points = [(0.0, initial)]
    value = initial
    for start, end, target in sorted(transitions):
        screen.require(start >= points[-1][0]-1e-18 and end > start and end <= stop,
                       "Overlapping or out-of-bounds PWL transition")
        if target == value:
            continue
        start = max(start, points[-1][0])
        if start > points[-1][0]:
            points.append((start, value))
        points.append((end, target))
        value = target
    points.append((stop, value))
    return "PWL(" + " ".join(f"{t:.14g} {v:.14g}" for t, v in points) + ")"


def mos_instances(netlist):
    """Map every leaf MOS terminal, including all four unchanged WL buffers."""
    top = screen.logical_lines(netlist.split("* expanding", 1)[0])
    result = {}
    for line in top:
        parts = line.split()
        if not parts or not parts[0].lower().startswith("x") or parts[-1] not in {"row_decoder", "wl_driver"}:
            continue
        pins, body = screen.subcircuit(netlist, parts[-1])
        port_map = dict(zip(pins, parts[1:-1]))
        for mos in body:
            tok = mos.upper().split()
            if not tok or not tok[0].startswith("XM"):
                continue
            result[parts[0].lower() + "." + tok[0][1:].lower()] = [
                port_map.get(n, parts[0].lower() + "." + n.lower()).lower() for n in tok[1:5]]
    screen.require(len(result) == 41, "Expected 25 decoder and 16 WL-driver MOS")
    return result


def make_deck(netlist, case, model):
    families = {"footer_um": (8,), "stack_um": (6, 7, 12, 13, 17, 18, 22, 23),
                "precharge_um": (5, 11, 16, 21), "out_p_um": (9, 14, 19, 24),
                "out_n_um": (10, 15, 20, 25), "addr_p_um": (1, 3), "addr_n_um": (2, 4)}
    for family, devices4 in families.items():
        if family in case:
            for device in devices4:
                netlist, count = re.subn(rf"(?im)^(XM{device}\s+[^\n]*?\bW=)\S+",
                                         rf"\g<1>{case[family]:g}", netlist)
                screen.require(count == 1, f"Expected one XM{device} for {family}")
    nodes, devices = screen.inspect_netlist(netlist, True)
    pins, _ = screen.subcircuit(netlist, "row_decoder")
    top = next(line.split() for line in netlist.splitlines() if line.startswith("x1 "))
    ports = dict(zip(pins, top[1:-1]))
    corner, vdd, temp = PROFILES[case["profile"]]
    rise = case.get("rise_ps", 50)*1e-12
    fall = case.get("fall_ps", 50)*1e-12
    address_slew = case.get("address_ps", 50)*1e-12
    first_rise, first_fall = 5e-9, 10e-9
    second_rise = first_fall + case.get("low_ns", 10)*1e-9
    second_fall = second_rise + case.get("high_ns", 5)*1e-9
    stop = second_fall + 5e-9
    clock = []
    for center, slew, target in ((first_rise, rise, vdd), (first_fall, fall, 0),
                                (second_rise, rise, vdd), (second_fall, fall, 0)):
        clock.append((center-slew/2, center+slew/2, target))
    text = re.sub(r"(?im)^(VDD_SRC\s+\S+\s+\S+)\s+\S+\s*$", rf"\g<1> {vdd:.14g}", netlist)
    text = re.sub(r"(?im)^(VPCLK\s+\S+\s+\S+)\s+[^\n]+$",
                  lambda m: m[1]+" "+pwl(0, clock, stop), text)
    lead = case.get("lead_ps", 2000)*1e-12
    skew = case.get("skew_ps", 0)*1e-12
    address_end = second_rise - lead
    ends = [address_end-max(skew, 0), address_end+min(skew, 0)]
    for bit in (0, 1):
        old = (case["old"] >> bit) & 1
        new = (case["new"] >> bit) & 1
        transition = [(ends[bit]-address_slew, ends[bit], new*vdd)] if old != new else []
        if transition:
            screen.require(transition[0][0] >= first_fall+fall/2,
                           "Address transition overlaps the priming evaluation")
        text = re.sub(rf"(?im)^(VA{bit}\s+\S+\s+\S+)\s+[^\n]+$",
                      lambda m: m[1]+" "+pwl(old*vdd, transition, stop), text)
    load = case.get("load_ff", 17.4)*1e-15
    text = re.sub(r"(?im)^(C_WL\d\s+\S+\s+\S+)\s+\S+", rf"\g<1> {load:.14g}", text)
    if case.get("charge_fc", 0):
        # Withdraw Q over a 120 ps trapezoid (10 ps ramps, 100 ps plateau).
        # Integral is amplitude * 110 ps. Injection exists only in this deck.
        start = second_rise+1e-9
        amplitude = case["charge_fc"]*1e-15/110e-12
        injection = pwl(0, [(start, start+10e-12, amplitude),
                            (start+110e-12, start+120e-12, 0)], stop)
        text = re.sub(r"(?im)^(\.subckt row_decoder[^\n]*\n)",
                      lambda m: m[1]+f"INOISE N{case['noise_node']} VSS {injection}\n", text)
    terminals = mos_instances(text)
    needed = {v.lower() for v in nodes.values()} | {n for pins4 in terminals.values() for n in pins4}
    needed -= {"gnd", "0"}
    text = re.sub(r"(?im)^\.end\s*$", "", text)
    text += (f'\n.lib "{model}" {corner}\n.temp {temp:g}\n'
             f'.options method={case.get("method", "gear")}\n.save ' +
             " ".join(f"v({n})" for n in sorted(needed)) + " i(VDD_SRC) i(VPCLK) i(VA0) i(VA1)\n" +
             f'.tran 5p {stop:.14g} 0 {case.get("step_ps", 5)*1e-12:.14g} uic\n'
             '.control\nset num_threads=1\nrun\nwrite waveform.raw\nquit 0\n.endc\n.end\n')
    schedule = dict(first_rise=first_rise, first_fall=first_fall, second_rise=second_rise,
                    second_fall=second_fall, stop=stop, rise=rise, fall=fall,
                    address_ends=ends, ports=ports, vdd=vdd)
    return text, nodes, devices, terminals, schedule


def window(time, signal, start, end):
    """Include interpolated boundaries; reject empty/out-of-record intervals."""
    screen.require(time[0] <= start < end <= time[-1]+1e-16, "Invalid waveform window")
    mask = (time > start) & (time < end)
    return np.r_[np.interp(start, time, signal), signal[mask], np.interp(end, time, signal)]


def crossing(time, signal, start, end, level, rising=True):
    ids = np.where((time >= start) & (time <= end))[0]
    for left, right in zip(ids[:-1], ids[1:]):
        a, b = signal[left], signal[right]
        if (a < level <= b) if rising else (a > level >= b):
            return float(time[left] + (level-a)/(b-a)*(time[right]-time[left]))
    return None


def analyze(raw, case, nodes, devices, terminals, schedule):
    time = raw["time"]
    screen.require(np.isfinite(time).all() and np.all(np.diff(time) > 0), "Bad waveform timestamps")
    screen.require(time[-1] >= schedule["stop"]-1e-16, "Truncated transient")
    def trace(node):
        if node.lower() in {"0", "gnd"}:
            return np.zeros_like(time)
        v = raw[f"v({node.lower()})"]
        screen.require(np.isfinite(v).all(), "Nonfinite waveform " + node)
        return v
    vdd = schedule["vdd"]
    checks = []
    def check(phase, output, metric, value, low=None, high=None):
        passed = math.isfinite(value) and (low is None or value >= low) and (high is None or value <= high)
        checks.append(dict(case=case["label"], phase=phase, output=output, metric=metric,
                           value=float(value), low="" if low is None else low,
                           high="" if high is None else high, result="PASS" if passed else "FAIL"))
    delays = {"DEC": [], "WL": []}
    pre_delays = {"DEC": [], "WL": []}
    finaldelays = {"DEC": [], "WL": []}
    for tag, address, begin, end in (("prime", case["old"], schedule["first_rise"], schedule["first_fall"]),
                                    ("test", case["new"], schedule["second_rise"], schedule["second_fall"])):
        finish = end-schedule["fall"]/2
        for out, node in nodes.items():
            if out == "PCLK":
                continue
            expected_high = int(out[-1]) == address
            y = trace(node)
            region = window(time, y, begin, finish)
            check(tag, out, "upper_excursion_v", region.max(), high=1.1*vdd)
            check(tag, out, "lower_excursion_v", region.min(), low=-.1*vdd)
            level = float(np.interp(finish, time, y))
            lo, hi = screen.logic_limits(expected_high, vdd)
            check(tag, out, "end_level_v", level, lo, hi)
            if expected_high:
                if finish > begin+1e-9:
                    check(tag, out, "settled_min_v", window(time, y, begin+1e-9, finish).min(), low=.9*vdd)
                t50 = crossing(time, y, begin, finish, .5*vdd)
                t90 = crossing(time, y, begin, finish, .9*vdd)
                if tag == "test":
                    if t50 is not None:
                        delays[out[:2] if out.startswith("WL") else "DEC"].append((t50-begin)*1e12)
                    if t90 is not None:
                        finaldelays[out[:2] if out.startswith("WL") else "DEC"].append((t90-begin)*1e12)
            else:
                check(tag, out, "unselected_max_v", region.max(), high=.1*vdd)
    pre_end = schedule["second_rise"]-schedule["rise"]/2
    pre_start = schedule["first_fall"]
    for out, node in nodes.items():
        if out == "PCLK":
            continue
        y = trace(node)
        check("recovery", out, "end_level_v", np.interp(pre_end, time, y), -.1*vdd, .1*vdd)
        if pre_end > pre_start+1e-9:
            check("recovery", out, "settled_max_v", window(time, y, pre_start+1e-9, pre_end).max(), high=.1*vdd)
        if int(out[-1]) == case["old"]:
            t10 = crossing(time, y, pre_start, pre_end, .1*vdd, False)
            if t10 is not None:
                pre_delays["WL" if out.startswith("WL") else "DEC"].append((t10-pre_start)*1e12)
    dynamic_min = []
    for row in range(4):
        y = trace(f"x1.n{row}")
        check("recovery", f"N{row}", "end_level_v", np.interp(pre_end, time, y), .9*vdd, 1.1*vdd)
        if row != case["new"]:
            minimum = float(window(time, y, schedule["second_rise"], schedule["second_fall"]-schedule["fall"]/2).min())
            dynamic_min.append(minimum)
    for out, node in nodes.items():
        if out != "PCLK":
            region = window(time, trace(node), schedule["second_fall"]+1e-9, schedule["stop"])
            check("final_precharge", out, "settled_max_v", region.max(), high=.1*vdd)
            check("final_precharge", out, "settled_min_v", region.min(), low=-.1*vdd)
    for row in range(4):
        check("final_precharge", f"N{row}", "end_level_v",
              trace(f"x1.n{row}")[-1], .9*vdd, 1.1*vdd)
    extrema = []
    for name, pins4 in terminals.items():
        d, g, s, b = [trace(n) for n in pins4]
        for voltage, y in (("VGS", g-s), ("VGD", g-d), ("VDS", d-s), ("VBS", b-s)):
            lo, hi = int(y.argmin()), int(y.argmax())
            extrema.append(dict(case=case["label"], device=name, voltage=voltage,
                                min_v=float(y[lo]), max_v=float(y[hi]),
                                min_time_ns=float(time[lo]*1e9), max_time_ns=float(time[hi]*1e9)))
    upper = max(trace(f"x1.n{i}").max() for i in range(4))
    worst = max((r for r in extrema if r["voltage"] != "VBS"),
                key=lambda r: max(abs(r["min_v"]), abs(r["max_v"])))
    magnitude = max(abs(worst["min_v"]), abs(worst["max_v"]))
    bad = sum(r["result"] == "FAIL" for r in checks)
    settling_bad = sum(r["result"] == "FAIL" and r["metric"] in {"settled_min_v", "settled_max_v"} for r in checks)
    testwrong = [r for r in checks if r["phase"] == "test" and r["metric"] == "unselected_max_v" and r["result"] == "FAIL"]
    if case["campaign"] == "negative":
        status = "EXPECTED_FAILURE" if testwrong else "NEGATIVE_CONTROL_NOT_DETECTED"
    elif bad:
        status = ("REJECTED_TIMING" if case["campaign"] in {"timing", "timing_refine", "low_phase", "high_phase"}
                  else "REJECTED_PERTURBATION" if case["campaign"] == "charge"
                  else "REJECTED_SIZING" if case["campaign"] == "sizing"
                  else "SETTLING_SCREEN_FAIL" if bad == settling_bad else "FAIL")
    else:
        status = "PASS"
    result = dict(case=case["label"], campaign=case["campaign"], profile=case["profile"],
                  old_address=case["old"], new_address=case["new"],
                  lead_ps=case.get("lead_ps", 2000), skew_ps=case.get("skew_ps", 0),
                  low_ns=case.get("low_ns", 10), high_ns=case.get("high_ns", 5),
                  load_ff=case.get("load_ff", 17.4), rise_ps=case.get("rise_ps", 50),
                  fall_ps=case.get("fall_ps", 50), max_step_ps=case.get("step_ps", 5),
                  address_slew_ps=case.get("address_ps", 50),
                  noise_node=case.get("noise_node", ""), charge_fc=case.get("charge_fc", 0),
                  method=case.get("method", "gear"), result=status,
                  candidate=case.get("candidate", "B6"),
                  footer_um=devices["M8"]["W"], stack_um=devices["M6"]["W"],
                  precharge_um=devices["M5"]["W"], out_n_um=devices["M10"]["W"], out_p_um=devices["M9"]["W"],
                  addr_n_um=devices["M2"]["W"], addr_p_um=devices["M1"]["W"],
                  channel_area_proxy_um2=sum(d["W"]*d["L"] for d in devices.values()),
                  corner=PROFILES[case["profile"]][0], vdd_v=vdd,
                  temperature_c=PROFILES[case["profile"]][2],
                  check_pass=len(checks)-bad, check_fail=bad,
                  settling_check_fail=settling_bad, other_check_fail=bad-settling_bad,
                  wrong_row_peak_v=max(r["value"] for r in checks if r["phase"] == "test" and r["metric"] == "unselected_max_v"),
                  unselected_dynamic_min_v=min(dynamic_min), output_vgs_peak_v=float(upper),
                  terminal_magnitude_max_v=magnitude, terminal_magnitude_device=worst["device"],
                  terminal_magnitude_voltage=worst["voltage"],
                  model_upper_result="PASS" if upper <= 1.95 else "OUTSIDE_MODEL_RANGE",
                  magnitude_result="PASS" if magnitude <= 1.95 else "OUTSIDE_SCREEN")
    for family in ("DEC", "WL"):
        result[family.lower()+"_delay50_ps"] = max(delays[family]) if delays[family] else ""
        result[family.lower()+"_delay90_ps"] = max(finaldelays[family]) if finaldelays[family] else ""
        result[family.lower()+"_precharge10_ps"] = max(pre_delays[family]) if pre_delays[family] else ""
    # Energy delivered by each ideal source; returned charge may produce negative
    # input-source contributions. This is not upstream-driver dissipation.
    for name, port in (("vdd_src", "VDD"), ("vpclk", "PCLK"), ("va0", "A0"), ("va1", "A1")):
        power = -trace(schedule["ports"][port])*raw[f"i({name})"]
        mask = (time >= schedule["first_fall"]) & (time <= schedule["second_fall"])
        result[name+"_cycle_energy_fj"] = float(np.trapz(power[mask], time[mask])*1e15)
    return result, checks, extrema


def simulate(case, netlist, folder, keep):
    target = folder / case["label"]
    target.mkdir(parents=True, exist_ok=True)
    model = Path(os.environ.get("PDK_ROOT", "/opt/pdks")) / "sky130A/libs.tech/combined/continuous/sky130.lib.spice"
    deck, nodes, devices, terminals, schedule = make_deck(netlist, case, model)
    (target / "case.spice").write_text(deck)
    process = subprocess.run(["ngspice", "-n", "-b", str(target / "case.spice")], cwd=target,
                             capture_output=True, text=True, timeout=180)
    log = process.stdout + process.stderr
    (target / "ngspice.log").write_text(log)
    screen.require(process.returncode == 0 and not re.search(r"Error:|failed!|aborted", log, re.I),
                   "ngspice failure: " + str(target))
    raw = read_raw(target / "waveform.raw")
    result = analyze(raw, case, nodes, devices, terminals, schedule)
    if not keep:
        (target / "waveform.raw").unlink()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", choices=("suite", "sizing", "history", "timing", "timing_refine", "negative", "low_phase", "high_phase", "retention", "edges", "address_edges", "charge"), required=True)
    parser.add_argument("--profiles", nargs="+", choices=tuple(PROFILES), default=["tt", "slow", "fast"])
    parser.add_argument("--netlist", type=Path, help="Explicit archived input; default freshly netlists the current schematic")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--artifacts-dir", type=Path)
    parser.add_argument("--workers", type=int, choices=(1, 2, 4), default=2)
    args = parser.parse_args()
    screen.require(not args.output_dir.exists(), "Use a new output directory to preserve archived evidence")
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "executed_script.py").write_text(SCRIPT_TEXT)
    with tempfile.TemporaryDirectory(prefix="decoder-contract-") as temp:
        folder = args.artifacts_dir.resolve() if args.artifacts_dir else Path(temp)
        folder.mkdir(parents=True, exist_ok=True)
        netlist = args.netlist.read_text() if args.netlist else netlist_current(folder)
        _, devices = screen.inspect_netlist(netlist, True)
        (args.output_dir / "input_netlist.spice").write_text(netlist)
        campaigns = ("timing", "negative", "low_phase", "high_phase", "retention", "edges", "address_edges", "charge") if args.campaign == "suite" else (args.campaign,)
        cases = [case for campaign in campaigns for case in matrix(campaign, args.profiles)]
        model = Path(os.environ.get("PDK_ROOT", "/opt/pdks")) / "sky130A/libs.tech/combined/continuous/sky130.lib.spice"
        manifest = dict(campaign=args.campaign, stage="pre-layout", cases=cases, profiles=PROFILES,
                        source="explicit archived netlist" if args.netlist else "fresh Xschem netlist",
                        netlist_sha256=hashlib.sha256(netlist.encode()).hexdigest(), decoder_devices=devices,
                        script_sha256=SCRIPT_HASH,
                        source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                       (ROOT / "cells/row_decoder/row_decoder.sch", ROOT / "cells/row_decoder/row_decoder.sym",
                                        ROOT / "cells/wordline_driver/wl_driver.sch", ROOT / "cells/wordline_driver/wl_driver.sym",
                                        ROOT / "sims/row_decoder/tb_row_decoder_sizing.sch")},
                        helper_sha256={Path(p).name: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                                       for p in (screen.__file__, Path(__file__).with_name("plot_row_decoder_review.py"))},
                        model_sha256=hashlib.sha256(model.read_bytes()).hexdigest(), model_hash_scope="top-level library only",
                        tools={"ngspice": screen.tool_version("ngspice"), "xschem": screen.tool_version("xschem")},
                        note="Experimental 10%/90% logic criteria; signed external VGS/VGD/VDS/VBS retained. Magnitude screen is not full signed model-domain or reliability closure. Internal address lead, not SRAM register setup; no Fmax claim.")
        (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
        runs = []
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for index, run in enumerate(pool.map(lambda c: simulate(c, netlist, folder, args.artifacts_dir is not None), cases), 1):
                runs.append(run)
                if index % 24 == 0 or index == len(cases):
                    print(f"{args.campaign}: {index}/{len(cases)} cases completed", flush=True)
        for name, index in (("summary", 0), ("checks", 1), ("terminals", 2)):
            rows = [run[0] for run in runs] if index == 0 else [row for run in runs for row in run[index]]
            screen.write_csv(args.output_dir / (name+".csv"), rows)
        counts = {status: sum(run[0]["result"] == status for run in runs) for status in sorted({r[0]["result"] for r in runs})}
        print(json.dumps(counts), flush=True)
        upper_bad = sum(r[0]["model_upper_result"] != "PASS" or r[0]["magnitude_result"] != "PASS" for r in runs)
        print(f"Terminal magnitude or output upper-screen findings: {upper_bad}", flush=True)
    # Characterized rejected boundary points and detected negative controls are
    # expected. Legal-history/retention/edge failures remain hard failures.
    return int(any(r[0]["result"] in {"FAIL", "SETTLING_SCREEN_FAIL", "NEGATIVE_CONTROL_NOT_DETECTED"}
                   or (r[0]["campaign"] in {"history", "retention", "edges", "address_edges"} and
                       (r[0]["model_upper_result"] != "PASS" or r[0]["magnitude_result"] != "PASS")) for r in runs))


if __name__ == "__main__":
    raise SystemExit(main())
