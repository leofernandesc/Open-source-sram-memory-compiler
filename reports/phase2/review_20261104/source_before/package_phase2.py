#!/usr/bin/env python3
"""Index the experimentally verified 4x8 delivery without publishing Git changes."""
import json
from collections import Counter
from pathlib import Path
import re
import shutil
import subprocess
import gdstk
from run_phase2_digital import ROOT,sha
from run_digital_regression import atomic_text,output_lock


def core_geometry(source,final):
    a=next(c for c in gdstk.read_gds(source).cells if c.name=='leaf_fabric')
    b=next(c for c in gdstk.read_gds(final).cells if c.name=='leaf_fabric')
    polygons_a=a.get_polygons();polygons_b=b.get_polygons()
    layers={(p.layer,p.datatype) for p in polygons_a+polygons_b}
    differences={}
    metadata={};metadata_layers={(70,5):'MET3TXT',(70,16):'MET3PIN',(235,4):'BOUND'}
    def canonical(polygon):
        points=[tuple(round(float(v)*1000) for v in xy) for xy in polygon.points]
        reverse=list(reversed(points));candidates=[]
        for sequence in (points,reverse):
            smallest=min(sequence)
            candidates.extend(tuple(sequence[i:]+sequence[:i]) for i,p in enumerate(sequence) if p==smallest)
        return min(candidates)
    for layer,datatype in sorted(layers):
        first=[p for p in polygons_a if (p.layer,p.datatype)==(layer,datatype)]
        second=[p for p in polygons_b if (p.layer,p.datatype)==(layer,datatype)]
        if Counter(map(canonical,first))==Counter(map(canonical,second)):continue
        xor=gdstk.boolean(first,second,'xor',precision=.001)
        area=sum(p.area() for p in xor)
        if area>1e-6:
            if (layer,datatype) in metadata_layers:
                metadata[str((layer,datatype))]={'meaning':metadata_layers[(layer,datatype)],'xor_area_um2':area}
            else:differences[str((layer,datatype))]=area
    if differences:raise ValueError('Packaged core differs from final GDS subcell: '+str(differences))
    return {'status':'PASS_FABRICATION_XOR','layers_checked':len(layers),'fabrication_xor_area_um2':0,
            'non_fabrication_annotation_changes':metadata,
            'metadata_layer_mapping':'Installed sky130A.tech CIF output: MET3TXT 70/5, MET3PIN 70/16, BOUND 235/4',
            'mapping_sha256':sha(Path('/opt/pdks/sky130A/libs.tech/magic/sky130A.tech')),
            'precision_um':.001,'size_um':[367.5,238.5]}


