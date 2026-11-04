#!/usr/bin/env python3
"""Import actual routed geometry into Magic and compare full transistor hierarchy.

Connectivity extraction only. Detailed resistor/capacitor PEX is not performed.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from run_digital_regression import atomic_text,output_lock
from run_phase2_binding import spice_from_json
from run_phase2_access import raw_fabric
from run_phase2_physical_pilot import normal_mos,digest

ROOT=Path(__file__).resolve().parents[1]
PDK=Path('/opt/pdks/sky130A');HD=PDK/'libs.ref/sky130_fd_sc_hd'
RC=PDK/'libs.tech/magic/sky130A.magicrc'


def normalized_hierarchy(text):
    result=[];total=0
    for m in re.finditer(r'(?ms)^\.subckt\s+(\S+)[^\n]*\n.*?^\.ends[^\n]*',text):
        name=m[1];body=m[0]
        instances=[l.split()[5] for l in body.splitlines() if re.match(r'(?i)^x\S+\s',l)]
        if instances and all(t.startswith('sky130_fd_pr__') for t in instances):
            normalized,n=normal_mos(body,name);result.append(normalized);total+=n
        elif any(t.startswith('sky130_fd_pr__') for t in instances):
            raise ValueError('Mixed primitive/hierarchical subckt requires explicit normalization')
        else:result.append(body+'\n')
    if not result:raise ValueError('No reference hierarchy')
    return '\n'.join(result),total


def selected_hd_lef(names):
    text=(HD/'lef/sky130_fd_sc_hd.lef').read_text()+'\n'+(HD/'lef/sky130_ef_sc_hd.lef').read_text()
    blocks=[]
    for name in sorted(names):
        m=re.search(r'(?ms)^MACRO '+re.escape(name)+r'\s.*?^END '+re.escape(name)+r'\s*$',text)
        if not m:raise ValueError('Missing actual HD LEF: '+name)
        blocks.append(m[0])
    return '\n'.join(['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;',*blocks,'END LIBRARY'])+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--route-report',default='reports/phase2/route_macro_access')
    parser.add_argument('--output',default='reports/phase2/integrated_layout')
    args=parser.parse_args();output=(ROOT/args.output).resolve()
    if not output.is_relative_to(ROOT/'reports/phase2') or output==ROOT/'reports/phase2':parser.error('Output under reports/phase2 required')
    if output==(ROOT/args.route_report).resolve():parser.error('Output cannot replace the routing input')
    output.mkdir(parents=True,exist_ok=True)
    with output_lock(output):
        receipt={'status':'RUNNING','CORE':'NOT_EVALUATED','F2_FIS':'NOT_EVALUATED',
                 'scope':'Full routed SRAM geometry and expanded W/L/terminal LVS; no RC PEX'}
        def publish():atomic_text(output/'results.json',json.dumps(receipt,indent=2)+'\n')
        publish()
        try:
            route=ROOT/args.route_report;state=json.loads((route/'results.json').read_text())
            if state['status']!='ROUTED_VERIFICATION_PENDING':raise ValueError('Routing must complete first')
            route_build=ROOT/state['build_directory']
            for n,h in state.get('build_artifacts',{}).items():
                if digest(route_build/n)!=h:raise ValueError('Changed routing build input: '+n)
            root=ROOT/'build/phase2';root.mkdir(parents=True,exist_ok=True)
            build=Path(tempfile.mkdtemp(prefix='finish-',dir=root))
            receipt.update(build_directory=str(build.relative_to(ROOT)),route_receipt_sha256=digest(route/'results.json'))
            receipt['inputs']={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):digest(p) for p in
                               (route/'results.json',HD/'spice/sky130_fd_sc_hd.spice',HD/'lib/sky130_fd_sc_hd__tt_025C_1v80.lib',RC,Path(__file__))}
            publish()
            def run(command,log,stdin=None,cwd=None,timeout=240):
                with (output/log).open('w') as f:
                    p=subprocess.run([str(a) for a in command],cwd=cwd or build,input=stdin,
                                     text=True,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
                if p.returncode:raise ValueError(f'{command[0]} failed: {log}')
                return (output/log).read_text()
            final=f'''set_thread_count 1
read_db {route_build}/routed.odb
filler_placement {{sky130_fd_sc_hd__fill_8 sky130_fd_sc_hd__fill_4 sky130_fd_sc_hd__fill_2 sky130_fd_sc_hd__fill_1}}
global_connect
check_placement -verbose
puts "FINAL_DELAY_STAGES=[llength [get_cells *phase_delay*]]"
write_def {build}/final.def
write_verilog {build}/final.v
write_verilog -include_pwr_gnd {build}/final_powered.v
write_db {build}/final.odb
exit
'''
            (build/'finish.tcl').write_text(final)
            text=run(['openroad','-exit','finish.tcl'],'openroad_finish.txt')
            if re.findall(r'FINAL_DELAY_STAGES=(\d+)',text)!=['80']:raise ValueError('Lost physical delay stages')
            definition=(build/'final.def').read_text()
            components=re.search(r'(?ms)^COMPONENTS.*?^END COMPONENTS',definition)[0]
            names=set(re.findall(r'^\s*-\s+\S+\s+(\S+)',components,re.M))
            hd_names=names-{'leaf_fabric'}
            (build/'used_cells.lef').write_text(selected_hd_lef(hd_names))
            shutil.copyfile(route_build/'leaf_fabric.gds',build/'leaf_fabric.gds')
            shutil.copyfile(route_build/'leaf_fabric.lef',build/'leaf_fabric.lef')
            shutil.copyfile(ROOT/'physical/phase2/macro_binding.v',build/'macro_binding.v')
            hd_spice=(HD/'spice/sky130_fd_sc_hd.spice').read_text()
            liberty=(HD/'lib/sky130_fd_sc_hd__tt_025C_1v80.lib').read_text()
            library_cells=set(re.findall(r'cell\s*\(\s*"([^"]+)"',liberty))
            stubs=[]
            for name in sorted(hd_names):
                if not name.startswith(('sky130_fd_sc_hd__fill','sky130_fd_sc_hd__tap')):
                    if name not in library_cells:raise ValueError('Unmodeled functional cell: '+name)
                    continue
                definition=re.search(r'(?ms)^\.subckt '+re.escape(name)+r' .*?^\.ends[^\n]*',hd_spice)
                if (not definition or not name.startswith(('sky130_fd_sc_hd__fill','sky130_fd_sc_hd__tap'))
                        or re.search(r'(?mi)^[xm]\S+\s',definition[0])):
                    raise ValueError('Unmodeled functional standard cell: '+name)
                # Zero-device physical-only fillers/taps have no signal ports
                # in the unpowered Verilog view. They are real GDS instances;
                # their well/rail connections remain part of transistor LVS.
                stubs.append(f'(* blackbox *) module {name} (); endmodule')
            (build/'physical_stubs.v').write_text('\n'.join(stubs)+'\n')
            ys=f'''read_liberty -lib {HD}/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_verilog physical_stubs.v macro_binding.v final.v
hierarchy -check -top sram_4x8_wrapper
write_json routed_reference.json
'''
            (build/'reference.ys').write_text(ys)
            run(['yosys','-Q','-T','-s','reference.ys'],'reference_yosys.txt')
            design=json.loads((build/'routed_reference.json').read_text())
            reference,ports,counts=spice_from_json(design,hd_spice)
            (build/'routed_reference.spice').write_text(reference+raw_fabric())
            normalized,_=normalized_hierarchy(reference+raw_fabric())
            (build/'reference_mos.spice').write_text(normalized)
            commands=f'''path search +{HD}/mag
lef read {HD}/techlef/sky130_fd_sc_hd__nom.tlef
gds read {build}/leaf_fabric.gds
load leaf_fabric
lef read {build}/leaf_fabric.lef -annotate
{chr(10).join('load '+name for name in sorted(hd_names))}
lef read {build}/used_cells.lef -annotate
def read {build}/final.def
load sram_4x8_wrapper
select top cell
expand
gds write {build}/sram_4x8.gds
save sram_4x8_wrapper
flatten integrated_flat
load integrated_flat
select top cell
expand
drc euclidean on
drc style drc(full)
drc on
drc check
drc catchup
puts "INTEGRATED_DRC=[llength [drc listall why]]"
puts "INTEGRATED_DETAILS=[drc listall why]"
save integrated_flat
extract all
ext2spice lvs
ext2spice scale off
ext2spice -o {build}/integrated_extracted.spice
quit -noprompt
'''
            (build/'import.tcl').write_text(commands)
            text=run(['magic','-dnull','-noconsole','-rcfile',RC],'magic.txt',commands,timeout=300)
            if re.search(r'(?i)encountered \d+ errors|I/O error|abstract view;|\(Error\):',text):
                raise ValueError('Magic import/export error; DRC/LVS cannot qualify incomplete geometry')
            receipt['drc_markers']=re.findall(r'^INTEGRATED_DRC=(\d+)$',text,re.M)
            for name in ('sram_4x8.gds','leaf_fabric.gds','leaf_fabric.lef','routed_reference.json','final.def','final.v','final_powered.v','routed_reference.spice','reference_mos.spice',
                         'integrated_extracted.spice','integrated_flat.mag','import.tcl','finish.tcl'):
                if (build/name).is_file():shutil.copyfile(build/name,output/name)
            if receipt['drc_markers']!=['0']:raise ValueError('Integrated Magic DRC failed')
            extracted=(build/'integrated_extracted.spice').read_text()
            # HDL/DEF vector notation and the scalar SPICE harness refer to
            # the same public bits; normalize only those explicit bus names.
            extracted=re.sub(r'(?<![A-Za-z0-9_])\\?(ADDR|DATA)\[(\d+)\]',r'\1\2',extracted)
            normalized,count=normal_mos(extracted,'sram_4x8_wrapper')
            header=re.search(r'(?mi)^\.subckt\s+\S+\s+(.+)$',normalized)[1].split()
            if set(header)!=set(ports):raise ValueError('Integrated public pin set differs from reference')
            (build/'layout_mos.spice').write_text(normalized)
            report=build/'lvs.txt'
            run(['netgen','-batch','lvs','layout_mos.spice sram_4x8_wrapper','reference_mos.spice sram_4x8_wrapper',
                 PDK/'libs.tech/netgen/sky130A_setup.tcl',report],'netgen.txt')
            text=report.read_text();atomic_text(output/'lvs.txt',text)
            if 'Circuits match uniquely.' not in text or re.search(r'(?i)property errors|do not match|black.box|placeholder',text):
                raise ValueError('Integrated LVS failed')
            receipt.update(status='LAYOUT_MATCH_REIMPORT_PENDING',extracted_mos=count,ports=ports)
            for path,expected in receipt['inputs'].items():
                p=Path(path) if Path(path).is_absolute() else ROOT/path
                if digest(p)!=expected:raise ValueError('Finishing input changed during run')
        except Exception as error:receipt.update(status='FAIL',error=str(error))
        receipt['artifacts']={p.name:digest(p) for p in output.iterdir() if p.is_file() and p.name not in ('results.json','.run.lock')}
        publish();print(json.dumps({k:receipt[k] for k in ('status','CORE','F2_FIS')},indent=2))
        if 'error' in receipt:print(receipt['error'])
        return 0 if receipt['status']=='LAYOUT_MATCH_REIMPORT_PENDING' else 1


if __name__=='__main__':raise SystemExit(main())
