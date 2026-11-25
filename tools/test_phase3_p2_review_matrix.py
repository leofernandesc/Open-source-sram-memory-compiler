"""Check that P2 matrix controls and supplements stay pinned to physical evidence."""

import copy
import json
from pathlib import Path
import unittest

from phase3_p2_review_matrix import (
    AUDITS, OBSERVED, validate_positive_control, validate_supplement,
)
from phase3_audit_integrated_no_transition import validate_receipts


def original(corner):
    run = OBSERVED / corner
    ownership = json.loads((run / 'revised_ownership.json').read_text())
    fixture = json.loads((run / 'fixture.json').read_text())
    analysis = json.loads((run / 'analysis.json').read_text())
    receipt = validate_receipts(run, analysis, fixture, ownership)
    return run, ownership, fixture, receipt


class P2ReviewMatrixTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = {corner: original(corner) for corner in ('TT', 'SS', 'FF')}

    def test_native_positive_controls_have_all_eight_lanes(self):
        for corner, cycle in [('SS', 2), ('TT', 10), ('SS', 10)]:
            with self.subTest(corner=corner, cycle=cycle):
                _, ownership, fixture, receipt = self.runs[corner]
                result = validate_positive_control(
                    corner, cycle, ownership[cycle], fixture['cycles'][cycle], receipt)
                self.assertEqual(result['original_ownership'], 'PASS')
                self.assertEqual(result['native_charge_witness_lanes'], 8)

    def test_positive_control_rejects_missing_lane_or_invalid_handoff(self):
        _, ownership, fixture, receipt = self.runs['SS']
        event = copy.deepcopy(ownership[2])
        event['strong_check']['bits'][4]['charge_response'] = None
        with self.assertRaisesRegex(ValueError, 'positive lane'):
            validate_positive_control('SS', 2, event, fixture['cycles'][2], receipt)

        event = copy.deepcopy(ownership[10])
        event['release_verified'] = False
        with self.assertRaisesRegex(ValueError, 'positive handoff'):
            validate_positive_control('SS', 10, event, fixture['cycles'][10], receipt)

    def test_supplements_match_immutable_source_hashes(self):
        for corner, cycle, file in (
            ('TT', 2, 'TT_static_payload.json'),
            ('FF', 2, 'FF_static_payload_diagnostic.json'),
            ('FF', 10, 'FF_c10_read_to_write_candidate_20261125.json'),
        ):
            with self.subTest(corner=corner, cycle=cycle):
                run, _, _, receipt = self.runs[corner]
                supplement = json.loads((AUDITS / file).read_text())
                validate_supplement(run, supplement, receipt, cycle)
                invalid = copy.deepcopy(supplement)
                key = 'immutable_input_artifacts' if cycle == 2 else 'immutable_source_sha256'
                invalid[key]['waveform.dat'] = '0' * 64
                with self.assertRaisesRegex(ValueError, 'provenance'):
                    validate_supplement(run, invalid, receipt, cycle)


if __name__ == '__main__':
    unittest.main()
