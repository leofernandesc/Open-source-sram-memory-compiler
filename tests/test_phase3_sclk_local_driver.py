"""Check SCLK qualification rules without running SPICE."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from phase3_sclk_local_driver import CELL, EXTRA, classify, instrument, intersect, library_cell, pulse_inventory
from review_phase3_bus_ss import Trace


class TestDriverFixture(unittest.TestCase):
    def test_preserves_solver_and_horizon(self):
        control='.save v(in)\n.control\ntran 10p 59n 0 25p\nquit\n.endc\n'
        observed=instrument(control)
        self.assertIn('tran 10p 59n 0 25p',observed)
        self.assertIn('wrdata driver.dat '+' '.join(EXTRA.values()),observed)
        with self.assertRaises(ValueError):
            instrument(control.replace('59n','39n'))

    def test_cells_use_installed_pin_order(self):
        signature=f'.subckt {CELL} A VGND VNB VPB VPWR Y'
        expected=signature+'\nX0 Y A VGND VNB model\n.ends\n'
        self.assertEqual(library_cell('* header\n'+expected+'.subckt unrelated\n.ends\n'),expected)
        with self.assertRaises(ValueError):
            library_cell(expected.replace('VGND VNB','VNB VGND'))

    def test_glitch_outside_evaluation_is_detected(self):
        good=[(188,0),(190,0),(193,0),(194,1.8),(200.5,1.8),(201,0),(207,0)]
        glitch=good[:-1]+[(203,1.8),(204,0),good[-1]]
        case={'low_ns':191.,'high_ns':199.,'capture_ns':200.}
        for data,valid in ((good,True),(glitch,False)):
            trace=Trace([(time*1e-9,level) for time,level in data],{'pulse':1})
            self.assertEqual(pulse_inventory(trace,'pulse',[case],207.)['compatible'],valid)


class TestDriverDecision(unittest.TestCase):
    def test_overlap_uses_timing_intersection(self):
        self.assertEqual(intersect([(1.,2.),(3.,4.)],[(2.,3.),(3.1,3.2)]),[[3.1,3.2]])

    def test_correct_decision_does_not_override_reset_and_loading(self):
        pulse={'clock':{'compatible':True}}
        predecessor={'decision_preserved':True}
        event=dict(driver={'decision':'CORRECT','stable_d_low':{'first_actual_ns':1.0}},reset={'adequate':True},
                   additional_turn_on_verified=True,conditioned=True,externals={'compatible':True},
                   loading={'comparable_load':True})
        self.assertEqual(classify(pulse,predecessor,[event]),'VIABLE_FOR_PHYSICAL_STUDY')
        event['loading']['comparable_load']=False
        self.assertEqual(classify(pulse,predecessor,[event]),'INCONCLUSIVE')
        event['reset']['adequate']=False
        self.assertEqual(classify(pulse,predecessor,[event]),'NOT_VIABLE')


if __name__=='__main__':
    unittest.main()
