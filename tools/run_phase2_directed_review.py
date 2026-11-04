#!/usr/bin/env python3
"""Bounded TT review: walking data, captured-input disturbances and real BL/BLB.

The original 1493-MOS extraction is used unchanged. No RC/PVT characterization,
internal initialization, new timing limit or new cell sizing is introduced.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import numpy as np
from run_digital_regression import atomic_text,output_lock
from run_phase2_digital import ROOT,sha
from phase2_resources import preflight
from phase2_access_checks import check as protocol_check


def observation_map(raw,flat,ext):
    """Locate extracted labels by existing MOS terminals; never reconnect MOS."""
    def cards(text):
        return {f[0]:f for l in text.splitlines() if re.match(r'(?i)^x\S+\s',l) for f in [l.split()]}
    original,renamed=cards(raw),cards(flat)
    if set(original)!=set(renamed):raise ValueError('Different MOS identities')
    mapping={};parent={}
    def clean(n):return n.replace('\\','')
    def find(n):
        n=clean(n);parent.setdefault(n,n)
        if parent[n]!=n:parent[n]=find(parent[n])
        return parent[n]
    for name,a in original.items():
        b=renamed[name]
        if a[5:]!=b[5:]:raise ValueError('Changed extracted model/junction/geometry')
        for x,y in zip(a[1:5],b[1:5]):mapping.setdefault(clean(x),set()).add(y)
    if any(len(v)!=1 for v in mapping.values()):raise ValueError('Node renaming is inconsistent')
    for line in ext.splitlines():
        q=re.findall(r'"([^"]*)"',line)
        if line.startswith('node ') and q:find(q[0])
        if line.startswith('equiv ') and len(q)==2:parent[find(q[1])]=find(q[0])
    groups={}
    for name,values in mapping.items():groups.setdefault(find(name),set()).update(values)
    def probe(label):
        if clean(label) not in parent:raise ValueError('Missing observation label: '+label)
        values=groups.get(find(label),set())
        if len(values)!=1:raise ValueError('Ambiguous extracted observation: '+label)
        return 'v(xdut.'+next(iter(values))+')'
    return probe


def deck_for_review(source,design,probe):
    state=json.loads((source/'results.json').read_text());vectors=list(state['vectors'])
    prefix='macro_core.array_and_peripherals.'
    extras={}
    for b in range(8):
        extras[f'BL{b}']=probe(prefix+f'write_driver_{b}.BL')
        extras[f'BLB{b}']=probe(prefix+f'write_driver_{b}.BLB')
        extras[f'DIN_Q{b}']=probe(prefix+f'DIN{b}')
    extras.update({f'ADDR_Q{b}':probe(prefix+f'A{b}') for b in range(2)})
    top=design['modules']['sram_4x8_wrapper']
    for b,q in enumerate(top['netnames']['read_data_q']['bits']):
        name=next(n for n,c in top['cells'].items() if c['type'].startswith('sky130_fd_sc_hd__df') and c['connections']['Q']==[q])
        extras[f'REG_Q{b}']=probe(name+'.Q')
    for value in extras.values():
        if value not in vectors:vectors.append(value)
    cycles=[('idle',0,0),('idle',0,0),('unwritten',0,0)];memory={}
    for i in range(16):
        value=(1<<i) if i<8 else (255^(1<<(i-8)));row=i%4
        cycles.extend([('write',row,value),('read',row,value)]);memory[row]=value
    cycles.extend([('idle',0,0),('idle',0,0)])
    cycles.extend(('read',r,memory[r]) for r in range(4))
    signals={n:[(0,0)] for n in ['CLK','CSb','OEb','WEb','ADDR0','ADDR1','HOST_EN','HOST_WEAK_EN',*[f'HOST{b}' for b in range(8)]]}
    for n in ('CSb','OEb','WEb'):signals[n].append((1,1))
    def event(name,time,value):signals[name].extend([(time,signals[name][-1][1]),(time+.05,int(value))])
    records=[]
    for index,(op,row,payload) in enumerate(cycles):
        edge=10+20*index;read=op in ('read','unwritten');write=op=='write'
        ctl=(0,0,1) if read else (0,1,0) if write else (1,1,1)
        for n,v in zip(('CSb','OEb','WEb'),ctl):event(n,edge-3,v)
        for b in range(2):
            event(f'ADDR{b}',edge-3,(row>>b)&1)
            if op in ('read','write'):event(f'ADDR{b}',edge+3,((row^3)>>b)&1)
        offered=payload if write else (0x96 if index%2 else 0x69)
        for b in range(8):
            event(f'HOST{b}',edge-2.5,(offered>>b)&1)
            if write:event(f'HOST{b}',edge+3,((payload^255)>>b)&1)
        event('HOST_EN',edge-2,write);event('HOST_EN',edge+6,0)
        if op in ('read','write'):
            for n in ('CSb','OEb','WEb'):event(n,edge+4,1)
        if op=='read':
            event('HOST_WEAK_EN',edge+5,1);event('HOST_WEAK_EN',edge+8,0)
            for n,v in zip(('CSb','OEb','WEb'),(0,0,1)):event(n,edge+11,v)
        event('CLK',edge,1);event('CLK',edge+10,0)
        records.append(dict(cycle=index,operation=op,row=row,expected=payload,rise_ns=edge,fall_ns=edge+10,sample_ns=edge+12,weak_payload=offered))
    old=(source/'bench.spice').read_text().splitlines()
    lines=[l for l in old[:old.index(next(l for l in old if l.startswith('V_CLK ')))] if not l.startswith('V_')]
    for name,events in signals.items():lines.append(f'V_{name} {name} 0 PWL('+ ' '.join(f'{t:g}n {v*1.8:g}' for t,v in events)+')')
    lines.extend(l for l in old if l.startswith(('S_HOST','S_WEAK','XDUT ')))
    lines.extend(['.save '+' '.join(vectors),'.control','set num_threads=1','set noaskquit','set wr_singlescale','set wr_vecnames',
                  f'tran 10p {10+20*len(cycles)}n 0 10p','wrdata waveform.dat '+' '.join(vectors),'quit','.endc','.end'])
    return '\n'.join(lines)+'\n',records,vectors,extras


def analyze(data,records,vectors,extras,state):
    checks,reference=protocol_check(data,records,vectors,state['capture_inputs'],state['capture_clocks']);metrics=[]
    time=data[:,0]*1e9;last=None
    def col(name):return vectors.index(extras[name])+1
    def levels(values,expected):return bool(np.all((values>=1.44)&(values<=1.98))) if expected else bool(np.all((values>=-.18)&(values<=.36)))
    def put(kind,passed,**details):checks.append(dict(kind=kind,status='PASS' if passed else 'FAIL',**details))
    reads=0
    for r in records:
        op=r['operation'];edge=r['rise_ns'];fall=r['fall_ns'];high=(time>=edge+1)&(time<fall-.5)
        if op in ('read','write'):
            for bit in range(2):put('captured_address_survives_live_change',levels(data[high,col(f'ADDR_Q{bit}')],(r['row']>>bit)&1),cycle=r['cycle'],bit=bit)
        if op=='write':
            for bit in range(8):put('captured_write_data_survives_live_change',levels(data[high,col(f'DIN_Q{bit}')],(r['expected']>>bit)&1),cycle=r['cycle'],bit=bit)
        if last is not None:
            window=high if op=='read' else ((time>=edge+1)&(time<fall+8))
            for bit in range(8):put('previous_read_register_retained',levels(data[window,col(f'REG_Q{bit}')],(last>>bit)&1),cycle=r['cycle'],bit=bit)
        if op!='read':continue
        at=int(np.searchsorted(time,r['sample_ns']));weak=int(np.searchsorted(time,edge+6.5));reads+=8
        for bit in range(8):
            expected=(r['expected']>>bit)&1
            put('read_bus_bit',levels(data[at:at+1,bit+1],expected),cycle=r['cycle'],bit=bit,voltage_v=float(data[at,bit+1]))
            put('captured_output_bit',levels(data[at:at+1,col(f'REG_Q{bit}')],expected),cycle=r['cycle'],bit=bit)
            put('live_mask_during_captured_read',abs(float(data[weak,bit+1])-1.8*((r['weak_payload']>>bit)&1))<=.05,cycle=r['cycle'],bit=bit)
        # Report actual BL differential at sense-enable onset; no fabricated
        # minimum differential or statistical sense margin is introduced.
        candidates=np.flatnonzero((time>=edge)&(time<fall)&(data[:,11]>=.36))
        if not len(candidates):raise ValueError('Missing sense onset')
        index=int(candidates[0])
        for bit in range(8):
            delta=float(data[index,col(f'BL{bit}')]-data[index,col(f'BLB{bit}')]);signed=delta*(1 if (r['expected']>>bit)&1 else -1)
            metrics.append(dict(cycle=r['cycle'],row=r['row'],bit=bit,time_ns=float(time[index]),bl_minus_blb_v=delta,signed_differential_v=signed))
        last=r['expected']
    return checks,metrics,reference,reads


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='reports/phase2/review_20261104/directed');args=parser.parse_args()
    out=(ROOT/args.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2') or out==ROOT/'reports/phase2':parser.error('Output under reports/phase2 required')
    out.mkdir(parents=True,exist_ok=True)
    with output_lock(out):
        result={'status':'RUNNING','scope':'Additional nominal electrical review; unchanged extracted MOS; no wire RC/PVT qualification'}
        def publish():atomic_text(out/'results.json',json.dumps(result,indent=2)+'\n')
        publish()
        try:
            result['resources']=preflight(ROOT);source=ROOT/'reports/phase2/extracted_access_singlethread';gds=ROOT/'reports/phase2/final_gds';state=json.loads((source/'results.json').read_text())
            for n,h in state['artifacts'].items():
                if sha(source/n)!=h:raise ValueError('Baseline electrical artifact changed')
            model_hashes=state['model_inputs']
            for n,h in model_hashes.items():
                if sha(n)!=h:raise ValueError('PDK model changed')
            design_path=ROOT/'reports/phase2/portable_raw/routed_reference.json';design=json.loads(design_path.read_text())
            files=[source/'results.json',source/'binding.spice',source/'bench.spice',gds/'final_extracted.spice',gds/'final_flat.ext',design_path,Path(__file__),ROOT/'tools/phase2_access_checks.py']
            pinned={str(p):sha(p) for p in files}
            probe=observation_map(files[3].read_text(),files[1].read_text(),files[4].read_text())
            deck,records,vectors,extras=deck_for_review(source,design,probe)
            if re.search(r'(?mi)^\s*\.(ic|nodeset)\b',deck):raise ValueError('Internal initialization forbidden')
            build=Path(tempfile.mkdtemp(prefix='directed-review-',dir=ROOT/'build/phase2'))
            (build/'bench.spice').write_text(deck);shutil.copyfile(source/'binding.spice',build/'binding.spice');shutil.copyfile(source/'fabric.spice',build/'fabric.spice')
            for n in ('bench.spice','binding.spice','fabric.spice'):shutil.copyfile(build/n,out/n)
            result.update(build_directory=str(build.relative_to(ROOT)),inputs=pinned,models=model_hashes,cycles=records,vectors=vectors,extra_probes=extras,
                          simulation_inputs={n:sha(build/n) for n in ('bench.spice','binding.spice','fabric.spice')},baseline_receipt_sha256=sha(source/'results.json'))
            publish()
            with (out/'ngspice.txt').open('w') as log:
                run=subprocess.run(['ngspice','-n','-b','bench.spice'],cwd=build,stdout=log,stderr=subprocess.STDOUT,timeout=3600,env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'))
            if run.returncode or not (build/'waveform.dat').is_file():raise ValueError('Directed simulation failed')
            data=np.loadtxt(build/'waveform.dat',skiprows=1);checks,metrics,reference,reads=analyze(data,records,vectors,extras,state)
            atomic_text(out/'checks.json',json.dumps({'checks':checks,'capture_reference':reference},indent=2)+'\n')
            with (out/'sense_differential.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(metrics[0]));w.writeheader();w.writerows(metrics)
            for p,h in pinned.items():
                if sha(p)!=h:raise ValueError('Directed source changed during run')
            for p,h in model_hashes.items():
                if sha(p)!=h:raise ValueError('PDK changed during run')
            result.update(checks=len(checks),failures=sum(c['status']=='FAIL' for c in checks),read_checks=reads,
                          raw_waveform_sha256=sha(build/'waveform.dat'),minimum_observed_signed_differential_v=min(m['signed_differential_v'] for m in metrics),
                          condition={'corner':'tt','vdd_v':1.8,'temp_c':27},interpretation='Differential amplitude observed only; no new minimum sense-margin criterion')
            result['status']='PASS_DIRECTED_NOMINAL' if not result['failures'] else 'FAIL'
            # A selected excerpt is illustrative; measurements always use the
            # full retained local trace identified above.
            np.savetxt(out/'waveform_excerpt.csv',data[::100],delimiter=',',header=','.join(['time_s',*vectors]),comments='')
        except Exception as e:result.update(status='FAIL',error=str(e))
        result['artifacts']={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name not in ('results.json','.run.lock')}
        publish();print(json.dumps({k:v for k,v in result.items() if k in ('status','checks','failures','read_checks','error')},indent=2))
        return 0 if result['status']=='PASS_DIRECTED_NOMINAL' else 1


if __name__=='__main__':raise SystemExit(main())
