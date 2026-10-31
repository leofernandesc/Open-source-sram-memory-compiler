#!/usr/bin/env python3
"""Reproduce the Phase 2 functional regression; no analog or timing signoff."""
from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
import fcntl
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEMORY_CASES = [("model", depth) for depth in (4, 8, 16, 32)] + [("wrapper", 4)]
CONTROL_RESULT = {"checks": 96, "controls": 8, "addresses": 4}
UNSUPPORTED_DEPTHS = (0, 1, 2, 3, 5, 64)
MUTATIONS = {
    "wrong_capture_edge": ("always @(posedge CLK)", "always @(negedge CLK)"),
    "address_alias": ("address_q <= ADDR;", "address_q <= 0;"),
    "missing_bus_mask": ("(read_q && live_read)", "read_q"),
    "corrupt_write_data": ("write_data_q <= DATA;", "write_data_q <= ~DATA;"),
    "invalid_control_write": ("write_q <= !CSb && OEb && !WEb;", "write_q <= !CSb && !WEb;"),
    "live_address": ("mem[address_q]", "mem[ADDR]"),
}


def atomic_text(path: Path, text: str) -> None:
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(text)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write_receipt(output: Path, receipt: dict) -> None:
    atomic_text(output / "results.json", json.dumps(receipt, indent=2) + "\n")


def invalidate_verification(output: Path, reason: str) -> None:
    path = output / "verification_checks.json"
    previous = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    atomic_text(path, json.dumps({"status": "NOT_CURRENT", "reason": reason,
                                 "invalidated_utc": datetime.now(timezone.utc).isoformat(),
                                 "previous_receipt_sha256": previous}, indent=2) + "\n")


@contextmanager
def output_lock(output: Path):
    # Keep the inode after unlocking: removing it would race with other owners.
    with (output / ".run.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(f"Output directory already in use: {output}") from error
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def input_paths(root: Path) -> list[Path]:
    paths = [*root.glob("rtl/*"), *root.glob("tb/*"),
             *root.glob("tools/tests/test_digital_regression*.py"),
             root / "scripts/run_rtl.sh", root / "tools/run_digital_regression.py",
             root / "specs/technical_specification.md", root / "specs/sram_4x8_digital.md",
             root / "docs/sram_4x8_interfaces.md"]
    required = [path for path in paths if not path.is_dir()]
    for path in required:
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"Missing or symbolic input: {path}")
    return sorted(required)


def verify_input_hashes(root: Path, directory: Path, hashes: dict[str, str]) -> None:
    current_names = {str(path.relative_to(root)) for path in input_paths(root)}
    if current_names != set(hashes):
        raise RuntimeError("Source inputs changed during regression: file set differs")
    for name, expected in hashes.items():
        for base in (root, directory):
            path = base / name
            if (not path.is_file() or path.is_symlink() or
                    hashlib.sha256(path.read_bytes()).hexdigest() != expected):
                raise RuntimeError(f"Source inputs changed during regression: {path}")


class SourceSnapshot:
    """Capture once, compile only the captured bytes, and reject later edits."""

    def __init__(self, root: Path, work: Path):
        self.root = root
        self.directory = work / "sources"
        self.hashes: dict[str, str] = {}
        for source in input_paths(root):
            name = str(source.relative_to(root))
            contents = source.read_bytes()
            self.hashes[name] = hashlib.sha256(contents).hexdigest()
            target = self.directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(contents)
            target.chmod(0o444)
        self.verify_unchanged()

    def verify_unchanged(self) -> None:
        verify_input_hashes(self.root, self.directory, self.hashes)


def run(command: list[str], *, expected_failure: bool = False, cwd: Path | None = None) -> str:
    result = subprocess.run(command, cwd=cwd or ROOT, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=120)
    expected_code = 1 if expected_failure else 0
    if result.returncode != expected_code:
        raise RuntimeError(f"Unexpected return code {result.returncode}: {command}\n{result.stdout}")
    return result.stdout


