#!/usr/bin/env python3
"""Experimental P3-DATA-002 nominal replay only. Never invokes SPICE or approves a gate."""
import argparse
import json
from pathlib import Path
import shutil
import sys
from phase2_evidence import digest
from phase3.runner import ROOT, git, write_json
from phase3.provenance import selected_inputs
from phase3.functional_a import context_for, replay
from phase3.nominal_bench_plan import load_policy, compile_plan, POLICY_PATH, POLICY_SHA256
from phase3.nominal_bench import evaluate


def review(source,output,manifest_sha256):
    source,output=Path(source).resolve(),Path(output).resolve()
    if not output.is_relative_to(ROOT/'reports/phase3') or output==ROOT/'reports/phase3':
        raise ValueError('Use a new directory below reports/phase3')
    if digest(source/'manifest.json')!=manifest_sha256:raise ValueError('Source manifest pin differs')
    output.mkdir(parents=True)  # Never overwrite prior assessments, including errors.
    result=dict(schema_version=1,status='ERROR',assessment_mode='replay',electrical_simulation_performed=False,
                sram_characterized=False,profile='phase3_nominal_bench_v1',approval='PROPOSED',global_gate_enabled=False)
    inputs={}
    try:
        for path in [*Path(__file__).with_name('phase3').glob('*.py'),Path(__file__),ROOT/POLICY_PATH]:
            target=output/'source_snapshot'/path.relative_to(ROOT)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
            inputs[str(path)]=digest(path)
        policy=load_policy(ROOT)
        manifest=json.loads((source/'manifest.json').read_text());c=manifest['configuration']
        identity=selected_inputs(ROOT,c['baseline'])
        context=context_for(c['baseline'],identity,{k:c[k] for k in ('deck','netlist','model')})
        partial=replay(ROOT,source,context,manifest_sha256)
        write_json(output/'original_a_assessment.json',partial)
        write_json(output/'legacy_comparison.json',partial['legacy_comparison'])
        receipt_path=ROOT/identity['qualification'];receipt=json.loads(receipt_path.read_text())
        fixture_path=ROOT/policy['fixture']['path'];inputs[str(fixture_path)]=digest(fixture_path)
        plan=compile_plan(policy,receipt,fixture_path.read_text())
        write_json(output/'observation_plan.json',plan)
        import numpy as np
        raw=source/'inputs/waveform.dat';raw_sha=digest(raw)
        if raw_sha!=manifest['evidence']['inputs/waveform.dat']:raise ValueError('Source raw pin differs')
        result.update(evaluate(np.loadtxt(raw,skiprows=1),receipt,partial,plan,policy))
        result['source_execution']=partial['source_execution']
        if digest(raw)!=raw_sha or digest(source/'manifest.json')!=manifest_sha256:
            raise ValueError('Source execution changed during review')
        for path,sha in {**inputs,**{str(ROOT/p):h for p,h in identity['inputs'].items()}}.items():
            if digest(path)!=sha:raise ValueError('Input changed during nominal review: '+path)
    except Exception as error:
        result.update(status='ERROR',reason=type(error).__name__+': '+str(error))
    write_json(output/'nominal_assessment.json',result)
    write_json(output/'review_manifest.json',dict(schema_version=1,status=result['status'],
        assessment_mode='replay',electrical_simulation_performed=False,source_manifest_sha256=manifest_sha256,
        policy_sha256=POLICY_SHA256,inputs=inputs,python=sys.version,
        git=dict(commit=git('rev-parse','HEAD'),branch=git('branch','--show-current'),dirty=bool(git('status','--porcelain'))),
        evidence={str(p.relative_to(output)):digest(p) for p in output.rglob('*') if p.is_file()}))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--manifest-sha256',required=True);args=parser.parse_args()
    try:result=review(args.run,args.output,args.manifest_sha256)
    except (ValueError,FileExistsError,FileNotFoundError) as error:parser.exit(2,str(error)+'\n')
    print(json.dumps({k:result[k] for k in ('status','assessment_mode','electrical_simulation_performed')}))
    raise SystemExit(1)  # No reviewed/approved operational gate or B sign-off exists.
