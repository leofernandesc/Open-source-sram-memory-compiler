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
            "verdict": "INCONCLUSIVO",
            "overlap": False,
            "release_verified": True,
            "initial_idle_bridged": {"samples": 4},
            "initial_idle_probe": {"release_verified": True},
            "strong_check": {"weak_host_off": True, "overlap": False, "end_ns": 67.0},
        }
        self.record = {"host_payload_ns": 48.0, "previous_operation": "idle"}
        self.lane = {
            "disabled_gate": True,
            "strong_host_on": True,
            "sustained_opposition": None,
            "opposition_with_gate_off": None,
            "charge_response": None,
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

    def test_rejects_read_to_write_static_witness(self):
        self.event["kind"] = "read_to_write"
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

    def test_rejects_explicit_failure(self):
        self.event["verdict"] = "FAIL"
        self.assertFalse(static_witness_eligible(self.event, self.record, self.lane)[0])

    def test_rejects_independent_release_failure(self):
        self.event["release_verified"] = False
        self.assertFalse(static_witness_eligible(self.event, self.record, self.lane)[0])

    def test_rejects_missing_opposition_evidence(self):
        del self.lane["opposition_with_gate_off"]
        self.assertFalse(static_witness_eligible(self.event, self.record, self.lane)[0])

    def test_rejects_nonfinite_witness(self):
        self.lane["quiet_suffix"]["conservative_ps"] = float("nan")
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
            "cycles": {str(i): {"verdict": "PASS", "operation": "idle", "ownership": "PASS"} for i in range(18)},
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

    def static_case(self):
        waveform = self.run / "waveform.dat"
        waveform.write_text("time v(data0)\n0 0\n4.79e-8 0\n4.8e-8 0\n4.81e-8 0\n4.82e-8 0\n6.7e-8 0\n3.7e-7 0\n")
        digest = hashlib.sha256(waveform.read_bytes()).hexdigest()
        receipt_path = self.run / "simulation.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["waveform_sha256"] = digest
        receipt_path.write_text(json.dumps(receipt))
        analysis_path = self.run / "analysis.json"
        analysis = json.loads(analysis_path.read_text())
        analysis.update(samples=7, waveform_sha256=digest, verdict="INCONCLUSIVO")
        analysis["cycles"]["2"].update(operation="write", ownership="INCONCLUSIVO")
        analysis_path.write_text(json.dumps(analysis))
        fixture_path = self.run / "fixture.json"
        fixture = json.loads(fixture_path.read_text())
        fixture["cycles"][2].update(operation="write", previous_operation="idle", expected=0, host_payload_ns=48.0)
        fixture_path.write_text(json.dumps(fixture))
        ownership_path = self.run / "revised_ownership.json"
        ownership = json.loads(ownership_path.read_text())
        lanes = [dict(bit=bit, disabled_gate=True, strong_host_on=True,
                      sustained_opposition=None, opposition_with_gate_off=None,
                      quiet_suffix={"actual_samples": 4, "conservative_ps": 80.0},
                      charge_response=None if bit == 0 else {"settled": True})
                 for bit in range(8)]
        ownership[2].update(kind="write", operation="write", verdict="INCONCLUSIVO",
                            overlap=False, release_verified=True,
                            initial_idle_bridged={"samples": 4},
                            initial_idle_probe={"release_verified": True},
                            strong_check={"weak_host_off": True, "overlap": False,
                                          "end_ns": 67.0, "bits": lanes})
        ownership_path.write_text(json.dumps(ownership))
        return ownership, ownership_path

    def test_static_payload_positive(self):
        self.static_case()
        report = audit(self.run, self.root / "positive.json")
        self.assertEqual(report["supplemental_verdict"], "PASS_WITH_STATIC_PAYLOAD_WITNESS")

    def test_static_payload_cannot_mask_failure_on_other_lane(self):
        ownership, path = self.static_case()
        ownership[2]["strong_check"]["bits"][1]["disabled_gate"] = False
        path.write_text(json.dumps(ownership))
        report = audit(self.run, self.root / "negative.json")
        self.assertEqual(report["supplemental_verdict"], "INCONCLUSIVE")
        self.assertFalse(report["ownership_pass_or_static_witness"])

    def test_static_payload_cannot_mask_real_contention(self):
        ownership, path = self.static_case()
        ownership[2]["strong_check"]["bits"][1]["sustained_opposition"] = {"conservative_ps": 80}
        path.write_text(json.dumps(ownership))
        self.assertEqual(audit(self.run, self.root / "negative.json")["supplemental_verdict"], "INCONCLUSIVE")

    def test_static_payload_cannot_mask_disabled_host_driver(self):
        ownership, path = self.static_case()
        ownership[2]["strong_check"]["bits"][0]["strong_host_on"] = False
        path.write_text(json.dumps(ownership))
        self.assertEqual(audit(self.run, self.root / "negative.json")["supplemental_verdict"], "INCONCLUSIVE")

    def test_all_ownership_pass_does_not_mask_functional_fail(self):
        path = self.run / "analysis.json"
        analysis = json.loads(path.read_text())
        analysis["verdict"] = "FAIL"
        analysis["cycles"]["2"]["verdict"] = "FAIL"
        path.write_text(json.dumps(analysis))
        self.assertEqual(audit(self.run, self.root / "negative.json")["supplemental_verdict"], "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
