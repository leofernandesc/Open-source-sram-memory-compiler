#!/usr/bin/env python3
"""Fresh-process DRC and expanded transistor LVS of the delivered full GDSII."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from run_digital_regression import atomic_text,output_lock
from run_phase2_physical_pilot import ROOT,PDK,RC,digest,normal_mos


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--layout-report',default='reports/phase2/integrated_import_fix')
    p.add_argument('--output',default='reports/phase2/final_gds')
    a=p.parse_args();source=ROOT/a.layout_report;out=(ROOT/a.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2') or out==ROOT/'reports/phase2':p.error('Output under reports/phase2 required')
    if out==source.resolve():p.error('Output cannot replace the layout input')
    out.mkdir(parents=True,exist_ok=True)
    with output_lock(out):
        result={'status':'RUNNING','CORE':'NOT_EVALUATED','F2_FIS':'NOT_EVALUATED',
                'scope':'Final full GDS reimport, DRC and W/L/body/model LVS; connectivity extraction only'}
        def publish():atomic_text(out/'results.json',json.dumps(result,indent=2)+'\n')
        publish()
        try:
            state=json.loads((source/'results.json').read_text())
            if state['status']!='LAYOUT_MATCH_REIMPORT_PENDING':raise ValueError('Source routed layout DRC/LVS required')
            build=Path(tempfile.mkdtemp(prefix='gds-check-',dir=ROOT/'build/phase2'))
            sources=[source/'sram_4x8.gds',source/'reference_mos.spice',source/'results.json',RC,PDK/'libs.tech/netgen/sky130A_setup.tcl']
            result.update(build_directory=str(build.relative_to(ROOT)),inputs={str(s):digest(s) for s in sources})
            shutil.copyfile(sources[0],build/'sram_4x8.gds');shutil.copyfile(sources[1],build/'reference_mos.spice')
            commands=f'''gds read {build}/sram_4x8.gds
load sram_4x8_wrapper
select top cell
expand
flatten final_flat
load final_flat
select top cell
expand
drc euclidean on
drc style drc(full)
drc on
drc check
drc catchup
puts "FINAL_GDS_DRC=[llength [drc listall why]]"
puts "FINAL_GDS_DETAILS=[drc listall why]"
save final_flat
extract all
ext2spice lvs
ext2spice scale off
ext2spice -o {build}/final_extracted.spice
quit -noprompt
'''
            (build/'verify.tcl').write_text(commands);atomic_text(out/'verify.tcl',commands)
            def run(argv,log,stdin=None):
                with (out/log).open('w') as f:
                    r=subprocess.run([str(v) for v in argv],cwd=build,input=stdin,text=True,stdout=f,stderr=subprocess.STDOUT,timeout=600)
                if r.returncode:raise ValueError('Command failed: '+log)
                return (out/log).read_text()
            text=run(['magic','-dnull','-noconsole','-rcfile',RC],'magic.txt',commands)
            if re.search(r'(?i)encountered \d+ errors|I/O error|abstract view;|\(Error\):',text):raise ValueError('GDS import/export error')
            result['drc_markers']=re.findall(r'^FINAL_GDS_DRC=(\d+)$',text,re.M)
            if result['drc_markers']!=['0']:raise ValueError('Reimported GDS DRC failed')
            extracted=(build/'final_extracted.spice').read_text()
            # Only rename the explicitly defined public bus labels.
            extracted=re.sub(r'(?<![A-Za-z0-9_])\\?(ADDR|DATA)\[(\d+)\]',r'\1\2',extracted)
            normalized,count=normal_mos(extracted,'sram_4x8_wrapper')
            if count!=state['extracted_mos']:raise ValueError('Reimport changed MOS count')
            (build/'layout_mos.spice').write_text(normalized)
            run(['netgen','-batch','lvs','layout_mos.spice sram_4x8_wrapper','reference_mos.spice sram_4x8_wrapper',sources[-1],build/'lvs.txt'],'netgen.txt')
            text=(build/'lvs.txt').read_text();atomic_text(out/'lvs.txt',text)
            if 'Circuits match uniquely.' not in text or re.search(r'(?i)property errors|do not match|black.box|placeholder|failed to open',text):raise ValueError('Final GDS LVS failed')
            for s in sources:
                if digest(s)!=result['inputs'][str(s)]:raise ValueError('GDS verification input changed')
            for name in ('sram_4x8.gds','final_extracted.spice','final_flat.ext','layout_mos.spice','reference_mos.spice'):
                shutil.copyfile(build/name,out/name)
            result.update(status='PASS_GEOMETRY_LVS',mos=count,lvs='UNIQUE_MATCH_W_L_BODY_MODEL',
                          electrical_access='REPEAT_ON_THIS_EXTRACTION_REQUIRED')
        except Exception as e:result.update(status='FAIL',error=str(e))
        result['artifacts']={s.name:digest(s) for s in out.iterdir() if s.is_file() and s.name not in ('results.json','.run.lock')}
        publish();print(json.dumps(result,indent=2))
        return 0 if result['status']=='PASS_GEOMETRY_LVS' else 1


if __name__=='__main__':raise SystemExit(main())
