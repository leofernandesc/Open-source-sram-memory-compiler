#!/usr/bin/env python3
"""Optional lossless transfer bundle; raw bytes are never added to Git here."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT/'release/phase2_experimental/raw_bundle.json'
RECEIPTS = {
    'baseline': 'reports/phase2/extracted_access_singlethread/results.json',
    'directed': 'reports/phase2/review_20261104/directed/results.json',
    'r1_idle0': 'reports/phase2/final_polish_20261104/startup_reduced/r1_idle0/results.json',
    **{n: f'reports/phase2/final_polish_20261104/startup_extended/{n}/results.json'
       for n in ('r1_idle2','r5_idle2','r10_idle2','r1_idle3')},
}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while b := f.read(1024*1024): h.update(b)
    return h.hexdigest()


def members(root=ROOT):
    found = []
    for name, rel in RECEIPTS.items():
        r = json.loads((root/rel).read_text())
        if r['status'] not in ('PASS','PASS_DIRECTED_NOMINAL','PASS_EXTRACTED_NOMINAL_ACCESS'):
            raise ValueError('Completed raw source required: '+rel)
        dest = (root/r['build_directory']/'waveform.dat').resolve()
        if not dest.is_relative_to((root/'build/phase2').resolve()):
            raise ValueError('Unsafe receipt build path')
        found.append(dict(member=name+'/waveform.dat', receipt=rel, receipt_sha256=digest(root/rel),
                          target=str(dest.relative_to(root)), sha256=r['raw_waveform_sha256']))
    return found


def verify(archive, expected, restore=False, root=ROOT):
    """No extractall: match a fixed whitelist and install only missing raw files."""
    wanted = {m['member']: m for m in expected}; seen = set(); installed = []
    with tarfile.open(archive, 'r:gz') as tar:
        for item in tar:
            if not item.isfile() or item.name not in wanted or item.name in seen:
                raise ValueError('Unexpected/duplicate/non-file archive member')
            seen.add(item.name); m = wanted[item.name]
            dest = (root/m['target']).resolve()
            if not dest.is_relative_to((root/'build/phase2').resolve()):
                raise ValueError('Unsafe restore target')
            if restore and dest.exists() and digest(dest) != m['sha256']:
                raise ValueError('Conflicting existing raw; nothing is overwritten')
            temp = None
            if restore and not dest.exists():
                dest.parent.mkdir(parents=True,exist_ok=True)
                fd, name = tempfile.mkstemp(prefix='raw-restore-',dir=dest.parent)
                os.close(fd); temp = Path(name)
            h = hashlib.sha256(); size = 0
            try:
                output = temp.open('wb') if temp else None
                try:
                    stream = tar.extractfile(item)
                    while b := stream.read(1024*1024):
                        h.update(b); size += len(b)
                        if output: output.write(b)
                finally:
                    if output: output.close()
                if h.hexdigest() != m['sha256'] or size != item.size:
                    raise ValueError('Raw archive identity differs')
                if temp:
                    # Publish only after full verification; original files untouched.
                    if dest.exists(): raise ValueError('Restore target appeared concurrently')
                    temp.rename(dest); installed.append(m['target'])
            finally:
                if temp and temp.exists(): temp.unlink()  # this command's own temporary file only
    if seen != set(wanted): raise ValueError('Missing raw archive member')
    return installed


def main():
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--output'); g.add_argument('--restore'); g.add_argument('--verify')
    args = p.parse_args(); expected = members()
    if args.output:
        target = (ROOT/args.output).resolve()
        if not target.is_relative_to(ROOT/'build/phase2') or target.exists():
            p.error('Use a new bundle under build/phase2')
        if shutil.disk_usage(ROOT).free < 512*2**20: raise ValueError('Insufficient free disk for optional raw bundle')
        target.parent.mkdir(parents=True,exist_ok=True)
        # Constant metadata gives repeatable archives for identical raw inputs.
        with target.open('xb') as raw, gzip.GzipFile(fileobj=raw, filename='',mode='wb',mtime=0,compresslevel=3) as gz:
            with tarfile.open(fileobj=gz,mode='w|') as tar:
                for m in expected:
                    path = ROOT/m['target']
                    if digest(path) != m['sha256']: raise ValueError('Changed raw input')
                    info = tarfile.TarInfo(m['member']); info.size=path.stat().st_size; info.mode=0o444; info.mtime=0
                    with path.open('rb') as f: tar.addfile(info,f)
        verify(target,expected)
        record = dict(status='PASS_LOSSLESS_RAW_ROUNDTRIP',scope='Optional local transfer file, not a GitHub-hosted artifact or cross-platform execution',
                      path=str(target.relative_to(ROOT)),sha256=digest(target),bytes=target.stat().st_size,
                      members=expected,restoration='Fixed receipt targets under build/phase2 only; matching existing files skipped')
        if INDEX.exists(): raise ValueError('Raw bundle index already exists; preserve it and use its selected bundle')
        INDEX.parent.mkdir(parents=True,exist_ok=True);INDEX.write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps(record,indent=2))
    else:
        archive = Path(args.restore or args.verify)
        index = json.loads(INDEX.read_text())
        if digest(archive) != index['sha256'] or index['members'] != expected: raise ValueError('Wrong transfer bundle or changed receipt inputs')
        # First pass validates every byte before any optional restoration.
        verify(archive,expected)
        installed = verify(archive,expected,True) if args.restore else []
        print(json.dumps(dict(status='PASS',restored=installed,verified_members=len(expected))))


if __name__=='__main__': main()