def file_list(name: str, snapshot: SourceSnapshot) -> list[str]:
    sources = (snapshot.directory / "rtl" / name).read_text().split()
    for source in sources:
        if source not in snapshot.hashes:
            raise RuntimeError(f"File list uses an input outside the captured source set: {source}")
    return sources


def extract_result(transcript: str, prefix: str) -> dict:
    matches = [line.removeprefix(prefix) for line in transcript.splitlines() if line.startswith(prefix)]
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one {prefix.strip()} result, received {len(matches)}")
    result = json.loads(matches[0])
    if not isinstance(result, dict):
        raise RuntimeError("Regression result must be an object")
    return result


def validate_expected_failure(transcript: str, cause: str) -> dict:
    fatals = re.findall(r"^FATAL: [^\n]*?:\d+: ([^\n]+)$", transcript, re.M)
    scopes = re.findall(r"^\s*Time:\s*\d+\s+Scope:\s*(\S+)\s*$", transcript, re.M)
    if len(fatals) != 1 or len(scopes) != 1:
        raise RuntimeError(f"Unexpected failure cause for {cause}: missing or ambiguous fatal diagnostic")
    message, scope = fatals[0], scopes[0]
    if cause == "scoreboard":
        matches = re.fullmatch(
            r"\S+ transaction=\d+ controls=[01xz]{3} address=\S+ DATA=[0-9a-fxz]+ expected=[0-9a-fxz]+",
            message)
        valid = bool(matches) and scope == "tb_sram_4x8.expect_bus"
    elif cause.startswith("unsupported_depth:"):
        depth = int(cause.partition(":")[2])
        valid = (message == f"Unsupported SRAM depth: {depth}" and
                 scope == "tb_sram_depth_guard.dut.invalid_depth")
    else:
        raise RuntimeError(f"Unknown expected failure cause: {cause}")
    if not valid:
        raise RuntimeError(f"Unexpected failure cause for {cause}: {message} (scope {scope})")
    return {"expected_cause": cause, "message": message, "scope": scope}


def validate_case(result: dict, depth: int, seed: int, random_ops: int) -> None:
    expected_values = {"depth": depth, "seed": seed, "random_ops": random_ops,
                       "control_transitions": 64}
    scalar_names = (*expected_values, "checks", "transactions")
    for name in scalar_names:
        if type(result.get(name)) is not int:
            raise RuntimeError(f"Invalid result counter: {name}")
    for name, expected in expected_values.items():
        if result[name] != expected:
            raise RuntimeError(f"Executed configuration mismatch: {name}={result[name]}, expected {expected}")
    if result["transactions"] < random_ops or result["checks"] <= 0:
        raise RuntimeError("Incomplete transaction/check counts")
    for name, size in (("controls", 8), ("read_addresses", depth), ("write_addresses", depth)):
        counts = result.get(name)
        if (not isinstance(counts, list) or len(counts) != size or
                any(type(count) is not int or count <= 0 for count in counts)):
            raise RuntimeError(f"Incomplete regression coverage: {name}")
    if (sum(result["controls"]) != result["transactions"] or
            sum(result["read_addresses"]) != result["controls"][1] or
            sum(result["write_addresses"]) != result["controls"][2]):
        raise RuntimeError("Inconsistent operation/address coverage totals")
    if set(result) != set(scalar_names) | {"controls", "read_addresses", "write_addresses"}:
        raise RuntimeError("Unexpected regression result fields")


