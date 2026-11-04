"""Reproduce the review failures with real Icarus in disposable project copies."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_digital_regression import PROJECT, populate_project, runner


@unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                     "Run through tools/sram-eda for real Icarus integration tests")
class DigitalIntegrationTests(unittest.TestCase):
    def setUp(self):
        build = PROJECT / "build/digital"
        build.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="runner-test-", dir=build)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        populate_project(self.root)

    def command(self, output, seed=23063):
        return [sys.executable, str(self.root / "tools/run_digital_regression.py"),
                "--output", str(output), "--seed", str(seed)]

    def invoke(self, output, env=None):
        return subprocess.run(self.command(output), cwd=self.root, env=env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)

    def test_fixed_four_word_bench_cannot_pass_the_eight_word_case(self):
        path = self.root / "tb/tb_sram_4x8.sv"
        source = re.sub(r"\bDEPTH\b", "ACTUAL_DEPTH", path.read_text())
        source = source.replace("parameter integer ACTUAL_DEPTH = 4;",
                                "parameter integer DEPTH = 4;\n    localparam integer ACTUAL_DEPTH = 4;")
        path.write_text(source.replace(".ACTUAL_DEPTH(", ".DEPTH("))
        output = self.root / "reports/digital/fixed_depth"
        result = self.invoke(output)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("depth=4, expected 8", result.stdout)
        self.assertEqual(json.loads((output / "results.json").read_text())["status"], "FAIL")

    def test_edit_after_compilation_is_not_certified_as_tested_source(self):
        target = self.root / "rtl/sram_model.v"
        original = target.read_bytes()
        expected_hash = hashlib.sha256(original).hexdigest()
        real_compiler = shutil.which("iverilog")
        binaries = self.root / "bin"
        binaries.mkdir()
        compiler = binaries / "iverilog"
        compiler.write_text(f'''#!{sys.executable}
import subprocess, sys
from pathlib import Path
result = subprocess.run([{real_compiler!r}, *sys.argv[1:]])
if result.returncode == 0 and any('verilog2005.vvp' in arg for arg in sys.argv):
    target = Path({str(target)!r})
    target.write_text(target.read_text().replace('(read_q && live_read)', "1'b1"))
sys.exit(result.returncode)
''')
        compiler.chmod(0o755)
        environment = dict(os.environ, PATH=str(binaries) + os.pathsep + os.environ["PATH"])
        output = self.root / "reports/digital/changed_source"
        result = self.invoke(output, environment)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("Source inputs changed during regression", result.stdout)
        receipt = json.loads((output / "results.json").read_text())
        manifest = json.loads((output / "source_manifest.json").read_text())
        self.assertEqual(receipt["status"], "FAIL")
        self.assertEqual(manifest["source_sha256"]["rtl/sram_model.v"], expected_hash)
        self.assertNotEqual(hashlib.sha256(target.read_bytes()).hexdigest(), expected_hash)
        snapshot = self.root / manifest["snapshot_directory"] / "rtl/sram_model.v"
        self.assertEqual(snapshot.read_bytes(), original)
        # Even after the live edit, each positive case compiled the safe copy.
        self.assertIn("PASS model_32x8", result.stdout)
        self.assertIn("PASS wrapper_4x8", result.stdout)
        self.assertIn("PASS SRAM", (output / "logs/model_4x8.txt").read_text())

    def test_parallel_runs_keep_executables_snapshots_and_waveforms_separate(self):
        seeds = (101, 202)
        outputs = [self.root / "reports/digital" / f"parallel_{seed}" for seed in seeds]
        processes = [subprocess.Popen(self.command(output, seed), cwd=self.root, text=True,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                     for seed, output in zip(seeds, outputs)]
        try:
            reports = []
            for seed, output, process in zip(seeds, outputs, processes):
                transcript, _ = process.communicate(timeout=120)
                self.assertEqual(process.returncode, 0, transcript)
                report = json.loads((output / "results.json").read_text())
                self.assertEqual(report["status"], "PASS")
                self.assertEqual(report["seed"], seed)
                self.assertEqual([case["depth"] for case in report["cases"]], [4, 8, 16, 32, 4])
                expected_cwd = str(self.root / report["snapshot_directory"])
                self.assertTrue(all(command["cwd"] == expected_cwd for command in report["commands"]))
                for waveform in report["waveforms"]:
                    contents = (output / waveform["file"]).read_text()
                    identifier = re.search(r"\$var reg 32 (\S+) seed ", contents).group(1)
                    value = re.search(r"^b([01]+) " + re.escape(identifier) + "$", contents, re.M).group(1)
                    self.assertEqual(int(value, 2), seed)
                reports.append(report)
            self.assertNotEqual(reports[0]["run_directory"], reports[1]["run_directory"])
            self.assertEqual(reports[0]["source_sha256"], reports[1]["source_sha256"])
            self.assertLess(reports[0]["started_utc"], reports[1]["created_utc"])
            self.assertLess(reports[1]["started_utc"], reports[0]["created_utc"])
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate()

    def test_reused_output_invalidates_consolidated_pass_on_success_and_failure(self):
        output = self.root / "reports/digital/reuse"
        first = self.invoke(output)
        self.assertEqual(first.returncode, 0, first.stdout)
        aggregate = output / "verification_checks.json"
        aggregate.write_text(json.dumps({"status": "PASS", "core_receipt_sha256":
                                        hashlib.sha256((output / "results.json").read_bytes()).hexdigest()}))
        second = self.invoke(output)
        self.assertEqual(second.returncode, 0, second.stdout)
        self.assertEqual(json.loads(aggregate.read_text())["status"], "NOT_CURRENT")
        aggregate.write_text('{"status":"PASS"}\n')
        binaries = self.root / "bin"
        binaries.mkdir()
        compiler = binaries / "iverilog"
        compiler.write_text("#!/bin/sh\nprintf 'injected compile error\\n'\nexit 2\n")
        compiler.chmod(0o755)
        environment = dict(os.environ, PATH=str(binaries) + os.pathsep + os.environ["PATH"])
        failed = self.invoke(output, environment)
        self.assertNotEqual(failed.returncode, 0, failed.stdout)
        self.assertIn("Unexpected return code 2", failed.stdout)
        self.assertEqual(json.loads((output / "results.json").read_text())["status"], "FAIL")
        self.assertEqual(json.loads(aggregate.read_text())["status"], "NOT_CURRENT")

    def test_watchdog_only_negative_run_fails_the_campaign(self):
        watchdog = self.root / "watchdog_tb.sv"
        watchdog.write_text('''`timescale 1ns/1ps
module tb_sram_4x8;
    initial begin
        #1;
        $fatal(1, "Testbench watchdog");
    end
endmodule
''')
        real_compiler = shutil.which("iverilog")
        binaries = self.root / "bin"
        binaries.mkdir()
        compiler = binaries / "iverilog"
        compiler.write_text(f'''#!{sys.executable}
import subprocess, sys
args = sys.argv[1:]
if any('/mutant_' in arg and arg.endswith('.vvp') for arg in args):
    args = [{str(watchdog)!r} if arg == 'tb/tb_sram_4x8.sv' else arg for arg in args]
sys.exit(subprocess.run([{real_compiler!r}, *args]).returncode)
''')
        compiler.chmod(0o755)
        environment = dict(os.environ, PATH=str(binaries) + os.pathsep + os.environ["PATH"])
        output = self.root / "reports/digital/watchdog"
        failed = self.invoke(output, environment)
        self.assertNotEqual(failed.returncode, 0, failed.stdout)
        self.assertIn("Unexpected failure cause for scoreboard", failed.stdout)
        self.assertIn("Testbench watchdog", failed.stdout)
        self.assertEqual(json.loads((output / "results.json").read_text())["status"], "FAIL")
        self.assertEqual(json.loads((output / "verification_checks.json").read_text())["status"], "NOT_CURRENT")
        self.assertIn("PASS model_32x8", failed.stdout)

    def test_altered_numeric_summary_cannot_be_consolidated(self):
        output = self.root / "reports/digital/altered_summary"
        completed = self.invoke(output)
        self.assertEqual(completed.returncode, 0, completed.stdout)
        core_path = output / "results.json"
        core = json.loads(core_path.read_text())
        original_count = core["cases"][0]["checks"]
        core["cases"][0]["checks"] += 1000000
        core_path.write_text(json.dumps(core, indent=2) + "\n")
        with runner.output_lock(output), patch.object(runner, "ROOT", self.root), \
                patch.object(runner.subprocess, "run", side_effect=AssertionError("Test suites must not start")) as launch, \
                self.assertRaisesRegex(RuntimeError, "Core summary differs from raw log: memory cases"):
            runner.verify_evidence(output)
        launch.assert_not_called()
        aggregate = json.loads((output / "verification_checks.json").read_text())
        self.assertEqual(aggregate["status"], "FAIL")
        self.assertIn("memory cases", aggregate["error"])
        observed = json.loads(next(line[7:] for line in (output / "logs/model_4x8.txt").read_text().splitlines()
                                   if line.startswith("RESULT ")))
        self.assertEqual(observed["checks"], original_count)
        self.assertEqual(json.loads(core_path.read_text())["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
