"""Synthetic observer/policy tests only. No SPICE or electrical qualification."""
from copy import deepcopy
from collections import Counter
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch, Mock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase2_evidence import digest
from phase2_extension import check
from phase3 import functional, functional_a as a, runner
from phase3.functional_a_coverage import compare, map_checks, legacy_identity, verify_inventory, MATRIX
from phase3.functional_a_observers import interval, retention
from phase3.contract import FIELDS
from phase3.provenance import selected_inputs
import test_phase2_extension as extension_fixtures

ROOT = runner.ROOT


def synthetic():
    return extension_fixtures.ExtensionObserverTests().fixture(True)


def assess_fixture(args, template):
    d, records, vectors, probes, state, stop, name = args
    checks, _, _ = check(*args)
    observations = retention(d, records, vectors, probes, state, stop)
    return a.assess(checks, template, records, observations)


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.c = json.loads((ROOT/'characterization/phase3/smoke.json').read_text())
        selection=dict(baseline='baseline',candidate='candidate.json',qualification='results.json',
                       fixture='fixture.json',gds='sram.gds',gds_sha256='0'*64,inputs={'candidate.json':'0'*64})
        self.context = a.context_for('baseline', selection, {k:self.c[k] for k in ('deck','netlist','model')})

    def test_profile_version_and_fields(self):
        self.assertEqual(a.validate_context(self.context)['adapter'], a.ADAPTER)
        for key,value in [('schema_version',2),('schema_version',True),('adapter','typo'),('extra',1)]:
            c=deepcopy(self.context);c[key]=value
            with self.subTest(key=key,value=value), self.assertRaises(ValueError): a.validate_context(c)

    def test_missing_decision_cannot_approve(self):
        for decision in a.DECISIONS:
            c=deepcopy(self.context);del c['decisions'][decision]
            with self.subTest(decision=decision),self.assertRaises(ValueError): a.validate_context(c)

    def test_fake_approval_and_gate_activation_rejected(self):
        for key,value in [('decisions',{d:'APPROVED' for d in a.DECISIONS}),('gate_enabled',True),('gate_enabled',0)]:
            c=deepcopy(self.context);c[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError): a.validate_context(c)

    def test_external_or_observed_data_window_rejected(self):
        for reference in ('settle(DATA)', 'Q_valid', 'stimulus'):
            c=deepcopy(self.context);c['observation_windows']=[dict(reference=reference,start_ns=1,end_ns=2)]
            with self.subTest(reference=reference),self.assertRaises(ValueError): a.validate_context(c)

    def test_input_pins_are_strict(self):
        for pin in ({'path':'x','sha256':'bad'}, {'path':'','sha256':'0'*64}, {'path':'x','sha256':'0'*64,'extra':1}):
            c=deepcopy(self.context);c['expected_inputs']['deck']=pin
            with self.subTest(pin=pin),self.assertRaises(ValueError): a.validate_context(c)

    def test_all_a_properties_have_requirement_sources(self):
        self.assertEqual(set(MATRIX),{f'A{i:02}' for i in range(1,13)})
        self.assertTrue(all(source for source,pending in MATRIX.values()))

    def test_inconsistent_known_read_rejected(self):
        records=synthetic()[1];records[1]['expected']=0x55
        with self.assertRaisesRegex(ValueError,'stimulus write'): a.validate_records(records)

    def test_duplicate_empty_and_nonfinite_stimulus_rejected(self):
        records=synthetic()[1]
        for mutation in ('duplicate','empty','nan'):
            r=deepcopy(records)
            if mutation=='duplicate':r[1]['cycle']=0
            elif mutation=='empty':r=[]
            else:r[1]['sample_ns']=float('nan')
            with self.subTest(mutation=mutation),self.assertRaises(ValueError): a.validate_records(r)


