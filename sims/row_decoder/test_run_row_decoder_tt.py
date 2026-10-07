#!/usr/bin/env python3
"""Regression checks using a real Xschem-generated B5 hierarchy as the fixture."""
import argparse
import math
import unittest
from pathlib import Path

import run_row_decoder_tt as screen


class DecoderScreenRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.netlist = (Path(__file__).parent / "results/b5_review_tt_netlist.spice").read_text()

    def reject_mutation(self, before, after, message):
        self.assertIn(before, self.netlist)
        with self.assertRaisesRegex(ValueError, message):
            screen.inspect_netlist(self.netlist.replace(before, after), True)

    def test_real_hierarchy_and_nonsequential_symbol_pin_order(self):
        nodes, devices = screen.inspect_netlist(self.netlist, True)
        self.assertEqual(devices["M8"]["W"], 0.5)
        self.assertEqual(nodes["WL2"], "net7")
        self.assertEqual(nodes["WL3"], "net8")

    def test_shorting_footer_drain_to_ground_is_rejected(self):
        self.reject_mutation("XM8 EVAL_GND PCLK VSS VSS",
                             "XM8 VSS PCLK VSS VSS", "M8: expected")

    def test_output_bulk_regression_is_rejected(self):
        self.reject_mutation("XM15 DEC1 N1 VSS VSS",
                             "XM15 DEC1 N1 VSS EVAL_GND", "M15: wrong bulk")

    def test_duplicate_driver_input_is_rejected(self):
        self.reject_mutation("x3 net1 DEC1 net6 GND wl_driver",
                             "x3 net1 DEC0 net6 GND wl_driver", "Duplicated driver input")

    def test_capacitor_on_the_wrong_row_is_rejected(self):
        self.reject_mutation("C_WL1 net6 GND", "C_WL1 net5 GND", "Wrong C_WL1")

    def test_subminimum_custom_footer_width_is_rejected(self):
        self.reject_mutation("W=0.5 nf=1", "W=0.30 nf=1", "M8: below ordinary")

    def test_negative_low_and_above_rail_high_are_not_false_passes(self):
        self.assertFalse(screen.passes_voltage(-1, False, 1.8))
        self.assertFalse(screen.passes_voltage(2.5, True, 1.8))
        self.assertFalse(screen.passes_voltage(math.nan, True, 1.8))
        self.assertTrue(screen.passes_voltage(-1e-6, False, 1.8))
        self.assertTrue(screen.passes_voltage(1.8, True, 1.8))

    def test_stimulus_overrides_do_not_change_sizing(self):
        args = argparse.Namespace(vdd=1.62, clock_slew_ps=250,
                                  address_slew_ps=None, wl_cap_ff=50)
        changed, rise, fall = screen.prepare_stimulus(self.netlist, args)
        nodes, devices = screen.inspect_netlist(changed, True)
        self.assertEqual(devices["M8"]["W"], 0.5)
        self.assertAlmostEqual(rise, 250e-12)
        self.assertAlmostEqual(fall, 250e-12)
        self.assertIn("VDD_SRC net1 GND 1.62", changed)
        self.assertIn("C_WL0 net5 GND 5e-14", changed)
        self.assertEqual(nodes["WL0"], "net5")

    def test_changed_address_schedule_is_not_silently_mislabeled(self):
        args = argparse.Namespace(vdd=1.8, clock_slew_ps=None,
                                  address_slew_ps=None, wl_cap_ff=None)
        changed = self.netlist.replace("PULSE(0 1.8 22n", "PULSE(0 1.8 23n")
        self.assertNotEqual(changed, self.netlist)
        with self.assertRaisesRegex(ValueError, "VA0: unsupported address/clock schedule"):
            screen.prepare_stimulus(changed, args)

    def test_precharge_crossing_uses_the_local_time_window(self):
        args = argparse.Namespace(bench="sizing", method="gear",
                                  max_step_ps=10, vdd=1.8, temp_c=27, corner="tt")
        nodes, _ = screen.inspect_netlist(self.netlist, True)
        deck, metrics = screen.make_deck(self.netlist, Path("/models/sky130.lib.spice"),
                                        nodes, args, 50e-12, 50e-12)
        line = next(line for line in deck.splitlines() if line.startswith(".meas tran t_01_dec1_fall10 "))
        self.assertIn("FALL=1 TD=3.905e-08", line)
        self.assertNotIn("FALL=2", line)
        limits = next(m for m in metrics if m["name"] == "vgs_peak_01_m15")
        self.assertEqual(limits["high"], 1.95)


if __name__ == "__main__":
    unittest.main()
