#!/usr/bin/env python3
"""Select the qualified keeper revision without rewriting the 29-MOS freeze.

--check is read-only and uses explicit checks under normal and optimized Python.
"""
import argparse
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/'release/phase1_keeper'
NAMES={'bitcell_6t','sense_amp','precharge','wl_driver','write_driver','row_decoder'}


def ensure(condition,message):
    if not condition:raise ValueError(message)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def check_case(directory,row,required):
    """Reconcile the saved checks and all 49-device intrinsic magnitude probes."""
    with (directory/'checks.csv').open() as handle:checks=list(csv.DictReader(handle))
    expected={f'{family}{r}_{stage}' for family in ('DEC','WL') for r in range(4)
              for stage in ('priming','final_precharge')}
    expected.update(f'N{r}_precharge_min' for r in range(4))
    expected.update(f'{family}{r}_unselected_peak' for family in ('DEC','WL') for r in range(4) if r!=row['new'])
    expected.update(('all_outputs_reset_dwell_ns','selected_DEC_WL_high90_dwell_ns','all_literals_stable_lead_ps'))
    ensure(len(checks)==29 and {r['check'] for r in checks}==expected,'Incomplete/duplicate check set')
    failed=0
    for check in checks:
        value=float(check['value']);passed=math.isfinite(value) and float(check['min'])<=value<=float(check['max'])
        ensure(check['status']==('PASS' if passed else 'FAIL'),'Check flag hides its numeric value')
        failed+=not passed
    ensure(row['checks_fail']==failed and row['checks_pass']==29-failed,'Case/check counts differ')
    with (directory/'intrinsic_magnitudes.csv').open() as handle:probes=list(csv.DictReader(handle))
    devices={r['device'] for r in probes}
    ensure(len(probes)==196 and len(devices)==49 and len({(r['device'],r['metric']) for r in probes})==196 and
           {r['metric'] for r in probes}=={'VGS','VGD','VDS','VGB'},'Incomplete intrinsic device coverage')
    values=[float(r['abs_max_v']) for r in probes]
    ensure(all(math.isfinite(v) and v>=0 for v in values) and
           abs(max(values)-row['max_intrinsic_magnitude_v'])<1e-9,'Magnitude result differs from saved probes')
    if required:
        ensure(failed==0 and row['timing_screen']=='PASS' and row['voltage_screen']=='PASS' and max(values)<=1.95,
               'Required experimental screen failed')
    return 29-failed