class IntervalTests(unittest.TestCase):
    def setUp(self):
        self.t=np.linspace(0,10,1001)
        self.v=np.ones(1001)*1.8
        self.w=dict(reference='test_fixture',start_ns=2,end_ns=8)

    def test_valid_all_patterns_bits_and_directions(self):
        for word in [0,255,0xAA,0x55,*[1<<b for b in range(8)],*[255^(1<<b) for b in range(8)]]:
            for bit in range(8):
                expected=(word>>bit)&1
                self.assertEqual(interval(self.t,np.full(len(self.t),1.8*expected),expected,self.w)['status'],'PASS')

    def test_temporary_q_corruption_detected(self):
        self.v[411:413]=0
        result=interval(self.t,self.v,1,self.w)
        self.assertEqual(result['status'],'FAIL');self.assertEqual(result['first_bad_ns'],4.11)

    def test_glitch_between_readback_points_detected(self):
        self.v[501]=.9
        self.assertEqual(interval(self.t,self.v,1,self.w)['status'],'FAIL')

    def test_only_instantaneous_validity_is_not_stability(self):
        self.v[:]=.9;self.v[500]=1.8
        self.assertEqual(interval(self.t,self.v,1,self.w)['status'],'FAIL')

    def test_boundaries_are_fixed_not_fitted_to_trace(self):
        for index in (200,799):
            v=self.v.copy();v[index]=0
            self.assertEqual(interval(self.t,v,1,self.w)['status'],'FAIL')
        self.assertEqual(self.w,dict(reference='test_fixture',start_ns=2,end_ns=8))

    def test_empty_window_rejected(self):
        for lo,hi in ((2,2),(8,2),(2.0001,2.0002)):
            w=dict(self.w,start_ns=lo,end_ns=hi)
            with self.subTest(lo=lo,hi=hi),self.assertRaises(ValueError): interval(self.t,self.v,1,w)

    def test_incomplete_and_nonfinite_evidence_rejected(self):
        with self.assertRaises(ValueError):interval(self.t[:500],self.v[:500],1,self.w)
        self.v[10]=np.nan
        with self.assertRaises(ValueError):interval(self.t,self.v,1,self.w)

    def test_data_dependent_references_rejected(self):
        for reference in ('DATA50','settle(DATA)','first_valid_Q'):
            with self.subTest(reference=reference),self.assertRaises(ValueError):
                interval(self.t,self.v,1,dict(self.w,reference=reference))


