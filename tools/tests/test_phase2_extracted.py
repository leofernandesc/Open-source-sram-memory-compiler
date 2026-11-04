"""Probes must follow extracted nets without concealing opens or shorts."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase2_extracted import bind


class ExtractedBindingTests(unittest.TestCase):
    def fixture(self):
        design={'modules':{'sram_4x8_wrapper':{
            'ports':{'A':{'bits':[2]},'Y':{'bits':[3]},'VSS':{'bits':[4]}},
            'cells':{'fabric':{'type':'leaf_fabric','connections':{'A0':[2],'DEC0':[3]}}}}}}
        spice='.subckt flat A Y VSS\n'+''.join(
            f'X{i} W{i} A Y VSS sky130_fd_pr__nfet_01v8 w=.42 l=.15 ad=.2 as=.3\n' for i in range(4))+'.ends\n'
        ext='node "A"\nnode "Y"\nnode "VSS"\nequiv "A" "fabric.A0"\nequiv "Y" "fabric.DEC0"\n'+''.join(
            f'node "W{i}"\nequiv "W{i}" "fabric.wl_driver_{i}.WL"\n' for i in range(4))
        return spice,ext,design

    def test_preserves_devices_and_junction_parameters(self):
        spice,ext,design=self.fixture();flat,probes,proof=bind(spice,ext,design)
        self.assertEqual(proof['mos'],4);self.assertEqual(proof['signal_nets_checked'],3)
        self.assertEqual(flat.count('w=.42 l=.15 ad=.2 as=.3'),4)
        self.assertEqual(probes['v(xdut.A)'],'v(xdut.A)')
        self.assertIn('v(xdut.xmapped0.WL3)',probes)

    def test_rejects_extracted_open_instead_of_repairing_from_hdl(self):
        spice,ext,design=self.fixture();ext=ext.replace('equiv "A" "fabric.A0"','equiv "Y" "fabric.A0"')
        with self.assertRaisesRegex(ValueError,'split'):bind(spice,ext,design)

    def test_rejects_two_hdl_nets_short_in_layout(self):
        spice,ext,design=self.fixture();spice=spice.replace('.subckt flat A Y VSS','.subckt flat A VSS').replace(' A Y VSS',' A A VSS')
        ext=ext.replace('node "Y"','equiv "A" "Y"')
        with self.assertRaisesRegex(ValueError,'short'):bind(spice,ext,design)

    def test_missing_probe_alias_is_a_failure(self):
        spice,ext,design=self.fixture();ext=ext.replace('equiv "W3" "fabric.wl_driver_3.WL"','')
        with self.assertRaisesRegex(ValueError,'Missing extracted observation'):bind(spice,ext,design)


if __name__=='__main__':unittest.main()
