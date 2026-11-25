"""Regression tests for full-cycle supply energy integration boundaries."""

import unittest

import numpy as np

from phase3_power_integrated_pilot import energy_window


class SupplyEnergyWindowTest(unittest.TestCase):
    def test_integrates_interpolated_window(self):
        time_s = np.array([0., 1e-9, 2e-9, 3e-9])
        power_w = np.array([0., 2., 2., 0.])
        self.assertAlmostEqual(energy_window(time_s, power_w, 0.5e-9, 2.5e-9),
                               3.5e-9, delta=1e-20)

    def test_accepts_float_rounding_at_waveform_endpoint(self):
        time_s = np.array([0., 10e-9, 20e-9, 370e-9])
        power_w = np.full(len(time_s), 0.002)
        begin_s = 350e-9
        end_s = begin_s + 20e-9
        self.assertAlmostEqual(energy_window(time_s, power_w, begin_s, end_s),
                               0.002 * 20e-9, delta=1e-20)

    def test_rejects_truncated_waveform(self):
        time_s = np.array([0., 10e-9, 20e-9, 369.9e-9])
        power_w = np.ones(len(time_s))
        with self.assertRaisesRegex(ValueError, 'outside'):
            energy_window(time_s, power_w, 350e-9, 370e-9)


if __name__ == '__main__':
    unittest.main()
