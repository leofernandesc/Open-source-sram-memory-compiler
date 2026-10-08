"""Bind decoder PEX to a checked layout; reject historical PEX after edits."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAYOUT = ROOT / 'layout/row_decoder'
STATE = LAYOUT / 'pex/provenance.json'


def text_hash(path: Path, *, layout=False) -> str:
    # Git may change EOLs on Windows; timestamps do not change Magic geometry.
    text = path.read_text()
    if layout:
        text = '\n'.join(line for line in text.splitlines()
                         if not line.startswith('timestamp ')) + '\n'
    return hashlib.sha256(text.encode()).hexdigest()


def write_state(*, top_drc=None, flat_drc=None, lvs=False, current=False):
    STATE.parent.mkdir(exist_ok=True)
    flat = LAYOUT / 'row_decoder_flat.mag'
    pex = LAYOUT / 'pex/row_decoder_pex.spice'
    state = dict(status='current' if current else 'stale',
                 updated_utc=datetime.now(timezone.utc).isoformat(),
                 reason='Extracted R-C belongs to this checked layout' if current else
                        'Layout changed; new R-C extraction must be performed on the other machine',
                 layout_sha256=text_hash(flat, layout=True) if flat.exists() else None,
                 schematic_sha256=text_hash(ROOT / 'cells/row_decoder/row_decoder.sch'),
                 pex_sha256=text_hash(pex) if pex.exists() else None,
                 drc_hierarchical=top_drc, drc_flattened=flat_drc, lvs_unique_match=lvs,
                 electrical_scope='Binding only; post-layout electrical qualification is separate')
    if current and (top_drc != 0 or flat_drc != 0 or not lvs):
        raise ValueError('Cannot bind PEX before DRC and unique LVS match')
    STATE.write_text(json.dumps(state, indent=2) + '\n')
    marker = LAYOUT / 'pex/STALE.md'
    if current:
        marker.unlink(missing_ok=True)
    else:
        marker.write_text('# PEX antigo — extração pendente\n\n'
                          'O layout do decoder foi compactado. O arquivo '
                          '`row_decoder_pex.spice` ainda pertence ao layout anterior.\n'
                          'Não use esse PEX para validar o layout atual. Execute a nova '
                          'extração na outra máquina conforme `../README.md`.\n'
                          'O histórico está em `../archive/`, incluindo a revisão remota 7ad0348.\n')
    return state


def require_current_pex():
    if not STATE.exists():
        if (LAYOUT / 'routing_plan.json').exists():
            raise ValueError('Compact layout is missing its PEX provenance record')
        return None
    state = json.loads(STATE.read_text())
    if state['status'] != 'current':
        raise ValueError('PEX is stale after layout compaction. Run new R-C extraction '
                         'on the other machine before simulating the current layout.')
    expected = (('layout_sha256', LAYOUT / 'row_decoder_flat.mag', True),
                ('schematic_sha256', ROOT / 'cells/row_decoder/row_decoder.sch', False),
                ('pex_sha256', LAYOUT / 'pex/row_decoder_pex.spice', False))
    for key, path, layout in expected:
        if text_hash(path, layout=layout) != state[key]:
            raise ValueError(f'PEX provenance mismatch: {key}; repeat affected physical checks/extraction')
    if state['drc_hierarchical'] != 0 or state['drc_flattened'] != 0 or not state['lvs_unique_match']:
        raise ValueError('PEX provenance does not establish DRC/LVS closure')
    return state
