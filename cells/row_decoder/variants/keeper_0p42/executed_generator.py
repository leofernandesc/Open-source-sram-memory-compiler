#!/usr/bin/env python3
"""Build a reversible four-keeper schematic derivative of the frozen decoder.

The 29-device baseline and the other five leaf cells are never rewritten.
The derivative is an experimental candidate until its own physical/electrical
evidence is closed. Pin order and dynamic NAND operation are preserved.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'release/phase1/cells/row_decoder'


def schematic(text,width=.42):
    if width not in (.42,.84):raise ValueError('Only characterized keeper candidates are supported')
    names=re.findall(r'name=(M\d+)\b',text)
    if set(names)!={f'M{i}' for i in range(1,30)} or len(names)!=29:
        raise ValueError('Expected the unchanged frozen XM1..XM29 baseline')
    additions=[f'T {{Experimental feedback keepers: W={width:g}um L=0.15um; candidate evidence is separate from the 29-MOS freeze.}} 420 -660 0 0 0.25 0.25 {{}}']
    for row in range(4):
        x=500+400*row;y=-540;name=f'M{30+row}'
        additions.extend([
            f'C {{sky130_fd_pr/pfet_01v8.sym}} {x} {y} 0 0 {{name={name}',
            f'W={width:g}','L=0.15','nf=1','mult=1',
            'ad="\'int((nf+1)/2) * W/nf * 0.29\'"',
            'pd="\'2*int((nf+1)/2) * (W/nf + 0.29)\'"',
            'as="\'int((nf+2)/2) * W/nf * 0.29\'"',
            'ps="\'2*int((nf+2)/2) * (W/nf + 0.29)\'"',
            'nrd="\'0.29 / W\'" nrs="\'0.29 / W\'"',
            'sa=0 sb=0 sd=0','model=pfet_01v8','spiceprefix=X','}',
            f'N {x-40} {y} {x-20} {y} {{lab=DEC{row}}}',
            f'N {x+20} {y+30} {x+20} {y+60} {{lab=N{row}}}',
            f'N {x+20} {y-30} {x+40} {y-30} {{lab=VDD}}',
            f'N {x+40} {y-30} {x+40} {y} {{lab=VDD}}',
            f'N {x+20} {y} {x+40} {y} {{lab=VDD}}',
            f'C {{devices/lab_pin.sym}} {x-40} {y} 0 0 {{name=keeper_gate_{row} lab=DEC{row}}}',
            f'C {{devices/lab_pin.sym}} {x+20} {y+60} 0 0 {{name=keeper_drain_{row} lab=N{row}}}',
            f'C {{devices/lab_pin.sym}} {x+40} {y-30} 0 0 {{name=keeper_supply_{row} lab=VDD}}',
        ])
    return text.rstrip()+'\n'+'\n'.join(additions)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path)
    p.add_argument('--width-um',type=float,choices=(.42,.84),default=.84)
    args=p.parse_args();out=args.output_dir or ROOT/f'cells/row_decoder/variants/keeper_{args.width_um:g}'.replace('.','p')
    if out.exists():raise ValueError('Use a new output directory; never overwrite a hand-edited schematic')
    source=BASE/'row_decoder.sch'
    # The release input is bound independently by its manifest.
    entry=json.loads((ROOT/'release/phase1/manifest.json').read_text())['cells']['row_decoder']['files']['schematic']
    if hashlib.sha256(source.read_bytes()).hexdigest()!=entry['sha256']:
        raise ValueError('Frozen baseline hash mismatch')
    out.mkdir(parents=True)
    (out/'row_decoder.sch').write_text(schematic(source.read_text(),args.width_um))
    (out/'row_decoder.sym').write_bytes((BASE/'row_decoder.sym').read_bytes())
    (out/'source.json').write_text(json.dumps(dict(status='EXPERIMENTAL_CANDIDATE',
        baseline=str(source.relative_to(ROOT)),baseline_sha256=entry['sha256'],
        added_devices=4,expected_mos=33,keeper_w_um=args.width_um,keeper_l_um=.15,
        connections='M30..M33: D=N0..N3, G=DEC0..DEC3, S=B=VDD',
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')
    (out/'executed_generator.py').write_bytes(Path(__file__).read_bytes())
    print(out)


if __name__=='__main__':main()
