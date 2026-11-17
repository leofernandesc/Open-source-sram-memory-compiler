"""Synthetic policy/observer regressions, not a new electrical simulation."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase2_evidence import digest
from phase3.runner import ROOT
from phase3.nominal_bench_plan import load_policy,validate_policy,compile_plan,parse_pwl,changes
from phase3.nominal_bench import observe,assemble,source_preconditions,validate_sampling
from phase3.functional_a_coverage import MATRIX
import review_phase3_nominal_bench as cli


def setUpModule():
    # Standalone software tests must also work before the first local run.
    (ROOT/'reports/phase3').mkdir(parents=True,exist_ok=True)


def window(kind='levels',bounds='[)'):
    return dict(id='synthetic',event='synthetic',signal='DATA',bit=0,cycle=0,
                properties=['A09'],expected=1,start_ns=5.,end_ns=6.,kind=kind,bounds=bounds)


class PlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy=load_policy(ROOT)
        path=ROOT/'reports/phase2/direct_abutment_20261111/qualification_v1/results.json'
        cls.receipt=json.loads(path.read_text())
        cls.fixture=(ROOT/cls.policy['fixture']['path']).read_text()
        cls.plan=compile_plan(cls.policy,cls.receipt,cls.fixture)

    def test_canonical_proposed_policy_and_scope(self):
        self.assertEqual(validate_policy(self.policy)['approval'],'PROPOSED')
        self.assertFalse(self.policy['global_gate_enabled'])
        self.assertEqual(len(self.plan['windows']),626)
        self.assertEqual(len(self.plan['resumes']),104)

    def test_approval_flag_cannot_authorize_gate(self):
        for name,value in [('approval','APPROVED'),('global_gate_enabled',True),('schema_version',True)]:
            p=deepcopy(self.policy);p[name]=value
            with self.subTest(name=name),self.assertRaises(ValueError):validate_policy(p)

    def test_pvt_or_load_change_rejected(self):
        for name,value in [('corner','ss'),('vdd_v',1.62),('temp_c',125),('load_ff',20)]:
            p=deepcopy(self.policy);p['conditions'][name]=value
            with self.subTest(name=name),self.assertRaises(ValueError):validate_policy(p)

    def test_data_fitted_windows_rejected(self):
        for reference in ('settle(DATA)','first_valid_Q',1.098):
            p=deepcopy(self.policy);p['window_rules'][0]['start']=reference
            with self.subTest(reference=reference),self.assertRaises(ValueError):validate_policy(p)

    def test_unqualified_recovery_cannot_gain_a_deadline(self):
        p=deepcopy(self.policy);p['recovery']['old_word_enable_deadline_ns']=1.2
        with self.assertRaises(ValueError):validate_policy(p)
        self.assertTrue(all(r['deadline_ns'] is None and r['electrical_recovery_status']=='NOT_CHARACTERIZED' for r in self.plan['resumes']))

    def test_fixture_hash_changes_rejected(self):
        with self.assertRaises(ValueError):compile_plan(self.policy,self.receipt,self.fixture+'\n')

    def test_moving_readback_to_fit_data_rejected(self):
        r=deepcopy(self.receipt);r['cycles'][6]['sample_ns']+=.2
        with self.assertRaises(ValueError):compile_plan(self.policy,r,self.fixture)

    def test_record_address_must_match_pwl(self):
        r=deepcopy(self.receipt);r['cycles'][0]['row']=3
        with self.assertRaises(ValueError):compile_plan(self.policy,r,self.fixture)

    def test_missing_cycle_cannot_reduce_denominator(self):
        r=deepcopy(self.receipt);r['cycles'].pop()
        with self.assertRaises(ValueError):compile_plan(self.policy,r,self.fixture)

    def test_continuous_window_spans_high_phase_to_scheduled_fall(self):
        w=next(w for w in self.plan['windows'] if w['event']=='DATA_POST_STABLE' and w['cycle']==6 and w['bit']==0)
        self.assertEqual((w['start_ns'],w['end_ns'],w['bounds']),(146.3,160,'[)'))
        self.assertIn('A05',w['properties'])
        self.assertTrue(w['start_ns']<150<w['end_ns'])

    def test_write_handoff_stops_continuity_at_true_control_change(self):
        w=next(w for w in self.plan['windows'] if w['event']=='DATA_POST_STABLE' and w['cycle']==7 and w['bit']==0)
        self.assertEqual(w['end_ns'],167)
        self.assertNotIn('A05',w['properties'])

    def test_mask_transition_and_recovery_are_explicit(self):
        phases={p['phase']:p for p in self.plan['phases'] if p['cycle']==6}
        self.assertEqual((phases['mask_transition']['start_ns'],phases['mask_transition']['end_ns']),(142.5,142.55))
        self.assertEqual((phases['post_probe_recovery']['start_ns'],phases['post_probe_recovery']['end_ns']),(145.55,146.3))
        self.assertEqual(phases['post_probe_recovery']['status'],'NOT_CHARACTERIZED')

    def test_final_stop_is_inclusive(self):
        w=next(w for w in self.plan['windows'] if w['event']=='DATA_POST_STABLE' and w['cycle']==17 and w['bit']==0)
        self.assertEqual((w['end_ns'],w['bounds']),(370,'[]'))

    def test_unchanged_bits_do_not_get_a_capture_exclusion(self):
        q=[w for w in self.plan['windows'] if w['event']=='Q_STABLE_CAPTURE']
        d=[w for w in self.plan['windows'] if w['event']=='DATA_STABLE_CAPTURE']
        self.assertEqual((len(q),len(d)),(20,12))
        self.assertEqual({w['bit'] for w in d if w['cycle']==15},{1,3,4,6})
        self.assertFalse(any(w['cycle']==9 for w in d))  # Write->read is recovery, not continuity.

    def test_unchanged_bit_glitch_during_capture_update_is_detected(self):
        for signal,event in [('DATA','DATA_STABLE_CAPTURE'),('REG_Q','Q_STABLE_CAPTURE')]:
            w=next(w for w in self.plan['windows'] if w['event']==event and w['cycle']==15)
            t=np.linspace(w['start_ns']-1,w['end_ns']+1,301)
            data=np.column_stack((t*1e-9,np.full(len(t),1.8*w['expected'])))
            vectors=[f'v(DATA{w["bit"]})'] if signal=='DATA' else ['v(synthetic_q)']
            probes={f'REG_Q{w["bit"]}':'v(synthetic_q)'}
            self.assertEqual(observe(data,vectors,probes,w)['status'],'PASS')
            data[int(np.searchsorted(t,w['start_ns']+.5)),1]=1.8*(1-w['expected'])
            with self.subTest(signal=signal):self.assertEqual(observe(data,vectors,probes,w)['status'],'FAIL')

    def test_same_value_pwl_events_do_not_invent_enable_interruptions(self):
        p=parse_pwl('V_X CSb 0 PWL(0n 0 10n 0 10.05n 0 20n 0 20.05n 1.8)')
        self.assertEqual(changes(p['CSb']),[(20,20.05)])


class ObserverTests(unittest.TestCase):
    def setUp(self):
        t=np.linspace(0,10,1001);self.d=np.column_stack((t*1e-9,np.full(len(t),1.8)))
        self.vectors=['v(DATA0)'];self.w=window()

    def at(self,ns):return int(np.searchsorted(self.d[:,0]*1e9,ns))

    def test_point_observes_first_sample_not_first_correct_sample(self):
        self.d[self.at(5),1]=.9
        r=observe(self.d,self.vectors,{},window('point'))
        self.assertEqual(r['status'],'FAIL')
        self.assertEqual(r['first_sample_ns'],5)

    def test_wrong_data_cannot_pass(self):
        self.d[:,1]=0
        self.assertEqual(observe(self.d,self.vectors,{},self.w)['status'],'FAIL')

    def test_glitch_between_observation_points_fails(self):
        self.d[self.at(5.37),1]=.9
        self.assertEqual(observe(self.d,self.vectors,{},self.w)['status'],'FAIL')

    def test_instantaneous_correct_value_is_insufficient(self):
        self.d[:,1]=.9;self.d[self.at(5),1]=1.8
        self.assertEqual(observe(self.d,self.vectors,{},window('point'))['status'],'PASS')
        self.assertEqual(observe(self.d,self.vectors,{},self.w)['status'],'FAIL')

    def test_start_boundary_is_mandatory(self):
        self.d[self.at(5),1]=0
        self.assertEqual(observe(self.d,self.vectors,{},self.w)['status'],'FAIL')

    def test_end_boundary_excludes_legal_next_perturbation(self):
        index=self.at(6);self.d[index,0]=6e-9;self.d[index,1]=0
        self.assertEqual(self.d[index,0]*1e9,6.)
        self.assertEqual(observe(self.d,self.vectors,{},self.w)['status'],'PASS')
        self.assertEqual(observe(self.d,self.vectors,{},window(bounds='[]'))['status'],'FAIL')

    def test_sample_numerically_after_closed_end_is_outside(self):
        index=self.at(6);self.d[index,0]=np.nextafter(6.,np.inf)/1e9;self.d[index,1]=0
        self.assertGreater(self.d[index,0]*1e9,6.)
        self.assertEqual(observe(self.d,self.vectors,{},window(bounds='[]'))['status'],'PASS')

    def test_just_before_falling_boundary_is_not_discarded(self):
        self.d[self.at(5.99),1]=0
        self.assertEqual(observe(self.d,self.vectors,{},self.w)['status'],'FAIL')

    def test_empty_or_single_sample_interval_rejected(self):
        for lo,hi in [(5,5),(5,5.001),(10.1,11)]:
            w=dict(self.w,start_ns=lo,end_ns=hi)
            with self.subTest(lo=lo,hi=hi),self.assertRaises(ValueError):observe(self.d,self.vectors,{},w)

    def test_missing_point_before_next_phase_rejected(self):
        w=dict(window('point'),start_ns=5.0001,end_ns=5.0002)
        with self.assertRaises(ValueError):observe(self.d,self.vectors,{},w)

    def test_omitted_interior_samples_are_evidence_error(self):
        validate_sampling(self.d,.01)
        with self.assertRaisesRegex(ValueError,'gaps'):validate_sampling(np.delete(self.d,550,axis=0),.01)

    def test_nonfinite_evidence_rejected(self):
        self.d[550,1]=np.nan
        with self.assertRaises(ValueError):validate_sampling(self.d,.01)

    def test_ideal_source_preconditions_detect_bad_plateau(self):
        names=['CLK','CSb','OEb','WEb','HOST_EN','HOST_WEAK_EN',*[f'HOST{b}' for b in range(8)]]
        t=self.d[:,0];d=np.column_stack((t,np.zeros((len(t),len(names)))))
        vectors=[f'v({n})' for n in names];probes={n:f'v({n})' for n in names};probes['WEAK_EN']=probes['HOST_WEAK_EN']
        plan=dict(sources={n:[(0.,0.),(10.,0.)] for n in names})
        self.assertTrue(all(f['status']=='PASS' for f in source_preconditions(d,vectors,probes,plan)))
        d[550,1]=.9
        self.assertEqual(source_preconditions(d,vectors,probes,plan)[0]['status'],'FAIL')


class AggregationTests(unittest.TestCase):
    def setUp(self):
        # Labeled synthetic aggregation inputs, not a fabricated SRAM waveform.
        self.base=dict(adapter='phase3_functional_a_v1',status='BLOCKED',coverage=dict(legacy_mapping_complete=True),
            properties={p:dict(observation_status='PASS') for p in MATRIX},
            legacy_comparison=dict(coverage_complete=True,total=1740,legacy_status='FAIL',mapping=[
                dict(source_kind='previous_data_visible_before_new_capture',property='A10',legacy_index=i,legacy_status='FAIL') for i in range(4)]))
        self.plan=dict(windows=[],resumes=[dict(deadline_ns=None) for _ in range(104)])
        self.obs=[]
        for i,prop in enumerate(('A05','A08','A09','A10')):
            w=dict(window(),id=str(i),properties=[prop],event='DATA_NEW')
            self.plan['windows'].append(w)
            self.obs.append(dict(id=w['id'],properties=w['properties'],signal=w['signal'],bit=w['bit'],
                cycle=w['cycle'],bounds=w['bounds'],end_ns=w['end_ns'],target_ns=w['start_ns'],status='PASS'))
        self.pre=[dict(source=n,status='PASS') for n in ('CLK','CSb','OEb','WEb','HOST_EN','HOST_WEAK_EN',*[f'HOST{b}' for b in range(8)])]

    def test_functional_trial_pass_is_not_global_approval(self):
        r=assemble(self.base,self.plan,self.obs,self.pre)
        self.assertEqual(r['nominal_functional_status'],'PASS');self.assertEqual(r['status'],'BLOCKED')
        self.assertEqual(r['temporal_qualification']['status'],'NOT_CHARACTERIZED')
        self.assertFalse(r['global_gate_enabled'])

    def test_a10_functional_and_electrical_scopes_are_separate(self):
        r=assemble(self.base,self.plan,self.obs,self.pre)['properties']['A10']
        self.assertEqual(r['functional_status'],'PASS');self.assertEqual(r['status'],'NOT_CHARACTERIZED')
        self.assertIsNone(r['electrical_recovery']['deadline_ns'])

    def test_a10_wrong_new_word_remains_failure(self):
        self.obs[-1]['status']='FAIL'
        r=assemble(self.base,self.plan,self.obs,self.pre)
        self.assertEqual(r['properties']['A10']['functional_status'],'FAIL');self.assertEqual(r['status'],'FAIL')

    def test_continuous_read_glitch_remains_failure(self):
        self.obs[0]['status']='FAIL'
        self.assertEqual(assemble(self.base,self.plan,self.obs,self.pre)['properties']['A05']['status'],'FAIL')

    def test_q_driver_and_contention_failures_cannot_be_hidden(self):
        for prop in ('A04','A06','A07'):
            b=deepcopy(self.base);b['properties'][prop]['observation_status']='FAIL';b['status']='FAIL'
            with self.subTest(property=prop):self.assertEqual(assemble(b,self.plan,self.obs,self.pre)['status'],'FAIL')

    def test_legacy_fails_are_preserved_without_retroactive_pass(self):
        original=deepcopy(self.base);r=assemble(self.base,self.plan,self.obs,self.pre)
        self.assertEqual(self.base,original);self.assertEqual(r['legacy_status'],'FAIL')
        self.assertEqual([c['legacy_status'] for c in r['legacy_classification']],['FAIL']*4)
        self.assertTrue(all(c['historical_verdict_changed'] is False for c in r['legacy_classification']))

    def test_missing_and_duplicated_observations_rejected(self):
        for observations in (self.obs[:-1],self.obs+[self.obs[0]]):
            with self.assertRaises(ValueError):assemble(self.base,self.plan,observations,self.pre)

    def test_requirement_cannot_be_removed_from_existing_identity(self):
        observations=deepcopy(self.obs);observations[0]['properties']=[]
        with self.assertRaises(ValueError):assemble(self.base,self.plan,observations,self.pre)

    def test_missing_base_coverage_prevents_nominal_pass(self):
        self.base['coverage']['legacy_mapping_complete']=False
        with self.assertRaises(ValueError):assemble(self.base,self.plan,self.obs,self.pre)

    def test_missing_source_precondition_prevents_pass(self):
        with self.assertRaises(ValueError):assemble(self.base,self.plan,self.obs,self.pre[:-1])

    def test_invalid_stimulus_is_reported_as_evidence_error(self):
        self.pre[0]['status']='FAIL'
        r=assemble(self.base,self.plan,self.obs,self.pre)
        self.assertEqual(r['status'],'ERROR');self.assertEqual(r['nominal_functional_status'],'BLOCKED')

    def test_tt_measure_does_not_become_pvt_or_approved_b_limit(self):
        self.base['measured_tt_enable_ns']=1.098
        r=assemble(self.base,self.plan,self.obs,self.pre)
        self.assertEqual(r['temporal_qualification']['status'],'NOT_CHARACTERIZED')
        self.assertNotEqual(r['status'],'PASS')


class CLISafetyTests(unittest.TestCase):
    def test_wrong_manifest_pin_rejected_before_creating_assessment(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'reports/phase3') as d:
            p=Path(d);source=p/'source';source.mkdir();(source/'manifest.json').write_text('{}')
            with self.assertRaises(ValueError):cli.review(source,p/'out','0'*64)
            self.assertFalse((p/'out').exists())

    def test_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'reports/phase3') as d:
            p=Path(d);(p/'manifest.json').write_text('{}')
            with self.assertRaises(FileExistsError):cli.review(p,p,digest(p/'manifest.json'))
            self.assertEqual((p/'manifest.json').read_text(),'{}')


if __name__=='__main__':unittest.main()