def execute_regression(args: argparse.Namespace, output: Path, state: dict) -> int:
    logs = output / "logs"
    logs.mkdir(exist_ok=True)
    build_root = ROOT / "build" / "digital"
    build_root.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="run-", dir=build_root))
    state["run_directory"] = str(work.relative_to(ROOT))
    write_receipt(output, state)
    snapshot = SourceSnapshot(ROOT, work)
    state["source_sha256"] = snapshot.hashes
    manifest = {"captured_utc": datetime.now(timezone.utc).isoformat(),
                "source_sha256": snapshot.hashes,
                "snapshot_directory": str(snapshot.directory.relative_to(ROOT))}
    atomic_text(output / "source_manifest.json", json.dumps(manifest, indent=2) + "\n")
    write_receipt(output, state)
    commands: list[dict] = []
    transcripts: list[Path] = []
    negative_results: list[dict] = []

    def compile_case(name: str, sources: list[str], top: str,
                     extra: list[str] | None = None, standard: str = "2012") -> Path:
        executable = work / f"{name}.vvp"
        command = ["iverilog", f"-g{standard}", "-Wall", "-s", top,
                   "-o", str(executable), *(extra or []), *sources]
        commands.append({"argv": command, "cwd": str(snapshot.directory)})
        transcripts.append(logs / f"{name}_compile.txt")
        try:
            transcript = run(command, cwd=snapshot.directory)
        except RuntimeError as error:
            (logs / f"{name}_compile.txt").write_text(str(error) + "\n")
            raise
        (logs / f"{name}_compile.txt").write_text(transcript)
        if transcript.strip():
            raise RuntimeError(f"Compilation produced diagnostics for {name}:\n{transcript}")
        return executable

    def simulate(name: str, executable: Path, *, expected_failure: str | None = None,
                 waveform: bool = False) -> str:
        command = ["vvp", str(executable), f"+seed={args.seed}",
                   f"+random_ops={args.random_ops}"]
        if waveform:
            command.append(f"+vcd={work / (name + '.vcd')}")
        commands.append({"argv": command, "cwd": str(snapshot.directory)})
        transcripts.append(logs / f"{name}.txt")
        try:
            transcript = run(command, expected_failure=expected_failure is not None, cwd=snapshot.directory)
        except RuntimeError as error:
            (logs / f"{name}.txt").write_text(str(error) + "\n")
            raise
        (logs / f"{name}.txt").write_text(transcript)
        if expected_failure is not None:
            observed = validate_expected_failure(transcript, expected_failure)
            negative_results.append({"case": name, **observed})
        return transcript

    # The public model is parsed as Verilog 2005, independently of the SV TB.
    compile_case("verilog2005", file_list("model.f", snapshot), "sram_model", standard="2005")
    # Separate synthesis and simulation lists must never define the macro twice.
    compile_case("blackbox_elaboration", file_list("wrapper_synth.f", snapshot), "sram_4x8_wrapper")
    units = compile_case("control", ["rtl/sram_controller.v", "rtl/row_decoder_2to4.v",
                                     "tb/tb_sram_control.sv"], "tb_sram_control")
    control_log = simulate("control", units)
    control = extract_result(control_log, "CONTROL_RESULT ")
    if control != CONTROL_RESULT:
        raise RuntimeError("Incomplete controller/decoder coverage")
    cases = []
    common = ["tb/sram_ref_model.sv", "tb/tb_sram_4x8.sv"]
    for view, depth in MEMORY_CASES:
        name = f"{view}_{depth}x8"
        sources = file_list("model.f" if view == "model" else "wrapper_sim.f", snapshot)
        extra = [f"-Ptb_sram_4x8.DEPTH={depth}"]
        if view == "wrapper":
            extra += ["-DTEST_WRAPPER"]
        executable = compile_case(name, sources + common, "tb_sram_4x8", extra)
        transcript = simulate(name, executable, waveform=(depth == 4))
        result = extract_result(transcript, "RESULT ")
        validate_case(result, depth, args.seed, args.random_ops)
        cases.append({"view": view, "status": "PASS", **result})
        print(f"PASS {name}: {result['checks']} checks / {result['transactions']} transactions", flush=True)
    equivalent = [{k: v for k, v in case.items() if k != "view"}
                  for case in cases if case["depth"] == 4]
    if equivalent[0] != equivalent[1]:
        raise RuntimeError("Public and structural views have different coverage/results")

    # Preserve small real waveform excerpts with the review evidence. Full
    # waveforms remain reproducible build products, not repository payload.
    waveforms = []
    waveform_directory = output / "waveforms"
    waveform_directory.mkdir(exist_ok=True)
    for view in ("model", "wrapper"):
        full_waveform = work / f"{view}_4x8.vcd"
        content = full_waveform.read_text()
        if not re.search(r"\$timescale\s+1ps\s+\$end", content):
            raise RuntimeError("Unexpected VCD time unit; do not guess excerpt timestamps")
        excerpt_lines = []
        for line in content.splitlines(keepends=True):
            if line.startswith("#") and int(line[1:].strip()) > 180000:
                break
            excerpt_lines.append(line)
        selected = waveform_directory / full_waveform.name
        selected.write_text("".join(excerpt_lines))
        waveforms.append({"file": str(selected.relative_to(output)), "stop_ns": 180,
                          "sha256": hashlib.sha256(selected.read_bytes()).hexdigest()})

    rejected = []
    for depth in UNSUPPORTED_DEPTHS:
        name = f"reject_depth_{depth}"
        executable = compile_case(name, ["rtl/sram_model.v", "tb/tb_sram_depth_guard.v"],
                                  "tb_sram_depth_guard", [f"-Ptb_sram_depth_guard.DEPTH={depth}"])
        simulate(name, executable, expected_failure=f"unsupported_depth:{depth}")
        rejected.append(depth)

    # Mutants live only under ignored build/, never in the delivered RTL.
    original = (snapshot.directory / "rtl/sram_model.v").read_text()
    detected = []
    for name, (before, after) in MUTATIONS.items():
        if before not in original:
            raise RuntimeError(f"Stale mutation: {name}")
        mutant = work / f"mutant_{name}.v"
        mutant.write_text(original.replace(before, after))
        executable = compile_case(f"mutant_{name}", [str(mutant), *common], "tb_sram_4x8")
        simulate(f"mutant_{name}", executable, expected_failure="scoreboard")
        detected.append(name)
    # These control files contain only edge-triggered procedural processes.
    # This is a source audit, not a Yosys synthesis/latch report.
    processes = []
    for filename in ("rtl/sram_controller.v", "rtl/sram_4x8_wrapper.v"):
        source = re.sub(r"//[^\n]*|/\*.*?\*/", "", (snapshot.directory / filename).read_text(), flags=re.S)
        events = re.findall(r"\balways\s*@\s*\(([^)]*)\)", source)
        if (len(events) != len(re.findall(r"\balways\b", source)) or
                any(event.strip() not in ("posedge CLK", "negedge CLK") for event in events) or
                re.search(r"\binitial\b|#", source)):
            raise RuntimeError(f"Unexpected procedural process or delay in {filename}")
        processes.append({"file": filename, "events": events})
    revision = run(["git", "rev-parse", "HEAD"]).strip()
    versions = {}
    for tool in ("iverilog", "vvp"):
        versions[tool] = subprocess.run([tool, "-V"], text=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, timeout=10).stdout.splitlines()[0]
    report = {"schema_version": 3, "status": "PASS", "scope": "functional digital verification; no physical timing signoff",
              "started_utc": state["started_utc"], "run_directory": state["run_directory"],
              "created_utc": datetime.now(timezone.utc).isoformat(), "base_commit": revision,
              "source_identity": "Immutable pre-compilation snapshot; working tree and snapshot verified unchanged before PASS",
              "seed": args.seed, "tool_versions": versions, "python": sys.version.split()[0],
              "cases": cases, "controller": control, "rejected_depths": rejected,
              "detected_mutants": detected, "clocked_process_audit": processes,
              "negative_results": negative_results,
              "source_sha256": snapshot.hashes, "commands": commands,
              "source_manifest_sha256": hashlib.sha256((output / "source_manifest.json").read_bytes()).hexdigest(),
              "snapshot_directory": str(snapshot.directory.relative_to(ROOT)),
              "inputs_unchanged": True,
              "waveforms": waveforms,
              "full_waveforms": [str((work / f"{view}_4x8.vcd").relative_to(ROOT))
                                 for view in ("model", "wrapper")],
              "log_sha256": {str(path.relative_to(output)): hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in sorted(transcripts)},
              "not_evaluated": ["Yosys synthesis/latch statistics", "GLS", "SDC/SDF timing",
                                "analog power-up", "PCLK/PRECH electrical sequencing",
                                "integrated physical SRAM read/write", "frequency and electrical margins"]}
    total = sum(case["checks"] for case in cases) + control["checks"]
    summary = (
        "# Phase 2 digital regression\n\n"
        f"Status: **PASS**. {total:,} checks across five memory runs and the controller test.\n\n"
        "| View | Depth | Transactions | Bus checks | Random operations |\n"
        "|---|---:|---:|---:|---:|\n" +
        "".join(f"| {c['view']} | {c['depth']} | {c['transactions']} | {c['checks']} | {c['random_ops']} |\n"
                for c in cases) +
        f"\nController: {control['checks']} checks. Unsupported depths rejected: {rejected}.\n"
        f"Six deliberately faulty models were detected: {', '.join(detected)}.\n\n"
        "Each memory run covers all eight controls, all 64 ordered control transitions, "
        "all read/write addresses, and 20 directed data patterns.\n\n"
        "Source identities, commands and tool versions are in `results.json`; transcripts "
        "are in `logs/`. Real 0..180 ns VCD excerpts are retained under `waveforms/`; "
        "full VCD files and read-only source snapshots remain in the unique run directory "
        "recorded in `results.json`, under ignored `build/digital/`. Testbench "
        "time is scheduling only, not a characterized operating period.\n\n"
        "The clocked-process source audit found only edge-triggered processes in the "
        "controller and wrapper. Synthesis, GLS, physical timing and analog integration "
        "are **NOT EVALUATED**. The black-box compilation checks interface elaboration only.\n")
    # JSON is the authoritative completion marker and is published last.
    snapshot.verify_unchanged()
    atomic_text(output / "summary.md", summary)
    write_receipt(output, report)
    print(f"PASS: {total} checks; 6 depth guards; 6 mutants detected. Report: {output}")
    return 0


