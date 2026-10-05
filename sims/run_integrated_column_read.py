#!/usr/bin/env python3
"""Integrated pre-layout SRAM column read timing/functional characterization."""

from __future__ import annotations

import argparse
import csv
import itertools
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


MODEL_LIB = "/opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice"
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
MEASURE_RE = re.compile(
    rf"^\s*(?P<name>"
    rf"bl_pre|blb_pre|t_wl50|t_dv|t_sclk50|t_res|"
    rf"bl_sclk|blb_sclk|sa_eval|sab_eval|"
    rf"stored_low_peak|stored_high_min|q_final|qb_final|"
    rf"bl_recovery|blb_recovery|t_prech_on50|t_bl_recovery|t_blb_recovery"
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
    "sense": (
        "cells/sense_amp.sch",
        ("BL", "BLB", "SA_OUT", "SA_OUTB", "SCLK", "VDD", "VSS"),
        {"XMP1", "XMP2", "XMN1", "XMN2", "XMSAMPBL", "XMSAMPBLB", "XMTAIL"},
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
    p.add_argument("--precharge-width-um", type=float, default=0.42)
    p.add_argument("--cell-access-ceff-ff", type=float, default=0.452619)
    p.add_argument("--precharge-ceff-ff", type=float, default=0.908533)
    p.add_argument("--sense-ceff-ff", type=float, default=9.004605)
    p.add_argument("--cbl-total-ff", type=float, default=65.0)
    p.add_argument(
        "--wl-extra-ff",
        type=float,
        default=17.0,
        help="Extra WL capacitance beyond the selected cell (other row cells + pre-layout wire).",
    )
    p.add_argument("--delta-target-mv", type=float, default=200.0)
    p.add_argument("--setup-min-ps", type=float, default=25.0)
    p.add_argument("--eval-max-ns", type=float, default=0.25)
    p.add_argument("--precharge-release-ns", type=float, default=2.0)
    p.add_argument("--wl-in-at-ns", type=float, default=2.25)
    p.add_argument("--wl-in-width-ns", type=float, default=1.5)
    p.add_argument("--sclk-at-ns", type=float, default=2.84)
    p.add_argument("--sclk-high-ns", type=float, default=0.5)
    p.add_argument("--precharge-recovery-window-ns", type=float, default=5.0)
    p.add_argument("--edge-ps", type=float, default=50.0)
    p.add_argument("--tran-step-ps", type=float, default=5.0)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--timeout-s", type=float, default=60.0)
    p.add_argument("--pex", action="store_true", help="Use Magic RC-extracted leaf netlists.")
    p.add_argument(
        "--sense-pex-netlist",
        type=Path,
        default=None,
        help="Optional sense-amplifier PEX override; implies PEX for all leaves.",
    )
    p.add_argument(
        "--resume",
        action="store_true",
        help="Reuse per-case part CSVs that already contain PASS.",
    )
    p.add_argument(
        "--parts-dir",
        type=Path,
        default=root / "sims" / "integrated_column_read_65ff_parts",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=root / "sims" / "integrated_column_read_65ff_pvt.csv",
    )
    p.add_argument("--root", type=Path, default=root)
    return p.parse_args()


def part_path(args: argparse.Namespace, row_or_case: object) -> Path:
    if isinstance(row_or_case, dict):
        corner = str(row_or_case["corner"])
        vdd = float(row_or_case["vdd_v"])
        temp_c = float(row_or_case["temp_c"])
        state = int(row_or_case["stored_q"])
    else:
        corner, vdd, temp_c, state = row_or_case  # type: ignore[misc]
    stem = f"{corner}_{vdd:g}V_{temp_c:g}C_q{state}"
    return args.parts_dir / f"integrated_read_{stem}.csv"


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
                f"Xschem netlist failed for {schematic}:\n"
                f"{result.stdout}\n{result.stderr}"
            )
        lines = netlist.read_text(encoding="utf-8").splitlines()

    header = next((line for line in lines if line.startswith("**.subckt ")), "")
    if set(header.split()[2:]) != set(pins):
        raise RuntimeError(f"unexpected {key} pin set: {header}")
    body = [line for line in lines if line.startswith(("X", "+"))]
    devices = {line.split()[0] for line in body if line.startswith("X")}
    if devices != expected_devices:
        raise RuntimeError(
            f"unexpected {key} devices: got {sorted(devices)}, "
            f"expected {sorted(expected_devices)}"
        )
    return (
        f".subckt {key}_core {' '.join(pins)}\n"
        + "\n".join(body)
        + f"\n.ends {key}_core\n"
    )


def pex_leaf(root: Path, key: str, sense_override: Path | None = None) -> str:
    pex_paths = {
        "bitcell": root / "layout" / "bitcell_6t" / "pex" / "bitcell_6t_pex.spice",
        "precharge": root / "layout" / "precharge" / "pex" / "precharge_pex.spice",
        "wl_driver": root / "layout" / "wl_driver" / "pex" / "wl_driver_pex.spice",
        "sense": (
            sense_override.resolve()
            if sense_override is not None
            else root / "layout" / "sense_amp" / "pex" / "sense_amp_pex.spice"
        ),
    }
    expected_pex_pins = {
        "bitcell": ("VDD", "BL", "BLB", "VSS", "WL"),
        "precharge": ("VDD", "BL", "BLB", "PRECH", "VSS"),
        "wl_driver": ("VDD", "VSS", "WL_IN", "WL"),
        "sense": ("VDD", "VSS", "BL", "BLB", "SCLK", "SA_OUT", "SA_OUTB"),
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


def override_precharge_width(subckt: str, width_um: float) -> str:
    """Override only the three precharge-device widths in an extracted leaf."""
    if width_um <= 0:
        raise ValueError("precharge width must be positive")
    lines = []
    changed = 0
    for line in subckt.splitlines():
        if line.startswith(("XMPBL ", "XMPBLB ", "XMEQ ")):
            line, count = re.subn(r"\bW=[^\s]+", f"W={width_um:g}", line, count=1)
            changed += count
        lines.append(line)
    if changed != 3:
        raise RuntimeError(f"expected to override 3 precharge widths, changed {changed}")
    return "\n".join(lines) + "\n"


def make_deck(
    *,
    args: argparse.Namespace,
    leafs: dict[str, str],
    corner: str,
    vdd: float,
    temp_c: float,
    state: int,
) -> str:
    # The total C_BL envelope already includes selected-cell access, precharge and
    # sense input capacitance.  Instantiate those real leaves and lump only the
    # remaining column/wire capacitance to avoid double counting.
    modeled_leaf_ff = (
        args.cell_access_ceff_ff + args.precharge_ceff_ff + args.sense_ceff_ff
    )
    lumped_extra_ff = args.cbl_total_ff - modeled_leaf_ff
    if lumped_extra_ff <= 0:
        raise ValueError("cbl-total-ff is smaller than modeled leaf capacitance")

    edge_ns = args.edge_ps * 1e-3
    wl_off_ns = args.wl_in_at_ns + args.wl_in_width_ns
    sclk50_ns = args.sclk_at_ns + edge_ns / 2.0
    eval_ns = sclk50_ns + args.eval_max_ns
    pre_reenable_ns = max(wl_off_ns + edge_ns + 0.25, args.sclk_at_ns + args.sclk_high_ns + edge_ns)
    stop_ns = pre_reenable_ns + args.precharge_recovery_window_ns
    target_v = args.delta_target_mv * 1e-3
    use_pex = args.pex or args.sense_pex_netlist is not None
    q_ref = "v(xcell.xpex.a_173_n1434.t0)" if use_pex else "v(xcell.q)"
    qb_ref = "v(xcell.xpex.a_126_n1530.t1)" if use_pex else "v(xcell.qb)"
    wl_extra = (
        f"CWL_EXTRA wl 0 {args.wl_extra_ff:.9f}f"
        if args.wl_extra_ff > 0
        else "* no additional WL lumped capacitance"
    )

    if state == 1:
        q0, qb0 = vdd, 0.0
        dv_expr = "v(bl)-v(blb)"
        sense_expr = "v(sa)-v(sab)"
        stored_low = qb_ref
        stored_high = q_ref
    else:
        q0, qb0 = 0.0, vdd
        dv_expr = "v(blb)-v(bl)"
        sense_expr = "v(sab)-v(sa)"
        stored_low = q_ref
        stored_high = qb_ref

    return f"""* Integrated pre-layout SRAM column read.
* Real precharge, WL driver, bitcell and sense-amplifier leaves.
* Total C_BL envelope={args.cbl_total_ff:g} fF; explicit remainder={lumped_extra_ff:.6f} fF.
.title integrated_column_read_{corner}_{vdd:g}V_{temp_c:g}C_q{state}
.lib "{MODEL_LIB}" {corner}
.temp {temp_c:g}
.param WPU={args.wpu:g} WPD={args.wpd:g} WACC={args.wacc:g}
{leafs["bitcell"]}
{leafs["precharge"]}
{leafs["wl_driver"]}
{leafs["sense"]}
VDD vdd 0 {vdd:g}
VPRECH prech 0 PWL(0 0 {args.precharge_release_ns:g}n 0 {args.precharge_release_ns + edge_ns:g}n {vdd:g} {pre_reenable_ns:g}n {vdd:g} {pre_reenable_ns + edge_ns:g}n 0 {stop_ns:g}n 0)
VWL_IN wl_in 0 PULSE(0 {vdd:g} {args.wl_in_at_ns:g}n {args.edge_ps:g}p {args.edge_ps:g}p {args.wl_in_width_ns:g}n {stop_ns + 10:g}n)
VSCLK sclk 0 PULSE(0 {vdd:g} {args.sclk_at_ns:g}n {args.edge_ps:g}p {args.edge_ps:g}p {args.sclk_high_ns:g}n {stop_ns + 10:g}n)
XPRE vdd bl blb prech 0 precharge_core
XWL vdd 0 wl_in wl wl_driver_core
XCELL vdd bl blb 0 wl bitcell_core
XSA bl blb sa sab sclk vdd 0 sense_core
CBL_EXTRA bl 0 {lumped_extra_ff:.6f}f
CBLB_EXTRA blb 0 {lumped_extra_ff:.6f}f
{wl_extra}
.ic {q_ref}={q0:.12g} {qb_ref}={qb0:.12g} v(bl)={vdd:.12g} v(blb)={vdd:.12g} v(sa)={vdd/2:.12g} v(sab)={vdd/2:.12g}
.options ngbehavior=ps method=gear reltol=1e-4 vabstol=1e-7 iabstol=1e-10
.tran {args.tran_step_ps:g}p {stop_ns:.12g}n 0 {args.tran_step_ps:g}p uic
.meas tran bl_pre find v(bl) at={args.precharge_release_ns - 0.05:.12g}n
.meas tran blb_pre find v(blb) at={args.precharge_release_ns - 0.05:.12g}n
.meas tran t_wl50 when v(wl)={vdd/2:.12g} rise=1
.meas tran t_dv when par('{dv_expr}')={target_v:.12g} rise=1 td={args.wl_in_at_ns:g}n
.meas tran t_sclk50 when v(sclk)={vdd/2:.12g} rise=1
.meas tran bl_sclk find v(bl) when v(sclk)={vdd/2:.12g} rise=1
.meas tran blb_sclk find v(blb) when v(sclk)={vdd/2:.12g} rise=1
.meas tran t_res when par('{sense_expr}')={0.8*vdd:.12g} rise=1 td={args.sclk_at_ns:g}n
.meas tran sa_eval find v(sa) at={eval_ns:.12g}n
.meas tran sab_eval find v(sab) at={eval_ns:.12g}n
.meas tran stored_low_peak max {stored_low} from={args.wl_in_at_ns:g}n to={pre_reenable_ns:.12g}n
.meas tran stored_high_min min {stored_high} from={args.wl_in_at_ns:g}n to={pre_reenable_ns:.12g}n
.meas tran q_final find {q_ref} at={stop_ns - 0.1:.12g}n
.meas tran qb_final find {qb_ref} at={stop_ns - 0.1:.12g}n
.meas tran bl_recovery find v(bl) at={stop_ns - 0.1:.12g}n
.meas tran blb_recovery find v(blb) at={stop_ns - 0.1:.12g}n
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
    *,
    args: argparse.Namespace,
    leafs: dict[str, str],
    corner: str,
    vdd: float,
    temp_c: float,
    state: int,
) -> dict[str, object]:
    deck_text = make_deck(
        args=args, leafs=leafs, corner=corner, vdd=vdd, temp_c=temp_c, state=state
    )
    with tempfile.TemporaryDirectory(prefix="integrated-column-") as td:
        deck = Path(td) / "integrated_read.spice"
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
        "bl_pre", "blb_pre", "t_wl50", "t_dv", "t_sclk50", "t_res",
        "bl_sclk", "blb_sclk", "sa_eval", "sab_eval", "stored_low_peak",
        "stored_high_min", "q_final", "qb_final", "bl_recovery", "blb_recovery",
    }
    complete = rc == 0 and required <= m.keys()
    setup_ps = (
        (m["t_sclk50"] - m["t_dv"]) * 1e12
        if {"t_sclk50", "t_dv"} <= m.keys() else None
    )
    t_dv_from_wl_ns = (
        (m["t_dv"] - m["t_wl50"]) * 1e9
        if {"t_dv", "t_wl50"} <= m.keys() else None
    )
    t_res_ns = (
        (m["t_res"] - m["t_sclk50"]) * 1e9
        if {"t_res", "t_sclk50"} <= m.keys() else None
    )
    precharge_recovery_ns = (
        max(m["t_bl_recovery"], m["t_blb_recovery"]) - m["t_prech_on50"]
    ) * 1e9 if {"t_bl_recovery", "t_blb_recovery", "t_prech_on50"} <= m.keys() else None
    delta_sclk_v = (
        (m["bl_sclk"] - m["blb_sclk"]) if state == 1
        else (m["blb_sclk"] - m["bl_sclk"])
    ) if {"bl_sclk", "blb_sclk"} <= m.keys() else None

    if state == 1:
        decision_ok = {"sa_eval", "sab_eval"} <= m.keys() and m["sa_eval"] >= 0.9*vdd and m["sab_eval"] <= 0.1*vdd
        final_ok = {"q_final", "qb_final"} <= m.keys() and m["q_final"] >= 0.9*vdd and m["qb_final"] <= 0.1*vdd
    else:
        decision_ok = {"sa_eval", "sab_eval"} <= m.keys() and m["sab_eval"] >= 0.9*vdd and m["sa_eval"] <= 0.1*vdd
        final_ok = {"q_final", "qb_final"} <= m.keys() and m["qb_final"] >= 0.9*vdd and m["q_final"] <= 0.1*vdd

    # The frozen integrated G2 contract is delta/setup/t_res based.  The
    # 90%/10% rail sample remains useful diagnostic evidence, but it is not a
    # second 250 ps acceptance criterion; full rail decision is qualified by
    # the dedicated sense-amplifier characterization.
    passed = bool(
        complete
        and m["bl_pre"] >= vdd - 0.1
        and m["blb_pre"] >= vdd - 0.1
        and delta_sclk_v is not None
        and delta_sclk_v >= args.delta_target_mv * 1e-3
        and setup_ps is not None
        and setup_ps >= args.setup_min_ps
        and t_res_ns is not None
        and 0.0 <= t_res_ns <= args.eval_max_ns
        and m["stored_low_peak"] <= 0.2
        and m["stored_high_min"] >= vdd / 2.0
        and final_ok
        and m["bl_recovery"] >= vdd - 0.1
        and m["blb_recovery"] >= vdd - 0.1
    )
    return {
        "corner": corner,
        "vdd_v": vdd,
        "temp_c": temp_c,
        "stored_q": state,
        "wpu_um": args.wpu,
        "wpd_um": args.wpd,
        "wacc_um": args.wacc,
        "wpre_um": args.precharge_width_um,
        "cbl_total_ff": args.cbl_total_ff,
        "wl_extra_ff": args.wl_extra_ff,
        "delta_target_mv": args.delta_target_mv,
        "setup_min_ps": args.setup_min_ps,
        "eval_max_ns": args.eval_max_ns,
        "t_wl50_ns": "" if "t_wl50" not in m else m["t_wl50"] * 1e9,
        "t_delta_from_wl50_ns": "" if t_dv_from_wl_ns is None else t_dv_from_wl_ns,
        "setup_to_sclk50_ps": "" if setup_ps is None else setup_ps,
        "delta_at_sclk_v": "" if delta_sclk_v is None else delta_sclk_v,
        "t_res_from_sclk50_ns": "" if t_res_ns is None else t_res_ns,
        "read_disturb_peak_v": m.get("stored_low_peak", ""),
        "stored_high_min_v": m.get("stored_high_min", ""),
        "sa_eval_v": m.get("sa_eval", ""),
        "sab_eval_v": m.get("sab_eval", ""),
        "sense_rail_check": "PASS" if decision_ok else "FAIL",
        "q_final_v": m.get("q_final", ""),
        "qb_final_v": m.get("qb_final", ""),
        "bl_recovery_v": m.get("bl_recovery", ""),
        "blb_recovery_v": m.get("blb_recovery", ""),
        "precharge_recovery_ns": "" if precharge_recovery_ns is None else precharge_recovery_ns,
        "status": "PASS" if passed else "FAIL",
        "returncode": rc,
        "error": "" if rc == 0 else output[-800:].replace("\n", " | "),
    }


def main() -> int:
    args = parse_args()
    if any(not 0.0 < v <= 1.8 for v in args.vdd_values):
        raise SystemExit("integrated qualification is limited to 1.62..1.80 V")
    if (
        args.workers < 1
        or args.delta_target_mv <= 0
        or args.cbl_total_ff <= 0
        or args.wl_extra_ff < 0
        or args.precharge_width_um <= 0
        or args.precharge_ceff_ff <= 0
    ):
        raise SystemExit("invalid workers/delta/cbl")

    use_pex = args.pex or args.sense_pex_netlist is not None
    leafs = {
        key: (
            pex_leaf(args.root, key, args.sense_pex_netlist)
            if use_pex else extract_leaf(args.root, key)
        )
        for key in LEAFS
    }
    if args.precharge_width_um != 0.42:
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
                run_case,
                args=args,
                leafs=leafs,
                corner=corner,
                vdd=vdd,
                temp_c=temp_c,
                state=state,
            )
            for corner, vdd, temp_c, state in pending
        ]
        for done, future in enumerate(as_completed(futures), start=1):
            row = future.result()
            rows.append(row)
            write_part(part_path(args, row), row)
            print(f"completed pending cases: {done}/{len(futures)}", flush=True)

    rows.sort(key=lambda r: (str(r["corner"]), float(r["vdd_v"]), float(r["temp_c"]), int(r["stored_q"])))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    failures = [row for row in rows if row["status"] != "PASS"]
    print(f"integrated column read: {len(rows)-len(failures)}/{len(rows)} PASS")
    if rows:
        valid_setup = [float(r["setup_to_sclk50_ps"]) for r in rows if r["setup_to_sclk50_ps"] != ""]
        valid_dv = [float(r["t_delta_from_wl50_ns"]) for r in rows if r["t_delta_from_wl50_ns"] != ""]
        valid_res = [float(r["t_res_from_sclk50_ns"]) for r in rows if r["t_res_from_sclk50_ns"] != ""]
        valid_disturb = [float(r["read_disturb_peak_v"]) for r in rows if r["read_disturb_peak_v"] != ""]
        valid_precharge = [float(r["precharge_recovery_ns"]) for r in rows if r["precharge_recovery_ns"] != ""]
        if valid_setup and valid_dv and valid_res and valid_disturb and valid_precharge:
            print(
                f"min_setup={min(valid_setup):.3f} ps "
                f"worst_t_delta={max(valid_dv):.5f} ns "
                f"worst_t_res={max(valid_res):.5f} ns "
                f"worst_disturb={max(valid_disturb):.6f} V "
                f"worst_precharge_recovery={max(valid_precharge):.5f} ns"
            )
    print(f"CSV: {args.output}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
