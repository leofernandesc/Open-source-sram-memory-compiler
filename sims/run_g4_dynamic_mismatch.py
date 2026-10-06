#!/usr/bin/env python3
"""G4 dynamic-mismatch screening for the selected pre-layout SRAM bitcell.

This runner intentionally reuses the already-closed integrated read/write decks.
It only changes the SKY130 model section to *_mm and inserts deterministic
ngspice seeds.  Results are engineering screening evidence, not a production
yield claim.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

import run_integrated_column_read as readmod
import run_integrated_column_write as writemod


MM_CORNERS = ("tt_mm", "ff_mm", "ss_mm", "fs_mm", "sf_mm")


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=["read", "write", "both"], default="both")
    p.add_argument("--corners", nargs="+", choices=MM_CORNERS, default=list(MM_CORNERS))
    p.add_argument("--samples", type=int, default=1)
    p.add_argument("--seed-base", type=int, default=7001)
    p.add_argument("--states", nargs="+", type=int, choices=[0, 1], default=[0, 1])
    p.add_argument("--read-vdd", type=float, default=1.80)
    p.add_argument("--read-temp-c", type=float, default=125.0)
    p.add_argument("--read-sclk-at-ns", type=float, default=2.79)
    p.add_argument("--write-vdd", type=float, default=1.62)
    p.add_argument("--write-temp-c", type=float, default=-40.0)
    p.add_argument("--cbl-total-ff", type=float, default=65.0)
    p.add_argument("--wl-extra-ff", type=float, default=17.0)
    p.add_argument("--wpd", type=float, default=1.26)
    p.add_argument("--read-tran-step-ps", type=float, default=10.0)
    p.add_argument("--write-tran-step-ps", type=float, default=10.0)
    p.add_argument("--timeout-s", type=float, default=120.0)
    p.add_argument("--resume", action="store_true")
    p.add_argument(
        "--parts-dir",
        type=Path,
        default=root / "sims" / "g4_dynamic_mismatch_parts",
    )
    p.add_argument("--root", type=Path, default=root)
    p.add_argument(
        "--output",
        type=Path,
        default=root / "sims" / "g4_dynamic_mismatch_smoke.csv",
    )
    return p.parse_args()


def read_args(args: argparse.Namespace) -> SimpleNamespace:
    return SimpleNamespace(
        root=args.root,
        wpu=0.42,
        wpd=args.wpd,
        wacc=0.60,
        precharge_width_um=0.42,
        precharge_ceff_ff=0.908533,
        cbl_total_ff=args.cbl_total_ff,
        wl_extra_ff=args.wl_extra_ff,
        delta_target_mv=200.0,
        setup_min_ps=25.0,
        eval_max_ns=0.25,
        precharge_release_ns=2.0,
        wl_in_at_ns=2.25,
        wl_in_width_ns=1.5,
        sclk_at_ns=args.read_sclk_at_ns,
        sclk_high_ns=0.5,
        precharge_recovery_window_ns=5.0,
        edge_ps=50.0,
        tran_step_ps=args.read_tran_step_ps,
        timeout_s=args.timeout_s,
    )


def write_args(args: argparse.Namespace) -> SimpleNamespace:
    return SimpleNamespace(
        root=args.root,
        wpu=0.42,
        wpd=args.wpd,
        wacc=0.60,
        cbl_total_ff=args.cbl_total_ff,
        cell_access_ceff_ff=0.452619,
        precharge_ceff_ff=0.908533,
        write_ceff_ff=4.033129,
        wl_extra_ff=args.wl_extra_ff,
        precharge_release_ns=2.0,
        we_at_ns=2.20,
        wl_in_at_ns=3.20,
        wl_in_width_ns=1.0,
        edge_ps=50.0,
        tran_step_ps=args.write_tran_step_ps,
        timeout_s=args.timeout_s,
    )


def run_deck(
    deck_text: str, *, seed: int, timeout_s: float, prefix: str
) -> tuple[int, str]:
    with tempfile.TemporaryDirectory(prefix=prefix) as td:
        deck = Path(td) / "g4_mm.spice"
        title_pos = deck_text.find(".title")
        title_end = deck_text.find("\n", title_pos)
        if title_pos < 0 or title_end < 0:
            raise RuntimeError("cannot inject deterministic seed before mismatch models")
        deck_text = (
            deck_text[: title_end + 1]
            + f".options seed={seed} seedinfo\n"
            + deck_text[title_end + 1 :]
        )
        deck.write_text(deck_text, encoding="utf-8")
        try:
            result = subprocess.run(
                ["ngspice", "-n", "-b", str(deck)],
                cwd=td,
                text=True,
                capture_output=True,
                check=False,
                timeout=timeout_s,
            )
            return result.returncode, result.stdout + "\n" + result.stderr
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            return 124, stdout + "\n" + stderr


def final_state_ok(state: int, vdd: float, q: float, qb: float) -> bool:
    if state == 1:
        return q >= 0.9 * vdd and qb <= 0.1 * vdd
    return q <= 0.1 * vdd and qb >= 0.9 * vdd


def part_path(
    args: argparse.Namespace,
    *, operation: str, corner: str, vdd: float, temp_c: float,
    sample: int, state: int, seed: int,
) -> Path:
    stem = (
        f"{operation}_{corner}_{vdd:g}V_{temp_c:g}C_"
        f"sample{sample}_q{state}_seed{seed}"
    )
    return args.parts_dir / f"{stem}.csv"


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


def run_read_case(
    *, args: argparse.Namespace, cfg: SimpleNamespace, leafs: dict[str, str],
    corner: str, sample: int, state: int, seed: int,
) -> dict[str, object]:
    deck = readmod.make_deck(
        args=cfg,
        leafs=leafs,
        corner=corner,
        vdd=args.read_vdd,
        temp_c=args.read_temp_c,
        state=state,
    )
    rc, output = run_deck(
        deck, seed=seed, timeout_s=args.timeout_s, prefix="g4-read-mm-"
    )
    m = {match.group("name"): float(match.group("value")) for match in readmod.MEASURE_RE.finditer(output)}
    required = {
        "bl_pre", "blb_pre", "t_wl50", "t_dv", "t_sclk50", "t_res",
        "bl_sclk", "blb_sclk", "sa_eval", "sab_eval", "stored_low_peak",
        "stored_high_min", "q_final", "qb_final", "bl_recovery", "blb_recovery",
        "t_prech_on50", "t_bl_recovery", "t_blb_recovery",
    }
    complete = rc == 0 and required <= m.keys()
    if complete:
        delta_sclk = (
            m["bl_sclk"] - m["blb_sclk"] if state == 1
            else m["blb_sclk"] - m["bl_sclk"]
        )
        setup_ps = (m["t_sclk50"] - m["t_dv"]) * 1e12
        t_res_ns = (m["t_res"] - m["t_sclk50"]) * 1e9
        precharge_recovery_ns = (
            max(m["t_bl_recovery"], m["t_blb_recovery"]) - m["t_prech_on50"]
        ) * 1e9
        retained = final_state_ok(state, args.read_vdd, m["q_final"], m["qb_final"])
        if state == 1:
            decision_ok = (
                m["sa_eval"] >= 0.9 * args.read_vdd
                and m["sab_eval"] <= 0.1 * args.read_vdd
            )
        else:
            decision_ok = (
                m["sab_eval"] >= 0.9 * args.read_vdd
                and m["sa_eval"] <= 0.1 * args.read_vdd
            )
        passed = bool(
            m["bl_pre"] >= args.read_vdd - 0.1
            and m["blb_pre"] >= args.read_vdd - 0.1
            and delta_sclk >= cfg.delta_target_mv * 1e-3
            and setup_ps >= cfg.setup_min_ps
            and 0.0 <= t_res_ns <= cfg.eval_max_ns
            and m["stored_low_peak"] <= 0.2
            and m["stored_high_min"] >= args.read_vdd / 2.0
            and decision_ok
            and retained
            and m["bl_recovery"] >= args.read_vdd - 0.1
            and m["blb_recovery"] >= args.read_vdd - 0.1
        )
    else:
        delta_sclk = setup_ps = t_res_ns = precharge_recovery_ns = None
        passed = False

    return {
        "operation": "read",
        "corner": corner,
        "vdd_v": args.read_vdd,
        "temp_c": args.read_temp_c,
        "sample": sample,
        "seed": seed,
        "stored_q_before": state,
        "stored_q_after": state,
        "wpd_um": args.wpd,
        "cbl_total_ff": args.cbl_total_ff,
        "wl_extra_ff": args.wl_extra_ff,
        "read_sclk_at_ns": args.read_sclk_at_ns,
        "read_disturb_peak_v": "" if not complete else m["stored_low_peak"],
        "stored_high_min_v": "" if not complete else m["stored_high_min"],
        "delta_at_sclk_v": "" if delta_sclk is None else delta_sclk,
        "setup_to_sclk50_ps": "" if setup_ps is None else setup_ps,
        "t_res_from_sclk50_ns": "" if t_res_ns is None else t_res_ns,
        "precharge_recovery_ns": "" if precharge_recovery_ns is None else precharge_recovery_ns,
        "full_flip_from_wl50_ns": "",
        "wl_min_30pct_ns": "",
        "actual_wl_high_ns": "",
        "margin_to_wl_fall_ns": "",
        "q_final_v": "" if not complete else m["q_final"],
        "qb_final_v": "" if not complete else m["qb_final"],
        "screen_status": "PASS" if passed else "FAIL",
        "returncode": rc,
        "error": "" if rc == 0 else output[-800:].replace("\n", " | "),
    }


def run_write_case(
    *, args: argparse.Namespace, cfg: SimpleNamespace, leafs: dict[str, str],
    corner: str, sample: int, state: int, seed: int,
) -> dict[str, object]:
    deck = writemod.make_deck(
        args=cfg,
        leafs=leafs,
        corner=corner,
        vdd=args.write_vdd,
        temp_c=args.write_temp_c,
        old_q=state,
    )
    rc, output = run_deck(
        deck, seed=seed, timeout_s=args.timeout_s, prefix="g4-write-mm-"
    )
    m = {match.group("name"): float(match.group("value")) for match in writemod.MEASURE_RE.finditer(output)}
    required = {
        "q_before", "qb_before", "t_wl_rise", "t_wl_fall", "bl_at_wl", "blb_at_wl",
        "t_q_full", "t_qb_full", "q_after", "qb_after", "bl_recovery", "blb_recovery",
    }
    complete = rc == 0 and required <= m.keys()
    new_q = 1 - state
    if complete:
        full_flip_s = max(m["t_q_full"], m["t_qb_full"])
        full_flip_ns = (full_flip_s - m["t_wl_rise"]) * 1e9
        actual_wl_high_ns = (m["t_wl_fall"] - m["t_wl_rise"]) * 1e9
        margin_ns = (m["t_wl_fall"] - full_flip_s) * 1e9
        wl_min_30pct_ns = 1.30 * full_flip_ns
        initialized = final_state_ok(state, args.write_vdd, m["q_before"], m["qb_before"])
        final_ok = final_state_ok(new_q, args.write_vdd, m["q_after"], m["qb_after"])
        bitlines_ready = (
            m["bl_at_wl"] >= 0.9 * args.write_vdd and m["blb_at_wl"] <= 0.1 * args.write_vdd
            if new_q else
            m["bl_at_wl"] <= 0.1 * args.write_vdd and m["blb_at_wl"] >= 0.9 * args.write_vdd
        )
        recovered = (
            m["bl_recovery"] >= args.write_vdd - 0.1
            and m["blb_recovery"] >= args.write_vdd - 0.1
        )
        passed = bool(
            initialized and final_ok and bitlines_ready and recovered
            and full_flip_ns >= 0.0 and margin_ns >= 0.0
            and wl_min_30pct_ns <= actual_wl_high_ns
        )
    else:
        full_flip_ns = actual_wl_high_ns = margin_ns = wl_min_30pct_ns = None
        passed = False

    return {
        "operation": "write",
        "corner": corner,
        "vdd_v": args.write_vdd,
        "temp_c": args.write_temp_c,
        "sample": sample,
        "seed": seed,
        "stored_q_before": state,
        "stored_q_after": new_q,
        "wpd_um": args.wpd,
        "cbl_total_ff": args.cbl_total_ff,
        "wl_extra_ff": args.wl_extra_ff,
        "read_sclk_at_ns": "",
        "read_disturb_peak_v": "",
        "stored_high_min_v": "",
        "delta_at_sclk_v": "",
        "setup_to_sclk50_ps": "",
        "t_res_from_sclk50_ns": "",
        "precharge_recovery_ns": "",
        "full_flip_from_wl50_ns": "" if full_flip_ns is None else full_flip_ns,
        "wl_min_30pct_ns": "" if wl_min_30pct_ns is None else wl_min_30pct_ns,
        "actual_wl_high_ns": "" if actual_wl_high_ns is None else actual_wl_high_ns,
        "margin_to_wl_fall_ns": "" if margin_ns is None else margin_ns,
        "q_final_v": "" if not complete else m["q_after"],
        "qb_final_v": "" if not complete else m["qb_after"],
        "screen_status": "PASS" if passed else "FAIL",
        "returncode": rc,
        "error": "" if rc == 0 else output[-800:].replace("\n", " | "),
    }


def main() -> int:
    args = parse_args()
    if (
        args.samples < 1 or args.seed_base < 1 or args.timeout_s <= 0
        or args.read_tran_step_ps <= 0 or args.write_tran_step_ps <= 0
        or args.read_sclk_at_ns <= 0
    ):
        raise SystemExit("samples, seed-base and timeout must be positive")
    if not 0 < args.read_vdd <= 1.8 or not 0 < args.write_vdd <= 1.8:
        raise SystemExit("G4 screening is limited to the qualified 1.62..1.80 V range")

    rows: list[dict[str, object]] = []
    case_index = 0

    if args.mode in ("read", "both"):
        r_cfg = read_args(args)
        r_leafs = {key: readmod.extract_leaf(args.root, key) for key in readmod.LEAFS}
        for corner in args.corners:
            for sample in range(1, args.samples + 1):
                for state in args.states:
                    seed = args.seed_base + case_index
                    path = part_path(
                        args, operation="read", corner=corner, vdd=args.read_vdd,
                        temp_c=args.read_temp_c, sample=sample, state=state, seed=seed,
                    )
                    cached = read_part(path) if args.resume else None
                    if cached is not None and cached.get("screen_status") == "PASS":
                        row: dict[str, object] = dict(cached)
                    else:
                        row = run_read_case(
                            args=args, cfg=r_cfg, leafs=r_leafs, corner=corner,
                            sample=sample, state=state, seed=seed,
                        )
                        write_part(path, row)
                    rows.append(row)
                    case_index += 1
                    print(
                        f"read {corner} sample={sample} q={state}: {rows[-1]['screen_status']}",
                        flush=True,
                    )

    if args.mode in ("write", "both"):
        w_cfg = write_args(args)
        w_leafs = {key: writemod.extract_leaf(args.root, key) for key in writemod.LEAFS}
        for corner in args.corners:
            for sample in range(1, args.samples + 1):
                for state in args.states:
                    seed = args.seed_base + case_index
                    path = part_path(
                        args, operation="write", corner=corner, vdd=args.write_vdd,
                        temp_c=args.write_temp_c, sample=sample, state=state, seed=seed,
                    )
                    cached = read_part(path) if args.resume else None
                    if cached is not None and cached.get("screen_status") == "PASS":
                        row = dict(cached)
                    else:
                        row = run_write_case(
                            args=args, cfg=w_cfg, leafs=w_leafs, corner=corner,
                            sample=sample, state=state, seed=seed,
                        )
                        write_part(path, row)
                    rows.append(row)
                    case_index += 1
                    print(
                        f"write {corner} sample={sample} q={state}: {rows[-1]['screen_status']}",
                        flush=True,
                    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    failures = [row for row in rows if row["screen_status"] != "PASS"]
    reads = [row for row in rows if row["operation"] == "read"]
    writes = [row for row in rows if row["operation"] == "write"]
    print(f"G4 dynamic mismatch smoke: {len(rows)-len(failures)}/{len(rows)} PASS")
    if reads:
        valid = [float(row["read_disturb_peak_v"]) for row in reads if row["read_disturb_peak_v"] != ""]
        if valid:
            print(f"read worst_disturb={max(valid):.6f} V")
    if writes:
        valid_flip = [float(row["full_flip_from_wl50_ns"]) for row in writes if row["full_flip_from_wl50_ns"] != ""]
        valid_guard = [float(row["wl_min_30pct_ns"]) for row in writes if row["wl_min_30pct_ns"] != ""]
        valid_margin = [float(row["margin_to_wl_fall_ns"]) for row in writes if row["margin_to_wl_fall_ns"] != ""]
        if valid_flip and valid_guard and valid_margin:
            print(
                f"write worst_full_flip={max(valid_flip):.6f} ns "
                f"worst_WL_min_30pct={max(valid_guard):.6f} ns "
                f"min_margin_to_WL_fall={min(valid_margin):.6f} ns"
            )
    print(f"CSV: {args.output}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
