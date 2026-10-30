"""Timing-boundary checks must detect short pulses and incomplete reset."""
import unittest
import numpy as np
import run_canonical_timing_limits as limits
import run_canonical_decoder_wl as pair


class TimingLimitsTests(unittest.TestCase):
    def test_dwell_does_not_sum_separate_spikes(self):
        time=np.arange(6)*0.1e-9
        good=np.array([False,True,True,False,True,True])
        self.assertAlmostEqual(limits.longest_dwell(time,good,0,time[-1]),0.1)

    def test_reset_requires_a_low_tail_before_evaluation(self):
        time=np.arange(6)*0.1e-9
        good=np.array([True,True,True,True,True,False])
        self.assertEqual(limits.longest_dwell(time,good,0,time[-1],tail=True),0)

    def test_literal_lead_uses_last_settling_not_first_crossing(self):
        time=np.arange(8)*0.1e-9
        good=np.array([False,True,True,False,True,True,True,True])
        self.assertAlmostEqual(limits.stable_lead_ns(time,good,0,time[-1],0.6e-9),0.2)

    def test_literal_glitch_after_clock_gives_negative_lead(self):
        time=np.arange(8)*0.1e-9
        good=np.array([True,True,True,True,True,False,True,True])
        self.assertLess(limits.stable_lead_ns(time,good,0,time[-1],0.5e-9),0)

    def test_literal_never_settles_cannot_pass_positive_guard(self):
        time=np.arange(8)*0.1e-9
        good=np.zeros(8,dtype=bool)
        self.assertLess(limits.stable_lead_ns(time,good,0,time[-1],0.5e-9),0)

    def test_schedule_preserves_declared_pulse_lengths(self):
        when=limits.schedule(low_ns=0.5,high_ns=1.3,lead_ps=100)
        self.assertAlmostEqual(when['rise_ns'],10.5)
        self.assertAlmostEqual(when['fall_ns'],11.8)
        self.assertAlmostEqual(when['address_ns'],10.4)
        self.assertAlmostEqual(when['stop_ns'],16.8)

    def test_overlapping_clock_ramps_are_rejected(self):
        with self.assertRaises(ValueError):limits.schedule(low_ns=0.01)

    def test_address_cannot_change_during_priming_evaluation(self):
        inputs=pair.release_inputs()
        when=limits.schedule(low_ns=0.25,lead_ps=2100)
        with self.assertRaisesRegex(ValueError,'first evaluation'):
            limits.make_deck(inputs,'ss',0,3,5,102.873935496,when)

    def test_same_row_can_test_reset_without_address_change(self):
        inputs=pair.release_inputs()
        when=limits.schedule(low_ns=0.25,lead_ps=2100)
        deck,_=limits.make_deck(inputs,'ss',0,0,5,102.873935496,when)
        self.assertIn('.tran 5p 20.65n 0 5p uic',deck)
        self.assertIn('.control\nset num_threads=1\n',deck)


if __name__=='__main__':
    unittest.main()