def require_log_match(recorded, observed, label: str) -> None:
    # Canonical JSON preserves scalar types (e.g. 1, 1.0 and true differ).
    if json.dumps(recorded, sort_keys=True, allow_nan=False) != json.dumps(observed, sort_keys=True, allow_nan=False):
        raise RuntimeError(f"Core summary differs from raw log: {label}")


def reconcile_core_results(output: Path, core: dict) -> dict:
    result_hashes = {}

    def read_log(name: str) -> str:
        relative = f"logs/{name}.txt"
        path = output / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if core["log_sha256"].get(relative) != digest:
            raise RuntimeError(f"Required result log is missing or has changed: {relative}")
        result_hashes[relative] = digest
        return path.read_text()

    cases = []
    seed = random_ops = None
    for view, depth in MEMORY_CASES:
        observed = extract_result(read_log(f"{view}_{depth}x8"), "RESULT ")
        if not cases:
            seed, random_ops = observed.get("seed"), observed.get("random_ops")
            if (type(seed) is not int or not 0 <= seed <= 0xFFFFFFFF or
                    type(random_ops) is not int or random_ops < 2048):
                raise RuntimeError("Invalid configuration in raw result log")
        validate_case(observed, depth, seed, random_ops)
        cases.append({"view": view, "status": "PASS", **observed})
    require_log_match(core.get("cases"), cases, "memory cases")
    require_log_match(core.get("seed"), seed, "seed")
    controller = extract_result(read_log("control"), "CONTROL_RESULT ")
    require_log_match(controller, CONTROL_RESULT, "controller coverage")
    require_log_match(core.get("controller"), controller, "controller")
    negatives = []
    for depth in UNSUPPORTED_DEPTHS:
        name = f"reject_depth_{depth}"
        negatives.append({"case": name, **validate_expected_failure(read_log(name), f"unsupported_depth:{depth}")})
    for mutant in MUTATIONS:
        name = f"mutant_{mutant}"
        negatives.append({"case": name, **validate_expected_failure(read_log(name), "scoreboard")})
    require_log_match(core.get("rejected_depths"), list(UNSUPPORTED_DEPTHS), "rejected depths")
    require_log_match(core.get("detected_mutants"), list(MUTATIONS), "detected mutants")
    require_log_match(core.get("negative_results"), negatives, "negative diagnostics")
    return {"core_checks": sum(case["checks"] for case in cases) + controller["checks"],
            "memory_cases": len(cases), "controller_checks": controller["checks"],
            "negative_cases": len(negatives), "result_log_sha256": result_hashes}


