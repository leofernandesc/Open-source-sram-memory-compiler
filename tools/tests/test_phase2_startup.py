"""Negative checks for the new startup observer, not SPICE signoff tests."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_phase2_startup_review import SCENARIOS, analyze, levels, validate_trace


class StartupReviewTests(unittest.TestCase):
    def fixture(self):
        # Independent synthetic waveform, intentionally small. The real runner
        # separately uses unchanged extracted SPICE and HD transistor models.
        vectors = [f'v(base{i})' for i in range(16)]
        extra = {n: f'v({n})' for n in ['VDD', 'READ_Q', 'WRITE_Q',
                 *[f'N{r}' for r in range(4)],
                 *[f'{n}{b}' for b in range(8) for n in ('BL', 'BLB', 'REG_Q')],
                 *[f'CELL_{r}_{b}' for r in range(4) for b in range(8)]]}
        vectors += list(extra.values())
        t = np.linspace(0, 90, 9001); data = np.zeros((len(t), len(vectors)+1)); data[:, 0] = t*1e-9
        def col(n): return vectors.index(extra[n])+1
        data[:, col('VDD')] = np.minimum(t, 1)*1.8
        for n in [*[f'N{r}' for r in range(4)], *[f'{n}{b}' for b in range(8) for n in ('BL', 'BLB')]]:
            data[:, col(n)] = 1.8
        # Initial weak probes: alternating patterns, not an initial memory state.
        for lo, hi, value in [(2, 4, 0x69), (4, 6, 0x96)]:
            for b in range(8): data[(t >= lo)&(t < hi), b+1] = 1.8*((value >> b)&1)
        records = [dict(cycle=0, operation='write', row=0, expected=0xAA, rise_ns=10, fall_ns=20, sample_ns=22),
                   dict(cycle=1, operation='read', row=0, expected=0xAA, rise_ns=30, fall_ns=40, sample_ns=42),
                   dict(cycle=2, operation='idle', row=0, expected=0, rise_ns=50, fall_ns=60, sample_ns=62)]
        for r in records:
            edge = r['rise_ns']; end = r['fall_ns']; op = r['operation']
            if op == 'idle':
                data[(t >= edge+4.1)&(t <= edge+8), 1:9] = 1.8
                continue
            data[(t >= edge+1)&(t <= end+2), 10] = 1.8
            data[(t >= edge+2)&(t <= end+.2), 9] = 1.8
            data[(t >= edge+2)&(t <= end+.2), 13] = 1.8
            data[(t >= edge+2)&(t <= end+.2), 12 if op == 'write' else 11] = 1.8
            data[(t >= edge+.2)&(t < edge+19), col('WRITE_Q' if op == 'write' else 'READ_Q')] = 1.8
        for b in range(8):
            v = 1.8*((0xAA >> b)&1)
            data[t >= 20.2, col(f'CELL_0_{b}')] = v
            data[t >= 40.2, col(f'REG_Q{b}')] = v
            data[(t >= 40.2)&(t < 47), b+1] = v
        return data, records, vectors, extra, SCENARIOS['r1_idle0'], dict(capture_inputs=[], capture_clocks=[]), 90

    def test_reference_fixture_and_no_expectation_on_unwritten_cells(self):
        args = self.fixture()
        checks, _, _ = analyze(*args)
        self.assertTrue(checks)
        self.assertFalse([c for c in checks if c['status'] == 'FAIL'])
        args[0][:, args[2].index(args[3]['CELL_3_7'])+1] = .8
        checks, _, _ = analyze(*args)
        self.assertFalse([c for c in checks if c['status'] == 'FAIL'])

    def test_missing_precharge_rejected(self):
        args = self.fixture(); args[0][:, args[2].index(args[3]['N0'])+1] = .5
        checks, _, _ = analyze(*args)
        self.assertIn(('decoder_precharged_before_first_access', 'FAIL'), [(c['kind'], c['status']) for c in checks])

    def test_initial_wordline_and_write_contention_rejected(self):
        args = self.fixture(); args[0][400:450, 13] = 1.8; args[0][400:450, 12] = 1.8
        checks, _, _ = analyze(*args)
        kinds = [c['kind'] for c in checks if c['status'] == 'FAIL']
        self.assertIn('startup_no_wordline', kinds)
        self.assertIn('startup_no_evaluation_write_sense', kinds)
        self.assertIn('write_precharge_nonoverlap', kinds)

    def test_incorrect_read_and_collateral_storage_error_rejected(self):
        args = self.fixture(); args[0][4200, 1] = 1.8
        args[0][6200, args[2].index(args[3]['CELL_0_0'])+1] = 1.8
        checks, _, _ = analyze(*args)
        kinds = [c['kind'] for c in checks if c['status'] == 'FAIL']
        self.assertIn('read_bus_bit', kinds)
        self.assertIn('known_storage_preserved', kinds)

    def test_bus_contention_during_conditioning_rejected(self):
        args = self.fixture(); args[0][350, 1:9] = 0
        checks, _, _ = analyze(*args)
        self.assertIn('startup_bus_release_1kohm', [c['kind'] for c in checks if c['status'] == 'FAIL'])

    def test_nonfinite_incomplete_and_empty_windows_rejected(self):
        args = self.fixture(); data, _, vectors, *_ = args
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            validate_trace(data[:-100], vectors, 90)
        data[1, 1] = np.nan
        with self.assertRaisesRegex(ValueError, 'Invalid'):
            validate_trace(data, vectors, 90)
        self.assertFalse(levels(np.array([]), 0))

    def test_existing_output_rejected_without_overwrite(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory(dir=root/'reports/phase2', prefix='startup-cli-test-') as d:
            target = Path(d)/'results.json'; original = '{"status":"HISTORICAL"}\n'; target.write_text(original)
            run = subprocess.run([sys.executable, str(root/'tools/run_phase2_startup_review.py'), '--output', d],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertIn('never overwritten', run.stderr)
            self.assertEqual(target.read_text(), original)


if __name__ == '__main__':
    unittest.main()
