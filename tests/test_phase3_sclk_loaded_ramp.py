"""Software checks for historical startup replay and the loaded control gate."""

from decimal import Decimal
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from phase3_sclk_loaded_ramp import (
    HORIZON, OFFSET, extend_card, final_verdict, guard, observed_bench, pwl_tokens,
)


class StartupTests(unittest.TestCase):
    def test_same_voltages_and_spacing_after_common_shift(self):
        source='VREPLAY0 archive_0 VSS PWL(0n 0 3.025n 0.900 100n 1.8\n+ )'
        new=extend_card(source,np.array([0.,10.025,46.]),np.array([0.,.9,0.]))
        points=pwl_tokens(new)[1]
        self.assertEqual(points[-3:],[(t+Decimal(OFFSET),v) for t,v in pwl_tokens(source)[1]])
        self.assertEqual([t for t,v in points[:3]],[Decimal(0),Decimal('10.025'),Decimal(46)])

    def test_observation_keeps_numeric_options_and_no_uic(self):
        config='.options method=gear reltol=1e-4 vabstol=1e-8 iabstol=1e-12\n.options klu\n'
        old=config+'.save v(r)\n.control\ntran 10p 100n 0 25p\nwrdata waveform.dat v(r)\nquit\n.endc\n'
        result=observed_bench(old,['v(q)'])
        self.assertTrue(result.startswith(config))
        self.assertIn(f'tran 10p {HORIZON:g}n 0 25p\n',result)
        self.assertIn('wrdata waveform.dat v(r) v(q)',result)
        self.assertNotIn('uic',result.lower())

    def test_time_limits_are_specific_to_each_phase(self):
        op={'tran_dispatch':{'elapsed_s':240},'dynamic_gmin_failed':{'elapsed_s':250}}
        self.assertIsNone(guard(539.,op,None))
        self.assertEqual(guard(540.,op,None),'INITIAL_SOLUTION_WALL_LIMIT')
        solved=dict(op,initial_solution_reported={'elapsed_s':270})
        self.assertIsNone(guard(650.,solved,None))
        self.assertEqual(guard(1198.,solved,None),'TOTAL_WALL_LIMIT')
        self.assertEqual(guard(300.,{},None),'PREPARATION_WALL_LIMIT')
        self.assertEqual(guard(310.,solved,'analysis aborted'),'SIMULATOR_ERROR')


class FunctionalTests(unittest.TestCase):
    def test_completed_reads_do_not_mask_missing_or_incorrect_storage(self):
        reads=[dict(observed_word=x,archived_word=x,logical_reference=True,equivalent=True)
               for x in (15,248,248)]
        writes=[dict(stored_after_write=x,expected=x,confirmed=True) for x in (15,240)]
        self.assertEqual(final_verdict(reads,writes),'VALIDATED')
        reads[-1]['equivalent']=False
        self.assertEqual(final_verdict(reads,writes),'INCONCLUSIVE')
        writes[-1]['stored_after_write']=248
        self.assertEqual(final_verdict(reads,writes),'NOT_REPRODUCED')
        writes[-1].update(stored_after_write=None,confirmed=False)
        self.assertEqual(final_verdict(reads,writes),'INCONCLUSIVE')


if __name__=='__main__':
    unittest.main()
