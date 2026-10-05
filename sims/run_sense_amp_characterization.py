#!/usr/bin/env python3
"""Characterize the pre-layout SKY130 latch sense-amplifier candidate.

The core follows the enable/sampling principle used by the SKY130 OpenRAM
sense amplifier bundled with the PDK: with SCLK low, PMOS sampling devices
connect BL/BLB to the internal latch nodes while the NMOS tail is off.  When
SCLK rises, the bitlines are isolated and the cross-coupled latch regenerates.

This script is a schematic-level functional/timing characterization.  It does
not establish an offset/yield requirement; mismatch is intentionally a separate
gate after deterministic PVT behavior is known to be sound.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path


MODEL_LIB = "/opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice"
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
MEASURE_RE = re.compile(
    rf"^\s*(?P<name>(?:sa_sample|sab_sample|sa_eval|sab_eval|t_res)_\d+)"
    rf"\s*=\s*(?P<value>{NUMBER})",
    re.MULTILINE,
)


@dataclass(frozen=True)
class Case:
    suite: str
    corner: str
    vdd: float
    temp_c: float
    delta_v: float
    polarity: int
    init_state: str


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corners",
        nargs="+",
        default=["tt", "ff", "ss", "fs", "sf"],
        choices=["tt", "ff", "ss", "fs", "sf"],
    )
    parser.add_argument("--vdd-values", nargs="+", type=float, default=[1.62, 1.80])
    parser.add_argument("--temps-c", nargs="+", type=float, default=[-40.0, 27.0, 125.0])
    parser.add_argument("--delta-mv", nargs="+", type=float, default=[5, 10, 20, 50, 100])
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout-s", type=float, default=90.0)
    parser.add_argument("--pex", action="store_true", help="Use the Magic RC-extracted sense-amplifier netlist.")
    parser.add_argument(
        "--pex-netlist",
        type=Path,
        default=None,
        help="Optional PEX netlist override; implies --pex.",
    )
    parser.add_argument("--sclk-at-ns", type=float, default=2.0)
    parser.add_argument("--sclk-rise-ps", type=float, default=50.0)
    parser.add_argument("--sample-at-ns", type=float, default=1.9)
    parser.add_argument("--eval-at-ns", type=float, default=3.5)
    parser.add_argument(
        "--schematic",
        type=Path,
        default=root / "cells" / "sense_amp.sch",
        help="Xschem leaf schematic used to generate the transistor netlist",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "sims" / "sense_amp_characterization_pvt.csv",
    )
    return parser.parse_args()


def sense_subckt(schematic: Path) -> str:
    schematic = schematic.resolve()
    with tempfile.TemporaryDirectory(prefix="sense-xschem-") as temp_dir:
        result = subprocess.run(
            ["xschem", "-x", "-q", "-n", "-o", temp_dir, str(schematic)],
            cwd=schematic.parent.parent,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        netlist = Path(temp_dir) / f"{schematic.stem}.spice"
        if result.returncode != 0 or not netlist.exists():
            raise RuntimeError(
                f"Xschem netlist failed for {schematic}:\n"
                f"{result.stdout}\n{result.stderr}"
            )
        lines = netlist.read_text(encoding="utf-8").splitlines()

    header = next((line for line in lines if line.startswith("**.subckt ")), "")
    expected_pins = {"BL", "BLB", "SA_OUT", "SA_OUTB", "SCLK", "VDD", "VSS"}
    if set(header.split()[2:]) != expected_pins:
        raise RuntimeError(f"Unexpected sense-amplifier pin set: {header}")
    body = [line for line in lines if line.startswith(("X", "+"))]
    devices = {line.split()[0] for line in body if line.startswith("X")}
    expected_devices = {
        "XMP1", "XMP2", "XMN1", "XMN2", "XMSAMPBL", "XMSAMPBLB", "XMTAIL"
    }
    if devices != expected_devices or any(re.search(r"\bnet\d+\b", line) for line in body):
        raise RuntimeError(f"Sense-amplifier netlist has wrong or unconnected devices: {devices}")
    return (
        ".subckt sense_amp_core BL BLB SA_OUT SA_OUTB SCLK VDD VSS\n"
        + "\n".join(body)
        + "\n.ends sense_amp_core\n"
    )


def sense_pex_subckt(root: Path, netlist_override: Path | None = None) -> tuple[str, str]:
    netlist = (
        netlist_override.resolve()
        if netlist_override is not None
        else root / "layout" / "sense_amp" / "pex" / "sense_amp_pex.spice"
    )
    text = netlist.read_text(encoding="utf-8")
    match = re.search(r"^\.subckt\s+(\S+)\s+(.+)$", text, re.MULTILINE)
    if not match:
        raise RuntimeError(f"Missing PEX sense subcircuit: {netlist}")
    name = match.group(1)
    pins = tuple(match.group(2).split())
    expected = ("VDD", "VSS", "BL", "BLB", "SCLK", "SA_OUT", "SA_OUTB")
    if pins != expected:
        raise RuntimeError(f"Unexpected PEX sense pins: {pins}")
    wrapper = (
        ".subckt sense_amp_core BL BLB SA_OUT SA_OUTB SCLK VDD VSS\n"
        f"XPEX VDD VSS BL BLB SCLK SA_OUT SA_OUTB {name}\n"
        ".ends sense_amp_core\n"
    )
    return text + "\n" + wrapper, hashlib.sha256(netlist.read_bytes()).hexdigest()


def initial_voltage(case: Case) -> tuple[float, float]:
    if case.init_state == "sa_low":
        return 0.0, case.vdd
    if case.init_state == "sa_high":
        return case.vdd, 0.0
    return case.vdd / 2.0, case.vdd / 2.0


def make_deck(
    cases: list[Case],
    *,
    subckt: str,
    corner: str,
    vdd: float,
    temp_c: float,
    sclk_at_ns: float,
    sclk_rise_ps: float,
    sample_at_ns: float,
    eval_at_ns: float,
) -> str:
    lines = [
        "* Batched deterministic sense-amplifier characterization.",
        f'.lib "{MODEL_LIB}" {corner}',
        f".temp {temp_c:g}",
        subckt,
        f"VDD vdd 0 {vdd:g}",
        (
            f"VSCLK sclk 0 PULSE(0 {vdd:g} {sclk_at_ns:g}n "
            f"{sclk_rise_ps:g}p {sclk_rise_ps:g}p 2n 10n)"
        ),
    ]
    for index, case in enumerate(cases):
        if case.polarity > 0:
            bl, blb = vdd, vdd - case.delta_v
            diff_expr = f"v(sa_{index})-v(sab_{index})"
        else:
            bl, blb = vdd - case.delta_v, vdd
            diff_expr = f"v(sab_{index})-v(sa_{index})"
        sa0, sab0 = initial_voltage(case)
        lines.extend(
            [
                f"VBL_{index} bl_{index} 0 {bl:.12g}",
                f"VBLB_{index} blb_{index} 0 {blb:.12g}",
                (
                    f"XSA_{index} bl_{index} blb_{index} sa_{index} sab_{index} "
                    "sclk vdd 0 sense_amp_core"
                ),
                f".ic v(sa_{index})={sa0:.12g} v(sab_{index})={sab0:.12g}",
                f".meas tran sa_sample_{index} find v(sa_{index}) at={sample_at_ns:g}n",
                f".meas tran sab_sample_{index} find v(sab_{index}) at={sample_at_ns:g}n",
                f".meas tran sa_eval_{index} find v(sa_{index}) at={eval_at_ns:g}n",
                f".meas tran sab_eval_{index} find v(sab_{index}) at={eval_at_ns:g}n",
                (
                    f".meas tran t_res_{index} when par('{diff_expr}')="
                    f"{0.8 * vdd:.12g} rise=1"
                ),
            ]
        )
    stop_ns = max(eval_at_ns + 0.5, sclk_at_ns + 2.0)
    lines.extend(
        [
            ".options ngbehavior=ps method=gear reltol=1e-4 vabstol=1e-7 iabstol=1e-10",
            f".tran 5p {stop_ns:g}n 0 5p uic",
            ".end",
        ]
    )
    return "\n".join(lines) + "\n"


def run_batch(
    ngspice: str,
    cases: list[Case],
    args: argparse.Namespace,
) -> tuple[list[dict[str, object]], str]:
    corner = cases[0].corner
    vdd = cases[0].vdd
    temp_c = cases[0].temp_c
    deck_text = make_deck(
        cases,
        subckt=args.subckt,
        corner=corner,
        vdd=vdd,
        temp_c=temp_c,
        sclk_at_ns=args.sclk_at_ns,
        sclk_rise_ps=args.sclk_rise_ps,
        sample_at_ns=args.sample_at_ns,
        eval_at_ns=args.eval_at_ns,
    )
    with tempfile.TemporaryDirectory(prefix="sense-amp-") as temp_dir:
        deck = Path(temp_dir) / "sense_amp.spice"
        deck.write_text(deck_text, encoding="utf-8")
        try:
            result = subprocess.run(
                [ngspice, "-n", "-b", str(deck)],
                cwd=temp_dir,
                text=True,
                capture_output=True,
                check=False,
                timeout=args.timeout_s,
            )
            returncode = result.returncode
            output = result.stdout + "\n" + result.stderr
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            returncode = 124
            output = stdout + "\n" + stderr

    measures = {
        match.group("name"): float(match.group("value"))
        for match in MEASURE_RE.finditer(output)
    }
    rows: list[dict[str, object]] = []
    sclk_50_s = (args.sclk_at_ns * 1e-9) + (args.sclk_rise_ps * 1e-12 / 2.0)
    for index, case in enumerate(cases):
        sa_sample = measures.get(f"sa_sample_{index}")
        sab_sample = measures.get(f"sab_sample_{index}")
        sa_eval = measures.get(f"sa_eval_{index}")
        sab_eval = measures.get(f"sab_eval_{index}")
        t_res = measures.get(f"t_res_{index}")
        sample_polarity_ok = False
        decision_ok = False
        if sa_sample is not None and sab_sample is not None:
            sample_polarity_ok = (
                sa_sample > sab_sample if case.polarity > 0 else sab_sample > sa_sample
            )
        if sa_eval is not None and sab_eval is not None:
            if case.polarity > 0:
                decision_ok = sa_eval >= 0.9 * case.vdd and sab_eval <= 0.1 * case.vdd
            else:
                decision_ok = sab_eval >= 0.9 * case.vdd and sa_eval <= 0.1 * case.vdd
        status = (
            "PASS"
            if returncode == 0 and sample_polarity_ok and decision_ok and t_res is not None
            else "FAIL"
        )
        rows.append(
            {
                "schematic_sha256": args.schematic_sha256,
                "suite": case.suite,
                "corner": case.corner,
                "vdd_v": case.vdd,
                "temp_c": case.temp_c,
                "delta_mv": case.delta_v * 1000.0,
                "polarity": "BL>BLB" if case.polarity > 0 else "BLB>BL",
                "init_state": case.init_state,
                "sa_sample_v": sa_sample if sa_sample is not None else "",
                "sab_sample_v": sab_sample if sab_sample is not None else "",
                "sample_polarity_ok": sample_polarity_ok,
                "sa_eval_v": sa_eval if sa_eval is not None else "",
                "sab_eval_v": sab_eval if sab_eval is not None else "",
                "decision_ok": decision_ok,
                "t_res_s": t_res if t_res is not None else "",
                "t_res_from_sclk50_ns": (
                    (t_res - sclk_50_s) * 1e9 if t_res is not None else ""
                ),
                "status": status,
                "returncode": returncode,
                "error": "" if returncode == 0 else output[-1000:].replace("\n", " | "),
            }
        )
    return rows, output


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parent.parent
    if args.workers < 1:
        raise SystemExit("--workers must be >= 1")
    if any(not 0 < voltage <= 1.8 for voltage in args.vdd_values):
        raise SystemExit("Sense-amplifier qualification is limited to VDD <= 1.8 V")
    if any(delta <= 0 for delta in args.delta_mv):
        raise SystemExit("--delta-mv values must be positive")

    if args.pex or args.pex_netlist is not None:
        args.subckt, args.schematic_sha256 = sense_pex_subckt(root, args.pex_netlist)
        source = args.pex_netlist or root / "layout" / "sense_amp" / "pex" / "sense_amp_pex.spice"
        print(f"PEX netlist: {source}, sha256={args.schematic_sha256}", flush=True)
    else:
        args.schematic_sha256 = hashlib.sha256(args.schematic.read_bytes()).hexdigest()
        args.subckt = sense_subckt(args.schematic)
        print(f"Xschem netlist: {args.schematic}, sha256={args.schematic_sha256}", flush=True)

    deltas_v = [delta * 1e-3 for delta in args.delta_mv]
    batches: list[list[Case]] = []
    for corner, vdd, temp_c in itertools.product(
        args.corners, args.vdd_values, args.temps_c
    ):
        batches.append(
            [
                Case("pvt", corner, vdd, temp_c, delta_v, polarity, "mid")
                for delta_v, polarity in itertools.product(deltas_v, (1, -1))
            ]
        )

    # Explicitly prove that the low-SCLK sampling phase erases prior latch state.
    batches.append(
        [
            Case("initial_state", "tt", 1.80, 27.0, delta_v, polarity, init_state)
            for delta_v, polarity, init_state in itertools.product(
                deltas_v, (1, -1), ("sa_low", "sa_high", "mid")
            )
        ]
    )

    all_rows: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(run_batch, "ngspice", batch, args) for batch in batches]
        for completed, future in enumerate(as_completed(futures), start=1):
            rows, _ = future.result()
            all_rows.extend(rows)
            print(f"completed batches: {completed}/{len(batches)}", flush=True)

    all_rows.sort(
        key=lambda row: (
            str(row["suite"]),
            str(row["corner"]),
            float(row["vdd_v"]),
            float(row["temp_c"]),
            float(row["delta_mv"]),
            str(row["polarity"]),
            str(row["init_state"]),
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(all_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(all_rows)

    failures = [row for row in all_rows if row["status"] != "PASS"]
    print(f"sense deterministic: {len(all_rows) - len(failures)}/{len(all_rows)} PASS")
    for delta_mv in args.delta_mv:
        rows = [
            row
            for row in all_rows
            if row["suite"] == "pvt" and abs(float(row["delta_mv"]) - delta_mv) < 1e-9
        ]
        delays = [
            float(row["t_res_from_sclk50_ns"])
            for row in rows
            if row["t_res_from_sclk50_ns"] != ""
        ]
        passed = sum(row["status"] == "PASS" for row in rows)
        print(
            f"delta={delta_mv:g} mV: {passed}/{len(rows)} PASS; "
            f"worst_t_res={max(delays):.6f} ns" if delays else
            f"delta={delta_mv:g} mV: {passed}/{len(rows)} PASS; no timing measure"
        )
    init_rows = [row for row in all_rows if row["suite"] == "initial_state"]
    print(
        "initial-state erase: "
        f"{sum(row['status'] == 'PASS' for row in init_rows)}/{len(init_rows)} PASS"
    )
    print(f"CSV: {args.output}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
