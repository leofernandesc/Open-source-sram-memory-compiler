#!/usr/bin/env python3
"""Prepare a local Norton SCLK contrast and gate it on a short TT startup."""

import argparse
from collections import defaultdict
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import time

from analyze_phase3_data3_tt import load
from phase3_rc_probe_report import read_waveform
from review_phase3_bus_ss import Trace
from run_phase3_data3_tt import BUILD, PDK, ROOT, model_closure, sha256
from run_phase3_eco_pex import new_directory, ngspice_limits, pinned
from run_phase3_integrated_ss import EXTRA
from run_phase3_sclk_contrast import GATES, REFERENCE


DELAY_PS = 182
SHORT_NS = 14
FULL_NS = 250
WINDOWS = ((211,219),(231,239))
GUARDS = ((120,1.),(300,10.))


def require(check, message):
    if not check:
        raise ValueError(message)


def branch(binding, mapping, edge='R87'):
    adjacency=defaultdict(set)
    boundary=None
    devices=[]
    caps=[]
    for card in binding.splitlines():
        pieces=card.split()
        if not pieces or not re.fullmatch(r'[RXC]\d+',pieces[0]):
            continue
        name,a,b=pieces[:3]
        if name==edge:
            boundary=(a,b,float(pieces[3]))
        elif name[0]=='R':
            adjacency[a].add(b)
            adjacency[b].add(a)
        elif name[0]=='X':
            devices.append((name,pieces[1:5]))
        else:
            caps.append((name,a,b))
    require(boundary is not None,f'Missing {edge}')
    upstream,local,resistance=boundary
    nodes=set()
    queue=[local]
    while queue:
        node=queue.pop()
        if node not in nodes:
            nodes.add(node)
            queue.extend(adjacency[node]-nodes)
    gates={mapping[key] for key in GATES}
    touched=[(name,pins) for name,pins in devices if any(pin in nodes for pin in pins)]
    require(upstream not in nodes and nodes=={local,*gates} and resistance>0 and len(touched)==3
            and {pins[1] for _,pins in touched}==gates
            and all(sum(p in nodes for p in pins)==1 for _,pins in touched),
            'Candidate resistor does not isolate precisely the three gate terminals')
    return dict(card=edge,upstream=upstream,local=local,resistance_ohm=resistance,
                consumers=touched,external_caps=[row for row in caps if sum(n in nodes for n in row[1:])==1])


def current_points(trace,resistance,delay_ps=DELAY_PS):
    points=[(0.,0.)]
    for begin,end in WINDOWS:
        for sample in range((end-begin)*200+1):
            t=begin+sample/200
            mask=min(1.,sample/5,((end-begin)*200-sample)/5)
            delta=sum(trace.value(t-delay_ps/1000,trace.cols[gate])-trace.value(t,trace.cols[gate])
                      for gate in GATES)/len(GATES)
            points.append((t,mask*delta/resistance))
    return points


def overlay(binding, proof, points):
    prefix,end=binding.rsplit('\n',2)[:2]
    require(end.startswith('.ends ') and binding.endswith('\n'),'Unexpected subcircuit ending')
    values=[f'{t:.6f}n {a:.12g}' for t,a in points]
    records=[' '.join(values[i:i+6]) for i in range(0,len(values),6)]
    a,b=proof['upstream'],proof['local']
    return '\n'.join([prefix,f'I_sclk_r87 {a} {b} PWL({records[0]}',
                       *('+ '+row for row in records[1:]),'+ )',end,''])


def prepare(output):
    source, sim, trace=load(REFERENCE,True)
    mapping=json.loads((REFERENCE/'probes.json').read_text())
    binding=(REFERENCE/'binding.spice').read_text()
    proof=branch(binding,mapping)
    points=current_points(trace,proof['resistance_ohm'])
    derived=overlay(binding,proof,points)
    deck=(REFERENCE/'bench.spice').read_text()
    require(deck.count('.include "binding.spice"')==1 and deck.count('tran 10p 250n 0 25p')==1,
            'Unexpected parent bench')
    out=new_directory(output)
    for name in ('binding.spice','model_hashes.json','fabric.spice','probes.json'):
        (out/name).write_bytes((REFERENCE/name).read_bytes())
    (out/'norton_fixture.spice').write_text(derived)
    bench=deck.replace('.include "binding.spice"','.include "norton_fixture.spice"')
    for mode,stop in (('startup',SHORT_NS),('full',FULL_NS)):
        (out/f'{mode}.spice').write_text(bench.replace('tran 10p 250n 0 25p',f'tran 10p {stop}n 0 25p'))
    source=dict(candidate=source['candidate'],pex_sha256=source['pex_sha256'],
                reference_waveform_sha256=sim['waveform_sha256'], delay_ps=DELAY_PS,
                branch=proof,source_peak_abs_a=max(abs(a) for _,a in points),
                source_zero_outside_windows=True,windows_ns=WINDOWS,source_spacing_ps=5,
                startup_horizon_ns=SHORT_NS,full_horizon_ns=FULL_NS,guards=GUARDS,
                startup_control_tolerance_v=.005,edge_fidelity_tolerance_ps=25,
                sources={str(p.relative_to(ROOT)):sha256(p) for p in
                         (REFERENCE/'preflight.json',REFERENCE/'simulation.json',Path(__file__).resolve())},
                artifacts={p.name:sha256(p) for p in out.iterdir()})
    (out/'preflight.json').write_text(json.dumps(source,indent=2)+'\n')
    print(f'Prepared {out}',flush=True)


def checked(output):
    data=json.loads((output/'preflight.json').read_text())
    for name,h in data['sources'].items():
        pinned(ROOT/name,h)
    for name,h in data['artifacts'].items():
        pinned(output/name,h)
    return data


