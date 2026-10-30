"""Bind reusable SPICE rows to settings, leaves, models and executable code."""
import hashlib
import json
from pathlib import Path
import re
import shutil


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def model_hashes(library):
    pending=[Path(library).resolve()]
    hashes={}
    while pending:
        path=pending.pop()
        if str(path) in hashes:
            continue
        content=path.read_bytes()
        hashes[str(path)]=hashlib.sha256(content).hexdigest()
        text=re.sub(r'\n\s*\+\s*',' ',content.decode())
        for line in text.splitlines():
            match=re.match(r'''(?i)^\s*\.inc(?:lude)?\s+(?:"([^"]+)"|'([^']+)'|(\S+))''',line)
            if match:
                name=next(v for v in match.groups() if v is not None)
                pending.append((path.parent/name).resolve())
    return dict(sorted(hashes.items()))


def campaign_contract(args, leafs, runner, library):
    """Exclude execution/output choices, never electrical conditions or sources."""
    ignored={'root','resume','output','parts_dir','workers','timeout_s'}
    def value(item):
        if isinstance(item,Path):
            return dict(path=str(item.resolve()),sha256=sha(item))
        if isinstance(item,(list,tuple)):
            return [value(v) for v in item]
        return item
    executable=shutil.which('ngspice')
    dependencies=[Path(__file__),Path(runner),Path(__file__).with_name('pex_access_nodes.py')]
    payload=dict(settings={k:value(v) for k,v in vars(args).items() if k not in ignored},
        leaves={k:hashlib.sha256(v.encode()).hexdigest() for k,v in leafs.items()},
        models=model_hashes(library),scripts={p.name:sha(p) for p in dependencies},
        ngspice_sha256=sha(executable) if executable else None)
    return hashlib.sha256(json.dumps(payload,sort_keys=True,allow_nan=False).encode()).hexdigest()


def reusable(row, contract):
    return row is not None and row.get('status')=='PASS' and row.get('cache_contract_sha256')==contract
