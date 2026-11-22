"""Offline checks of the bus observer using synthetic voltage/current traces."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from review_phase3_bus_ss import OUTPUT_ENABLES, Trace, ge, inspect_probe, inspect_strong, isolated_gap


def trace(pattern):
    names = ['time', 'clk', *(f'data{i}' for i in range(8)), *OUTPUT_ENABLES,
             'v(HOST_EN)', 'v(HOST_WEAK_EN)',
             *(f'i({name}{i})' for name in ('v_sense_host','v_dut','v_sense_weak') for i in range(8))]
    cols = {name:i for i,name in enumerate(names)}
    rows = []
    for index in range(101):
        t = index/100
        te, host_gate, weak_gate, pad, host, macro, weak = pattern(t)
        rows.append((t*1e-9, 0., *([pad]*8), *([te]*8), host_gate, weak_gate,
                     *([host]*8), *([macro]*8), *([weak]*8)))
    return Trace(rows,cols)


def low_read(t):
    if t<.45:
        return 0., 0., 1.8, .25, 0., -.00025, .00025
    return 1.8, 0., 1.8, 1.8, 0., 0., 0.


def step_charge(t, gate=1.8):
    if t<=.20:
        return gate, 1.8, 0., 0., 0., 0., 0.
    if t<.28:
        current = (.28-t)*.004
        return gate, 1.8, 0., 1.799, current, -current, 0.
    return gate, 1.8, 0., 1.8, 0., 0., 0.


class BusReviewTests(unittest.TestCase):
    def test_drive_and_release_need_signed_currents_and_valid_expected_rails(self):
        result = inspect_probe(trace(low_read),7,1,.02,.4,.8,True)
        self.assertGreater(result['conduction']['conservative_ps'], 50)
        self.assertTrue(result['release'])
        self.assertGreater(result['drive_through_disable_ns'],.4)
        self.assertLess(result['first_drive']['dut_ua'],0)
        self.assertGreater(result['first_drive']['weak_ua'],0)

    def test_internal_enable_or_current_in_wrong_direction_is_insufficient(self):
        for mode in ('weak_only','inverted','wrong_pad'):
            def pattern(t):
                te,h,w,p,ih,im,iw = low_read(t)
                if t>=.45:
                    return te,h,w,p,ih,im,iw
                return te,h,w,1.78 if mode=='wrong_pad' else p,ih,(
                    0. if mode=='weak_only' else -im if mode=='inverted' else im),iw
            with self.subTest(mode=mode):
                result = inspect_probe(trace(pattern),1,1,.02,.4,.8,True)
                self.assertTrue(result['internal_enable'])
                self.assertIsNone(result['conduction'])

    def test_high_z_requires_charge_to_settle_and_pad_to_follow_probe(self):
        for t_end in (.44,.47):
            result = inspect_probe(trace(low_read),0,1,.02,.4,t_end,True)
            self.assertTrue(result['conduction'])
            self.assertIsNone(result['release'])

    def test_suffix_disallows_replacing_late_failure_with_an_earlier_witness(self):
        w = trace(lambda t:(0.,0.,1.8,1.8 if t<.7 else 0.,0.,0.,0.))
        spec = [ge(2,1.44)]
        self.assertTrue(w.signal_window(.02,.9,spec))
        self.assertIsNone(w.signal_window(.02,.9,spec,suffix=True))

    def test_single_spike_and_coarse_two_samples_are_not_sustained_drive(self):
        w = trace(lambda t:(0.,0.,1.8,1.8 if t==.5 else 0.,0.,0.,0.))
        self.assertIsNone(w.signal_window(.3,.7,[ge(2,1.44)]))
        coarse = Trace([(0.,1.8),(.1e-9,1.8),(.3e-9,0.)],{'signal':1})
        self.assertIsNone(coarse.signal_window(0.,.105,[ge(1,1.44)]))

    def test_switch_discontinuity_is_not_interpolated_into_open_gap(self):
        w = trace(lambda t:(1.8,0. if t<.5 else 1.8,0.,0.,.02 if t>=.5 else 0.,0.,0.))
        self.assertTrue(isolated_gap(w,.3,w.times[50]))
        self.assertIsNone(isolated_gap(w,.3,.54))

    def test_opposing_current_with_driver_on_is_a_failure(self):
        w = trace(lambda t:step_charge(t, gate=0.))
        result = inspect_strong(w,.1,.8,payload_event=.2,payload=255)
        self.assertTrue(result['overlap'])
        self.assertFalse(result['isolated'])

    def test_gate_off_charge_event_recovers_to_quiet_rail(self):
        result = inspect_strong(trace(step_charge),.1,.8,payload_event=.2,payload=255)
        self.assertFalse(result['overlap'])
        self.assertTrue(result['isolated'])
        self.assertTrue(all(bit['charge_response'] for bit in result['bits']))

    def test_gate_off_persistent_current_remains_unverified(self):
        def pattern(t):
            return step_charge(t) if t<.28 else (1.8,1.8,0.,1.799,.00025,-.00025,0.)
        result = inspect_strong(trace(pattern),.1,.8,payload_event=.2,payload=255)
        self.assertFalse(result['overlap'])
        self.assertFalse(result['isolated'])
        self.assertTrue(all(bit['opposition_with_gate_off'] for bit in result['bits']))

    def test_gate_off_currents_wrong_polarity_or_reappearing_are_unverified(self):
        for mode in ('wrong_polarity','recurrence'):
            def pattern(t):
                te,h,w,p,ih,im,iw = step_charge(t)
                if mode=='recurrence' and .40<=t<=.49:
                    return te,h,w,p,.0003,-.0003,iw
                return te,h,w,p,-ih if mode=='wrong_polarity' else ih,-im if mode=='wrong_polarity' else im,iw
            with self.subTest(mode=mode):
                self.assertFalse(inspect_strong(trace(pattern),.1,.8,payload_event=.2,payload=255)['isolated'])

    def test_strong_window_rejects_weak_probe_still_enabled(self):
        def pattern(t):
            te,h,_,p,ih,im,iw = step_charge(t)
            return te,h,1.8,p,ih,im,iw
        self.assertFalse(inspect_strong(trace(pattern),.1,.8,payload_event=.2,payload=255)['isolated'])


if __name__ == '__main__':
    unittest.main()
