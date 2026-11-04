"""Physical integration may buffer CLK, but cannot silently rewrite phase/data nets."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase2_routed_graph import audit


class RoutedGraphTests(unittest.TestCase):
    def fixture(self):
        original={'modules':{'sram_4x8_wrapper':{
            'ports':{'A':{'bits':[2]},'CLK':{'bits':[3]},'Y':{'bits':[5]}},
            'cells':{'u1':{'type':'sky130_fd_sc_hd__inv_1','connections':{'A':[2],'Y':[4]}},
                     'u2':{'type':'sky130_fd_sc_hd__dfxtp_1','connections':{'D':[4],'CLK':[3],'Q':[5]}}}}}}
        routed=copy.deepcopy(original);cells=routed['modules']['sram_4x8_wrapper']['cells']
        cells['clkbuf']={'type':'sky130_fd_sc_hd__clkbuf_2','connections':{'A':[3],'X':[6]}}
        cells['u2']['connections']['CLK']=[6]
        cells['fill']={'type':'sky130_fd_sc_hd__fill_1','connections':{}}
        return original,routed

    def test_allows_clock_tree_and_physical_fill(self):
        a,b=self.fixture();r=audit(a,b)
        self.assertEqual(r['inserted_clock_buffers'],1);self.assertEqual(r['other_inserted_instances'],1)

    def test_rejects_buffer_inserted_in_phase_instead_of_clock(self):
        a,b=self.fixture();cells=b['modules']['sram_4x8_wrapper']['cells']
        cells['clkbuf']['connections']['A']=[4]
        with self.assertRaisesRegex(ValueError,'outside public CLK'):audit(a,b)

    def test_rejects_data_reconnection(self):
        a,b=self.fixture();b['modules']['sram_4x8_wrapper']['cells']['u2']['connections']['D']=[2]
        with self.assertRaisesRegex(ValueError,'split/reconnection'):audit(a,b)

    def test_rejects_functional_master_replacement(self):
        a,b=self.fixture();b['modules']['sram_4x8_wrapper']['cells']['u1']['type']='sky130_fd_sc_hd__inv_2'
        with self.assertRaisesRegex(ValueError,'Changed functional master'):audit(a,b)

    def test_rejects_missing_functional_instance(self):
        a,b=self.fixture();del b['modules']['sram_4x8_wrapper']['cells']['u1']
        with self.assertRaisesRegex(ValueError,'Lost original'):audit(a,b)


if __name__=='__main__':unittest.main()
