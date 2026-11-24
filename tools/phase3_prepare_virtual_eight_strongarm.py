#!/usr/bin/env python3
"""Prepare an isolated, virtual-only 8-StrongARM C250 comparison deck.

The original C250 extracted binding is used as an immutable RC envelope. This
script removes only the five remaining native sense-amplifier transistor sets
and inserts flattened copies of the archived 11-MOS StrongARM plus two output
buffers per lane. It does not edit layout or claim a new physical extraction.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import shutil


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKOUT = Path("/tmp/phase3-v6-handoff-20261122/historical-checkout")
BUILD = Path("build/phase3")
C250 = BUILD / "strongarm_functional_closure_20261122/c250/TT"
TRIPLE = BUILD / "strongarm_triple_20261122/physical/fabric_v6"
CORE = TRIPLE / "fabric_reference.spice"
EXPECTED_PEX = "a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f"
EXPECTED_BINDING = "3b6f7205476b79d02754ba081a7d2eb2ef9d372670daf26067d3d0cb5745e76d"
EXPECTED_BENCH = "a5e3adba9f5c1461054817928487901a8f06505585d6a57c1c6b3b4cc7b1c2ce"
LANES = {
    0: {"removed": ("X508", "X827", "X1096", "X1213", "X1214", "X1318", "X1496"),
        "BL": "pnode8188", "BLB": "pnode8200", "SCLK": "pnode8801", "VDD": "pnode1729", "VSS": "pnode6038", "SA": "pnode6156", "SAB": "pnode8382", "NTAIL": "pnode6706", "D": "pnode6506", "Q": "pnode6601"},
    1: {"removed": ("X63", "X241", "X261", "X882", "X1298", "X1732", "X1734"),
        "BL": "pnode8212", "BLB": "pnode8224", "SCLK": "pnode8768", "VDD": "pnode1731", "VSS": "pnode6040", "SA": "pnode6151", "SAB": "pnode8388", "NTAIL": "pnode6863", "D": "pnode6509", "Q": "pnode6611"},
    2: {"removed": ("X824", "X1072", "X1358", "X1491", "X1492", "X1614", "X1778"),
        "BL": "pnode8402", "BLB": "pnode8414", "SCLK": "pnode8771", "VDD": "pnode1733", "VSS": "pnode6042", "SA": "pnode6143", "SAB": "pnode8418", "NTAIL": "pnode7133", "D": "pnode6511", "Q": "pnode6512"},
    4: {"removed": ("X105", "X283", "X1070", "X1337", "X1656", "X1773", "X1774"),
        "BL": "pnode8432", "BLB": "pnode8444", "SCLK": "pnode8780", "VDD": "pnode1735", "VSS": "pnode6046", "SA": "pnode6130", "SAB": "pnode8448", "NTAIL": "pnode7501", "D": "pnode6527", "Q": "pnode6643"},
    5: {"removed": ("X78", "X404", "X532", "X533", "X658", "X836", "X1590"),
        "BL": "pnode8260", "BLB": "pnode8272", "SCLK": "pnode8783", "VDD": "pnode1737", "VSS": "pnode6049", "SA": "pnode6119", "SAB": "pnode8454", "NTAIL": "pnode7653", "D": "pnode6528", "Q": "pnode6654"},
}
STD_BUF = "sky130_fd_sc_hd__buf_1"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def cards(text: str) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        s = line.strip()
        if s and not s.startswith(("*", ".")) and s[0].upper() in "XRC":
            name = s.split()[0]
            if name in result:
                raise ValueError(f"duplicate SPICE card {name}")
            result[name] = s
    return result


def check_inputs(checkout: Path) -> tuple[Path, Path, Path, dict]:
    c250 = checkout / C250
    triple = checkout / TRIPLE
    pex = checkout / BUILD / "strongarm_triple_20261122/physical/pex_verified/extracted_rc.spice"
    manifest = read_json(c250 / "preflight.json")
    if manifest.get("gate") != "READY" or manifest.get("corner") != "tt":
        raise ValueError("C250 TT capture is not READY")
    for name, expected in manifest["outputs"].items():
        if sha(c250 / name) != expected:
            raise ValueError(f"C250 input hash mismatch: {name}")
    if sha(pex) != manifest["physical_pex_sha256"]:
        raise ValueError("sealed physical PEX hash differs from C250 manifest")
    if (sha(pex) != EXPECTED_PEX or sha(c250 / "binding.spice") != EXPECTED_BINDING
            or sha(c250 / "bench.spice") != EXPECTED_BENCH):
        raise ValueError("input PEX/binding/fixture differs from the reviewed v6 identity")
    if sha(triple / "fabric_reference.spice") != "f22ba2beb25fa4f8d3e2a4549d0933581d4af7fbe3263c61d18fe7fcd812539c":
        # The source is checked structurally below as well; update only if the
        # archived release source itself is intentionally revised.
        raise ValueError("archived StrongARM source hash differs from reviewed source")
    return c250, triple, pex, manifest


def model_sources(source: str) -> tuple[str, str]:
    core_match = re.search(r"(?ms)^\.subckt\s+strongarm_tt_v0\b.*?^\.ends\s+strongarm_tt_v0\s*$", source)
    buf_match = re.search(r"(?ms)^\.subckt\s+sky130_fd_sc_hd__buf_1\b.*?^\.ends\s+sky130_fd_sc_hd__buf_1\s*$", source)
    if not core_match or not buf_match:
        raise ValueError("StrongARM core or archived buf_1 subcircuit not found")
    core, buf = core_match.group(0), buf_match.group(0)
    if core.splitlines()[0].split()[2:] != ["BL", "BLB", "SCLK", "VDD", "VSS", "SA", "SAB"]:
        raise ValueError("unexpected StrongARM port order")
    if buf.splitlines()[0].split()[2:] != ["A", "VGND", "VNB", "VPB", "VPWR", "X"]:
        raise ValueError("unexpected buf_1 port order")
    return core, buf


def flatten_core(core: str, lane: int, mapping: dict[str, str]) -> list[str]:
    internal = {"DI_BL": f"virtual_b{lane}_di_bl", "DI_BLB": f"virtual_b{lane}_di_blb",
                "SA": f"virtual_b{lane}_sa", "SAB": f"virtual_b{lane}_sab"}
    pinmap = {**mapping, **internal}
    out = []
    for line in core.splitlines():
        tokens = line.split()
        if not tokens or tokens[0][0].upper() != "X":
            continue
        if len(tokens) < 6:
            raise ValueError(f"malformed StrongARM instance: {line}")
        name, nodes, model, params = tokens[0], tokens[1:5], tokens[5], tokens[6:]
        try:
            mapped = [pinmap[n] for n in nodes]
        except KeyError as e:
            raise ValueError(f"unmapped core node {e.args[0]}") from e
        out.append(" ".join([f"XV8_B{lane}_{name}", *mapped, model, *params]))
    if len(out) != 11:
        raise ValueError(f"expected 11 flattened core MOS, found {len(out)}")
    return out


def prepare(checkout: Path, out: Path, corner: str) -> None:
    c250, triple, pex, manifest = check_inputs(checkout)
    if out.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {out}")
    original = (c250 / "binding.spice").read_text()
    original_lines = original.splitlines(keepends=True)
    original_cards = cards(original)
    removed = {name for lane in LANES.values() for name in lane["removed"]}
    if len(removed) != 35 or not removed <= original_cards.keys():
        raise ValueError("native sense device inventory does not match 35 unique cards")
    for lane_id, lane in LANES.items():
        if any(not re.search(r"\bsky130_fd_pr__(?:n|p)fet_01v8\b", original_cards[n]) for n in lane["removed"]):
            raise ValueError(f"lane {lane_id} inventory includes a non-native MOS")
    core, buf = model_sources((triple / "fabric_reference.spice").read_text())
    source_map_path = c250 / "map.json"
    if sha(source_map_path) != manifest["outputs"]["map.json"]:
        raise ValueError("C250 probe map hash mismatch")
    probe_map = read_json(source_map_path)
    out.mkdir(parents=True)
    candidate_lines = [line for line in original_lines if not (line.split() and line.split()[0] in removed)]
    try:
        end_index = next(i for i, line in enumerate(candidate_lines) if line.strip().lower() == ".ends sram_4x8_wrapper")
    except StopIteration as e:
        raise ValueError("wrapper end marker missing") from e
    added = []
    current_probes = []
    currents_by_lane = {}
    core_probe_aliases = {}
    for lane_id, lane in LANES.items():
        added.extend(flatten_core(core, lane_id, lane))
        currents_by_lane[lane_id] = [
            f"@m.xdut.xv8_b{lane_id}_xtail.msky130_fd_pr__nfet_01v8[id]",
            f"@m.xdut.xv8_b{lane_id}_xr_di_bl.msky130_fd_pr__pfet_01v8[id]",
            f"@m.xdut.xv8_b{lane_id}_xr_di_blb.msky130_fd_pr__pfet_01v8[id]",
            f"@m.xdut.xv8_b{lane_id}_xr_sa.msky130_fd_pr__pfet_01v8[id]",
            f"@m.xdut.xv8_b{lane_id}_xr_sab.msky130_fd_pr__pfet_01v8[id]",
        ]
        current_probes.extend(currents_by_lane[lane_id])
        core_probe_aliases[str(lane_id)] = {key: f"v(xdut.virtual_b{lane_id}_{suffix})"
            for key, suffix in (("core_sa", "sa"), ("core_sab", "sab"),
                                ("di_bl", "di_bl"), ("di_blb", "di_blb"))}
        added.extend([
            f"XV8_B{lane_id}_BUF_SA virtual_b{lane_id}_sa {lane['VSS']} {lane['VSS']} {lane['VDD']} {lane['VDD']} {lane['SA']} {STD_BUF}",
            f"XV8_B{lane_id}_BUF_SAB virtual_b{lane_id}_sab {lane['VSS']} {lane['VSS']} {lane['VDD']} {lane['VDD']} {lane['SAB']} {STD_BUF}",
        ])
    candidate_lines[end_index:end_index] = [s + "\n" for s in added]
    candidate = "".join(candidate_lines)
    post_cards = cards(candidate)
    if original_cards.keys() - post_cards.keys() != removed:
        raise ValueError("candidate card removals differ from approved inventory")
    if post_cards.keys() - original_cards.keys() != {x.split()[0] for x in added}:
        raise ValueError("candidate additions differ from generated ECO inventory")
    for name in original_cards.keys() - removed:
        if post_cards[name] != original_cards[name]:
            raise ValueError(f"unchanged source card was modified: {name}")
    original_passives = [(n, v) for n, v in original_cards.items() if n.startswith(("R", "C"))]
    candidate_passives = [(n, v) for n, v in post_cards.items() if n.startswith(("R", "C"))]
    if original_passives != candidate_passives:
        raise ValueError("RC card inventory or ordering changed")

    old_bench = (c250 / "bench.spice").read_text()
    voltage_probes = []
    for lane_id, lane in LANES.items():
        voltage_probes += [f"v(xdut.{lane[key]})" for key in ("BL", "BLB", "SCLK", "NTAIL", "SA", "SAB", "D", "Q")]
        voltage_probes += [f"v(xdut.virtual_b{lane_id}_{suffix})" for suffix in ("sa", "sab", "di_bl", "di_blb")]
        lane_map = probe_map["probes"]["columns"][str(lane_id)]
        v = lane_map["voltages"]
        retained_currents = {key: value for key, value in lane_map["currents"].items()
                             if key.startswith("X")}
        v.update({
            "core_sa": f"v(xdut.virtual_b{lane_id}_sa)",
            "core_sab": f"v(xdut.virtual_b{lane_id}_sab)",
            "sa": f"v(xdut.{lane['SA']})", "sab": f"v(xdut.{lane['SAB']})",
            "out_sa": f"v(xdut.{lane['SA']})", "out_sab": f"v(xdut.{lane['SAB']})",
            "di_bl": f"v(xdut.virtual_b{lane_id}_di_bl)",
            "di_blb": f"v(xdut.virtual_b{lane_id}_di_blb)",
            "ntail": f"v(xdut.{lane['NTAIL']})", "sclk": f"v(xdut.{lane['SCLK']})",
            "vdd": f"v(xdut.{lane['VDD']})", "vss": f"v(xdut.{lane['VSS']})",
            "clk_tail": f"v(xdut.{lane['SCLK']})",
            "clk_reset_dibl": f"v(xdut.{lane['SCLK']})",
            "clk_reset_diblb": f"v(xdut.{lane['SCLK']})",
            "clk_reset_sa": f"v(xdut.{lane['SCLK']})",
            "clk_reset_sab": f"v(xdut.{lane['SCLK']})",
        })
        lane_map["currents"] = {**retained_currents,
            "tail": currents_by_lane[lane_id][0],
            "reset0": currents_by_lane[lane_id][1],
            "reset1": currents_by_lane[lane_id][2],
            "reset2": currents_by_lane[lane_id][3],
            "reset3": currents_by_lane[lane_id][4],
        }
    probe_map["scope"] = "virtual 8-StrongARM candidate; original v6 PEX RC envelope"
    probe_map["virtual_core_nodes"] = core_probe_aliases
    waveform_line, = [line for line in old_bench.splitlines() if line.startswith("wrdata waveform.dat ")]
    current_line, = [line for line in old_bench.splitlines() if line.startswith("wrdata currents.dat ")]
    old_wave_vectors = set(waveform_line.split()[2:])
    old_current_vectors = set(current_line.split()[2:])
    new_voltage_probes = list(dict.fromkeys(v for v in voltage_probes if v not in old_wave_vectors))
    new_current_probes = list(dict.fromkeys(v for v in current_probes if v not in old_current_vectors))
    lines = []
    for line in old_bench.splitlines():
        if line.startswith(".lib "):
            if not line.endswith(" tt"):
                raise ValueError("expected archived TT library selection")
            lines.append(line[:-2] + corner)
        elif line.startswith('.include "binding.spice"'):
            lines += [line, '.include "buf_1.spice"']
        elif line.startswith(".save "):
            lines.append(line + " " + " ".join(new_voltage_probes + new_current_probes))
        elif line.startswith("wrdata waveform.dat "):
            lines.append(line + " " + " ".join(new_voltage_probes))
        elif line.startswith("wrdata currents.dat "):
            lines.append(line + " " + " ".join(new_current_probes))
        else:
            lines.append(line)
    if sum(line.startswith('.include "buf_1.spice"') for line in lines) != 1:
        raise ValueError("bench include insertion failed")
    if [line for line in lines if line.startswith("tran ")] != ["tran 10p 250n 0 25p"]:
        raise ValueError("C250 timing contract changed")
    new_bench = "\n".join(lines) + "\n"

    shutil.copyfile(c250 / "fabric.spice", out / "fabric.spice")
    shutil.copyfile(c250 / "model_hashes.json", out / "model_hashes.json")
    (out / "binding.spice").write_text(candidate)
    (out / "bench.spice").write_text(new_bench)
    (out / "buf_1.spice").write_text(buf + "\n")
    (out / "map.json").write_text(json.dumps(probe_map, indent=2) + "\n")
    for name, before, after in (("binding", original, candidate), ("bench", old_bench, new_bench)):
        (out / f"{name}.diff").write_text("".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True), fromfile=f"v6/{name}.spice", tofile=f"virtual_8_strongarm/{name}.spice")))

    audit = {
        "verdict": "VIRTUAL_ECO_READY",
        "corner": corner,
        "scope": "preflight only; no ngspice simulation, layout edit, extraction update, or signoff",
        "lane_ids": list(LANES),
        "native_mos_removed": {str(bit): {name: original_cards[name] for name in LANES[bit]["removed"]} for bit in LANES},
        "added_device_count": {"strongarm_mos": 55, "buf_1_instances": 10, "buf_1_mos_each": 4, "net_mos_delta": 60},
        "added_instances": added,
        "all_unchanged_cards_byte_identical": True,
        "all_extracted_rc_cards_byte_identical_and_ordered": True,
        "probes_added": {"voltage": new_voltage_probes, "current": new_current_probes},
        "source_proof": {"v6_pex_sha256": sha(pex), "v6_binding_sha256": sha(c250 / "binding.spice"), "c250_manifest_sha256": sha(c250 / "preflight.json"), "strongarm_cell_source_sha256": sha(triple / "fabric_reference.spice")},
        "physical_boundary": "original v6 PEX only; added MOS parasitics are not extracted",
        "captured_fixture": {k: manifest[k] for k in ("stop_ns", "max_step_ps", "nominal_v", "temp_c")},
    }
    (out / "eco_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    preflight_files = ("bench.spice", "binding.spice", "buf_1.spice", "fabric.spice", "model_hashes.json", "map.json")
    preflight = {"gate": "READY", "topology": "VIRTUAL_ECO_READY", "corner": corner, "stop_ns": 250, "temperature_c": 27, "nominal_v": 1.8, "temp_c": 27, "max_step_ps": 25, "outputs": {n: sha(out / n) for n in preflight_files}}
    (out / "preflight.json").write_text(json.dumps(preflight, indent=2) + "\n")
    print(json.dumps({"output": str(out), "verdict": audit["verdict"], "corner": corner, "removed_mos": len(removed), "added_core_mos": 55, "added_buf_instances": 10, "net_mos_delta": 60, "rc_cards_preserved": len(original_passives), "preflight": preflight}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, default=DEFAULT_CHECKOUT, help="restored historical artifact checkout")
    parser.add_argument("--output", type=Path, required=True, help="new, nonexistent output directory")
    parser.add_argument("--corner", choices=("tt", "ss", "ff"), default="tt")
    args = parser.parse_args()
    prepare(args.checkout.resolve(), args.output.resolve(), args.corner)


if __name__ == "__main__":
    main()
