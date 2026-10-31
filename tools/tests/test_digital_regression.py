"""Guard the regression entry point against false PASS and unsafe output paths."""
import importlib.util
import copy
from contextlib import redirect_stderr
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "run_digital_regression.py"
spec = importlib.util.spec_from_file_location("digital_regression", SOURCE)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
PROJECT = SOURCE.parents[1]


def populate_project(root):
    for source in runner.input_paths(PROJECT):
        target = root / source.relative_to(PROJECT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def valid_result():
    return {"depth": 4, "seed": 23063, "random_ops": 2048,
            "transactions": 2064, "checks": 12385, "control_transitions": 64,
            "controls": [256, 264, 264, 256, 256, 256, 256, 256],
            "read_addresses": [66, 66, 66, 66],
            "write_addresses": [66, 66, 66, 66]}


def raw_core_fixture(output):
    """Synthetic raw records for testing reconciliation, not SRAM simulation."""
    (output / "logs").mkdir(parents=True)
    hashes = {}

    def write_log(name, text):
        relative = f"logs/{name}.txt"
        (output / relative).write_text(text)
        hashes[relative] = runner.hashlib.sha256((output / relative).read_bytes()).hexdigest()

    cases = []
    for view, depth in runner.MEMORY_CASES:
        result = valid_result()
        result["depth"] = depth
        counts = [264 // depth + (index < 264 % depth) for index in range(depth)]
        result["read_addresses"] = list(counts)
        result["write_addresses"] = list(counts)
        write_log(f"{view}_{depth}x8", "RESULT " + json.dumps(result) + "\nPASS SRAM transaction regression\n")
        cases.append({"view": view, "status": "PASS", **result})
    write_log("control", 'CONTROL_RESULT {"checks":96,"controls":8,"addresses":4}\n')
    negatives = []
    for depth in runner.UNSUPPORTED_DEPTHS:
        case = f"reject_depth_{depth}"
        message = f"Unsupported SRAM depth: {depth}"
        scope = "tb_sram_depth_guard.dut.invalid_depth"
        write_log(case, f"FATAL: rtl/sram_model.v:20: {message}\n Time: 0 Scope: {scope}\n")
        negatives.append({"case": case, "expected_cause": f"unsupported_depth:{depth}",
                          "message": message, "scope": scope})
    for mutant in runner.MUTATIONS:
        case = f"mutant_{mutant}"
        message = "falling/result transaction=2 controls=001 address=0 DATA=ff expected=00"
        scope = "tb_sram_4x8.expect_bus"
        write_log(case, f"FATAL: tb/tb_sram_4x8.sv:42: {message}\n Time: 1 Scope: {scope}\n")
        negatives.append({"case": case, "expected_cause": "scoreboard", "message": message, "scope": scope})
    return {"cases": cases, "seed": 23063, "controller": dict(runner.CONTROL_RESULT),
            "rejected_depths": list(runner.UNSUPPORTED_DEPTHS), "detected_mutants": list(runner.MUTATIONS),
            "negative_results": negatives, "log_sha256": hashes}


class DigitalRunnerTests(unittest.TestCase):
    def test_frozen_output_is_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frozen = root / "release" / "phase1"
            frozen.mkdir(parents=True)
            receipt = frozen / "results.json"
            receipt.write_text("protected\n")
            with redirect_stderr(io.StringIO()), patch.object(runner, "ROOT", root), patch("sys.argv", [
                    "runner", "--output", str(frozen)]), self.assertRaises(SystemExit) as error:
                runner.main()
            self.assertEqual(error.exception.code, 2)
            self.assertEqual(receipt.read_text(), "protected\n")

    def test_failed_compile_cannot_leave_previous_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            populate_project(root)
            output = root / "reports" / "digital" / "failure"
            output.mkdir(parents=True)
            (output / "results.json").write_text('{"status":"PASS"}\n')
            (output / "verification_checks.json").write_text('{"status":"PASS"}\n')
            stub_directory = root / "bin"
            stub_directory.mkdir()
            for tool in ("iverilog", "vvp"):
                stub = stub_directory / tool
                stub.write_text("#!/bin/sh\nprintf 'injected compile failure\\n'\nexit 1\n")
                stub.chmod(0o755)
            with patch.object(runner, "ROOT", root), patch.dict(os.environ, {
                    "PATH": str(stub_directory) + os.pathsep + os.environ.get("PATH", "")}), \
                    patch("sys.argv", ["runner", "--output", str(output)]), \
                    self.assertRaisesRegex(RuntimeError, "Unexpected return code 1"):
                runner.main()
            self.assertEqual(json.loads((output / "results.json").read_text())["status"], "FAIL")
            self.assertEqual(json.loads((output / "verification_checks.json").read_text())["status"], "NOT_CURRENT")
            self.assertIn("injected compile failure", (output / "logs/verilog2005_compile.txt").read_text())

    def test_random_count_below_acceptance_minimum_is_rejected(self):
        with redirect_stderr(io.StringIO()), patch("sys.argv", ["runner", "--random-ops", "2047"]), \
                self.assertRaises(SystemExit) as error:
            runner.main()
        self.assertEqual(error.exception.code, 2)

    def test_missing_tool_replaces_previous_pass_with_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "reports/digital/preflight"
            output.mkdir(parents=True)
            (output / "results.json").write_text('{"status":"PASS"}\n')
            with patch.object(runner, "ROOT", root), patch("sys.argv", [
                    "runner", "--output", str(output)]), patch.object(runner.shutil, "which", return_value=None), \
                    self.assertRaisesRegex(RuntimeError, "iverilog is unavailable"):
                runner.main()
            self.assertEqual(json.loads((output / "results.json").read_text())["status"], "FAIL")

    def test_busy_output_does_not_overwrite_active_owner(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "reports/digital/owned"
            output.mkdir(parents=True)
            receipt = output / "results.json"
            receipt.write_text('{"status":"RUNNING","owner":"first"}\n')
            before = receipt.read_bytes()
            aggregate = output / "verification_checks.json"
            aggregate.write_text('{"status":"NOT_CURRENT","owner":"first"}\n')
            aggregate_before = aggregate.read_bytes()
            with runner.output_lock(output), patch.object(runner, "ROOT", root), patch("sys.argv", [
                    "runner", "--output", str(output)]), \
                    self.assertRaisesRegex(RuntimeError, "already in use"):
                runner.main()
            self.assertEqual(receipt.read_bytes(), before)
            self.assertEqual(aggregate.read_bytes(), aggregate_before)
            # The lock is reusable after its owner exits.
            with runner.output_lock(output):
                pass

    def test_snapshot_keeps_compilation_bytes_and_detects_source_edits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            populate_project(root)
            work = root / "build/run"
            work.mkdir(parents=True)
            snapshot = runner.SourceSnapshot(root, work)
            source = root / "rtl/sram_model.v"
            saved = (snapshot.directory / "rtl/sram_model.v").read_bytes()
            source.write_text(source.read_text().replace("(read_q && live_read)", "1'b1"))
            self.assertEqual((snapshot.directory / "rtl/sram_model.v").read_bytes(), saved)
            self.assertEqual((snapshot.directory / "rtl/sram_model.v").stat().st_mode & 0o222, 0)
            with self.assertRaisesRegex(RuntimeError, "Source inputs changed"):
                snapshot.verify_unchanged()

    def test_changes_to_the_snapshot_itself_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            populate_project(root)
            work = root / "build/run"
            work.mkdir(parents=True)
            snapshot = runner.SourceSnapshot(root, work)
            target = snapshot.directory / "rtl/sram_model.v"
            target.chmod(0o644)
            target.write_text("changed snapshot\n")
            with self.assertRaisesRegex(RuntimeError, "Source inputs changed"):
                snapshot.verify_unchanged()

    def test_new_inputs_during_a_run_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            populate_project(root)
            work = root / "build/run"
            work.mkdir(parents=True)
            snapshot = runner.SourceSnapshot(root, work)
            (root / "rtl/new_module.v").write_text("module new_module; endmodule\n")
            with self.assertRaisesRegex(RuntimeError, "file set differs"):
                snapshot.verify_unchanged()

    def test_file_lists_cannot_escape_the_captured_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            populate_project(root)
            (root / "rtl/model.f").write_text("/tmp/outside.v\n")
            work = root / "build/run"
            work.mkdir(parents=True)
            snapshot = runner.SourceSnapshot(root, work)
            with self.assertRaisesRegex(RuntimeError, "outside the captured source set"):
                runner.file_list("model.f", snapshot)

    def test_matching_case_is_accepted(self):
        runner.validate_case(valid_result(), 4, 23063, 2048)

    def test_wrong_executed_depth_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "depth=4, expected 8"):
            runner.validate_case(valid_result(), 8, 23063, 2048)

    def test_wrong_seed_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "seed="):
            runner.validate_case(valid_result(), 4, 101, 2048)

    def test_fewer_random_operations_than_requested_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "random_ops="):
            runner.validate_case(valid_result(), 4, 23063, 4096)

    def test_coverage_vectors_must_have_the_requested_size(self):
        for field in ("controls", "read_addresses", "write_addresses"):
            with self.subTest(field=field):
                result = valid_result()
                result[field] = result[field][:-1]
                with self.assertRaisesRegex(RuntimeError, "Incomplete regression coverage"):
                    runner.validate_case(result, 4, 23063, 2048)

    def test_invalid_coverage_counter_values_are_rejected(self):
        for counter in (0, -1, True, "66"):
            with self.subTest(counter=counter):
                result = valid_result()
                result["read_addresses"][0] = counter
                with self.assertRaisesRegex(RuntimeError, "Incomplete regression coverage"):
                    runner.validate_case(result, 4, 23063, 2048)

    def test_inconsistent_counter_totals_are_rejected(self):
        result = valid_result()
        result["write_addresses"][0] += 1
        with self.assertRaisesRegex(RuntimeError, "Inconsistent operation/address"):
            runner.validate_case(result, 4, 23063, 2048)

    def test_reserved_result_fields_cannot_override_the_runner(self):
        result = valid_result()
        result["status"] = "PASS"
        with self.assertRaisesRegex(RuntimeError, "Unexpected regression result fields"):
            runner.validate_case(result, 4, 23063, 2048)

    def test_missing_or_duplicate_result_records_are_rejected(self):
        for transcript in ("PASS only\n", "RESULT {}\nRESULT {}\n"):
            with self.subTest(transcript=transcript), self.assertRaisesRegex(RuntimeError, "exactly one"):
                runner.extract_result(transcript, "RESULT ")

    def test_scoreboard_failure_has_the_expected_message_and_scope(self):
        transcript = ("FATAL: tb/tb_sram_4x8.sv:42: falling/result transaction=2 controls=001 address=0 DATA=ff expected=00\n"
                      "       Time: 1000  Scope: tb_sram_4x8.expect_bus\n")
        observed = runner.validate_expected_failure(transcript, "scoreboard")
        self.assertEqual(observed["scope"], "tb_sram_4x8.expect_bus")
        self.assertEqual(observed["expected_cause"], "scoreboard")

    def test_watchdog_is_not_a_detected_mutant(self):
        transcript = ("FATAL: tb/tb_sram_4x8.sv:220: Testbench watchdog\n"
                      "       Time: 1000000  Scope: tb_sram_4x8\n")
        with self.assertRaisesRegex(RuntimeError, "Unexpected failure cause for scoreboard"):
            runner.validate_expected_failure(transcript, "scoreboard")

    def test_wrong_scope_or_unrelated_fatal_is_rejected(self):
        for message, scope in (
                ("falling/result transaction=2 controls=001 address=0 DATA=ff expected=00", "unrelated_module"),
                ("File could not be opened", "tb_sram_4x8.expect_bus")):
            transcript = f"FATAL: tb/test.sv:1: {message}\n Time: 1 Scope: {scope}\n"
            with self.subTest(message=message), self.assertRaisesRegex(RuntimeError, "Unexpected failure cause"):
                runner.validate_expected_failure(transcript, "scoreboard")

    def test_ambiguous_fatal_diagnostics_are_rejected(self):
        fatal = ("FATAL: tb/test.sv:1: falling/result transaction=2 controls=001 address=0 DATA=ff expected=00\n"
                 " Time: 1 Scope: tb_sram_4x8.expect_bus\n")
        with self.assertRaisesRegex(RuntimeError, "ambiguous fatal"):
            runner.validate_expected_failure(fatal + fatal, "scoreboard")

    def test_depth_guard_failure_must_match_the_requested_depth(self):
        transcript = ("FATAL: rtl/sram_model.v:20: Unsupported SRAM depth: 5\n"
                      "       Time: 0  Scope: tb_sram_depth_guard.dut.invalid_depth\n")
        self.assertEqual(runner.validate_expected_failure(transcript, "unsupported_depth:5")["expected_cause"],
                         "unsupported_depth:5")
        with self.assertRaisesRegex(RuntimeError, "Unexpected failure cause"):
            runner.validate_expected_failure(transcript, "unsupported_depth:3")

    def test_crashes_and_other_exit_codes_are_not_expected_failures(self):
        for returncode in (0, 2, -6, -11):
            result = subprocess.CompletedProcess(["vvp"], returncode, stdout="FATAL: unrelated failure\n")
            with self.subTest(returncode=returncode), patch.object(runner.subprocess, "run", return_value=result), \
                    self.assertRaisesRegex(RuntimeError, "Unexpected return code"):
                runner.run(["vvp"], expected_failure=True)

    def test_complete_unittest_logs_accept_both_supported_formats(self):
        expected = {("test_one", "test_sample", "Example")}
        for identifier in ("test_sample.Example", "test_sample.Example.test_one"):
            log = f"test_one ({identifier}) ... ok\n\nRan 1 tests in 0.1s\n\nOK\n"
            with self.subTest(identifier=identifier):
                self.assertEqual(runner.validate_test_log(log, expected), 1)

    def test_missing_skipped_or_duplicate_test_results_are_rejected(self):
        expected = {("test_one", "test_sample", "Example")}
        for log in ("Ran 1 tests in 0.1s\n\nOK\n",
                    "test_one (test_sample.Example) ... skipped 'tool missing'\n\nRan 1 tests in 0.1s\n\nOK (skipped=1)\n",
                    "test_one (test_sample.Example) ... ok\ntest_one (test_sample.Example) ... ok\n\nRan 1 tests in 0.1s\n\nOK\n"):
            with self.subTest(log=log), self.assertRaisesRegex(RuntimeError, "mismatched verification"):
                runner.validate_test_log(log, expected)

    def test_failed_core_cannot_keep_a_consolidated_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "results.json").write_text('{"status":"FAIL","schema_version":3}\n')
            aggregate = output / "verification_checks.json"
            aggregate.write_text('{"status":"PASS"}\n')
            with self.assertRaisesRegex(RuntimeError, "current passing core regression"):
                runner.verify_evidence(output)
            self.assertEqual(json.loads(aggregate.read_text())["status"], "FAIL")

    def test_reconciled_total_comes_from_all_raw_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            core = raw_core_fixture(output)
            parsed = runner.reconcile_core_results(output, core)
            self.assertEqual(parsed["core_checks"], 5 * 12385 + 96)
            self.assertEqual(parsed["memory_cases"], 5)
            self.assertEqual(parsed["negative_cases"], 12)
            self.assertEqual(len(parsed["result_log_sha256"]), 18)

    def test_altered_memory_check_count_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            core = raw_core_fixture(output)
            core["cases"][0]["checks"] += 1000000
            with self.assertRaisesRegex(RuntimeError, "Core summary differs from raw log: memory cases"):
                runner.reconcile_core_results(output, core)

    def test_altered_controller_check_count_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            core = raw_core_fixture(output)
            core["controller"]["checks"] += 1000000
            with self.assertRaisesRegex(RuntimeError, "Core summary differs from raw log: controller"):
                runner.reconcile_core_results(output, core)

    def test_all_case_metadata_is_reconciled_not_only_check_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            original = raw_core_fixture(output)
            for field, value in (("transactions", 9999), ("seed", 101), ("depth", 8),
                                 ("controls", [1] * 8), ("status", "FAIL")):
                core = copy.deepcopy(original)
                core["cases"][0][field] = value
                with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, "Core summary differs from raw log"):
                    runner.reconcile_core_results(output, core)

    def test_missing_duplicate_or_reordered_cases_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            original = raw_core_fixture(output)
            for cases in (original["cases"][:-1], original["cases"] + [original["cases"][0]],
                          list(reversed(original["cases"]))):
                core = copy.deepcopy(original)
                core["cases"] = cases
                with self.subTest(cases=cases), self.assertRaisesRegex(RuntimeError, "memory cases"):
                    runner.reconcile_core_results(output, core)

    def test_negative_diagnostics_are_reconciled_with_raw_logs(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            core = raw_core_fixture(output)
            core["negative_results"][0]["message"] = "different failure"
            with self.assertRaisesRegex(RuntimeError, "negative diagnostics"):
                runner.reconcile_core_results(output, core)

    def test_missing_result_log_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            core = raw_core_fixture(output)
            del core["log_sha256"]["logs/model_4x8.txt"]
            with self.assertRaisesRegex(RuntimeError, "Required result log is missing"):
                runner.reconcile_core_results(output, core)

    def test_modified_raw_log_without_matching_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            core = raw_core_fixture(output)
            path = output / "logs/model_4x8.txt"
            path.write_text(path.read_text() + "changed log\n")
            with self.assertRaisesRegex(RuntimeError, "has changed"):
                runner.reconcile_core_results(output, core)

    def test_duplicate_result_records_fail_even_with_updated_log_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            core = raw_core_fixture(output)
            path = output / "logs/model_4x8.txt"
            path.write_text(path.read_text() + "RESULT {}\n")
            core["log_sha256"]["logs/model_4x8.txt"] = runner.hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(RuntimeError, "exactly one RESULT"):
                runner.reconcile_core_results(output, core)

    def test_numerically_equal_but_different_json_types_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            core = raw_core_fixture(output)
            core["cases"][0]["checks"] = float(core["cases"][0]["checks"])
            with self.assertRaisesRegex(RuntimeError, "memory cases"):
                runner.reconcile_core_results(output, core)


if __name__ == "__main__":
    unittest.main()
