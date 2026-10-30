#!/usr/bin/env python3
"""Summarize completed decoder experiments without concealing rejected points."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import run_row_decoder_tt as screen


def eligible(row):
    return row["result"] == "PASS" and row["model_upper_result"] == "PASS" and row["magnitude_result"] == "PASS"


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", type=Path, nargs="+")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = []
    for directory in args.directories:
        manifest = json.loads((directory / "manifest.json").read_text())
        measured = rows(directory / "summary.csv")
        screen.require(manifest.get("complete", True) and len(measured) == len(manifest["cases"])
                       and {r["case"] for r in measured} == {r["label"] for r in manifest["cases"]},
                       "Incomplete campaign: " + str(directory))
        data.extend(measured)
    grouped = {}
    for row in data:
        key = (row["campaign"], row["profile"], row["load_ff"])
        grouped.setdefault(key, []).append(row)
    totals = []
    boundaries = []
    for (campaign, profile, load), group in sorted(grouped.items()):
        totals.append(dict(campaign=campaign, profile=profile, load_ff=load, cases=len(group),
                           logic_pass=sum(r["result"] == "PASS" for r in group),
                           combined_screen_pass=sum(eligible(r) for r in group),
                           model_upper_outside=sum(r["model_upper_result"] != "PASS" for r in group),
                           magnitude_outside=sum(r["magnitude_result"] != "PASS" for r in group),
                           wrong_row_peak_v=max(float(r["wrong_row_peak_v"]) for r in group),
                           terminal_magnitude_max_v=max(float(r["terminal_magnitude_max_v"]) for r in group)))
        if campaign in {"timing", "timing_refine", "low_phase", "high_phase"}:
            parameter = {"timing": "lead_ps", "timing_refine": "lead_ps", "low_phase": "low_ns", "high_phase": "high_ns"}[campaign]
            grid = {}
            for r in group:
                grid.setdefault(float(r[parameter]), []).append(r)
            for value, points in sorted(grid.items()):
                boundaries.append(dict(campaign=campaign, profile=profile, load_ff=load,
                                       parameter=parameter, value=value, cases=len(points),
                                       logic_pass=sum(r["result"] == "PASS" for r in points),
                                       combined_screen_pass=sum(eligible(r) for r in points)))
    screen.write_csv(args.output_dir / "campaign_totals.csv", totals)
    if boundaries:
        screen.write_csv(args.output_dir / "boundary_grid.csv", boundaries)
    # Only compared dimensions are included. Area is a channel proxy, and ideal
    # source energy is stimulus dependent; neither is physical sign-off.
    sizes = {}
    for row in data:
        if row["campaign"] == "sizing":
            sizes.setdefault(row["candidate"], []).append(row)
    candidates = []
    for name, group in sizes.items():
        candidate = dict(candidate=name, cases=len(group), eligible=all(eligible(r) for r in group),
                         wl_delay90_max_ps=max(float(r["wl_delay90_ps"]) for r in group if r["wl_delay90_ps"]),
                         wl_precharge10_max_ps=max(float(r["wl_precharge10_ps"]) for r in group if r["wl_precharge10_ps"]),
                         vdd_cycle_energy_mean_fj=sum(float(r["vdd_src_cycle_energy_fj"]) for r in group)/len(group),
                         channel_area_proxy_um2=float(group[0]["channel_area_proxy_um2"]),
                         terminal_magnitude_max_v=max(float(r["terminal_magnitude_max_v"]) for r in group))
        candidate.update({k: group[0][k] for k in ("footer_um", "stack_um", "precharge_um", "out_n_um", "out_p_um", "addr_n_um", "addr_p_um")})
        candidates.append(candidate)
    dimensions = ("wl_delay90_max_ps", "wl_precharge10_max_ps", "vdd_cycle_energy_mean_fj", "channel_area_proxy_um2")
    for candidate in candidates:
        candidate["nominal_nondominated"] = candidate["eligible"] and not any(
            other["eligible"] and all(other[k] <= candidate[k] for k in dimensions)
            and any(other[k] < candidate[k] for k in dimensions) for other in candidates)
    if candidates:
        screen.write_csv(args.output_dir / "sizing_candidates.csv", candidates)
    robust = {}
    for row in data:
        if row['campaign'] in {'robustness', 'sizing_qualification'}:
            robust.setdefault((row['campaign'], row['candidate']), []).append(row)
    comparison = []
    for (campaign, candidate), group in sorted(robust.items()):
        worst = max(group, key=lambda r: float(r['terminal_magnitude_max_v']))
        comparison.append(dict(campaign=campaign, candidate=candidate, cases=len(group),
            eligible=all(eligible(r) for r in group), logic_fail=sum(r['result']!='PASS' for r in group),
            magnitude_outside=sum(r['magnitude_result']!='PASS' for r in group),
            terminal_magnitude_max_v=float(worst['terminal_magnitude_max_v']),
            diagnostic_headroom_mv=1000*(1.95-float(worst['terminal_magnitude_max_v'])),
            worst_device=worst['terminal_magnitude_device'], worst_voltage=worst['terminal_magnitude_voltage'],
            worst_profile=worst['profile'], worst_old=worst['old_address'], worst_new=worst['new_address'],
            wl_delay90_max_ps=max(float(r['wl_delay90_ps']) for r in group if r['wl_delay90_ps']),
            wl_precharge10_max_ps=max(float(r['wl_precharge10_ps']) for r in group if r['wl_precharge10_ps']),
            vdd_energy_max_fj=max(float(r['vdd_src_cycle_energy_fj']) for r in group),
            channel_area_proxy_um2=float(group[0]['channel_area_proxy_um2'])))
    if comparison:
        screen.write_csv(args.output_dir / 'robustness_candidates.csv', comparison)
    (args.output_dir / "sources.json").write_text(json.dumps(dict(directories=[str(d) for d in args.directories],
                                                                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                                                source_sha256={str(d/name): hashlib.sha256((d/name).read_bytes()).hexdigest()
                                                                               for d in args.directories for name in ("manifest.json", "summary.csv")},
                                                                note="PASS combines declared logic/settling checks and upper/magnitude diagnostics; not full signed model validity. Grid endpoints are sampled bounds, not exact minima or external setup/Fmax."), indent=2)+"\n")
    print(json.dumps(totals, indent=2))


if __name__ == "__main__":
    main()
