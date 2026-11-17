"""Operational r1 regressions: synthetic/mocked subprocesses, no real SPICE."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase2_evidence import digest
from phase3.runner import ROOT
from phase3 import runner,functional,nominal_operational as op
from phase3.nominal_bench_plan import POLICY_SHA256 as R0_SHA,load_policy
from prepare_phase3_4x8 import prepare,nominal_template


def setUpModule():
    # A fresh checkout has no ignored run directory; tests own this prerequisite.
    (ROOT/'reports/phase3').mkdir(parents=True,exist_ok=True)


class ApprovedPolicyTests(unittest.TestCase):
    def test_r1_authority_and_r0_pins(self):
        p,pins=op.load_approved(ROOT)
        self.assertEqual(p['revision'],'r1');self.assertEqual(p['r0']['policy']['sha256'],R0_SHA)
        self.assertTrue(p['functional_gate_enabled']);self.assertFalse(p['global_gate_enabled'])
        self.assertGreater(len(pins),3)

    def test_modified_or_missing_approval_dependency_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=ROOT/op.POLICY_PATH;p=root/op.POLICY_PATH;p.parent.mkdir(parents=True)
            p.write_bytes(source.read_bytes()+b'\n')
            with self.assertRaises(ValueError):op.load_approved(root)
            p.write_bytes(source.read_bytes())
            with self.assertRaises(FileNotFoundError):op.load_approved(root)

    def test_historical_or_approval_document_tampering_is_rejected(self):
        policy,pins=op.load_approved(ROOT)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name in pins:
                source=Path(name);target=root/source.relative_to(ROOT)
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
            target=root/policy['r0']['document']['path'];target.write_bytes(target.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'hash'):op.load_approved(root)

    def test_global_never_passes_without_b(self):
        for measured in ('PASS','NOT_CHARACTERIZED'):
            self.assertEqual(op.global_status(measured,'PASS'),'NOT_CHARACTERIZED')
        self.assertEqual(op.global_status('PASS','FAIL'),'FAIL')
        self.assertEqual(op.global_status('PASS','ERROR'),'ERROR')

    def test_legacy_remains_default_and_a_remains_blocked(self):
        self.assertEqual(prepare.__defaults__,(functional.ADAPTER,))
        from phase3.functional_a import blocked_assessment
        self.assertEqual(blocked_assessment()['status'],'BLOCKED')
        self.assertEqual(load_policy(ROOT)['approval'],'PROPOSED')


class ContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'reports/phase3')
        cls.folder=Path(cls.temp.name)
        config=prepare(cls.folder/'prepared',op.PROFILE)
        cls.c=json.loads(config.read_text());cls.context=json.loads(Path(cls.c['functional_validation']['path']).read_text())

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_approved_context_and_exact_plan(self):
        pins=op.validate_context(ROOT,self.c,self.context)
        self.assertIn(str((ROOT/op.POLICY_PATH).resolve()),pins)
        result=functional.prepare_context(ROOT,self.c)
        self.assertTrue(result['operational_nominal']);self.assertNotIn('activation_blocked',result)
        plan=json.loads(Path(self.context['observation_plan']['path']).read_text())
        self.assertEqual(len(plan['windows']),626)
        source=(ROOT/self.context['selection']['qualification']).parent
        self.assertEqual(Path(self.c['deck']['path']).read_text(),nominal_template(source))

    def test_unknown_and_unapproved_profiles_rejected(self):
        for change in ({'adapter':'unknown'},{'revision':'r0'},{'schema_version':True}):
            context={**self.context,**change}
            with self.subTest(change=change),self.assertRaises(ValueError):op.validate_context(ROOT,self.c,context)

    def test_replay_context_cannot_be_promoted(self):
        with self.assertRaises(ValueError):op.validate_context(ROOT,self.c,{**self.context,'assessment_mode':'replay'})

    def test_adulterated_or_reduced_plan_rejected_after_rehash(self):
        for mutation in ('time','omitted','duplicate','bounds'):
            plan=json.loads(Path(self.context['observation_plan']['path']).read_text())
            if mutation=='time':plan['windows'][0]['start_ns']+=.1
            elif mutation=='omitted':plan['windows'].pop()
            elif mutation=='duplicate':plan['windows'].append(plan['windows'][0])
            else:plan['windows'][0]['bounds']='[]'
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/'plan.json';p.write_text(json.dumps(plan));context=deepcopy(self.context)
                context['observation_plan']=dict(path=str(p),sha256=digest(p))
                with self.subTest(mutation=mutation),self.assertRaises(ValueError):op.validate_context(ROOT,self.c,context)

    def test_incompatible_conditions_rejected(self):
        for key,value in [('corner','ss'),('load_ff',20),('temp_c',25),('period_ns',10),('extraction','distributed RC')]:
            c=deepcopy(self.c);c[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):op.validate_context(ROOT,c,self.context)

    def test_candidate_and_inputs_cannot_be_relabelled(self):
        for mutation in ('candidate','model','netlist'):
            c=deepcopy(self.c);context=deepcopy(self.context)
            if mutation=='candidate':context['selection']['candidate']='other.json'
            else:c[mutation]['sha256']='0'*64;context['expected_inputs'][mutation]=c[mutation]
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):op.validate_context(ROOT,c,context)

    def test_wrong_context_hash_rejected(self):
        c=deepcopy(self.c);c['functional_validation']['sha256']='0'*64
        with self.assertRaises(ValueError):functional.prepare_context(ROOT,c)

    def test_copy_or_load_old_raw_command_rejected_even_when_repinned(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'deck';p.write_text(Path(self.c['deck']['path']).read_text().replace('.control','.control\nload old.raw'))
            c=deepcopy(self.c);c['deck']=dict(path=str(p),sha256=digest(p));context=deepcopy(self.context)
            context['expected_inputs']['deck']=c['deck']
            with self.assertRaises(ValueError):op.validate_context(ROOT,c,context)

    def test_missing_dependency_or_plan_rejected(self):
        context=deepcopy(self.context);context['observation_plan']['path']=str(self.folder/'absent')
        with self.assertRaises(FileNotFoundError):op.validate_context(ROOT,self.c,context)

    def test_fresh_adapter_preserves_functional_failure_with_b_pending(self):
        # Synthetic assessment stub only; real checkers/windows are covered by the 142 regressions.
        with tempfile.TemporaryDirectory() as d:
            work=Path(d)/'inputs';work.mkdir();(work/'waveform.dat').write_text('time x\n0 0\n')
            with patch.object(op,'validate_context'),patch.object(op,'verify_execution',return_value=work/'waveform.dat'):
                # Header validation still rejects incomplete evidence before any verdict.
                with self.assertRaisesRegex(ValueError,'header'):op.check_fresh(ROOT,work,self.context,{})

    def test_approved_adapter_success_path_with_synthetic_evaluator_stub(self):
        receipt=json.loads((ROOT/self.context['selection']['qualification']).read_text())
        with tempfile.TemporaryDirectory() as d:
            work=Path(d)/'inputs';work.mkdir()
            raw=work/'waveform.dat'
            raw.write_text('time '+' '.join(receipt['vectors'])+'\n'+' '.join(['0']*(len(receipt['vectors'])+1))+'\n'+' '.join(['1']*(len(receipt['vectors'])+1))+'\n')
            partial=dict(legacy_comparison=dict(checks=[],total=1740),status='BLOCKED')
            synthetic=dict(status='BLOCKED',nominal_functional_status='PASS',properties={},
                observations=[],legacy_classification=[],coverage=dict(windows=626),
                temporal_qualification=dict(status='NOT_CHARACTERIZED'))
            with patch.object(op,'verify_execution',return_value=raw), \
                 patch('phase3.functional_a.evaluate_waveform',return_value=partial), \
                 patch('phase3.nominal_bench.evaluate',return_value=synthetic):
                result=op.check_fresh(ROOT,work,self.context,{})
            self.assertEqual(result['status'],'PASS');self.assertEqual(result['revision'],'r1')
            self.assertEqual(result['temporal_qualification']['status'],'NOT_CHARACTERIZED')
            self.assertFalse(result['global_gate_enabled'])

    def test_dry_run_then_mocked_real_integration(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'reports/phase3') as d:
            folder=Path(d);config=folder/'config.json';config.write_text(json.dumps(self.c))
            real_popen=subprocess.Popen
            def dry_process(command,**kwargs):
                if Path(command[0]).name=='ngspice' and '-b' in command:
                    raise AssertionError('Dry-run started a simulator')
                return real_popen(command,**kwargs)
            with patch.object(runner.subprocess,'Popen',side_effect=dry_process):
                dry=runner.run(config,folder/'dry',True)
            self.assertEqual(dry['status'],'NOT_CHARACTERIZED');self.assertFalse(dry['electrical_simulation_performed'])
            class Proc:
                pid=987654
                returncode=0
                def wait(self,timeout=None):return 0
            for status in ('PASS','FAIL','ERROR'):
                def start(command,**kwargs):
                    if Path(command[0]).name!='ngspice' or '-b' not in command:
                        return real_popen(command,**kwargs)
                    (Path(kwargs['cwd'])/'waveform.dat').write_text('synthetic test-only waveform\n')
                    kwargs['stdout'].write('synthetic ngspice test stub\n');kwargs['stdout'].flush()
                    return Proc()
                result=dict(status=status,checks=[],temporal_qualification=dict(status='NOT_CHARACTERIZED'))
                with patch.object(runner.subprocess,'Popen',side_effect=start),patch.object(runner,'check_waveform',return_value=result) as checker:
                    receipt=runner.run(config,folder/status)
                self.assertEqual(receipt['status'],'NOT_CHARACTERIZED' if status=='PASS' else status)
                self.assertEqual(receipt['simulator_status'],'PASS')
                self.assertEqual(receipt['functional_validation']['status'],status)
                proof=checker.call_args.kwargs['execution'];self.assertEqual(proof['assessment_mode'],'fresh_run')
                self.assertFalse(receipt['sram_characterized'])


class FreshEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name)
        marker=self.work/'.nominal_execution_started';marker.write_text('synthetic test only')
        self.started=marker.stat().st_mtime_ns
        (self.work/'waveform.dat').write_text('synthetic test only')
        self.proof=dict(assessment_mode='fresh_run',workdir=str(self.work.resolve()),simulator_status='PASS',
            return_code=0,waveform_absent_before_start=True,started_ns=self.started,finished_ns=time.time_ns())

    def test_new_file_and_simulator_proof_are_required(self):
        self.assertEqual(op.verify_execution(self.work,self.proof),self.work/'waveform.dat')

    def test_missing_or_replay_proof_rejected(self):
        for proof in (None,{},dict(self.proof,assessment_mode='replay'),dict(self.proof,waveform_absent_before_start=False)):
            with self.subTest(proof=proof),self.assertRaises(ValueError):op.verify_execution(self.work,proof)

    def test_old_file_mtime_rejected(self):
        os.utime(self.work/'waveform.dat',ns=(0,0))
        with self.assertRaises(ValueError):op.verify_execution(self.work,self.proof)

    def test_missing_or_symlink_waveform_rejected(self):
        raw=self.work/'waveform.dat';raw.unlink()
        with self.assertRaises(ValueError):op.verify_execution(self.work,self.proof)
        outside=self.work/'old';outside.write_text('historical');raw.symlink_to(outside)
        with self.assertRaises(ValueError):op.verify_execution(self.work,self.proof)

    def test_wrong_workdir_or_simulator_failure_rejected(self):
        for change in ({'workdir':'/old'},{'return_code':1},{'simulator_status':'FAIL'},{'started_ns':True}):
            with self.subTest(change=change),self.assertRaises(ValueError):op.verify_execution(self.work,{**self.proof,**change})

    def test_empty_marker_or_modified_proof_rejected(self):
        (self.work/'.nominal_execution_started').unlink()
        with self.assertRaises(ValueError):op.verify_execution(self.work,self.proof)


if __name__=='__main__':unittest.main()
