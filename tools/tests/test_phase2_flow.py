"""Guards for mapped technology inventory and parameter-aware physical binding."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_phase2_digital import add_power, mapped_inventory
from run_phase2_physical_pilot import normal_mos


class Phase2FlowTests(unittest.TestCase):
    def design(self):
        types=['sram_4x8_macro']+['sky130_fd_sc_hd__dfxtp_1']*20+['sky130_fd_sc_hd__ebufn_1']*8
        return {'modules':{'sram_4x8_wrapper':{'cells':{str(i):{'type':t} for i,t in enumerate(types)}}}}

    def test_reject_storage_removed_or_register_array(self):
        for replacement in ('sky130_fd_sc_hd__dfxtp_1', '$mem_v2'):
            d=self.design();d['modules']['sram_4x8_wrapper']['cells']['0']['type']=replacement
            with self.assertRaises(ValueError):mapped_inventory(d,'sram_4x8_wrapper')

    def test_reject_generic_tristate_and_latch(self):
        for replacement in ('$_TBUF_','sky130_fd_sc_hd__dlxtp_1'):
            d=self.design();d['modules']['sram_4x8_wrapper']['cells']['1']['type']=replacement
            with self.assertRaises(ValueError):mapped_inventory(d,'sram_4x8_wrapper')

    def test_bind_power_and_body_on_every_mapped_instance(self):
        text='sky130_fd_sc_hd__inv_1 _1_ (.A(a), .Y(b));\nsky130_fd_sc_hd__ebufn_1 \\out[0]  (.A(b));'
        powered=add_power(text)
        self.assertEqual(powered.count('.VPWR(VDD)'),2)
        self.assertEqual(powered.count('.VPB(VDD)'),2)
        self.assertEqual(powered.count('.VNB(VSS)'),2)

    def test_normalize_pdk_suffix_without_million_fold_size_error(self):
        normalized,count=normal_mos('.subckt inv A Z VDD VSS\nX0 Z A VSS VSS sky130_fd_pr__nfet_01v8 w=650000u l=150000u\n.ends','inv')
        self.assertEqual(count,1)
        self.assertIn('w=0.65u l=0.15u',normalized)

    def test_reject_unexpanded_or_multifinger_lvs(self):
        for device in ('X0 a b c d custom_inv w=1 l=.15',
                       'X0 a b c d sky130_fd_pr__nfet_01v8 w=1 l=.15 nf=2'):
            with self.assertRaises(ValueError):normal_mos('.subckt inv a b c d\n'+device+'\n.ends','inv')


if __name__=='__main__':unittest.main()
