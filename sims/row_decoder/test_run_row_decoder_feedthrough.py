#!/usr/bin/env python3
"""Protect the causal experiments from accidental changes outside their target."""
import unittest
from pathlib import Path
import run_row_decoder_feedthrough as investigation
import run_row_decoder_tt as screen

class FeedthroughExperiments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.netlist=(Path(__file__).parent/'results/b5_review_tt_netlist.spice').read_text()

    def test_width_override_changes_only_the_four_precharge_devices(self):
        changed, _, devices=investigation.modify(self.netlist,pre_width=.42)
        _, baseline=screen.inspect_netlist(self.netlist,True)
        changed_names={n for n,d in devices.items() if d!=baseline[n]}
        self.assertEqual(changed_names,{'M5','M11','M16','M21'})
        self.assertEqual(devices['M8']['W'],.5)
        self.assertEqual(devices['M5']['W'],.42)
        self.assertEqual(changed.count('W=0.42'),6) # Four precharge + two existing WL devices.

    def test_subminimum_width_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'below ordinary'):
            investigation.modify(self.netlist,pre_width=.3)

    def test_address_override_changes_only_the_two_input_inverters(self):
        _, _, devices=investigation.modify(self.netlist,address_width=.42)
        _, baseline=screen.inspect_netlist(self.netlist,True)
        self.assertEqual({n for n,d in devices.items() if d!=baseline[n]},
                         {'M1','M2','M3','M4'})
        self.assertEqual(devices['M5']['W'],1)

    def test_separated_precharge_clock_does_not_change_footer(self):
        changed,_,devices=investigation.modify(self.netlist,isolated='precharge_slow')
        self.assertEqual(devices['M5']['nodes'][1],'DIAG_CLK')
        self.assertEqual(devices['M8']['nodes'][1],'PCLK')
        self.assertIn('VDIAG DIAG_CLK VSS PULSE(0 1.8 10n 250p 250p 10n 20n)',changed)

    def test_footer_off_is_explicitly_isolated_from_precharge_clock(self):
        changed,_,devices=investigation.modify(self.netlist,isolated='footer_off')
        self.assertEqual(devices['M8']['nodes'][1],'DIAG_CLK')
        self.assertEqual(devices['M5']['nodes'][1],'PCLK')
        self.assertIn('VDIAG DIAG_CLK VSS 0',changed)

if __name__=='__main__':
    unittest.main()
