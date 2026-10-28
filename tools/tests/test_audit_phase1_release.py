"""Exercise the real release audit in normal, -O and -OO subprocesses.

All mutations and generated failure reports are confined to temporary copies.
These tests prevent optimized Python from accepting invalid release evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT=Path(__file__).resolve().parents[2]
BOOTSTRAP='''
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import audit_phase1_release as audit
audit.ROOT=Path(sys.argv[2])
audit.DEST=audit.ROOT/'release/phase1'
raise SystemExit(audit.cli())
'''


class ReleaseAuditRegressionTests(unittest.TestCase):
    def setUp(self):
        self.scratch=tempfile.TemporaryDirectory(prefix='phase1-audit-regression-')
        self.addCleanup(self.scratch.cleanup)
        self.root=Path(self.scratch.name)
        self.release=self.root/'release/phase1'
        shutil.copytree(ROOT/'release/phase1',self.release)
        (self.root/'tools').mkdir()
        for name in ('prepare_phase1_release.py','verify_phase1_physical.py',
                     'verify_phase1_g7_support.py','audit_phase1_release.py'):
            shutil.copy2(ROOT/'tools'/name,self.root/'tools'/name)

    def change_json(self,path,change):
        target=self.release/path
        data=json.loads(target.read_text())
        change(data)
        target.write_text(json.dumps(data,indent=2)+'\n')

    def run_audit(self,flag):
        return subprocess.run([sys.executable,*([flag] if flag else []),
            '-c',BOOTSTRAP,str(ROOT/'tools'),str(self.root)],cwd=ROOT,
            capture_output=True,text=True,timeout=60)

    def expect_rejection(self,diagnostic):
        checksum_bytes=(self.release/'checksums.json').read_bytes()
        for flag in ('','-O','-OO'):
            with self.subTest(python_mode=flag or 'normal'):
                result=self.run_audit(flag)
                self.assertNotEqual(result.returncode,0,result.stdout)
                self.assertNotIn('PASS:',result.stdout)
                self.assertIn('FAIL:',result.stderr)
                self.assertIn(diagnostic,result.stderr)
                report=json.loads((self.release/'verification/release_audit.json').read_text())
                self.assertEqual(report['status'],'FAIL')
                self.assertEqual((self.release/'checksums.json').read_bytes(),checksum_bytes)

    def test_valid_release_passes_in_all_modes(self):
        for flag in ('','-O','-OO'):
            with self.subTest(python_mode=flag or 'normal'):
                result=self.run_audit(flag)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn('PASS: 6 cells',result.stdout)
                report=json.loads((self.release/'verification/release_audit.json').read_text())
                self.assertEqual(report['status'],'PASS')

    def test_failed_summary_replaces_previous_pass(self):
        self.change_json('verification/summary.json',lambda d:d.update(status='FAIL'))
        self.expect_rejection('Physical summary')

    def test_incomplete_summary_is_rejected(self):
        self.change_json('verification/summary.json',lambda d:d['cells'].pop())
        self.expect_rejection('Physical summary')

    def test_corrupted_canonical_schematic_is_rejected(self):
        with (self.release/'cells/row_decoder/row_decoder.sch').open('a') as handle:
            handle.write('\n* intentional regression-test corruption\n')
        self.expect_rejection('cells/row_decoder/row_decoder.sch')

    def test_failed_cell_result_is_rejected(self):
        self.change_json('verification/row_decoder/result.json',lambda d:d.update(status='FAIL'))
        self.expect_rejection('physical status is not PASS')

    def test_missing_negative_control_is_rejected(self):
        self.change_json('verification/row_decoder/result.json',lambda d:d['negative_controls'].pop('width'))
        self.expect_rejection('negative controls')

    def test_missing_lvs_evidence_is_rejected(self):
        (self.release/'verification/row_decoder/lvs_report.txt').unlink()
        self.expect_rejection('lvs_report.txt')

    def test_stale_verification_script_is_rejected(self):
        self.change_json('verification/summary.json',lambda d:d['scripts_sha256'].update(
            {'audit_phase1_release.py':'0'*64}))
        self.expect_rejection('audit_phase1_release.py')

    def test_failed_g7_column_is_rejected(self):
        self.change_json('support/g7_column/result.json',lambda d:d.update(status='FAIL'))
        self.expect_rejection('Supporting G7')

    def test_corrupted_electrical_csv_is_rejected(self):
        target=self.release/'electrical/g7_read_requal_latch_t0_20261008.csv'
        target.write_text(target.read_text().replace('PASS','FAIL',1))
        self.expect_rejection('electrical CSV hash mismatch')


if __name__=='__main__':
    unittest.main()
