"""An owner disposition cannot hide a failed audit or approve missing evidence."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import verify_phase1_handoff as handoff


class HandoffTests(unittest.TestCase):
    def decision(self):return json.loads(handoff.DECISION.read_text())

    def test_recorded_nonblocking_disposition_is_valid(self):
        handoff.validate_decision(self.decision())

    def test_nonblocking_does_not_mean_model_accuracy_established(self):
        decision=self.decision();decision['independent_off_state_model_accuracy']='ESTABLISHED'
        with self.assertRaisesRegex(ValueError,'limitation was erased'):handoff.validate_decision(decision)

    def test_local_experiment_is_not_an_approved_macro_contract(self):
        decision=self.decision();decision['local_reference_status']='APPROVED_MACRO_TIMING'
        with self.assertRaisesRegex(ValueError,'implicitly approved'):handoff.validate_decision(decision)

    def test_failed_artifact_audit_replaces_an_existing_pass_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary)/'audit.json';output.write_text('{"status":"PASS"}\n')
            with patch.object(sys,'argv',['verify','--output',str(output)]),patch.object(
                handoff.current,'check',side_effect=ValueError('corrupted selected artifact')),contextlib.redirect_stdout(io.StringIO()):
                result=handoff.main()
            self.assertEqual(result,1)
            receipt=json.loads(output.read_text());self.assertEqual(receipt['status'],'FAIL')
            self.assertIn('corrupted selected artifact',receipt['error'])

    def test_disposition_guards_survive_optimized_python(self):
        command=('import json,sys; sys.path.insert(0,sys.argv[1]); import verify_phase1_handoff as h; '
            'd=json.loads(h.DECISION.read_text()); d["independent_off_state_model_accuracy"]="ESTABLISHED"; '
            'h.validate_decision(d)')
        for mode in ([],['-O'],['-OO']):
            with self.subTest(mode=mode):
                process=subprocess.run([sys.executable,*mode,'-c',command,str(ROOT/'tools')],capture_output=True,text=True)
                self.assertNotEqual(process.returncode,0);self.assertIn('limitation was erased',process.stderr)


if __name__=='__main__':unittest.main()
