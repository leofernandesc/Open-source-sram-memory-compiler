#!/usr/bin/env python3
"""Directed nominal diagnosis. Diagnostic netlists are never library candidates.

All decision criteria are imported unchanged from the published isolated run.
Functional FAIL is data: successful execution/integrity is reported separately.
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import numpy as np

from phase2_resources import preflight
from run_phase1_final_isolated import (
    ROOT, LIB, CRITERIA, EXPECTED, sha, identities, deck as original_deck,
    evaluate, negative_controls, read_data, write_json,
)
from run_phase2_extracted_access import model_closure

SOURCE=ROOT/'release/phase1/cells/sense_amp/sense_amp_pex.spice'
PORTS=['VDD','VSS','BL','BLB','SCLK','SA_OUT','SA_OUTB']
MODES=['full','no_c','no_r','no_rc','no_output_ground','no_clock_output','equal_output_ground']
PROBES={'CLK_tail':'SCLK.t0','CLK_sample_BL':'SCLK.t2','CLK_sample_BLB':'SCLK.t1',
        'gate_out':'SA_OUT.t3','gate_outb':'SA_OUTB.t3',
        'tail_left':'a_615_n3098.t0','tail_right':'a_615_n3098.t2'}


def topology(text):
    """Collapse only resistor-connected nodes, with formal ports as representatives."""
    parent={}
    def find(x):
        parent.setdefault(x,x)
        if parent[x]!=x:parent[x]=find(parent[x])
        return parent[x]
    for line in text.splitlines():
        words=line.split()
        if re.match(r'^R\d+\b',line):parent[find(words[1])]=find(words[2])
        elif re.match(r'^X\d+\b',line):
            for node in words[1:5]:find(node)
    groups={}
    for node in parent:groups.setdefault(find(node),[]).append(node)
    mapping={}
    for nodes in groups.values():
        ports=set(nodes)&set(PORTS)
        if len(ports)>1:raise ValueError('Resistor collapse would short formal ports')
        representative=next(iter(ports)) if ports else min(nodes)
        mapping.update({n:representative for n in nodes})
    def device_graph(netlist):
        records=[]
        for line in netlist.splitlines():
            if re.match(r'^X\d+\b',line):
                w=line.split();records.append([w[0],*[mapping.get(n,n) for n in w[1:5]],*w[5:]])
        return records
    return mapping,device_graph


def variant(mode):
    original=SOURCE.read_text();mapping,graph=topology(original)
    caps=[line.split() for line in original.splitlines() if re.match(r'^C\d+\b',line)]
    def ground_side(words):
        nodes={mapping.get(words[1],words[1]),mapping.get(words[2],words[2])}
        if 'VSS' in nodes:
            return next((n for n in ('SA_OUT','SA_OUTB') if n in nodes),None)
        return None
    ground={side:sum(float(c[3][:-1]) for c in caps if ground_side(c)==side)
            for side in ('SA_OUT','SA_OUTB')}
    target=sum(ground.values())/2
    removed=[];changed=[];lines=[]
    for line in original.splitlines():
        words=line.split()
        is_r=bool(re.match(r'^R\d+\b',line));is_c=bool(re.match(r'^C\d+\b',line))
        if is_r and mode in ('no_r','no_rc'):
            removed.append(line);continue
        if is_c:
            groups={mapping.get(n,n) for n in words[1:3]}
            drop=(mode in ('no_c','no_rc') or
                  (mode=='no_output_ground' and ground_side(words) is not None) or
                  (mode=='no_clock_output' and 'SCLK' in groups and bool(groups&{'SA_OUT','SA_OUTB'})))
            if drop:removed.append(line);continue
            if mode=='equal_output_ground' and ground_side(words):
                side=ground_side(words);words[3]=f'{float(words[3][:-1])*target/ground[side]:.12g}f'
                changed.append(dict(original=line,modified=' '.join(words)))
        if mode in ('no_r','no_rc') and words and (is_c or re.match(r'^X\d+\b',line)):
            end=3 if is_c else 5
            words[1:end]=[mapping.get(n,n) for n in words[1:end]]
            if is_c and words[1]==words[2]:removed.append(line);continue
            line=' '.join(words)
        elif mode=='equal_output_ground' and is_c:line=' '.join(words)
        lines.append(line)
    text='\n'.join(lines)+'\n' if mode!='full' else original
    if graph(original)!=graph(text):raise ValueError('Diagnostic transformation changed MOS connectivity/parameters')
    if mode=='full' and hashlib.sha256(text.encode()).hexdigest()!=EXPECTED['sense_amp'][1]:
        raise ValueError('Frozen PEX identity mismatch')
    description=dict(mode=mode,diagnostic_only=mode!='full',source_sha256=sha(SOURCE),
                     removed_elements=removed,changed_capacitors=changed,
                     resistor_collapsed_mos_graph_preserved=True,
                     original_output_ground_totals_ff=ground,
                     remaining_resistors=sum(bool(re.match(r'^R\d+\b',x)) for x in lines),
                     remaining_capacitors=sum(bool(re.match(r'^C\d+\b',x)) for x in lines))
    probes={k:(mapping.get(n,n) if mode in ('no_r','no_rc') else n) for k,n in PROBES.items()}
    return text,description,probes


def plan(suite,deltas,modes):
    result=[]
    settings=(('full',1.8,50),)
    if suite=='ablation':settings=tuple((m,1.8,50) for m in modes)
    elif suite=='operating':settings=(('full',1.6,50),('full',1.8,200))
    for mode,high,slew in settings:
        for delta in deltas:
            for polarity in (1,-1):
                for cap in (2,10):
                    result.append(dict(cell='sense_amp',view='pex',mode=mode,delta_mv=delta,polarity=polarity,
                                       cap_ff=cap,high_v=high,slew_ps=slew,
                                       id=f'{mode}_d{delta:g}_p{polarity:+}_c{cap}_h{high:g}_s{slew}'))
    return result


def bench(case,view,probes):
    text,vectors,stop=original_deck(case,view)
    high=case['high_v'];delta=case['delta_mv']/1000
    a,b=(high,high-delta) if case['polarity']==1 else (high-delta,high)
    slew=case['slew_ps']/1000
    substitutions={
        'VBL ':f'VBL BL 0 PWL(0 0 1n {high} 3n {high} 3.05n {a} 10n {a} 10.05n {b})',
        'VBLB ':f'VBLB BLB 0 PWL(0 0 1n {high} 3n {high} 3.05n {b} 10n {b} 10.05n {a})',
        'VSCLK ':f'VSCLK SCLK 0 PWL(0 0 5n 0 {5+slew:g}n 1.8 9n 1.8 {9+slew:g}n 0 13n 0 {13+slew:g}n 1.8 17n 1.8 {17+slew:g}n 0)',
    }
    lines=[]
    for line in text.splitlines():
        lines.append(next((v for k,v in substitutions.items() if line.startswith(k)),line))
    extras=[f'v(xdut.{node})' for node in probes.values()]
    old='wrdata waveform.dat '+' '.join(vectors)
    text=('\n'.join(lines)+'\n').replace(old,old+' '+' '.join(extras))
    if re.search(r'(?im)^\s*\.(ic|nodeset)\b|\buic\b',text):raise ValueError('Artificial initialization')
    return text,vectors+extras,stop


def observations(case,data):
    t=data[:,0]*1e9;rows=[]
    for event,edge in enumerate((5,13)):
        sign=case['polarity']*(-1 if event else 1)
        for offset in (-.1,0,.025,.05,.1,.2,.5):
            time=edge+offset
            row=dict(event=event,time_ns=time,offset_ps=offset*1000,expected_sign=sign,
                     delta_output_v=float(np.interp(time,t,data[:,5]-data[:,6])),
                     sclk_v=float(np.interp(time,t,data[:,4])))
            for i,name in enumerate(PROBES):row[name]=float(np.interp(time,t,data[:,7+i]))
            rows.append(row)
    return rows


def seal(out,result):
    result['artifacts']={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*'))
                         if p.is_file() and p.name!='results.json'}
    write_json(out/'results.json',result)


def run(out,suite,deltas,modes):
    out.mkdir(parents=True,exist_ok=False)
    result=dict(execution_status='RUNNING',functional_status='NOT_EVALUATED',criteria=CRITERIA,
                suite=suite,cases=[])
    write_json(out/'results.json',result)
    try:
        inputs,selected=identities();view=selected['sense_amp']['views']['pex']
        for p in (Path(__file__),ROOT/'tools/run_phase1_final_isolated.py',ROOT/'tools/phase2_resources.py',
                  ROOT/'tools/run_phase2_extracted_access.py'):
            inputs[str(p.relative_to(ROOT))]=sha(p)
        result.update(inputs=inputs,model_inputs=model_closure(LIB),resources=preflight(ROOT),
                      base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                      ngspice_version=subprocess.check_output(['ngspice','--version'],text=True),command=sys.argv)
        planned=plan(suite,deltas,modes)
        write_json(out/'plan.json',dict(criteria=CRITERIA,cases=planned))
        for case in planned:
            resource=preflight(ROOT);folder=out/case['id'];folder.mkdir()
            dut,description,probes=variant(case['mode'])
            (folder/'dut.spice').write_text(dut);write_json(folder/'transformation.json',description)
            text,vectors,stop=bench(case,view,probes);(folder/'bench.spice').write_text(text)
            with (folder/'ngspice.txt').open('w') as log:
                proc=subprocess.run(['ngspice','-n','-b','bench.spice'],cwd=folder,stdout=log,stderr=subprocess.STDOUT,
                                    timeout=120,env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1'))
            if proc.returncode or not (folder/'waveform.dat').exists():raise ValueError('Simulator execution failed')
            payload=(folder/'waveform.dat').read_bytes()
            with (folder/'waveform.dat.gz').open('wb') as f:
                with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as g:g.write(payload)
            (folder/'waveform.dat').unlink()
            data=read_data(folder/'waveform.dat.gz')
            if data.shape[1]!=len(vectors)+1:raise ValueError('Wrong transient columns')
            native=(folder/'ngspice.txt').read_text()
            rows=re.findall(r'No\. of Data Rows\s*:\s*(\d+)',native)
            if rows!=[str(len(data))] or 'ngspice-44.2 done' not in native:raise ValueError('Incomplete native run')
            checks=evaluate(case,data[:,:7],stop);write_json(folder/'checks.json',checks)
            write_json(folder/'observations.json',observations(case,data))
            negative=negative_controls(case,data[:,:7],stop)
            if not all(negative.values()):raise ValueError('Checker accepted wrong outputs')
            result['cases'].append(dict(case=case,status=checks['status'],returncode=proc.returncode,
                                         vectors=vectors,probes=probes,stop_ns=stop,resources=resource,
                                         dut_sha256=sha(folder/'dut.spice'),negative_controls=negative,
                                         uncompressed_waveform_sha256=hashlib.sha256(payload).hexdigest()))
            print(case['id'],checks['status'],flush=True);write_json(out/'results.json',result)
        result.update(execution_status='COMPLETED',functional_status='FAIL' if any(c['status']=='FAIL' for c in result['cases']) else 'PASS')
        for p,digest in inputs.items():
            if sha(ROOT/p)!=digest:raise ValueError('Changed input during diagnosis')
        for p,digest in result['model_inputs'].items():
            if sha(p)!=digest:raise ValueError('Changed PDK during diagnosis')
    except Exception as exc:
        result.update(execution_status='FAIL_EXECUTION',error=f'{type(exc).__name__}: {exc}')
        raise
    finally:seal(out,result)
    return result


def verify(out):
    result=json.loads((out/'results.json').read_text());planned=json.loads((out/'plan.json').read_text())
    if result['execution_status']!='COMPLETED' or result['criteria']!=CRITERIA or planned['criteria']!=CRITERIA:
        raise ValueError('Incomplete execution/changed criteria')
    if planned['cases']!=[c['case'] for c in result['cases']]:raise ValueError('Changed case matrix')
    for path,h in result['inputs'].items():
        if sha(ROOT/path)!=h:raise ValueError('Changed input: '+path)
    for path,h in result['model_inputs'].items():
        if sha(path)!=h:raise ValueError('Changed model: '+path)
    for path,h in result['artifacts'].items():
        if sha(out/path)!=h:raise ValueError('Changed artifact: '+path)
    _,selected=identities();view=selected['sense_amp']['views']['pex'];failed=0
    for item in result['cases']:
        case=item['case'];folder=out/case['id'];dut,description,probes=variant(case['mode'])
        text,vectors,stop=bench(case,view,probes)
        if (folder/'dut.spice').read_text()!=dut or (folder/'bench.spice').read_text()!=text:
            raise ValueError('Executed netlist or stimuli differ')
        if json.loads((folder/'transformation.json').read_text())!=description or item['vectors']!=vectors:
            raise ValueError('Changed transformation/probes')
        data=read_data(folder/'waveform.dat.gz');checks=evaluate(case,data[:,:7],stop)
        if checks!=json.loads((folder/'checks.json').read_text()) or checks['status']!=item['status']:
            raise ValueError('Full transient decision disagreement')
        with gzip.open(folder/'waveform.dat.gz','rb') as f:payload=f.read()
        if hashlib.sha256(payload).hexdigest()!=item['uncompressed_waveform_sha256']:raise ValueError('Changed raw')
        log=(folder/'ngspice.txt').read_text()
        if item['returncode']!=0 or re.findall(r'No\. of Data Rows\s*:\s*(\d+)',log)!=[str(len(data))]:
            raise ValueError('Native log mismatch')
        if observations(case,data)!=json.loads((folder/'observations.json').read_text()):raise ValueError('Changed observations')
        if not all(negative_controls(case,data[:,:7],stop).values()):raise ValueError('False positive checker')
        failed+=checks['status']=='FAIL'
    if result['functional_status']!=('FAIL' if failed else 'PASS'):raise ValueError('False aggregate status')
    return dict(evidence_status='PASS_INTEGRITY',cases=len(result['cases']),case_failures=failed,
                functional_status=result['functional_status'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--suite',choices=['sweep','ablation','operating'],default='sweep')
    p.add_argument('--deltas-mv',nargs='+',type=float)
    p.add_argument('--modes',nargs='+',choices=MODES,default=['no_c','no_r','no_rc'])
    p.add_argument('--verify',action='store_true')
    args=p.parse_args();out=args.output.resolve()
    if not out.is_relative_to(ROOT/'reports/phase1') or out==ROOT/'reports/phase1':p.error('New directory under reports/phase1 required')
    deltas=args.deltas_mv or ([5,10,20,30,50] if args.suite=='sweep' else [5])
    if any(not 0<d<500 for d in deltas) or len(set(deltas))!=len(deltas):p.error('Distinct positive small differentials required')
    result=verify(out) if args.verify else run(out,args.suite,deltas,args.modes)
    print(json.dumps({k:v for k,v in result.items() if k in ('evidence_status','execution_status','functional_status','case_failures')}))


if __name__=='__main__':main()
