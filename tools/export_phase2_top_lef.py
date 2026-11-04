#!/usr/bin/env python3
"""Export a geometry-only top-level macro LEF from the verified final GDSII."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile
import gdstk
from run_phase2_digital import ROOT,sha
from run_phase2_physical_pilot import RC
from run_digital_regression import atomic_text,output_lock


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-report',help='Recheck an existing GDS-bound export without rerunning Magic')
    parser.add_argument('--output',default='reports/phase2/top_abstract_current')
    args=parser.parse_args()
    source=ROOT/'reports/phase2/final_gds';out=(ROOT/args.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2') or out==ROOT/'reports/phase2':parser.error('Output under reports/phase2 required')
    out.mkdir(parents=True,exist_ok=True)
    with output_lock(out):
        result={'status':'RUNNING','scope':'Geometry-only final top LEF; no characterized timing/capacitance or higher-level route qualification'}
        def publish():atomic_text(out/'results.json',json.dumps(result,indent=2)+'\n')
        publish()
        try:
            state=json.loads((source/'results.json').read_text())
            if state['status']!='PASS_GEOMETRY_LVS':raise ValueError('Verified final GDS required')
            gds=source/'sram_4x8.gds';identity=sha(gds)
            build=Path(tempfile.mkdtemp(prefix='top-lef-',dir=ROOT/'build/phase2'))
            commands=f'''gds read {gds}
load sram_4x8_wrapper
select top cell
expand
lef write {build}/sram_4x8.lef -hide
quit -noprompt
'''
            if args.source_report:
                previous=ROOT/args.source_report;proof=json.loads((previous/'results.json').read_text())
                lef=previous/'sram_4x8.lef'
                if (proof['status']!='PASS_GEOMETRY_ABSTRACT' or proof['source_gds_sha256']!=identity
                        or sha(lef)!=proof['artifacts']['sram_4x8.lef']):raise ValueError('Existing export identity mismatch')
                result['source_lef_sha256']=sha(lef);text=lef.read_text()
            else:
                (build/'export.tcl').write_text(commands)
                r=subprocess.run(['magic','-dnull','-noconsole','-rcfile',RC],cwd=build,input=commands,text=True,capture_output=True,timeout=120)
                atomic_text(out/'magic.txt',r.stdout+r.stderr)
                if r.returncode or re.search(r'(?i)I/O error|\(Error\):',r.stdout+r.stderr):raise ValueError('Top LEF export failed')
                text=(build/'sram_4x8.lef').read_text()
            # Obsolete since LEF 5.6; removing this ignored metadata statement
            # leaves every pin/obstruction coordinate unchanged.
            text=re.sub(r'(?m)^\s*NOWIREEXTENSIONATPIN[^\n]*\n','',text)
            directions={'CLK':'INPUT','CSb':'INPUT','OEb':'INPUT','WEb':'INPUT','VDD':'INOUT','VSS':'INOUT',
                        **{f'ADDR[{b}]':'INPUT' for b in range(2)},**{f'DATA[{b}]':'INOUT' for b in range(8)}}
            blocks=re.findall(r'(?ms)^\s*PIN (\S+)\s*\n(.*?)^\s*END \1\s*$',text)
            if len(blocks)!=16 or {n for n,_ in blocks}!=set(directions):raise ValueError('Top LEF pin set differs from public interface')
            lib=gdstk.read_gds(gds);top=next(c for c in lib.cells if c.name=='sram_4x8_wrapper')
            if top.bounding_box()!=((0.,0.),(540.,380.)):raise ValueError('Unexpected final geometry origin/size')
            if not re.search(r'\bSIZE\s+540(?:\.0*)?\s+BY\s+380(?:\.0*)?\s*;',text):raise ValueError('Top LEF size differs from GDS')
            levels={'met1':68,'met2':69,'met3':70,'met4':71,'met5':72};checked=0
            shapes={}
            for name,body in blocks:
                ports=re.findall(r'(?s)\bPORT\b(.*?)\bEND\b',body)
                if not ports:raise ValueError('Missing top pin PORT')
                layer=None
                for line in '\n'.join(ports).splitlines():
                    l=re.search(r'\bLAYER (\S+)\s*;',line)
                    if l:layer=l[1]
                    rect=re.search(r'\bRECT\s+([\d. -]+);',line)
                    if rect:
                        x1,y1,x2,y2=map(float,rect[1].split())
                        if layer not in levels:raise ValueError('Nonrouting top pin layer')
                        if layer not in shapes:shapes[layer]=top.get_polygons(layer=levels[layer],datatype=20)
                        outside=gdstk.boolean([gdstk.rectangle((x1,y1),(x2,y2))],shapes[layer],'not',precision=.001)
                        if sum(p.area() for p in outside)>1e-6:raise ValueError('Top LEF pin outside actual GDS metal: '+name)
                        checked+=1
                # Set semantic attributes from the public contract, preserving
                # all generated pin/obstruction coordinates unchanged.
                old=re.search(r'(?ms)^\s*PIN '+re.escape(name)+r'\s*\n.*?^\s*END '+re.escape(name)+r'\s*$',text)[0]
                new=re.sub(r'DIRECTION \w+\s*;',f'DIRECTION {directions[name]} ;',old)
                if 'DIRECTION ' not in new:new=new.replace('PORT',f'DIRECTION {directions[name]} ;\n    PORT',1)
                use='POWER' if name=='VDD' else 'GROUND' if name=='VSS' else 'CLOCK' if name=='CLK' else 'SIGNAL'
                new=re.sub(r'USE \w+\s*;',f'USE {use} ;',new)
                if 'USE ' not in new:new=new.replace('PORT',f'USE {use} ;\n    PORT',1)
                text=text.replace(old,new,1)
            if checked<16:raise ValueError('Insufficient actual pin rectangles')
            if sha(gds)!=identity:raise ValueError('GDS changed during abstraction')
            atomic_text(out/'sram_4x8.lef',text)
            # Independently parse the delivered abstract using OpenROAD.
            tcl=f'''read_lef /opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef
read_lef {out}/sram_4x8.lef
puts TOP_LEF_READ_OK
exit
'''
            (build/'check.tcl').write_text(tcl)
            r=subprocess.run(['openroad','-exit',build/'check.tcl'],capture_output=True,text=True,timeout=60)
            atomic_text(out/'openroad.txt',r.stdout+r.stderr)
            if r.returncode or 'TOP_LEF_READ_OK' not in r.stdout:raise ValueError('Top LEF parser check failed')
            result.update(status='PASS_GEOMETRY_ABSTRACT',source_gds_sha256=identity,pins=directions,
                          size_um=[540.,380.],actual_metal_rectangles_checked=checked)
        except Exception as e:result.update(status='FAIL',error=str(e))
        result['artifacts']={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name not in ('results.json','.run.lock')}
        publish();print(json.dumps(result,indent=2))
        return 0 if result['status']=='PASS_GEOMETRY_ABSTRACT' else 1


if __name__=='__main__':raise SystemExit(main())
