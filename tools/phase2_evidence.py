"""Small strict integrity guards shared by Phase 2 audit and delivery.

Hashes detect stale/changed local artifacts, not hostile rewriting of every
receipt. Legacy output inventories are explicitly dated review observations.
"""
import hashlib
import math
from pathlib import Path
import re
import json


def digest(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):result.update(chunk)
    return result.hexdigest()


def finite(value,label):
    if isinstance(value,bool) or value is None:raise ValueError('Invalid numeric evidence: '+label)
    try:result=float(value)
    except (ValueError,TypeError) as error:raise ValueError('Invalid numeric evidence: '+label) from error
    if not math.isfinite(result):raise ValueError('Nonfinite numeric evidence: '+label)
    return result


def hashes(entries,required=()):
    if not isinstance(entries,dict) or not entries or not set(required)<=set(entries):
        raise ValueError('Missing mandatory evidence inventory')
    if any(not isinstance(k,str) or not isinstance(v,str) or not re.fullmatch('[0-9a-f]{64}',v) for k,v in entries.items()):
        raise ValueError('Malformed evidence hash inventory')


def stage_inventory(root,directory,state,required):
    """Require producer hashes, or the pinned pre-review inventory of a legacy run."""
    if 'artifacts' in state:
        inventory=state['artifacts']
    else:
        path=root/'physical/phase2/history/legacy_artifacts_20261104.json'
        previous=json.loads(path.read_text())['stages'].get(str(directory.relative_to(root)))
        if not previous or previous['receipt_sha256']!=digest(directory/'results.json'):
            raise ValueError('Legacy stage has no matching review inventory: '+str(directory))
        inventory=previous['artifacts']
    hashes(inventory,required)
    for name,expected in inventory.items():
        if Path(name).name!=name or digest(directory/name)!=expected:
            raise ValueError('Changed stage artifact: '+str(directory/name))
    return [directory/name for name in inventory]


def seal(root,paths):
    result={}
    for path in paths:
        path=Path(path).resolve()
        key=str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        result[key]=digest(path)
    hashes(result)
    return dict(sorted(result.items()))


def verify_seal(root,approved,required):
    inventory=approved.get('verified_files')
    hashes(inventory,required)
    # Verify the actual proposed payload first, before optional build metadata.
    ordered=list(required)+[p for p in inventory if p not in required]
    for name in ordered:
        path=Path(name) if Path(name).is_absolute() else root/name
        if not path.is_file() or digest(path)!=inventory[name]:
            raise ValueError('Delivery artifact changed since audit: '+name)
