#!/usr/bin/env python3
"""Run the complementary keeper-PEX campaigns with at most three single-core jobs.

The complete 16-address-pair canonical TT/SS/FF runs are separate. Deliberate
32 fC boundary points may fail; the queue records measurements, not signoff.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import json
from pathlib import Path
import subprocess
import sys
import run_keeper_pex as study


def acceptable(result):
    """Only the named charge-boundary job may contain an expected rejection."""
    if not result.get('complete') or result.get('returncode')!=0:
        return False
    return result.get('status')=='PASS_EXPERIMENTAL_SCREEN' or (
        result.get('label')=='charge_boundary' and result.get('allow_boundary') is True
        and result.get('status')=='MEASURED_BOUNDARY')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tag',default='20261029')
    p.add_argument('--jobs',type=int,choices=(1,2,3),default=3)
    args=p.parse_args();root=study.pair.ROOT/'sims/row_decoder/results'
    record=root/f'keeper_campaign_queue_{args.tag}.json'
    study.pair.require(not record.exists(),'Use a new tag')
    extra=[name for name in study.POINTS if name not in ('tt','ss','ff')]
    critical=['tt','ss','ff','sf_1.62_-40','fs_1.62_125']
    jobs=[]
    for i in range(3):jobs.append((f'pvt_{i+1}',extra[i*9:(i+1)*9],[]))
    jobs.extend([
        ('charge',critical,['--kind','charge_down','--value','16']),
        ('pullup',critical,['--kind','leak_up','--value','10']),
        ('retention',['tt','ss','ff'],['--kind','leak_down','--value','10','--high-ns','10']),
        ('op',['tt','ss','ff'],['--initialization','op']),
        ('anchored_uic',['tt','ss','ff'],['--initialization','anchored_uic']),
        ('early_charge',critical,['--kind','charge_down','--value','16','--charge-offset-ns','.25']),
        ('charge_boundary',critical,['--kind','charge_down','--value','32','--allow-boundary']),
    ])
    runner=Path(study.__file__).resolve()
    state=dict(status='RUNNING',complete=False,jobs=args.jobs,runner_sha256=study.pair.sha(runner),
        coordinator_sha256=study.pair.sha(Path(__file__)),cases=[])
    record.write_text(json.dumps(state,indent=2)+'\n')
    (root/f'keeper_campaign_queue_{args.tag}_script.py').write_bytes(Path(__file__).read_bytes())
    def execute(job):
        label,profiles,options=job;out=root/f'keeper_pex_{label}_{args.tag}'
        command=[sys.executable,str(runner),'--profiles',*profiles,'--transitions','1:2',
                 *options,'--output-dir',str(out)]
        process=subprocess.run(command,cwd=study.pair.ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        (root/f'keeper_pex_{label}_{args.tag}_console.txt').write_text(process.stdout)
        path=out/'manifest.json';manifest=json.loads(path.read_text()) if path.exists() else {}
        return dict(label=label,returncode=process.returncode,profiles=profiles,command=command,
            complete=manifest.get('complete',False),status=manifest.get('status','NO_RESULT'),
            allow_boundary=manifest.get('allow_boundary',False),
            manifest=str(path.relative_to(study.pair.ROOT)),manifest_sha256=study.pair.sha(path) if path.exists() else None)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for future in as_completed([pool.submit(execute,job) for job in jobs]):
            result=future.result();state['cases'].append(result)
            record.write_text(json.dumps(state,indent=2)+'\n');print(result['label'],result['status'],flush=True)
    success=len(state['cases'])==len(jobs) and all(acceptable(r) for r in state['cases'])
    state.update(complete=success,status='COMPLETED_MEASUREMENTS' if success else 'ERROR')
    record.write_text(json.dumps(state,indent=2)+'\n')
    return 0 if success else 1


if __name__=='__main__':raise SystemExit(main())
