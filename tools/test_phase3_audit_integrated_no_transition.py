#!/usr/bin/env python3
"""Fast negative tests for the integrated static-payload audit gates."""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase3_audit_integrated_no_transition import (  # noqa: E402
    audit,
    static_witness_eligible,
    validate_receipts,
)


class StaticWitnessEligibilityTests(unittest.TestCase):
    def setUp(self):
        self.event = {
            "kind": "write",
            "operation": "write",
            "overlap": False,
            "strong_check": {"weak_host_off": True, "end_ns": 67.0},
        }
        self.record = {"host_payload_ns": 48.0}
        self.lane = {
            "disabled_gate": True,
            "strong_host_on": True,
            "opposition_with_gate_off": None,
            "quiet_suffix": {"actual_samples": 4, "conservative_ps": 80.0},
        }

    def test_accepts_complete_static_payload_witness(self):
        self.assertEqual(static_witness_eligible(self.event, self.record, self.lane),
                         (True, "eligible static payload lane"))

    def test_rejects_overlap(self):
        self.event["overlap"] = True
        self.assertFalse(static_witness_eligible(self.event, self.record, self.lane)[0])

    def test_rejects_non_write_ownership_event(self):
        self.event["kind"] = "read_to_idle"
        self.assertFalse(static_witness_eligible(self.event, self.record, self.lane)[0])

    def test_rejects_insufficient_raw_samples(self):
        self.lane["quiet_suffix"]["actual_samples"] = 2
        self.assertFalse(static_witness_eligible(self.event, self.record, self.lane)[0])

    def test_rejects_short_static_window(self):
        self.lane["quiet_suffix"]["conservative_ps"] = 49.9
        self.assertFalse(static_witness_eligible(self.event, self.record, self.lane)[0])

    def test_rejects_missing_host_or_macro_isolation(self):
        self.event["strong_check"]["weak_host_off"] = False
        self.assertFalse(static_witness_eligible(self.event, self.record, self.lane)[0])


class ReceiptIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name)
        (self.run / "waveform.dat").write_text("time v(data0)\n0 0\n")
        waveform_sha = hashlib.sha256((self.run / "waveform.dat").read_bytes()).hexdigest()
        (self.run / "simulation.json").write_text(json.dumps({
            "status": "COMPLETED",
            "returncode": 0,
            "errors": [],
            "simulation_ns": 370.0,
            "waveform_sha256": waveform_sha,
            "model_check": {"sha256_matches": 319},
        }))
        (self.run / "model_hashes.json").write_text(json.dumps({f"model_{i}": "sha" for i in range(319)}))
        self.analysis = {
            "waveform_sha256": waveform_sha,
            "samples": 1,
            "cycles": {str(i): {} for i in range(18)},
        }
        self.fixture = {"cycles": [{"cycle": i} for i in range(18)]}
        self.ownership = [{"cycle": i} for i in range(18)]

    def test_accepts_complete_verified_receipts(self):
        result = validate_receipts(self.run, self.analysis, self.fixture, self.ownership)
        self.assertEqual(result["cycle_count"], 18)
        self.assertEqual(result["model_hash_count"], 319)

    def test_rejects_waveform_hash_mismatch(self):
        self.analysis["waveform_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Analysis is not tied"):
            validate_receipts(self.run, self.analysis, self.fixture, self.ownership)

    def test_rejects_incomplete_cycle_coverage(self):
        self.ownership.pop()
        with self.assertRaisesRegex(ValueError, "18 unique cycles"):
            validate_receipts(self.run, self.analysis, self.fixture, self.ownership)

    def test_rejects_duplicate_cycle_ids(self):
        self.ownership[-1]["cycle"] = 16
        with self.assertRaisesRegex(ValueError, "unique cycles"):
            validate_receipts(self.run, self.analysis, self.fixture, self.ownership)

    def test_rejects_failed_simulation_receipt(self):
        receipt_path = self.run / "simulation.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["returncode"] = 1
        receipt_path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "failed process"):
            validate_receipts(self.run, self.analysis, self.fixture, self.ownership)


class ImmutableOutputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / "input"
        self.run.mkdir()
        (self.run / "waveform.dat").write_text("time\n0\n0.00000037\n")
        waveform_sha = hashlib.sha256((self.run / "waveform.dat").read_bytes()).hexdigest()
        (self.run / "simulation.json").write_text(json.dumps({
            "status": "COMPLETED", "returncode": 0, "errors": [],
            "simulation_ns": 370.0, "waveform_sha256": waveform_sha,
            "model_check": {"sha256_matches": 319},
        }))
        (self.run / "model_hashes.json").write_text(json.dumps({f"m{i}": "sha" for i in range(319)}))
        (self.run / "analysis.json").write_text(json.dumps({
            "waveform_sha256": waveform_sha,
            "samples": 2,
            "verdict": "PASS",
            "cycles": {str(i): {"verdict": "PASS", "operation": "idle"} for i in range(18)},
        }))
        (self.run / "fixture.json").write_text(json.dumps({
            "cycles": [{"cycle": i, "operation": "idle"} for i in range(18)],
        }))
        (self.run / "revised_ownership.json").write_text(json.dumps([
            {"cycle": i, "verdict": "PASS"} for i in range(18)
        ]))

    def test_audit_writes_outside_and_verifies_inputs_unchanged(self):
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.run.iterdir()}
        output = self.root / "derived" / "static_payload_witness.json"
        report = audit(self.run, output)
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.run.iterdir()}
        self.assertEqual(before, after)
        self.assertTrue(report["input_unchanged_during_audit"])
        self.assertEqual(report["supplemental_verdict"], "NO_SUPPLEMENT_REQUIRED")
        self.assertTrue(output.is_file())

    def test_audit_refuses_output_inside_input_run(self):
        before = sorted(p.name for p in self.run.iterdir())
        with self.assertRaisesRegex(ValueError, "outside the immutable input"):
            audit(self.run, self.run / "static_payload_witness.json")
        self.assertEqual(before, sorted(p.name for p in self.run.iterdir()))


if __name__ == "__main__":
    unittest.main()
