#!/usr/bin/env python3
"""Generate an inspectable B7 schematic copy; refuse to overwrite any file.

Preserve the dynamic NAND core, interface, original wire placement and MOS
properties. Add two true-literal inverters and the measured width changes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def generate(source):
    if sorted(int(n) for n in re.findall(r'\bname=M(\d+)\b', source)) != list(range(1,26)):
        raise ValueError('Expected the original 25-MOS decoder')
    widths={8:1.5,5:.5,11:.5,16:.5,21:.5,9:2,10:2,14:2,15:2,19:2,20:2,24:2,25:2}
    for n,w in widths.items():
        source,count=re.subn(rf'(\{{name=M{n}\s+W=)\S+',rf'\g<1>{w:g}',source)
        if count!=1:
            raise ValueError(f'Expected one width for M{n}')
    # Only the four true-literal labels at evaluation gates change. External
    # address pins and the original address-inverter wires remain A0/A1.
    source,count=re.subn(r'(C \{lab_pin\.sym\}[^\n]*\blab=)(A[01])(?=\})',r'\1\2T',source)
    if count!=4:
        raise ValueError('Expected exactly four unbuffered true-literal labels')
    blocks=[]
    for bit,x,n in [(0,500,26),(1,820,28)]:
        drain=x+20; gate=x-20; left=x-50; rail=x+40
        for number,template,y in [(n,1,-950),(n+1,2,-850)]:
            match=re.search(rf'C \{{sky130_fd_pr/(?:p|n)fet_01v8.sym\}} \S+ \S+ 0 0 \{{name=M{template}\n.*?\n\}}',source,re.S)
            if not match:
                raise ValueError('Missing original inverter template')
            block=re.sub(r'(^C \{[^}]+\}) \S+ \S+',rf'\g<1> {x} {y}',match[0])
            block=block.replace(f'name=M{template}\n',f'name=M{number}\n')
            block=re.sub(r'\bW=\S+','W=2',block)
            blocks.append('\n'.join(line.rstrip() for line in block.splitlines()))
        wires=[(left,-950,gate,-950,f'A{bit}B'),(left,-950,left,-850,f'A{bit}B'),
               (left,-850,gate,-850,f'A{bit}B'),(drain,-920,drain,-880,f'A{bit}T'),
               (drain,-900,x+60,-900,f'A{bit}T'),(drain,-980,rail,-980,'VDD'),
               (rail,-980,rail,-950,'VDD'),(drain,-950,rail,-950,'VDD'),
               (drain,-820,rail,-820,'VSS'),(rail,-850,rail,-820,'VSS'),
               (drain,-850,rail,-850,'VSS')]
        blocks += [f'N {a} {b} {c} {d} {{lab={label}}}' for a,b,c,d,label in wires]
        labels=[(left,-900,f'A{bit}B'),(x+60,-900,f'A{bit}T'),(rail,-980,'VDD'),(rail,-820,'VSS')]
        blocks += [f'C {{lab_pin.sym}} {a} {b} 0 0 {{name=b7_{bit}_{i} sig_type=std_logic lab={label}}}'
                   for i,(a,b,label) in enumerate(labels)]
    return source.rstrip()+'\n'+'\n'.join(blocks)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise ValueError('Refusing to overwrite the output')
    base=args.source.read_text()
    result=generate(base)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(result)
    args.output.with_suffix('.derivation.json').write_text(json.dumps(dict(
        source=str(args.source),source_sha256=hashlib.sha256(base.encode()).hexdigest(),
        output_sha256=hashlib.sha256(result.encode()).hexdigest(),
        status='Generated candidate; requires fresh netlist and electrical qualification before adoption'),indent=2)+'\n')


if __name__=='__main__':
    main()
