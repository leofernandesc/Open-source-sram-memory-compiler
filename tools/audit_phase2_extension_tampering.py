#!/usr/bin/env python3
"""Deliberate evidence defects in disposable copies; never edit original raws."""
import argparse
import json
import shutil
import tempfile
from pathlib import Path
from run_phase2_digital import ROOT,sha
from verify_phase2_extension import verify_case


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    source=ROOT/a.source;out=(ROOT/a.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2') or out.exists():p.error('Use a new report directory')
    out.mkdir(parents=True);original={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()}
    result=dict(status='RUNNING',control=verify_case(source),cases=[])
    cases={
      'counter':('Counters/status differ',lambda s,c:s.update(checks=s['checks']+1)),
      'raw_identity':('Raw changed',lambda s,c:s.update(raw_sha256='0'*64)),
      'stimulus':('Declared stimulus',lambda s,c:s['cycles'][2].update(row=3)),
      'missing_required_artifact':('Missing mandatory artifact',lambda s,c:s['artifacts'].pop('checks.json')),
      'changed_circuit':('Changed campaign artifact',lambda s,c:(c/'binding.spice').write_text((c/'binding.spice').read_text()+'\n* deliberate mutation\n')),
      'incomplete_native_log':('Missing native successful',lambda s,c:edit_artifact(s,c,'ngspice.txt',lambda text:text.replace('ngspice-44.2 done','INCOMPLETE'))),
      'checks_after_generation':('Checks differ',lambda s,c:edit_artifact(s,c,'checks.json',lambda text:change_first_check(text))),
      'source_snapshot':('Source snapshot differs',lambda s,c:edit_artifact(s,c,'source_snapshot/phase2_extension.py',lambda text:text+'\n# deliberate mutation\n')),
    }
    for name,(expected,mutate) in cases.items():
        with tempfile.TemporaryDirectory(dir=ROOT/'build/phase2',prefix='extension-mutant-') as tmp:
            copy=Path(tmp)/'evidence';shutil.copytree(source,copy)
            s=json.loads((copy/'results.json').read_text());mutate(s,copy);(copy/'results.json').write_text(json.dumps(s))
            try:verify_case(copy);error='NOT_REJECTED'
            except Exception as exc:error=str(exc)
            result['cases'].append(dict(name=name,status='PASS_REJECTED' if expected in error else 'FAIL',expected=expected,diagnostic=error))
    if original!={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()}:raise ValueError('Original changed')
    result.update(status='PASS' if all(c['status']=='PASS_REJECTED' for c in result['cases']) else 'FAIL',
                  original_receipt_sha256=sha(source/'results.json'),auditor_sha256=sha(Path(__file__)),original_preserved=True)
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0 if result['status']=='PASS' else 1


def edit_artifact(state,copy,name,edit):
    path=copy/name;path.write_text(edit(path.read_text()));state['artifacts'][name]=sha(path)


def change_first_check(text):
    data=json.loads(text);data['checks'][0]['status']='FAIL';return json.dumps(data)


if __name__=='__main__':raise SystemExit(main())
