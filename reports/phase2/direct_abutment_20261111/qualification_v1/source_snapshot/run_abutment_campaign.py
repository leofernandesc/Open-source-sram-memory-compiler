#!/usr/bin/env python3
"""Requalify the NEW extracted abutment candidate using existing C1/C2 criteria.

Explicit inputs replace historical module defaults only in this process.
No baseline selector, old circuit, checker thresholds or phase taps are changed.
"""
import argparse,json,os,re,shutil,subprocess,tempfile
from pathlib import Path
import numpy as np
import run_phase2_startup_review as startup
import phase2_extension as campaign
from run_phase2_digital import ROOT,sha
from phase2_resources import preflight


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--campaign',choices=['sequences','bus','qualification'],required=True)
    p.add_argument('--fixture-report','--access-report',dest='access_report',required=True,type=Path)
    p.add_argument('--gds-report',required=True,type=Path)
    p.add_argument('--design-json',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--timeout',type=int,default=2400)
    a=p.parse_args();source=(ROOT/a.access_report).resolve();gds=(ROOT/a.gds_report).resolve()
    design_path=(ROOT/a.design_json).resolve();out=(ROOT/a.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2/direct_abutment_20261111') or out.exists():
        p.error('Use a new candidate output directory')
    out.mkdir(parents=True)
    profile=a.campaign;protocol='bus' if profile=='qualification' else profile
    record=dict(status='RUNNING',campaign=protocol,profile=profile,condition=dict(corner='tt',vdd_v=1.8,temp_c=27),
                scope='NEW direct-abutment extraction; no old electrical acceptance reused; no wire RC',official_selection_changed=False)
    def publish():
        record['artifacts']={str(q.relative_to(out)):sha(q) for q in out.rglob('*') if q.is_file() and q.name!='results.json'}
        (out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
    publish()
    try:
        record['resources']=preflight(ROOT)
        state=json.loads((source/'results.json').read_text());geometry=json.loads((gds/'results.json').read_text())
        if state['status'] not in ('PREPARED_EXTRACTED_FIXTURE','PASS_EXTRACTED_NOMINAL_ACCESS') or geometry['status']!='PASS_GEOMETRY_LVS':
            raise ValueError('New physical qualification and independently prepared extraction required')
        if state['inputs'].get(str(gds/'results.json'))!=sha(gds/'results.json'):
            raise ValueError('Baseline access did not use this GDS extraction')
        for folder,receipt in [(source,state),(gds,geometry)]:
            for name,h in receipt['artifacts'].items():
                if sha(folder/name)!=h:raise ValueError('Changed new candidate artifact: '+name)
        if [h for n,h in state['inputs'].items() if n.endswith('/routed_reference.json')]!=[sha(design_path)]:
            raise ValueError('New routed design differs from baseline access')
        selected=[source/n for n in ('binding.spice','fabric.spice','bench.spice','results.json')]
        selected += [gds/'final_extracted.spice',gds/'final_flat.ext',gds/'results.json',design_path,Path(__file__)]
        selected += [ROOT/'tools'/n for n in ('phase2_extension.py','run_phase2_startup_review.py',
                    'run_phase2_directed_review.py','phase2_access_checks.py','phase2_resources.py')]
        pinned={str(q):sha(q) for q in selected};pinned.update(state['model_inputs']);startup.verify_pins(pinned)
        # These pure helper functions read module-level paths. Rebind all of
        # them coherently, instead of ever touching historical evidence files.
        startup.SOURCE=campaign.SOURCE=source;startup.GDS=campaign.GDS=gds
        if profile=='qualification':
            # One bounded campaign covers all rows, complementary rewrites,
            # repeated reads, retention, output capture and both handoffs.
            # Reuse bus stimuli/check criteria without changing any threshold.
            sequence=[('idle',0,0),('idle',0,0),('write',0,0xAA),('write',1,0x55),
                      ('write',2,0x0F),('write',3,0xF0),('read',0,0xAA),('read',1,0x55),
                      ('write',0,0x55),('read',0,0x55),('write',1,0xAA),('read',1,0xAA),
                      ('idle',0,0),('read',0,0x55),('read',1,0xAA),('read',2,0x0F),
                      ('read',3,0xF0),('read',3,0xF0)]
            campaign.campaign=lambda name,pilot=False:list(sequence)
        design=json.loads(design_path.read_text())
        vectors,extra=campaign.probes(state,design,protocol=='bus')
        text,records,stop=campaign.deck(protocol,False,state,vectors)
        if re.search(r'(?mi)^\s*\.(ic|nodeset)\b',text):raise ValueError('Internal initialization forbidden')
        build=Path(tempfile.mkdtemp(prefix='abutment-'+a.campaign+'-',dir=ROOT/'build/phase2'))
        (build/'bench.spice').write_text(text)
        for n in ('binding.spice','fabric.spice'):shutil.copyfile(source/n,build/n)
        for n in ('binding.spice','fabric.spice','bench.spice'):shutil.copyfile(build/n,out/n)
        snap=out/'source_snapshot';snap.mkdir()
        for q in selected:
            if q.suffix=='.py':shutil.copyfile(q,snap/q.name)
        record.update(inputs=pinned,model_inputs=state['model_inputs'],build_directory=str(build.relative_to(ROOT)),
                      cycles=records,vectors=vectors,probes=extra,stop_ns=stop,
                      simulation_inputs={n:sha(build/n) for n in ('binding.spice','fabric.spice','bench.spice')})
        publish()
        with (out/'ngspice.txt').open('w') as log:
            result=subprocess.run(['ngspice','-n','-b','bench.spice'],cwd=build,stdout=log,stderr=subprocess.STDOUT,
                                  timeout=a.timeout,env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'))
        record['return_code']=result.returncode
        if result.returncode or 'ngspice-44.2 done' not in (out/'ngspice.txt').read_text():
            raise ValueError('Simulator execution incomplete or failed')
        raw=build/'waveform.dat'
        with raw.open() as f:
            if f.readline().split()!=['time',*vectors]:raise ValueError('Wrong raw columns')
        data=np.loadtxt(raw,skiprows=1)
        checks,ref,metrics=campaign.check(data,records,vectors,extra,state,stop,protocol)
        (out/'checks.json').write_text(json.dumps(dict(checks=checks,capture_reference=ref),indent=2)+'\n')
        startup.verify_pins(pinned)
        for n,h in record['simulation_inputs'].items():
            if sha(build/n)!=h or sha(out/n)!=h:raise ValueError('Simulation input changed')
        np.savetxt(out/'waveform_excerpt.csv',data[::500],delimiter=',',header=','.join(['time_s',*vectors]),comments='')
        record.update(checks=len(checks),failures=sum(c['status']=='FAIL' for c in checks),metrics=metrics,raw_sha256=sha(raw),rows=len(data))
        record['status']='PASS' if checks and not record['failures'] else 'FAIL_ELECTRICAL_SCREEN'
    except subprocess.TimeoutExpired as e:record.update(status='BLOCKED_EXECUTION',error=f'Timeout {e.timeout}s')
    except Exception as e:record.update(status='FAIL_EXECUTION_OR_EVIDENCE',error=str(e))
    publish();print(json.dumps({k:record[k] for k in ('status','checks','failures','error') if k in record},indent=2))
    return 0 if record['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
