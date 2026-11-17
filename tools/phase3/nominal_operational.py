"""P3-DATA-002 r1: approved opt-in nominal functional verification, B unqualified."""
import hashlib
import json
from pathlib import Path
import time
from phase2_evidence import digest
from .nominal_bench_plan import PROFILE, load_policy as load_r0, compile_plan

POLICY_PATH='characterization/phase3/nominal_bench_v1_r1.json'
POLICY_SHA256='ea5da44896590c71f0ddb11cd23c91084c9acbec0d5a550371ed31799674a8d4'
FIELDS={'schema_version','adapter','revision','assessment_mode','baseline','selection',
        'expected_inputs','approved_policy','observation_plan'}


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def pinned(root,spec):
    if not isinstance(spec,dict) or set(spec)!={'path','sha256'}:
        raise ValueError('Expected pinned approved dependency')
    path=Path(spec['path']);path=path if path.is_absolute() else root/path
    if digest(path)!=spec['sha256']:raise ValueError('Approved dependency hash differs: '+str(path))
    return path.resolve()


def load_approved(root):
    path=root/POLICY_PATH
    if digest(path)!=POLICY_SHA256:raise ValueError('Unknown/unapproved nominal policy version')
    policy=json.loads(path.read_text())
    if (policy['revision']!='r1' or policy['approval']!='APPROVED_NOMINAL_BENCH'
            or policy['functional_gate_enabled'] is not True or policy['global_gate_enabled'] is not False):
        raise ValueError('Invalid approved nominal scope')
    pins={str(path.resolve()):POLICY_SHA256}
    dependencies=[policy['authority'],*policy['r0'].values(),
                  *[dict(path=p,sha256=h) for p,h in policy['evaluator_inputs'].items()]]
    for spec in dependencies:
        source=pinned(root,spec);pins[str(source)]=spec['sha256']
    return policy,pins


def approved_plan(root,policy,identity):
    receipt=json.loads((root/identity['qualification']).read_text())
    plan=compile_plan(load_r0(root),receipt,(root/policy['fixture']['path']).read_text())
    if canonical_sha(plan)!=policy['approved_plan_sha256']:
        raise ValueError('Events/windows differ from approved r0 plan')
    return json.loads(json.dumps({**plan,'revision':'r1','approval':'APPROVED_NOMINAL_BENCH'}))


def prepare_approved(root,c,identity,output):
    from .runner import write_json
    policy,_=load_approved(root)
    plan=approved_plan(root,policy,identity)
    path=output/'approved_observation_plan.json';write_json(path,plan)
    return dict(schema_version=1,adapter=PROFILE,revision='r1',assessment_mode='fresh_run',
        baseline=c['baseline'],selection=identity,expected_inputs={k:c[k] for k in ('deck','netlist','model')},
        approved_policy=dict(path=POLICY_PATH,sha256=POLICY_SHA256),
        observation_plan=dict(path=str(path),sha256=digest(path)))


def validate_context(root,c,context):
    if (set(context)!=FIELDS or type(context['schema_version']) is not int or context['schema_version']!=1
            or context['adapter']!=PROFILE or context['revision']!='r1'
            or context['assessment_mode']!='fresh_run'):
        raise ValueError('Unknown/unapproved nominal context or replay context')
    if context['approved_policy']!={'path':POLICY_PATH,'sha256':POLICY_SHA256}:
        raise ValueError('Context does not reference the approved r1 policy')
    policy,pins=load_approved(root)
    for key,value in policy['conditions'].items():
        if c[key]!=value:raise ValueError('Conditions outside approved nominal scope: '+key)
    from .provenance import selected_inputs
    identity=selected_inputs(root,c['baseline'])
    if context['selection']!=identity or context['baseline']!=c['baseline']:
        raise ValueError('Approved context selection/baseline differs')
    if context['expected_inputs']!={k:c[k] for k in ('deck','netlist','model')}:
        raise ValueError('Approved context inputs differ')
    source=(root/identity['qualification']).parent
    if pinned(root,c['netlist'])!=(source/'binding.spice').resolve() or c['netlist']['sha256']!=identity['inputs'][str((source/'binding.spice').relative_to(root))]:
        raise ValueError('Netlist outside selected nominal candidate')
    if c['model']!=policy['model']:raise ValueError('Process model differs from approved nominal model')
    pinned(root,c['model'])
    deck=pinned(root,c['deck'])
    from prepare_phase3_4x8 import nominal_template
    if deck.read_text()!=nominal_template(source):
        raise ValueError('Deck differs from canonical fixture; replay/copy commands prohibited')
    path=pinned(root,context['observation_plan'])
    if canonical_sha(json.loads(path.read_text()))!=canonical_sha(approved_plan(root,policy,identity)):
        raise ValueError('Approved observation plan differs')
    pins[str(path)]=context['observation_plan']['sha256']
    return pins


