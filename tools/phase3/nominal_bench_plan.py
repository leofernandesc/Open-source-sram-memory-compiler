"""P3-DATA-002 r0: fixed nominal fixture schedule, independent of DATA/Q results."""
import hashlib
import json
from pathlib import Path
import re

PROFILE = 'phase3_nominal_bench_v1'
POLICY_PATH = 'characterization/phase3/nominal_bench_v1.json'
POLICY_SHA256 = 'cd8f9d83ca3141d2768055d65846962c4d969ee36c50924964f61128fd7181f6'


def validate_policy(policy):
    # The draft is immutable by content, not merely by a caller's approval flag.
    root = Path(__file__).resolve().parents[2]
    raw = (root/POLICY_PATH).read_bytes()
    if (hashlib.sha256(raw).hexdigest() != POLICY_SHA256
            or json.dumps(policy,sort_keys=True,allow_nan=False)!=json.dumps(json.loads(raw),sort_keys=True)):
        raise ValueError('Unknown/modified nominal policy or unapproved observation windows')
    if policy['approval'] != 'PROPOSED' or policy['global_gate_enabled'] is not False:
        raise ValueError('Nominal gate activation is not authorized')
    return policy


def load_policy(root):
    return validate_policy(json.loads((root/POLICY_PATH).read_text()))


def parse_pwl(text):
    """Only the literal, single-line voltage PWL dialect of the pinned fixture."""
    sources = {}
    def scalar(token, time=False):
        match = re.fullmatch(r'([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([np]?)', token)
        if not match: raise ValueError('Unsupported fixture PWL scalar: '+token)
        value = float(match[1])
        return value*({'n':1.,'p':.001,'':1e9}[match[2]]) if time else value
    for line in text.splitlines():
        match = re.fullmatch(r'V_\S+\s+(\S+)\s+0\s+PWL\((.*)\)',line)
        if not match: continue
        words = match[2].split()
        if len(words)%2 or match[1] in sources: raise ValueError('Invalid/duplicate fixture source')
        points = [(scalar(words[i],True),scalar(words[i+1])) for i in range(0,len(words),2)]
        if any(b[0]<=a[0] for a,b in zip(points,points[1:])):
            raise ValueError('Nonmonotonic PWL source')
        sources[match[1]] = points
    return sources


def changes(points):
    return [(a[0],b[0]) for a,b in zip(points,points[1:]) if a[1]!=b[1]]


def source_value(points, time_ns):
    import numpy as np
    return float(np.interp(time_ns,*zip(*points)))


