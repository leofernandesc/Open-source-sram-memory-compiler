"""Reject electrically unsafe controls even when sampled read data looks right."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase2_access_checks import check


class ElectricalProtocolTests(unittest.TestCase):
    def trace(self):
        data=np.zeros((3001,17));data[:,0]=np.linspace(0,30e-9,3001)
        return data,[{'cycle':0,'operation':'idle','row':0,'rise_ns':10,'fall_ns':20,'expected':0}]

    def test_reject_write_precharge_contention_independent_of_read_result(self):
        data,records=self.trace();data[1200:1230,12]=1.8
        result,_=check(data,records,[str(i) for i in range(16)])
        self.assertIn(('write_precharge_nonoverlap','FAIL'),[(c['kind'],c['status']) for c in result])

    def test_reject_multiple_rows(self):
        data,records=self.trace();data[1200:1500,13:15]=1.8
        result,_=check(data,records,[str(i) for i in range(16)])
        self.assertEqual(result[0]['status'],'FAIL')

    def test_reject_late_wordline_release(self):
        data,records=self.trace();data[2150:2250,13]=1.8
        result,_=check(data,records,[str(i) for i in range(16)])
        self.assertIn(('low_phase_wordlines','FAIL'),[(c['kind'],c['status']) for c in result])

    def test_reject_misdeclared_waveform_columns(self):
        data,records=self.trace()
        with self.assertRaises(ValueError):check(data,records,['missing'])

    def test_clock_arrival_delay_allowed_only_before_precharge_conduction(self):
        data,records=self.trace();data[2000:2300,10]=1.8;data[2000:2070,13]=1.8
        result,_=check(data,records,[str(i) for i in range(16)])
        self.assertFalse(any(c['status']=='FAIL' for c in result))
        data[2050:2300,10]=0
        result,_=check(data,records,[str(i) for i in range(16)])
        self.assertIn(('wordline_precharge_nonoverlap','FAIL'),[(c['kind'],c['status']) for c in result])

    def test_precharge_must_finish_before_next_access(self):
        data,records=self.trace();data[2000:,10]=1.8
        result,_=check(data,records,[str(i) for i in range(16)])
        self.assertIn(('precharge_ready_before_next_access','FAIL'),[(c['kind'],c['status']) for c in result])


if __name__=='__main__':unittest.main()
