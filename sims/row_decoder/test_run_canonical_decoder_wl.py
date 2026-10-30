"""Regression checks for frozen-pair pin mapping and waveform rejection."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import run_canonical_decoder_wl as runner


class CanonicalPairTests(unittest.TestCase):
    def synthetic(self):
        time=np.linspace(0,27.5e-9,5501)
        first=(time>=5.2e-9)&(time<=10e-9)
        second=(time>=17.3e-9)&(time<=22.5e-9)
        raw={'time':time,'v(vdd)':np.full_like(time,1.8)}
        for family in ('dec','wl'):
            for row in range(4):
                raw[f'v({family}{row})']=1.8*((first if row==0 else np.zeros_like(first))|
                                             (second if row==3 else np.zeros_like(second)))
        return raw

    def analysis(self,raw):
        terminals={'probe':dict(d='WL3',g='VDD',s='0',b='0')}
        return runner.analyze(raw,'tt',0,3,terminals,3.8)[0]

    def test_port_order_comes_from_subcircuit(self):
        result=runner.instance('X','decoder',['VDD','DEC3','DEC2'],
                               dict(VDD='PWR',DEC2='ROW2',DEC3='ROW3'))
        self.assertEqual(result,'X PWR ROW3 ROW2 decoder')

    def test_missing_port_is_rejected(self):
        with self.assertRaises(ValueError):
            runner.instance('X','decoder',['DEC3','DEC2'],dict(DEC3='ROW3'))

    def test_changed_release_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);release=root/'release';release.mkdir()
            (root/'fixture').write_text('changed')
            (release/'checksums.json').write_text(json.dumps({'fixture':hashlib.sha256(b'expected').hexdigest()}))
            with patch.object(runner,'ROOT',root),self.assertRaisesRegex(ValueError,'Release evidence changed'):
                runner.release_inputs(release)

    def test_correct_selection_passes(self):
        self.assertEqual(self.analysis(self.synthetic())['status'],'PASS_SCREEN')

    def test_wrong_wordline_is_rejected(self):
        raw=self.synthetic();mask=(raw['time']>=17.3e-9)&(raw['time']<=22.5e-9)
        raw['v(wl2)'][mask]=1.8
        self.assertEqual(self.analysis(raw)['functional_status'],'FAIL')

    def test_late_wordline_is_rejected(self):
        raw=self.synthetic();mask=(raw['time']>10e-9)&(raw['time']<21.5e-9)
        raw['v(wl3)'][mask]=0
        self.assertEqual(self.analysis(raw)['functional_status'],'FAIL')

    def test_bias_screen_is_separate_from_functionality(self):
        raw=self.synthetic();raw['v(vdd)'][:]=2.1
        result=self.analysis(raw)
        self.assertEqual(result['functional_status'],'PASS')
        self.assertEqual(result['voltage_screen_status'],'REVIEW_REQUIRED')

    def test_incomplete_record_is_rejected(self):
        raw={name:values[:-400] for name,values in self.synthetic().items()}
        with self.assertRaisesRegex(ValueError,'Incomplete transient'):
            self.analysis(raw)


if __name__=='__main__':
    unittest.main()
