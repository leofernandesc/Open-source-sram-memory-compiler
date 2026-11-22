"""Software-only checks of the tail branch cut and its causal gate."""

import unittest

import numpy as np

from phase3_sense3_precondition import pwl_tokens
from phase3_sense3_tail_only import (
    HISTORY, LOCAL_R, ORIGINAL_R, REFERENCE, START, decision, localized_slice, series_stimulus,
)


class TailOnlyTest(unittest.TestCase):
    def test_localized_slice_changes_only_shared_side_of_r76(self):
        original = (HISTORY / "control/slice.spice").read_text()
        binding = (REFERENCE / "binding.spice").read_text()
        altered, nodes = localized_slice(original, binding)
        self.assertEqual(altered.replace(LOCAL_R, ORIGINAL_R), original)
        self.assertIn("X351", nodes["rc8585"])
        self.assertNotIn("X521", nodes["rc8585"])
        with self.assertRaisesRegex(ValueError, "branch fanout"):
            localized_slice(original, binding + "\nC99999 rc8585 rc8584 1f\n")

    def test_series_pulse_zero_until_c16_and_during_falls(self):
        t = np.linspace(188, 247, 5901)
        volts = np.clip(t-214, 0, 1) + np.clip(t-234, 0, 1)
        source, _ = series_stimulus(t, volts)
        head, pairs = pwl_tokens(source)
        self.assertEqual(head, "VTAIL tail_series rc8571")
        ts, vs = np.asarray(pairs, dtype=float).T
        np.testing.assert_allclose(np.interp(np.array([194., 204., 213.8, 224., 244.])-START, ts, vs), 0)
        self.assertAlmostEqual(np.interp(214.5-START, ts, vs), -.182)

    def test_verdict_is_c16_and_requires_capture_and_isolation(self):
        c16 = {"checks": {"isolated": True}, "trial": {"decision": "CORRECT", "correct_d_until_capture": [{}]}}
        c17 = {"checks": {"isolated": False}, "trial": {"decision": "WRONG"}}
        self.assertEqual(decision([c16, c17], True), "TAIL_ONLY_SUFFICIENCY_SUPPORTED")
        c16["checks"]["isolated"] = False
        self.assertEqual(decision([c16, c17], True), "INCONCLUSIVE")
        c16["checks"]["isolated"] = True
        c16["trial"]["correct_d_until_capture"] = None
        self.assertEqual(decision([c16, c17], True), "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
