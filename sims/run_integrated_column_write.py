#!/usr/bin/env python3
"""Integrated pre-layout SRAM write path using the canonical Xschem leaves."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import re
import subprocess
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from pex_access_nodes import bitcell_storage_nodes


MODEL_LIB = "/opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice"
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
MEASURE_RE = re.compile(
    rf"^\s*(?P<name>"
    rf"q_before|qb_before|t_wl_rise|t_wl_fall|bl_at_wl|blb_at_wl|"
    rf"t_q_full|t_qb_full|q_after|qb_after|bl_recovery|blb_recovery|"
    rf"bl_prech_on|blb_prech_on|t_prech_on50|t_bl_recovery|t_blb_recovery"
    rf")\s*=\s*(?P<value>{NUMBER})",
    re.MULTILINE,
)


LEAFS = {
    "bitcell": (
        "cells/bitcell_6t.sch",
        ("VDD", "BL", "BLB", "VSS", "WL"),
        {"XMPL", "XMNL", "XMPR", "XMNR", "XMAL", "XMAR"},
    ),
    "precharge": (
        "cells/precharge.sch",
        ("VDD", "BL", "BLB", "PRECH", "VSS"),
        {"XMPBL", "XMPBLB", "XMEQ"},
    ),
    "wl_driver": (
        "cells/wl_driver.sch",
        ("VDD", "VSS", "WL_IN", "WL"),
        {"XMP1", "XMN1", "XMP2", "XMN2"},
    ),
    "write_driver": (
        "cells/write_driver.sch",
        ("DATA", "DATA_B", "WE", "BL", "BLB", "VDD", "VSS"),
        {
            "XMPWEB", "XMNWEB", "XMPENBL", "XMPDBL", "XMNDBL", "XMNENBL",
            "XMPENBLB", "XMPDBLB", "XMNDBLB", "XMNENBLB",
        },
    ),
}


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corners", nargs="+", default=["tt", "ff", "ss", "fs", "sf"])
    p.add_argument("--vdd-values", nargs="+", type=float, default=[1.62, 1.80])
    p.add_argument("--temps-c", nargs="+", type=float, default=[-40.0, 27.0, 125.0])
    p.add_argument("--states", nargs="+", type=int, choices=[0, 1], default=[0, 1])
    p.add_argument("--wpu", type=float, default=0.42)
    p.add_argument("--wpd", type=float, default=1.26)
    p.add_argument("--wacc", type=float, default=0.60)
    p.add_argument(
        "--write-output-width-um",
        type=float,
        default=0.84,
        help=(
            "Override the eight BL/BLB output-stack transistor widths for sizing "
            "sweeps; the WE-to-WE_B inverter remains at its canonical 0.84 um."
        ),
    )
    p.add_argument(
        "--precharge-width-um",
        type=float,
        default=0.42,
        help="Override the three precharge/equalization PMOS widths for sizing sweeps.",
    )
    p.add_argument("--cbl-total-ff", type=float, default=65.0)
    p.add_argument("--cell-access-ceff-ff", type=float, default=0.452619)
    p.add_argument("--precharge-ceff-ff", type=float, default=0.908533)
    p.add_argument("--write-ceff-ff", type=float, default=4.033129)
    p.add_argument("--pex-cell-access-ceff-ff", type=float, default=8.592457068)
    p.add_argument("--pex-precharge-ceff-ff", type=float, default=6.525893794)
    p.add_argument("--pex-write-ceff-ff", type=float, default=26.721160015)
    p.add_argument(
        "--wl-extra-ff",
        type=float,
        default=17.0,
        help=(
            "Extra WL capacitance beyond the selected cell. The 17 fF default covers the "
            "measured 14-gate remainder plus the conservative pre-layout wire bound."
        ),
    )
    p.add_argument("--precharge-release-ns", type=float, default=2.0)
    p.add_argument("--we-at-ns", type=float, default=2.20)
    p.add_argument("--wl-in-at-ns", type=float, default=3.20)
    p.add_argument("--wl-in-width-ns", type=float, default=1.0)
    p.add_argument(
        "--precharge-recovery-window-ns",
        type=float,
        default=4.0,
        help="Observation window after precharge is re-enabled.",
    )
    p.add_argument("--edge-ps", type=float, default=50.0)
    p.add_argument("--tran-step-ps", type=float, default=10.0)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--timeout-s", type=float, default=90.0)
    p.add_argument("--pex", action="store_true", help="Use Magic RC-extracted leaf netlists.")
    p.add_argument(
        "--precharge-pex-netlist",
        type=Path,
        default=None,
        help="Optional precharge/equalization PEX override; implies PEX for all leaves.",
    )
    p.add_argument(
        "--write-pex-netlist",
        type=Path,
        default=None,
        help="Optional write-driver PEX override; implies PEX for all leaves.",
    )
    p.add_argument(
        "--wl-driver-pex-netlist",
        type=Path,
        default=None,
        help="Optional wordline-driver PEX override; implies PEX for all leaves.",
    )
    p.add_argument(
        "--resume",
        action="store_true",
        help="Reuse per-case part CSVs that already contain PASS.",
    )
    p.add_argument(
        "--parts-dir",
        type=Path,
        default=root / "sims" / "integrated_column_write_65ff_parts",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=root / "sims" / "integrated_column_write_65ff_pvt.csv",
    )
    p.add_argument("--root", type=Path, default=root)
    return p.parse_args()


def part_path(args: argparse.Namespace, row_or_case: object) -> Path:
    if isinstance(row_or_case, dict):
        corner = str(row_or_case["corner"])
        vdd = float(row_or_case["vdd_v"])
        temp_c = float(row_or_case["temp_c"])
        state = int(row_or_case["stored_q_before"])
    else:
        corner, vdd, temp_c, state = row_or_case  # type: ignore[misc]
    stem = f"{corner}_{vdd:g}V_{temp_c:g}C_q{state}"
    return args.parts_dir / f"integrated_write_{stem}.csv"


def read_part(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8") as stream:
        return next(csv.DictReader(stream), None)


def write_part(path: Path, row: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row), lineterminator="\n")
        writer.writeheader()
        writer.writerow(row)


def extract_leaf(root: Path, key: str) -> str:
    rel, pins, expected_devices = LEAFS[key]
    schematic = (root / rel).resolve()
    static_spice = root / "cells" / f"{schematic.stem}.spice"
    if static_spice.exists():
        text = static_spice.read_text(encoding="utf-8")
        match = re.search(r"^\.subckt\s+(\S+)\s+(.+)$", text, re.MULTILINE)
        if not match:
            raise RuntimeError(f"missing subcircuit header in {static_spice}")
        if set(match.group(2).split()) != set(pins):
            raise RuntimeError(f"unexpected {key} pin set in {static_spice}: {match.group(2)}")
        body = [
            line for line in text.splitlines()
            if line.startswith("X")
        ]
        if len(body) != len(expected_devices):
            raise RuntimeError(
                f"unexpected {key} device count in {static_spice}: "
                f"got {len(body)}, expected {len(expected_devices)}"
            )
        return (
            f".subckt {key}_core {' '.join(pins)}\n"
            + "\n".join(body)
            + f"\n.ends {key}_core\n"
        )
    with tempfile.TemporaryDirectory(prefix=f"{key}-xschem-") as td:
        result = subprocess.run(
            ["xschem", "-x", "-q", "-n", "-o", td, str(schematic)],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        netlist = Path(td) / f"{schematic.stem}.spice"
        if result.returncode != 0 or not netlist.exists():
            raise RuntimeError(
                f"Xschem netlist failed for {schematic}:\n{result.stdout}\n{result.stderr}"
            )
        lines = netlist.read_text(encoding="utf-8").splitlines()

    header = next((line for line in lines if line.startswith("**.subckt ")), "")
    if set(header.split()[2:]) != set(pins):
        raise RuntimeError(f"unexpected {key} pin set: {header}")
    body = [line for line in lines if line.startswith(("X", "+"))]
    devices = {line.split()[0] for line in body if line.startswith("X")}
    if devices != expected_devices:
        raise RuntimeError(
            f"unexpected {key} devices: got {sorted(devices)}, expected {sorted(expected_devices)}"
        )
    unnamed_nets = Counter(re.findall(r"\bnet\d+\b", "\n".join(body)))
    dangling_nets = sorted(net for net, count in unnamed_nets.items() if count < 2)
    if dangling_nets:
        raise RuntimeError(f"unexpected unnamed/open net in {key}: {dangling_nets}")
    return (
        f".subckt {key}_core {' '.join(pins)}\n"
        + "\n".join(body)
        + f"\n.ends {key}_core\n"
    )


def override_write_output_width(subckt: str, width_um: float) -> str:
    if width_um <= 0:
        raise ValueError("write-driver output width must be positive")
    lines = []
    changed = 0
    for line in subckt.splitlines():
        device = line.split(maxsplit=1)[0] if line.startswith("X") else ""
        if device not in {"XMPWEB", "XMNWEB", ""}:
            line, count = re.subn(
                r"\b[wW]=[^\s]+", f"w={width_um:g}", line, count=1
            )
            changed += count
        lines.append(line)
    if changed != 8:
        raise RuntimeError(
            f"expected to override 8 write-driver output widths, changed {changed}"
        )
    return "\n".join(lines) + "\n"


def override_precharge_width(subckt: str, width_um: float) -> str:
    if width_um <= 0:
        raise ValueError("precharge width must be positive")
    lines = []
    changed = 0
    for line in subckt.splitlines():
        device = line.split(maxsplit=1)[0] if line.startswith("X") else ""
        if device in {"XMPBL", "XMPBLB", "XMEQ"}:
            line, count = re.subn(
                r"\b[wW]=[^\s]+", f"w={width_um:g}", line, count=1
            )
            changed += count
        lines.append(line)
    if changed != 3:
        raise RuntimeError(f"expected to override 3 precharge widths, changed {changed}")
    return "\n".join(lines) + "\n"


def pex_leaf(
    root: Path,
    key: str,
    precharge_override: Path | None = None,
    write_override: Path | None = None,
    wl_driver_override: Path | None = None,
) -> str:
    pex_paths = {
        "bitcell": root / "layout" / "bitcell_6t" / "pex" / "bitcell_6t_pex.spice",
        "precharge": (
            precharge_override.resolve()
            if precharge_override is not None
            else root / "layout" / "precharge" / "pex" / "precharge_pex.spice"
        ),
        "wl_driver": (
            wl_driver_override.resolve()
            if wl_driver_override is not None
            else root / "layout" / "wl_driver" / "pex" / "wl_driver_pex.spice"
        ),
        "write_driver": (
            write_override.resolve()
            if write_override is not None
            else root / "layout" / "write_driver" / "pex" / "write_driver_pex.spice"
        ),
    }
    expected_pex_pins = {
        "bitcell": ("VDD", "BL", "BLB", "VSS", "WL"),
        "precharge": ("VDD", "BL", "BLB", "PRECH", "VSS"),
        "wl_driver": ("VDD", "VSS", "WL_IN", "WL"),
        "write_driver": ("DATA", "DATA_B", "WE", "BL", "BLB", "VDD", "VSS"),
    }
    text = pex_paths[key].read_text(encoding="utf-8")
    match = re.search(r"^\.subckt\s+(\S+)\s+(.+)$", text, re.MULTILINE)
    if not match:
        raise RuntimeError(f"missing PEX subcircuit for {key}")
    pex_name = match.group(1)
    pex_pins = tuple(match.group(2).split())
    if pex_pins != expected_pex_pins[key]:
        raise RuntimeError(f"unexpected {key} PEX pins: {pex_pins}")
    canonical_pins = LEAFS[key][1]
    wrapper = (
        f".subckt {key}_core {' '.join(canonical_pins)}\n"
        f"XPEX {' '.join(pex_pins)} {pex_name}\n"
        f".ends {key}_core\n"
    )
    return text + "\n" + wrapper


def pex_source_paths(args: argparse.Namespace) -> dict[str, Path]:
    root = args.root.resolve()
    return {
        "bitcell": root / "layout/bitcell_6t/pex/bitcell_6t_pex.spice",
        "precharge": (
            args.precharge_pex_netlist.resolve()
            if args.precharge_pex_netlist is not None
            else root / "layout/precharge/pex/precharge_pex.spice"
        ),
        "wl_driver": (
            args.wl_driver_pex_netlist.resolve()
            if args.wl_driver_pex_netlist is not None
            else root / "layout/wl_driver/pex/wl_driver_pex.spice"
        ),
        "write_driver": (
            args.write_pex_netlist.resolve()
            if args.write_pex_netlist is not None
            else root / "layout/write_driver/pex/write_driver_pex.spice"
        ),
    }


def source_metadata(args: argparse.Namespace, key: str) -> tuple[str, str]:
    if args.pex:
        path = pex_source_paths(args)[key]
    else:
        path = (args.root / LEAFS[key][0]).resolve()
    return str(path), hashlib.sha256(path.read_bytes()).hexdigest()


def extracted_width_um(path: Path) -> float:
    widths = [
        float(value)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("X")
        for value in re.findall(r"\bw=([0-9.eE+-]+)", line, flags=re.IGNORECASE)
    ]
    if not widths:
        raise RuntimeError(f"no MOS widths found in {path}")
    return max(widths)


def make_deck(
    *, args: argparse.Namespace, leafs: dict[str, str], corner: str,
    vdd: float, temp_c: float, old_q: int,
) -> str:
    new_q = 1 - old_q
    edge_ns = args.edge_ps * 1e-3
    wl_in_off_ns = args.wl_in_at_ns + args.wl_in_width_ns
    we_off_ns = wl_in_off_ns + 0.50
    pre_reenable_ns = we_off_ns + 0.25
    stop_ns = pre_reenable_ns + args.precharge_recovery_window_ns

    # Total C_BL already includes the explicit selected-cell access, precharge,
    # and disabled write-driver output capacitances. The sense input and wire
    # remain in this lumped remainder because the sense leaf is not instantiated
    # in the write bench.
    explicit_ceff_ff = (
        args.pex_cell_access_ceff_ff
        + args.pex_precharge_ceff_ff
        + args.pex_write_ceff_ff
        if args.pex
        else args.cell_access_ceff_ff + args.precharge_ceff_ff + args.write_ceff_ff
    )
    lumped_extra_ff = args.cbl_total_ff - explicit_ceff_ff
    if lumped_extra_ff <= 0:
        raise ValueError("cbl-total-ff is smaller than the explicitly modeled leaf capacitance")

    q0 = vdd if old_q else 0.0
    qb0 = 0.0 if old_q else vdd
    if args.pex:
        q_node, qb_node = bitcell_storage_nodes(leafs["bitcell"])
        q_ref = f"v(xcell.xpex.{q_node})"
        qb_ref = f"v(xcell.xpex.{qb_node})"
    else:
        q_ref, qb_ref = "v(xcell.q)", "v(xcell.qb)"
    data = vdd if new_q else 0.0
    data_b = 0.0 if new_q else vdd
    q_crossing = "rise=1" if new_q else "fall=1"
    qb_crossing = "fall=1" if new_q else "rise=1"
    q_full = 0.9 * vdd if new_q else 0.1 * vdd
    qb_full = 0.1 * vdd if new_q else 0.9 * vdd
    wl_extra = (
        f"CWL_EXTRA wl 0 {args.wl_extra_ff:.9f}f"
        if args.wl_extra_ff > 0
        else "* no additional WL lumped capacitance"
    )

    return f"""* Integrated pre-layout SRAM column write.
