"""Offline checks for differential reconstruction and rail feasibility."""

import unittest

import numpy as np

from phase3_sense3_diff_advance import ADVANCE_NS, START, feasible_spans, reconstruct, trajectory


class DifferentialAdvanceTest(unittest.TestCase):
    def test_reconstruction_preserves_common_mode(self):
        bl = np.array([1.4, 1.3, 1.5])
        blb = np.array([1.6, 1.5, 1.52])
        delta = np.array([0.45, 0.2, -0.1])
        trial = reconstruct(bl, blb, delta, 1.8)
        left, right = trial["bl_required_v"], trial["blb_required_v"]
        np.testing.assert_allclose(left + right, bl + blb)
        np.testing.assert_allclose(right - left, delta)
        self.assertTrue(np.all(trial["upper_excess_v"] < 0))

    def test_common_mode_above_supply_disallows_even_zero_differential(self):
        trial = reconstruct(np.array([1.84]), np.array([1.88]), np.array([0.]), 1.8)
        self.assertLess(trial["rail_capacity_v"][0], 0)
        self.assertAlmostEqual(trial["upper_excess_v"][0], .06)

    def test_common_mode_below_supply_can_still_block_the_target(self):
        trial = reconstruct(np.array([1.60]), np.array([1.78]), np.array([.30]), 1.8)
        self.assertAlmostEqual(trial["rail_capacity_v"][0], .22)
        self.assertAlmostEqual(trial["blb_required_v"][0], 1.84)

    def test_feasible_span_solves_both_roots_between_knots(self):
        times = np.array([0., 1., 2.])
        self.assertEqual(feasible_spans(times, np.array([-1., 3., 4.]), np.array([3., 1., -3.])),
                         [[.25, 1.25]])
        self.assertEqual(feasible_spans(times, np.array([-1., -2., -3.])), [])

    def test_time_advance_changes_only_the_differential(self):
        sources = {
            "rc8202": np.array([[0., 1.], [1.8, 1.3]]),
            "rc8216": np.array([[0., 1.], [1.8, 1.8]]),
            "VDD": np.array([[0., 1.], [1.8, 1.8]]),
        }
        trial = trajectory(sources, START + .25)
        self.assertAlmostEqual(trial["delta_advanced_v"] - trial["delta_control_v"], ADVANCE_NS * .5)
        self.assertAlmostEqual(trial["common_v"], 1.8 - .25 * .25)


if __name__ == "__main__":
    unittest.main()
