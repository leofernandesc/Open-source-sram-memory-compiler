#!/usr/bin/env python3
"""Read-only integrity check of the recorded reconciliation experiments."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import freeze_keeper_revision as frozen


def main():
    index=json.loads((ROOT/'sims/integration/results/checksums_20261030.json').read_text())
    frozen.ensure(bool(index),'Empty integration evidence index')
    for name,expected in index.items():
        path=(ROOT/name).resolve()
        frozen.ensure(path.is_relative_to(ROOT/'sims/integration/results'),'Evidence path escapes its directory')
        frozen.ensure(hashlib.sha256(path.read_bytes()).hexdigest()==expected,'Changed integration evidence: '+name)
    review=json.loads((ROOT/'sims/integration/results/review_20261030.json').read_text())
    frozen.ensure(review['status']=='PASS' and review['scope']=='PHASE1_REPOSITORY_RECONCILIATION_NOT_FULL_MACRO',
                  'Wrong reconciliation conclusion/scope')
    current=frozen.check()
    print(json.dumps(dict(status='PASS',integration_artifacts=len(index),frozen_delivery=current,
        scope='Integrity of recorded evidence; no new simulation/physical run or SRAM macro qualification.'),indent=2))


if __name__=='__main__':main()
