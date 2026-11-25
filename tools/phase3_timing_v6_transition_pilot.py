#!/usr/bin/env python3
"""Extract provisional tCLK_TO_DATA from the sealed v6 integrated waveforms."""

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PEX_SHA256 = "a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f"
GDS_SHA256 = "315c2ebceb2bc4cf258fa63be2279843805db3010637d0c273aea9db12813e37"
CORNERS = ("TT", "SS", "FF")
VDD = 1.8
FALL_THRESHOLD = VDD / 2
LOW_MAX = VDD * .2
HIGH_MIN = VDD * .8


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def crossing(samples, bit, expected, fall_ns):
    before = [sample for sample in samples if sample[0] <= fall_ns]
    after = [sample for sample in samples if sample[0] > fall_ns]
    require(before and after, "Missing native samples around public CLK fall")
    initial = before[-1][bit + 1]
    opposite = initial <= LOW_MAX if expected else initial >= HIGH_MIN
    if not opposite:
        return dict(status="NOT_CHARACTERIZED", reason="DATA_NOT_OPPOSITE_AT_CLK_FALL",
                    pre_fall_v=initial)

    previous = before[-1]
    for sample in after:
        if sample[0] > fall_ns + 2:
            break
        current = sample[bit + 1]
        passed = previous[1 + bit] < FALL_THRESHOLD <= current if expected else (
            previous[1 + bit] > FALL_THRESHOLD >= current)
        if passed:
            time_ns = previous[0] + (FALL_THRESHOLD - previous[1 + bit]) * (
                sample[0] - previous[0]) / (current - previous[1 + bit])
            return dict(status="MEASURED", pre_fall_v=initial, data50_ns=time_ns,
                        tclk_to_data_ns=time_ns - fall_ns,
                        native_bracket_ns=[previous[0], sample[0]])
        previous = sample
    return dict(status="NOT_CHARACTERIZED", reason="NO_EXPECTED_DIRECTION_CROSSING_WITHIN_2NS",
                pre_fall_v=initial)


def analyze_corner(build, corner):
    run = build / "integrated_v6_idle_247p5" / corner
    observed = build / "integrated_v6_observed_247p5" / corner
    simulation_path = run / "simulation.json"
    fixture_path = run / "fixture.json"
    waveform_path = run / "waveform.dat"
    analysis_path = observed / "analysis.json"
    simulation, fixture, analysis = (json.loads(p.read_text()) for p in
                                     (simulation_path, fixture_path, analysis_path))
    require(simulation["status"] == "COMPLETED" and simulation["returncode"] == 0,
            f"{corner}: source replay did not complete")
    require(simulation["electrical_qualification"] == "NOT_CHARACTERIZED",
            f"{corner}: unexpected qualification state")
    require(simulation["waveform_sha256"] == sha256(waveform_path),
            f"{corner}: waveform hash mismatch")
    reads = [cycle for cycle in fixture["cycles"] if cycle["operation"] == "read"]
    require(len(reads) == 9, f"{corner}: expected nine integrated read events")

    windows = [(cycle["fall_ns"] - .1, cycle["fall_ns"] + 2, cycle)
               for cycle in reads]
    selected = {cycle["cycle"]: [] for cycle in reads}
    with waveform_path.open() as stream:
        columns = stream.readline().split()
        indices = [columns.index("time")] + [columns.index(f"v(DATA{bit})") for bit in range(8)]
        for line in stream:
            fields = line.split()
            time_ns = float(fields[indices[0]]) * 1e9
            for start, end, cycle in windows:
                if start <= time_ns <= end:
                    selected[cycle["cycle"]].append(
                        (time_ns, *[float(fields[i]) for i in indices[1:]]))

    events = []
    for cycle in reads:
        number = cycle["cycle"]
        observed_cycle = analysis["cycles"][str(number)]
        require(observed_cycle["verdict"] == "PASS", f"{corner} c{number}: functional read failed")
        lanes = observed_cycle["lanes"]
        require(len(lanes) == 8, f"{corner} c{number}: expected eight lanes")
        measurements = []
        for bit, lane in enumerate(lanes):
            expected = (cycle["expected"] >> bit) & 1
            require(lane["verdict"] == "PASS" and lane["expected"] == expected,
                    f"{corner} c{number} bit{bit}: observer/fixture mismatch")
            result = crossing(selected[number], bit, expected, cycle["fall_ns"])
            if result["status"] == "MEASURED":
                valid_ns = lane["verified_from_ns"]["data"]
                require(result["data50_ns"] <= valid_ns,
                        f"{corner} c{number} bit{bit}: DATA50 occurs after observer validity")
                result["observer_valid_ns"] = valid_ns
                result["observer_valid_after_data50_ps"] = (valid_ns-result["data50_ns"])*1000
            measurements.append(dict(bit=bit, expected=expected, **result))
        events.append(dict(cycle=number, expected_word=f"0x{cycle['expected']:02X}",
                           clk_fall_ns=cycle["fall_ns"], lanes=measurements))

    values = [lane["tclk_to_data_ns"] for event in events for lane in event["lanes"]
              if lane["status"] == "MEASURED"]
    require(len(values) == 48, f"{corner}: expected 48 measured lane transitions, got {len(values)}")
    return dict(status="PROVISIONAL", read_count=len(reads), measured_transitions=len(values),
                not_characterized_lanes=72-len(values),
                min_ns=min(values), mean_ns=sum(values)/len(values), max_ns=max(values),
                events=events,
                inputs={str(p.relative_to(ROOT)): sha256(p) for p in
                        (simulation_path, fixture_path, waveform_path, analysis_path)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--build-root", type=Path, default=ROOT / "build/phase3")
    args = parser.parse_args()
    result = dict(schema="phase3-v6-tclk-to-data-pilot-v1", status="PROVISIONAL",
                  method="For each read lane whose DATA is at the opposite rail immediately before public CLK falling, linearly interpolate the first expected-direction DATA50 crossing after that edge. Confirm later DATA validity with the pinned integrated observer. No added probe or load/slew sweep.",
                  geometry="v6 physical integrated PEX",
                  conditions=dict(pex_sha256=PEX_SHA256, gds_sha256=GDS_SHA256,
                                 vdd_v=VDD, temperature_c=27, data_load_ff_per_lane=10,
                                 cycle_ns=20, threshold_v=FALL_THRESHOLD),
                  corners={corner: analyze_corner(args.build_root, corner) for corner in CORNERS},
                  qualification="NOT_CHARACTERIZED")
    result["script_sha256"] = sha256(Path(__file__).resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
