#!/usr/bin/env python3
"""Exercise real G7 checkpoints: correct case reused, wrong case resimulated."""
import argparse
import csv
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def table(path):
    with path.open() as stream:return list(csv.DictReader(stream))


def require(good,message):
    if not good:raise ValueError(message)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True)
    out=p.parse_args().output_dir.resolve();require(out.is_relative_to(ROOT),'Record evidence in this checkout')
    require(not out.exists(),'Use a fresh output directory');out.mkdir(parents=True)
    historical=ROOT/'sims/integration/results/reconciliation_v2_20261030/manifest.json'
    selected=json.loads(historical.read_text())['commands'][:2]
    record=out/'manifest.json'
    result=dict(status='RUNNING',complete=False,started_utc=datetime.now(timezone.utc).isoformat(),
        scope='Checkpoint identity regression, one TT/1.8 V/27 C/state 0 read and write case; not a new PVT qualification.',
        runner_sha256=sha(Path(__file__)),historical_command_manifest_sha256=sha(historical),commands=[])
    (out/'executed_script.py').write_bytes(Path(__file__).read_bytes())
    snapshots=out/'sources';snapshots.mkdir()
    for name in ('run_integrated_column_read.py','run_integrated_column_write.py','qualification_contract.py','pex_access_nodes.py'):
        shutil.copy2(ROOT/'sims'/name,snapshots/name)
    result['source_sha256']={p.name:sha(p) for p in snapshots.iterdir()}
    def save():record.write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        for original in selected:
            label=original['label'];folder=out/label;folder.mkdir()
            command=original['argv'].copy();command[0]=sys.executable
            command[1]=str(ROOT/'sims'/Path(command[1]).name)
            command[command.index('--parts-dir')+1]=str(folder/'parts')
            command+=['--corners','tt','--vdd-values','1.8','--temps-c','27','--states','0']
            state='stored_q' if label=='g7_read' else 'stored_q_before'
            expected=None
            for stage in ('fresh','reuse','wrong_case'):
                current=command.copy();output=folder/(stage+'.csv');current[current.index('--output')+1]=str(output)
                if stage!='fresh':current+=['--resume']
                if stage=='wrong_case':
                    part=next((folder/'parts').glob('*.csv'));row=table(part)[0]
                    row['corner']='ss'
                    with part.open('w',newline='') as handle:
                        writer=csv.DictWriter(handle,fieldnames=list(row),lineterminator='\n');writer.writeheader();writer.writerow(row)
                    shutil.copy2(part,folder/'injected_wrong_case.csv')
                process=subprocess.run(current,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
                console=folder/(stage+'_console.txt');console.write_text(process.stdout)
                entry=dict(label=label,stage=stage,argv=current,returncode=process.returncode,status='FAIL',
                           console_sha256=sha(console))
                result['commands'].append(entry);save()
                require(process.returncode==0 and output.exists(),'G7 runner failed')
                rows=table(output);require(len(rows)==1 and rows[0]['status']=='PASS','No passing single case')
                row=rows[0]
                require(row['corner']=='tt' and float(row['vdd_v'])==1.8 and float(row['temp_c'])==27 and row[state]=='0',
                        'Wrong row was accepted')
                if stage=='reuse':require('resume: 1/1 PASS parts reused; 0 cases pending' in process.stdout,'Correct row not reused')
                if stage=='wrong_case':require('resume: 0/1 PASS parts reused; 1 cases pending' in process.stdout,'Wrong row reused')
                if expected is None:expected=row
                else:require(row==expected,'Reproduction differs after checkpoint reuse/resimulation')
                entry.update(status='PASS',output_sha256=sha(output),cache_contract_sha256=row['cache_contract_sha256']);save()
                print(label,stage,'PASS',flush=True)
        result.update(status='PASS',complete=True,fresh_spice_runs=4,correct_cache_hits=2,rejected_wrong_cases=2)
    except Exception as error:
        result.update(status='FAIL',error=f'{type(error).__name__}: {error}')
        raise
    finally:
        result['finished_utc']=datetime.now(timezone.utc).isoformat()
        result['artifact_sha256']={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p!=record}
        save()


if __name__=='__main__':main()
