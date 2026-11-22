"""Unit checks of the SCLK intervention and campaign batch limits."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from analyze_phase3_sclk_contrast import classify
from complete_phase3_snm import batch_limit
from review_phase3_bus_ss import Trace
from run_phase3_sclk_contrast import GATES, instrument, playback, sizing


class InterventionTests(unittest.TestCase):
    def test_single_displacement_uses_worst_matched_wl_wait(self):
        def checks(activation, wl, ss=False):
            label='sclk_sampling_ns' if ss else 'sclk_tail_ns'
            return [dict(origin_cycle=c,wl_ns={'80':w},capture_ns=20+c,
                         **{label:{'20':a}}) for c,(a,w) in
                    zip((16,17),zip(activation,wl,strict=True),strict=True)]
        inputs=dict(cases={'reduced_tt':{'checks':checks([14.152765,34.152509],[14.215535,34.208891])},
                            'archived_ss':{'checks':checks([16.26585,36.26849],[16.15149,36.14292],True)}})
        delay,rows=sizing(inputs)
        self.assertEqual(delay,182)
        self.assertEqual(len(rows),2)

    def test_playback_moves_times_without_amplitude_change(self):
        trace=Trace([(0.,0.),(.2e-9,.36),(.5e-9,.9),(1e-9,1.8),(2e-9,1.8)],{'gate':1})
        wave=playback(trace,1,[(.1,1.6)],.1)
        self.assertEqual(wave[1][1],.36)
        self.assertAlmostEqual(wave[1][0],.3)
        self.assertEqual(wave[-1],(1.6,1.8))

    def test_original_device_terminals_and_rc_values_persist_in_overlay(self):
        mapping={gate:f'pin{i}' for i,gate in enumerate(GATES)}
        trace=Trace([(0.,0.,0.,0.),(1e-9,1.8,1.8,1.8),(2e-9,1.8,1.8,1.8)],
                    {key:i+1 for i,key in enumerate(GATES)})
        devices=[f'X{i} a pin{i} b c mos' for i in range(3)]
        raw='\n'.join(['.subckt sram in out',*devices,
                       *(f'R{i} upstream pin{i} 500' for i in range(3)),
                       'C1 a pin0 1f','.ends sram'])+'\n'
        overlay,links=instrument(raw,mapping,trace,[(.1,1.9)],.1)
        self.assertTrue(all(line in overlay.splitlines() for line in [*devices,'C1 a pin0 1f']))
        self.assertTrue(all(link['adapter_card'].endswith(' 500') for link in links))
        self.assertEqual(overlay.count('\nB_sclk_fixture_'),3)

    def test_recovery_requires_correct_latch_predecessors_and_low_phase(self):
        pre=[dict(observed_word='0xAA',expected='0xAA',stable_external_word=True),
             dict(observed_word='0x0F',expected='0x0F',stable_external_word=True)]
        item=dict(observed_word='0xF0',stable_external_word=True,valid_sense_and_d_onset=True,
                  cell_correct_from_before_wl_to_observation=True,precharge_recovery=True,
                  correct_input_during_tail_ramp=True,opposite_logic_during_evaluation=False,
                  sclk_tail20_fall_ns=3.,pch_fall50_ns=4.,wrong_data_sustained=False)
        args=(pre,pre+[item,item],[{'verified':True}],[{'peak_error_v':.0001}],True)
        self.assertEqual(classify(*args),'SUPPORTED')
        item['precharge_recovery']=False
        self.assertEqual(classify(*args),'INCONCLUSIVE')
        item.update(observed_word='0xF8',wrong_data_sustained=True)
        self.assertEqual(classify(*args),'NOT_SUPPORTED')


class BatchTests(unittest.TestCase):
    def test_respects_seed_target_batch_and_budget(self):
        self.assertEqual(batch_limit({'MEASURED':4,'NOT_RUN':216},1100,15),50)
        self.assertEqual(batch_limit({'MEASURED':199,'NOT_RUN':20},1100,15),1)
        self.assertEqual(batch_limit({'MEASURED':100,'NOT_RUN':99},89,15),4)
        self.assertEqual(batch_limit({'MEASURED':100,'NOT_RUN':99},26,15),0)
        self.assertEqual(batch_limit({'MEASURED':198,'NOT_RUN':0},1000,15),0)


if __name__=='__main__':
    unittest.main()
