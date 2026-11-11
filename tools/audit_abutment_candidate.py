#!/usr/bin/env python3
"""Final independent terminal/seam/preservation audit of the new candidate."""
import argparse,json,re,subprocess
from collections import defaultdict
from pathlib import Path
import gdstk
import numpy as np
from run_phase2_digital import ROOT,sha
from review_phase2_structure import inspect
from validate_direct_abutment import inspect_array
import phase2_extension
import analyze_phase2_extension_timing as timing

BASE=ROOT/'reports/phase2/direct_abutment_20261111'


def lower_geometry(path,dx=0,dy=0):
    layers=defaultdict(list);layer=''
    for line in Path(path).read_text().splitlines():
        if line.startswith('<<'):layer=line[3:-3]
        elif line.startswith('rect ') and layer not in ('checkpaint','metal3','via3','metal4'):
            x,y,a,b=map(int,line.split()[1:]);layers[layer].append((x-dx,y-dy,a-dx,b-dy))
    return {k:sorted(v) for k,v in layers.items()}


def check_seams(cell,tile,rows,cols,origin=(0,180)):
    (x0,y0),(x1,y1)=tile.bounding_box();width,height=x1-x0,y1-y0
    if not np.allclose([x0,y0],[0,0]):raise ValueError('Leaf origin differs')
    labels={l.text:l.origin for l in tile.labels}
    merged=gdstk.boolean(tile.get_polygons(layer=70,datatype=20),[],'or',precision=.001)
    rails=sorted({round((p.bounding_box()[0][1]+p.bounding_box()[1][1])/2,6) for p in merged
                  if abs(p.bounding_box()[0][0])<1e-6 and abs(p.bounding_box()[1][0]-width)<1e-6})
    if len(rails)!=3:raise ValueError('Expected only WL/VDD/VSS at horizontal boundaries')
    ox,oy=origin;m3=cell.get_polygons(layer=70,datatype=20);m4=cell.get_polygons(layer=71,datatype=20);checks=0
    for r in range(rows):
        for b in range(cols-1):
            for y in rails:
                points=[(ox+(b+1)*width-.001,oy+r*height+y),(ox+(b+1)*width+.001,oy+r*height+y)]
                if not all(gdstk.inside(points,m3)):raise ValueError('Horizontal gap or missing continuity')
                checks+=1
    for r in range(rows-1):
        for b in range(cols):
            for name in ('BL','BLB','VDD','VSS'):
                x=ox+b*width+labels[name][0]
                if not all(gdstk.inside([(x,oy+(r+1)*height-.001),(x,oy+(r+1)*height+.001)],m4)):
                    raise ValueError('Vertical gap or missing continuity')
                checks+=1
    return dict(seams_checked=checks,tile_size_um=[width,height],matrix_size_um=[cols*width,rows*height],horizontal_rail_y_um=rails)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=(ROOT/a.output).resolve()
    if not out.is_relative_to(BASE) or out.exists():p.error('New candidate audit directory required')
    out.mkdir(parents=True);record=dict(status='RUNNING',script_sha256=sha(Path(__file__)))
    try:
        paths=[BASE/n for n in ('fabric_v3','route_v1','layout_v1','gds_v1','fixture_v1','qualification_v1')]
        expected=['PASS_LEAF_FABRIC','ROUTED_VERIFICATION_PENDING','LAYOUT_MATCH_REIMPORT_PENDING','PASS_GEOMETRY_LVS','PREPARED_EXTRACTED_FIXTURE','PASS']
        receipts={}
        for folder,wanted in zip(paths,expected):
            s=json.loads((folder/'results.json').read_text())
            if s['status']!=wanted:raise ValueError('Incomplete candidate stage '+str(folder))
            for n,h in s['artifacts'].items():
                if sha(folder/n)!=h:raise ValueError('Candidate artifact changed '+n)
            for n,h in s.get('inputs',{}).items():
                if sha(n)!=h:raise ValueError('Candidate input changed '+n)
            receipts[str(folder.relative_to(ROOT))]=sha(folder/'results.json')
        baseline=json.loads((ROOT/'physical/phase2_direct_abutment/baseline.json').read_text())
        for path,h in baseline['inputs'].items():
            if sha(ROOT/path)!=h:raise ValueError('Historical selected artifact changed '+path)
        protected=subprocess.check_output(['git','diff','--name-only','--diff-filter=MD',baseline['base_commit'],'--',
            'release','cells','layout','rtl','synth','specs','scripts','tools','physical/phase2','reports/phase2'],cwd=ROOT,text=True).strip()
        if protected:raise ValueError('Existing protected files modified: '+protected)
        old=lower_geometry(ROOT/'release/phase1/cells/bitcell_6t/bitcell_6t.mag')
        new=lower_geometry(ROOT/'physical/phase2_direct_abutment/bitcell_6t_abut.mag',450,3050)
        if old!=new:raise ValueError('Pre-M3 geometry changed, including device/well/contact layers')
        fabric=gdstk.read_gds(BASE/'fabric_v3/leaf_fabric.gds').top_level()[0]
        tile=gdstk.read_gds(ROOT/'reports/direct_abutment/20261111/leaf_v2/bitcell_6t_abut.gds').top_level()[0]
        geometry=check_seams(fabric,tile,4,8)
        layout=BASE/'layout_v1';gds=BASE/'gds_v1';design=json.loads((layout/'routed_reference.json').read_text())
        structure=inspect(gds,(layout/'routed_reference.spice').read_text(),design)
        pitch=np.diff(structure['physical_row_y_internal_units'])
        if not np.allclose(pitch,2800):raise ValueError('Extracted device rows do not have direct tile pitch')
        top=design['modules']['sram_4x8_wrapper'];delay=[v for n,v in top['cells'].items() if 'phase_delay' in n]
        if len(delay)!=80 or any(v['type']!='sky130_fd_sc_hd__inv_1' for v in delay):raise ValueError('Delay chain changed')
        ff=sum(v['type'].startswith('sky130_fd_sc_hd__df') for v in top['cells'].values())
        eb=sum(v['type']=='sky130_fd_sc_hd__ebufn_1' for v in top['cells'].values())
        if (ff,eb)!=(20,8):raise ValueError('Interface FF/tri-state count changed')
        fixture=BASE/'fixture_v1';source=BASE/'qualification_v1'
        s=json.loads((source/'results.json').read_text());state=json.loads((fixture/'results.json').read_text())
        for path,h in s['inputs'].items():
            if sha(path)!=h:raise ValueError('Electrical input changed '+path)
        raw=ROOT/s['build_directory']/'waveform.dat'
        if sha(raw)!=s['raw_sha256']:raise ValueError('Electrical raw changed')
        data=np.loadtxt(raw,skiprows=1)
        checks,ref,metrics=phase2_extension.check(data,s['cycles'],s['vectors'],s['probes'],state,s['stop_ns'],'bus')
        if json.loads((source/'checks.json').read_text())!=dict(checks=checks,capture_reference=ref):
            raise ValueError('Checks do not reconcile with full raw')
        if len(checks)!=s['checks'] or metrics!=s['metrics'] or s['failures'] or any(c['status']!='PASS' for c in checks):
            raise ValueError('Electrical counters or actual checks disagree')
        log=(source/'ngspice.txt').read_text();native=re.findall(r'No\. of Data Rows\s*:\s*(\d+)',log)
        if native!=[str(len(data))] or 'ngspice-44.2 done' not in log:raise ValueError('Native completion/row count differs')
        del data
        timing.SOURCE=fixture
        measured=timing.measure(source)
        if any(c['status']!='PASS' for c in measured['checks']):raise ValueError('Fresh timing/precharge screens failed')
        (out/'timing.json').write_text(json.dumps(measured,indent=2)+'\n')
        ranges={}
        for group,fields in [('phase',['write_on_guard_ns','wl_to_sense_ns','wl_release_guard_ns','write_release_guard_ns']),
                             ('capture',['raw_valid_before_capture_ns','fd_valid_before_capture_ns','data_from_public_fall_ns']),
                             ('bus',['disable_from_control50_ns','enable_from_control50_ns','measured_release_to_host20_ns'])]:
            for key in fields:
                values=[r[key] for r in measured[group] if r.get(key) is not None]
                if values:ranges[key]=dict(min=min(values),max=max(values),samples=len(values))
        # Negative checks use disposable in-memory copies of real evidence.
        pilot=ROOT/'reports/direct_abutment/20261111/pilot_stream_v1/stream_extracted.spice';text=pilot.read_text();inspect_array(text,2,2)
        mutants={'row_alias':text.replace('WL1','WL0'),
                 'column_alias':text.replace('BL1','BL0').replace('BLB1','BLB0'),
                 'wrong_width':text.replace('w=0.6 ','w=0.61 ',1),
                 'supply_short':re.sub(r'\bVDD\b','VSS',text)}
        negative=[]
        for name,mutant in mutants.items():
            try:inspect_array(mutant,2,2)
            except ValueError as error:negative.append(dict(name=name,status='REJECTED',diagnostic=str(error)))
            else:raise ValueError('Independent checker accepted mutant '+name)
        pilot_lib=gdstk.read_gds(ROOT/'reports/direct_abutment/20261111/pilot_v2/array_2x2_abut.gds');pilot_cell=pilot_lib.top_level()[0]
        moved=next(ref for ref in pilot_cell.references if ref.origin[0]>0)
        moved.origin=(moved.origin[0]+.01,moved.origin[1])
        try:check_seams(pilot_cell,tile,2,2,(0,0))
        except ValueError as error:negative.append(dict(name='10nm_horizontal_gap',status='REJECTED',diagnostic=str(error)))
        else:raise ValueError('Independent checker accepted a placement gap')
        (out/'structure.json').write_text(json.dumps(structure,indent=2)+'\n')
        area_old=(7*30+17.25)*(3*25+12.92);area_new=138*56
        record.update(status='PASS_NEW_CANDIDATE_AUDIT',receipts=receipts,geometry=geometry,
                      lower_layers_identical=list(old),preserved_selected_inputs=baseline['inputs'],
                      protected_existing_git_files_modified=False,storage_bits=structure['storage_bits'],mos=structure['mos'],
                      hd_ff=ff,ebufn=eb,delay_inverters=len(delay),negative_controls=negative,
                      electrical_checks=len(checks),read_bits_included=metrics['read_bit_checks'],
                      additional_raw_screens=len(measured['checks']),nominal_timing_ranges=ranges,
                      area=dict(old_matrix_envelope_um2=area_old,new_matrix_envelope_um2=area_new,
                                reduction_percent=100*(1-area_new/area_old),old_pitch_budget_um2=24000,
                                new_pitch_budget_um2=7728,top_floorplan_um2=540*380,top_floorplan_reduction_percent=0),
                      scope='Nominal new candidate only; no official selector change, detailed wire RC or PVT guarantee')
    except Exception as e:record.update(status='FAIL',error=str(e))
    record['artifacts']={q.name:sha(q) for q in out.iterdir() if q.is_file() and q.name!='results.json'}
    (out/'results.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
    return 0 if record['status']=='PASS_NEW_CANDIDATE_AUDIT' else 1


if __name__=='__main__':raise SystemExit(main())
