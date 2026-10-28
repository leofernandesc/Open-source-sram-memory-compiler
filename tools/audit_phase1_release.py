#!/usr/bin/env python3
"""Audit frozen inputs, generated symbols/netlists, PEX provenance and evidence."""
from __future__ import annotations
import csv
import hashlib
import json
import re
from pathlib import Path
from prepare_phase1_release import ROOT, DEST, CELLS, blob, set_widths


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    manifest=json.loads((DEST/'manifest.json').read_text())
    results=[]
    for name,item in manifest['cells'].items():
        for info in item['files'].values():
            assert sha(ROOT/info['path'])==info['sha256'],info['path']
        for kind,info in item['inputs'].items():
            original=blob(item['source_revision'],info['path'])
            assert hashlib.sha256(original).hexdigest()==info['sha256']
            expected=original
            if kind=='schematic' and CELLS[name]['widths']:
                expected=set_widths(original.decode(),CELLS[name]['widths']).encode()
            assert (ROOT/item['files'][kind]['path']).read_bytes()==expected
        physical=json.loads((ROOT/item['physical_result']).read_text())
        assert physical['status']=='PASS'
        assert physical['mos_count']==item['expected_mos']
        assert physical['source_sha256']==item['files']['spice']['sha256']
        assert physical['symbol_sha256']==item['files']['symbol']['sha256']
        assert physical['layout_sha256']==item['files']['layout']['sha256']
        assert physical['pex_sha256']==item['files']['pex']['sha256']
        evidence_dir=ROOT/item['physical_result']
        evidence_dir=evidence_dir.parent
        assert sha(evidence_dir/'layout_extracted.spice')==physical['extracted_sha256']
        for filename,checksum in physical['evidence_sha256'].items():
            assert sha(evidence_dir/filename)==checksum,(name,filename)
        assert physical['pex_connectivity_binding']=='PASS_PARASITIC_RESISTORS_COLLAPSED'
        assert physical['negative_controls']==dict.fromkeys(
            ('width','length','gate','bulk','model'),'REJECTED_AS_EXPECTED')
        symbol=(ROOT/item['files']['symbol']['path']).read_text()
        symbol_pins=re.findall(r'^B 5 .*?\{name=(\S+)\s+dir=',symbol,re.M)
        assert symbol_pins==physical['pins'],(name,symbol_pins,physical['pins'])
        results.append(dict(cell=name,status='PASS',checks='source provenance, exact mask/PEX hashes, symbol pin order, physical result and negative controls'))
    columns={'bitcell':'bitcell_6t','precharge':'precharge','wl_driver':'wl_driver',
             'write_driver':'write_driver','sense':'sense_amp','sense_amp':'sense_amp'}
    electrical=[]
    for name,info in manifest['electrical_evidence'].items():
        path=ROOT/info['path']
        assert sha(path)==info['sha256']
        rows=list(csv.DictReader(path.open()))
        assert rows and all(r['status']=='PASS' for r in rows)
        checks=0
        for row in rows:
            for column,cell in columns.items():
                key=column+'_source_sha256'
                if key in row:
                    assert row[key]==manifest['cells'][cell]['files']['pex']['sha256'],(name,key)
                    checks+=1
        assert checks>=len(rows)*3,(name,'missing leaf provenance')
        electrical.append(dict(file=name,cases=len(rows),status='PASS',pex_hash_checks=checks))
    summary=json.loads((DEST/'verification/summary.json').read_text())
    assert summary['status']=='PASS' and len(summary['cells'])==6
    for script,checksum in summary['scripts_sha256'].items():
        assert sha(ROOT/'tools'/script)==checksum,script
    support=DEST/'support/g7_column'
    g7=json.loads((support/'result.json').read_text())
    assert g7['status']=='PASS' and g7['mos_count']==212 and g7['drc_groups']==0
    assert sha(ROOT/'tools/verify_phase1_g7_support.py')==g7['script_sha256']
    for filename,checksum in g7['evidence_sha256'].items():
        assert sha(support/filename)==checksum,filename
    for cell,checksum in g7['schematic_leaf_hashes'].items():
        assert manifest['cells'][cell]['files']['spice']['sha256']==checksum,cell
    for filename,info in g7['inputs'].items():
        assert (support/filename).read_bytes()==blob(info['source_revision'],info['source_path'])
    result=dict(status='PASS',cells=results,electrical=electrical,
        supporting_g7_column='PASS_DRC_AND_PARAMETER_AWARE_LVS_212_MOS',
        limits='Audit of existing electrical CSVs and physical reruns; no new electrical simulation or R-C extraction.')
    (DEST/'verification/release_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    checksums={str(p.relative_to(ROOT)):sha(p) for p in sorted(DEST.rglob('*'))
               if p.is_file() and p.name!='checksums.json'}
    (DEST/'checksums.json').write_text(json.dumps(checksums,indent=2)+'\n')
    print(f'PASS: {len(results)} cells, 30 negative controls, G7 support column, {sum(e["cases"] for e in electrical)} archived electrical cases, exact PEX provenance.')


if __name__=='__main__':
    main()
