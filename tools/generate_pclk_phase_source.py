#!/usr/bin/env python3
"""Generate the experimental Xschem 24/60/80 PCLK phase-source hierarchy.

The generator is intentionally limited to the new cells/control hierarchy. It
does not edit the existing decoder, precharge, wordline, or write-driver cells.
Run with --write to create/update the generated Xschem sources, or --check to
verify that the checked-in files match this generator.
"""

from __future__ import annotations

import argparse
import difflib
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "cells" / "control"
VERSION = "3.4.6"


def sch_head(title: str) -> list[str]:
    return [
        f"v {{xschem version={VERSION} file_version=1.2}}",
        "G {}",
        "K {}",
        "V {}",
        "S {}",
        "E {}",
        f"T {{{title}}} 100 -700 0 0 0.25 0.25 {{}}",
    ]


def wire(x1: int, y1: int, x2: int, y2: int, net: str) -> str:
    return f"N {x1} {y1} {x2} {y2} {{lab={net}}}"


def lab(x: int, y: int, signal: str, index: int, rotation: int = 0) -> str:
    return (f"C {{devices/lab_pin.sym}} {x} {y} {rotation} 0 "
            f"{{name=l{index} lab={signal}}}")


def pin(kind: str, x: int, y: int, signal: str, index: int,
        rotation: int = 0) -> str:
    return (f"C {{devices/{kind}.sym}} {x} {y} {rotation} 0 "
            f"{{name=p{index} lab={signal}}}")


def mos(kind: str, x: int, y: int, name: str, width: str) -> str:
    model = "pfet_01v8" if kind == "pfet" else "nfet_01v8"
    return (f"C {{sky130_fd_pr/{kind}_01v8.sym}} {x} {y} 0 0 "
            f"{{name={name} L=0.15 W={width} nf=1 model={model} spiceprefix=X}}")


def subckt_symbol(name: str, ports: list[tuple[str, str, int, int]],
                  width: int = 100, height: int = 100) -> str:
    """Make a symbol whose pin Y order matches the schematic's formal order."""
    lines = [
        f"v {{xschem version={VERSION} file_version=1.2}}",
        "K {type=subcircuit",
        'format="@name @pinlist @symname"',
        'template="name=x1"',
        "}",
        f"T {{{name}}} -55 -6 0 0 0.3 0.3 {{}}",
        "T {@name} 110 -45 0 0 0.2 0.2 {}",
        f"P 4 5 {-width} {-height} {-width} {height} {width} {height} {width} {-height} {-width} {-height} {{}}",
    ]
    for pname, direction, x, y in ports:
        lines.append(
            f"B 5 {x-2.5} {y-2.5} {x+2.5} {y+2.5} "
            f"{{name={pname} dir={direction}}}"
        )
        if x < 0:
            lines.append(f"L 4 {x} {y} {-width} {y} {{}}")
            lines.append(f"T {{{pname}}} {-width+5} {y-4} 0 0 0.2 0.2 {{}}")
        elif x > 0:
            lines.append(f"L 4 {width} {y} {x} {y} {{}}")
            lines.append(f"T {{{pname}}} {width-5} {y-4} 0 1 0.2 0.2 {{}}")
        else:
            lines.append(f"L 7 {x} {y} {x} {y + (10 if y < 0 else -10)} {{}}")
            if y < 0:
                lines.append(f"T {{{pname}}} {x+5} {y+4} 0 0 0.2 0.2 {{}}")
            else:
                lines.append(f"T {{{pname}}} {x+5} {y-14} 0 0 0.2 0.2 {{}}")
    return "\n".join(lines) + "\n"


def make_phase_delay_inv() -> tuple[str, str]:
    s = sch_head("SKY130A delay-chain inverter; experimental Wp=0.84 um, Wn=0.42 um")
    s += [
        wire(420, -190, 420, -160, "VDD"),
        wire(420, -130, 420, -30, "Y"),
        wire(420, 0, 420, 30, "VSS"),
        wire(280, -160, 280, 0, "A"),
        wire(280, -160, 380, -160, "A"),
        wire(280, 0, 380, 0, "A"),
        mos("pfet", 400, -160, "MP", "0.84"),
        mos("nfet", 400, 0, "MN", "0.42"),
        pin("ipin", 280, -80, "A", 1),
        pin("opin", 420, -80, "Y", 2),
        pin("iopin", 420, -190, "VDD", 3, 1),
        pin("iopin", 420, 30, "VSS", 4, 1),
    ]
    sym = subckt_symbol("phase_delay_inv", [
        ("VDD", "inout", 0, -30),
        ("A", "in", -50, 0),
        ("Y", "out", 50, 0),
        ("VSS", "inout", 0, 30),
    ], 40, 40)
    return "\n".join(s) + "\n", sym


