"""Scientific regression checks for signed model states and missing probes."""
import unittest
from pathlib import Path
import tempfile
import numpy as np
import run_canonical_intrinsic_bias as probe


class IntrinsicBiasTests(unittest.TestCase):
    def test_nfet_forward_polarity(self):
        result=probe.oriented_states('n',np.array([0.7]),np.array([0.8]),np.array([-0.1]))
        self.assertAlmostEqual(result['VGS'][0],0.7)
        self.assertAlmostEqual(result['VDS'][0],0.8)
        self.assertAlmostEqual(result['VBS'][0],-0.1)

    def test_nfet_reverse_uses_gate_drain_and_body_drain(self):
        result=probe.oriented_states('n',np.array([-0.2]),np.array([-0.8]),np.array([-1.0]))
        self.assertAlmostEqual(result['VGS'][0],0.6)
        self.assertAlmostEqual(result['VDS'][0],0.8)
        self.assertAlmostEqual(result['VBS'][0],-0.2)

    def test_pfet_physical_sign_and_reverse_mode(self):
        result=probe.oriented_states('p',np.array([0.4]),np.array([-0.8]),np.array([-0.9]))
        self.assertAlmostEqual(result['VGS'][0],-1.2)
        self.assertAlmostEqual(result['VDS'][0],-0.8)
        self.assertAlmostEqual(result['VBS'][0],0.1)

    def test_off_nfet_negative_vgs_is_not_clipped(self):
        result=probe.oriented_states('n',np.array([-0.5]),np.array([0.6]),np.array([-0.8]))
        self.assertEqual(result['VGS'][0],-0.5)

    def test_pfet_positive_vgs_is_not_clipped(self):
        result=probe.oriented_states('p',np.array([-0.08]),np.array([0.3]),np.array([0.0]))
        self.assertEqual(result['VGS'][0],0.08)

    def test_unknown_polarity_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unknown MOS polarity'):
            probe.oriented_states('bad',np.array([0]),np.array([0]),np.array([0]))

    def test_missing_model_query_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Missing/ambiguous'):
            probe.state_trace({'time':np.array([0.,1.])},'@m.bad[vgs]')

    def test_nonfinite_query_is_rejected(self):
        raw={'time':np.array([0.,1.]),'v(@m.a[vgs])':np.array([0.,np.nan])}
        with self.assertRaisesRegex(ValueError,'Invalid query'):probe.state_trace(raw,'@m.a[vgs]')

    def test_duration_counts_intervals_not_number_of_samples(self):
        time=np.arange(5)*0.1e-9
        lower,upper=probe.span_bounds_ps(time,np.array([False,True,True,False,False]))
        self.assertAlmostEqual(lower,100)
        self.assertAlmostEqual(upper,300)

    def test_dc_reference_never_targets_an_active_gate_or_terminal(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'leaf.spice'
            path.write_text('.subckt leaf VDD IN OUT VSS\n'
                'X0 OUT gate_only VSS VSS sky130_fd_pr__nfet_01v8 w=1 l=0.15\n'
                'R0 floating floating2 100\nC0 floating IN 1f\n'
                'C1 floating2 VSS 2f\nC2 gate_only VSS 3f\n.ends\n')
            leaf=dict(path=path,pins=['VDD','IN','OUT','VSS'],
                      devices=[['X0','OUT','gate_only','VSS','VSS','sky130_fd_pr__nfet_01v8']])
            islands=probe.passive_islands(dict(row_decoder=leaf,wl_driver=leaf))
            self.assertEqual(len(islands),5)
            for island in islands:
                self.assertEqual(island['component'],['floating','floating2'])
                self.assertAlmostEqual(island['coupling_cap_f']/1e-15,3)

    def test_frozen_pair_has_one_passive_island_and_45_queries(self):
        inputs=probe.pair.release_inputs();islands=probe.passive_islands(inputs)
        self.assertEqual([r['node'] for r in islands],['xdec.m1_160_n1740#'])
        self.assertEqual(len(probe.probe_map(inputs)),45)


if __name__=='__main__':unittest.main()
