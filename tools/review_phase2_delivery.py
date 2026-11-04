#!/usr/bin/env python3
"""Read-only handoff audit: recorded seals, inventory, Git selection and links.

Does not run SPICE, route, DRC or LVS. Original raw-dependent audits remain
separate; this command checks identities and accessibility of delivered proof.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while chunk := f.read(1024*1024): h.update(chunk)
    return h.hexdigest()


def verify_entries(record, root=ROOT):
    """Require every referenced delivery payload to match, including byte count."""
    found = []
    def walk(value):
        if isinstance(value, dict):
            if 'path' in value and 'sha256' in value:
                p = (root/value['path']).resolve()
                if not p.is_relative_to(root) or not p.is_file() or digest(p) != value['sha256']:
                    raise ValueError('Changed/missing delivery payload: '+value['path'])
                if 'bytes' in value and p.stat().st_size != value['bytes']:
                    raise ValueError('Delivery byte count differs: '+value['path'])
                found.append(value['path'])
            for item in value.values(): walk(item)
        elif isinstance(value, list):
            for item in value: walk(item)
    walk(record)
    if not found: raise ValueError('Empty delivery manifest')
    return found


def classify(name, selected):
    if name.startswith(('build/',)) or '/local/' in name or name.endswith('.run.lock'):
        return 'D', 'Regenerable local intermediate; excluded from Git'
    if name in selected:
        return ('B', 'Selected delivered physical/electrical view') if name.endswith(('.gds','.mag','.lef','.def','.spice','.v')) else ('C', 'Sealed selected evidence')
    if name.startswith('reports/'):
        return ('C', 'Selected review evidence') if any(s in name for s in ('review_20261104/','final_polish_20261104/','phase2_review_20261104/')) else ('E', 'Preserved development/historical checkpoint; not a new acceptance claim')
    if name.startswith('physical/phase2/history/'):
        return 'E', 'Prior selector/identity record'
    if name.startswith('presentations/'):
        return 'B', 'Selected presentation source, figures or review export'
    return 'A', 'Source/configuration/documentation required for reconstruction or review'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    p.add_argument('--require-versioned', action='store_true')
    args = p.parse_args(); out = (ROOT/args.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2/local') or out.exists():
        p.error('Use a new directory under reports/phase2/local')
    out.mkdir(parents=True)
    result = {'status': 'RUNNING', 'scope': 'Payload identity and publication selection; no fresh electrical/physical qualification'}
    try:
        selected = set()
        for rel, key in [('reports/phase2/review_20261104/acceptance/results.json','verified_files'),
                         ('reports/phase2/final_polish_20261104/final_state.json','files')]:
            state = json.loads((ROOT/rel).read_text())
            for name, expected in state[key].items():
                if digest(ROOT/name) != expected: raise ValueError('Historical seal changed: '+name)
                selected.add(name)
        manifest = json.loads((ROOT/'physical/phase2/delivery.json').read_text())
        delivered = verify_entries(manifest); selected.update(delivered)
        previous = json.loads((ROOT/'reports/phase2/final_polish_20261104/startup_verification/results.json').read_text())
        if previous['status'] != 'PASS' or previous['checks'] != 3383 or previous['read_bit_checks'] != 240:
            raise ValueError('Startup summary differs')
        staged = set(subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines())
        candidates = set(subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines())
        include = sorted(n for n in staged | candidates if n in selected or n.startswith(('reports/phase2/','reports/digital/phase2_','physical/phase2/','synth/','verification/phase2/','presentations/phase2/','release/phase2_experimental/')) or n in ('README.md','.gitignore') or n.startswith(('docs/phase2','tools/phase2','tools/run_phase2','tools/review_phase2','tools/verify_phase2','tools/analyze_phase2','tools/plot_phase2','tools/package_phase2','tools/pack_phase2','tools/finish_phase2','tools/export_phase2','tools/tests/test_phase2','scripts/run_phase2','scripts/run_synth','scripts/reproduce_phase2','specs/phase2','specs/sram_4x8_timing','rtl/','tb/','scripts/run_rtl','tools/run_digital_regression','tools/sram-eda','tools/tests/test_digital','tools/audit_phase2','tools/bundle_phase2','tools/ENVIRONMENT','specs/technical_specification','specs/sram_4x8_digital')))
        include = [n for n in include if n != 'release/phase2_experimental/inventory.json']
        ignored = subprocess.run(['git','check-ignore','--stdin'],cwd=ROOT,input='\n'.join(selected)+'\n',capture_output=True,text=True).stdout.splitlines()
        if ignored: raise ValueError('Mandatory evidence hidden by gitignore: '+str(ignored))
        if args.require_versioned and not selected <= staged:
            raise ValueError('Mandatory evidence not versioned: '+str(sorted(selected-staged)))
        inventory = []
        secrets = re.compile(rb'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
        for name in include:
            path = ROOT/name
            if not path.is_file(): raise ValueError('Missing inventory file: '+name)
            content = path.read_bytes()
            if secrets.search(content): raise ValueError('Credential-like content in '+name)
            if len(content) > 50*2**20: raise ValueError('Oversized publication file: '+name)
            kind, reason = classify(name, selected)
            inventory.append(dict(path=name,category=kind,reason=reason,bytes=len(content),sha256=digest(path),versioned=name in staged))
        link_errors = []
        documents = [ROOT/'README.md',*ROOT.glob('docs/phase2*.md'),ROOT/'specs/sram_4x8_timing_contract.md',*ROOT.glob('presentations/phase2/*.md'),*ROOT.glob('release/phase2_experimental/*.md')]
        for doc in documents:
            for target in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
                if '://' in target or target.startswith(('#','mailto:')): continue
                target = target.split('#')[0]
                if target and not (doc.parent/target).resolve().exists(): link_errors.append(f'{doc.relative_to(ROOT)}: {target}')
        if link_errors: raise ValueError('Broken document links: '+str(link_errors))
        (out/'inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
        result.update(status='PASS',delivery_entries=len(delivered),selected_sealed_files=len(selected),inventory_files=len(inventory),
                      excluded_regenerable_groups={'build/phase2/':'D: route databases, raw caches, optional bundle and local presentation packages','build/presentations/':'D: office profile and preview renders','reports/phase2/local/':'D: fresh review/reproduction candidates'},
                      categories=dict(Counter(i['category'] for i in inventory)),inventory_sha256=digest(out/'inventory.json'),
                      branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
                      head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                      credentials_scan='No matching token/private-key pattern; manual scope review still required',
                      startup_checks=previous['checks'],read_bit_checks=previous['read_bit_checks'],versioned_gate=args.require_versioned)
    except Exception as error: result.update(status='FAIL',error=str(error))
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__': raise SystemExit(main())
