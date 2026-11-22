"""Software-only checks for the extended TT replay and its contrast gate."""

from decimal import Decimal
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from phase3_sense3_precondition import (
    START, control_verdict, delayed_source, extend_pwl, outside, pwl_tokens, validate_authorization,
)


class ReplayTest(unittest.TestCase):
    def test_extension_preserves_old_knots_exactly(self):
        card='VPORT0 rc8202 VSS PWL(0n 1.799881840 1.111111111n 1.80253526214\n+ 39n 1.8\n+ )'
        times=np.array([188.,194.,199.,208.])
        volts=np.array([1.79988,1.72,1.81,1.79988184])
        output,info=extend_pwl(card,times,volts)
        head,knots=pwl_tokens(output)
        self.assertEqual(head,'VPORT0 rc8202 VSS')
        self.assertEqual(knots[-3:],[(t+Decimal(20),v) for t,v in pwl_tokens(card)[1]])
        self.assertEqual(info['preserved_knots'],3)
        self.assertLessEqual(info['max_history_error_v'],1e-4)

    def test_reject_inconsistent_seam(self):
        with self.assertRaisesRegex(ValueError,'seam'):
            extend_pwl('VPORT0 a VSS PWL(0n 1.7 39n 1.8)',np.array([188.,208.]),np.array([1.8,1.8]))

    def test_delay_only_in_two_rise_windows(self):
        source='VPORT0 rc8562 VSS PWL(0n 0 6n 0 6.5n 1.8 16n 1.8 16.5n 0 26n 0 26.5n 1.8 36n 1.8 36.5n 0 46n 0 46.5n 1.8 56n 1.8 56.5n 0 59n 0)'
        _,clock=pwl_tokens(source)
        _,series=pwl_tokens(delayed_source(source))
        def voltage(t,data):
            return np.interp(t,[float(x)+START for x,_ in data],[float(y) for _,y in data])
        for t in [194.25,204.25,224.25,244.25,211.,231.]:
            self.assertEqual(voltage(t,series),0.)
        for t in (214.432,234.432):
            self.assertAlmostEqual(voltage(t,clock)+voltage(t,series),.9,places=6)


class AcceptanceTest(unittest.TestCase):
    def test_intermediate_n_tail_excursion_counts(self):
        self.assertEqual(outside([0.,1.,2.,3.],[0.,.06,-.06,0.],.03),[[.5,1.25],[1.75,2.5]])
        self.assertEqual(outside([0.,1.,2.],[.03,-.03,.03],.03),[])

    def case(self):
        return dict(reference={'decision':'WRONG'},isolated={'decision':'WRONG'},input={'eligible':True},
                    conditioning_valid=True,tail={'envelope_compatible':True,'tail_conduction':[{}]},
                    clock_valid=True,decision_timing_compatible=True)

    def test_validation_requires_all_electrical_and_regeneration_checks(self):
        one,two=self.case(),self.case()
        self.assertEqual(control_verdict([one,two]),'VALIDATED')
        one['tail']['envelope_compatible']=False
        self.assertEqual(control_verdict([one,two]),'INCONCLUSIVE')
        one['tail']['envelope_compatible']=True
        one['decision_timing_compatible']=False
        self.assertEqual(control_verdict([one,two]),'INCONCLUSIVE')
        one['isolated']['decision']='CORRECT'
        self.assertEqual(control_verdict([one,two]),'NOT_REPRODUCED')

    def test_unvalidated_or_unpinned_gate_cannot_authorize_contrast(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            gate=root/'control_gate.json'
            gate.write_text(json.dumps({'verdict':'INCONCLUSIVE','contrast_authorized':False}))
            with self.assertRaisesRegex(ValueError,'did not validate'):
                validate_authorization(root)
            (root/'manifest.json').write_text('{}')
            gate.write_text(json.dumps({'verdict':'VALIDATED','contrast_authorized':True,'manifest_sha256':'0'*64}))
            with self.assertRaisesRegex(ValueError,'Input hash differs'):
                validate_authorization(root)


if __name__=='__main__':
    unittest.main()