def make_phase_and3() -> tuple[str, str]:
    s = sch_head("Three-input static CMOS AND; NAND3 followed by output inverter")
    # Parallel PMOS pull-up of the NAND3 stage, with local body ties to VDD.
    for idx, cy, label in (("A", -400, "A"), ("B", -320, "B"), ("C", -240, "C")):
        s += [
            wire(320, cy - 30, 320, cy, "VDD"),
            wire(320, cy + 30, 620, cy + 30, "NAND3"),
            wire(80, cy, 280, cy, label),
            mos("pfet", 300, cy, f"MP{idx}", "0.84"),
            lab(320, cy - 30, "VDD", len(s) + 10),
        ]
    s += [wire(620, -370, 620, -150, "NAND3")]
    # Series NMOS pull-down. Bulk terminals remain tied to VSS.
    for idx, cy, label in (("A", -120, "A"), ("B", -40, "B"), ("C", 40, "C")):
        s += [
            mos("nfet", 600, cy, f"MN{idx}", "0.42"),
            lab(620, cy, "VSS", len(s) + 20),
            lab(580, cy, label, len(s) + 21),
        ]
    s += [
        wire(620, -90, 620, -70, "STACK1"),
        wire(620, -10, 620, 10, "STACK2"),
        wire(620, 70, 620, 160, "VSS"),
        # Inverter producing AND3 from NAND3.
        wire(920, -90, 920, -60, "VDD"),
        wire(920, -30, 920, 70, "Y"),
        wire(920, 100, 920, 130, "VSS"),
        mos("pfet", 900, -60, "MPINV", "3.0"),
        mos("nfet", 900, 100, "MNINV", "1.5"),
        lab(620, -150, "NAND3", 200),
        lab(880, -60, "NAND3", 201),
        lab(880, 100, "NAND3", 202),
        lab(620, 70, "VSS", 203),
        lab(920, -90, "VDD", 204),
        pin("iopin", 320, -430, "VDD", 1, 1),
        pin("ipin", 80, -400, "A", 2),
        pin("ipin", 80, -320, "B", 3),
        pin("ipin", 80, -240, "C", 4),
        pin("opin", 920, 20, "Y", 5, 2),
        pin("iopin", 920, 130, "VSS", 6, 1),
    ]
    # The inter-device source/drain links are explicit below the device list.
    sym = subckt_symbol("phase_and3", [
        ("VDD", "inout", 0, -60),
        ("A", "in", -120, -40),
        ("B", "in", -120, -20),
        ("C", "in", -120, 0),
        ("Y", "out", 120, 20),
        ("VSS", "inout", 0, 40),
    ], 100, 50)
    return "\n".join(s) + "\n", sym


def make_phase_or2() -> tuple[str, str]:
    s = sch_head("Two-input static CMOS OR; NOR2 followed by output inverter")
    s += [
        # NOR pull-up: two PMOS in series.
        wire(320, -230, 320, -200, "VDD"),
        wire(320, -170, 320, -130, "PSTACK"),
        wire(320, -70, 620, -70, "NOR2"),
        wire(80, -200, 280, -200, "A"),
        wire(80, -100, 280, -100, "B"),
        mos("pfet", 300, -200, "MPA", "1.68"),
        mos("pfet", 300, -100, "MPB", "1.68"),
        lab(320, -230, "VDD", 10),
        lab(320, -100, "VDD", 11),
        # Parallel NMOS pull-down.
        wire(620, -70, 620, 110, "NOR2"),
        wire(320, 30, 620, 30, "NOR2"),
        wire(320, 110, 620, 110, "NOR2"),
        mos("nfet", 300, 60, "MNA", "0.42"),
        mos("nfet", 300, 140, "MNB", "0.42"),
        lab(320, 60, "VSS", 12),
        lab(320, 140, "VSS", 13),
        lab(280, 60, "A", 14),
        lab(280, 140, "B", 15),
        lab(320, 90, "VSS", 16),
        lab(320, 170, "VSS", 17),
        # Output inverter.
        wire(920, -90, 920, -60, "VDD"),
        wire(920, -30, 920, 70, "Y"),
        wire(920, 100, 920, 130, "VSS"),
        mos("pfet", 900, -60, "MPINV", "3.0"),
        mos("nfet", 900, 100, "MNINV", "1.5"),
        lab(620, -70, "NOR2", 200),
        lab(880, -60, "NOR2", 201),
        lab(880, 100, "NOR2", 202),
        lab(920, -90, "VDD", 203),
        pin("iopin", 320, -230, "VDD", 1, 1),
        pin("ipin", 80, -200, "A", 2),
        pin("ipin", 80, -100, "B", 3),
        pin("opin", 920, 20, "Y", 4, 2),
        pin("iopin", 920, 130, "VSS", 5, 1),
    ]
    sym = subckt_symbol("phase_or2", [
        ("VDD", "inout", 0, -60),
        ("A", "in", -120, -40),
        ("B", "in", -120, -20),
        ("Y", "out", 120, 0),
        ("VSS", "inout", 0, 20),
    ], 100, 40)
    return "\n".join(s) + "\n", sym


