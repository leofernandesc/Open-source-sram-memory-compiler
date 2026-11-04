#!/usr/bin/env python3
"""Run one of two incremental nominal campaigns, preserving every DUT MOS."""
import argparse,json,os,re,shutil,subprocess,tempfile
from pathlib import Path
import numpy as np
from run_phase2_digital import ROOT,sha
from run_digital_regression import atomic_text
from phase2_resources import preflight
from run_phase2_startup_review import SOURCE,GDS,verify_pins
from phase2_extension import probes,deck,check


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--campaign',choices=['sequences','bus'],required=True);p.add_argument('--pilot',action='store_true');p.add_argument('--output',required=True);p.add_argument('--timeout',type=int,default=2400);args=p.parse_args()
    out=(ROOT/args.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2') or out.exists():p.error('Use a new report directory under reports/phase2')
    out.mkdir(parents=True);r=dict(status='RUNNING',campaign=args.campaign,pilot=args.pilot,condition=dict(corner='tt',vdd_v=1.8,temp_c=27),scope='Unchanged 1493-MOS extracted DUT, no wire RC; optional external current meters')
    def publish():atomic_text(out/'results.json',json.dumps(r,indent=2)+'\n')
    publish()
    try:
        r['resources']=preflight(ROOT);state=json.loads((SOURCE/'results.json').read_text());seal=json.loads((ROOT/'reports/phase2/review_20261104/acceptance/results.json').read_text())
        selected=[SOURCE/'binding.spice',SOURCE/'fabric.spice',SOURCE/'bench.spice',SOURCE/'results.json',GDS/'final_extracted.spice',GDS/'final_flat.ext']
        for s in selected:
            if seal['verified_files'][str(s.relative_to(ROOT))]!=sha(s):raise ValueError('Selected circuit/evidence changed')
        design_path=ROOT/'reports/phase2/portable_raw/routed_reference.json';design=json.loads(design_path.read_text())
        if [h for n,h in state['inputs'].items() if n.endswith('/routed_reference.json')]!=[sha(design_path)]:raise ValueError('Routed design differs')
        source_files=[*selected,design_path,Path(__file__),ROOT/'tools/phase2_extension.py',ROOT/'tools/run_phase2_startup_review.py',ROOT/'tools/run_phase2_directed_review.py',ROOT/'tools/phase2_access_checks.py',ROOT/'tools/phase2_resources.py']
        pinned={str(s):sha(s) for s in source_files};pinned.update(state['model_inputs']);verify_pins(pinned)
        vectors,extra=probes(state,design,args.campaign=='bus');text,records,stop=deck(args.campaign,args.pilot,state,vectors)
        if re.search(r'(?mi)^\s*\.(ic|nodeset)\b',text):raise ValueError('Internal initialization forbidden')
        build=Path(tempfile.mkdtemp(prefix='extension-'+args.campaign+'-',dir=ROOT/'build/phase2'));(build/'bench.spice').write_text(text)
        for n in ['binding.spice','fabric.spice']:shutil.copyfile(SOURCE/n,build/n)
        for n in ['binding.spice','fabric.spice','bench.spice']:shutil.copyfile(build/n,out/n)
        snap=out/'source_snapshot';snap.mkdir()
        for s in source_files:
            if s.suffix=='.py':shutil.copyfile(s,snap/s.name)
        r.update(inputs=pinned,build_directory=str(build.relative_to(ROOT)),cycles=records,vectors=vectors,probes=extra,stop_ns=stop,
                 simulation_inputs={n:sha(build/n) for n in ['binding.spice','fabric.spice','bench.spice']});publish()
        with (out/'ngspice.txt').open('w') as log:
            run=subprocess.run(['ngspice','-n','-b','bench.spice'],cwd=build,stdout=log,stderr=subprocess.STDOUT,timeout=args.timeout,env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'))
        r['return_code']=run.returncode
        if run.returncode or not (build/'waveform.dat').exists():raise ValueError('Simulator execution failed')
        raw=build/'waveform.dat'
        with raw.open() as f:
            if f.readline().split()!=['time',*vectors]:raise ValueError('Raw header differs')
        data=np.loadtxt(raw,skiprows=1);checks,reference,metrics=check(data,records,vectors,extra,state,stop,args.campaign)
        (out/'checks.json').write_text(json.dumps(dict(checks=checks,capture_reference=reference),indent=2)+'\n')
        verify_pins(pinned)
        for n,h in r['simulation_inputs'].items():
            if sha(build/n)!=h or sha(out/n)!=h:raise ValueError('Input changed during run')
        np.savetxt(out/'waveform_excerpt.csv',data[::500],delimiter=',',header=','.join(['time_s',*vectors]),comments='')
        r.update(checks=len(checks),failures=sum(c['status']=='FAIL' for c in checks),metrics=metrics,raw_sha256=sha(raw),rows=len(data))
        r['status']='PASS' if checks and not r['failures'] else 'FAIL_ELECTRICAL_SCREEN'
    except subprocess.TimeoutExpired as e:r.update(status='BLOCKED_EXECUTION',error=f'Simulator timeout: {e.timeout} s')
    except Exception as e:r.update(status='BLOCKED_RESOURCE' if 'Resource preflight' in str(e) else 'FAIL_EXECUTION_OR_EVIDENCE',error=str(e))
    r['artifacts']={str(s.relative_to(out)):sha(s) for s in out.rglob('*') if s.is_file() and s.name!='results.json'};publish()
    print(json.dumps({k:v for k,v in r.items() if k in ['status','checks','failures','error']},indent=2));return 0 if r['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
