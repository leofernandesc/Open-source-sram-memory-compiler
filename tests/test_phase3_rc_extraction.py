"""Protect the Phase 3 parser from accepting device-only or broken RC decks."""

import importlib.util
from pathlib import Path
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / 'tools/phase3_rc_extraction.py'
spec = importlib.util.spec_from_file_location('phase3_rc_extraction', SOURCE)
import sys
sys.path.insert(0, str(SOURCE.parent))
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)


class ExtractionTests(unittest.TestCase):
    def test_flat_deck_keeps_distributed_rc(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'rc.spice'
            path.write_text('.subckt phase3_rc_flat ' + ' '.join(rc.EXPECTED_PINS) + '\n'
                            + ''.join(f'X{i} VDD CLK VSS VSS nmos w=1 l=.15\n' for i in range(1493))
                            + 'Rwire VDD split 10\nCwire split 0 2.5f\n.ends phase3_rc_flat\n')
            info = rc.inspect_netlist(path)
            self.assertEqual((info['mos'], info['resistors'], info['capacitors']), (1493, 1, 1))
            path.write_text(path.read_text().replace('Rwire VDD split 10', '* eliminated R'))
            with self.assertRaisesRegex(ValueError, 'Distributed R/C missing'):
                rc.inspect_netlist(path)

    def test_full_rc_uses_integrated_magic_resistance_extraction(self):
        tcl = rc.magic_script(Path('/work/baseline.gds'), Path('/work/new_pex.spice'))
        self.assertIn('gds read ', tcl)
        self.assertIn('extresist threshold 0', tcl)
        self.assertIn('extract do resistance\nextract all', tcl)
        self.assertNotIn('extresist all', tcl)
        self.assertNotIn('ext2sim\n', tcl)
        self.assertIn('PHASE3_RESISTANCE_INTEGRATED=1', tcl)
        self.assertIn('ext2spice extresist on', tcl)
        self.assertLess(tcl.index('extract do resistance'), tcl.index('ext2spice -o'))

    def test_rail_audit_detects_disconnected_ground(self):
        deck = ('.subckt phase3_rc_flat VDD VSS\n'
                'X1 a b VDD FILLER_21_0.VNB nmos\n'
                'R1 VSS VSS.n0 10\n'
                '.ends phase3_rc_flat\n')
        audit = rc.inspect_dc_supply_paths(deck)
        self.assertEqual(audit['VDD']['mos_terminals_reachable'], 1)
        self.assertEqual(audit['VSS']['mos_terminals_reachable'], 0)
        self.assertFalse(audit['rails_short_through_resistors'])

    def test_targeted_resistance_profile_limits_scope_explicitly(self):
        tcl = rc.magic_script(Path('/work/baseline.gds'), Path('/work/new_pex.spice'),
                              'critical_signals')
        self.assertIn('extresist include {CLK}\nextresist include {CSb}\nextresist include {OEb}\n', tcl)
        self.assertIn('macro_core.array_and_peripherals.write_driver_7.BLB', tcl)
        self.assertEqual(tcl.count('extresist include {'), len(rc.CRITICAL_NETS))
        self.assertIn('PHASE3_PROFILE=critical_signals', tcl)
        self.assertLess(tcl.index('extresist include'), tcl.index('extresist all'))
        with self.assertRaisesRegex(ValueError, 'Unsupported RC'):
            rc.magic_script(Path('/work/in.gds'), Path('/work/out.spice'), 'other')

    def test_zero_magic_capacitances_are_retained_but_negative_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'rc.spice'
            path.write_text('.subckt phase3_rc_flat ' + ' '.join(rc.EXPECTED_PINS) + '\n'
                            + ''.join(f'X{i} VDD CLK VSS VSS nmos w=1 l=.15\n' for i in range(1493))
                            + 'Rwire VDD split 10\nC0 split 0 0\nC1 split VSS 2f\n'
                            + '.ends phase3_rc_flat\n')
            info = rc.inspect_netlist(path)
            self.assertEqual((info['zero_capacitors'], info['positive_capacitors']), (1, 1))
            path.write_text(path.read_text().replace('.ends phase3_rc_flat', '.ends'))
            self.assertEqual(rc.inspect_netlist(path)['zero_capacitors'], 1)
            path.write_text(path.read_text().replace('C1 split VSS 2f', 'C1 split VSS -2f'))
            with self.assertRaisesRegex(ValueError, 'Invalid passive|Nonpositive passive'):
                rc.inspect_netlist(path)


if __name__ == '__main__':
    unittest.main()