* Canonical Xschem precharge, write driver, WL driver and bitcell leaves.
* Total C_BL={args.cbl_total_ff:g} fF; external remainder={lumped_extra_ff:.6f} fF.
.title integrated_column_write_{corner}_{vdd:g}V_{temp_c:g}C_q{old_q}
.lib "{MODEL_LIB}" {corner}
.temp {temp_c:g}
.param WPU={args.wpu:g} WPD={args.wpd:g} WACC={args.wacc:g}
{leafs["bitcell"]}
{leafs["precharge"]}
{leafs["wl_driver"]}
{leafs["write_driver"]}
VDD vdd 0 {vdd:g}
VDATA data 0 {data:.12g}
VDATAB data_b 0 {data_b:.12g}
VPRECH prech 0 PWL(0 0 {args.precharge_release_ns:g}n 0 {args.precharge_release_ns + edge_ns:g}n {vdd:g} {pre_reenable_ns:g}n {vdd:g} {pre_reenable_ns + edge_ns:g}n 0 {stop_ns:g}n 0)
VWE we 0 PWL(0 0 {args.we_at_ns:g}n 0 {args.we_at_ns + edge_ns:g}n {vdd:g} {we_off_ns:g}n {vdd:g} {we_off_ns + edge_ns:g}n 0 {stop_ns:g}n 0)
VWL_IN wl_in 0 PULSE(0 {vdd:g} {args.wl_in_at_ns:g}n {args.edge_ps:g}p {args.edge_ps:g}p {args.wl_in_width_ns:g}n {stop_ns + 10:g}n)
XPRE vdd bl blb prech 0 precharge_core
XWR data data_b we bl blb vdd 0 write_driver_core
XWL vdd 0 wl_in wl wl_driver_core
XCELL vdd bl blb 0 wl bitcell_core
CBL_EXTRA bl 0 {lumped_extra_ff:.6f}f
CBLB_EXTRA blb 0 {lumped_extra_ff:.6f}f
{wl_extra}
.ic {q_ref}={q0:.12g} {qb_ref}={qb0:.12g} v(bl)={vdd:.12g} v(blb)={vdd:.12g}
.options ngbehavior=ps method=gear reltol=1e-4 vabstol=1e-7 iabstol=1e-10
.tran {args.tran_step_ps:g}p {stop_ns:.12g}n 0 {args.tran_step_ps:g}p uic
.meas tran q_before find {q_ref} at={args.we_at_ns - 0.05:.12g}n
.meas tran qb_before find {qb_ref} at={args.we_at_ns - 0.05:.12g}n
.meas tran t_wl_rise when v(wl)={vdd/2:.12g} rise=1
.meas tran t_wl_fall when v(wl)={vdd/2:.12g} fall=1 td={wl_in_off_ns:.12g}n
.meas tran bl_at_wl find v(bl) when v(wl)={vdd/2:.12g} rise=1
.meas tran blb_at_wl find v(blb) when v(wl)={vdd/2:.12g} rise=1
.meas tran t_q_full when {q_ref}={q_full:.12g} {q_crossing} td={args.wl_in_at_ns:g}n
.meas tran t_qb_full when {qb_ref}={qb_full:.12g} {qb_crossing} td={args.wl_in_at_ns:g}n
.meas tran q_after find {q_ref} at={stop_ns - 0.1:.12g}n
.meas tran qb_after find {qb_ref} at={stop_ns - 0.1:.12g}n
.meas tran bl_recovery find v(bl) at={stop_ns - 0.1:.12g}n
.meas tran blb_recovery find v(blb) at={stop_ns - 0.1:.12g}n
.meas tran bl_prech_on find v(bl) at={pre_reenable_ns + edge_ns / 2.0:.12g}n
.meas tran blb_prech_on find v(blb) at={pre_reenable_ns + edge_ns / 2.0:.12g}n
.meas tran t_prech_on50 when v(prech)={vdd/2:.12g} fall=1 td={pre_reenable_ns:.12g}n
.meas tran t_bl_recovery when v(bl)={vdd-0.1:.12g} rise=1 td={pre_reenable_ns:.12g}n
.meas tran t_blb_recovery when v(blb)={vdd-0.1:.12g} rise=1 td={pre_reenable_ns:.12g}n
.control
run
quit
.endc
.end
"""


def run_case(
    *, args: argparse.Namespace, leafs: dict[str, str], corner: str,
    vdd: float, temp_c: float, old_q: int,
) -> dict[str, object]:
    deck_text = make_deck(
        args=args, leafs=leafs, corner=corner, vdd=vdd, temp_c=temp_c, old_q=old_q
    )
    with tempfile.TemporaryDirectory(prefix="integrated-write-") as td:
        deck = Path(td) / "integrated_write.spice"
        deck.write_text(deck_text, encoding="utf-8")
        try:
            result = subprocess.run(
                ["ngspice", "-n", "-b", str(deck)],
                cwd=td,
                text=True,
                capture_output=True,
                check=False,
                timeout=args.timeout_s,
            )
            rc = result.returncode
            output = result.stdout + "\n" + result.stderr
        except subprocess.TimeoutExpired as exc:
            rc = 124
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            output = stdout + "\n" + stderr

    m = {match.group("name"): float(match.group("value")) for match in MEASURE_RE.finditer(output)}
    required = {
        "q_before", "qb_before", "t_wl_rise", "t_wl_fall", "bl_at_wl", "blb_at_wl",
        "t_q_full", "t_qb_full", "q_after", "qb_after", "bl_recovery", "blb_recovery",
    }
    complete = rc == 0 and required <= m.keys()
    new_q = 1 - old_q
    if {"t_wl_rise", "t_wl_fall"} <= m.keys():
        wl_high_ns = (m["t_wl_fall"] - m["t_wl_rise"]) * 1e9
    else:
        wl_high_ns = None
    if {"t_q_full", "t_qb_full", "t_wl_rise"} <= m.keys():
        full_flip_s = max(m["t_q_full"], m["t_qb_full"])
        full_flip_ns = (full_flip_s - m["t_wl_rise"]) * 1e9
    else:
        full_flip_s = None
        full_flip_ns = None
    if full_flip_s is not None and "t_wl_fall" in m:
        margin_ns = (m["t_wl_fall"] - full_flip_s) * 1e9
    else:
        margin_ns = None
    if {"bl_at_wl", "blb_at_wl"} <= m.keys():
        bitlines_ready = (
            m["bl_at_wl"] >= 0.9 * vdd and m["blb_at_wl"] <= 0.1 * vdd
            if new_q else
            m["bl_at_wl"] <= 0.1 * vdd and m["blb_at_wl"] >= 0.9 * vdd
        )
    else:
        bitlines_ready = False
    if {"q_before", "qb_before"} <= m.keys():
        initialized = (
            m["q_before"] <= 0.1 * vdd and m["qb_before"] >= 0.9 * vdd
            if old_q == 0 else
            m["q_before"] >= 0.9 * vdd and m["qb_before"] <= 0.1 * vdd
        )
    else:
        initialized = False
    if {"q_after", "qb_after"} <= m.keys():
        final_ok = (
            m["q_after"] >= 0.9 * vdd and m["qb_after"] <= 0.1 * vdd
            if new_q else
            m["q_after"] <= 0.1 * vdd and m["qb_after"] >= 0.9 * vdd
        )
    else:
        final_ok = False
    if {"bl_recovery", "blb_recovery"} <= m.keys():
        recovered = m["bl_recovery"] >= vdd - 0.1 and m["blb_recovery"] >= vdd - 0.1
    else:
        recovered = False
    threshold = vdd - 0.1
    edge_ns = args.edge_ps * 1e-3
    wl_in_off_ns = args.wl_in_at_ns + args.wl_in_width_ns
    we_off_ns = wl_in_off_ns + 0.50
    pre_reenable_ns = we_off_ns + 0.25
    prech50_s = (pre_reenable_ns + edge_ns / 2.0) * 1e-9
    recovery_delays_ns: list[float] = []
    recovery_complete = True
    for prefix in ("bl", "blb"):
        initial = m.get(f"{prefix}_prech_on")
        crossing = m.get(f"t_{prefix}_recovery")
        if initial is None:
            recovery_complete = False
        elif initial >= threshold:
            recovery_delays_ns.append(0.0)
        elif crossing is not None:
            recovery_delays_ns.append((crossing - prech50_s) * 1e9)
        else:
            recovery_complete = False
    precharge_recovery_ns = (
        max(recovery_delays_ns)
        if recovery_complete and len(recovery_delays_ns) == 2
        else None
    )

    passed = bool(
        complete and initialized and bitlines_ready and full_flip_ns is not None
        and full_flip_ns >= 0.0 and margin_ns is not None and margin_ns >= 0.0
        and final_ok and recovered
    )
    if args.pex:
        pex_paths = pex_source_paths(args)
        wpre_um = extracted_width_um(pex_paths["precharge"])
        wwrite_out_um = extracted_width_um(pex_paths["write_driver"])
        explicit_leaf_ceff_ff = (
            args.pex_cell_access_ceff_ff
            + args.pex_precharge_ceff_ff
            + args.pex_write_ceff_ff
        )
    else:
        pex_paths = {}
        wpre_um = args.precharge_width_um
        wwrite_out_um = args.write_output_width_um
        explicit_leaf_ceff_ff = (
            args.cell_access_ceff_ff
            + args.precharge_ceff_ff
            + args.write_ceff_ff
        )
    source_fields = {
        "simulation_mode": "post_layout_pex" if args.pex else "schematic_screen"
    }
    for key in ("bitcell", "precharge", "wl_driver", "write_driver"):
        source, digest = source_metadata(args, key)
        source_fields[f"{key}_source"] = source
        source_fields[f"{key}_source_sha256"] = digest
    return {
        "corner": corner,
        "vdd_v": vdd,
        "temp_c": temp_c,
        "stored_q_before": old_q,
        "stored_q_after": new_q,
        "wpu_um": args.wpu,
        "wpd_um": args.wpd,
        "wacc_um": args.wacc,
        "wpre_um": wpre_um,
        "wwrite_out_um": wwrite_out_um,
        "cbl_total_ff": args.cbl_total_ff,
        "pex_cell_access_ceff_ff": args.pex_cell_access_ceff_ff if args.pex else args.cell_access_ceff_ff,
        "pex_precharge_ceff_ff": args.pex_precharge_ceff_ff if args.pex else args.precharge_ceff_ff,
        "pex_write_ceff_ff": args.pex_write_ceff_ff if args.pex else args.write_ceff_ff,
        "explicit_leaf_ceff_sum_ff": explicit_leaf_ceff_ff,
        "lumped_bitline_remainder_ff": args.cbl_total_ff - explicit_leaf_ceff_ff,
        "wl_extra_ff": args.wl_extra_ff,
        "wl_in_width_ns": args.wl_in_width_ns,
        "actual_wl_high_ns": "" if wl_high_ns is None else wl_high_ns,
        "full_flip_from_wl50_ns": "" if full_flip_ns is None else full_flip_ns,
        "full_flip_margin_to_wl_fall_ns": "" if margin_ns is None else margin_ns,
        "wl_min_30pct_ns": "" if full_flip_ns is None else 1.30 * full_flip_ns,
        "bl_at_wl_v": m.get("bl_at_wl", ""),
        "blb_at_wl_v": m.get("blb_at_wl", ""),
        "q_after_v": m.get("q_after", ""),
        "qb_after_v": m.get("qb_after", ""),
        "bl_recovery_v": m.get("bl_recovery", ""),
        "blb_recovery_v": m.get("blb_recovery", ""),
        "precharge_recovery_ns": (
            "" if precharge_recovery_ns is None else precharge_recovery_ns
        ),
        "status": "PASS" if passed else "FAIL",
        "returncode": rc,
        "error": "" if rc == 0 else output[-800:].replace("\n", " | "),
        **source_fields,
    }


def main() -> int:
    args = parse_args()
    if any(not 0.0 < v <= 1.8 for v in args.vdd_values):
        raise SystemExit("integrated qualification is limited to 1.62..1.80 V")
    if (
        args.workers < 1 or args.cbl_total_ff <= 0 or args.wl_extra_ff < 0
        or args.wl_in_width_ns <= 0 or args.tran_step_ps <= 0
        or args.precharge_recovery_window_ns <= 0
        or args.write_output_width_um <= 0
        or args.precharge_width_um <= 0
    ):
        raise SystemExit("invalid workers/capacitance/timing arguments")

    use_pex = (
        args.pex
        or args.precharge_pex_netlist is not None
        or args.write_pex_netlist is not None
        or args.wl_driver_pex_netlist is not None
    )
    args.pex = use_pex
    leafs = {
        key: (
            pex_leaf(
                args.root,
                key,
                args.precharge_pex_netlist,
                args.write_pex_netlist,
                args.wl_driver_pex_netlist,
            )
            if use_pex
            else extract_leaf(args.root, key)
        )
        for key in LEAFS
    }
    if not args.pex and args.write_output_width_um != 0.84:
        leafs["write_driver"] = override_write_output_width(
            leafs["write_driver"], args.write_output_width_um
        )
    if not args.pex and args.precharge_width_um != 0.42:
        leafs["precharge"] = override_precharge_width(
            leafs["precharge"], args.precharge_width_um
        )
    cases = list(itertools.product(args.corners, args.vdd_values, args.temps_c, args.states))
    rows: list[dict[str, object]] = []
    pending = []
    for case in cases:
        cached = read_part(part_path(args, case)) if args.resume else None
        if cached is not None and cached.get("status") == "PASS":
            rows.append(dict(cached))
        else:
            pending.append(case)
    if args.resume:
        print(
            f"resume: {len(rows)}/{len(cases)} PASS parts reused; "
            f"{len(pending)} cases pending",
            flush=True,
        )
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(
                run_case, args=args, leafs=leafs, corner=corner,
                vdd=vdd, temp_c=temp_c, old_q=state,
            )
            for corner, vdd, temp_c, state in pending
        ]
        for done, future in enumerate(as_completed(futures), start=1):
            row = future.result()
            rows.append(row)
            write_part(part_path(args, row), row)
            print(f"completed pending cases: {done}/{len(futures)}", flush=True)

    rows.sort(
        key=lambda r: (
            str(r["corner"]), float(r["vdd_v"]), float(r["temp_c"]),
            int(r["stored_q_before"]),
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    failures = [row for row in rows if row["status"] != "PASS"]
    print(f"integrated column write: {len(rows)-len(failures)}/{len(rows)} PASS")
    valid_flip = [
        float(r["full_flip_from_wl50_ns"])
        for r in rows if r["full_flip_from_wl50_ns"] != ""
    ]
    valid_margin = [
        float(r["full_flip_margin_to_wl_fall_ns"])
        for r in rows if r["full_flip_margin_to_wl_fall_ns"] != ""
    ]
    if valid_flip and valid_margin:
        worst = max(valid_flip)
        print(
            f"worst_full_flip_from_WL50={worst:.5f} ns "
            f"WL_min_30pct={1.30*worst:.5f} ns "
            f"min_margin_to_WL_fall={min(valid_margin):.5f} ns"
        )
    print(f"CSV: {args.output}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
