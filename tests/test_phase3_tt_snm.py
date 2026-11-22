"""Offline regression tests for TT preparation and statistical SNM analysis."""

import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from phase3_snm_measure import butterfly, read_vtc, statistics
from run_phase3_integrated_tt import PDK, tt_deck
from run_phase3_snm import design, nominal_deck, paired_snm, reported_seed, result_for, run, sha256


class TTDeckTests(unittest.TestCase):
    def test_one_model_change_preserves_deck_bytes(self):
        old = f'* frozen fixture\n.lib "{PDK}" ss\n.temp 27\n.tran 10p 370n\n.end\n'
        self.assertEqual(tt_deck(old),old.replace('" ss','" tt'))

    def test_invalid_or_duplicate_lib_cannot_be_used(self):
        for bad in ('.lib "untrusted.spice" ss\n',f'.lib "{PDK}" tt\n',
                    f'.lib "{PDK}" ss\n.lib "{PDK}" ss\n'):
            with self.subTest(card=bad), self.assertRaises(ValueError):
                tt_deck(bad)


class SNMTests(unittest.TestCase):
    def setUp(self):
        self.x = np.array([0.,.4,.6,1.])

    def test_known_square_at_rails_and_roundoff_close_to_rails(self):
        for dr in (0.,1e-9):
            f = np.array([1.-dr,1.-dr,dr,dr])
            val = butterfly(self.x,f,f)
            self.assertEqual(val['classification'],'BISTABLE')
            self.assertEqual(len(val['intersection_u_v']),3)
            self.assertAlmostEqual(val['snm_v'],.4,places=7)

    def test_smaller_asymmetric_lobe_is_selected_and_is_invariant_to_side_swap(self):
        xa = np.linspace(0,1,21)
        l = np.clip((.60-xa)/.20,0.,1.)
        r = np.clip((.68-xa)/.18,0.,1.)
        val = butterfly(xa,l,r)
        self.assertGreater(abs(val['lobes_v'][0]-val['lobes_v'][1]),.01)
        self.assertEqual(val['snm_v'],min(val['lobes_v']))
        self.assertAlmostEqual(val['snm_v'],butterfly(xa,r,l)['snm_v'])

    def test_legacy_false_positive_on_monostable_case(self):
        f = .75-.5*self.x
        self.assertGreater(paired_snm(self.x,f,f),0.)
        self.assertEqual(butterfly(self.x,f,f)['classification'],'MONOSTABLE_ZERO')
        self.assertEqual(butterfly(self.x,f,f)['snm_v'],0.)

    def test_bad_trace_does_not_become_zero(self):
        for bad in ([1.,.4,.5,0.],[1.,.8,.2,np.nan]):
            with self.subTest(output=bad), self.assertRaises(ValueError):
                butterfly(self.x,bad,bad)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'vtc.dat'
            path.write_text('v-sweep v(in) v(out_l) v(out_r)\n0 0 1 1\n.5 .5 .6 .6\n')
            with self.assertRaisesRegex(ValueError,'Incomplete'):
                read_vtc(path,1.,.5)

    def test_statistics_keep_physical_zeros_and_reproduce_interval(self):
        values = [0.,.1,.2,.3,.4]
        a = statistics(values,draws=1000)
        self.assertEqual(a,statistics(values,draws=1000))
        self.assertEqual(a['zero_count'],1)
        self.assertAlmostEqual(a['mean_v'],.2)
        self.assertAlmostEqual(a['sample_std_v'],np.std(values,ddof=1))
        self.assertLess(a['mean_ci95_v'][0],a['mean_v'])
        self.assertGreater(a['mean_ci95_v'][1],a['mean_v'])

    def test_seed_configuration_is_parsed_from_ngspice_44_log(self):
        self.assertEqual(reported_seed('Note: fixture\nSeed value for random number generator is set to 1001\n'),1001)
        self.assertIsNone(reported_seed('unrelated message: 1001'))

    def test_nominal_deck_retains_all_six_transistors_and_uses_read_or_hold_wl(self):
        for mode,wl in (('hold','0'),('read','vdd')):
            c = design('nominal-proposed',mode,20001,200)
            b = nominal_deck(c['cases'][0],c)
            self.assertEqual(b.count('\nXM'),6)
            self.assertIn(f'XMAL out_l {wl} vdd 0 ',b)
            self.assertIn(f'XMAR vdd {wl} out_r 0 ',b)
            self.assertIn('.options seed=20001 seedinfo',b)
            self.assertIn(' tt_mm\n',b)

    def test_definitive_series_has_predeclared_unique_seeds(self):
        cfg = design('nominal-proposed','hold',20001,220)
        self.assertEqual(len({x['seed'] for x in cfg['cases']}),220)
        with self.assertRaises(ValueError):
            design('nominal-proposed','hold',20001,199)
        self.assertEqual(len(design('legacy-pilot','hold',1001,200)['cases']),5)

    def test_resume_checks_hashes_skips_success_and_retries_only_when_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            cfg = design('nominal-proposed','hold',20001,200)
            receipt = dict(config=cfg,models={'fake':True},sources={},ngspice_version='fake')
            mf = out/'manifest.json'
            mf.write_text(json.dumps(receipt))
            for case,state in zip(cfg['cases'],('MEASURED','TIMEOUT')):
                attempt = out/case['id']/'attempt-001'
                attempt.mkdir(parents=True)
                path = attempt/'ngspice.log'
                path.write_text(state)
                (attempt/'result.json').write_text(json.dumps(
                    {**case,'status':state,'manifest_sha256':sha256(mf),'artifacts':{path.name:sha256(path)},
                     'attempt':str(attempt.relative_to(out))}))
            cli = argparse.Namespace(output=out,retry_failed=False,limit=1,timeout=30)
            with patch('run_phase3_snm.model_config',return_value=receipt['models']), \
                    patch('run_phase3_snm.subprocess.run') as process, patch('run_phase3_snm.run_case') as run_case:
                process.return_value.stdout = 'fake'
                run(cli)
                self.assertEqual(run_case.call_args.args[1]['seed'],20003)
                cli.retry_failed = True
                run(cli)
                self.assertEqual(run_case.call_args.args[1]['seed'],20002)
            bad = out/'20001/attempt-001/ngspice.log'
            bad.write_text('changed')
            with self.assertRaises(ValueError):
                result_for(out,cfg['cases'][0])


if __name__=='__main__':
    unittest.main()
