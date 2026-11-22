"""Targeted checks for zero-loss RC binding and physical timing/power units."""

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('phase3_rc_characterization', TOOLS / 'phase3_rc_characterization.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class CharacterizationTests(unittest.TestCase):
    def test_ideal_supply_diagnostic_preserves_signal_rc_and_rail_capacitance(self):
        extracted = ('.subckt phase3_rc_flat ' + ' '.join(mod.EXPECTED_PINS)
                     + '\nX1 DATA[0] CLK VDD.tap VSS.tap nmos l=0.15 w=1\n'
                     'R1 VDD VDD.tap 2\nR2 VSS VSS.tap 5\n'
                     'R3 DATA[0] DATA[0].tap 20\n'
                     'C1 VDD.tap VSS.tap 3f\nC2 VDD.tap VSS.tap 4f\n'
                     'C3 DATA[0].tap VSS.tap 2f\nC4 DATA[0] 0 0\n'
                     '.ends phase3_rc_flat\n')
        diagnostic, info = mod.idealize_supply_mesh(extracted)
        self.assertEqual(info['mos'], 1)
        self.assertEqual(info['original_resistors'], 3)
        self.assertEqual(info['retained_signal_resistors'], 1)
        self.assertEqual(info['retained_capacitor_pairs'], 2)
        self.assertAlmostEqual(info['rail_to_rail_capacitance_f'], 7e-15)
        self.assertIn('X1 DATA[0] CLK VDD VSS nmos l=0.15 w=1', diagnostic)
        self.assertIn('R3 DATA[0] DATA[0].tap 20', diagnostic)
        self.assertNotIn('R1 ', diagnostic)
        self.assertNotIn('R2 ', diagnostic)
        self.assertEqual(diagnostic.strip().splitlines()[-1], '.ends phase3_rc_flat')
        bound, _ = mod.bind_rc_deck(diagnostic)
        self.assertEqual(len([x for x in bound.splitlines() if x.startswith('C_IDEAL_RAIL_')]), 2)

    def test_ideal_supply_diagnostic_rejects_resistive_short(self):
        with self.assertRaisesRegex(ValueError, 'VDD/VSS short'):
            mod.idealize_supply_mesh('.subckt m VDD VSS\nR1 VDD VSS 1\n.ends m\n')

    def test_supply_audit_rejects_floating_full_rc_ground(self):
        extracted = ('.subckt macro VDD VSS\n'
                     'X1 x y VDD FILLER_21_0.VNB sky130_fd_pr__nfet_01v8\n'
                     'R1 VDD VDD.n0 2.0\n'
                     'R2 VSS.n0 VSS.n1 5.0\n'
                     '.ends macro\n')
        audit = mod.inspect_dc_supply_paths(extracted)
        self.assertEqual(audit['VDD']['mos_terminals_reachable'], 1)
        self.assertEqual(audit['VSS']['mos_terminals_reachable'], 0)
        self.assertFalse(audit['rails_short_through_resistors'])

    def test_supply_audit_accepts_resistive_rail_paths(self):
        extracted = ('.subckt macro VDD VSS\n'
                     'X1 x y VDD.n0 VSS.n0 sky130_fd_pr__nfet_01v8\n'
                     'R1 VDD VDD.n0 2.0\n'
                     'R2 VSS VSS.n0 5.0\n'
                     '.ends macro\n')
        audit = mod.inspect_dc_supply_paths(extracted)
        self.assertEqual(audit['VDD']['mos_terminals_reachable'], 1)
        self.assertEqual(audit['VSS']['mos_terminals_reachable'], 1)
        self.assertFalse(audit['rails_short_through_resistors'])

    def test_preserves_all_resistors_capacitors_and_mos_parameters(self):
        extracted = ('.subckt phase3_rc_flat ' + ' '.join(mod.EXPECTED_PINS)
                     + '\nX1 a[0] b c d sky130_fd_pr__nfet_01v8 l=0.15 w=1\n'
                     + 'R1 a[0] a[0].t0 15.2\nC2 a[0].t0 0 1.5f\n.ends phase3_rc_flat\n')
        bound, public = mod.bind_rc_deck(extracted)
        self.assertIn('l=0.15 w=1', bound)
        self.assertIn('R1 ', bound)
        self.assertIn(' 15.2\n', bound)
        self.assertIn(' 1.5f\n', bound)
        self.assertIn('ADDR0', public.values())
        self.assertEqual(len(bound.splitlines()), 6)

    def test_interpolated_rise_and_energy_sign(self):
        t = 1e-9
        rows = [(0., 0., *([0.] * 8), 1.8, -0.001),
                (t, 1.8, *([0.] * 8), 1.8, -0.001),
                (2 * t, 1.8, *([0.] * 8), 1.8, -0.001)]
        self.assertAlmostEqual(mod.crossing(rows, 1, 0, t, .9, 'rise')[0], .5e-9)
        self.assertAlmostEqual(mod.supply_energy(rows, .1e-9, 1.9e-9), 3.24e-12)
        self.assertEqual(mod.at(rows, 0., 10), 1.8)
        self.assertEqual(mod.at(rows, 2e-9, 11), -.001)

    def test_waveform_rejects_reordered_vectors(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'waveform.dat'
            names = ['time', *(x.lower() for x in mod.PUBLIC)]
            rows = [' '.join(names)]
            rows.extend(f'{i * 4e-9:g} ' + ' '.join('0' for _ in mod.PUBLIC)
                        for i in range(101))
            path.write_text('\n'.join(rows) + '\n')
            self.assertEqual(len(mod.parse_waveform(path)), 101)
            names[2], names[3] = names[3], names[2]
            path.write_text(' '.join(names) + '\n' + '\n'.join(rows[1:]) + '\n')
            with self.assertRaisesRegex(ValueError, 'waveform order'):
                mod.parse_waveform(path)

    def test_new_word_transition_required_for_access_delay(self):
        rows = []
        for i in range(801):
            ns = 125 + i * .05
            clk = 1.8 if 130.05 <= ns < 140.05 else 0.
            data0 = 1.8 if ns >= 140.3 else 0.
            rows.append((ns * 1e-9, clk, data0, *([0.] * 7), 1.8, -.001))
        cycles = [{'cycle': 6, 'operation': 'read', 'rise_ns': 130,
                   'fall_ns': 140, 'sample_ns': 141, 'expected': 1}]
        metrics, checks = mod.analyze(rows, cycles, 'tt', 'fixture')
        self.assertTrue(all(c['status'] == 'PASS' for c in checks))
        access = [m for m in metrics if m['metric'] == 'tACCESS']
        self.assertEqual(len(access), 1)
        self.assertIsNone(access[0]['bit'])
        self.assertEqual(access[0]['status'], 'PASS')
        self.assertAlmostEqual(access[0]['value'], 10.265e-9, delta=1e-15)
        stable = next(m for m in metrics if m['metric'] == 'tCLK_TO_DATA' and m['bit'] == 1)
        self.assertEqual(stable['status'], 'NOT_CHARACTERIZED')
        self.assertEqual(stable['reason'], 'PREVIOUS_WORD_ALREADY_MATCHED')

    def test_pre_capture_recovery_is_not_new_read_data(self):
        rows = []
        for i in range(801):
            ns = 125 + i * .05
            clk = 1.8 if 130.05 <= ns < 140.05 else 0.
            data0 = 1.8 if ns >= 135 else 0.
            rows.append((ns * 1e-9, clk, data0, *([0.] * 7), 1.8, -.001))
        cycles = [{'cycle': 6, 'operation': 'read', 'rise_ns': 130,
                   'fall_ns': 140, 'sample_ns': 141, 'expected': 1}]
        metrics, checks = mod.analyze(rows, cycles, 'tt', 'fixture')
        self.assertEqual(checks[0]['status'], 'PASS')
        for name, bit, reason in (('tACCESS', None, 'NO_ATTRIBUTABLE_WORD_TRANSITION'),
                                  ('tCLK_TO_DATA', 0, 'OUTPUT_BEFORE_FALLING_EDGE')):
            record = next(m for m in metrics if m['metric'] == name and m['bit'] == bit)
            self.assertEqual(record['status'], 'NOT_CHARACTERIZED')
            self.assertIsNone(record['value'])
            self.assertEqual(record['reason'], reason)

    def test_word_access_waits_for_slowest_valid_bit_through_closed_window(self):
        for final in (1.8, 1.2):
            with self.subTest(final=final):
                rows = []
                for i in range(3501):
                    ns = 125 + i * .01
                    clk = 1.8 if 130.05 <= ns < 140.05 else 0.
                    data0 = 1.8 if ns >= 140.3 else 0.
                    data1 = final if ns >= 140.8 else 1.0 if ns >= 140.5 else 0.
                    rows.append((ns * 1e-9, clk, data0, data1, *([0.] * 6), 1.8, -.001))
                run = [{'cycle': 6, 'operation': 'read', 'rise_ns': 130,
                        'fall_ns': 140, 'sample_ns': 141, 'expected': 3}]
                metrics, checks = mod.analyze(rows, run, 'ss', 'fixture')
                word = next(m for m in metrics if m['metric'] == 'tACCESS')
                self.assertEqual(checks[1]['status'], 'PASS' if final == 1.8 else 'FAIL')
                if final == 1.8:
                    self.assertAlmostEqual(word['value'], (140.7955 - 130.045) * 1e-9, delta=1e-15)
                else:
                    self.assertIsNone(word['value'])
                    self.assertEqual(word['status'], 'NOT_CHARACTERIZED')

    def test_one_valid_bit_cannot_qualify_an_ambiguous_word(self):
        rows = []
        for i in range(801):
            ns = 125 + i * .05
            clk = 1.8 if 130.05 <= ns < 140.05 else 0.
            data0 = 1.8 if ns >= 140.3 else 0.
            data1 = 1.8 if ns >= 135 else 0.
            rows.append((ns * 1e-9, clk, data0, data1, *([0.] * 6), 1.8, -.001))
        run = [{'cycle': 6, 'operation': 'read', 'rise_ns': 130,
                'fall_ns': 140, 'sample_ns': 141, 'expected': 3}]
        metrics, checks = mod.analyze(rows, run, 'ss', 'fixture')
        self.assertTrue(all(c['status'] == 'PASS' for c in checks))
        word = next(m for m in metrics if m['metric'] == 'tACCESS')
        self.assertEqual(word['status'], 'NOT_CHARACTERIZED')
        self.assertEqual(word['reason'], 'AMBIGUOUS_WORD_TRANSITION')


if __name__ == '__main__':
    unittest.main()
