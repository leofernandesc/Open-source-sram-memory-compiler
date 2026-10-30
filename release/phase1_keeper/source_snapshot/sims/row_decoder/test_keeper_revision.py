"""Regress actual keeper import, coverage and OP-only passive-island anchoring."""
import argparse
import json
from pathlib import Path
import re
import sys
import unittest
import run_keeper_pex as run

ROOT=run.pair.ROOT
sys.path.insert(0,str(ROOT/'layout/row_decoder'))
sys.path.insert(0,str(ROOT/'tools'))
import build_layout as layout
import verify_phase1_physical as physical


class KeeperRevisionTests(unittest.TestCase):
    def test_signed_range_warning_is_not_hidden_by_a_passing_logic_screen(self):
        path=ROOT/'sims/row_decoder/results/keeper_pex_pilot_20261029/tt_1_to_2/result.json'
        result=json.loads(path.read_text())
        self.assertEqual(result['timing_screen'],'PASS')
        self.assertGreater(result['signed_domain_findings'],0)
        self.assertLess(result['max_intrinsic_magnitude_v'],1.95)

    def test_rejected_cached_width_report_cannot_be_accepted(self):
        path=ROOT/'layout/row_decoder_keeper/archive/rejected_stale_pcell/dimension_rejection.txt'
        report=path.read_text()
        self.assertIn('Property errors were found.',report)
        self.assertFalse(physical.matched(report))

    def test_all_49_mos_have_actual_pex_terminal_and_intrinsic_probes(self):
        inputs,_=run.revision_inputs()
        args=argparse.Namespace(step_ps=5,initialization='uic',kind='none',value=0)
        deck,terminals,probes,_=run.make_deck(inputs,'tt',1,2,run.timing.schedule(3,2.5,2100),args,102.873935496)
        self.assertEqual(len(terminals),49);self.assertEqual(set(terminals),set(probes))
        for r in range(4):self.assertIn(f'v(xdec.N{r})',deck)
        self.assertNotIn('RDC_PASSIVE',deck)

    def test_op_anchor_is_not_a_hardware_keeper_or_a_dynamic_node_resistor(self):
        inputs,_=run.revision_inputs()
        args=argparse.Namespace(step_ps=5,initialization='op',kind='none',value=0)
        deck,terminals,_,islands=run.make_deck(inputs,'tt',1,2,run.timing.schedule(3,2.5,2100),args,102.873935496)
        self.assertEqual([i['node'] for i in islands],['xdec.m1_160_n1740#'])
        self.assertIn('RDC_PASSIVE_ONLY_0 xdec.m1_160_n1740# 0 1e12',deck)
        self.assertNotRegex(deck,r'(?m)^RDC_\S+ xdec.N[0-3] ')
        self.assertNotIn(' uic\n',deck)

    def test_existing_29_device_positions_and_escapes_are_preserved(self):
        baseline=json.loads((ROOT/'layout/row_decoder/routing_plan.json').read_text())
        devices=layout.parse_devices((ROOT/'layout/row_decoder_keeper/row_decoder_import.spice').read_text())
        plan=layout.compact_plan(devices)
        for name,position in baseline['placement'].items():
            self.assertEqual(list(plan.placement[name]),position)
            self.assertEqual(plan.drain_offset[name],-300)
            self.assertEqual(plan.gate_offset[name],baseline['gate_offset'][name])
        for row in range(4):
            name=f'XM{30+row}';lower=f'XM{(7,13,18,23)[row]}'
            self.assertEqual(plan.placement[name][0],plan.placement[lower][0])
            self.assertNotEqual(plan.drain_offset[name],plan.drain_offset[lower])


if __name__=='__main__':unittest.main()
