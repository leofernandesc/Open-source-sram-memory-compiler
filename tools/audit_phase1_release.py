#!/usr/bin/env python3
"""Audit frozen inputs and evidence with checks that remain active under -O."""
from __future__ import annotations
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from prepare_phase1_release import ROOT, DEST, CELLS, blob, set_widths


class AuditError(RuntimeError):
    """The release does not satisfy an acceptance condition."""


def require(condition, message):
    if not condition:
        raise AuditError(str(message))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    manifest=json.loads((DEST/'manifest.json').read_text())
    results=[]
    for name,item in manifest['cells'].items():
        for info in item['files'].values():
            require(sha(ROOT/info['path'])==info['sha256'], info['path'])
        for kind,info in item['inputs'].items():
            original=blob(item['source_revision'],info['path'])
            require(hashlib.sha256(original).hexdigest()==info['sha256'], f'{name}: upstream {kind} hash mismatch')
            expected=original
            if kind=='schematic' and CELLS[name]['widths']:
                expected=set_widths(original.decode(),CELLS[name]['widths']).encode()
            require((ROOT/item['files'][kind]['path']).read_bytes()==expected, f'{name}: {kind} differs from selected upstream variant')
        physical=json.loads((ROOT/item['physical_result']).read_text())
        require(physical['status']=='PASS', f'{name}: physical status is not PASS')
        require(physical['mos_count']==item['expected_mos'], f'{name}: unexpected MOS count')
        require(physical['source_sha256']==item['files']['spice']['sha256'], f'{name}: physical spice binding hash mismatch')
        require(physical['symbol_sha256']==item['files']['symbol']['sha256'], f'{name}: physical symbol binding hash mismatch')
        require(physical['layout_sha256']==item['files']['layout']['sha256'], f'{name}: physical layout binding hash mismatch')
        require(physical['pex_sha256']==item['files']['pex']['sha256'], f'{name}: physical pex binding hash mismatch')
        evidence_dir=ROOT/item['physical_result']
        evidence_dir=evidence_dir.parent
        require(sha(evidence_dir/'layout_extracted.spice')==physical['extracted_sha256'], f'{name}: extracted netlist hash mismatch')
        for filename,checksum in physical['evidence_sha256'].items():
            require(sha(evidence_dir/filename)==checksum, (name,filename))
        require(physical['pex_connectivity_binding']=='PASS_PARASITIC_RESISTORS_COLLAPSED', f'{name}: PEX connectivity binding is not PASS')
        require(physical['negative_controls']==dict.fromkeys(
            ('width','length','gate','bulk','model'),'REJECTED_AS_EXPECTED'), f'{name}: negative controls are incomplete or failed')
        symbol=(ROOT/item['files']['symbol']['path']).read_text()
        symbol_pins=re.findall(r'^B 5 .*?\{name=(\S+)\s+dir=',symbol,re.M)
        require(symbol_pins==physical['pins'], (name,symbol_pins,physical['pins']))
        results.append(dict(cell=name,status='PASS',checks='source provenance, exact mask/PEX hashes, symbol pin order, physical result and negative controls'))
    columns={'bitcell':'bitcell_6t','precharge':'precharge','wl_driver':'wl_driver',
             'write_driver':'write_driver','sense':'sense_amp','sense_amp':'sense_amp'}
    electrical=[]
    for name,info in manifest['electrical_evidence'].items():
        path=ROOT/info['path']
        require(sha(path)==info['sha256'], f'{name}: electrical CSV hash mismatch')
        rows=list(csv.DictReader(path.open()))
        require(rows and all(r['status']=='PASS' for r in rows), f'{name}: empty or failed electrical results')
        checks=0
        for row in rows:
            for column,cell in columns.items():
                key=column+'_source_sha256'
                if key in row:
                    require(row[key]==manifest['cells'][cell]['files']['pex']['sha256'], (name,key))
                    checks+=1
        require(checks>=len(rows)*3, (name,'missing leaf provenance'))
        electrical.append(dict(file=name,cases=len(rows),status='PASS',pex_hash_checks=checks))
    summary=json.loads((DEST/'verification/summary.json').read_text())
    require(summary['status']=='PASS' and len(summary['cells'])==6, 'Physical summary must report PASS for six cells')
    for script,checksum in summary['scripts_sha256'].items():
        require(sha(ROOT/'tools'/script)==checksum, script)
    support=DEST/'support/g7_column'
    g7=json.loads((support/'result.json').read_text())
    require(g7['status']=='PASS' and g7['mos_count']==212 and g7['drc_groups']==0, 'Supporting G7 status, MOS count or DRC did not pass')
    require(sha(ROOT/'tools/verify_phase1_g7_support.py')==g7['script_sha256'], 'G7 verification script hash mismatch')
    for filename,checksum in g7['evidence_sha256'].items():
        require(sha(support/filename)==checksum, filename)
    for cell,checksum in g7['schematic_leaf_hashes'].items():
        require(manifest['cells'][cell]['files']['spice']['sha256']==checksum, cell)
    for filename,info in g7['inputs'].items():
        require((support/filename).read_bytes()==blob(info['source_revision'],info['source_path']), f'G7 upstream input mismatch: {filename}')
    result=dict(status='PASS',cells=results,electrical=electrical,
        supporting_g7_column='PASS_DRC_AND_PARAMETER_AWARE_LVS_212_MOS',
        validation_policy='Explicit runtime checks, including under Python -O and -OO',
        limits='Audit of existing electrical CSVs and physical reruns; no new electrical simulation or R-C extraction.')
    (DEST/'verification/release_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    checksums={str(p.relative_to(ROOT)):sha(p) for p in sorted(DEST.rglob('*'))
               if p.is_file() and p.name!='checksums.json'}
    (DEST/'checksums.json').write_text(json.dumps(checksums,indent=2)+'\n')
    print(f'PASS: {len(results)} cells, 30 negative controls, G7 support column, {sum(e["cases"] for e in electrical)} archived electrical cases, exact PEX provenance.')


def cli():
    try:
        main()
    except Exception as error:
        message=f'{type(error).__name__}: {error}'
        # Replace a stale PASS report; do not update checksums on a failed audit.
        try:
            directory=DEST/'verification'
            directory.mkdir(parents=True,exist_ok=True)
            (directory/'release_audit.json').write_text(json.dumps(
                dict(status='FAIL',error=message),indent=2)+'\n')
        except OSError as report_error:
            print(f'Unable to write failure report: {report_error}',file=sys.stderr)
        print('FAIL: '+message,file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':
    raise SystemExit(cli())
