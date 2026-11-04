#!/usr/bin/env python3
"""Power-aware functional GLS of the actual OpenROAD delivered netlist.

The fabric substitute is verification-only; this is not an electrical test.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from run_digital_regression import atomic_text, output_lock
from run_phase2_digital import MODELS, ROOT, sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--layout-report',default='reports/phase2/integrated_import_fix')
    p.add_argument('--output',default='reports/phase2/routed_gls')
    a=p.parse_args();out=(ROOT/a.output).resolve();source=(ROOT/a.layout_report).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2') or out==ROOT/'reports/phase2':p.error('Output under reports/phase2 required')
    if out==source:p.error('Output cannot replace the layout input')
    out.mkdir(parents=True,exist_ok=True)
    with output_lock(out):
        result={'status':'RUNNING','F2_FIS':'NOT_EVALUATED',
                'scope':'Actual routed, powered HD netlist, zero-delay GLS with verification-only fabric substitute'}
        def publish():atomic_text(out/'results.json',json.dumps(result,indent=2)+'\n')
        publish()
        try:
            receipt=json.loads((source/'results.json').read_text())
            if receipt['status'] not in ('LAYOUT_MATCH_REIMPORT_PENDING','PASS_GEOMETRY_LVS'):
                raise ValueError('Require completed routed layout DRC/LVS before selected GLS')
            build=Path(tempfile.mkdtemp(prefix='routed-gls-',dir=ROOT/'build/phase2'))
            sources=[source/'final_powered.v',ROOT/'verification/phase2/leaf_fabric_model.v',
                     ROOT/'tb/sram_ref_model.sv',ROOT/'tb/tb_sram_4x8.sv',*MODELS]
            result.update(build_directory=str(build.relative_to(ROOT)),
                          inputs={str(s):sha(s) for s in sources},layout_receipt_sha256=sha(source/'results.json'))
            snapshots=[]
            for s in sources:
                target=build/s.name;shutil.copyfile(s,target);snapshots.append(target)
            command=['iverilog','-g2012','-DFUNCTIONAL','-DUSE_POWER_PINS','-DUNIT_DELAY=#0','-DTEST_WRAPPER',
                     *snapshots,'-s','tb_sram_4x8','-o',build/'routed.vvp']
            for argv,name in [(command,'compile.txt'),
                              (['vvp',build/'routed.vvp','+seed=23063','+random_ops=2048'],'gls.txt')]:
                run=subprocess.run([str(v) for v in argv],cwd=build,capture_output=True,text=True,timeout=120)
                atomic_text(out/name,run.stdout+run.stderr)
                if run.returncode:raise ValueError('GLS command failed: '+name)
            raw=re.findall(r'^RESULT (\{.*\})$',(out/'gls.txt').read_text(),re.M)
            if len(raw)!=1:raise ValueError('Expected exactly one GLS RESULT')
            coverage=json.loads(raw[0])
            if (coverage['depth']!=4 or coverage['seed']!=23063 or coverage['random_ops']!=2048
                    or coverage['control_transitions']!=64 or coverage['checks']!=15619
                    or any(v<=0 for v in coverage['controls']+coverage['read_addresses']+coverage['write_addresses'])):
                raise ValueError('Routed GLS coverage incomplete')
            for s,target in zip(sources,snapshots):
                if sha(s)!=result['inputs'][str(s)] or sha(target)!=result['inputs'][str(s)]:
                    raise ValueError('GLS input changed')
            result.update(status='PASS_FUNCTIONAL_ROUTED_GLS',coverage=coverage)
        except Exception as e:result.update(status='FAIL',error=str(e))
        result['artifacts']={s.name:sha(s) for s in out.iterdir() if s.is_file() and s.name not in ('results.json','.run.lock')}
        publish();print(json.dumps(result,indent=2))
        return 0 if result['status']=='PASS_FUNCTIONAL_ROUTED_GLS' else 1


if __name__=='__main__':raise SystemExit(main())
