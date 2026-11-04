#!/usr/bin/env python3
"""Retain a portable, losslessly compressed full electrical trace for review."""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
from run_digital_regression import atomic_text,output_lock
from run_phase2_digital import ROOT,sha


def main():
    selector=json.loads((ROOT/'physical/phase2/checkpoints.json').read_text())
    source=ROOT/selector['extracted_access'];out=ROOT/'reports/phase2/portable_raw';out.mkdir(exist_ok=True)
    with output_lock(out):
        result={'status':'RUNNING','scope':'Full-resolution raw trace, lossless gzip; no resimulation or downsampling'}
        def publish():atomic_text(out/'results.json',json.dumps(result,indent=2)+'\n')
        publish()
        try:
            receipt=json.loads((source/'results.json').read_text())
            if receipt['status']!='PASS_EXTRACTED_NOMINAL_ACCESS' or receipt['quick']:raise ValueError('Complete extracted access required')
            identity=sha(source/'results.json');raw=ROOT/receipt['build_directory']/'waveform.dat'
            expected=receipt['raw_waveform_sha256']
            if sha(raw)!=expected:raise ValueError('Raw trace changed')
            compressed=out/'waveform.dat.gz';temporary=out/'waveform.dat.gz.tmp'
            with raw.open('rb') as original,temporary.open('wb') as file:
                with gzip.GzipFile(filename='',mode='wb',compresslevel=3,fileobj=file,mtime=0) as archive:
                    shutil.copyfileobj(original,archive)
            digest=hashlib.sha256()
            with gzip.open(temporary,'rb') as check:
                while chunk:=check.read(1024*1024):digest.update(chunk)
            if digest.hexdigest()!=expected or sha(source/'results.json')!=identity:raise ValueError('Compressed evidence/source mismatch')
            temporary.replace(compressed)
            layout=json.loads((ROOT/selector['integrated_layout']/'results.json').read_text())
            route=json.loads((ROOT/selector['route']/'results.json').read_text())
            archived={}
            for original,name in [(ROOT/layout['build_directory']/'routed_reference.json','routed_reference.json'),
                                  (ROOT/route['build_directory']/'binding.v','route_binding.v')]:
                shutil.copyfile(original,out/name)
                archived[str(original.relative_to(ROOT))]={'path':str((out/name).relative_to(ROOT)),'sha256':sha(original)}
            result.update(status='PASS_LOSSLESS_RAW',source_receipt_sha256=identity,
                          uncompressed_sha256=expected,compressed_sha256=sha(compressed),
                          uncompressed_bytes=raw.stat().st_size,compressed_bytes=compressed.stat().st_size,
                          archived_build_inputs=archived)
        except Exception as e:result.update(status='FAIL',error=str(e))
        publish();print(json.dumps(result,indent=2))
        return 0 if result['status']=='PASS_LOSSLESS_RAW' else 1


if __name__=='__main__':raise SystemExit(main())
