#!/usr/bin/env python3
"""Independently verify the keeper masks, dimensions, terminals and PEX binding.

Reuse the Phase 1 primitive-MOS audit, including all five deliberate faults.
The original six-cell freeze and Danilo's sources are read-only.
"""
import json
from pathlib import Path
import verify_phase1_physical as physical

ROOT=physical.ROOT
LAYOUT=ROOT/'layout/row_decoder_keeper'
SOURCE=ROOT/'cells/row_decoder/variants/keeper_0p84'


def main():
    state=json.loads((LAYOUT/'pex/provenance.json').read_text())
    if state['status']!='current' or not state['lvs_unique_match']:
        raise ValueError('New R-C extraction/geometry binding is not current')
    for item in state['files'].values():
        if physical.sha(ROOT/item['path'])!=item['sha256']:raise ValueError('Changed extraction input')
    physical.RELEASE=LAYOUT/'qualification'
    paths=dict(schematic=SOURCE/'row_decoder.sch',symbol=SOURCE/'row_decoder.sym',
        layout=LAYOUT/'row_decoder_flat.mag',pex=LAYOUT/'pex/row_decoder_pex.spice')
    item=dict(expected_mos=33,files={k:dict(path=str(v.relative_to(ROOT)),sha256=physical.sha(v)) for k,v in paths.items()})
    result=physical.verify('row_decoder',item,True)
    (physical.RELEASE/'manifest.json').write_text(json.dumps(dict(
        status='PASS',decision='33-MOS feedback-keeper revision; 29-MOS Phase 1 baseline remains archived unchanged.',
        inputs=item,verification=str((physical.RELEASE/'verification/row_decoder/result.json').relative_to(ROOT)),
        verifier_sha256=physical.sha(Path(__file__)),shared_verifier_sha256=physical.sha(Path(physical.__file__))),indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
