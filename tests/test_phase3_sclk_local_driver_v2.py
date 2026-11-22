"""Focused checks for the R87 candidate's library and decision rules."""

import unittest

import numpy as np

from phase3_sclk_local_driver_v2 import CELL, coordinated, integral, judge, select_library_cell


class DriverV2Test(unittest.TestCase):
    def test_restoring_cell_pinout_and_physical_devices(self):
        cell = f""".subckt {CELL} A VGND VNB VPB VPWR Y
X0 Y A VGND VNB sky130_fd_pr__nfet_01v8
X1 VPWR A Y VPB sky130_fd_pr__pfet_01v8_hvt
X2 VGND A Y VNB sky130_fd_pr__nfet_01v8
X3 Y A VPWR VPB sky130_fd_pr__pfet_01v8_hvt
.ends
"""
        self.assertEqual(select_library_cell(cell), cell)
        with self.assertRaisesRegex(ValueError, "pinout"):
            select_library_cell(cell.replace("VPWR Y", "Y VPWR", 1))

    def test_coordination_allows_distinct_slews(self):
        def wave(t, slew):
            return dict(rise_ns={"20": [t], "80": [t+slew]}, fall_ns={"80": [10+t], "20": [10+t+slew]})
        clock = {"sclk_sampler_bl": wave(1,4), "sclk_sampler_blb": wave(2,3), "sclk_tail": wave(3,1)}
        self.assertTrue(coordinated(clock))
        clock["sclk_tail"] = wave(6,1)
        self.assertFalse(coordinated(clock))

    def test_decision_distinguishes_diagnostic_risk_and_failure(self):
        self.assertEqual(judge(False, True, []), "PROMISING_LOCAL_DRIVER")
        self.assertEqual(judge(False, True, ["comparative current"]), "FUNCTIONAL_WITH_INTEGRATION_RISK")
        self.assertEqual(judge(False, False, []), "FUNCTIONAL_FAIL")
        self.assertEqual(judge(True, True, []), "ELECTRICAL_FAIL")

    def test_trapezoid_uses_the_native_nonuniform_time_and_si_units(self):
        self.assertAlmostEqual(integral(np.array([0.,2e-6,2e-6]),np.array([0.,2.,3.]))*1e15,4.)


if __name__ == "__main__":
    unittest.main()