def verify_execution(work,proof):
    raw=work/'waveform.dat'
    marker=work/'.nominal_execution_started'
    if (not isinstance(proof,dict) or proof.get('assessment_mode')!='fresh_run'
            or proof.get('workdir')!=str(work.resolve()) or proof.get('simulator_status')!='PASS'
            or proof.get('return_code')!=0 or proof.get('waveform_absent_before_start') is not True
            or type(proof.get('started_ns')) is not int or type(proof.get('finished_ns')) is not int
            or proof['started_ns']>proof['finished_ns'] or proof['finished_ns']>time.time_ns()
            or not marker.is_file() or marker.is_symlink() or marker.stat().st_mtime_ns!=proof['started_ns']
            or not raw.is_file() or raw.is_symlink()
            or not proof['started_ns']<=raw.stat().st_mtime_ns<=proof['finished_ns']):
        raise ValueError('No valid fresh simulator evidence; replay cannot be promoted')
    return raw


def check_fresh(root,work,context,proof):
    """Called by the runner only after a new successful child simulator process."""
    import numpy as np
    from .functional_a import evaluate_waveform
    from .nominal_bench import evaluate
    from .runner import write_json
    policy,_=load_approved(root)
    validate_context(root,{**policy['conditions'],'baseline':context.get('baseline'),
                           **context.get('expected_inputs',{})},context)
    raw=verify_execution(work,proof);raw_sha=digest(raw)
    identity=context['selection']
    receipt_path=root/identity['qualification'];receipt=json.loads(receipt_path.read_text())
    state=json.loads((root/identity['fixture']).read_text())
    template=json.loads((receipt_path.parent/'checks.json').read_text())['checks']
    plan_path=pinned(root,context['observation_plan']);plan=json.loads(plan_path.read_text())
    if canonical_sha(plan)!=canonical_sha(approved_plan(root,policy,identity)):raise ValueError('Approved plan changed before checking')
    with raw.open() as stream:
        if stream.readline().split()!=['time',*receipt['vectors']]:raise ValueError('Functional waveform header differs')
    data=np.loadtxt(raw,skiprows=1)
    partial=evaluate_waveform(data,receipt,state,template)
    output=work.parent
    write_json(output/'original_a_assessment.json',partial)
    if 'legacy_comparison' not in partial:raise ValueError('Incomplete underlying legacy/A evaluation')
    write_json(output/'legacy_comparison.json',partial['legacy_comparison'])
    # Reuse unchanged r0 calculations; r1 separately validates authority and exact plan.
    result=evaluate(data,receipt,partial,plan,policy)
    function=result['nominal_functional_status']
    if result['status']=='ERROR':function='ERROR'
    result.update(status=function,adapter=PROFILE,revision='r1',approval='APPROVED_NOMINAL_BENCH',
        functional_gate_enabled=True,global_gate_enabled=False,assessment_mode='fresh_run',
        waveform_sha256=raw_sha,policy=dict(path=POLICY_PATH,sha256=POLICY_SHA256),
        approval_required=[])
    for prop in result['properties'].values():prop['scope']='Approved r1 nominal bench functional scope only'
    for item in result['legacy_classification']:item['decision']='P3-DATA-002 r1 approved nominal scope; historical verdict unchanged'
    if digest(raw)!=raw_sha:raise ValueError('Fresh waveform changed during checking')
    write_json(output/'nominal_assessment.json',result)
    return {k:result[k] for k in ('status','adapter','revision','approval','functional_gate_enabled',
             'global_gate_enabled','assessment_mode','waveform_sha256','policy','coverage','properties',
             'nominal_functional_status','temporal_qualification')} | dict(
             checks=result['observations'],evidence_files=['nominal_assessment.json','legacy_comparison.json',
                 'original_a_assessment.json','execution_proof.json'])


def global_status(measurement,function):
    from .functional_a import characterization_status
    return characterization_status(measurement,function)  # B is still unqualified.
