"""Experimental nominal observations for P3-DATA-002; no approval/sign-off gate."""
from collections import Counter
import math
import numpy as np
from run_phase2_startup_review import levels
from analyze_phase2_extension_timing import valid
from .functional_a_coverage import MATRIX, verify_inventory
from .nominal_bench_plan import PROFILE


def validate_sampling(data, maximum_step_ns):
    if (data.ndim!=2 or len(data)<2 or not np.all(np.isfinite(data))
            or not np.all(np.diff(data[:,0])>0)):
        raise ValueError('Invalid/nonfinite/nonmonotonic evidence')
    t = data[:,0]*1e9
    # The archived wrdata prints 8 decimal places in the scientific mantissa.
    # This bound accounts for rounding of two timestamps, not physical settling.
    magnitude = max(abs(t[0]),abs(t[-1]))
    quantization = 10.**(math.floor(math.log10(magnitude))-8) if magnitude else 0.
    roundoff = quantization+2*np.spacing(magnitude)
    if np.any(np.diff(t)>maximum_step_ns+roundoff):
        raise ValueError('Evidence has gaps beyond the declared 10ps transient resolution')


def observe(data, vectors, probes, window):
    t = data[:,0]*1e9
    lo,hi=window['start_ns'],window['end_ns']
    if not math.isfinite(lo) or not math.isfinite(hi) or lo>=hi or t[0]>lo or t[-1]<hi:
        raise ValueError('Empty/incomplete observation window')
    signal,bit=window['signal'],window['bit']
    name=f'v(DATA{bit})' if signal=='DATA' else probes[signal+(str(bit) if bit is not None else '')]
    column=vectors.index(name)+1
    if window['kind']=='point':
        index=int(np.searchsorted(t,lo))
        if index>=len(t) or t[index]>=hi:raise ValueError('Scheduled point missing before next phase')
        ids=np.array([index])
    elif window['kind']=='levels':
        if window['bounds'] not in ('[)','[]'):raise ValueError('Unknown interval bounds')
        ids=np.flatnonzero((t>=lo)&((t<=hi) if window['bounds']=='[]' else (t<hi)))
        if len(ids)<2:raise ValueError('Empty/isolated interval evidence')
    else:raise ValueError('Unknown observer kind')
    values=data[ids,column];expected=window['expected'];bad=~valid(values,expected)
    return dict(id=window['id'],properties=window['properties'],signal=signal,bit=bit,cycle=window['cycle'],
                status='PASS' if levels(values,expected) else 'FAIL',expected=expected,
                target_ns=lo,first_sample_ns=float(t[ids[0]]),last_sample_ns=float(t[ids[-1]]),
                first_bad_ns=float(t[ids[np.flatnonzero(bad)[0]]]) if np.any(bad) else None,
                minimum_v=float(np.min(values)),maximum_v=float(np.max(values)),samples=len(ids),
                bounds=window['bounds'],end_ns=hi)


def source_preconditions(data,vectors,probes,plan):
    """Verify observable ideal-source plateaus; no public setup/hold minimum."""
    t=data[:,0]*1e9;facts=[]
    names=['CLK','CSb','OEb','WEb','HOST_EN','HOST_WEAK_EN',*[f'HOST{b}' for b in range(8)]]
    for name in names:
        vector=probes['WEAK_EN' if name=='HOST_WEAK_EN' else name]
        column=vectors.index(vector)+1;points=plan['sources'][name]
        mask=np.zeros(len(t),dtype=bool);good=np.ones(len(t),dtype=bool)
        segments=[*zip(points,points[1:]),(points[-1],(t[-1]+1,points[-1][1]))]
        for (lo,a),(hi,b) in segments:
            if a!=b:continue  # Exact PWL ramp; no invented electrical guard.
            selected=(t>=lo)&(t<hi);mask|=selected
            good[selected]=valid(data[selected,column],int(a==1.8))
        if not np.any(mask):raise ValueError('No plateau evidence for '+name)
        bad=mask&~good
        facts.append(dict(source=name,status='FAIL' if np.any(bad) else 'PASS',samples=int(np.sum(mask)),
                          first_bad_ns=float(t[np.flatnonzero(bad)[0]]) if np.any(bad) else None))
    return facts


