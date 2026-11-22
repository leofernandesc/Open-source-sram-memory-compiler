"""Exercise the R87 startup gate and the offline SNM endpoint audit."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from audit_phase3_snm_endpoints import certify
from phase3_sclk_r87 import GATES, WINDOWS, branch, current_points, execute, overlay
from phase3_snm_measure import butterfly


class NortonTests(unittest.TestCase):
    mapping = {gate:f'g{i}' for i,gate in enumerate(GATES)}
    binding = ('.subckt wrapper input out\nR87 input leaf 6.46438\n'
               'R80 root input 95\nR1 leaf g0 1\nR2 leaf g1 1\nR3 leaf g2 1\n'
               'X1 d g0 s b mos\nX2 d g1 s b mos\nX3 d g2 s b mos\n'
               'X4 d input s b mos\nC1 leaf 0 1f\n.ends wrapper\n')

    def test_overlay_preserves_original_pex_terminals_and_only_adds_one_current_source(self):
        proof = branch(self.binding,self.mapping)
        altered = overlay(self.binding,proof,[(0.,0.),(211.,0.),(211.1,-.05),(219.,0.)])
        self.assertEqual(proof['resistance_ohm'],6.46438)
        self.assertEqual([name for name,_ in proof['consumers']],['X1','X2','X3'])
        self.assertIn('I_sclk_r87 input leaf PWL(',altered)
        remaining = [line for line in altered.splitlines() if not line.startswith(('I_sclk_r87','+'))]
        self.assertEqual(remaining,self.binding.splitlines())

    def test_shared_precharge_gate_prevents_intervention(self):
        with self.assertRaisesRegex(ValueError,'does not isolate'):
            branch(self.binding,self.mapping,edge='R80')
        shared = self.binding.replace('X4 d input','X4 d leaf')
        with self.assertRaisesRegex(ValueError,'does not isolate'):
            branch(shared,self.mapping)

    def test_no_current_at_zero_delay_or_outside_programmed_intervals(self):
        class RisingEdge:
            cols = {gate:0 for gate in GATES}

            def value(self,time,_):
                return max(0.,min(1.8,(time-212.)*1.8/.08))

        trace = RisingEdge()
        baseline = current_points(trace,6.46438,delay_ps=0)
        self.assertTrue(all(current==0. for _,current in baseline))
        measured = dict(current_points(trace,6.46438))
        self.assertEqual(measured[0.],0.)
        for start,end in WINDOWS:
            self.assertEqual(measured[start],0.)
            self.assertEqual(measured[end],0.)
        self.assertLess(measured[212.08],0.)

    def test_full_run_rejects_failed_startup_without_launching_ngspice(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'startup_gate.json').write_text(json.dumps({'status':'BLOCKED'}))
            with patch('phase3_sclk_r87.checked'),patch('phase3_sclk_r87.subprocess.Popen') as spawn:
                with self.assertRaisesRegex(ValueError,'Full TT blocked'):
                    execute(root,'full',2400)
                spawn.assert_not_called()
            self.assertFalse((root/'full').exists())


class EndpointTests(unittest.TestCase):
    eps = (5e-9,5e-9)

    def test_resolves_two_lobes_even_with_endpoints_inside_old_epsilon(self):
        x = np.array([0.,.4,.6,1.])
        f = np.array([1.,1.,0.,0.])
        rounded = np.clip(f+np.array([-4e-8,-4e-8,4e-8,4e-8]),0,1)
        result = certify(x,rounded,rounded,self.eps)
        self.assertEqual(result['verdict'],'VALID')
        self.assertEqual(len(result['brackets_v']),3)
        self.assertEqual(len(result['lobes_v']),2)
        self.assertAlmostEqual(result['snm_v'],.4,places=6)

    def test_asymmetry_and_side_swap_agree_with_original_lobe_size(self):
        x = np.linspace(0,1,21)
        left = np.clip((.60-x)/.20,0.,1.)
        right = np.clip((.68-x)/.18,0.,1.)
        actual = certify(x,left,right,self.eps)
        self.assertNotAlmostEqual(*actual['lobes_v'],places=2)
        self.assertAlmostEqual(actual['snm_v'],butterfly(x,left,right)['snm_v'])
        self.assertAlmostEqual(actual['snm_v'],certify(x,right,left,self.eps)['snm_v'])

    def test_one_certified_fixed_point_preserves_physical_failure(self):
        x = np.linspace(0,1,21)
        f = .75-.5*x
        result = certify(x,f,f,self.eps)
        self.assertEqual(result['verdict'],'PHYSICAL_FAILURE')
        self.assertEqual(result['snm_v'],0.)

    def test_unresolved_coincidence_is_not_classified_as_zero_snm(self):
        x = np.linspace(0,1,21)
        with self.assertRaisesRegex(ValueError,'certified monotonic crossing'):
            certify(x,1.-x,1.-x,self.eps)


if __name__=='__main__':
    unittest.main()
