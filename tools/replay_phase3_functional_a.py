#!/usr/bin/env python3
"""Read-only, pinned offline A assessment. Never runs ngspice; never approves A."""
import argparse
import json
from pathlib import Path
import shutil
import sys
from phase2_evidence import digest
from phase3.runner import ROOT, write_json, git
from phase3.provenance import selected_inputs
from phase3.functional_a import context_for, replay


def review(source, output, manifest_sha256):
    source, output = Path(source).resolve(), Path(output).resolve()
    if not output.is_relative_to(ROOT/'reports/phase3') or output == ROOT/'reports/phase3':
        raise ValueError('Use a new directory below reports/phase3')
    if digest(source/'manifest.json') != manifest_sha256:
        raise ValueError('Replay manifest hash differs')
    output.mkdir(parents=True)  # Never overwrite even a failed assessment.
    result = dict(schema_version=1, assessment_mode='replay', status='ERROR',
                  electrical_simulation_performed=False, sram_characterized=False)
    inputs = {}
    try:
        sources = [*Path(__file__).with_name('phase3').glob('*.py'), Path(__file__),
                   *[ROOT/'tools'/name for name in ('phase2_extension.py','phase2_access_checks.py',
                     'run_phase2_startup_review.py','analyze_phase2_extension_timing.py','phase2_evidence.py')]]
        for source_file in sources:
            target=output/'source_snapshot'/source_file.relative_to(ROOT)
            target.parent.mkdir(parents=True,exist_ok=True)
            inputs[str(source_file)]=digest(source_file)
            shutil.copyfile(source_file,target)
        manifest = json.loads((source/'manifest.json').read_text())
        c = manifest['configuration']
        context = context_for(c['baseline'], selected_inputs(ROOT, c['baseline']),
                              {k:c[k] for k in ('deck','netlist','model')})
        write_json(output/'context.json', context)
        result.update(replay(ROOT, source, context, manifest_sha256))
        if 'legacy_comparison' in result:
            write_json(output/'legacy_comparison.json', result['legacy_comparison'])
        for path,sha in inputs.items():
            if digest(path)!=sha: raise ValueError('Replay code changed: '+path)
    except Exception as error:
        result.update(status='ERROR', reason=type(error).__name__+': '+str(error))
    write_json(output/'functional_a_checks.json', result)
    write_json(output/'assessment_manifest.json', dict(schema_version=1, status=result['status'],
        assessment_mode='replay', electrical_simulation_performed=False,
        source_manifest_sha256=manifest_sha256,
        inputs=inputs, tools=dict(python=sys.version),
        git=dict(commit=git('rev-parse','HEAD'),branch=git('branch','--show-current'),dirty=bool(git('status','--porcelain'))),
        evidence={str(p.relative_to(output)):digest(p) for p in output.rglob('*') if p.is_file()}))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--manifest-sha256', required=True)
    args=parser.parse_args()
    try:
        result=review(args.run,args.output,args.manifest_sha256)
    except (ValueError,FileExistsError,FileNotFoundError) as error:
        parser.exit(2,str(error)+'\n')
    print(json.dumps({k:result[k] for k in ('status','assessment_mode','electrical_simulation_performed')}))
    raise SystemExit(1)  # The complete A gate is deliberately unavailable.
