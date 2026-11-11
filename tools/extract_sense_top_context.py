#!/usr/bin/env python3
"""Read existing abutted SRAM raw; bind actual sense pins independently by MOS/ext.

No simulation, extraction or changes to the original circuit/results.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

from phase2_resources import preflight
from run_phase1_final_isolated import ROOT, sha, write_json
from run_phase2_directed_review import observation_map
from analyze_phase2_extension_timing import crossing

BASE=ROOT/'reports/phase2/direct_abutment_20261111'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve()
    if not out.is_relative_to(ROOT/'reports/phase1'):p.error('Output under reports/phase1 required')
    resource=preflight(ROOT);out.mkdir(parents=True,exist_ok=False)
    source=BASE/'qualification_v1';s=json.loads((source/'results.json').read_text())
    timing=json.loads((BASE/'audit_v1/timing.json').read_text())
    raw=ROOT/s['build_directory']/'waveform.dat'
    if sha(raw)!=s['raw_sha256'] or sha(source/'results.json')!=timing['source_receipt_sha256'] or timing['raw_sha256']!=s['raw_sha256']:
        raise ValueError('Historical raw/receipt/timing identity differs')
    paths=[BASE/'gds_v1/final_extracted.spice',source/'binding.spice',BASE/'gds_v1/final_flat.ext',
           source/'results.json',BASE/'audit_v1/timing.json',Path(__file__),ROOT/'tools/run_phase2_directed_review.py']
    probe=observation_map(*(x.read_text() for x in paths[:3]))
    prefix='macro_core.array_and_peripherals'
    mapping={}
    for bit in range(8):
        mapping[f'BL{bit}']=probe(f'{prefix}.sense_amp_{bit}.BL')
        mapping[f'BLB{bit}']=probe(f'{prefix}.sense_amp_{bit}.BLB')
        mapping[f'SCLK{bit}']=probe(f'{prefix}.sense_amp_{bit}.SCLK')
        if mapping[f'BL{bit}']!=s['probes'][f'BL{bit}'] or mapping[f'BLB{bit}']!=s['probes'][f'BLB{bit}']:
            raise ValueError('Historical BL probes do not refer to actual sense pins')
        if mapping[f'SCLK{bit}']!=s['vectors'][10]:raise ValueError('Historical SCLK vector differs from sense pin')
    with raw.open() as f:
        if f.readline().split()!=['time',*s['vectors']]:raise ValueError('Raw vector header mismatch')
    data=np.loadtxt(raw,skiprows=1);t=data[:,0]*1e9
    if not np.all(np.isfinite(data)) or np.any(np.diff(t)<=0) or t[-1]<s['stop_ns']-.001:
        raise ValueError('Incomplete top waveform')
    def col(name):return s['vectors'].index(mapping[name])+1
    clk=data[:,col('SCLK0')];rows=[];phases=[];mask=np.zeros(len(t),dtype=bool)
    for cycle in s['cycles']:
        if cycle['operation']!='read':continue
        rise,fall=cycle['rise_ns'],cycle['fall_ns']
        edges={f't{level}':crossing(t,clk,voltage,rise,fall) for level,voltage in ((10,.18),(20,.36),(50,.9),(80,1.44),(90,1.62))}
        record=dict(cycle=cycle['cycle'],row=cycle['row'],**edges,sclk_slew_10_90_ps=(edges['t90']-edges['t10'])*1000)
        for label,time in [('before20_50ps',edges['t20']-.05),('at20',edges['t20']),('at50',edges['t50']),('at80',edges['t80'])]:
            for bit in range(8):
                bl=float(np.interp(time,t,data[:,col(f'BL{bit}')]))
                blb=float(np.interp(time,t,data[:,col(f'BLB{bit}')]))
                expected=(cycle['expected']>>bit)&1
                rows.append(dict(cycle=cycle['cycle'],row=cycle['row'],bit=bit,expected=expected,
                                 reference=label,time_ns=time,bl_v=bl,blb_v=blb,
                                 signed_delta_v=(bl-blb)*(1 if expected else -1),
                                 common_mode_v=(bl+blb)/2,high_v=max(bl,blb),low_v=min(bl,blb)))
        old=next(x for x in timing['phase'] if x['cycle']==cycle['cycle'])
        for label,field in [('at20','minimum_signed_bl_at_sense_v'),('before20_50ps','minimum_signed_bl_50ps_before_sense_v')]:
            actual=min(x['signed_delta_v'] for x in rows if x['cycle']==cycle['cycle'] and x['reference']==label)
            if not np.isclose(actual,old[field],rtol=0,atol=1e-10):raise ValueError('Historical minimum does not reconcile')
            record[field]=actual
        mask|=(t>=edges['t20']-.3)&(t<=edges['t20']+.7)
        phases.append(record)
    with (out/'pins_at_sense.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (out/'clock_edges.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(phases[0]));w.writeheader();w.writerows(phases)
    # All original samples in the selected edge windows; no interpolation/decimation here.
    excerpt=np.column_stack([t[mask],clk[mask],*[data[mask,col(f'{name}{bit}')] for bit in range(8) for name in ('BL','BLB')]])
    np.savez_compressed(out/'top_edge_windows.npz',data=excerpt)
    ranges={ref:{field:dict(min=min(x[field] for x in rows if x['reference']==ref),
                           max=max(x[field] for x in rows if x['reference']==ref))
                 for field in ('signed_delta_v','common_mode_v','high_v','low_v')}
            for ref in ('before20_50ps','at20','at50','at80')}
    record=dict(status='PASS_PIN_IDENTITY_AND_RAW_RECONCILIATION',resources=resource,
                inputs={str(x.relative_to(ROOT)):sha(x) for x in paths},source_raw_sha256=sha(raw),
                source_raw_path=str(raw.relative_to(ROOT)),condition=s['condition'],
                source_scope=s['scope'],pins=mapping,read_cycles=9,bit_observations=len(rows),ranges=ranges,
                sclk_slew_10_90_ps=dict(min=min(x['sclk_slew_10_90_ps'] for x in phases),max=max(x['sclk_slew_10_90_ps'] for x in phases)),
                excerpt_columns=['time_ns','SCLK',*[f'{name}{bit}' for bit in range(8) for name in ('BL','BLB')]],
                excerpt_scope='All native samples only in nine windows -0.3..+0.7 ns around sense20, not the complete top transient',
                limitations='Top uses extracted MOS/junctions without wire/leaf R-C. No implication of full top PEX qualification.',
                artifacts={x.name:sha(x) for x in out.iterdir() if x.is_file()})
    write_json(out/'results.json',record)
    print(json.dumps({k:record[k] for k in ('status','ranges','sclk_slew_10_90_ps')}))


if __name__=='__main__':main()
