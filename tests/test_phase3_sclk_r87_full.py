"""Offline checks for the full R87 monitor and causal requirements."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from analyze_phase3_sclk_r87_full import (causal_verdict,compare_signals,functional_verdict,gate_shape,interpret_gate,
                                         stored_zero)
from review_phase3_bus_ss import Trace
from run_phase3_sclk_r87_full import FIDELITY,observed_deck,stop_reason


class MonitorTests(unittest.TestCase):
    def test_missing_progress_does_not_retrigger_previous_120s_guard(self):
        self.assertIsNone(stop_reason(120,{},None))
        self.assertEqual(stop_reason(300,{},None),'PREPARATION_WALL_LIMIT')
        self.assertIsNone(stop_reason(300,{'tran_dispatch':{'elapsed_s':113}},None))

    def test_proven_error_and_separate_operational_budgets(self):
        events={'tran_dispatch':{'elapsed_s':95},'first_positive_reference':{'elapsed_s':120}}
        self.assertEqual(stop_reason(121,events,'analysis aborted'),'PROVEN_SIMULATOR_ERROR')
        self.assertEqual(stop_reason(2970,events,None),'INTEGRATION_WALL_LIMIT')
        self.assertEqual(stop_reason(2998,events,None),'TOTAL_WALL_LIMIT')

    def test_observability_additions_leave_transient_and_existing_save_vectors_alone(self):
        deck = '.save v(clk)\n.control\ntran 10p 250n 0 25p\nwrdata waveform.dat v(clk)\nquit\n.endc\n'
        new = observed_deck(deck,('rc8562','rc8571'))
        self.assertEqual(new.count('tran 10p 250n 0 25p\n'),1)
        self.assertIn('wrdata waveform.dat v(clk) v(xdut.rc8562) v(xdut.rc8571)\n',new)
        self.assertIn('wrdata r87_current.dat @i.xdut.i_sclk_r87[current]\n',new)
        self.assertIn('echo __R87_DECK_READY__\n',new)


class VerdictTests(unittest.TestCase):
    def gate(self,delay=0.,off=0.):
        return Trace([(t*1e-9,v) for t,v in [(0.,0.),(2.+delay,0.),(2.5+delay,1.8),
                                            (11.+off,1.8),(11.5+off,0.),(20.,0.)]],{'gate':1})

    def test_gate_fidelity_requires_both_displacement_and_unchanged_deactivation(self):
        ref = gate_shape(self.gate(),'gate',1.,9.)
        good = gate_shape(self.gate(.182),'gate',1.,9.)
        self.assertTrue(interpret_gate(ref,good,FIDELITY)['fidelity_verified'])
        for new in (self.gate(.125),self.gate(.182,.182)):
            self.assertFalse(interpret_gate(ref,gate_shape(new,'gate',1.,9.),FIDELITY)['fidelity_verified'])

    def test_shared_waveform_comparison_uses_edges_and_not_small_voltage_differences(self):
        ref = self.gate()
        tiny = Trace([(row[0],row[1]+.003) for row in ref.rows],ref.cols)
        self.assertTrue(compare_signals(ref,tiny,('gate',),1.,12.,25)[0]['equivalent_in_observed_logic_and_timing'])
        self.assertFalse(compare_signals(ref,self.gate(.182),('gate',),1.,12.,25)[0]['equivalent_in_observed_logic_and_timing'])

    def test_an_analog_shoulder_alone_does_not_change_a_nontarget_logic_transition(self):
        a,b = (Trace([(0.,0.),(1e-9,v),(2e-9,0.)],{'node':1}) for v in (.365,.355))
        measurement = compare_signals(a,b,('node',),0.,2.,25)[0]
        self.assertFalse(measurement['equivalent_in_observed_logic_and_timing'])
        self.assertTrue(measurement['equivalent_at_validated_logic_transitions'])

    def test_intermediate_storage_voltage_is_not_automatically_corruption(self):
        cols={'cell_q':1,'cell_qb':2}
        for q,qb,expected in [(0.,1.8,True),(.4,1.8,None),(1.8,0.,False)]:
            trace=Trace([(t*1e-9,q,qb) for t in (0.,.025,.05,.075,.1,.15)],cols)
            self.assertEqual(stored_zero(trace,0.,.1),expected)

    def test_functional_failure_survives_inconclusive_causality(self):
        reads=[{'readback_status':k} for k in ('PASS','PASS','FAIL','FAIL')]
        writes=[dict(verified=True)]*6
        bad = functional_verdict(reads,writes,True,True,True)
        self.assertEqual(bad,'FAIL')
        self.assertEqual(causal_verdict(True,False,True,True,bad,True),'INCONCLUSIVE')
        self.assertEqual(causal_verdict(True,True,True,True,bad,True),'NOT_CORROBORATED')

    def test_correct_output_needs_independent_fidelity_and_no_side_effects(self):
        reads=[{'readback_status':'PASS'}]*4
        writes=[dict(verified=True)]*6
        self.assertEqual(functional_verdict(reads,writes,True,True,False),'INCONCLUSIVE')
        passed = functional_verdict(reads,writes,True,True,True)
        self.assertEqual(passed,'PASS_IN_SCOPE')
        self.assertEqual(causal_verdict(True,True,False,True,passed,False),'INCONCLUSIVE')
        self.assertEqual(causal_verdict(True,True,True,True,passed,False),'CORROBORATED_IN_CONTRAST')


if __name__=='__main__':
    unittest.main()