def compile_plan(policy, receipt, fixture_text):
    validate_policy(policy)
    from .functional_a import validate_records
    records = receipt['cycles']; validate_records(records)
    if (len(records)!=18 or receipt['stop_ns']!=370 or sum(r['operation']=='read' for r in records)!=9
            or hashlib.sha256(fixture_text.encode()).hexdigest()!=policy['fixture']['sha256']):
        raise ValueError('Nominal fixture/record scope differs')
    sources = parse_pwl(fixture_text)
    needed = {'CLK','CSb','OEb','WEb','ADDR0','ADDR1','HOST_EN','HOST_WEAK_EN',*[f'HOST{b}' for b in range(8)]}
    if not needed <= set(sources): raise ValueError('Missing PWL fixture source')
    control_changes = sorted({start for n in ('CSb','OEb','WEb','HOST_EN','HOST_WEAK_EN')
                              for start,end in changes(sources[n])})
    windows, phases, resumes, events, calibration_windows = [], [], [], [], []
    reads = [r for r in records if r['operation']=='read']
    def row(r, ident, signal, bit, start, end, kind, props, closed=False):
        if not start < end: raise ValueError('Empty planned observation window')
        windows.append(dict(id=f'{ident}:c{r["cycle"]}:{signal}:{bit}', event=ident,
            cycle=r['cycle'], row=r['row'], signal=signal, bit=bit,
            expected=(r['expected']>>bit)&1 if signal in ('DATA','REG_Q') else 0 if signal=='TE_B' else 1,
            start_ns=start,end_ns=end,bounds='[]' if closed else '[)',kind=kind,properties=props,
            reference='fixed fixture PWL / preexisting scheduled observations'))
    for r in records:
        rise,fall = r['rise_ns'],r['fall_ns']
        if source_value(sources['CLK'],rise)!=0 or source_value(sources['CLK'],fall)!=1.8:
            raise ValueError('CLK record does not match pinned PWL')
        control = tuple(round(source_value(sources[n],rise)/1.8) for n in ('CSb','OEb','WEb'))
        expected_control = (0,0,1) if r['operation']=='read' else (0,1,0) if r['operation']=='write' else (1,1,1)
        if control!=expected_control: raise ValueError('Fixture operation precondition differs')
        address = sum(round(source_value(sources[f'ADDR{b}'],rise)/1.8)<<b for b in range(2))
        if address!=r['row']: raise ValueError('Fixture address precondition differs')
        if r['operation']=='write':
            payload=sum(round(source_value(sources[f'HOST{b}'],rise)/1.8)<<b for b in range(8))
            if payload!=r['expected'] or source_value(sources['HOST_EN'],rise)!=1.8:
                raise ValueError('Fixture write precondition differs')
        if r['operation']!='read': continue
        cal = r['calibration']; post=rise+policy['post_probe_offset_ns']
        for field,source,offset in [('weak_on_ns','HOST_WEAK_EN',11.5),('mask_ns','CSb',12.5),
                                    ('restore_ns','CSb',14),('weak_off_ns','HOST_WEAK_EN',15.5)]:
            if cal[field]!=rise+offset or not any(start==cal[field] for start,end in changes(sources[source])):
                raise ValueError('Fixture calibration event differs')
        if r['sample_ns']!=rise+11: raise ValueError('Scheduled external observation differs')
        future_reads=[q for q in reads if q['cycle']>r['cycle']]
        next_fall=future_reads[0]['fall_ns'] if future_reads else receipt['stop_ns']
        next_disturbance=min([x for x in control_changes if x>=post]+[next_fall,receipt['stop_ns']])
        continuous = bool(future_reads and next_disturbance==next_fall
                          and records[r['cycle']+1]['operation']=='read')
        previous=records[r['cycle']-1]['operation'] if r['cycle'] else 'startup'
        previous_reads=[q for q in reads if q['cycle']<r['cycle']]
        previous_read=previous_reads[-1] if previous_reads else None
        resumed=previous in ('write','idle')
        if source_value(sources['HOST_EN'],rise)!=0: raise ValueError('Strong host active at read capture')
        events.append(dict(cycle=r['cycle'],rise_pwl_ns=rise,fall_pwl_ns=fall,
                           new_sample_ns=r['sample_ns'],post_probe_sample_ns=post,
                           next_disturbance_ns=next_disturbance,continuous_to_next_read=continuous,
                           **cal))
        for name,lo,hi,kinds in [
            ('probe_enabled',12.,12.35,['probe_observes_enabled_drive']),
            ('masked',13.2,13.8,['masked_probe_current','masked_probe_voltage']),
            ('restored_probe',14.7,15.2,['restored_drive_current'])]:
            calibration_windows.append(dict(cycle=r['cycle'],phase=name,start_ns=rise+lo,end_ns=rise+hi,
                                            bounds='[]',source='unchanged Phase 2 observer',check_kinds=kinds))
        transition_end = {field:next(end for start,end in changes(sources[source]) if start==cal[field])
                          for field,source in [('mask_ns','CSb'),('restore_ns','CSb'),('weak_off_ns','HOST_WEAK_EN')]}
        phases.extend([
            dict(cycle=r['cycle'],phase='legal_capture_update',start_ns=fall,end_ns=r['sample_ns'],bounds='[)',status='NOT_CHARACTERIZED',obligation='new word at the scheduled endpoint'),
            dict(cycle=r['cycle'],phase='intentional_probe',start_ns=cal['weak_on_ns'],end_ns=cal['mask_ns'],bounds='[)',status='NOT_CHARACTERIZED',obligation='unchanged enabled-drive current calibration'),
            dict(cycle=r['cycle'],phase='mask_transition',start_ns=cal['mask_ns'],end_ns=transition_end['mask_ns'],bounds='[)',status='NOT_CHARACTERIZED',obligation='Q retained; no instantaneous physical disable guarantee'),
            dict(cycle=r['cycle'],phase='masked',start_ns=transition_end['mask_ns'],end_ns=cal['restore_ns'],bounds='[)',status='NOT_CHARACTERIZED',obligation='unchanged masked current/voltage checks; Q retained'),
            dict(cycle=r['cycle'],phase='restore_transition',start_ns=cal['restore_ns'],end_ns=transition_end['restore_ns'],bounds='[)',status='NOT_CHARACTERIZED',obligation='Q retained; no B recovery budget'),
            dict(cycle=r['cycle'],phase='restore_with_probe',start_ns=transition_end['restore_ns'],end_ns=cal['weak_off_ns'],bounds='[)',status='NOT_CHARACTERIZED',obligation='unchanged restored-drive current calibration'),
            dict(cycle=r['cycle'],phase='probe_off_transition',start_ns=cal['weak_off_ns'],end_ns=transition_end['weak_off_ns'],bounds='[)',status='NOT_CHARACTERIZED',obligation='Q retained'),
            dict(cycle=r['cycle'],phase='post_probe_recovery',start_ns=transition_end['weak_off_ns'],end_ns=post,bounds='[)',status='NOT_CHARACTERIZED',obligation='word at preexisting post-probe observation; no B maximum')])
        if resumed:
            phases.append(dict(cycle=r['cycle'],phase='old_word_reenable_recovery',start_ns=rise,end_ns=fall,bounds='[)',status='NOT_CHARACTERIZED',obligation='Q retained; DATA old-word deadline absent'))
        for bit in range(8):
            unchanged=previous_read is not None and ((previous_read['expected']>>bit)&1)==((r['expected']>>bit)&1)
            if unchanged:
                row(r,'Q_STABLE_CAPTURE','REG_Q',bit,fall,r['sample_ns'],'levels',['A03','A04'])
                if previous=='read':
                    prior_post=previous_read['rise_ns']+policy['post_probe_offset_ns']
                    if not any(prior_post<=x<r['sample_ns'] for x in control_changes):
                        row(r,'DATA_STABLE_CAPTURE','DATA',bit,fall,r['sample_ns'],'levels',['A05','A09'])
            row(r,'DATA_NEW','DATA',bit,r['sample_ns'],cal['weak_on_ns'],'point',['A08']+(['A10'] if resumed else []))
            row(r,'Q_NEW','REG_Q',bit,r['sample_ns'],cal['weak_on_ns'],'point',['A03'])
            row(r,'DATA_NEW_STABLE','DATA',bit,r['sample_ns'],cal['weak_on_ns'],'levels',['A09'])
            row(r,'ENABLE_NEW','TE_B',bit,r['sample_ns'],cal['weak_on_ns'],'levels',['A06'])
            row(r,'DATA_POST','DATA',bit,post,next_disturbance,'point',['A08','A10'])
            row(r,'DATA_POST_STABLE','DATA',bit,post,next_disturbance,'levels',['A09']+(['A05'] if continuous else []),next_disturbance==receipt['stop_ns'])
            row(r,'ENABLE_POST','TE_B',bit,post,next_disturbance,'levels',['A06'],next_disturbance==receipt['stop_ns'])
            row(r,'Q_RETAIN','REG_Q',bit,r['sample_ns'],next_fall,'levels',['A04'],not future_reads)
            for scenario in (['captured_'+previous] if resumed else [])+['mask_restore']:
                resumes.append(dict(id=f'{scenario}:c{r["cycle"]}:b{bit}',cycle=r['cycle'],bit=bit,
                                    scenario=scenario,functional_event='DATA_NEW' if scenario!='mask_restore' else 'DATA_POST',
                                    electrical_recovery_status='NOT_CHARACTERIZED',deadline_ns=None))
        row(r,'READ_ENABLE_NEW','READ_Q',None,r['sample_ns'],cal['weak_on_ns'],'levels',['A06'])
        row(r,'READ_ENABLE_POST','READ_Q',None,post,next_disturbance,'levels',['A06'],next_disturbance==receipt['stop_ns'])
    if len(resumes)!=policy['recovery']['required_functional_resume_bits'] or len(windows)!=626:
        raise ValueError('Nominal mandatory scope is incomplete')
    return dict(schema_version=1,profile=PROFILE,decision=policy['decision'],revision=policy['revision'],
                windows=windows,phases=phases,resumes=resumes,events=events,sources=sources,
                calibration_windows=calibration_windows,
                legacy_calibration='All existing inclusive current/voltage/Q windows preserved unchanged')