def make_pclk_phase_source() -> tuple[str, str]:
    s = sch_head("Experimental 24/60/80-tap non-overlap phase source; VALID_ACCESS_Q is captured upstream")
    count = 0
    first_center = 200
    spacing = 110
    for stage in range(1, 81):
        cx = first_center + (stage - 1) * spacing
        s.append(f"C {{phase_delay_inv.sym}} {cx} 0 0 0 {{name=XDL{stage:02d}}}")
        s.append(wire(cx, -30, cx, -120, "VDD"))
        s.append(wire(cx, 30, cx, 120, "VSS"))
        if stage < 80:
            out_x = cx + 50
            next_in_x = cx + spacing - 50
            net = f"DLY{stage}" if stage in (24, 60) else f"LINK{stage:02d}"
            s.append(wire(out_x, 0, next_in_x, 0, net))
            if stage in (24, 60):
                count += 1
                s.append(lab(out_x, 0, net, 1000 + count))
        else:
            s.append(wire(cx + 50, 0, cx + 90, 0, "DLY80"))
            s.append(lab(cx + 50, 0, "DLY80", 1003))

    last_cx = first_center + 79 * spacing
    s += [
        wire(first_center - 50, 0, first_center - 40, 0, "CLK"),
        wire(first_center - 50, -120, last_cx + 50, -120, "VDD"),
        wire(first_center - 50, 120, last_cx + 50, 120, "VSS"),
        # Exact logic of the screened transistor candidate:
        # CLK_RELEASED = CLK & DLY24
        # PRECH_SET = CLK_RELEASED | DLY80
        # PCLK = VALID_ACCESS_Q & CLK & DLY60
        # PRECH = VALID_ACCESS_Q & PRECH_SET
        "C {phase_and3.sym} 1300 500 0 0 {name=XREL}",
        "C {phase_or2.sym} 3300 600 0 0 {name=XOR1}",
        "C {phase_and3.sym} 5300 800 0 0 {name=XPCLK}",
        "C {phase_and3.sym} 7300 900 0 0 {name=XPRECH}",
        lab(1300, 440, "VDD", 1100),
        lab(1180, 460, "CLK", 1101),
        lab(1180, 480, "DLY24", 1102),
        lab(1180, 500, "VDD", 1103),
        lab(1420, 520, "CLK_RELEASED", 1104),
        lab(1300, 540, "VSS", 1105),
        lab(3300, 540, "VDD", 1110),
        lab(3180, 560, "CLK_RELEASED", 1111),
        lab(3180, 580, "DLY80", 1112),
        lab(3420, 600, "PRECH_SET", 1113),
        lab(3300, 620, "VSS", 1114),
        lab(5300, 740, "VDD", 1120),
        lab(5180, 760, "VALID_ACCESS_Q", 1121),
        lab(5180, 780, "CLK", 1122),
        lab(5180, 800, "DLY60", 1123),
        lab(5300, 840, "VSS", 1124),
        lab(7300, 840, "VDD", 1130),
        lab(7180, 860, "VALID_ACCESS_Q", 1131),
        lab(7180, 880, "PRECH_SET", 1132),
        lab(7180, 900, "VDD", 1133),
        lab(7300, 940, "VSS", 1134),
        pin("ipin", first_center - 50, 0, "CLK", 1),
        pin("iopin", first_center - 50, -120, "VDD", 2, 1),
        pin("iopin", first_center - 50, 120, "VSS", 3, 1),
        pin("ipin", 1000, 700, "VALID_ACCESS_Q", 4),
        pin("opin", 5420, 820, "PCLK", 5, 2),
        pin("opin", 7420, 920, "PRECH", 6, 2),
        "T {24 stages release precharge; 60 stages start evaluation; 80 stages delay reassertion after CLK falls.} 300 180 0 0 0.2 0.2 {}",
    ]
    sym = subckt_symbol("pclk_phase_source", [
        ("VDD", "inout", 0, -60),
        ("CLK", "in", -120, -40),
        ("VSS", "inout", 0, -20),
        ("VALID_ACCESS_Q", "in", -120, 0),
        ("PCLK", "out", 120, 20),
        ("PRECH", "out", 120, 40),
    ], 100, 50)
    return "\n".join(s) + "\n", sym


def generated_files() -> dict[Path, str]:
    result: dict[Path, str] = {}
    for name, fn in (
        ("phase_delay_inv", make_phase_delay_inv),
        ("phase_and3", make_phase_and3),
        ("phase_or2", make_phase_or2),
        ("pclk_phase_source", make_pclk_phase_source),
    ):
        schematic, symbol = fn()
        result[OUT / f"{name}.sch"] = schematic
        result[OUT / f"{name}.sym"] = symbol
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true", help="write the generated Xschem cells")
    action.add_argument("--check", action="store_true", help="check generated cells without changing them")
    args = parser.parse_args()
    mismatches = 0
    for path, expected in generated_files().items():
        actual = path.read_text(encoding="utf-8") if path.exists() else None
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")
            print(f"WROTE {path.relative_to(ROOT)}")
        elif actual != expected:
            mismatches += 1
            print(f"MISMATCH {path.relative_to(ROOT)}")
            print("".join(difflib.unified_diff(
                (actual or "").splitlines(keepends=True),
                expected.splitlines(keepends=True),
                fromfile=str(path), tofile="generated")))
    if args.check:
        if mismatches:
            return 1
        print("Xschem phase-source hierarchy matches generator.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
