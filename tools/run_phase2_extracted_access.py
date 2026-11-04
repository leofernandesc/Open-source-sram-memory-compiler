#!/usr/bin/env python3
"""Electrical access using the full flat circuit extracted from final GDSII.

No interconnect R-C PEX or SRAM timing characterization is claimed.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import numpy as np
from run_digital_regression import atomic_text,output_lock
from run_phase2_access import ROOT,PDK,bench
from phase2_access_checks import check as protocol_check
from phase2_extracted import bind
from run_phase2_digital import sha
from phase2_resources import preflight


def model_closure(path):
    """Hash the transitive include closure, conservatively including all corners."""
    found={}
    def visit(p):
        p=p.resolve()
        if str(p) in found:return
        text=p.read_text();found[str(p)]=sha(p)
        for line in text.splitlines():
            m=re.match(r'(?i)^\s*\.include\s+["\']?([^"\'\s]+)',line)
            if m:visit(p.parent/m[1])
    visit(path)
    return found


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--quick',action='store_true')
    p.add_argument('--gds-report',default='reports/phase2/final_gds')
    p.add_argument('--layout-report',default='reports/phase2/integrated_import_fix')
    p.add_argument('--output',default='reports/phase2/extracted_access')
    a=p.parse_args();source=ROOT/a.gds_report;layout=ROOT/a.layout_report;out=(ROOT/a.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2') or out==ROOT/'reports/phase2':p.error('Output under reports/phase2 required')
    out.mkdir(parents=True,exist_ok=True)
    with output_lock(out):
        result={'status':'RUNNING','CORE':'NOT_EVALUATED','F2_FIS':'NOT_EVALUATED',
                'scope':'Final GDS extracted MOS, actual junction geometry and CTS/capture; no wire R-C PEX',
                'quick':a.quick,'condition':{'corner':'tt','vdd_v':1.8,'temp_c':27}}
        def publish():atomic_text(out/'results.json',json.dumps(result,indent=2)+'\n')
        publish()
        try:
            result['resources_before_run']=preflight(ROOT)
            gds=json.loads((source/'results.json').read_text());state=json.loads((layout/'results.json').read_text())
            if gds['status']!='PASS_GEOMETRY_LVS':raise ValueError('Final GDS DRC/LVS required')
            if gds['inputs'][str(layout/'sram_4x8.gds')]!=sha(layout/'sram_4x8.gds'):raise ValueError('Layout and GDS verification differ')
            layout_build=ROOT/state['build_directory'];design_path=layout_build/'routed_reference.json'
            sources=[source/'results.json',source/'final_extracted.spice',source/'final_flat.ext',design_path,
                     Path(__file__),ROOT/'tools/phase2_extracted.py',ROOT/'tools/phase2_access_checks.py',ROOT/'tools/run_phase2_access.py']
            hashes={str(s):sha(s) for s in sources}
            models=model_closure(PDK/'libs.tech/ngspice/sky130.lib.spice')
            design=json.loads(design_path.read_text())
            flat,probes,proof=bind(sources[1].read_text(),sources[2].read_text(),design)
            ports=re.search(r'^\.subckt \S+ (.+)$',flat,re.M)[1].split()
            build=Path(tempfile.mkdtemp(prefix='extracted-access-',dir=ROOT/'build/phase2'))
            (build/'binding.spice').write_text(flat);(build/'fabric.spice').write_text('* Entire fabric already in the extracted flat circuit\n')
            deck,records,vectors,inputs,clocks=bench({'ports':ports},design,a.quick)
            deck=deck.replace('.control\n','.control\nset num_threads=1\n')
            if any(v not in probes for v in vectors):raise ValueError('Unbound extracted probes: '+str([v for v in vectors if v not in probes]))
            for old,new in probes.items():deck=deck.replace(old,new)
            vectors=[probes[v] for v in vectors];inputs=[probes[v] for v in inputs];clocks=[probes[v] for v in clocks]
            if '.ic ' in deck.lower() or '.nodeset' in deck.lower():raise ValueError('Artificial initialization forbidden')
            (build/'bench.spice').write_text(deck)
            result.update(build_directory=str(build.relative_to(ROOT)),inputs=hashes,model_inputs=models,
                          binding_audit=proof,cycles=records,vectors=vectors,capture_inputs=inputs,capture_clocks=clocks,
                          artifacts_before_run={n:sha(build/n) for n in ('bench.spice','binding.spice','fabric.spice')})
            publish()
            for n in ('bench.spice','binding.spice','fabric.spice'):shutil.copyfile(build/n,out/n)
            with (out/'ngspice.txt').open('w') as log:
                run=subprocess.run(['ngspice','-n','-b','bench.spice'],cwd=build,stdout=log,stderr=subprocess.STDOUT,timeout=2400,
                                   env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'))
            if run.returncode or not (build/'waveform.dat').exists():raise ValueError('Extracted electrical simulation failed')
            data=np.loadtxt(build/'waveform.dat',skiprows=1)
            if not len(data)>100 or data.shape[1]!=len(vectors)+1 or not np.all(np.isfinite(data)):raise ValueError('Invalid raw waveform')
            reads=[]
            for rec in records:
                if rec['operation']!='read':continue
                idx=np.searchsorted(data[:,0],rec['sample_ns']*1e-9)
                if idx>=len(data):raise ValueError('Transient ended before read sampling')
                for bit in range(8):
                    expected=(rec['expected']>>bit)&1;v=float(data[idx,bit+1]);ok=1.44<=v<=1.98 if expected else -.18<=v<=.36
                    reads.append(dict(**rec,bit=bit,voltage_v=v,status='PASS' if ok else 'FAIL'))
            protocol,ref=protocol_check(data,records,vectors,inputs,clocks)
            for rec in records:
                if not rec['operation'].startswith('inactive'):continue
                for offset,invert in ((1,False),(8,True)):
                    idx=np.searchsorted(data[:,0],(rec['rise_ns']+offset)*1e-9)
                    for bit in range(8):
                        expected=((rec['expected']^(255 if invert else 0))>>bit)&1;v=float(data[idx,bit+1])
                        protocol.append(dict(kind='bus_release_1kohm_probe',cycle=rec['cycle'],bit=bit,voltage_v=v,status='PASS' if abs(v-expected*1.8)<=.05 else 'FAIL'))
            with (out/'checks.csv').open('w') as f:
                w=csv.DictWriter(f,fieldnames=list(reads[0]));w.writeheader();w.writerows(reads)
            atomic_text(out/'protocol.json',json.dumps({'checks':protocol,'capture_reference':ref},indent=2)+'\n')
            for s in sources:
                if sha(s)!=hashes[str(s)]:raise ValueError('Electrical source changed during simulation')
            if model_closure(PDK/'libs.tech/ngspice/sky130.lib.spice')!=models:raise ValueError('PDK models changed during simulation')
            result.update(read_checks=len(reads),read_failures=sum(c['status']=='FAIL' for c in reads),
                          protocol_checks=len(protocol),protocol_failures=sum(c['status']=='FAIL' for c in protocol),
                          raw_waveform_sha256=sha(build/'waveform.dat'))
            result['status']='PASS_EXTRACTED_NOMINAL_ACCESS' if reads and not result['read_failures'] and not result['protocol_failures'] else 'FAIL'
            np.savetxt(out/'waveform_excerpt.csv',data[::10],delimiter=',',header=','.join(['time_s',*vectors]),comments='')
        except Exception as e:result.update(status='FAIL',error=str(e))
        result['artifacts']={s.name:sha(s) for s in out.iterdir() if s.is_file() and s.name not in ('results.json','.run.lock')}
        publish();print(json.dumps({k:v for k,v in result.items() if k in ('status','read_checks','read_failures','protocol_checks','protocol_failures','error')},indent=2))
        return 0 if result['status']=='PASS_EXTRACTED_NOMINAL_ACCESS' else 1


if __name__=='__main__':raise SystemExit(main())
