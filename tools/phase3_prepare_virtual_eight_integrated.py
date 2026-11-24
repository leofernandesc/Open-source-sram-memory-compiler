#!/usr/bin/env python3
"""Prepare the archived 18-cycle integrated fixture for the virtual 8-sense ECO."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


CHECKOUT = Path("/tmp/phase3-v6-handoff-20261122/historical-checkout")
BASE = Path("build/phase3/strongarm_functional_closure_20261122/integrated/TT")
C250 = Path("build/phase3/strongarm_eight_virtual_20261123_retry1/TT")
OUT_ROOT = Path("build/phase3/strongarm_eight_integrated_20261124")
VIRTUAL_LANES = (0, 1, 2, 4, 5)
PHYSICAL_STRONGARM_LANES = (3, 6, 7)
PEX_SHA = "a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f"
GDS_SHA = "315c2ebceb2bc4cf258fa63be2279843805db3010637d0c273aea9db12813e37"
VEC = re.compile(r"^v\(xdut\.([^)]+)\)$", re.I)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def flatten(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from flatten(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from flatten(item)
    elif isinstance(value, str):
        yield value


def prepare(checkout: Path, corner: str) -> None:
    root = checkout
    base, c250 = root / BASE, root / C250
    out = root / OUT_ROOT / corner.upper()
    if out.exists():
        raise FileExistsError(f"refusing to overwrite {out}")
    base_pre = json.loads((base / "preflight.json").read_text())
    if base_pre["gate"] != "READY" or base_pre["physical_pex_sha256"] != PEX_SHA or base_pre["gds_sha256"] != GDS_SHA:
        raise ValueError("integrated fixture is not bound to the reviewed v6 PEX/GDS")
    for name, digest in base_pre["outputs"].items():
        if sha(base / name) != digest:
            raise ValueError(f"integrated source hash mismatch: {name}")
    c250_pre = json.loads((c250 / "preflight.json").read_text())
    if c250_pre["topology"] != "VIRTUAL_ECO_READY" or c250_pre["corner"] != "tt":
        raise ValueError("8-sense virtual TT gate is not ready")
    for name, digest in c250_pre["outputs"].items():
        if sha(c250 / name) != digest:
            raise ValueError(f"C250 candidate hash mismatch: {name}")

    probe_map = json.loads((c250 / "map.json").read_text())
    virtual_bits = {int(bit) for bit in probe_map.get("virtual_core_nodes", {})}
    if virtual_bits != set(VIRTUAL_LANES):
        raise ValueError(f"candidate virtual StrongARM lanes differ: {sorted(virtual_bits)}")
    internals = {"probes": probe_map["probes"]}
    probe_aliases = json.loads((base / "probes.json").read_text())
    columns = probe_map["probes"]["columns"]
    for bit in range(8):
        v = columns[str(bit)]["voltages"]
        alias = f"macro_core.array_and_peripherals.sense_amp_{bit}.SA_OUTB"
        # The integrated observer sees the sense output at the mux route. For
        # virtual lanes that is the buffer output (sab); the three physical
        # StrongARM lanes retain the archived core_sab observation.
        sense_vector = v["core_sab"] if bit in PHYSICAL_STRONGARM_LANES else v["sab"]
        probe_aliases[alias] = VEC.fullmatch(sense_vector)[1]
        probe_aliases[f"SCLK_SENSE_{bit}"] = VEC.fullmatch(v["sclk"])[1]
        for polarity in ("BL", "BLB"):
            alias = f"macro_core.array_and_peripherals.write_driver_{bit}.{polarity}"
            probe_aliases[alias] = VEC.fullmatch(v[polarity.lower()])[1]
    vectors = list(flatten(probe_map["probes"]))
    voltage_nodes = sorted({m[1] for vector in vectors if (m := VEC.fullmatch(vector))})
    voltage_nodes = sorted(set(voltage_nodes) | set(probe_aliases.values()))
    current_vectors = sorted({vector for vector in vectors if vector.startswith("@")})
    old_bench = (base / "bench.spice").read_text()
    old_wave, = [line for line in old_bench.splitlines() if line.startswith("wrdata waveform.dat ")]
    old_current, = [line for line in old_bench.splitlines() if line.startswith("wrdata currents.dat ")]
    wave_set, current_set = set(old_wave.split()[2:]), set(old_current.split()[2:])
    add_voltages = [f"v(xdut.{node})" for node in voltage_nodes if f"v(xdut.{node})" not in wave_set]
    add_currents = [vector for vector in current_vectors if vector not in current_set]
    if len(set(v.lower() for v in (*add_voltages, *add_currents))) != len(add_voltages) + len(add_currents):
        raise ValueError("duplicate supplemental integrated vector")

    candidate_bench = []
    for line in old_bench.splitlines():
        if line.startswith('.include "binding.spice"'):
            candidate_bench += [line, '.include "buf_1.spice"']
        elif line.startswith(".lib "):
            if not line.endswith(" tt"):
                raise ValueError("integrated reference bench is not TT")
            candidate_bench.append(line[:-2] + corner.lower())
        elif line.startswith(".save "):
            candidate_bench.append(line + " " + " ".join(add_voltages + add_currents))
        elif line.startswith("wrdata waveform.dat "):
            candidate_bench.append(line + " " + " ".join(add_voltages))
        elif line.startswith("wrdata currents.dat "):
            candidate_bench.append(line + " " + " ".join(add_currents))
        else:
            candidate_bench.append(line)
    bench = "\n".join(candidate_bench) + "\n"
    if [line for line in bench.splitlines() if line.startswith("tran ")] != ["tran 10p 370n 0 25p"]:
        raise ValueError("integrated 370 ns stimulus changed")
    if bench.count('.include "buf_1.spice"') != 1:
        raise ValueError("buf_1 include missing or duplicated")
    if sha(c250 / "binding.spice") == base_pre["outputs"]["binding.spice"]:
        raise ValueError("integrated candidate accidentally retained the baseline binding")

    out.mkdir(parents=True)
    (out / "bench.spice").write_text(bench)
    (out / "binding.spice").write_bytes((c250 / "binding.spice").read_bytes())
    (out / "buf_1.spice").write_bytes((c250 / "buf_1.spice").read_bytes())
    (out / "fabric.spice").write_bytes((base / "fabric.spice").read_bytes())
    (out / "model_hashes.json").write_bytes((base / "model_hashes.json").read_bytes())
    (out / "fixture.json").write_bytes((base / "fixture.json").read_bytes())
    (out / "probes.json").write_text(json.dumps(probe_aliases, indent=2) + "\n")
    internals["voltage_nodes"] = voltage_nodes
    (out / "internals.json").write_text(json.dumps(internals, indent=2) + "\n")
    outputs = ["bench.spice", "binding.spice", "buf_1.spice", "fabric.spice", "model_hashes.json", "fixture.json", "probes.json", "internals.json"]
    preflight = {
        "gate": "READY", "topology": "VIRTUAL_ECO_READY", "corner": corner.lower(),
        "guard_ns": base_pre["guard_ns"], "stop_ns": 370,
        "conditions": {**base_pre["conditions"], "corner": corner.lower()},
        "physical_pex_sha256": PEX_SHA, "gds_sha256": GDS_SHA,
        "historic_bench_sha256": sha(base / "bench.spice"),
        "c250_virtual_binding_sha256": sha(c250 / "binding.spice"),
        "outputs": {name: sha(out / name) for name in outputs},
    }
    (out / "preflight.json").write_text(json.dumps(preflight, indent=2) + "\n")
    audit = {
        "scope": "18-cycle integrated functional replay; virtual StrongARM MOS use v6 PEX RC envelope",
        "simulator_status": "NOT_RUN",
        "corner": corner.lower(), "cycles": len(json.loads((out / "fixture.json").read_text())["cycles"]),
        "voltage_nodes": len(voltage_nodes), "current_vectors": len(current_vectors),
        "new_saved_voltage_vectors": len(add_voltages), "new_saved_current_vectors": len(add_currents),
        "pex_sha256": PEX_SHA, "binding_sha256": sha(out / "binding.spice"),
        "fixture_sha256": sha(out / "fixture.json"), "preflight_outputs": preflight["outputs"],
        "electrical_qualification": "NOT_CHARACTERIZED",
    }
    (out / "eco_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps({"output": str(out), **audit}, indent=2))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkout", type=Path, default=CHECKOUT)
    p.add_argument("--corner", choices=("tt", "ss", "ff"), required=True)
    args = p.parse_args()
    prepare(args.checkout.resolve(), args.corner)


if __name__ == "__main__":
    main()