def read_run(directory, names, stop, receipt):
    nodes=json.loads(names.read_text())
    wave=pinned(directory/'waveform.dat',receipt['waveform_sha256'])
    records, cols=read_waveform(wave,sorted(set(nodes.values())),EXTRA,minimum_end=stop*1e-9-1e-15)
    cols.update((alias,cols[node]) for alias,node in nodes.items())
    cols.update(public_clk=1,vdd=10)
    return Trace(records,cols)


def startup_compare(output,run,result,started):
    _,_,baseline=load(REFERENCE,True)
    baseline.cols['vdd']=10
    new=read_run(run,output/'probes.json',SHORT_NS,result)
    controls=['public_clk','vdd','v(CSb)','v(OEb)','v(WEb)','macro_core.precharge_drive.X',
              'macro_core.evaluation.X','_62_.Y','sclk_tail',*(f'SCLK_SENSE_{i}' for i in range(8))]
    # Compare idle plateaus, away from the programmed first clock edge.
    idle=[x/8 for x in range(10,112) if not 9.75<=x/8<=10.25]
    errors={name:max(abs(new.value(t,new.cols[name])-baseline.value(t,baseline.cols[name])) for t in idle)
            for name in controls}
    limit=json.loads((output/'preflight.json').read_text())['startup_control_tolerance_v']
    return dict(status='PASS' if max(errors.values())<=limit else 'BLOCKED',
                duration_s=time.monotonic()-started,comparison_samples=len(idle),max_difference_v=errors,
                startup_waveform_sha256=result['waveform_sha256'],simulator_receipt_sha256=sha256(run/'result.json'),
                parent_manifest_sha256=sha256(output/'preflight.json'))


def execute(output,mode,timeout):
    data=checked(output)
    if mode=='full':
        gate=json.loads((output/'startup_gate.json').read_text())
        require(gate['status']=='PASS' and gate['parent_manifest_sha256']==sha256(output/'preflight.json'),
                'Full TT blocked by startup gate')
        pinned(output/'startup/result.json',gate['simulator_receipt_sha256'])
        pinned(output/'startup/waveform.dat',gate['startup_waveform_sha256'])
    require(model_closure(PDK)==json.loads((output/'model_hashes.json').read_text()),'PDK changed')
    work=new_directory(output/mode)
    for name in ('fabric.spice','norton_fixture.spice'):
        (work/name).write_bytes((output/name).read_bytes())
    (work/'bench.spice').write_bytes((output/f'{mode}.spice').read_bytes())
    cmd=['ngspice','-n','-b','bench.spice']
    (work/'attempt.json').write_text(json.dumps(dict(command=cmd,timeout_s=timeout, mode=mode,
        preflight_sha256=sha256(output/'preflight.json'),guards=GUARDS),indent=2)+'\n')
    log=work/'ngspice.log'
    begin=time.monotonic()
    notes=[]
    reason=None
    last=0.
    with (BUILD/'.eco_simulator.lock').open('a') as lock,log.open('xb') as stream:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with subprocess.Popen(cmd,cwd=work,stdout=stream,stderr=subprocess.STDOUT,
                              env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'},
                              preexec_fn=ngspice_limits) as proc:
            while proc.poll() is None:
                elapsed=time.monotonic()-begin
                ticks=re.findall(rb'Reference value\s*:\s*(\S+)',log.read_bytes())
                last=float(ticks[-1])*1e9 if ticks else 0.
                for elapsed_s,ns in GUARDS[len(notes):]:
                    if elapsed>=elapsed_s:
                        notes.append(dict(elapsed_s=elapsed,reached_ns=last,minimum_exclusive_ns=ns))
                        if last<=ns:
                            reason=f'Progress guard at {elapsed_s}s'
                            break
                if not reason and elapsed>=timeout:
                    reason='Operational timeout'
                if reason:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=5)
                    break
                time.sleep(1)
    raw=log.read_bytes()
    ticks=re.findall(rb'Reference value\s*:\s*(\S+)',raw)
    elapsed=time.monotonic()-begin
    successful=(not reason and proc.returncode==0 and re.search(rb'^ngspice-\S+ done\s*$',raw,re.M)
                and not re.search(rb'analysis aborted|timestep too small|^\s*(?:Fatal|Error):',raw,re.I|re.M)
                and (work/'waveform.dat').is_file())
    receipt=dict(status='PASS' if successful else 'ERROR',stop_reason=reason,elapsed_s=elapsed,
                 last_progress_ns=float(ticks[-1])*1e9 if ticks else None,guard_observations=notes,
                 ngspice_returncode=proc.returncode,log_sha256=sha256(log),
                 horizon_ns=SHORT_NS if mode=='startup' else FULL_NS)
    if successful:
        receipt['waveform_sha256']=sha256(work/'waveform.dat')
    (work/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if mode=='startup':
        gate=dict(status='BLOCKED',reason=reason or 'Startup waveform unavailable')
        if successful:
            gate=startup_compare(output,work,receipt,begin)
        (output/'startup_gate.json').write_text(json.dumps(gate,indent=2)+'\n')
        print(json.dumps(gate),flush=True)
    print(json.dumps(receipt),flush=True)
    return int(not successful or (mode=='startup' and gate['status']!='PASS'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','startup','full'))
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--timeout',type=int)
    a=p.parse_args()
    if a.action=='prepare':
        prepare(a.output.resolve())
        return 0
    defaults={'startup':420,'full':2400}
    limit=a.timeout if a.timeout is not None else defaults[a.action]
    require(0<limit<=defaults[a.action],'Invalid operational timeout')
    return execute(a.output.resolve(),a.action,limit)


if __name__=='__main__':
    raise SystemExit(main())