def main():
    out=ROOT/'reports/phase2/delivery';out.mkdir(exist_ok=True)
    manifest=ROOT/'physical/phase2/delivery.json'
    with output_lock(out):
        result={'status':'RUNNING','publication':'LOCAL_ONLY','phase':'2','configuration':'4x8'}
        def publish():atomic_text(manifest,json.dumps(result,indent=2)+'\n')
        publish()
        try:
            selector=json.loads((ROOT/'physical/phase2/checkpoints.json').read_text())
            acceptance=ROOT/'reports/phase2/acceptance/results.json';approved=json.loads(acceptance.read_text())
            if approved['status']!='PASS_EXPERIMENTAL_4X8':raise ValueError('Complete experimental acceptance required before packaging')
            for key,expected in approved['receipt_sha256'].items():
                if sha(ROOT/selector[key]/'results.json')!=expected:raise ValueError('Acceptance selector changed: '+key)
            state=json.loads((ROOT/selector['integrated_layout']/'results.json').read_text())
            build=ROOT/state['build_directory'];gds=ROOT/selector['final_gds']/'sram_4x8.gds'
            proof=core_geometry(build/'leaf_fabric.gds',gds)
            for source,name in [(build/'leaf_fabric.gds','core_4x8.gds'),(build/'leaf_fabric.lef','core_4x8.lef')]:
                shutil.copyfile(source,out/name)
            atomic_text(out/'core_geometry.json',json.dumps(proof,indent=2)+'\n')
            raw=ROOT/'reports/phase2/portable_raw';portable=json.loads((raw/'results.json').read_text())
            if (portable['status']!='PASS_LOSSLESS_RAW' or portable['source_receipt_sha256']!=sha(ROOT/selector['extracted_access']/'results.json')
                    or sha(raw/'waveform.dat.gz')!=portable['compressed_sha256']):raise ValueError('Portable full trace incomplete/stale')
            def file(path):
                path=Path(path);return {'path':str(path.relative_to(ROOT)),'sha256':sha(path),'bytes':path.stat().st_size}
            layout=ROOT/selector['integrated_layout'];access=ROOT/selector['extracted_access'];lef=ROOT/selector['top_abstract']
            physical_spice=(access/'binding.spice').read_text()
            ports=re.search(r'^\.subckt sram_4x8_wrapper (.+)$',physical_spice,re.M)[1].split()
            result.update(status='LOCAL_REVIEW_CANDIDATE',F2_DIG=approved['F2_DIG'],CORE=approved['CORE'],F2_FIS=approved['F2_FIS'],
                review='Advisor/team review pending; no commit, push, merge or project-wide closure performed',
                baseline_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                source_state='Uncommitted implementation on integration/phase2-4x8',
                phase1_selection=file(ROOT/'release/phase1_current.json'),
                core={'module':'leaf_fabric','gds':file(out/'core_4x8.gds'),'lef':file(out/'core_4x8.lef'),'geometry_in_top':file(out/'core_geometry.json'),
                      'boundary':'401-MOS storage/peripheral fabric; qualified row/data/phase signals are explicit external pins'},
                top={'module':'sram_4x8_wrapper','gds':file(gds),'lef':file(lef/'sram_4x8.lef'),
                     'spice':file(access/'binding.spice'),'spice_port_order':ports,
                     'spice_bus_aliases':{'ADDR[0]':'ADDR0','ADDR[1]':'ADDR1',**{f'DATA[{i}]':f'DATA{i}' for i in range(8)}},
                     'routed_powered_verilog':file(layout/'final_powered.v'),'def':file(layout/'final.def'),
                     'magic_flat':file(layout/'integrated_flat.mag'),'mos_before_parallel_reduction':1493,'footprint_um':[540,380]},
                functional_verilog_inputs=[file(ROOT/p) for p in ['rtl/sram_controller.v','rtl/sram_4x8_wrapper.v','rtl/sram_4x8_macro_model.v']],
                physical_generator_source=file(ROOT/'physical/phase2/macro_binding.v'),
                evidence={'acceptance':file(acceptance),'electrical_receipt':file(access/'results.json'),
                          'gds_lvs':file(ROOT/selector['final_gds']/'lvs.txt'),'gds_drc_transcript':file(ROOT/selector['final_gds']/'magic.txt'),
                          'routed_gls':file(ROOT/selector['routed_gls']/'gls.txt'),
                          'full_raw_gzip':file(raw/'waveform.dat.gz'),'raw_identity':file(raw/'results.json')},
                exclusions=['No characterized Liberty, Fmax or complete SRAM STA',
                            'No detailed wire R-C PEX, PVT/statistical startup or yield qualification',
                            'Phase 1 model-coverage/reliability disposition is retained',
                            'The GLS leaf_fabric model is verification-only and is not a physical deliverable'],
                reproduction='docs/phase2_execution.md; scripts/run_phase2.sh')
        except Exception as e:result.update(status='FAIL',error=str(e))
        publish();print(json.dumps({k:v for k,v in result.items() if k in ('status','F2_DIG','CORE','F2_FIS','error')},indent=2))
        return 0 if result['status']=='LOCAL_REVIEW_CANDIDATE' else 1


if __name__=='__main__':raise SystemExit(main())
