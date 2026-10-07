#!/usr/bin/env python3
"""Generate, route, and check the SKY130A layout of the dynamic row decoder.

Run inside the project EDA container:
    ./tools/sram-eda python3 layout/row_decoder/build_layout.py

The script reads the canonical Xschem schematic. It does not edit the schematic.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LAYOUT = ROOT / "layout" / "row_decoder"
SCHEMATIC = ROOT / "cells" / "row_decoder" / "row_decoder.sch"
MAGIC_RC = Path("/opt/pdks/sky130A/libs.tech/magic/sky130A.magicrc")
EXPECTED_PINS = ("VDD", "PCLK", "A0", "A1", "DEC0", "DEC1", "DEC3", "DEC2", "VSS")
PORT_INDEX = {name: index for index, name in enumerate(EXPECTED_PINS)}
DEVICE_RE = re.compile(r"^(XM\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(sky130_fd_pr__(?:p|n)fet_01v8)\b", re.I)
RECT_RE = re.compile(r"^rect\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*$")


@dataclass(frozen=True)
class Device:
    name: str
    drain: str
    gate: str
    source: str
    bulk: str
    model: str


@dataclass(frozen=True)
class Geometry:
    drain_x: int
    drain_y: int
    gate_contacts: tuple[tuple[int, int], ...]
    source_x: int
    source_y: int
    bulk_x: int
    bulk_y: int


def run_checked(command: list[str], *, cwd: Path, log: Path, input_text: str | None = None) -> str:
    result = subprocess.run(command, cwd=cwd, input=input_text, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"Command returned {result.returncode}: {' '.join(command)}\nSee {log}")
    return result.stdout


def xschem_netlist() -> tuple[Path, list[Device]]:
    outdir = LAYOUT / "netlist"
    outdir.mkdir(parents=True, exist_ok=True)
    pdk_xschem = Path("/opt/pdks/sky130A/libs.tech/xschem")
    library_paths = [
        '"$XSCHEM_SHAREDIR/xschem_library"',
        '"$XSCHEM_SHAREDIR/xschem_library/devices"',
        f'"{pdk_xschem}"',
        f'"{ROOT / "cells/row_decoder"}"',
    ]
    tcl = "set XSCHEM_LIBRARY_PATH [join [list " + " ".join(library_paths) + '] ":"]'
    run_checked(
        ["xschem", "-x", "-q", "-n", "--tcl", tcl, "-o", str(outdir), str(SCHEMATIC)],
        cwd=ROOT, log=outdir / "xschem.log",
    )
    path = outdir / "row_decoder.spice"
    if not path.is_file():
        raise RuntimeError(f"Xschem did not generate {path}")
    text = path.read_text(encoding="utf-8")
    header = re.search(r"(?m)^\*\*\.subckt\s+row_decoder\s+(.+)$", text)
    if not header or tuple(header.group(1).split()) != EXPECTED_PINS:
        actual = header.group(1).split() if header else "missing subcircuit header"
        raise RuntimeError(f"Unexpected decoder pin order: {actual}")
    devices = parse_devices(text)
    if {d.name for d in devices} != {f"XM{i}" for i in range(1, 30)}:
        raise RuntimeError("Expected exactly 29 decoder MOS devices, XM1..XM29")
    if sum("pfet" in d.model.lower() for d in devices) != 12:
        raise RuntimeError("Unexpected PFET count; expected 12 PMOS devices")
    if sum("nfet" in d.model.lower() for d in devices) != 17:
        raise RuntimeError("Unexpected NFET count; expected 17 NMOS devices")
    return path, devices


def parse_devices(text: str) -> list[Device]:
    merged: list[str] = []
    for line in text.splitlines():
        if line.startswith("+") and merged:
            merged[-1] += " " + line[1:].strip()
        elif line.startswith("XM"):
            merged.append(line)
    devices: list[Device] = []
    for line in merged:
        match = DEVICE_RE.match(line)
        if not match:
            raise RuntimeError(f"Cannot parse MOS line: {line}")
        devices.append(Device(*match.groups()))
    return devices


def write_import_alias(source: Path) -> None:
    lines = source.read_text(encoding="utf-8").splitlines()
    body: list[str] = []
    for line in lines:
        if line.startswith("XM") or line.startswith("+"):
            body.append(line)
    alias = ("* Generated from cells/row_decoder/row_decoder.sch by Xschem.\n"
             + ".subckt row_decoder_sram6t " + " ".join(EXPECTED_PINS) + "\n"
             + "\n".join(body) + "\n.ends row_decoder_sram6t\n")
    (LAYOUT / "row_decoder_import.spice").write_text(alias, encoding="utf-8")


def parse_mag_sections(path: Path) -> dict[str, list[tuple[int, int, int, int]]]:
    sections: dict[str, list[tuple[int, int, int, int]]] = {}
    current: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("<< ") and line.endswith(" >>"):
            current = line[3:-3]
            sections.setdefault(current, [])
        elif current:
            match = RECT_RE.match(line)
            if match:
                sections[current].append(tuple(map(int, match.groups())))
    return sections


def center(rect: tuple[int, int, int, int]) -> tuple[int, int]:
    x1, y1, x2, y2 = rect
    return (x1 + x2) // 2, (y1 + y2) // 2


def device_geometry(child: Path, is_pfet: bool) -> Geometry:
    sections = parse_mag_sections(child)
    diffusion = [center(rect) for rect in sections.get("viali", [])]
    diffusion = [xy for xy in diffusion if abs(xy[0]) > 20 and abs(xy[1]) < 20]
    if len(diffusion) != 2:
        raise RuntimeError(f"Expected two horizontal diffusion contacts in {child}")
    drain = min(diffusion, key=lambda xy: xy[0])
    source = max(diffusion, key=lambda xy: xy[0])
    gate_rects = sections.get("polycont", [])
    if len(gate_rects) != 2:
        raise RuntimeError(f"Expected two gate contacts in {child}")
    gates = tuple(sorted((center(rect) for rect in gate_rects), key=lambda xy: xy[1], reverse=True))
    body_layer = "nsubdiffcont" if is_pfet else "psubdiffcont"
    body_rects = sections.get(body_layer, [])
    body_candidates = [center(rect) for rect in body_rects]
    body_candidates = [xy for xy in body_candidates if abs(xy[0]) < 20 and xy[1] > 0]
    if not body_candidates:
        raise RuntimeError(f"Missing centered upper body contact {body_layer} in {child}")
    bulk = max(body_candidates, key=lambda xy: xy[1])
    return Geometry(drain[0], drain[1], gates,
                    source[0], source[1], bulk[0], bulk[1])


def parse_instances(path: Path) -> dict[str, tuple[str, int, int]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    instances: dict[str, tuple[str, int, int]] = {}
    for i, line in enumerate(lines):
        match = re.match(r"use\s+(\S+)\s+(XM\d+)\s*$", line)
        if not match:
            continue
        child, instance = match.groups()
        transform = next((lines[j] for j in range(i + 1, min(i + 5, len(lines)))
                          if lines[j].startswith("transform ")), None)
        if not transform:
            raise RuntimeError(f"Missing transform for {instance} in {path}")
        values = [int(v) for v in transform.split()[1:]]
        if values != [1, 0, values[2], 0, 1, values[5]]:
            raise RuntimeError(f"Rotated PCell {instance} needs explicit terminal mapping")
        instances[instance] = (child, values[2], values[5])
    if set(instances) != {f"XM{i}" for i in range(1, 30)}:
        raise RuntimeError("Imported Magic top does not contain all 29 named devices")
    return instances


def ordered_nets(devices: list[Device]) -> list[str]:
    names = {net for d in devices for net in (d.drain, d.gate, d.source, d.bulk)}
    preferred = ["VDD", "VSS", "PCLK", "A0", "A1", "A0B", "A1B", "A0T", "A1T",
                 "N0", "N1", "N2", "N3", "net1", "net2", "net3", "net4",
                 "EVAL_GND", "DEC0", "DEC1", "DEC2", "DEC3"]
    if names != set(preferred):
        raise RuntimeError(f"Unexpected decoder net set: {sorted(names ^ set(preferred))}")
    return preferred


def generate_route_tcl(devices: list[Device]) -> None:
    import_mag = LAYOUT / "row_decoder_import.mag"
    instances = parse_instances(import_mag)
    net_order = ordered_nets(devices)
    track_y = {net: 6000 + i * 300 for i, net in enumerate(net_order)}
    track_xmin, track_xmax = 400, 44500
    pitch = 1500
    pmos_y, nmos_y = 2000, -2000

    rows = [
        "load row_decoder_import",
        "save row_decoder_placed",
        "snap internal",
        "",
        "proc move_inst_to {name dx dy} {",
        "    select clear",
        "    select cell $name",
        "    if {$dx > 0} { move e $dx }",
        "    if {$dx < 0} { move w [expr {-$dx}] }",
        "    if {$dy > 0} { move n $dy }",
        "    if {$dy < 0} { move s [expr {-$dy}] }",
        "    select clear",
        "}",
        "",
    ]
    for i in range(1, 30):
        name = f"XM{i}"
        _, old_x, old_y = instances[name]
        target_x = 1500 + (i - 1) * pitch
        is_pfet = "pfet" in next(d.model for d in devices if d.name == name).lower()
        target_y = pmos_y if is_pfet else nmos_y
        rows.append(f"move_inst_to {name} {target_x - old_x} {target_y - old_y}")
    rows += [
        "",
        "# Remove the M1 placeholders that Magic creates for top-level pins.",
        "box values -10 -3300 210 210",
        "select do labels",
        "select area metal1",
        "delete",
        "select clear",
        "select no labels",
        "",
        "proc m3_track {y} {",
        "    box values 400 [expr {$y - 30}] 44500 [expr {$y + 30}]",
        "    paint metal3",
        "}",
        "",
        "proc terminal_to_m3 {tx ty vx track {create_m3_via 1}} {",
        "    set xlo [expr {min($tx, $vx) - 20}]",
        "    set xhi [expr {max($tx, $vx) + 20}]",
        "    box values $xlo [expr {$ty - 20}] $xhi [expr {$ty + 20}]",
        "    paint metal1",
        "    set vxlo [expr {$vx - 30}]",
        "    set vxhi [expr {$vx + 30}]",
        "    set tylo [expr {$ty - 30}]",
        "    set tyhi [expr {$ty + 30}]",
        "    box values [expr {$vx - 40}] [expr {$ty - 40}] [expr {$vx + 40}] [expr {$ty + 40}]",
        "    paint metal1",
        "    paint metal2",
        "    box values $vxlo $tylo $vxhi $tyhi",
        "    contact m2contact",
        "    set ylo [expr {min($ty, $track) - 30}]",
        "    set yhi [expr {max($ty, $track) + 30}]",
        "    box values $vxlo $ylo $vxhi $yhi",
        "    paint metal2",
        "    if {$create_m3_via} {",
        "        box values $vxlo [expr {$track - 30}] $vxhi [expr {$track + 30}]",
        "        contact m3contact",
        "        box values [expr {$vx - 42}] [expr {$track - 42}] [expr {$vx + 42}] [expr {$track + 42}]",
        "        paint metal2",
        "        box values [expr {$vx - 36}] [expr {$track - 36}] [expr {$vx + 36}] [expr {$track + 36}]",
        "        paint metal3",
        "    }",
        "}",
        "",
        "proc body_to_m3 {gx gy mx vx track} {",
        "    set xlo [expr {min($gx, $mx) - 20}]",
        "    set xhi [expr {max($gx, $mx) + 20}]",
        "    box values $xlo [expr {$gy - 20}] $xhi [expr {$gy + 20}]",
        "    paint locali",
        "    set mxlo [expr {$mx - 30}]",
        "    set mxhi [expr {$mx + 30}]",
        "    box values $mxlo [expr {$gy - 30}] $mxhi [expr {$gy + 30}]",
        "    paint locali",
        "    box values [expr {$mx - 50}] [expr {$gy - 50}] [expr {$mx + 50}] [expr {$gy + 50}]",
        "    paint metal1",
        "    box values $mxlo [expr {$gy - 30}] $mxhi [expr {$gy + 30}]",
        "    contact mcon",
        "    terminal_to_m3 $mx $gy $vx $track",
        "}",
        "",
    ]
    for net in net_order:
        rows.append(f"m3_track {track_y[net]}")
    rows.append("")

    for device in devices:
        name = device.name
        child, inst_x, inst_y = instances[name]
        is_pfet = "pfet" in device.model.lower()
        geometry = device_geometry(LAYOUT / f"{child}.mag", is_pfet)
        # The placed cell transform is known from the target placement above.
        x = 1500 + (int(name[2:]) - 1) * pitch
        y = pmos_y if is_pfet else nmos_y
        tracks = track_y
        rows.append(f"# {name}: D={device.drain}, G={device.gate}, S={device.source}, B={device.bulk}")
        rows.append(f"terminal_to_m3 {x + geometry.drain_x} {y + geometry.drain_y} {x - 300} {tracks[device.drain]}")
        # The SKY130 Magic MOS PCell exposes gate contacts on both sides. Route
        # both to the same gate net so no small floating metal landing remains.
        # Keep the M1-to-M2 landing beyond the adjacent diffusion contacts.
        for gate_index, (gate_x, gate_y) in enumerate(geometry.gate_contacts):
            make_m3_via = 1 if gate_index == 0 else 0
            rows.append(
                f"terminal_to_m3 {x + gate_x} {y + gate_y} {x + 150} "
                f"{tracks[device.gate]} {make_m3_via}"
            )
        rows.append(f"terminal_to_m3 {x + geometry.source_x} {y + geometry.source_y} {x + 300} {tracks[device.source]}")
        # Keep the mcon outside the PCell's substrate/well tap footprint; the
        # LI route joins the tap to this offset via, as in the peripheral flows.
        rows.append(f"body_to_m3 {x + geometry.bulk_x} {y + geometry.bulk_y} {x + 500} {x + 560} {tracks[device.bulk]}")
        rows.append("")

    for net in net_order:
        y = track_y[net]
        if net in PORT_INDEX:
            rows += [
                f"box values 475 {y - 25} 525 {y + 25}",
                f"label {net} center metal3",
                "select clear",
                "select do labels",
                "select area metal3",
                f"port make {PORT_INDEX[net]} n",
                "select clear",
                "select no labels",
            ]
        else:
            rows += [
                f"box values 44350 {y - 25} 44400 {y + 25}",
                f"label {net} center metal3",
                "select clear",
                "select no labels",
            ]
    rows += [
        "",
        "select top cell",
        "drc style drc(full)",
        "drc check",
        "drc catchup",
        "drc count total",
        "save row_decoder_layout",
        "quit -noprompt",
        "",
    ]
    (LAYOUT / "route_row_decoder.tcl").write_text("\n".join(rows), encoding="utf-8")


def magic(script_name: str, log_name: str) -> str:
    script = (LAYOUT / script_name).read_text(encoding="utf-8")
    return run_checked(
        ["magic", "-dnull", "-noconsole", "-rcfile", str(MAGIC_RC)],
        cwd=LAYOUT, log=LAYOUT / "reports" / log_name, input_text=script,
    )


def flatten_script() -> None:
    script = "\n".join([
        "load row_decoder_layout",
        "save row_decoder_routed_hier",
        "flatten row_decoder_flat",
        "load row_decoder_flat",
        "select top cell",
        "drc style drc(full)",
        "drc check",
        "drc catchup",
        "drc count total",
        "save row_decoder_flat",
        "quit -noprompt",
        "",
    ])
    (LAYOUT / "flatten_for_check.tcl").write_text(script, encoding="utf-8")


def extraction_script() -> None:
    (LAYOUT / "extract_layout.tcl").write_text("\n".join([
        "load row_decoder_flat",
        "select top cell",
        "extract do local",
        "extract all",
        # Magic 8.3.589 uses the legacy extresist flow: generate the labeled
        # .sim/.nodes database for the currently loaded cell before extresist.
        "ext2sim labels on",
        "ext2sim",
        "extresist",
        "ext2spice lvs",
        "ext2spice -o row_decoder_flat_extracted.spice",
        "ext2spice default",
        "ext2spice extresist on",
        "ext2spice cthresh 0",
        "ext2spice rthresh 0",
        "ext2spice -o pex/row_decoder_pex.spice",
        "quit -noprompt",
        "",
    ]), encoding="utf-8")


def run_netgen_lvs() -> str:
    command = [
        "netgen", "-batch", "lvs",
        "layout/row_decoder/row_decoder_flat_extracted.spice row_decoder_flat",
        "layout/row_decoder/row_decoder_import.spice row_decoder_sram6t",
        "/opt/pdks/sky130A/libs.tech/netgen/setup.tcl",
        "layout/row_decoder/reports/lvs.out",
    ]
    lvs_log = run_checked(command, cwd=ROOT, log=LAYOUT / "reports" / "lvs.log")
    report = (LAYOUT / "reports" / "lvs.out").read_text(encoding="utf-8")
    if "Circuits match uniquely" not in lvs_log + report:
        raise RuntimeError("Netgen LVS did not report a unique match; inspect reports/lvs.log and lvs.out")
    return lvs_log


def run_lvs_only() -> str:
    """Extract connectivity from the current flat layout and run LVS, without RC PEX."""
    script = "\n".join([
        "load row_decoder_flat",
        "select top cell",
        "extract do local",
        "extract all",
        "ext2spice lvs",
        "ext2spice -o row_decoder_flat_extracted.spice",
        "quit -noprompt",
        "",
    ])
    run_checked(
        ["magic", "-dnull", "-noconsole", "-rcfile", str(MAGIC_RC)],
        cwd=LAYOUT, log=LAYOUT / "reports" / "lvs_extract.log", input_text=script,
    )
    extracted_path = LAYOUT / "row_decoder_flat_extracted.spice"
    spice = extracted_path.read_text(encoding="utf-8").rstrip() + "\n"
    extracted_path.write_text(spice, encoding="utf-8")
    devices = [line for line in spice.splitlines() if re.match(r"^X\S+\s", line)]
    if len(devices) != 29:
        raise RuntimeError(f"Magic connectivity extraction found {len(devices)} MOS devices; expected 29")
    if re.search(r"(?m)^[RC]\S+\s", spice):
        raise RuntimeError("LVS-only extraction unexpectedly contains parasitic R or C elements")
    header = re.search(r"(?m)^\.subckt\s+row_decoder_flat\s+(.+)$", spice)
    if not header or tuple(header.group(1).split()) != EXPECTED_PINS:
        raise RuntimeError("Magic LVS extraction changed the decoder external pin order")
    return run_netgen_lvs()


def run_extraction_and_lvs() -> tuple[str, str]:
    (LAYOUT / "pex").mkdir(exist_ok=True)
    extraction_script()
    magic("extract_layout.tcl", "extract.log")
    spice = (LAYOUT / "row_decoder_flat_extracted.spice").read_text(encoding="utf-8")
    devices = [line for line in spice.splitlines() if re.match(r"^X\S+\s", line)]
    if len(devices) != 29:
        raise RuntimeError(f"Magic extraction found {len(devices)} MOS devices; expected 29")
    if re.search(r"(?m)^X\S+\s+.*\s+(?:a_|w_)\S*#\s+sky130_fd_pr__", spice):
        raise RuntimeError("Magic extraction left one or more MOS body terminals floating")
    pex = (LAYOUT / "pex" / "row_decoder_pex.spice").read_text(encoding="utf-8")
    if not re.search(r"(?m)^\.subckt\s+row_decoder_flat\s+" + r"\s+".join(EXPECTED_PINS) + r"$", pex):
        raise RuntimeError("PEX subcircuit does not preserve the Xschem external pin order")
    if not re.search(r"(?m)^R\d+\s", pex) or not re.search(r"(?m)^C\d+\s", pex):
        raise RuntimeError("Magic PEX netlist is missing extracted R or C elements")
    lvs_log = run_netgen_lvs()
    return lvs_log, pex


def drc_count(log: str) -> int:
    matches = re.findall(r"Total DRC errors found:\s*(\d+)", log)
    if not matches:
        raise RuntimeError("Magic output did not contain a DRC total")
    return int(matches[-1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-import", action="store_true",
                        help="Reuse the existing Magic import and generated PCells.")
    parser.add_argument("--skip-route", action="store_true",
                        help="Only regenerate the Xschem netlist and Magic import.")
    parser.add_argument("--extract", action="store_true",
                        help="After zero-error DRC, extract RC and run Netgen LVS.")
    parser.add_argument("--lvs-only", action="store_true",
                        help="After zero-error DRC, extract connectivity and run Netgen LVS without RC PEX.")
    args = parser.parse_args()
    if args.extract and args.lvs_only:
        parser.error("--extract and --lvs-only are mutually exclusive")
    if args.skip_route and (args.extract or args.lvs_only):
        parser.error("--extract and --lvs-only require the routed layout and DRC checks")
    LAYOUT.mkdir(parents=True, exist_ok=True)
    netlist_path, devices = xschem_netlist()
    write_import_alias(netlist_path)
    if not args.skip_import:
        import_script = "\n".join([
            'set netlist "/work/layout/row_decoder/row_decoder_import.spice"',
            "load __row_decoder_import_scratch__",
            "magic::netlist_to_layout $netlist sky130",
            "set physical_top row_decoder_sram6t",
            "set physical_children [cellname list children $physical_top]",
            "puts \"ROWDEC_CHILDREN=$physical_children\"",
            "foreach child $physical_children { load $child; save $child }",
            "load $physical_top",
            "save row_decoder_import",
            "select top cell",
            "drc style drc(full)",
            "drc check",
            "drc catchup",
            "drc count total",
            "quit -noprompt",
            "",
        ])
        (LAYOUT / "generate_import.tcl").write_text(import_script, encoding="utf-8")
        magic("generate_import.tcl", "import.log")
    if args.skip_route:
        print(f"Generated Xschem netlist: {netlist_path}")
        print("Magic device import is saved under layout/row_decoder/")
        return 0
    generate_route_tcl(devices)
    route_log = magic("route_row_decoder.tcl", "route.log")
    flatten_script()
    flat_log = magic("flatten_for_check.tcl", "drc_flat.log")
    route_errors, flat_errors = drc_count(route_log), drc_count(flat_log)
    print(f"Xschem MOS: {len(devices)} (12 PFET, 17 NFET)")
    print(f"Magic DRC hierarchical/top: {route_errors}")
    print(f"Magic DRC flattened: {flat_errors}")
    print(f"Logs: {LAYOUT / 'reports'}")
    if route_errors or flat_errors:
        print("DRC is not closed; inspect reports and fix routing before extraction.")
        return 2
    print("DRC PASS")
    if args.lvs_only:
        lvs_log = run_lvs_only()
        spice = (LAYOUT / "row_decoder_flat_extracted.spice").read_text(encoding="utf-8")
        devices = [line for line in spice.splitlines() if re.match(r"^X\S+\s", line)]
        print(f"Magic connectivity extraction: {len(devices)} MOS devices; no RC PEX requested")
        print("Netgen LVS: Circuits match uniquely")
        print(f"Logs: {LAYOUT / 'reports' / 'lvs_extract.log'} and {LAYOUT / 'reports' / 'lvs.log'}")
        return 0
    if args.extract:
        lvs_log, pex = run_extraction_and_lvs()
        resistor_count = sum(1 for line in pex.splitlines() if re.match(r"^R\d+\s", line))
        capacitor_count = sum(1 for line in pex.splitlines() if re.match(r"^C\d+\s", line))
        print(f"Magic extraction: 29 devices; {resistor_count} resistors; {capacitor_count} capacitors")
        print("Netgen LVS: Circuits match uniquely")
        print(f"PEX: {LAYOUT / 'pex/row_decoder_pex.spice'}")
    else:
        print("Run with --lvs-only to recheck connectivity without RC PEX, or --extract for RC PEX and LVS.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
