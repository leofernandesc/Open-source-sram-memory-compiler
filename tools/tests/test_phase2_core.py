"""Independent topology audit must catch plausible cross-view common-mode errors."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import phase2_core as core


class CoreTopologyTests(unittest.TestCase):
    def test_reject_address_bit_permutation_even_when_matrix_is_complete(self):
        d=core.graph()
        a,b=d['instances'][0],d['instances'][8]
        a['pins']['WL'],b['pins']['WL']=b['pins']['WL'],a['pins']['WL']
        with self.assertRaises(ValueError):core.audit(d)

    def test_reject_shared_wrong_graph_for_reference_and_layout(self):
        for name,pin,wrong in [('decode','DEC2','DEC3'),('write0','BLB','BL0'),
                               ('sense7','SA_OUT','DOUT6'),('qualify0','B','VDD'),
                               ('complement0','A','DIN1')]:
            with self.subTest(name=name,pin=pin):
                d=core.graph();next(i for i in d['instances'] if i['name']==name)['pins'][pin]=wrong
                with self.assertRaises(ValueError):core.audit(d)

    def test_reject_missing_and_duplicate_storage(self):
        for duplicate in (False,True):
            d=core.graph()
            if duplicate:d['instances'].append(copy.deepcopy(d['instances'][0]))
            else:d['instances'].pop(0)
            with self.assertRaises(ValueError):core.audit(d)


if __name__=='__main__':unittest.main()
