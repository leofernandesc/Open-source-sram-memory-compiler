"""Do not confuse Netgen structural uniqueness with parameter correctness."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audit_phase2 import negative_lvs


class LVSReceiptTests(unittest.TestCase):
    def width(self):
        return '''W circuit1: 2.016e-06 circuit2: 1.68e-06
Final result: Circuits match uniquely.
Property errors were found.
The following cells had property errors:
 pilot_flat
'''

    def test_width_defect_rejected_even_when_connectivity_is_unique(self):
        negative_lvs(self.width(),'width')

    def test_reject_unrelated_property_error_scope(self):
        with self.assertRaises(ValueError):negative_lvs(self.width().replace('pilot_flat','other_cell'),'width')

    def test_reject_wrong_width_mutation(self):
        with self.assertRaises(ValueError):negative_lvs(self.width().replace('2.016e-06','1.68e-06'),'width')

    def test_require_deliberate_gate_mismatch_in_successful_tool_run(self):
        text='Net: INJECTED_GATE\nFinal result: Netlists do not match.\n'
        negative_lvs(text,'gate')
        with self.assertRaises(ValueError):negative_lvs('failed to open input\n'+text,'gate')
        with self.assertRaises(ValueError):negative_lvs(text.replace('INJECTED_GATE','unrelated'),'gate')


if __name__=='__main__':unittest.main()
