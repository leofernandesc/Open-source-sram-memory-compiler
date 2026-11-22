"""Software regressions for reduction and the mandatory control gate."""

from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from analyze_phase3_sense3_isolation import contrast_verdict, control_verdict, input_evidence, tail_conditioning
from export_phase3_sense3_evidence import port_resistance
from review_phase3_bus_ss import Trace
from run_phase3_eco_pex import sha256
from run_phase3_sense3_isolation import START, authorized_gate, compress, delay_source


class ReductionTests(unittest.TestCase):
    def test_dc_equivalent_retains_parallel_paths(self):
        cards = ['R1 a mid 20','R2 mid b 40','R3 a b 30','R4 a stub 500']
        self.assertAlmostEqual(port_resistance(cards,'a','b'),20.)
        with self.assertRaisesRegex(ValueError,'does not reach'):
            port_resistance(cards,'a','unrelated')

    def test_pwl_compression_respects_native_sample_bound(self):
        t = np.linspace(0,3,600)
        v = np.sin(t)*1.8
        x,y = compress(t,v)
        self.assertGreater(len(x),2)
        self.assertLess(len(x),len(t))
        self.assertLessEqual(max(abs(np.interp(t,x,y)-v)),.0001)

    def test_shift_edits_only_rise_windows_and_preserves_fall(self):
        t = [208.,214.,214.5,224.,224.5,234.,234.5,244.,244.5,247.]
        v = [0.,0.,1.8,1.8,0.,0.,1.8,1.8,0.,0.]
        ref = Trace([(a*1e-9,b) for a,b in zip(t,v,strict=True)],{'sclk_root':1})
        card = delay_source(ref).replace('\n+',' ').split('PWL(')[1].split(')')[0].split()
        tx = np.array([float(s[:-1])+START for s in card[::2]])
        data = np.array(list(map(float,card[1::2])))
        for crossing in (224.25,244.25):
            self.assertEqual(np.interp(crossing,tx,data),0.)
        self.assertAlmostEqual(0.9+np.interp(214.432,tx,data),.2448,places=6)
        self.assertAlmostEqual(np.interp(214.432,t,v)+np.interp(214.432,tx,data),.9)


class GateTests(unittest.TestCase):
    def case(self):
        return dict(reference={'decision':'WRONG'},isolated={'decision':'WRONG'},input={'eligible':True},
                    conditioning_valid=True,tail_conditioning={'compatible':True},clock_valid=True,
                    decision_timing_compatible=True)

    def test_two_wrong_decisions_cannot_bypass_tail_initial_gate(self):
        one,two = self.case(),self.case()
        self.assertEqual(control_verdict([one,two]),'REPRODUCED')
        one['tail_conditioning']['compatible'] = False
        self.assertEqual(control_verdict([one,two]),'INCONCLUSIVE')
        one['isolated']['decision'] = 'CORRECT'
        self.assertEqual(control_verdict([one,two]),'NOT_REPRODUCED')

    def test_tail_reports_mismatch_while_device_conducts(self):
        ref = dict(conditioning={'sense_tail':1.15},activation={'sense_tail':1.20},tail50={'sense_tail':1.04})
        cut = dict(conditioning={'sense_tail':1.43},activation={'sense_tail':1.45},
                   tail50={'sense_tail':1.26,'tail_id_a':38e-6})
        result = tail_conditioning(ref,cut,.03)
        self.assertFalse(result['compatible'])
        self.assertAlmostEqual(result['at_tail50_difference_v'],.22)
        self.assertEqual(result['tail_id_at_tail50_a'],38e-6)

    def test_same_common_mode_does_not_hide_differential_deviation(self):
        t=[0.,1.,2.,3.,4.]
        ref = Trace([(x*1e-9,1.8,1.82) for x in t],{'bl_at_sense':1,'blb_at_sense':2})
        cut = Trace([(x*1e-9,1.794,1.826) for x in t],ref.cols)
        criteria=dict(early_max_delta_error_v=.00755, common_mode_error_v=.0151, later_relative_delta_tolerance=.05)
        case=dict(low_ns=1.,capture_ns=3.,early_input_window_ns=[1.9,2.1])
        actual=input_evidence(ref,cut,case,criteria)
        self.assertFalse(actual['eligible'])
        self.assertAlmostEqual(actual['max_delta_error_early_v'],.012)
        self.assertAlmostEqual(actual['max_common_mode_error_early_v'],0.)

    def test_contrast_requires_correct_isolated_stimuli_as_well_as_decision(self):
        case=dict(sclk_fidelity=True,same_bitline_terminals=True,same_conditioning=True,isolated={'decision':'CORRECT'})
        self.assertEqual(contrast_verdict([case,case]),'CORROBORATED')
        bad=dict(case,same_bitline_terminals=False)
        self.assertEqual(contrast_verdict([case,bad]),'INCONCLUSIVE')
        bad=dict(case,isolated={'decision':'WRONG'})
        self.assertEqual(contrast_verdict([bad,bad]),'NOT_CORROBORATED')

    def test_runner_requires_reproduced_control_and_exact_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'result.json'
            path.write_text('original')
            g=dict(verdict='INCONCLUSIVE',control_result_sha256=sha256(path))
            with self.assertRaisesRegex(ValueError,'blocked'):
                authorized_gate(g,path,Path(tmp)/'control_gate.json')
            g['verdict']='REPRODUCED'
            authorized_gate(g,path,Path(tmp)/'control_gate.json')
            path.write_text('different')
            with self.assertRaisesRegex(ValueError,'blocked'):
                authorized_gate(g,path,Path(tmp)/'control_gate.json')


if __name__=='__main__':
    unittest.main()
