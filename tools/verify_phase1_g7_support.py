#!/usr/bin/env python3
"""Replace missing historical G7 DRC/LVS logs with a parameter-aware rerun.

The G7 column is supporting evidence, not a seventh delivered leaf or a full
macro. No PEX is regenerated. The reference expands the frozen schematic
leaves using the original structural column wiring, not extracted leaf models.
"""
from __future__ import annotations
import json
import re
import shutil
import tempfile
from datetime import datetime,timezone
from pathlib import Path
from prepare_phase1_release import blob, UPSTREAM
from verify_phase1_physical import ROOT, RELEASE, MAGIC_RC, NETGEN_SETUP, run, sha, primitives, matched, joined


def main():
    out=RELEASE/'support/g7_column'
    out.mkdir(parents=True,exist_ok=True)
    source_root='layout/column_32_full_g7_wpre2p52_final/'
    inputs={}
    for filename in ['column_32_full_g7_wpre2p52_flat.mag','column_32_full_g7_reference_top.spice']:
        target=out/filename
        target.write_bytes(blob(UPSTREAM,source_root+filename))
        inputs[filename]=dict(source_revision=UPSTREAM,source_path=source_root+filename,sha256=sha(target))
    top=(out/'column_32_full_g7_reference_top.spice').read_text()
    top_pins=re.search(r'(?mi)^\.subckt\s+\S+\s+([^\n]+)',top).group(1).split()
    aliases={'bitcell_6t_flat':'bitcell_6t','sense_amp_scale1p5_flat':'sense_amp',
             'precharge_w2p52_flat':'precharge','write_driver_w5p04_flat':'write_driver'}
    devices=[]
    for instance in joined(top):
        if not instance.startswith('X'):
            continue
        tokens=instance.split()
        leaf=aliases[tokens[-1]]
        schematic=RELEASE/'cells'/leaf/(leaf+'.spice')
        text=schematic.read_text()
        ports=re.search(r'(?mi)^\.subckt\s+\S+\s+([^\n]+)',text).group(1).split()
        assert len(ports)==len(tokens)-2
        connections=dict(zip(ports,tokens[1:-1]))
        for line in joined(text):
            if not line.startswith('X'):
                continue
            fields=line.split()
            fields[0]=tokens[0]+'_'+fields[0]
            fields[1:5]=[connections.get(node,tokens[0]+'/'+node) for node in fields[1:5]]
            devices.append(' '.join(fields))
    name='g7_column'
    source='.subckt '+name+' '+' '.join(top_pins)+'\n'+'\n'.join(devices)+'\n.ends '+name+'\n'
    (out/'schematic_from_frozen_leaves.spice').write_text(source)
    normalized,count,pins=primitives(source,name)
    assert count==212
    (out/'schematic_mos.spice').write_text(normalized)
    mask=out/'column_32_full_g7_wpre2p52_flat.mag'
    with tempfile.TemporaryDirectory(prefix='phase1-g7-support-') as directory:
        scratch=Path(directory)
        shutil.copy2(mask,scratch/'g7_column.mag')
        commands=f'''load g7_column
select top cell
expand
drc euclidean on
drc style drc(full)
drc on
drc check
drc catchup
set findings [drc listall why]
puts "PHASE1_DRC_GROUPS=[llength $findings]"
puts "PHASE1_DRC_DETAILS=$findings"
extract do local
extract all
ext2spice lvs
ext2spice scale off
ext2spice -o {out}/layout_extracted.spice
quit -noprompt
'''
        (out/'verify.tcl').write_text(commands)
        log=run(['magic','-dnull','-noconsole','-rcfile',str(MAGIC_RC)],scratch,out/'magic.txt',commands)
        assert re.findall(r'PHASE1_DRC_GROUPS=(\d+)',log)==['0']
        extracted,count2,pins2=primitives((out/'layout_extracted.spice').read_text(),name)
        assert count2==212 and set(pins)==set(pins2)
        (out/'layout_mos.spice').write_text(extracted)
        report=out/'lvs_report.txt'
        run(['netgen','-batch','lvs',f'{out}/layout_mos.spice {name}',
             f'{out}/schematic_mos.spice {name}',str(NETGEN_SETUP),str(report)],scratch,out/'netgen.txt')
        if not matched(report.read_text()):
            raise RuntimeError(f'G7 parameter-aware LVS failed: {report}')
    result=dict(status='PASS',scope='Supporting G7 flat column; not a full SRAM macro',
        mos_count=212,drc_groups=0,lvs='UNIQUE_MATCH_WITH_W_L_AND_TERMINALS',
        inputs=inputs,schematic_leaf_hashes={cell:sha(RELEASE/'cells'/cell/(cell+'.spice'))
                                          for cell in aliases.values()},
        script_sha256=sha(Path(__file__)),
        evidence_sha256={p.name:sha(p) for p in sorted(out.iterdir())
                         if p.is_file() and p.name!='result.json'},
        completed_utc=datetime.now(timezone.utc).isoformat())
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('G7 supporting column: DRC 0, parameter-aware LVS PASS, 212 MOS; no PEX regenerated.')


if __name__=='__main__':
    main()