def assemble(partial_a, plan, observations, preconditions):
    """Independent experimental verdict; never rewrites a legacy or A verdict."""
    if (partial_a.get('adapter')!='phase3_functional_a_v1'
            or partial_a.get('status') not in ('BLOCKED','FAIL')
            or partial_a.get('coverage',{}).get('legacy_mapping_complete') is not True
            or partial_a.get('legacy_comparison',{}).get('coverage_complete') is not True
            or partial_a['legacy_comparison'].get('total')!=1740
            or set(partial_a.get('properties',{}))!=set(MATRIX)):
        raise ValueError('Incomplete/unknown underlying A or legacy coverage')
    verify_inventory([w['id'] for w in plan['windows']],[o['id'] for o in observations])
    by_id={w['id']:w for w in plan['windows']}
    for o in observations:
        w=by_id[o['id']]
        if any(o[k]!=w[k] for k in ('properties','signal','bit','cycle','bounds','end_ns')) or o['target_ns']!=w['start_ns']:
            raise ValueError('Observation metadata/requirement coverage differs')
    if any(o['status'] not in ('PASS','FAIL') for o in observations+preconditions):
        raise ValueError('Invalid observation verdict')
    expected_sources={'CLK','CSb','OEb','WEb','HOST_EN','HOST_WEAK_EN',*[f'HOST{b}' for b in range(8)]}
    verify_inventory(list(expected_sources),[o['source'] for o in preconditions])
    properties={}
    for prop,(requirements,_) in MATRIX.items():
        base=partial_a['properties'][prop]
        added=[o for o in observations if prop in o['properties']]
        statuses=[o['status'] for o in added]
        if base['observation_status']=='FAIL':statuses.append('FAIL')
        status='FAIL' if 'FAIL' in statuses else 'PASS'
        if prop in ('A05','A08','A09','A10') and not added:status='BLOCKED'
        properties[prop]=dict(status=status,functional_status=status,requirements=requirements,
                              added_observations=len(added),scope='PROPOSED nominal bench observations only')
    properties['A10'].update(status='NOT_CHARACTERIZED' if properties['A10']['functional_status']=='PASS' else properties['A10']['functional_status'],
        electrical_recovery=dict(status='NOT_CHARACTERIZED',opportunities=len(plan['resumes']),deadline_ns=None),
        complete_electrical_contract=False)
    functional='FAIL' if partial_a['status']=='FAIL' or any(p['functional_status']=='FAIL' for p in properties.values()) else 'BLOCKED' if any(p['functional_status']=='BLOCKED' for p in properties.values()) else 'PASS'
    precondition_failure=any(o['status']=='FAIL' for o in preconditions)
    status='ERROR' if precondition_failure else 'FAIL' if functional=='FAIL' else 'BLOCKED'
    classification=[]
    for item in partial_a['legacy_comparison']['mapping']:
        if item['source_kind']=='previous_data_visible_before_new_capture':
            classification.append(dict(legacy_index=item['legacy_index'],legacy_status=item['legacy_status'],
                proposal='independent continuous-read observation' if item['property']=='A05' else 'unqualified B recovery; no old-word 1ns requirement',
                decision='P3-DATA-002 r0 PROPOSED',historical_verdict_changed=False))
    return dict(schema_version=1,profile=PROFILE,decision='P3-DATA-002',revision='r0',approval='PROPOSED',
        global_gate_enabled=False,status=status,nominal_functional_status='BLOCKED' if precondition_failure else functional,
        preconditions=preconditions,properties=properties,observations=observations,
        recovery_opportunities=plan['resumes'],legacy_classification=classification,
        legacy_status=partial_a['legacy_comparison']['legacy_status'],
        original_a_status=partial_a['status'],temporal_qualification=dict(status='NOT_CHARACTERIZED',
            reason='No approved B maximum; observed TT values never establish a PVT guarantee'),
        coverage=dict(window_identities_complete=True,windows=len(observations),
                      new_read_bits=sum(w['event']=='DATA_NEW' for w in plan['windows']),
                      functional_resume_bits=sum('A10' in w['properties'] for w in plan['windows'])),
        approval_required=['O1a nominal scope','O2 scheduled windows and transition treatment',
                           'O3 revised A10 functional/electrical split','O4 fixture preconditions',
                           'authorization of any operational gate activation'])


def evaluate(data,receipt,partial_a,plan,policy):
    if partial_a['status']=='ERROR':raise ValueError('Incomplete underlying A/legacy assessment')
    validate_sampling(data,policy['maximum_transient_step_ns'])
    observations=[observe(data,receipt['vectors'],receipt['probes'],w) for w in plan['windows']]
    preconditions=source_preconditions(data,receipt['vectors'],receipt['probes'],plan)
    return assemble(partial_a,plan,observations,preconditions)
