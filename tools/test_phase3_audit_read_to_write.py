"""Regression tests for the provisional read-to-write handoff preconditions."""

import copy
import json
from pathlib import Path
import unittest

from phase3_audit_read_to_write import eligible_handoff
from phase3_rc_read_path import HIGH, LOW
from review_phase3_bus_ss import Trace, ge, le
from phase3_rc_read_path import HIGH, LOW
from review_phase3_bus_ss import Trace, ge, le


ROOT = Path(__file__).resolve().parent.parent


class ReadToWriteHandoffTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run = ROOT / 'build/phase3/integrated_observed_247p5/FF'
        cls.event = json.loads((run / 'revised_ownership.json').read_text())[10]
        cls.fixture = json.loads((run / 'fixture.json').read_text())['cycles'][10]

    def test_existing_ff_c10_is_candidate(self):
        self.assertEqual(eligible_handoff(self.event, self.fixture), (True, []))

    def test_rejects_missing_release_or_gap(self):
        for field, value in [('release_verified', False),
                             ('conductance_gap_isolated', None),
                             ('minimum_sample_separation_ns', 0)]:
            with self.subTest(field=field):
                event = copy.deepcopy(self.event)
                event[field] = value
                self.assertFalse(eligible_handoff(event, self.fixture)[0])

    def test_rejects_host_absent_or_unreleased_weak_probe(self):
        for field, value in [('strong_host_on', False),
                             ('opposition_with_gate_off', {'conservative_ps': 100})]:
            with self.subTest(field=field):
                event = copy.deepcopy(self.event)
                event['strong_check']['bits'][4][field] = value
                self.assertFalse(eligible_handoff(event, self.fixture)[0])
        event = copy.deepcopy(self.event)
        event['strong_check']['weak_host_off'] = False
        self.assertFalse(eligible_handoff(event, self.fixture)[0])

    def test_rejects_idle_to_write_as_read_to_write(self):
        fixture = copy.deepcopy(self.fixture)
        fixture['previous_operation'] = 'idle'
        self.assertFalse(eligible_handoff(self.event, fixture)[0])

    def test_rejects_data_that_stabilizes_late(self):
        # 0.10 ns is stable before CLK, but DATA is incorrect when the host
        # first engages at 1.0 ns. A suffix-only check would accept this trace.
        rows = [[time_ns * 1e-9, value] for time_ns, value in
                [(0.0, 0.0), (0.1, 0.0), (0.5, 0.0),
                 (1.0, 0.0), (1.1, 1.8), (1.2, 1.8),
                 (1.3, 1.8), (1.4, 1.8), (1.5, 1.8), (2.0, 1.8)]]
        trace = Trace(rows, {'time': 0, 'v(data0)': 1})
        expected = [ge(1, HIGH)]
        terminal = trace.signal_window(1.0, 1.5, expected, suffix=True)
        self.assertIsNotNone(terminal)
        self.assertFalse(trace.through(1.0, 1.5, expected))

        low_trace = Trace(rows, {'time': 0, 'v(data0)': 1})
        expected_low = [le(1, LOW)]
        self.assertFalse(low_trace.through(1.0, 1.5, expected_low))


if __name__ == '__main__':
    unittest.main()
