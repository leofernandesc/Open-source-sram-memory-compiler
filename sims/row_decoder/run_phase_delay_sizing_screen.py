#!/usr/bin/env python3
"""Compare PCLK delay-chain inverter widths using the Xschem phase hierarchy.

This is a bounded screening campaign. It keeps the checked-in schematic and
phase logic unchanged, overrides only the two widths in the generated
phase_delay_inv SPICE subcircuit, then runs the existing decoder/WL/precharge
integration bench at TT, SS, and FF.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "sims/row_decoder/run_precharge_phase_interface.py"
DEFAULT_CANDIDATES = (
    ("min_balanced", 0.42, 0.42),
    ("reference", 0.84, 0.42),
    ("p_stronger", 1.26, 0.42),
    ("n_stronger", 0.84, 0.63),
    ("scaled_1p5", 1.26, 0.63),
    ("scaled_2x", 1.68, 0.84),
)


def parse_candidate(value: str) -> tuple[str, float, float]:
    parts = value.split(":")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("candidate format is NAME:PFET_W_UM:NFET_W_UM")
    name = parts[0]
    try:
        pfet, nfet = float(parts[1]), float(parts[2])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("candidate widths must be numbers") from exc
    if not name or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
                        for character in name):
        raise argparse.ArgumentTypeError("candidate name may contain letters, numbers, _ and -")
    if pfet < 0.42 or nfet < 0.42:
        raise argparse.ArgumentTypeError("SKY130A 01v8 widths must be at least 0.42 um per finger")
    return name, pfet, nfet


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def load_metrics(folder: Path) -> dict:
    summaries = read_csv(folder / "summary.csv")
    case_data = []
    for path in sorted((folder / "cases").glob("*/case.json")):
        case_data.append(json.loads(path.read_text(encoding="utf-8")))
    checks = read_csv(folder / "checks.csv")

    def numbers(values):
        return [float(value) for value in values
                if value is not None and value != "" and value != "None"]

    captures = numbers([
        case.get("phase_source_timing", {}).get("capture_to_pclk_rise_ps")
        for case in case_data])
    release_leads = numbers([
        measurement.get("lead_ps")
        for case in case_data
        for measurement in case.get("precharge_timing", {}).get("precharge_releases", [])])
    reassert_delays = numbers([
        measurement.get("pclk_fall_to_precharge_conduction_ps")
        for case in case_data
        for measurement in case.get("precharge_timing", {}).get("precharge_reassertions", [])])
    wl_clearances = numbers([
        measurement.get("selected_wl_off_clearance_ps")
        for case in case_data
        for measurement in case.get("precharge_timing", {}).get("precharge_reassertions", [])])
    bitline_values = numbers([
        row.get("value") for row in checks
        if "_precharged_before_eval_v" in row.get("check", "")])
    statuses = [row.get("status", "MISSING") for row in summaries]
    return {
        "cases": len(summaries),
        "case_json_count": len(case_data),
        "passed_cases": sum(status == "PASS" for status in statuses),
        "failed_cases": sum(status != "PASS" for status in statuses),
        "capture_to_pclk_min_ps": min(captures) if captures else None,
        "capture_to_pclk_max_ps": max(captures) if captures else None,
        "precharge_release_lead_min_ps": min(release_leads) if release_leads else None,
        "pclk_fall_to_precharge_min_ps": min(reassert_delays) if reassert_delays else None,
        "selected_wl_off_clearance_min_ps": min(wl_clearances) if wl_clearances else None,
        "bitline_pre_eval_min_v": min(bitline_values) if bitline_values else None,
        "status": "PASS" if summaries and all(status == "PASS" for status in statuses)
                  and len(case_data) == len(summaries) else "INCOMPLETE_OR_FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--candidate", action="append", type=parse_candidate,
                        help="Candidate NAME:PFET_W_UM:NFET_W_UM; may be repeated")
    parser.add_argument("--profiles", nargs="+", choices=("tt", "slow", "fast"),
                        default=["tt", "slow", "fast"])
    parser.add_argument("--step-ps", type=float, default=5.0)
    args = parser.parse_args()

    output = args.output_dir.resolve()
    if output.exists():
        parser.error(f"choose a new output directory: {output}")
    candidates = args.candidate or list(DEFAULT_CANDIDATES)
    names = [candidate[0] for candidate in candidates]
    if len(names) != len(set(names)):
        parser.error("candidate names must be unique")
    output.mkdir(parents=True)
    campaign = {
        "campaign": "phase_delay_inverter_width_screen",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "source_schematic_unchanged": True,
        "device_width_floor_um_per_finger": 0.42,
        "width_floor_basis": "Xschem SKY130 helper fet_drc checks [np]fet_01v8 finger width against 0.42 um",
        "fixed_topology": "80-stage Xschem CMOS inverter chain; taps 24/60/80; only phase_delay_inv PFET/NFET widths vary",
        "profiles": args.profiles,
        "access_case": "valid read, address 0 to 3",
        "phase_and_load_conditions": {
            "phase_source": "xschem-tapped-delay-chain",
            "capture_schedule_ps": 2100,
            "clock_fall_ps": 22000,
            "settling_allowance_ns": 3.4,
            "row_load_ff": 102.873935496,
            "bitline_target_ceff_ff": 597.056241,
            "maximum_transient_step_ps": args.step_ps,
            "decoder_wl_precharge": "current project PEX inputs, including Danilo's pinned W2.52 precharge PEX",
        },
        "candidates": [],
    }
    (output / "campaign.json").write_text(json.dumps(campaign, indent=2) + "\n",
                                          encoding="utf-8")
    summary_rows = []
    for index, (name, pfet, nfet) in enumerate(candidates, 1):
        candidate_dir = output / name
        command = [
            sys.executable, str(RUNNER),
            "--output-dir", str(candidate_dir),
            "--profiles", *args.profiles,
            "--transitions", "0:3",
            "--control-vectors", "001",
            "--phase-ps", "2100",
            "--clk-fall-ps", "22000",
            "--settling-allowance-ns", "3.4",
            "--wl-cap-ff", "102.873935496",
            "--release-lead-ps", "250",
            "--turnoff-guard-ps", "1800",
            "--step-ps", str(args.step_ps),
            "--phase-source", "xschem-tapped-delay-chain",
            "--delay-release-stages", "24",
            "--delay-evaluation-stages", "60",
            "--delay-reassert-stages", "80",
            "--phase-delay-pfet-w-um", f"{pfet:.6g}",
            "--phase-delay-nfet-w-um", f"{nfet:.6g}",
        ]
        print(f"Sizing screen {index}/{len(candidates)}: {name} Wp={pfet:g} um Wn={nfet:g} um",
              flush=True)
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        (output / f"{name}.log").write_text(proc.stdout + proc.stderr,
                                              encoding="utf-8")
        metrics = load_metrics(candidate_dir)
        result = {
            "name": name,
            "pfet_width_um": pfet,
            "nfet_width_um": nfet,
            "chain_width_sum_um": 80 * (pfet + nfet),
            "chain_channel_area_proxy_um2": 80 * 0.15 * (pfet + nfet),
            "runner_exit_code": proc.returncode,
            "output_dir": str(candidate_dir.relative_to(ROOT)),
            **metrics,
        }
        campaign["candidates"].append(result)
        summary_rows.append(result)
        (output / "campaign.json").write_text(json.dumps(campaign, indent=2) + "\n",
                                              encoding="utf-8")
        print(f"  {result['status']}: {result['passed_cases']}/{result['cases']} cases; "
              f"minimum WL-off clearance={result['selected_wl_off_clearance_min_ps']} ps",
              flush=True)

    campaign["finished_utc"] = datetime.now(timezone.utc).isoformat()
    campaign["complete"] = all(row["runner_exit_code"] == 0
                               and row["status"] == "PASS" for row in summary_rows)
    (output / "campaign.json").write_text(json.dumps(campaign, indent=2) + "\n",
                                          encoding="utf-8")
    columns = [
        "name", "pfet_width_um", "nfet_width_um", "chain_width_sum_um",
        "chain_channel_area_proxy_um2", "cases", "passed_cases", "failed_cases",
        "capture_to_pclk_min_ps", "capture_to_pclk_max_ps",
        "precharge_release_lead_min_ps", "pclk_fall_to_precharge_min_ps",
        "selected_wl_off_clearance_min_ps", "bitline_pre_eval_min_v", "status",
        "runner_exit_code", "output_dir",
    ]
    with (output / "summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows({key: row.get(key) for key in columns} for row in summary_rows)
    print(f"Summary: {output / 'summary.csv'}")
    print(f"Campaign: {output / 'campaign.json'}")
    return 0 if campaign["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
