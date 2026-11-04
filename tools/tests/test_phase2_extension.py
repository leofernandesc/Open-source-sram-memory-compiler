"""Observer tests on labeled synthetic traces, never electrical DUT evidence."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_phase2_startup as startup_fixtures
from phase2_extension import check, campaign
from analyze_phase2_extension_timing import crossing, settle, current_event


class ExtensionObserverTests(unittest.TestCase):
    def fixture(self,bus=False):
        d,r,v,p,_,s,stop=startup_fixtures.StartupReviewTests().fixture()
        names=[*[f'ADDR_Q{i}' for i in range(2)],*[f'DIN_Q{i}' for i in range(8)],
               'HOST_EN',*[f'TE_B{i}' for i in range(8)],
               *[f'I_{n}{i}' for n in ('HOST','WEAK') for i in range(8)]]
        for n in names:p[n]=f'v(synthetic_{n})';v.append(p[n])
        d=np.column_stack((d,np.zeros((len(d),len(names)))))
        col=lambda n:v.index(p[n])+1
        for b in range(8):
            d[:,col(f'DIN_Q{b}')]=1.8*((0xAA>>b)&1)
            d[:,col(f'TE_B{b}')]=1.8
        if bus:
            t=d[:,0]*1e9
            r[0].update(host_enable_ns=8,host_payload_ns=7.5)
            r[1]['calibration']=dict(mask_ns=42.5,restore_ns=44,weak_off_ns=45.5)
            for b in range(8):
                enabled=((t>=42)&(t<=42.35))|((t>=44.7)&(t<=45.2))
                d[enabled,col(f'I_WEAK{b}')]=100e-6
                masked=(t>=43.2)&(t<=43.8)
                d[masked,b+1]=1.8*(1-((0xAA>>b)&1))
        return d,r,v,p,s,stop,'bus' if bus else 'sequences'

    def failures(self,args):
        return [c['kind'] for c in check(*args)[0] if c['status']=='FAIL']

    def test_independent_reference_fixture(self):
        self.assertEqual(self.failures(self.fixture()),[])
        self.assertEqual(self.failures(self.fixture(True)),[])

    def test_wrong_captured_data_and_address(self):
        a=self.fixture();a[0][:,a[2].index(a[3]['DIN_Q0'])+1]=1.8
        a[0][:,a[2].index(a[3]['ADDR_Q0'])+1]=1.8
        self.assertIn('captured_write_data',self.failures(a))
        self.assertIn('captured_address',self.failures(a))

    def test_collateral_known_storage(self):
        a=self.fixture();a[0][6200:6202,a[2].index(a[3]['CELL_0_0'])+1]=1.8
        self.assertIn('known_storage',self.failures(a))

    def test_unwritten_storage_is_not_assumed(self):
        a=self.fixture();a[0][:,a[2].index(a[3]['CELL_3_7'])+1]=.8
        self.assertEqual(self.failures(a),[])

    def test_expected_read_requires_prior_write(self):
        a=self.fixture();a[1][1]['row']=1
        with self.assertRaisesRegex(ValueError,'not established'):check(*a)

    def test_nonfinite_and_truncated_rejected(self):
        a=self.fixture();a[0][1,1]=float('nan')
        with self.assertRaisesRegex(ValueError,'Invalid'):check(*a)
        a=self.fixture();a=(a[0][:-100],*a[1:])
        with self.assertRaisesRegex(ValueError,'Incomplete'):check(*a)

    def test_voltage_alone_cannot_fake_bus_release(self):
        a=self.fixture(True);t=a[0][:,0]*1e9
        a[0][(t>=43.2)&(t<=43.8),a[2].index(a[3]['I_WEAK0'])+1]=100e-6
        self.assertIn('masked_probe_current',self.failures(a))

    def test_current_alone_cannot_fake_probe_voltage(self):
        a=self.fixture(True);t=a[0][:,0]*1e9;a[0][(t>=43.2)&(t<=43.8),1]=0
        self.assertIn('masked_probe_voltage',self.failures(a))

    def test_invisible_load_rejected(self):
        a=self.fixture(True);a[0][:,a[2].index(a[3]['I_WEAK0'])+1]=0
        self.assertIn('probe_observes_enabled_drive',self.failures(a))

    def test_strong_driver_overlap_and_current_rejected(self):
        a=self.fixture(True);a[0][900:950,a[2].index(a[3]['I_HOST0'])+1]=.001
        a[0][900:950,a[2].index(a[3]['HOST_EN'])+1]=1.8
        a[0][900:950,a[2].index(a[3]['TE_B0'])+1]=0
        self.assertIn('strong_master_steady_current',self.failures(a))
        self.assertIn('no_strong_host_ebuf_overlap',self.failures(a))

    def test_capture_retention_during_mask(self):
        a=self.fixture(True);a[0][4350:4352,a[2].index(a[3]['REG_Q0'])+1]=1.8
        self.assertIn('mask_preserves_ff_q',self.failures(a))

    def test_crossing_unique_and_interpolated(self):
        t=np.array([0.,1.,2.]);v=np.array([0.,1.,2.])
        self.assertEqual(crossing(t,v,.5,0,2),.5)
        with self.assertRaisesRegex(ValueError,'found 0'):crossing(t,v,3,0,2)

    def test_settling_does_not_measure_unchanged_as_transition(self):
        t=np.array([0.,1.,2.]);self.assertEqual(settle(t,np.zeros(3),0,0,2),(0.,True))
        self.assertEqual(settle(t,np.array([1.8,0.,0.]),0,0,2),(1.,False))
        with self.assertRaisesRegex(ValueError,'not valid'):settle(t,np.ones(3)*.9,0,0,2)

    def test_current_floor_interpolation(self):
        t=np.array([0.,1.,2.]);v=np.array([100.,0.,0.])*1e-6
        when,bound=current_event(t,v,0,2,False)
        self.assertAlmostEqual(when,.5);self.assertFalse(bound)

    def test_output_not_overwritten(self):
        root=Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory(dir=root/'reports/phase2') as d:
            path=Path(d)/'results.json';path.write_text('preserve\n')
            run=subprocess.run([sys.executable,str(root/'tools/run_phase2_extension.py'),
                 '--campaign','sequences','--output',d],capture_output=True,text=True)
            self.assertEqual(run.returncode,2);self.assertEqual(path.read_text(),'preserve\n')

if __name__=='__main__':unittest.main()
