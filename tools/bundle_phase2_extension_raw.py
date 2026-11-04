#!/usr/bin/env python3
"""Use the existing optional lossless raw-bundle format for extension inputs."""
import argparse
import gzip
import json
import shutil
import tarfile
from pathlib import Path
from bundle_phase2_raw import ROOT,digest,verify

INDEX=ROOT/'reports/phase2/extension_20261104/raw_bundle.json'
CASES=('c1_pilot','c1_sequences','c2_bus')


def members():
    result=[]
    for name in CASES:
        rel=f'reports/phase2/extension_20261104/{name}/results.json'
        r=json.loads((ROOT/rel).read_text())
        if r['status'] not in ('PASS','FAIL_ELECTRICAL_SCREEN'):raise ValueError('Complete scenario required')
        dest=(ROOT/r['build_directory']/'waveform.dat').resolve()
        if not dest.is_relative_to((ROOT/'build/phase2').resolve()):raise ValueError('Unsafe raw path')
        result.append(dict(member=name+'/waveform.dat',receipt=rel,receipt_sha256=digest(ROOT/rel),
                           target=str(dest.relative_to(ROOT)),sha256=r['raw_sha256']))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--output');g.add_argument('--verify');g.add_argument('--restore');a=p.parse_args();expected=members()
    if a.output:
        dest=(ROOT/a.output).resolve()
        if not dest.is_relative_to(ROOT/'build/phase2') or dest.exists() or INDEX.exists():p.error('New archive and index required')
        if shutil.disk_usage(ROOT).free<512*2**20:raise ValueError('Insufficient free disk; do not remove historical data')
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f,gzip.GzipFile(fileobj=f,filename='',mode='wb',mtime=0,compresslevel=3) as gz:
            with tarfile.open(fileobj=gz,mode='w|') as tar:
                for m in expected:
                    path=ROOT/m['target']
                    if digest(path)!=m['sha256']:raise ValueError('Changed raw')
                    info=tarfile.TarInfo(m['member']);info.size=path.stat().st_size;info.mode=0o444;info.mtime=0
                    with path.open('rb') as data:tar.addfile(info,data)
        verify(dest,expected)
        INDEX.write_text(json.dumps(dict(status='PASS_LOSSLESS_RAW_ROUNDTRIP',path=str(dest.relative_to(ROOT)),
            sha256=digest(dest),bytes=dest.stat().st_size,members=expected,
            scope='Optional local transfer file; no raw uploaded to GitHub; same whitelist verifier as original bundle'),indent=2)+'\n')
    else:
        dest=Path(a.restore or a.verify);index=json.loads(INDEX.read_text())
        if digest(dest)!=index['sha256'] or expected!=index['members']:raise ValueError('Wrong bundle or changed receipts')
        verify(dest,expected);installed=verify(dest,expected,True) if a.restore else []
        print(json.dumps(dict(status='PASS',verified_members=len(expected),restored=installed)))


if __name__=='__main__':raise SystemExit(main())
