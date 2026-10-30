"""Reject inconsistent retained evidence using temporary copies of real cases."""
import contextlib
import csv
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest


SCRIPT=Path(__file__).parent/'results/canonical_timing_review_20261028/inspect_evidence.py'
NAME='canonical_timing_frontend_pilot_20261028'


class EvidenceInspectionTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('evidence_inspection',SCRIPT)
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.temporary=tempfile.TemporaryDirectory(prefix='.timing-inspection-test-',dir=SCRIPT.parent.parent)
        self.addCleanup(self.temporary.cleanup)
        root=Path(self.temporary.name)
        shutil.copytree(SCRIPT.parent.parent/NAME,root/NAME)
        self.module.RESULTS=root;self.module.HERE=root/'review';self.module.HERE.mkdir()
        self.module.CAMPAIGNS={NAME:self.module.CAMPAIGNS[NAME]}
        self.directory=root/NAME
        self.manifest=json.loads((self.directory/'manifest.json').read_text())
        self.case=self.directory/self.manifest['cases'][0]['case']

    def inspect(self):
        with contextlib.redirect_stdout(io.StringIO()):self.module.inspect()

    def csv_change(self,name,column,value):
        path=self.case/name
        with path.open() as handle:
            reader=csv.DictReader(handle);fields=reader.fieldnames;rows=list(reader)
        rows[0][column]=value
        with path.open('w',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(rows)

    def test_valid_negative_boundary_data_is_accepted_as_evidence(self):
        self.inspect()
        report=json.loads((self.module.HERE/'evidence_audit.json').read_text())
        self.assertEqual(report['status'],'PASS_EVIDENCE_INTEGRITY')
        self.assertEqual(report['timing_fail'],2)

    def test_forged_threshold_status_is_rejected(self):
        self.csv_change('checks.csv','status','FAIL')
        with self.assertRaisesRegex(ValueError,'inconsistent check status'):self.inspect()

    def test_forged_logic_pass_is_rejected(self):
        self.manifest['cases'][0]['timing_screen']='PASS'
        (self.case/'result.json').write_text(json.dumps(self.manifest['cases'][0]))
        (self.directory/'manifest.json').write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError,'incorrect timing conclusion'):self.inspect()

    def test_missing_coverage_is_rejected(self):
        self.manifest['cases'].pop()
        (self.directory/'manifest.json').write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError,'wrong case coverage'):self.inspect()

    def test_changed_runner_snapshot_is_rejected(self):
        path=self.directory/'executed_script.py';path.write_text(path.read_text()+'\n# changed\n')
        with self.assertRaisesRegex(ValueError,'changed runner snapshot'):self.inspect()

    def test_forged_bias_magnitude_is_rejected(self):
        self.csv_change('bias_extrema.csv','abs_max_v','100')
        with self.assertRaisesRegex(ValueError,'inconsistent bias magnitude'):self.inspect()

    def test_incomplete_campaign_is_rejected(self):
        self.manifest['complete']=False
        (self.directory/'manifest.json').write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError,'incomplete'):self.inspect()


if __name__=='__main__':unittest.main()
