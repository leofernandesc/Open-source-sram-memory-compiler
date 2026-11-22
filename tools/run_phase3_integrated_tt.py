#!/usr/bin/env python3
"""Derive and run the TT bench from the sealed integrated SS preparation."""

import argparse
import json
from pathlib import Path
import re

from run_phase3_integrated_ss import (
    BUILD, PDK, ROOT, checked_preparation, model_closure, new_directory,
    plan_cycles, require, sha256, simulate,
)
from phase3_rc_characterization import QUAL


SS = BUILD / 'integrated_ss_20261119_preflight'


def tt_deck(source):
    model_cards = re.findall(r'^\s*\.lib [^\n]+', source, re.MULTILINE)
    ss_card = f'.lib "{PDK}" ss'
    require(model_cards == [ss_card], 'Expected exactly the sealed SS model card')
    return source.replace(ss_card, f'.lib "{PDK}" tt', 1)


def prepare(source, output):
    receipt = checked_preparation(source)
    old = json.loads((source/'simulation.json').read_text())
    require(receipt['conditions']['corner']=='ss' and old['simulator_status']=='PASS'
            and old['preparation_sha256']==sha256(source/'preparation.json'),
            'Expected the sealed SS preparation of a successful transient')
    underlying = json.loads((QUAL/'results.json').read_text())['cycles']
    records, strong, weak = plan_cycles(underlying)
    expected = dict(cycles=records,strong_edges_ns=strong,weak_intervals_ns=weak)
    fixture = json.loads((source/'fixture.json').read_text())
    require(fixture == json.loads(json.dumps(expected)), 'Integrated fixture differs from its authorized schedule')
    lib = PDK.read_text()
    cards = re.findall(r'^\.lib\s+tt\s*\n(.*?)^\.endl(?:\s+tt)?\s*$',lib,re.MULTILINE|re.DOTALL|re.IGNORECASE)
    require(len(cards)==1 and re.search(r'(?im)^\s*\.param\s+mc_mm_switch\s*=\s*0\s*$',cards[0])
            and re.search(r'(?im)^\s*\.param\s+mc_pr_switch\s*=\s*0\s*$',cards[0]),
            'Expected deterministic TT in the installed SKY130 model wrapper')
    require(model_closure(PDK)==json.loads((source/'model_hashes.json').read_text()),
            'Installed PDK differs from the sealed SS reference')
    deck = tt_deck((source/'bench.spice').read_text())
    output = new_directory(output)
    for name in receipt['artifacts']:
        (output/name).write_bytes(deck.encode() if name=='bench.spice' else (source/name).read_bytes())
    receipt['artifacts']['bench.spice'] = sha256(output/'bench.spice')
    receipt['conditions']['corner'] = 'tt'
    receipt['parent_ss_preparation_sha256'] = old['preparation_sha256']
    for path in (source/'preparation.json',source/'simulation.json',Path(__file__).resolve()):
        receipt['inputs_sha256'][str(path.relative_to(ROOT))] = sha256(path)
    (output/'preparation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    require(checked_preparation(output)['conditions']['corner']=='tt', 'Invalid TT preparation')
    print(f'Prepared {output}. The deck differs from SS only in the .lib corner.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','simulate'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--timeout',type=int,default=2700)
    args = parser.parse_args()
    output = args.output.resolve()
    if args.action=='prepare':
        prepare(SS,output)
        return 0
    require(0 < args.timeout <= 2700, 'Use a timeout of at most 2700 seconds')
    receipt = checked_preparation(output)
    require(receipt['conditions']['corner']=='tt' and
            (output/'bench.spice').read_bytes()==tt_deck((SS/'bench.spice').read_text()).encode(),
            'Expected the deterministic TT deck derived from sealed SS')
    return simulate(output,args.timeout)


if __name__ == '__main__':
    raise SystemExit(main())