def verify_core_inputs(output: Path, core: dict) -> dict:
    if core.get("status") != "PASS" or core.get("schema_version") != 3:
        raise RuntimeError("A current passing core regression is required before evidence verification")
    hashes = core["source_sha256"]
    verify_input_hashes(ROOT, ROOT / core["snapshot_directory"], hashes)
    manifest = output / "source_manifest.json"
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != core["source_manifest_sha256"]:
        raise RuntimeError("Source manifest no longer matches the core receipt")
    if json.loads(manifest.read_text())["source_sha256"] != hashes:
        raise RuntimeError("Captured input identities differ between receipts")
    for name, expected in core["log_sha256"].items():
        if hashlib.sha256((output / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Core transcript no longer matches its recorded hash: {name}")
    for waveform in core["waveforms"]:
        if hashlib.sha256((output / waveform["file"]).read_bytes()).hexdigest() != waveform["sha256"]:
            raise RuntimeError(f"Waveform no longer matches its recorded hash: {waveform['file']}")
    return reconcile_core_results(output, core)


def expected_tests(directory: Path) -> set[tuple[str, str, str]]:
    records = set()
    for source in directory.glob("test*.py"):
        for node in ast.walk(ast.parse(source.read_text())):
            if isinstance(node, ast.ClassDef):
                for method in node.body:
                    if isinstance(method, ast.FunctionDef) and method.name.startswith("test_"):
                        records.add((method.name, source.stem, node.name))
    if not records:
        raise RuntimeError(f"No unittest methods found in {directory}")
    return records


def validate_test_log(transcript: str, expected: set[tuple[str, str, str]]) -> int:
    summary = re.search(r"Ran (\d+) tests in [^\n]+\n\nOK\s*$", transcript)
    observed = []
    for name, module, cls, suffix in re.findall(
            r"^(test_\w+) \((\w+)\.(\w+)(?:\.(test_\w+))?\) \.\.\. ok$", transcript, re.M):
        if suffix and suffix != name:
            raise RuntimeError("Inconsistent unittest identity")
        observed.append((name, module, cls))
    if (not summary or int(summary[1]) != len(expected) or
            len(observed) != len(expected) or set(observed) != expected):
        raise RuntimeError("Incomplete, skipped or mismatched verification test log")
    return len(observed)


def verify_evidence(output: Path) -> int:
    """Called with the output lock held; run guards and bind fresh receipts."""
    invalidate_verification(output, "Consolidated verification started")
    target = output / "verification_checks.json"
    try:
        core_path = output / "results.json"
        core_digest = hashlib.sha256(core_path.read_bytes()).hexdigest()
        core = json.loads(core_path.read_text())
        reconciled = verify_core_inputs(output, core)
        suites = (("tools/tests", "verification_tests.txt"),
                  ("sims/integration", "reconciliation_tests.txt"))
        tests = []
        guard_count = 0
        for directory, filename in suites:
            expected = expected_tests(ROOT / directory)
            command = [sys.executable, "-m", "unittest", "discover", "-s", directory, "-p", "test*.py", "-v"]
            result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=120)
            atomic_text(output / filename, result.stdout)
            if result.returncode != 0:
                raise RuntimeError(f"Verification test suite failed: {directory}")
            count = validate_test_log(result.stdout, expected)
            tests.append({"command": command, "passed": count, "skipped": 0, "log": filename,
                          "sha256": hashlib.sha256((output / filename).read_bytes()).hexdigest()})
            guard_count += sum(module.startswith("test_digital_regression") for _, module, _ in expected)
        preservation_command = [sys.executable, "tools/verify_phase1_handoff.py"]
        preservation = run(preservation_command)
        audit = json.loads(preservation)
        if (audit.get("status") != "PASS" or audit.get("audit_kind") != "READ_ONLY_STORED_EVIDENCE_CHECK"):
            raise RuntimeError("Phase 1 preservation audit did not pass")
        atomic_text(output / "phase1_preservation.json", preservation)
        reconciled_after = verify_core_inputs(output, core)
        if reconciled_after != reconciled:
            raise RuntimeError("Raw result records changed during consolidated verification")
        if hashlib.sha256(core_path.read_bytes()).hexdigest() != core_digest:
            raise RuntimeError("Core receipt changed during consolidated verification")
        receipt = {"status": "PASS", "verified_utc": datetime.now(timezone.utc).isoformat(),
                   "scope": "Verification-flow guards and stored-evidence preservation; no new physical qualification",
                   "python_tests": tests, "python_tests_passed": sum(test["passed"] for test in tests),
                   "digital_guard_tests_included": guard_count,
                   "core_checks": reconciled_after["core_checks"],
                   "log_reconciliation": reconciled_after,
                   "source_inputs_verified": len(core["source_sha256"]), "core_receipt_sha256": core_digest,
                   "preservation_command": preservation_command,
                   "preservation_receipt_sha256": hashlib.sha256((output / "phase1_preservation.json").read_bytes()).hexdigest(),
                   "frozen_indexed_artifacts": audit["indexed_artifacts"]}
        atomic_text(target, json.dumps(receipt, indent=2) + "\n")
        print(f"PASS consolidated verification: {receipt['python_tests_passed']} Python tests; bound core and preservation receipts")
        return 0
    except (Exception, KeyboardInterrupt) as error:
        atomic_text(target, json.dumps({"status": "FAIL", "error": f"{type(error).__name__}: {error}",
                                      "verified_utc": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n")
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reports/digital/latest"))
    parser.add_argument("--seed", type=lambda s: int(s, 0), default=0x5A17)
    parser.add_argument("--random-ops", type=int, default=2048)
    parser.add_argument("--verify-evidence", action="store_true",
                        help="verify an existing core PASS, run Python suites and preservation audit, and publish the consolidated receipt")
    args = parser.parse_args()
    if not 0 <= args.seed <= 0xFFFFFFFF or args.random_ops < 2048:
        parser.error("seed must fit 32 bits; at least 2048 random operations are required")
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "reports" / "digital"):
        parser.error("--output must be inside reports/digital; source and frozen delivery paths are protected")
    output.mkdir(parents=True, exist_ok=True)
    with output_lock(output):
        if args.verify_evidence:
            return verify_evidence(output)
        invalidate_verification(output, "New core regression started; consolidated verification must be rerun")
        state = {"status": "RUNNING", "started_utc": datetime.now(timezone.utc).isoformat(),
                 "requested_seed": args.seed, "requested_random_ops": args.random_ops}
        write_receipt(output, state)
        atomic_text(output / "summary.md", "# Phase 2 digital regression\n\nStatus: **RUNNING / INCOMPLETE**.\n")
        try:
            for tool in ("iverilog", "vvp"):
                if not shutil.which(tool):
                    raise RuntimeError(f"{tool} is unavailable; run scripts/run_rtl.sh through tools/sram-eda")
            return execute_regression(args, output, state)
        except (Exception, KeyboardInterrupt) as error:
            state.update(status="FAIL", error=f"{type(error).__name__}: {error}",
                         finished_utc=datetime.now(timezone.utc).isoformat())
            atomic_text(output / "summary.md", "# Phase 2 digital regression\n\nStatus: **FAIL**. See `results.json`.\n")
            write_receipt(output, state)
            raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.TimeoutExpired, OSError, ValueError, StopIteration) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