class AssessmentTests(unittest.TestCase):
    def setUp(self):
        self.args=synthetic()
        self.template=deepcopy(check(*self.args)[0])

    def test_correct_partial_stays_blocked_and_retains_pin_observations(self):
        r=assess_fixture(self.args,self.template)
        self.assertEqual(r['status'],'BLOCKED')
        self.assertEqual(r['legacy_comparison']['counts'],{'PASS':len(self.template)})
        self.assertEqual(r['properties']['A12']['status'],'PASS')
        self.assertEqual(r['properties']['A08']['status'],'BLOCKED')
        self.assertEqual(r['properties']['A09']['pending_opportunities'],8)
        self.assertEqual(r['temporal_qualification']['status'],'NOT_CHARACTERIZED')

    def test_q_corruption_during_idle_between_legacy_points_fails(self):
        d,r,v,p,s,stop,name=self.args
        d[7000:7002,v.index(p['REG_Q0'])+1]=1.8
        result=assess_fixture(self.args,self.template)
        self.assertEqual(result['status'],'FAIL')
        self.assertEqual(result['properties']['A04']['status'],'FAIL')

    def test_wrong_edge_update_cannot_hide_in_pending_decisions(self):
        d,r,v,p,s,stop,name=self.args
        # A second read's output clock is high at the next public rising edge;
        # Q changing there must be caught before the actual local capture.
        r.append(dict(cycle=3,operation='read',row=0,expected=0xAA,rise_ns=70,fall_ns=80,sample_ns=82))
        for b in range(8):
            clock=f'v(local_clock{b})';v.append(clock);s['capture_clocks'].append(clock)
            d=np.column_stack((d,np.where(d[:,0]*1e9>=80.25,1.8,0)))
        d[(d[:,0]*1e9>=70.25)&(d[:,0]*1e9<80.25),v.index(p['REG_Q0'])+1]=1.8
        o=retention(d,r,v,p,s,stop)
        self.assertTrue(any(x['status']=='FAIL' and x['cycle']==1 for x in o))

    def capture_fixture(self):
        args=list(self.args);d,r,v,p,s,stop,name=args
        t=d[:,0]*1e9
        for bit in range(8):
            data_name=f'v(synthetic_ff_d{bit})';clock_name=f'v(synthetic_capture{bit})'
            v.extend([data_name,clock_name]);s['capture_inputs'].append(data_name);s['capture_clocks'].append(clock_name)
            d=np.column_stack((d,np.full(len(t),1.8*((0xAA>>bit)&1)),np.where(t>=40.25,1.8,0)))
        args[0]=d
        reference=dict(path='synthetic-test.lib',sha256='0'*64,
                       setup={'D':(None,None,np.array([[.6]]))},hold={'D':(None,None,np.array([[.1]]))})
        return args,types.SimpleNamespace(liberty_constraints=lambda corner:reference)

    def test_internal_setup_hold_violation_fails_without_public_timing_claim(self):
        args,library=self.capture_fixture()
        with patch.dict(sys.modules,{'run_row_address_setup_hold':library}):
            template=deepcopy(check(*args)[0]);t=args[0][:,0]*1e9
            args[0][(t>=40.1)&(t<=40.12),args[2].index(args[4]['capture_inputs'][0])+1]=1.8
            result=assess_fixture(args,template)
        self.assertEqual(result['properties']['A03']['status'],'FAIL')
        self.assertIn('O4',result['properties']['A03']['pending_decisions'])

    def test_missing_local_capture_is_fail_not_a_dropped_opportunity(self):
        args,library=self.capture_fixture()
        with patch.dict(sys.modules,{'run_row_address_setup_hold':library}):
            template=deepcopy(check(*args)[0]);metrics=dict(checks_by_kind=dict(Counter(c['kind'] for c in template)),read_bit_checks=8)
            args[0][:,args[2].index(args[4]['capture_clocks'][0])+1]=0
            receipt=dict(cycles=args[1],vectors=args[2],probes=args[3],stop_ns=args[5],campaign=args[6],metrics=metrics)
            result=a.evaluate_waveform(args[0],receipt,args[4],template)
        self.assertEqual(result['status'],'FAIL')
        self.assertEqual(result['properties']['A03']['status'],'FAIL')

    def test_wrong_address_and_captured_write_data_fail(self):
        d,r,v,p,*_=self.args
        d[:,v.index(p['ADDR_Q0'])+1]=1.8;d[:,v.index(p['DIN_Q0'])+1]=1.8
        result=assess_fixture(self.args,self.template)
        self.assertEqual(result['properties']['A01']['status'],'FAIL')
        self.assertEqual(result['properties']['A02']['status'],'FAIL')

    def test_data_wrong_despite_q_correct_fails_observation(self):
        self.args[0][4200,1]=1.8
        result=assess_fixture(self.args,self.template)
        self.assertEqual(result['properties']['A08']['status'],'FAIL')
        self.assertEqual(result['properties']['A03']['observation_status'],'PASS')

    def test_driver_active_when_masked_fails(self):
        d,r,v,p,*_=self.args;t=d[:,0]*1e9
        d[(t>=43.2)&(t<=43.8),v.index(p['I_WEAK0'])+1]=100e-6
        self.assertEqual(assess_fixture(self.args,self.template)['properties']['A06']['status'],'FAIL')

    def test_floating_correct_voltage_does_not_prove_drive(self):
        d,r,v,p,*_=self.args;d[:,v.index(p['I_WEAK0'])+1]=0
        self.assertEqual(assess_fixture(self.args,self.template)['properties']['A06']['status'],'FAIL')

    def test_contention_even_equal_data_is_detected(self):
        d,r,v,p,*_=self.args
        d[900:950,v.index(p['HOST_EN'])+1]=1.8;d[900:950,v.index(p['TE_B0'])+1]=0
        self.assertEqual(assess_fixture(self.args,self.template)['properties']['A07']['status'],'FAIL')

    def test_unknown_kind_blocks_complete_mapping(self):
        c=deepcopy(self.template);c[0]['kind']='unmapped'
        with self.assertRaises(ValueError): compare(c,c,self.args[1])

    def test_duplicate_check_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicated'):
            compare(self.template+[self.template[0]],self.template,self.args[1])

    def test_missing_check_rejected(self):
        with self.assertRaisesRegex(ValueError,'Coverage'):
            compare(self.template[:-1],self.template,self.args[1])

    def test_equal_counts_cannot_replace_missing_identity(self):
        c=deepcopy(self.template);next(x for x in c if x.get('bit')==0)['bit']=8
        with self.assertRaises(ValueError):compare(c,self.template,self.args[1])

    def test_missing_internal_retention_inventory_rejected(self):
        with self.assertRaises(ValueError):a.assess(self.template,self.template,self.args[1])

    def test_retention_observation_duplicates_rejected(self):
        d,r,v,p,s,stop,_=self.args;o=retention(d,r,v,p,s,stop)
        with self.assertRaises(ValueError):a.assess(self.template,self.template,r,o+[o[0]])

    def test_no_legacy_status_is_rewritten(self):
        c=deepcopy(self.template)
        # Introduce the legacy observation kind with a resumed-read context.
        extra=dict(kind='previous_data_visible_before_new_capture',cycle=1,bit=0,status='FAIL')
        c.append(extra);original=deepcopy(c)
        comp=compare(c,c,self.args[1])
        self.assertEqual(c,original);self.assertEqual(comp['legacy_status'],'FAIL')
        self.assertEqual(comp['mapping'][-1]['property'],'A10')
        self.assertEqual(comp['mapping'][-1]['normative_disposition'],'PENDING')
        d,r,v,p,s,stop,_=self.args
        assessed=a.assess(c,c,r,retention(d,r,v,p,s,stop))
        self.assertEqual(assessed['properties']['A10']['pending_legacy_status_counts']['FAIL'],1)
        self.assertEqual(assessed['legacy_comparison']['counts']['FAIL'],1)
        self.assertEqual(assessed['status'],'BLOCKED')

    def test_read_read_and_resume_have_distinct_mapping(self):
        records=deepcopy(self.args[1]);records[2]['operation']='read'
        c=[dict(kind='previous_data_visible_before_new_capture',cycle=1,bit=0,status='FAIL'),
           dict(kind='previous_data_visible_before_new_capture',cycle=2,bit=0,status='FAIL')]
        mapped=map_checks(c,records)
        self.assertEqual([m['property'] for m in mapped],['A10','A05'])

    def test_capture_edge_failure_preserves_opportunity(self):
        reference=[dict(kind='output_ff_setup_hold_envelope',cycle=1,bit=0,status='PASS')]
        failed=[dict(kind='local_capture_edge',cycle=1,bit=0,status='FAIL',edges=0)]
        result=compare(failed,reference,self.args[1])
        self.assertTrue(result['coverage_complete']);self.assertEqual(result['legacy_status'],'FAIL')

    def test_incomplete_waveform_is_rejected(self):
        d,r,v,p,s,stop,name=self.args
        receipt=dict(cycles=r,vectors=v,probes=p,stop_ns=stop,campaign=name)
        with self.assertRaises(ValueError):a.evaluate_waveform(d[:-100],receipt,s,self.template)

    def test_missing_probe_is_rejected(self):
        d,r,v,p,s,stop,_=self.args;del p['REG_Q0']
        with self.assertRaises((ValueError,KeyError)):retention(d,r,v,p,s,stop)

    def test_a_and_numeric_measurements_cannot_qualify_b(self):
        self.assertEqual(a.characterization_status('PASS','PASS'),'NOT_CHARACTERIZED')
        self.assertEqual(a.characterization_status('PASS','FAIL'),'FAIL')
        self.assertEqual(a.characterization_status('PASS','BLOCKED'),'BLOCKED')


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.identity=selected_inputs(ROOT)
        self.c=json.loads((ROOT/'characterization/phase3/smoke.json').read_text())
        self.c.update(functional.CONDITIONS)
        self.c['measurements']=[]
        self.context=a.context_for(self.c['baseline'],self.identity,{k:self.c[k] for k in ('deck','netlist','model')})

    def test_context_identity_and_hash_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'a.json';path.write_text(json.dumps(self.context))
            self.c['functional_validation']=dict(path=str(path),sha256=digest(path))
            prepared=functional.prepare_context(ROOT,self.c)
            self.assertIn('activation_blocked',prepared)
            path.write_text(path.read_text()+'\n')
            with self.assertRaisesRegex(ValueError,'hash'):functional.prepare_context(ROOT,self.c)

    def test_candidate_and_conditions_cannot_be_relabeled(self):
        for mutation in ('candidate','corner','model'):
            with tempfile.TemporaryDirectory() as d:
                c=deepcopy(self.c);context=deepcopy(self.context)
                if mutation=='candidate':context['selection']['candidate']='different'
                elif mutation=='corner':c['corner']='ss'
                else:context['expected_inputs']['model']['sha256']='0'*64
                path=Path(d)/'a.json';path.write_text(json.dumps(context))
                c['functional_validation']=dict(path=str(path),sha256=digest(path))
                with self.subTest(mutation=mutation),self.assertRaises(ValueError):functional.prepare_context(ROOT,c)

    def test_runtime_adapter_cannot_activate_a(self):
        result=functional.check_waveform(ROOT,Path('/nonexistent'),self.context)
        self.assertEqual(result['status'],'BLOCKED')
        self.assertFalse(result['gate_enabled'])

    def test_runner_blocks_real_before_any_simulator_process(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'reports/phase3').mkdir(parents=True);(root/'release').mkdir()
            selector=ROOT/'release/phase2_current.json'
            (root/'release/phase2_current.json').write_bytes(selector.read_bytes())
            config=root/'config.json';config.write_text(json.dumps(self.c))
            prepared=dict(context=self.context,pins={},activation_blocked='O1-O4 pending')
            with patch.object(runner,'ROOT',root),patch.object(runner,'git',return_value='baseline'), \
                 patch.object(runner.subprocess,'run') as baseline, \
                 patch.object(runner.subprocess,'check_output',return_value=selector.read_bytes()), \
                 patch.object(runner,'preflight',return_value={}), \
                 patch.object(runner,'prepare_context',return_value=prepared), \
                 patch.object(runner.subprocess,'Popen') as simulator:
                baseline.return_value.returncode=0
                result=runner.run(config,root/'reports/phase3/blocked')
                simulator.assert_not_called()
            self.assertEqual(result['status'],'BLOCKED')
            self.assertFalse(result['electrical_simulation_performed'])
            self.assertEqual(result['functional_validation']['status'],'BLOCKED')
            manifest=json.loads((root/'reports/phase3/blocked/manifest.json').read_text())
            self.assertIn('functional_a.py',{Path(p).name for p in manifest['inputs']})
            with (root/'reports/phase3/blocked/metrics.csv').open() as f:
                self.assertEqual(next(csv.reader(f)),FIELDS);self.assertEqual(len(FIELDS),14)

    def test_replay_rejects_wrong_manifest_pin_before_reading_raw(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'manifest.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'manifest hash'):
                a.replay(ROOT,p,self.context,'0'*64)


if __name__=='__main__':unittest.main()
