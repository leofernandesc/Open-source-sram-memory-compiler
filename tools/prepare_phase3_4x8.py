#!/usr/bin/env python3
"""Prepare the existing nominal 4x8 fixture without running any simulation.

The old stimulus is deliberately fixed at TT/1.8V/27C/20ns/50ps. This is a
preparation adapter, not a new parameterized SRAM stimulus generator.
"""
import argparse
import json
from pathlib import Path
import re
from phase2_evidence import digest
from phase3.runner import ROOT, write_json
from phase3.provenance import selected_inputs
from phase3.functional import ADAPTER
from phase3.functional_a import ADAPTER as A_ADAPTER, context_for


def nominal_template(source):
    """One canonical transformation, shared by preparation and approved validation."""
    # Preserve historical PWL and clock chain. No artificial timing/power measure.
    text = (source/'bench.spice').read_text()
    text = re.sub(r'(?m)^\.lib .+$', '.lib "{{MODEL}}" {{CORNER}}', text)
    text = text.replace('.include "binding.spice"', '.include "{{NETLIST}}"')
    text = text.replace('.include "fabric.spice"', '.include "'+str(source/'fabric.spice')+'"')
    # Work directory is new: all simulator outputs remain in the new run.
    if re.search(r'(?im)^\s*(shell|source|cd|write\s+/|wrdata\s+/)', text):
        raise ValueError('Unexpected historical deck side effect')
    text = text.replace('.control', '\n'.join(f'C_PHASE3_LOAD{bit} DATA{bit} 0 {{{{LOAD}}}}' for bit in range(8))+'\n.control')
    return text


def prepare(output, profile=ADAPTER):
    if profile not in (ADAPTER, A_ADAPTER, 'phase3_nominal_bench_v1'):
        raise ValueError('Unsupported functional profile')
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT/'reports/phase3'):
        raise ValueError('Use a new directory below reports/phase3')
    output.mkdir(parents=True)  # no overwrite, including preparation directories
    identity = selected_inputs(ROOT)
    source = (ROOT/identity['qualification']).parent
    receipt = json.loads((source/'results.json').read_text())
    for name in ('bench.spice', 'binding.spice', 'fabric.spice'):
        if digest(source/name) != receipt['artifacts'][name]:
            raise ValueError('Historical input changed: '+name)
    c = json.loads((ROOT/'characterization/phase3/smoke.json').read_text())
    model = Path(c['model']['path'])
    if digest(model) != c['model']['sha256']:
        raise ValueError('Model pin differs; audit environment before repinning')
    text = nominal_template(source)
    deck = output/'nominal.spice.in'; deck.write_text(text)
    def pin(path): return dict(path=str(path), sha256=digest(path))
    c.update(scope='sram', extraction='devices/junctions', deck=pin(deck),
             netlist=pin(source/'binding.spice'), measurements=[], timeout_s=2400, memory_mb=4096,
             load_ff=10, stimuli='Historical qualification_v1 PWL; fixed TT/1.8V/27C/20ns/50ps, plus explicit exploratory 10fF per DATA bit. No timing or power measurements configured.')
    context = output/'preparation.json'
    write_json(context, dict(status='NOT_CHARACTERIZED', electrical_simulation_performed=False,
        adapter=ADAPTER, baseline=c['baseline'], selection=identity,
        inputs={str(ROOT/name):sha for name,sha in identity['inputs'].items()},
        expected_inputs={k:c[k] for k in ('deck','netlist','model')},
        limitation='Fixed nominal stimulus; no simulation, distributed RC or characterization inferred.'))
    if profile == A_ADAPTER:
        write_json(context, context_for(c['baseline'], identity, {k:c[k] for k in ('deck','netlist','model')}))
    elif profile == 'phase3_nominal_bench_v1':
        from phase3.nominal_operational import prepare_approved
        write_json(context, prepare_approved(ROOT,c,identity,output))
    c['functional_validation'] = pin(context)
    write_json(output/'config.json',c)
    return output/'config.json'

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--output',required=True)
    p.add_argument('--profile', choices=(ADAPTER, A_ADAPTER, 'phase3_nominal_bench_v1'), default=ADAPTER,
                   help='Default: legacy. A remains blocked. Nominal uses approved P3-DATA-002 r1.')
    args=p.parse_args()
    print(prepare(args.output, args.profile))
