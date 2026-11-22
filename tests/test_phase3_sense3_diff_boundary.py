"""Offline checks of the differential boundary audit."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from audit_phase3_sense3_diff_boundary import audit, evaluate


class BoundaryAuditTest(unittest.TestCase):
    def test_advance_preserves_common_mode_and_reports_splice(self):
        time = np.array([0., 1., 2., 3.])
        bl = np.array([1.8, 1.7, 1.2, 0.2])
        blb = np.array([1.8, 1.82, 1.75, 1.7])
        case = dict(low_ns=.5, high_ns=1.5, capture_ns=2., tail20_ns=1.0,
                    early_input_window_ns=[.95, 1.05], cycle=16)
        result = evaluate(time, bl, blb, np.full(4, 1.8), case)
        np.testing.assert_allclose(result["bl_required_v"] + result["blb_required_v"],
                                   result["bl_control_v"] + result["blb_control_v"])
        marker = result["summary"]["tail20"]
        self.assertAlmostEqual(marker["blb_control_v"], 1.82)
        self.assertAlmostEqual(marker["delta_advanced_v"], .12 + .182 * .43)
        self.assertGreater(result["summary"]["hard_splice_b_jump_v"]["late_enable"], 0.)

    def test_archive_has_only_two_exact_pairs_and_preserves_coupling(self):
        with TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            output = Path(directory)
            audit(output)
            manifest = json.loads((output / "manifest.json").read_text())
        self.assertEqual(manifest["card_counts"], {"X": 17, "R": 28, "C": 93})
        self.assertAlmostEqual(manifest["cap_ff_by_group"]["BLxBLB"], 15.9883)
        observed = [pair["role"] for pair in manifest["candidates"] if pair["waveform"] == "OBSERVED"]
        self.assertEqual(observed, ["row3_access", "sampler"])
        self.assertTrue(all(not p["measurements"] for p in manifest["candidates"] if p["role"] not in observed))


if __name__ == "__main__":
    unittest.main()
