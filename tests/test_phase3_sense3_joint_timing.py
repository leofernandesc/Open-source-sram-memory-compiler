"""Focused software checks for the archived timing comparison."""

import unittest

import numpy as np

from audit_phase3_sense3_joint_timing import current_exposure, verify_source


class JointTimingAuditTest(unittest.TestCase):
    def test_integral_resolves_current_zero_between_native_points(self):
        result = current_exposure(np.array([0., 1.]), np.array([-2e-6, 2e-6]))
        self.assertAlmostEqual(result["integral_abs_id_fc"], 1.)
        self.assertAlmostEqual(result["peak_ua"], 2.)
        self.assertAlmostEqual(result["cumulative_10_50_90_ns"][1], .5)

    def test_pwl_must_be_zero_outside_the_two_rise_interventions(self):
        head = "VSHIFT sclk_driver rc8562"
        verify_source(f"{head} PWL(0n 0 26n 0 26.1n -.3 27n 0 59n 0)", head)
        with self.assertRaisesRegex(ValueError, "active outside"):
            verify_source(f"{head} PWL(0n 0 26.1n -.3 27n 0 59n 0)", head)


if __name__ == "__main__":
    unittest.main()
