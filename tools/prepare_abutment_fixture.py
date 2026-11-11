#!/usr/bin/env python3
"""Prepare probes/fixture from NEW GDS extraction; this is not a test PASS."""
import argparse,json,re
from pathlib import Path
from run_phase2_digital import ROOT,sha
from run_phase2_access import bench,PDK
from run_phase2_extracted_access import model_closure
from phase2_extracted import bind


def main():
    p=argparse.ArgumentParser();p.add_argument('--gds-report',type=Path,required=True)
    p.add_argument('--layout-report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    gds=(ROOT/a.gds_report).resolve();layout=(ROOT/a.layout_report).resolve();out=(ROOT/a.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2/direct_abutment_20261111') or out.exists():p.error('New candidate fixture directory required')
    out.mkdir(parents=True)
    proof=json.loads((gds/'results.json').read_text())
    if proof['status']!='PASS_GEOMETRY_LVS':raise ValueError('New GDS DRC/LVS required')
    for name,h in proof['artifacts'].items():
        if sha(gds/name)!=h:raise ValueError('Changed GDS artifact '+name)
    design_path=layout/'routed_reference.json';design=json.loads(design_path.read_text())
    sources=[gds/'results.json',gds/'final_extracted.spice',gds/'final_flat.ext',design_path,
             Path(__file__),ROOT/'tools/phase2_extracted.py',ROOT/'tools/run_phase2_access.py']
    flat,probes,identity=bind(sources[1].read_text(),sources[2].read_text(),design)
    ports=re.search(r'^\.subckt \S+ (.+)$',flat,re.M)[1].split()
    deck,cycles,vectors,inputs,clocks=bench(dict(ports=ports),design,False)
    for old,new in probes.items():deck=deck.replace(old,new)
    vectors=[probes[v] for v in vectors];inputs=[probes[v] for v in inputs];clocks=[probes[v] for v in clocks]
    (out/'binding.spice').write_text(flat);(out/'fabric.spice').write_text('* Fabric is already in the extracted flat circuit\n')
    (out/'bench.spice').write_text(deck)
    result=dict(status='PREPARED_EXTRACTED_FIXTURE',scope='Input preparation only; no electrical simulation or approval',
                inputs={str(q):sha(q) for q in sources},model_inputs=model_closure(PDK/'libs.tech/ngspice/sky130.lib.spice'),
                binding_audit=identity,vectors=vectors,capture_inputs=inputs,capture_clocks=clocks,
                artifacts={q.name:sha(q) for q in out.iterdir() if q.is_file()})
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'])


if __name__=='__main__':main()
