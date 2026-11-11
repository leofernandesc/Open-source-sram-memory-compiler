#!/usr/bin/env python3
"""Repeat a nominal small-signal PEX failure with original and refined solver steps.

This preserves the circuit, sources, loads and functional acceptance criteria.
Execution success does not mean functional PASS: inspect functional_status.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import numpy as np

from phase2_resources import preflight
from run_phase1_final_isolated import ROOT, sha, read_data, evaluate, verify, write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args();source=args.evidence.resolve();out=args.output.resolve()
    if not out.is_relative_to(ROOT/'reports/phase1'):p.error('Output under reports/phase1 required')
    verify(source)
    selected=json.loads((source/'results.json').read_text())
    item=next(x for x in selected['cases'] if x['case']['id']=='sa_pex_d5_p+1_c2')
    original=source/item['case']['id']
    out.mkdir(parents=True,exist_ok=False)
    report=dict(execution_status='RUNNING',functional_status='NOT_EVALUATED',
                inputs={str(p.relative_to(ROOT)):sha(p) for p in (source/'results.json',original/'dut.spice',original/'bench.spice',Path(__file__),ROOT/'tools/run_phase1_final_isolated.py')},
                case=item['case'],repetitions=[])
    write_json(out/'results.json',report)
    try:
        for label,step,reltol in (('repeat_5ps',5,'1e-5'),('refined_1ps',1,'1e-6')):
            resources=preflight(ROOT);folder=out/label;folder.mkdir()
            shutil.copyfile(original/'dut.spice',folder/'dut.spice')
            deck=(original/'bench.spice').read_text()
            if step!=5:
                deck=deck.replace('tran 5p 18n 0 5p',f'tran {step}p 18n 0 {step}p')
                deck=deck.replace('reltol=1e-5',f'reltol={reltol}')
            (folder/'bench.spice').write_text(deck)
            with (folder/'ngspice.txt').open('w') as log:
                run=subprocess.run(['ngspice','-n','-b','bench.spice'],cwd=folder,stdout=log,stderr=subprocess.STDOUT,
                                   timeout=120,env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1'))
            raw=folder/'waveform.dat'
            if run.returncode or not raw.exists():raise ValueError('Simulation execution failed')
            payload=raw.read_bytes()
            with (folder/'waveform.dat.gz').open('wb') as f:
                with gzip.GzipFile(fileobj=f,mode='wb',filename='',mtime=0) as g:g.write(payload)
            raw.unlink()
            data=read_data(folder/'waveform.dat.gz')
            native=(folder/'ngspice.txt').read_text()
            if f'No. of Data Rows : {len(data)}' not in native:raise ValueError('Native log/row count mismatch')
            checks=evaluate(item['case'],data,item['stop_ns']);write_json(folder/'checks.json',checks)
            t=data[:,0]*1e9
            snapshots=[dict(time_ns=time,sclk_v=float(np.interp(time,t,data[:,4])),
                            sa_out_v=float(np.interp(time,t,data[:,5])),sa_outb_v=float(np.interp(time,t,data[:,6])),
                            delta_out_v=float(np.interp(time,t,data[:,5]-data[:,6])))
                       for time in (4.9,5,5.025,5.05,5.1,5.2,5.5,8.5)]
            report['repetitions'].append(dict(name=label,returncode=run.returncode,resources=resources,
                                              step_ps=step,reltol=reltol,functional_status=checks['status'],
                                              first_event=checks['metrics'][0],snapshots=snapshots,
                                              uncompressed_waveform_sha256=hashlib.sha256(payload).hexdigest()))
            write_json(out/'results.json',report)
        wrong=[x['first_event']['sa_out_v'] < .18 and x['first_event']['sa_outb_v'] > 1.62
               and x['functional_status']=='FAIL' for x in report['repetitions']]
        report.update(execution_status='COMPLETED',functional_status='FAIL_REPRODUCED' if all(wrong) else 'INCONCLUSIVE',
                      artifacts={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='results.json'})
    except Exception as exc:
        report.update(execution_status='FAIL_EXECUTION',error=f'{type(exc).__name__}: {exc}')
        raise
    finally:write_json(out/'results.json',report)
    print(json.dumps({k:report[k] for k in ('execution_status','functional_status')}))


if __name__=='__main__':main()
