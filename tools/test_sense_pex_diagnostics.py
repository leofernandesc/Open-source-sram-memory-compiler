#!/usr/bin/env python3
"""Topology and intervention guards for diagnostic-only parasitic variants."""
import re
import unittest

from investigate_sense_pex import MODES, PORTS, SOURCE, topology, variant, plan, bench


class DiagnosticGuards(unittest.TestCase):
    def test_full_is_exact_original(self):
        self.assertEqual(variant('full')[0],SOURCE.read_text())

    def test_all_interventions_preserve_device_graph_and_parameters(self):
        original=SOURCE.read_text();_,graph=topology(original)
        for mode in MODES:
            with self.subTest(mode=mode):
                text,description,_=variant(mode)
                self.assertEqual(graph(original),graph(text))
                self.assertEqual(len(graph(text)),7)
                self.assertEqual(description['diagnostic_only'],mode!='full')

    def test_parasitic_removal_is_exact(self):
        for mode,r,c in [('no_c',76,0),('no_r',0,61),('no_rc',0,0)]:
            with self.subTest(mode=mode):
                text,description,_=variant(mode)
                self.assertEqual(description['remaining_resistors'],r)
                self.assertEqual(description['remaining_capacitors'],c)

    def test_clock_cap_intervention_only_removes_clock_to_output(self):
        _,description,_=variant('no_clock_output')
        self.assertEqual({x.split()[0] for x in description['removed_elements']},{'C6','C8'})
        self.assertFalse(description['changed_capacitors'])

    def test_gate_mutant_detected(self):
        original=SOURCE.read_text();_,graph=topology(original)
        mutant=original.replace('a_615_n3098.t0 SA_OUT.t3','a_615_n3098.t0 SA_OUTB.t3',1)
        self.assertNotEqual(original,mutant)
        self.assertNotEqual(graph(original),graph(mutant))

    def test_ground_cap_symmetrization_conserves_total(self):
        text,description,_=variant('equal_output_ground')
        mapping,_=topology(SOURCE.read_text());sums={'SA_OUT':0.,'SA_OUTB':0.}
        for line in text.splitlines():
            if not re.match(r'^C\d+\b',line):continue
            f=line.split();nodes={mapping.get(n,n) for n in f[1:3]}
            if 'VSS' not in nodes:continue
            for side in sums:
                if side in nodes:sums[side]+=float(f[3][:-1])
        self.assertAlmostEqual(sums['SA_OUT'],sums['SA_OUTB'],places=8)
        self.assertAlmostEqual(sum(sums.values()),sum(description['original_output_ground_totals_ff'].values()),places=8)

    def test_collapsed_formal_ports_are_probed_at_top_level(self):
        _,_,probes=variant('no_r')
        case=plan('ablation',[5],['no_r'])[0]
        text,_,_=bench(case,dict(ports=PORTS,subckt='sense_amp_scale1p5_flat'),probes)
        self.assertNotIn('v(xdut.SCLK)',text)
        self.assertNotIn('v(xdut.SA_OUT)',text)
        self.assertIn('v(SCLK)',text)

    def test_mirrored_capacitances_exchange_output_ground_totals(self):
        text,description,_=variant('no_r_mirror_outputs')
        sums={'SA_OUT':0.,'SA_OUTB':0.}
        for line in text.splitlines():
            if not re.match(r'^C\d+\b',line):continue
            f=line.split();nodes=set(f[1:3])
            if 'VSS' in nodes:
                for side in sums:
                    if side in nodes:sums[side]+=float(f[3][:-1])
        self.assertAlmostEqual(sums['SA_OUT'],description['original_output_ground_totals_ff']['SA_OUTB'])
        self.assertAlmostEqual(sums['SA_OUTB'],description['original_output_ground_totals_ff']['SA_OUT'])


if __name__=='__main__':unittest.main(verbosity=2)
