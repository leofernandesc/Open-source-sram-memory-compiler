#!/usr/bin/env python3
"""Recheck retained timing-campaign integrity; intentional rejects are data."""
import csv
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
RESULTS=HERE.parent
CAMPAIGNS={
    'canonical_timing_frontend_pilot_20261028':{('ss',1,2,v) for v in (0,250)},
    'canonical_address_limits_20261028':{(p,a,b,v) for p in ('ss','ff')
        for a,b in ((0,3),(3,0),(1,2),(2,1)) for v in (250,500,1000,1500)},
    'canonical_precharge_limits_20261028':{('ss',a,a,v) for a in range(4)
        for v in (0.25,0.5,1,1.5,2)},
    'canonical_evaluation_limits_20261028':{('ss',1,2,v) for v in (0.7,1,1.3,2)},
    'canonical_retention_limits_20261028':{('ff',1,2,v) for v in (20,50)},
    **{name:{(p,a,b,0) for p in ('ss','tt','ff')
            for a,b in ((0,3),(3,0),(1,2),(2,1))}
       for name in ('canonical_contract_candidate_20261028','canonical_contract_robust_20261028')},
    **{f'canonical_contract_robust_{p}_remaining_20261028':{(p,a,b,0)
       for a in range(4) for b in range(4) if (a,b) not in ((0,3),(3,0),(1,2),(2,1))}
       for p in ('ss','tt')},
    **{f'canonical_contract_robust_ff_remaining_{part}_20261028':{('ff',a,b,0) for a,b in pairs}
       for part,pairs in dict(a=((0,0),(0,1),(0,2),(1,0)),
                             b=((1,1),(1,3),(2,0),(2,2)),
                             c=((2,3),(3,1),(3,2),(3,3))).items()},
}


def require(condition,message):
    if not condition:raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def csv_rows(path):
    with path.open() as handle:return list(csv.DictReader(handle))


def inspect():
    summaries=[];counts=dict(cases=0,timing_pass=0,timing_fail=0,checks_pass=0,checks_fail=0)
    pinned=json.loads((ROOT/'sims/row_decoder/inputs/canonical_row_load_20261028.provenance.json').read_text())['sha256']
    for name,expected in CAMPAIGNS.items():
        directory=RESULTS/name;m=json.loads((directory/'manifest.json').read_text())
        require(m['complete'] and m['errors']==0 and m['status']=='COMPLETE_BOUNDARY_SCREEN',f'{name}: incomplete')
        observed={(r['profile'],r['old'],r['new'],r['value']) for r in m['cases']}
        require(observed==expected and len(m['cases'])==len(expected),f'{name}: wrong case coverage')
        require(sha(directory/'executed_script.py')==m['runner_sha256'],f'{name}: changed runner snapshot')
        for helper,digest in m['helper_sha256'].items():
            require(sha(directory/'helper_snapshots'/helper)==digest,f'{name}: changed helper {helper}')
        require(m['row_load']['sha256']==pinned,f'{name}: wrong row-load evidence')
        for leaf,info in m['inputs'].items():
            require(sha(ROOT/info['path'])==info['sha256'],f'{name}: changed PEX {leaf}')
        passing=0;failing=0
        for row in m['cases']:
            case=directory/row['case']
            require(row['status']=='MEASURED',f'{case}: simulator error')
            require(json.loads((case/'result.json').read_text())==row,f'{case}: result/manifest mismatch')
            require(sha(case/'case.spice')==row['deck_sha256'],f'{case}: changed deck')
            log=(case/'ngspice.txt').read_text()
            require(re.search(r'(?m)^TIMING_LIMITS_NUM_THREADS=1\s*$',log),f'{case}: missing thread marker')
            require(not re.search(r'(?i)warning|error:|aborted|timestep too small',log),f'{case}: simulator diagnostic')
            checks=csv_rows(case/'checks.csv')
            statuses=[]
            for check in checks:
                status='PASS' if float(check['min'])<=float(check['value'])<=float(check['max']) else 'FAIL'
                require(status==check['status'],f'{case}: inconsistent check status')
                statuses.append(status)
            passed=statuses.count('PASS');failed=statuses.count('FAIL')
            require((passed,failed)==(row['checks_pass'],row['checks_fail']),f'{case}: check count mismatch')
            require(row['timing_screen']==('FAIL' if failed else 'PASS'),f'{case}: incorrect timing conclusion')
            extrema=csv_rows(case/'bias_extrema.csv')
            for bias in extrema:
                maximum=max(abs(float(bias['min_v'])),abs(float(bias['max_v'])))
                require(abs(maximum-float(bias['abs_max_v']))<1e-12,f'{case}: inconsistent bias magnitude')
            peak=max(float(b['abs_max_v']) for b in extrema)
            require(abs(peak-row['worst_external_bias']['abs_max_v'])<1e-12,f'{case}: inconsistent worst bias')
            require(row['voltage_screen']==('PASS' if peak<=1.95 else 'REVIEW_REQUIRED'),f'{case}: wrong voltage conclusion')
            if name.startswith('canonical_contract_'):
                literals=csv_rows(case/'literal_settling.csv')
                measured=min(float(r['stable_lead_ps']) for r in literals)
                check=next(r for r in checks if r['check']=='all_literals_stable_lead_ps')
                require(abs(measured-float(check['value']))<1e-9,f'{case}: inconsistent literal guard')
            waveform=csv_rows(case/'waveforms.csv');times=[float(r['time']) for r in waveform]
            require(4<=len(times)<=1800 and all(a<b for a,b in zip(times,times[1:])),f'{case}: invalid plot samples')
            counts['cases']+=1;counts['checks_pass']+=passed;counts['checks_fail']+=failed
            passing+=not failed;failing+=bool(failed)
        require((passing,failing)==(m['timing_pass'],m['timing_fail']),f'{name}: wrong summary')
        counts['timing_pass']+=passing;counts['timing_fail']+=failing
        summaries.append(dict(campaign=name,cases=len(expected),timing_pass=passing,timing_fail=failing,
                              manifest_sha256=sha(directory/'manifest.json')))
    # The frozen physical package must remain byte-identical throughout this study.
    frozen=json.loads((ROOT/'release/phase1/checksums.json').read_text())
    for path,digest in frozen.items():require(sha(ROOT/path)==digest,f'Changed frozen file: {path}')
    report=dict(status='PASS_EVIDENCE_INTEGRITY',scope='Artifact consistency, coverage and recorded threshold decisions; not independent raw-transient reanalysis or timing/model signoff.',
                inspect_script_sha256=sha(Path(__file__)),frozen_files_unchanged=len(frozen),campaigns=summaries,**counts)
    (HERE/'evidence_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    files=[p for name in CAMPAIGNS for p in (RESULTS/name).rglob('*') if p.is_file()]
    files += [p for p in HERE.rglob('*') if p.is_file() and p.name!='checksums.json' and '__pycache__' not in p.parts]
    require(not any(p.suffix=='.raw' for p in files),'Unexpected retained raw transient')
    (HERE/'checksums.json').write_text(json.dumps({str(p.relative_to(ROOT)):sha(p) for p in sorted(files)},indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    try:inspect()
    except Exception as error:
        (HERE/'evidence_audit.json').write_text(json.dumps(dict(status='FAIL',error=str(error)),indent=2)+'\n')
        raise
