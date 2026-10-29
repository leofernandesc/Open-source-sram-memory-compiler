#!/usr/bin/env python3
"""Build/check the separate 33-MOS feedback-keeper revision, preserving the freeze.

Use --lvs-only for inexpensive connectivity checks. --extract runs the detailed
Magic R-C extraction and can be expensive on the notebook.
"""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'layout/row_decoder'))
import build_layout as engine

LAYOUT=Path(__file__).resolve().parent
SCHEMATIC=ROOT/'cells/row_decoder/variants/keeper_0p84/row_decoder.sch'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def write_state(*,top_drc=None,flat_drc=None,lvs=False,current=False):
    if current and (top_drc!=0 or flat_drc!=0 or not lvs):
        raise ValueError('Cannot bind new PEX without DRC/LVS')
    (LAYOUT/'pex').mkdir(exist_ok=True)
    files=dict(schematic=SCHEMATIC,layout=LAYOUT/'row_decoder_flat.mag',
        pex=LAYOUT/'pex/row_decoder_pex.spice',builder=Path(__file__),
        shared_builder=ROOT/'layout/row_decoder/build_layout.py',
        routing=ROOT/'layout/row_decoder/compact_routing.py')
    state=dict(status='current' if current else 'pending',updated_utc=datetime.now(timezone.utc).isoformat(),
        expected_mos=33,drc_top=top_drc,drc_flat=flat_drc,lvs_unique_match=lvs,
        limitation='Geometry binding only. Electrical qualification of this new PEX is separate.',
        files={k:dict(path=str(v.relative_to(ROOT)),sha256=digest(v)) for k,v in files.items()})
    (LAYOUT/'pex/provenance.json').write_text(json.dumps(state,indent=2)+'\n')


if __name__=='__main__':
    engine.LAYOUT=LAYOUT;engine.SCHEMATIC=SCHEMATIC
    engine.DEVICE_COUNT=33;engine.PFET_COUNT=16;engine.NFET_COUNT=17
    engine.IMPORT_TOP='row_decoder_keeper084_sram6t'
    engine.write_state=write_state
    raise SystemExit(engine.main())
