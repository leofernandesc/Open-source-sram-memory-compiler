#!/usr/bin/env python3
"""Expanded full-top LVS and deliberate gate/body/W/L defects in copies only."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from run_phase2_digital import ROOT,sha
from run_digital_regression import atomic_text,output_lock
from phase2_resources import preflight


def main():
    out=ROOT/'reports/phase2/review_20261104/lvs_negative';out.mkdir(exist_ok=True)
    with output_lock(out):
        result={'status':'RUNNING','scope':'Expanded original 1493-MOS top; copies only; no geometric or frozen-cell edit','cases':[]}
        def publish():atomic_text(out/'results.json',json.dumps(result,indent=2)+'\n')
        publish()
        try:
            result['resources']=preflight(ROOT)
            source=ROOT/'reports/phase2/final_gds';setup=Path('/opt/pdks/sky130A/libs.tech/netgen/sky130A_setup.tcl')
            inputs=[source/'layout_mos.spice',source/'reference_mos.spice',setup,Path(__file__)]
            pinned={str(p):sha(p) for p in inputs};result['inputs']=pinned
            build=Path(tempfile.mkdtemp(prefix='lvs-review-',dir=ROOT/'build/phase2'));result['build_directory']=str(build.relative_to(ROOT))
            reference=build/'reference.spice';shutil.copyfile(inputs[1],reference)
            text=inputs[0].read_text();original=text.splitlines();index=next(i for i,l in enumerate(original) if re.match(r'^M\S+\s',l))
            for fault in ('golden','gate','body','width','length'):
                lines=list(original);fields=lines[index].split()
                if fault=='gate':fields[2]='AUDIT_INJECTED_GATE';lines[index]=' '.join(fields)
                elif fault=='body':fields[4]='AUDIT_INJECTED_BULK';lines[index]=' '.join(fields)
                elif fault in ('width','length'):
                    parameter='w' if fault=='width' else 'l'
                    lines[index]=re.sub(r'\b'+parameter+r'=([\d.eE+-]+)u',lambda m:parameter+'='+str(float(m[1])*1.2)+'u',lines[index])
                netlist=build/(fault+'.spice');netlist.write_text('\n'.join(lines)+'\n');report=build/(fault+'.log')
                run=subprocess.run(['netgen','-batch','lvs',str(netlist)+' sram_4x8_wrapper',str(reference)+' sram_4x8_wrapper',str(setup),str(report)],cwd=build,capture_output=True,text=True,timeout=120)
                atomic_text(out/(fault+'_console.txt'),run.stdout+run.stderr)
                if run.returncode or not report.is_file():raise ValueError('Netgen tool failure: '+fault)
                raw=report.read_text();atomic_text(out/(fault+'.log'),raw)
                if re.search(r'(?i)black.box|placeholder|failed to open',raw):raise ValueError('Invalid comparator scope')
                if fault=='golden':
                    ok='Final result: Circuits match uniquely.' in raw and not re.search(r'(?i)property errors|do not match',raw)
                elif fault in ('gate','body'):
                    name='AUDIT_INJECTED_GATE' if fault=='gate' else 'AUDIT_INJECTED_BULK'
                    final_mismatch=('Final result: Netlists do not match.' in raw or
                                    'Final result: Top level cell failed pin matching.' in raw)
                    ok=final_mismatch and 'Netlists do not match.' in raw and name in raw
                else:
                    parameter='W' if fault=='width' else 'L'
                    values=re.findall(parameter+r' circuit1:\s*([\d.eE+-]+)\s+circuit2:\s*([\d.eE+-]+)',raw)
                    scope=re.search(r'The following cells had property errors:\s*(.*?)\s*$',raw,re.S)
                    ok=bool(scope and scope[1].strip()=='sram_4x8_wrapper' and values and
                            any(abs(float(a)/float(b)-1.2)<1e-8 for a,b in values))
                if not ok:raise ValueError('Wrong negative outcome or scope: '+fault)
                result['cases'].append({'fault':fault,'status':'PASS' if fault=='golden' else 'REJECTED',
                                        'report_sha256':sha(out/(fault+'.log')),'netlist_sha256':sha(netlist)})
            for p,h in pinned.items():
                if sha(p)!=h:raise ValueError('LVS review input changed')
            result['status']='PASS_FULL_TOP_LVS_AND_4_NEGATIVES'
        except Exception as e:result.update(status='FAIL',error=str(e))
        publish();print(json.dumps(result,indent=2))
        return 0 if result['status']=='PASS_FULL_TOP_LVS_AND_4_NEGATIVES' else 1


if __name__=='__main__':raise SystemExit(main())
