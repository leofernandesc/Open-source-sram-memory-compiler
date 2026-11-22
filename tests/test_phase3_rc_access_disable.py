"""Unit regressions for the offline SS access and disable procedure."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from measure_phase3_access_disable import joint_release, measure_word, open_waveform
from phase3_rc_read_path import LOCAL_CLOCKS, OUTPUT_ENABLES, WORDLINES


def waveform(*, never_valid=False, late_glitch=False, host_active=False, wrong_row=False, stable_word=False):
    names = ['time', 'CLK', *(f'DATA{i}' for i in range(8)), *WORDLINES,
             *LOCAL_CLOCKS, *OUTPUT_ENABLES, 'v(HOST_EN)',
             *(f'_{43-i}_.A1' for i in range(8)), *(f'_{75+i}_.D' for i in range(8)),
             '_75_.Q', *(f'_{87+i}_.A' for i in range(1, 8))]
    columns = {name: i for i, name in enumerate(names)}
    expected = 0x81
    rows = []
    for ns in (0., .05, 1., 9.9, 10., 10.05, 10.10, 10.15, 10.2, 10.3, 10.4,
               10.5, 10.6, 10.7, 10.8, 10.9, 11., 11.15, 11.3, 11.5):
        row = {name: 0. for name in names}
        row.update(time=ns*1e-9, CLK=1.8 if .05 <= ns <= 10 else 0.)
        row[WORDLINES[int(wrong_row)]] = 1.8 if 1 <= ns <= 10 else 0.
        row['v(HOST_EN)'] = 1.8 if host_active and ns >= 10.6 else 0.
        for bit, clock in enumerate(LOCAL_CLOCKS):
            level = 1.8*((expected >> bit) & 1)
            row[f'_{43-bit}_.A1'] = level
            row[f'_{75+bit}_.D'] = level
            row[clock] = 1.8 if ns >= 10.15 else 0.
            row['_75_.Q' if bit == 0 else f'_{87+bit}_.A'] = level if stable_word or ns >= 10.3 else 0.
            near = 10.5 if bit == 7 else 10.4
            value = level if stable_word or ns >= near else 0.
            if bit == 7 and (never_valid or late_glitch and ns == 11.):
                value = 0.
            row[f'DATA{bit}'] = value
        rows.append(tuple(row[name] for name in names))
    record = dict(cycle=6, row=0, expected=expected, rise_ns=0., fall_ns=10.,
                  calibration={'weak_on_ns': 11.5})
    return rows, columns, record


class AccessDisableTests(unittest.TestCase):
    def test_access_uses_last_valid_bit_instead_of_its_data50(self):
        result = measure_word(*waveform())
        bit = result['bits'][7]
        self.assertEqual(result['status'], 'PROVISIONAL')
        self.assertEqual(result['word_verification'], 'VERIFIED')
        self.assertEqual(result['stable_word_since_s'], bit['data_valid_since_s'])
        self.assertGreater(result['tREAD_VALID_s'], bit['tCLK_TO_DATA_s'])
        self.assertAlmostEqual(result['tACCESS_s']*1e9, 10.455)
        self.assertIsNone(result['bits'][3]['tCLK_TO_DATA_s'])

    def test_late_glitch_restarts_the_shared_valid_interval(self):
        original = measure_word(*waveform())
        glitched = measure_word(*waveform(late_glitch=True))
        self.assertGreater(glitched['stable_word_since_s'], 11e-9)
        self.assertLess(glitched['stable_duration_s'], original['stable_duration_s'])
        self.assertIsNone(glitched['bits'][7]['tCLK_TO_DATA_s'])

    def test_missing_bit_wrong_row_and_host_drive_block_word_measurement(self):
        for change in ('never_valid', 'wrong_row', 'host_active'):
            with self.subTest(change=change):
                result = measure_word(*waveform(**{change: True}))
                self.assertEqual(result['status'], 'NOT_CHARACTERIZED')
                self.assertIsNone(result['tACCESS_s'])

    def test_identical_previous_word_verifies_levels_without_timing_a_transition(self):
        result = measure_word(*waveform(stable_word=True))
        self.assertEqual(result['word_verification'], 'VERIFIED')
        self.assertIsNone(result['tACCESS_s'])

    def test_tdis_requires_current_and_waits_for_voltage(self):
        mask = dict(status='PASS', weak_current_release_ps=101., weak_pull_valid_ps=130.)
        self.assertEqual(joint_release(mask), 130.)
        self.assertEqual(joint_release({**mask, 'weak_pull_valid_ps': None}), 101.)
        self.assertIsNone(joint_release({**mask, 'status': 'FAIL'}))
        self.assertIsNone(joint_release({**mask, 'weak_current_release_ps': None}))

    def test_pex_geometry_mismatch_blocks_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            pex, run = Path(tmp)/'pex', Path(tmp)/'run'
            pex.mkdir()
            run.mkdir()
            seal = dict(status='PASS_RC_STRUCTURE', profile='all', capacitance_audit={'different': 0},
                        geometry_receipt_sha256='proof', gds_sha256='candidate')
            (pex/'manifest.json').write_text(json.dumps(seal))
            (run/'manifest.json').write_text(json.dumps({'gds_sha256': 'other'}))
            with self.assertRaisesRegex(ValueError, 'Geometry'):
                open_waveform(pex, run, {'gds_sha256': 'candidate', 'physical_receipt_sha256': 'proof'}, (), {})


if __name__ == '__main__':
    unittest.main()
