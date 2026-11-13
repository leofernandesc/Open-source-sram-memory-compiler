"""Independent revision regressions; no electrical simulation is started."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phase3 import functional, provenance
from phase3.runner import ROOT
from phase2_evidence import digest


class CLITests(unittest.TestCase):
    def test_entrypoint_exit_codes(self):
        cli = str(ROOT/'tools/run_phase3.py')
        for dry, status, performed, expected in (
            (True,'NOT_CHARACTERIZED',False,0), (False,'NOT_CHARACTERIZED',True,1),
            (False,'NOT_CHARACTERIZED',False,1), (True,'NOT_CHARACTERIZED',True,1),
            (False,'PASS',True,0), (False,'FAIL',True,1), (False,'ERROR',True,1),
            (True,'BLOCKED',False,1)):
            with self.subTest(dry=dry,status=status,performed=performed):
                result = dict(run_id='cli-test',status=status,electrical_simulation_performed=performed)
                # Run the real CLI main/argparse/SystemExit in a child Python process;
                # replace only its runner to prohibit any simulator invocation.
                code = ('import runpy,sys; from unittest.mock import patch; '
                        'sys.path.insert(0,'+repr(str(ROOT/'tools'))+'); '
                        'p=patch("phase3.runner.run",return_value='+repr(result)+'); p.start(); '
                        'runpy.run_path('+repr(cli)+',run_name="__main__")')
                command = [sys.executable,'-c',code,'--config','unused','--output','unused']
                if dry: command.append('--dry-run')
                proc = subprocess.run(command,capture_output=True,text=True,timeout=20)
                self.assertEqual(proc.returncode,expected,proc.stderr)
                self.assertEqual(json.loads(proc.stdout),result)


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        real = provenance.selected_inputs(ROOT)
        # Copy only the audited repository chain; do not edit original evidence.
        for name in real['inputs']:
            target=self.root/name; target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/name,target)
        self.approved = {p:(ROOT/p).read_bytes() for p in ('release/phase2_current.json',real['candidate'])}

    def audit(self):
        with patch.object(provenance.subprocess,'check_output',side_effect=lambda cmd:self.approved[cmd[-1].split(':',1)[1]]):
            return provenance.selected_inputs(self.root)

    def test_live_selected_chain(self):
        identity = self.audit()
        self.assertEqual(identity['qualification'],'reports/phase2/direct_abutment_20261111/qualification_v1/results.json')
        self.assertIn('physical/phase2_direct_abutment/candidate.json',identity['inputs'])

    def test_tampered_netlist_receipt_and_selector(self):
        for relative in ('reports/phase2/direct_abutment_20261111/qualification_v1/binding.spice',
                         'reports/phase2/direct_abutment_20261111/qualification_v1/results.json',
                         'reports/phase2/direct_abutment_20261111/fixture_v1/results.json',
                         'release/phase2_current.json','physical/phase2_direct_abutment/candidate.json'):
            with self.subTest(path=relative):
                p=self.root/relative; raw=p.read_bytes();p.write_bytes(raw+b'\n')
                with self.assertRaisesRegex(ValueError,'hash mismatch|differs from baseline'): self.audit()
                p.write_bytes(raw)

    def test_locally_consistent_forgery_still_rejected(self):
        # Updating both the local receipt and candidate hash cannot rewrite the baseline.
        candidate_path=self.root/'physical/phase2_direct_abutment/candidate.json'
        candidate=json.loads(candidate_path.read_text())
        proof=candidate['proof']['electrical']; receipt=self.root/proof['path']
        data=json.loads(receipt.read_text()); data['inputs'].pop(next(k for k in data['inputs'] if k.endswith('/fixture_v1/results.json')))
        receipt.write_text(json.dumps(data));proof['sha256']=digest(receipt)
        candidate_path.write_text(json.dumps(candidate))
        with self.assertRaisesRegex(ValueError,'differs from baseline'): self.audit()

    def test_identity_edge_not_just_individual_hashes(self):
        candidate_path=self.root/'physical/phase2_direct_abutment/candidate.json'
        candidate=json.loads(candidate_path.read_text());proof=candidate['proof']['electrical']
        receipt=self.root/proof['path'];data=json.loads(receipt.read_text())
        data['inputs'].pop(next(k for k in data['inputs'] if k.endswith('/fixture_v1/results.json')))
        receipt.write_text(json.dumps(data));proof['sha256']=digest(receipt)
        candidate_path.write_text(json.dumps(candidate))
        # Even a separately approved candidate needs a coherent extraction/fixture edge.
        self.approved['physical/phase2_direct_abutment/candidate.json']=candidate_path.read_bytes()
        with self.assertRaisesRegex(ValueError,'identity edge differs'): self.audit()


class FunctionalTests(unittest.TestCase):
    def test_three_independent_outcomes(self):
        for measurement, checks, expected in (
            ('PASS','NOT_CHARACTERIZED','NOT_CHARACTERIZED'),('PASS','PASS','PASS'),
            ('PASS','FAIL','FAIL'),('PASS','ERROR','ERROR'),
            ('NOT_CHARACTERIZED','PASS','NOT_CHARACTERIZED'),('FAIL','PASS','FAIL')):
            with self.subTest(measurement=measurement,checks=checks):
                self.assertEqual(functional.overall_status(measurement,checks,'sram'),expected)
        self.assertEqual(functional.overall_status('PASS','NOT_CHARACTERIZED','infrastructure_smoke'),'PASS')

    def test_existing_checker_is_called_with_fresh_waveform(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'work').mkdir()
            receipt=dict(vectors=['v(DATA0)'],cycles=[{'cycle':0}],probes={'a':'b'},stop_ns=370,campaign='bus',metrics=dict(checks_by_kind={'read_data':1},read_bit_checks=8))
            state=dict(capture_inputs=['x'],capture_clocks=['y'])
            (p/'receipt.json').write_text(json.dumps(receipt));(p/'fixture.json').write_text(json.dumps(state))
            raw=p/'work/waveform.dat';raw.write_text('time v(DATA0)\n0 0\n1e-9 1.8\n')
            context=dict(selection=dict(qualification='receipt.json',fixture='fixture.json'))
            checker=Mock(return_value=([dict(status='FAIL',kind='read_data')],None,dict(read_bit_checks=8)))
            with patch.dict(sys.modules,{'phase2_extension':types.SimpleNamespace(check=checker)}):
                result=functional.check_waveform(p,p/'work',context)
                self.assertEqual(result['status'],'FAIL')
                args=checker.call_args.args
                self.assertEqual(args[1:],(receipt['cycles'],receipt['vectors'],receipt['probes'],state,370,'bus'))
                self.assertEqual(args[0].shape,(2,2))
                checker.return_value=([],None,dict(read_bit_checks=8))
                with self.assertRaisesRegex(ValueError,'Empty/invalid'): functional.check_waveform(p,p/'work',context)
                checker.return_value=([dict(status='PASS',kind='read_data')],None,dict(read_bit_checks=0))
                with self.assertRaisesRegex(ValueError,'coverage differs'): functional.check_waveform(p,p/'work',context)
                raw.write_text('time wrong_column\n0 0\n')
                with self.assertRaisesRegex(ValueError,'header differs'): functional.check_waveform(p,p/'work',context)
                self.assertEqual(checker.call_count,3)

    def test_nominal_adapter_rejects_unreviewed_conditions(self):
        c=json.loads((ROOT/'characterization/phase3/smoke.json').read_text())
        self.assertIsNone(functional.prepare_context(ROOT,c))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'context.json';p.write_text(json.dumps(dict(adapter=functional.ADAPTER,baseline=c['baseline'])))
            c.update(functional.CONDITIONS); c['functional_validation']=dict(path=str(p),sha256=digest(p))
            c['corner']='ss'
            with self.assertRaisesRegex(ValueError,'nominal conditions only'): functional.prepare_context(ROOT,c)

if __name__=='__main__': unittest.main()
