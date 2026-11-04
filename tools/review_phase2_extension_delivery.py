#!/usr/bin/env python3
"""Seal/verify incremental artifacts and unchanged historical inputs, no EDA."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'reports/phase2/extension_20261104'
MANIFEST=REPORT/'manifest.json'


def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(1024*1024):h.update(b)
    return h.hexdigest()


def selected_files():
    for directory in (REPORT,ROOT/'presentations/phase2/extension_20261104'):
        for p in directory.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p!=MANIFEST:yield p
    for name in ('phase2_coverage_extension.md','phase2_timing_extension.md','phase2_team_review_checklist.md','phase2_extension_state_20261104.md'):yield ROOT/'docs'/name
    for name in ('phase2_extension.py','run_phase2_extension.py','verify_phase2_extension.py',
      'analyze_phase2_extension_timing.py','audit_phase2_extension_tampering.py',
      'review_phase2_extension_structure.py','plot_phase2_extension.py',
      'bundle_phase2_extension_raw.py','review_phase2_extension_delivery.py','tests/test_phase2_extension.py'):yield ROOT/'tools'/name


def verify(require_versioned=False):
    m=json.loads(MANIFEST.read_text())
    for rel,h in m['files'].items():
        path=(ROOT/rel).resolve()
        if not path.is_relative_to(ROOT) or digest(path)!=h:raise ValueError('Changed/missing extension artifact: '+rel)
    initial=json.loads((REPORT/'initial.json').read_text())
    for rel,h in initial['baseline_files'].items():
        if digest(ROOT/rel)!=h:raise ValueError('Historical input changed: '+rel)
    for rel,key in [('reports/phase2/review_20261104/acceptance/results.json','verified_files'),
                    ('reports/phase2/final_polish_20261104/final_state.json','files')]:
        r=json.loads((ROOT/rel).read_text())
        for path,h in r[key].items():
            if digest(ROOT/path)!=h:raise ValueError('Prior seal differs: '+path)
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    tracked=set(subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines())
    if require_versioned and not set([*m['files'],str(MANIFEST.relative_to(ROOT))]).issubset(tracked):raise ValueError('Extension input not versioned')
    errors=[]
    for rel in m['files']:
        path=ROOT/rel
        if path.suffix=='.md':
            text=path.read_text()
            for target in re.findall(r'\]\(([^)]+)\)',text):
                if re.match(r'^(https?:|mailto:|#)',target):continue
                dest=target.split('#')[0]
                if dest and not (path.parent/dest).exists():errors.append(rel+': '+dest)
        if path.suffix in ('.py','.md','.json','.spice','.txt'):
            if re.search(r'(?m)-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{25,}',path.read_text(errors='replace')):raise ValueError('Credential-like text in '+rel)
    if errors:raise ValueError('Broken relative links: '+str(errors))
    return dict(status='PASS_EXTENSION_IDENTITIES',files=len(m['files']),historical_inputs_preserved=len(initial['baseline_files']),
                circuit='Unchanged 1493-MOS selected DUT and frozen Phase 1 artifacts',branch=branch,
                manifest_sha256=digest(MANIFEST),scope='Identity, Git selection, local links and token-pattern scan; raw reanalysis separate')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--seal',action='store_true');p.add_argument('--require-versioned',action='store_true');p.add_argument('--output',required=True);a=p.parse_args();out=(ROOT/a.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2/local') or out.exists():p.error('New directory under reports/phase2/local required')
    out.mkdir(parents=True)
    try:
        if a.seal:
            if MANIFEST.exists():raise ValueError('Manifest already exists; preserve it')
            files=sorted(set(selected_files()));MANIFEST.write_text(json.dumps(dict(
                baseline_commit='4ffbbf571bdff1c995de5bd2815083b3a0eda3d0',
                scope='Incremental Phase 2 extension only; earlier release manifests unchanged',
                files={str(path.relative_to(ROOT)):digest(path) for path in files}),indent=2)+'\n')
        result=verify(a.require_versioned)
    except Exception as error:result=dict(status='FAIL_OR_INCOMPLETE',error=str(error))
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0 if result['status']=='PASS_EXTENSION_IDENTITIES' else 1


if __name__=='__main__':raise SystemExit(main())
