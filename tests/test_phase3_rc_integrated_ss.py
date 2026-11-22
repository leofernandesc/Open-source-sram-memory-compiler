"""Offline fixture and physical bus ownership regressions."""

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from analyze_phase3_integrated_ss import follow_disable, stable_word
from phase3_rc_characterization import QUAL
from phase3_rc_read_path import OUTPUT_ENABLES
from run_phase3_integrated_ss import deck_text, ns, plan_cycles


class IntegratedTests(unittest.TestCase):
    def setUp(self):
        self.records = json.loads((QUAL/'results.json').read_text())['cycles']
        self.template = (QUAL/'bench.spice').read_text()

    def test_exact_benchmark_coverage_and_fixed_ownership_order(self):
        records, strong, weak = plan_cycles(self.records)
        self.assertEqual([r['expected'] for r in self.records],[r['expected'] for r in records])
        self.assertEqual([r['cycle'] for r in records if r['operation']=='read'],[6,7,9,11,13,14,15,16,17])
        self.assertEqual({r['row'] for r in records if r['operation']=='read'},{0,1,2,3})
        self.assertEqual(strong,[(48.,1),(126.5,0),(168.5,1),(186.5,0),(208.5,1),(226.5,0)])
        self.assertIn((161.5,168.4,0xAA),weak)
        self.assertIn((201.5,208.4,0xAA),weak)
        self.assertIn((241.5,266.5,0x55),weak)

    def test_deck_instruments_the_bus_without_changing_clock_address_or_operation(self):
        _, strong, weak = plan_cycles(self.records)
        deck = deck_text(self.template,['rc0'],strong,weak)
        for source in ('CLK','ADDR0','ADDR1','CSb','OEb','WEb'):
            prefix = f'V_{source} '
            self.assertEqual([l for l in deck.splitlines() if l.startswith(prefix)],
                             [l for l in self.template.splitlines() if l.startswith(prefix)])
        self.assertEqual(deck.count('\nV_DUT'),8)
        self.assertIn('S_WEAK0 METER_WEAK0 WEAK0 HOST_WEAK_EN 0 HOST_WEAK_SWITCH',deck)
        self.assertIn('tran 10p 370n 0 25p',deck)

    def test_follow_disable_needs_both_branch_currents_and_sustained_valid_pad(self):
        names = ['time','clk', *(f'data{i}' for i in range(8)),*OUTPUT_ENABLES,
                 *(f'i(v_sense_weak{i})' for i in range(8)), *(f'i(v_dut{i})' for i in range(8))]
        cols = {name:i for i,name in enumerate(names)}
        rows = []
        for t in (.8,.9,1.,1.1,1.2,1.3,1.4,1.5,1.6):
            row = dict.fromkeys(names,0.)
            row['time'] = ns(t)
            for bit,label in enumerate(OUTPUT_ENABLES):
                row[label] = 1.8 if t>=1.1 else 0.
                row[f'data{bit}'] = 1.8 if t>=1.2 else 0.
                row[f'i(v_sense_weak{bit})'] = .0003 if t<1.2 else 0.
                row[f'i(v_dut{bit})'] = -.0003 if t<(1.4 if bit==7 else 1.2) else 0.
            rows.append(tuple(row[name] for name in names))
        verified = follow_disable(rows,cols,ns(1.),ns(1.6),255,True)
        self.assertGreater(verified['last_release_ns'],1.3)
        self.assertIsNone(follow_disable(rows,cols,ns(1.),ns(1.3),255,True)['last_release_ns'])

    def test_single_correct_point_does_not_give_a_stable_word(self):
        rows = [(ns(i),0.,*([1.8]*8 if i==2 else [0.]*8)) for i in (0,1,2,3)]
        self.assertIsNone(stable_word(rows,ns(1.),ns(3.),255))


if __name__ == '__main__':
    unittest.main()
