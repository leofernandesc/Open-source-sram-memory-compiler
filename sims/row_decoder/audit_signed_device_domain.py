#!/usr/bin/env python3
"""Audit polarity-oriented MOS terminal voltages in archived decoder waveforms.

This is a postprocessor: it does not netlist or simulate. For each MOS sample,
it treats the lower-potential diffusion as the effective source for NFETs and
the higher-potential diffusion as the effective source for PFETs, then checks
the resulting VGS/VDS/VBS values against the published SKY130 1.8 V ranges.
That source/drain convention is an engineering screen, not a PDK signoff rule.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "sims/row_decoder/results"
LIMITS = {
    "n": {"VGS": (0.0, 1.95), "VDS": (0.0, 1.95), "VBS": (-1.95, 0.30)},
    "p": {"VGS": (-1.95, 0.0), "VDS": (-1.95, 0.0), "VBS": (-0.10, 1.95)},
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_leaf_devices(netlist_path: Path) -> dict[str, tuple[str, list[str]]]:
    """Map archived top-level instances to MOS polarity and four probe nodes."""
    subckts: dict[str, tuple[list[str], list[str]]] = {}
    instances: list[list[str]] = []
    current: str | None = None
    body: list[str] = []
    for raw_line in netlist_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("*"):
            continue
        parts = line.split()
        if parts[0].lower() == ".subckt":
            current = parts[1].lower()
            body = []
            subckts[current] = (parts[2:], body)
        elif parts[0].lower() == ".ends":
            current = None
        elif current is not None:
            body.append(line)
        elif parts[0].lower().startswith("x") and parts[-1].lower() in {"row_decoder", "wl_driver"}:
            instances.append(parts)

    result: dict[str, tuple[str, list[str]]] = {}
    for inst in instances:
        instance_name, subckt_name = inst[0].lower(), inst[-1].lower()
        if subckt_name not in subckts:
            raise ValueError(f"Missing .subckt {subckt_name} in {netlist_path}")
        pins, body = subckts[subckt_name]
        port_map = {pin.upper(): net for pin, net in zip(pins, inst[1:-1])}
        if len(port_map) != len(pins):
            raise ValueError(f"Pin count mismatch for {instance_name} in {netlist_path}")
        for line in body:
            tok = line.split()
            if len(tok) < 6 or not tok[0].lower().startswith("x"):
                continue
            model = tok[5].lower()
            if "sky130_fd_pr__nfet_01v8" in model:
                kind = "n"
            elif "sky130_fd_pr__pfet_01v8" in model:
                kind = "p"
            else:
                continue
            label = instance_name + "." + tok[0][1:].lower()
            nodes = []
            for pin in tok[1:5]:
                node = port_map.get(pin.upper(), instance_name + "." + pin.lower()).lower()
                nodes.append("0" if node in {"gnd", "0"} else node)
            if label in result:
                raise ValueError(f"Duplicate MOS label {label} in {netlist_path}")
            result[label] = (kind, nodes)
    if not result:
        raise ValueError(f"No SKY130 1.8 V MOS devices found in {netlist_path}")
    return result


def read_raw(path: Path) -> tuple[dict[str, np.ndarray], str]:
    """Read a real, point-major ngspice raw file and return traces plus hash."""
    content = path.read_bytes()
    try:
        header, binary = content.split(b"Binary:\n", 1)
    except ValueError as error:
        raise ValueError(f"Missing Binary marker in {path}") from error
    text = header.decode()
    if "Flags: real" not in text or "fastaccess" in text.lower():
        raise ValueError(f"Expected real point-major ngspice data in {path}")
    variable_count = int(re.search(r"No. Variables:\s*(\d+)", text)[1])
    point_count = int(re.search(r"No. Points:\s*(\d+)", text)[1])
    names = [line.split()[1].lower() for line in text.split("Variables:\n")[1].splitlines()
             if line.strip()]
    if len(names) != variable_count or len(binary) != point_count * variable_count * 8:
        raise ValueError(f"Raw header/data dimensions disagree in {path}")
    data = np.frombuffer(binary, dtype=np.float64).reshape(point_count, variable_count)
    return {name: data[:, index] for index, name in enumerate(names)}, sha256(content)


def new_accumulator(low: float, high: float) -> dict:
    return {
        "limits_v": [low, high],
        "min_v": float("inf"),
        "max_v": float("-inf"),
        "low_violation_samples": 0,
        "high_violation_samples": 0,
        "low_violation_device_cases": set(),
        "high_violation_device_cases": set(),
        "worst_low": None,
        "worst_high": None,
        "low_excursion_v": 0.0,
        "high_excursion_v": 0.0,
    }


def measure(raw: dict[str, np.ndarray], devices: dict, case: str,
            start_time_s: float, window_name: str, stats: dict) -> None:
    time = raw["time"]
    mask = np.ones(time.shape, dtype=bool) if window_name == "full_transient" else time >= start_time_s
    if not np.any(mask):
        raise ValueError(f"No samples in {window_name} for {case}")
    for name, (kind, nodes) in devices.items():
        pins = []
        for node in nodes:
            key = f"v({node})"
            if node == "0":
                pins.append(np.zeros_like(time))
            elif key in raw:
                pins.append(raw[key])
            else:
                raise ValueError(f"Missing probe {key} for {case}/{name}")
        drain, gate, source, bulk = (pin[mask] for pin in pins)
        if kind == "n":
            effective_source = np.minimum(drain, source)
            values = {
                "VGS": gate - effective_source,
                "VDS": np.maximum(drain, source) - effective_source,
                "VBS": bulk - effective_source,
            }
        else:
            effective_source = np.maximum(drain, source)
            values = {
                "VGS": gate - effective_source,
                "VDS": np.minimum(drain, source) - effective_source,
                "VBS": bulk - effective_source,
            }
        for metric, wave in values.items():
            key = (kind, metric)
            entry = stats[(window_name, *key)]
            low, high = LIMITS[kind][metric]
            minimum, maximum = float(wave.min()), float(wave.max())
            entry["min_v"] = min(entry["min_v"], minimum)
            entry["max_v"] = max(entry["max_v"], maximum)
            low_mask, high_mask = wave < low, wave > high
            entry["low_violation_samples"] += int(low_mask.sum())
            entry["high_violation_samples"] += int(high_mask.sum())
            if np.any(low_mask):
                entry["low_violation_device_cases"].add((case, name))
                excursion = float(low - minimum)
                if excursion > entry["low_excursion_v"]:
                    index = int(np.argmin(wave))
                    entry["low_excursion_v"] = excursion
                    entry["worst_low"] = {
                        "case": case, "device": name, "value_v": minimum,
                        "time_ns": float(time[mask][index] * 1e9), "limit_v": low,
                    }
            if np.any(high_mask):
                entry["high_violation_device_cases"].add((case, name))
                excursion = float(float(wave[high_mask].max()) - high)
                if excursion > entry["high_excursion_v"]:
                    index = int(np.argmax(wave))
                    entry["high_excursion_v"] = excursion
                    entry["worst_high"] = {
                        "case": case, "device": name, "value_v": maximum,
                        "time_ns": float(time[mask][index] * 1e9), "limit_v": high,
                    }


def audit_matrix(profile: str, step_ps: float, after_ns: float,
                 matrix_root_override: Path | None = None,
                 expected_cases: int = 16) -> tuple[list[dict], dict]:
    label = f"compact_decoder_full_{profile}_matrix_{step_ps:g}ps"
    matrix_root = matrix_root_override or (RESULTS / label)
    label = matrix_root.name
    if not matrix_root.is_dir():
        raise ValueError(f"Missing archived matrix: {matrix_root}")
    records, provenance = [], {"matrix": label, "stages": {}}
    for stage in ("baseline", "pex"):
        netlist_path = matrix_root / stage / "input_netlist.spice"
        devices = parse_leaf_devices(netlist_path)
        raw_paths = sorted((matrix_root / "artifacts" / stage).glob("*/waveform.raw"))
        if len(raw_paths) != expected_cases:
            raise ValueError(f"Expected {expected_cases} raw waveforms in {matrix_root}/artifacts/{stage}; found {len(raw_paths)}")
        stats = {}
        for window in ("full_transient", "after_startup"):
            for kind in ("n", "p"):
                for metric, (low, high) in LIMITS[kind].items():
                    stats[(window, kind, metric)] = new_accumulator(low, high)
        raw_hashes = {}
        print(f"Auditing {profile.upper()} {stage}: {len(raw_paths)} waveforms, {len(devices)} MOS", flush=True)
        for raw_path in raw_paths:
            raw, raw_hash = read_raw(raw_path)
            case = raw_path.parent.name
            raw_hashes[case] = raw_hash
            measure(raw, devices, case, after_ns * 1e-9, "full_transient", stats)
            measure(raw, devices, case, after_ns * 1e-9, "after_startup", stats)
        netlist_hash = sha256(netlist_path.read_bytes())
        manifest_path = matrix_root / stage / "manifest.json"
        manifest_hash = sha256(manifest_path.read_bytes()) if manifest_path.exists() else None
        provenance["stages"][stage] = {
            "netlist_sha256": netlist_hash,
            "manifest_sha256": manifest_hash,
            "pex_sha256": (matrix_root / "pex.sha256").read_text().split()[0]
            if (matrix_root / "pex.sha256").exists() else None,
            "device_count": len(devices),
            "case_count": len(raw_paths),
            "expected_case_count": expected_cases,
            "raw_sha256_by_case": raw_hashes,
        }
        for (window, kind, metric), entry in stats.items():
            records.append({
                "profile": profile, "stage": stage, "window": window,
                "device_type": "nfet_01v8" if kind == "n" else "pfet_01v8",
                "metric": metric, "low_limit_v": entry["limits_v"][0],
                "high_limit_v": entry["limits_v"][1],
                "min_v": entry["min_v"], "max_v": entry["max_v"],
                "low_violation_samples": entry["low_violation_samples"],
                "high_violation_samples": entry["high_violation_samples"],
                "low_violation_device_cases": len(entry["low_violation_device_cases"]),
                "high_violation_device_cases": len(entry["high_violation_device_cases"]),
                "worst_low": entry["worst_low"], "worst_high": entry["worst_high"],
            })
    return records, provenance


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", nargs="+", choices=("tt", "fast", "slow"), default=("fast", "slow"))
    parser.add_argument("--step-ps", type=float, default=1.0)
    parser.add_argument("--matrix-root", type=Path,
                        help="use a custom archive root for one selected profile")
    parser.add_argument("--expected-cases", type=int, default=16,
                        help="require this number of waveforms per stage (default: full 16-pair matrix)")
    parser.add_argument("--after-ns", type=float, default=1.0,
                        help="also report an operating window that excludes the initial transient")
    parser.add_argument("--output-json", type=Path,
                        default=RESULTS / "signed_device_domain_audit.json")
    parser.add_argument("--output-csv", type=Path,
                        default=RESULTS / "signed_device_domain_audit.csv")
    args = parser.parse_args()
    if args.step_ps <= 0 or args.after_ns < 0 or args.expected_cases <= 0:
        parser.error("step and expected-cases must be positive; after-ns must be nonnegative")
    if args.matrix_root is not None and len(args.profiles) != 1:
        parser.error("--matrix-root requires exactly one --profiles entry")
    matrix_root = args.matrix_root
    if matrix_root is not None and not matrix_root.is_absolute():
        matrix_root = ROOT / matrix_root
    all_records, matrices = [], []
    for profile in args.profiles:
        records, provenance = audit_matrix(profile, args.step_ps, args.after_ns,
                                           matrix_root, args.expected_cases)
        all_records.extend(records)
        matrices.append(provenance)
    result = {
        "title": "Polarity-oriented SKY130 1.8 V MOS bias-range screen",
        "audit_script_sha256": sha256(Path(__file__).read_bytes()),
        "scope": (
            f"Postprocessing of archived {args.expected_cases}-case baseline and extracted-PEX "
            f"waveforms for profile(s) {', '.join(args.profiles)}. "
            "For each sample, the lower-potential diffusion is treated as NFET effective source and "
            "the higher-potential diffusion as PFET effective source. Published SKY130 VGS/VDS/VBS "
            "ranges are compared under that convention. This is an engineering screen, not a PDK "
            "model-owner qualification, reliability assessment, or signoff."
        ),
        "published_ranges_source": "https://github.com/google/skywater-pdk/blob/main/docs/rules/device-details.rst#L196-L248",
        "operating_window": {"name": "after_startup", "start_ns": args.after_ns,
                             "definition": "all archived samples at or after this time"},
        "full_transient_window": "all samples in each archived waveform, including UIC startup",
        "records": all_records,
        "matrices": matrices,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2) + "\n")
    with args.output_csv.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(all_records[0]), lineterminator="\n")
        writer.writeheader()
        for record in all_records:
            writer.writerow({key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value
                             for key, value in record.items()})
    print(f"JSON: {args.output_json}")
    print(f"CSV: {args.output_csv}")
    for row in all_records:
        if row["window"] != "after_startup":
            continue
        low, high = row["low_violation_samples"], row["high_violation_samples"]
        print(f"{row['profile'].upper()} {row['stage']} {row['device_type']} {row['metric']}: "
              f"{row['min_v']:.6f}..{row['max_v']:.6f} V; "
              f"out-of-range low/high samples={low}/{high}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
