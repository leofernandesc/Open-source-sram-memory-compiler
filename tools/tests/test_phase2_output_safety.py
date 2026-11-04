"""Reject output/input collisions before touching an existing report."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]


class ReportOutputSafetyTests(unittest.TestCase):
    def test_real_entrypoints_preserve_input_receipt_on_rejected_output(self):
        parent=ROOT/'reports/phase2/local';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='output-safety-',dir=parent) as d:
            report=Path(d)/'results.json';report.write_text('{"status":"SENTINEL_EXISTING_EVIDENCE"}\n')
            before=hashlib.sha256(report.read_bytes()).hexdigest()
            for script,flag in [('run_phase2_place.py','--fabric-report'),('finish_phase2_layout.py','--route-report'),
                                ('verify_phase2_gds.py','--layout-report'),('run_phase2_routed_gls.py','--layout-report')]:
                with self.subTest(script=script):
                    run=subprocess.run([sys.executable,str(ROOT/'tools'/script),flag,d,'--output',d],capture_output=True,text=True,timeout=30)
                    self.assertEqual(run.returncode,2,run.stdout+run.stderr)
                    self.assertIn('Output cannot replace',run.stderr)
                    self.assertEqual(hashlib.sha256(report.read_bytes()).hexdigest(),before)


if __name__=='__main__':unittest.main()
