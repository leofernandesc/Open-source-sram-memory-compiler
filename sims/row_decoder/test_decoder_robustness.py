"""Check physical units/polarity and independent-data parsing for the study."""
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import audit_sky130_measurements as mdm
import run_decoder_robustness as study


class MeasurementParserTests(unittest.TestCase):
    def fixture(self,body):
        return ('BEGIN_HEADER\nVS V 3 CON 0\nVB V 4 CON 0\nEND_HEADER\n'
                'BEGIN_DB\nICCAP_VAR VD 1.8\n# VG IG ID IB\n'+body+'\nEND_DB\n')

    def test_reordered_columns_keep_negative_measured_current(self):
        row=mdm.parse_mdm(self.fixture('-0.1 2e-12 -3e-9 4e-12'))[0]
        self.assertEqual(row['VGS'],-.1);self.assertEqual(row['VDS'],1.8)
        self.assertEqual(row['ID'],-3e-9);self.assertEqual(row['IG'],2e-12)

    def test_nonfinite_incomplete_and_missing_columns_are_rejected(self):
        for text in (self.fixture('0 0 nan 0'),self.fixture('0 0 1 0').replace('END_DB',''),
                     self.fixture('0 0 1 0').replace('ICCAP_VAR VD 1.8','')):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):mdm.parse_mdm(text)

    def test_multiplicity_is_kept_as_metadata(self):
        r=mdm.geometry('sky130_nfet_01v8_w0p42u_l0p15u_m20(test).mdm')
        self.assertEqual(r['multiplicity_label'],20);self.assertEqual(r['w_um'],.42)


class PhysicalStressTests(unittest.TestCase):
    def deck(self,kind,value,width=0):
        with patch.object(study.timing,'make_deck',return_value=('.save v(pclk)\n',
            {f'x{i}':{} for i in range(45)})):
            return study.make_deck({},'tt',1,2,study.timing.schedule(3,2.5,2100),
                5,102.873935496,width,None,kind,value,1.5)

    def test_leakage_is_microamps_and_only_unselected_nodes_are_pulled_down(self):
        deck,_,targets=self.deck('leak_down',10)
        self.assertEqual(targets,[0,1,3]);self.assertNotIn('ISTRESS2',deck)
        self.assertIn('ISTRESS0 xdec.N0 0 PWL',deck)
        points=list(map(float,re.search(r'PWL\(([^)]+)\)',deck)[1].split()))
        self.assertAlmostEqual(max(points[1::2]),10e-6)
        self.assertAlmostEqual(np.trapz(points[1::2],points[::2])/1e-15,25,places=7)

    def test_charge_is_femtocoulombs_and_retains_its_sign(self):
        deck,_,_=self.deck('charge_down',16)
        points=list(map(float,re.search(r'PWL\(([^)]+)\)',deck)[1].split()))
        self.assertAlmostEqual(np.trapz(points[1::2],points[::2])/1e-15,16,places=7)
        self.assertIn('ISTRESS3 xdec.N3 0',deck)

    def test_selected_node_pull_up_has_opposite_source_orientation(self):
        deck,_,targets=self.deck('leak_up',1)
        self.assertEqual(targets,[2]);self.assertIn('ISTRESS2 0 xdec.N2',deck)

    def test_keeper_feedback_ports_and_baseline_preservation(self):
        baseline='.subckt row_decoder VDD PCLK A0 A1 DEC0 DEC1 DEC3 DEC2 VSS\nR0 N0 N0.t0 1\n.ends\n'
        with tempfile.TemporaryDirectory() as folder:
            a=Path(folder)/'a.spice';a.write_text(baseline);b=Path(folder)/'b.spice'
            study.candidate_file({'row_decoder':{'path':a}},.42,b)
            self.assertEqual(a.read_text(),baseline)
            for row in range(4):
                self.assertIn(f'XKEEP{row} N{row} DEC{row} VDD VDD sky130_fd_pr__pfet_01v8 w=0.42 l=0.15',b.read_text())


if __name__=='__main__':unittest.main()
