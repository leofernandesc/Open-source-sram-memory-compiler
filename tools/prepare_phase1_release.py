#!/usr/bin/env python3
"""Freeze the six selected Phase 1 leaves without editing development sources."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'release/phase1'
UPSTREAM = 'eb9217ee80c585cf952e14f6a13f6fc7230ba639'
PERIPHERALS = '5f55d06225002f0f399e29239c59835d4101969f'

CELLS = {
    'bitcell_6t': dict(owner='Danilo', schematic='cells/bitcell_6t.sch',
        layout='layout/bitcell_6t/bitcell_6t_flat.mag',
        pex='layout/bitcell_6t/pex/bitcell_6t_pex.spice',
        widths={'MPL':'0.42','MPR':'0.42','MNL':'1.26','MNR':'1.26','MAL':'0.60','MAR':'0.60'},
        expected_mos=6),
    'sense_amp': dict(owner='André', schematic='cells/sense_amp.sch',
        layout='layout/sense_amp/experimental/sense_amp_scale1p5_flat.mag',
        pex='layout/sense_amp/experimental/pex/sense_amp_scale1p5_pex.spice',
        widths={'MP1':'1.89','MP2':'1.89','MN1':'0.975','MN2':'0.975','MTAIL':'0.975',
                'MSAMPBL':'2.0','MSAMPBLB':'2.0'}, expected_mos=7),
    'precharge': dict(owner='André', schematic='cells/precharge.sch',
        layout='layout/precharge/experimental_w2p52/precharge_w2p52_flat.mag',
        pex='layout/precharge/experimental_w2p52/pex/precharge_w2p52_pex.spice',
        widths={'MPBL':'2.52','MPBLB':'2.52','MEQ':'2.52'}, expected_mos=3),
    'wl_driver': dict(owner='Leonardo', schematic='cells/wl_driver.sch',
        layout='layout/wl_driver/experimental_s1p68_s2p5p04/wl_driver_s1p68_s2p5p04_flat.mag',
        pex='layout/wl_driver/experimental_s1p68_s2p5p04/pex/wl_driver_s1p68_s2p5p04_pex.spice',
        widths={'MP1':'1.68','MN1':'1.68','MP2':'5.04','MN2':'5.04'}, expected_mos=4),
    'write_driver': dict(owner='Leonardo', schematic='cells/write_driver.sch',
        layout='layout/write_driver/experimental_w5p04/write_driver_w5p04_flat.mag',
        pex='layout/write_driver/experimental_w5p04/pex/write_driver_w5p04_pex.spice',
        widths={name: ('0.84' if name in ('MPWEB','MNWEB') else '5.04') for name in
                ('MPWEB','MNWEB','MPENBL','MPDBL','MNDBL','MNENBL','MPENBLB','MPDBLB','MNDBLB','MNENBLB')},
        expected_mos=10),
    'row_decoder': dict(owner='Leonardo', schematic='cells/row_decoder/row_decoder.sch',
        layout='layout/row_decoder/row_decoder_flat.mag',
        pex='layout/row_decoder/pex/row_decoder_pex.spice', widths={}, expected_mos=29),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob(revision: str, path: str) -> bytes:
    return subprocess.check_output(['git','show',f'{revision}:{path}'],cwd=ROOT)


def set_widths(text: str, widths: dict[str,str]) -> str:
    found = set()
    def replace(match):
        component = match.group(0)
        name = re.search(r'\bname=(\S+)', component).group(1)
        if name not in widths:
            raise ValueError(f'Unexpected transistor {name}')
        found.add(name)
        component, count = re.subn(r"\bW=(?:'[^']*'|\S+)", 'W='+widths[name], component, count=1)
        if count != 1:
            raise ValueError(f'Missing width on {name}')
        return component
    text = re.sub(r'C \{sky130_fd_pr/(?:p|n)fet_01v8\.sym\}[^\n]*\{name=.*?\n?\}', replace, text, flags=re.S)
    if found != set(widths):
        raise ValueError(f'Width mapping mismatch: {found} / {set(widths)}')
    return text


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    manifest = dict(schema_version=1, scope='Six Phase 1 leaf cells',
        decision='Leonardo dynamic 29-MOS PCLK decoder retained; alternative PCH_N/EVAL candidate excluded.',
        phase2=['complete SRAM macros','compiler and final generated views',
                'physical qualification of complete capture and PCLK/PRECH control source'], cells={})
    for name, config in CELLS.items():
        revision = PERIPHERALS if name == 'row_decoder' else UPSTREAM
        directory = DEST/'cells'/name
        directory.mkdir(parents=True,exist_ok=True)
        item = {k:v for k,v in config.items() if k not in ('schematic','layout','pex')}
        item.update(source_revision=revision, inputs={}, files={})
        for kind, suffix in [('schematic','.sch'),('layout','.mag'),('pex','_pex.spice')]:
            original = blob(revision,config[kind])
            payload = original
            if kind == 'schematic' and config['widths']:
                payload = set_widths(original.decode(),config['widths']).encode()
            if kind == 'layout' and re.search(rb'^use ',payload,re.M):
                raise ValueError(f'{name}: release layout must be the final flattened mask')
            target = directory/(name+suffix)
            target.write_bytes(payload)
            item['inputs'][kind] = dict(path=config[kind],sha256=sha(original))
            item['files'][kind] = dict(path=str(target.relative_to(ROOT)),sha256=sha(payload))
        if name=='row_decoder':
            original_symbol='cells/row_decoder/row_decoder.sym'
            data=blob(revision,original_symbol)
            target=directory/'row_decoder.sym'
            target.write_bytes(data)
            item['inputs']['symbol']=dict(path=original_symbol,sha256=sha(data))
            item['files']['symbol']=dict(path=str(target.relative_to(ROOT)),sha256=sha(data))
        manifest['cells'][name]=item
    electrical=DEST/'electrical'
    electrical.mkdir(exist_ok=True)
    manifest['electrical_evidence']={}
    for filename in ['g7_read_requal_latch_t0_20261008.csv',
                     'g7_write_requal_casewise_wlsetup1p2ns_20261008.csv',
                     'g7_read_critical_refined_1ps_20261008.csv',
                     'g7_write_critical_refined_1ps_20261008.csv']:
        data=blob(UPSTREAM,'sims/'+filename)
        (electrical/filename).write_bytes(data)
        manifest['electrical_evidence'][filename]=dict(path=str((electrical/filename).relative_to(ROOT)),
             source_revision=UPSTREAM,source_path='sims/'+filename,sha256=sha(data))
    (DEST/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    print(f'Frozen {len(CELLS)} cells in {DEST.relative_to(ROOT)}; no development sources changed.')


if __name__ == '__main__':
    main()