def check(root=ROOT,release=RELEASE):
    index=json.loads((release/'checksums.json').read_text())
    for name,expected in index.items():ensure(sha(root/name)==expected,f'Changed artifact: {name}')
    m=json.loads((release/'manifest.json').read_text())
    old=json.loads((root/'release/phase1/manifest.json').read_text())
    oldindex=json.loads((root/'release/phase1/checksums.json').read_text())
    for name,expected in oldindex.items():
        ensure(index.get(name)==expected and sha(root/name)==expected,'Historical evidence missing/changed')
    ensure(set(m['cells'])==NAMES,'The revision must select exactly six cells')
    ensure(m['cells']['row_decoder']['expected_mos']==33,'Wrong hardened decoder count')
    for name in NAMES-{'row_decoder'}:ensure(m['cells'][name]==old['cells'][name],f'Other owner/leaf changed: {name}')
    for name,item in m['cells'].items():
        for info in item['files'].values():
            ensure(info['path'] in index and sha(root/info['path'])==info['sha256'],f'Unbound {name} artifact')
    proof=json.loads((root/m['cells']['row_decoder']['physical_result']).read_text())
    ensure(proof['status']=='PASS' and proof['mos_count']==33 and proof['drc_groups']==0 and
        proof['lvs']=='UNIQUE_MATCH_WITH_W_L_AND_TERMINALS' and len(proof['negative_controls'])==5 and
        set(proof['negative_controls'].values())=={'REJECTED_AS_EXPECTED'},'Incomplete physical closure')
    review=json.loads((root/m['electrical_review']).read_text())
    ensure(m['electrical_review'] in index and m['cells']['row_decoder']['physical_result'] in index,
           'Unindexed electrical/physical conclusion')
    ensure(review['status']=='PASS_PROJECT_SCREENS_WITH_MODEL_COVERAGE_LIMITATION' and review['functional_cases']==48 and
        review['functional_checks']==1392 and review['crossed_pvt_points']==30,'Incomplete electrical coverage')
    ensure(review['signed_gate_findings_remain'] and review['signed_vds_vbs_outside_after_2ns']==0,
        'Model coverage disposition missing/changed')
    counted=0;passes=0;boundary=0;functional=set();pvt=set()
    for entry in review['campaigns'].values():
        ensure(entry['path'] in index and sha(root/entry['path'])==entry['sha256'],'Unbound campaign manifest')
        campaign=json.loads((root/entry['path']).read_text());directory=(root/entry['path']).parent
        ensure(campaign['complete'],'Incomplete campaign')
        required='charge_boundary' not in directory.name
        if not required:ensure(campaign['kind']=='charge_down' and campaign['value']==32,'Wrong boundary-test classification')
        for case in campaign['cases']:
            ensure(case['status']=='MEASURED','Case execution failed')
            folder=directory/case['case']
            for name in ('case.spice','checks.csv','intrinsic_magnitudes.csv'):
                ensure(str((folder/name).relative_to(root)) in index,'Unindexed case evidence')
            ensure(sha(folder/'case.spice')==case['deck_sha256'],'Case deck changed')
            good=check_case(folder,case,required)
            if required:counted+=1;passes+=good
            else:boundary+=1
            if '_functional_' in directory.name:functional.add((case['profile'],case['old'],case['new']))
            if '_pvt_' in directory.name or ('_functional_' in directory.name and (case['old'],case['new'])==(1,2)):
                pvt.add(tuple(campaign['profiles'][case['profile']]))
    ensure(counted==review['mandatory_post_layout_cases']==105 and passes==review['mandatory_checks']==3045 and
        boundary==review['boundary_cases']==5,'Final campaign accounting differs')
    ensure(functional=={(p,a,b) for p in ('tt','ss','ff') for a in range(4) for b in range(4)},'Address matrix incomplete')
    ensure(pvt=={(c,v,t) for c in ('tt','ss','ff','sf','fs') for v in (1.62,1.8) for t in (-40,27,125)},'Crossed PVT matrix incomplete')
    row=m['cells']['row_decoder']
    ensure(proof['layout_sha256']==row['files']['layout']['sha256'] and proof['pex_sha256']==row['files']['pex']['sha256'] and
        proof['source_sha256']==row['files']['spice']['sha256'],'Physical proof belongs to different files')
    for name,digest in proof['evidence_sha256'].items():
        path=(root/row['physical_result']).parent/name
        ensure(str(path.relative_to(root)) in index and sha(path)==digest,'Unbound physical evidence')
    ensure(sha(root/m['base_checksums']['path'])==m['base_checksums']['sha256'],'Historical index changed')
    pointer=json.loads((root/'release/phase1_current.json').read_text())
    ensure(pointer['manifest']==str((release/'manifest.json').relative_to(root)) and
        pointer['checksums_sha256']==sha(release/'checksums.json'),'Active pointer differs')
    return dict(status='PASS',indexed_files=len(index),cells=6,row_decoder_mos=33,
        electrical_status=review['status'],historical_freeze_preserved=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');args=p.parse_args()
    if args.check:print(json.dumps(check(),indent=2));return
    ensure(not RELEASE.exists(),'Use --check for an existing revision; never overwrite a release')
    base=ROOT/'release/phase1';oldindex=json.loads((base/'checksums.json').read_text())
    for name,expected in oldindex.items():ensure(sha(ROOT/name)==expected,'Historical six-cell freeze changed')
    reviewpath=ROOT/'sims/row_decoder/results/keeper_review_20261029/summary.json'
    review=json.loads(reviewpath.read_text())
    ensure(review['status']=='PASS_PROJECT_SCREENS_WITH_MODEL_COVERAGE_LIMITATION','Complete electrical review required')
    manifest=copy.deepcopy(json.loads((base/'manifest.json').read_text()))
    target=RELEASE/'cells/row_decoder';target.mkdir(parents=True)
    source=ROOT/'cells/row_decoder/variants/keeper_0p84';layout=ROOT/'layout/row_decoder_keeper'
    sources=dict(schematic=source/'row_decoder.sch',symbol=source/'row_decoder.sym',spice=source/'row_decoder.spice',
        layout=layout/'row_decoder_flat.mag',pex=layout/'pex/row_decoder_pex.spice')
    filenames=dict(schematic='row_decoder.sch',symbol='row_decoder.sym',spice='row_decoder.spice',
                   layout='row_decoder.mag',pex='row_decoder_pex.spice')
    files={}
    for key,path in sources.items():
        output=target/filenames[key];shutil.copy2(path,output)
        files[key]=dict(path=str(output.relative_to(ROOT)),sha256=sha(output))
    shutil.copytree(layout/'qualification/verification/row_decoder',RELEASE/'verification/row_decoder')
    shutil.copytree(layout/'archive',RELEASE/'development_evidence')
    extraction=RELEASE/'verification/extraction';extraction.mkdir()
    for name in ('extraction_manifest.json','provenance.json'):
        shutil.copy2(layout/'pex'/name,extraction/name)
    for name in ('extract.log','drc_flat.log','route.log','lvs.out'):
        shutil.copy2(layout/'reports'/name,extraction/(name.replace('.','_')+'.txt'))
    for name in ('routing_plan.json','route_row_decoder.tcl','row_decoder_import.spice'):
        shutil.copy2(layout/name,extraction/name)
    widths={}
    text=(source/'row_decoder.sch').read_text()
    for name,width in re.findall(r'name=(M\d+)\s+W=([\d.]+)',text):widths[name]=width
    ensure(len(widths)==33,'Incomplete width binding')
    manifest.update(scope='Six Phase 1 leaves, hardened Leonardo decoder revision 2026-10-29',
        decision='Dynamic PCLK NAND decoder retained; four W0.84/L0.15 PMOS feedback keepers added. Other five leaf selections unchanged.',
        base_checksums=dict(path='release/phase1/checksums.json',sha256=sha(base/'checksums.json')),
        electrical_review=str(reviewpath.relative_to(ROOT)),
        limitation=review['limitation'])
    manifest['cells']['row_decoder']=dict(owner='Leonardo',expected_mos=33,widths=widths,
        source_revision='Content-addressed 2026-10-29 keeper revision; exact worktree inputs below.',
        pin_order=['VDD','PCLK','A0','A1','DEC0','DEC1','DEC3','DEC2','VSS'],
        inputs={k:dict(path=str(v.relative_to(ROOT)),sha256=sha(v)) for k,v in sources.items()},files=files,
        physical_result='release/phase1_keeper/verification/row_decoder/result.json')
    (RELEASE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    lines=['# Phase 1 selected keeper revision — 2026-10-29','',
        'Exactly six leaves. Leonardo\'s dynamic decoder is retained and hardened with four feedback PMOS keepers.',
        'The five other selections are identical to the original six-cell freeze.','',
        '| Cell | MOS | SCH | SYM | SPICE | MAG | PEX | Physical result |',
        '|---|---:|---|---|---|---|---|---|']
    for name,item in manifest['cells'].items():
        links=['['+key.upper()+'](../../'+item['files'][key]['path']+')' for key in ('schematic','symbol','spice','layout','pex')]
        lines.append('| '+name+' | '+str(item['expected_mos'])+' | '+' | '.join(links)+' | [result](../../'+item['physical_result']+') |')
    lines+=['','The [electrical review](../../'+manifest['electrical_review']+') records 48 address cases and 30 crossed PVT points.',
        'Functional and experimental terminal-magnitude checks do not establish independent off-state model accuracy, statistical yield or foundry reliability.',
        'See [engineering analysis](../../docs/row_decoder_robustness_20261029.md). The [29-MOS freeze](../phase1/README.md) remains byte-for-byte unchanged.','',
        'Read-only audit: `python3 tools/freeze_keeper_revision.py --check`.','']
    (RELEASE/'README.md').write_text('\n'.join(lines))
    # Copy mutable worktree sources into the release instead of making later
    # legitimate source/layout development invalidate the archived selection.
    source_files=set(p for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for pattern in ('*keeper*.py','*robustness*.py','*offstate*.py','audit_sky130_measurements.py','run_canonical*.py'):
        source_files.update((ROOT/'sims/row_decoder').glob(pattern))
    source_files.update([Path(__file__),ROOT/'tools/verify_decoder_keeper.py',ROOT/'tools/generate_decoder_keeper.py',
        ROOT/'tools/verify_phase1_physical.py',ROOT/'layout/row_decoder/build_layout.py',
        ROOT/'layout/row_decoder/compact_routing.py',layout/'build_layout.py',
        ROOT/'tools/reports/magic_8_3_684_20261029.txt',ROOT/'docs/row_decoder_robustness_20261029.md',
        ROOT/'tools/tests/test_keeper_release_evidence.py',ROOT/'specs/technical_specification.md',ROOT/'GITFLOW.md'])
    for path in source_files:
        output=RELEASE/'source_snapshot'/path.relative_to(ROOT)
        output.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,output)
    selected=set(ROOT/name for name in oldindex)
    selected.update(p for p in RELEASE.rglob('*') if p.is_file())
    results=ROOT/'sims/row_decoder/results'
    for pattern in ('keeper*20261029*','robustness*20261029','offstate*20261029'):
        for path in results.glob(pattern):
            selected.update(p for p in (path.rglob('*') if path.is_dir() else [path]) if p.is_file() and p.suffix!='.raw')
    selected.update(p for p in (ROOT/'sims/row_decoder/inputs/sky130_measured_20261029').rglob('*') if p.is_file())
    selected={p for p in selected if '__pycache__' not in p.parts}
    index={str(p.relative_to(ROOT)):sha(p) for p in sorted(selected)}
    (RELEASE/'checksums.json').write_text(json.dumps(index,indent=2)+'\n')
    (ROOT/'release/phase1_current.json').write_text(json.dumps(dict(
        manifest='release/phase1_keeper/manifest.json',checksums_sha256=sha(RELEASE/'checksums.json'),
        historical_baseline='release/phase1/manifest.json',
        electrical_status=review['status']),indent=2)+'\n')
    print(json.dumps(check(),indent=2))


if __name__=='__main__':main()
