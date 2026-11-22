#!/usr/bin/env python3
"""Recover the loaded TT control with the archived supply and idle prefix."""

import argparse
from decimal import Decimal
import fcntl
import json
import math
import os
from pathlib import Path
import re
import resource
import selectors
import subprocess
import time

import numpy as np

from diagnose_phase3_sclk_startup import FATAL, Observations, now, proc_sample
from phase3_sclk_loaded import (
    BUILD, HIGH, INITIAL, LOW, PCH, PDK, PEX, PEX_SHA, REFERENCE, ROOT, STOP,
    WORDLINES, WRITE_BOUNDARIES, archived, compress, control_verdict, ge, grid, inventory,
    le, load, logic_val, model_closure, new_directory, ngspice_limits, one_cross, pinned,
    pwl, read_stage, read_word, reference_compare, require, sample, sha256, view, write_json,
)
from phase3_sense3_precondition import pwl_tokens, write_knots
from run_phase3_sense3_isolation import ResistanceGraph
from review_phase3_bus_ss import Trace

BASE = BUILD/'sclk_shared_loaded_20261120'
BASE_SHA = '9e72e7e98baf18ff93901d4f1880cca4a3e452cdbbc427010140b3bca8edf854'
OFFSET = 47
JOIN = 46
HORIZON = STOP-INITIAL+OFFSET
HARD_S = 1200
PHASE_S = 300
GRACE_S = 2
OLD_SUPPLY = 'VDD_BASE VDD VSS 1.8'
SUPPLY = 'VDD_BASE VDD VSS PWL(0 0 1n 1.8)'
CARD = re.compile(r'(?m)^VREPLAY\d+ archive_\d+ VSS PWL\([^\n]*(?:\n\+[^\n]*)*?\n\+ \)')


def extend_card(card, startup_t, startup_v):
    head,old=pwl_tokens(card)
    _,prefix=pwl_tokens(pwl('Vstartup','a','b',startup_t,startup_v))
    require(old[0][0]==0 and old[-1][0]==STOP-INITIAL
            and prefix[0][0]==0 and prefix[-1][0]==JOIN,'Unexpected archived PWL bounds')
    shifted=[(t+OFFSET,v) for t,v in old]
    result=write_knots(head,[*prefix,*shifted])
    require(pwl_tokens(result)[1][-len(old):]==shifted,'Existing replay knots changed')
    return result.rstrip('\n')


def extend_stimuli(text,manifest,ref):
    require(text.splitlines().count(OLD_SUPPLY)==1 and 'VSS_BASE VSS 0 0\n' in text,'Supply boundary changed')
    links=dict(re.findall(r'(?m)^VCUT\d+ (\S+) (archive_\d+) 0$',text))
    sources={}
    for node,boundary in manifest['boundaries'].items():
        if label:=boundary['archived_trace']:
            name=links[node]
            require(name not in sources or sources[name]==label,'Incompatible archived source aliases')
            sources[name]=label
    used={}
    def change(match):
        card=match[0]
        name=card.split()[1]
        label=sources[name]
        points=ref.points(0.,float(JOIN),[(ref.cols[label],1.,0.)])
        a,v=np.asarray([(t,vector[0]) for t,vector in points]).T
        t,volts=compress(a,v)
        new=extend_card(card,t,volts)
        used[name]=dict(trace=label,original_knots=len(pwl_tokens(card)[1]),
                        extended_knots=len(pwl_tokens(new)[1]))
        return new
    modified=CARD.sub(change,text).replace(OLD_SUPPLY,SUPPLY)
    require(used.keys()==sources.keys(),'Incomplete prefix extension')
    require(CARD.sub('',modified).replace(SUPPLY,OLD_SUPPLY)==CARD.sub('',text),
            'A non-replay boundary changed')
    return modified,used


def storage(slice_text,manifest):
    cards={n:line.split()[1:] for n,line in inventory(slice_text).items()}
    graph=ResistanceGraph(cards)
    probes={}
    for row in (2,3):
        wordline=graph.group(manifest['wordlines'][row])
        for b,bit in enumerate(manifest['bits']):
            for name,side in [('q','bl_at_sense'),('qb','blb_at_sense')]:
                bus=graph.group(bit[side])
                hits=[(n,p) for n,p in cards.items() if n in manifest['physical_access_loads']
                      and p[1] in wordline and ((p[0] in bus)!=(p[2] in bus))]
                require(len(hits)==1,f'Expected one access device per cell terminal {row}/{b}/{name}')
                device,pins=hits[0]
                node=next(n for n in (pins[0],pins[2]) if n not in bus)
                require(node not in manifest['boundaries'],'Storage probe coincides with a source')
                probes[f'cell{row}_{b}_{name}']=dict(node=node,access_device=device)
    require(len({x['node'] for x in probes.values()})==32,'Storage probes are not unique')
    return probes


def audit_schedule(candidate,historical,manifest):
    cards={card[0].split()[1]:pwl_tokens(card[0])[1] for card in CARD.finditer(candidate)}
    oldcards={card[0].split()[1]:pwl_tokens(card[0])[1] for card in CARD.finditer(historical)}
    require(cards.keys()==oldcards.keys(),'Replay sources changed identity')
    for name,old in oldcards.items():
        require(cards[name][-len(old):]==[(t+OFFSET,v) for t,v in old],'Changed historical knot or level')
    links=dict(re.findall(r'(?m)^VCUT\d+ (\S+) (archive_\d+) 0$',candidate))
    trace_ports={b['archived_trace']:n for n,b in manifest['boundaries'].items()
                 if b['mode']=='captured_input_or_public_clock'}
    def values(label,t):
        points=cards[links[trace_ports[label]]]
        return float(np.interp(t,[float(a) for a,_ in points],[float(v) for _,v in points]))
    coords=[float(x) for x,_ in cards[links['CLK']]]
    tr=Trace([(t*1e-9,values('public_clk',t)) for t in coords],{'clk':1})
    clocks=[one_cross(tr,'clk',n-.2,n+.2,.5) for n in range(10,131,20)]
    require(all(x is not None and abs(x-(n+.025))<.001 for n,x in zip(range(10,131,20),clocks)),
            'Clock phase or cycle count changed')
    require(all(values('public_clk',t)<=LOW for t in (0.,.5,1.,46.,47.,49.)),
            'CLK not low at ramp or handoff')
    expected=[]
    for t,row,data in ((57.,2,15),(77.,3,240)):
        states=[logic_val(values(label,t)) for label in WRITE_BOUNDARIES]
        require(states[:2]==[1,0] and read_word(states[2:4])==row and read_word(states[4:])==data,
                'Altered write conditioning')
        expected.append(dict(local_ns=t,row=row,data=data))
    return dict(ramp_ns=[0.,1.],idle_clock_rises50_ns=clocks[:2],first_write_clock_rises50_ns=clocks[2:4],
        read_rises50_ns=clocks[4:],join_clock_low=True,writes=expected)


def observed_bench(original,vectors):
    require(original.count('tran 10p 100n 0 25p\n')==1 and original.count('.control\n')==1,'Unexpected archived deck')
    extra=' '.join(vectors)
    text=re.sub(r'(?m)^(\.save .+)$',r'\1 '+extra,original,count=1)
    text=re.sub(r'(?m)^(wrdata waveform\.dat .+)$',r'\1 '+extra,text,count=1)
    text=text.replace('.control\n','.control\necho __R87_DECK_READY__\n')
    return text.replace('tran 10p 100n 0 25p\n',f'set numdgt=15\necho __R87_TRAN_DISPATCH__\n'
          f'tran 10p {HORIZON:g}n 0 25p\necho __R87_TRAN_RETURN__\n')


def prepare(out):
    archived()
    m=json.loads(pinned(BASE/'manifest.json',BASE_SHA).read_text())
    _,old,trace=read_stage(BASE,'control')
    require(old['status']=='TIMEOUT' and trace is None,'Unexpected sealed parent attempt')
    for name,digest in m['source_sha256'].items():
        pinned(ROOT/name,digest)
    require(m['pex_sha256']==PEX_SHA,'PEX identity changed')
    pinned(PEX/'extracted_rc.spice',PEX_SHA)
    models=REFERENCE/'model_hashes.json'
    require(model_closure(PDK)==json.loads(models.read_text()),'Model closure changed')
    original_deck=(REFERENCE/'bench.spice').read_text()
    require('VDD_SRC VDD 0 PWL(0 0 1n 1.8)\n' in original_deck and
            'VSS_SRC VSS 0 0\n' in original_deck,'Archived VDD waveform changed')
    _,_,ref=load(REFERENCE,True)
    base=BASE/'control'
    stim=(base/'stimuli.spice').read_text()
    extended,files=extend_stimuli(stim,m,ref)
    schedule=audit_schedule(extended,stim,m)
    sliced=(base/'slice.spice').read_text()
    probes=storage(sliced,m)
    extra={k:f'v({item["node"].lower()})' for k,item in probes.items()}
    old_attempt=json.loads((base/'attempt.json').read_text())
    bench=observed_bench((base/'bench.spice').read_text(),extra.values())
    require(all(line in bench.splitlines() for line in m['config']) and
            not re.search(r'(?mi)^\.(?:ic|nodeset)\b|^tran .*\buic\b',bench+extended+sliced),
            'Numerical options or initial states changed')
    target=new_directory(out)
    (target/'slice.spice').write_bytes((base/'slice.spice').read_bytes())
    (target/'local_driver.spice').write_bytes((base/'local_driver.spice').read_bytes())
    (target/'bench.spice').write_text(bench)
    (target/'stimuli.spice').write_text(extended)
    before_signals=['public_clk',PCH,'macro_core.write_drive.X',*WORDLINES,*WRITE_BOUNDARIES[:4]]
    history={str(t):dict(vdd_v=ref.value(t,10),**{k:view(ref,k,t) for k in before_signals})
             for t in (0.,.5,1.,2.,9.,12.,30.,40.1,46.,47.,50.025,55.,87.,97.,117.)}
    dependencies=[Path(__file__),Path(__file__).with_name('phase3_sclk_loaded.py'),
                  Path(__file__).with_name('diagnose_phase3_sclk_startup.py'),
                  REFERENCE/'bench.spice',models,BASE/'manifest.json',base/'result.json',
                  *(base/n for n in ('slice.spice','stimuli.spice','bench.spice','local_driver.spice'))]
    write_json(target/'manifest.json',dict(schema='phase3.sclk_loaded_ramp.v1',previous_manifest_sha256=BASE_SHA,
        pex_sha256=PEX_SHA,retained_components=m['component_counts'],new_supply=SUPPLY,time_shift_ns=OFFSET,
        horizon_ns=HORIZON,startup_replay_ns=[0.,float(JOIN)],join_ns=[float(JOIN),float(OFFSET)],
        historical_read_mapping='reported reference time = simulator local time + 100 ns',
        archival_controls=history,schedule=schedule,extended_sources=files,storage_probes=probes,
        ordered_vectors=dict(old_attempt['output_vectors'],**extra),guards=dict(preparation_s=PHASE_S,
            initial_solution_from_dispatch_s=PHASE_S,total_s=HARD_S),
        source_sha256={str(p.relative_to(ROOT)):sha256(p) for p in dependencies},
        files_sha256={p.name:sha256(p) for p in target.iterdir()}))
    print(f'Prepared {target}',flush=True)


def guard(elapsed,events,error,stagnant=False):
    if error:
        return 'SIMULATOR_ERROR'
    if elapsed>=HARD_S-GRACE_S:
        return 'TOTAL_WALL_LIMIT'
    dispatch=events.get('tran_dispatch')
    if dispatch is None:
        return 'PREPARATION_WALL_LIMIT' if elapsed>=PHASE_S else None
    solved=events.get('initial_solution_reported') or events.get('first_positive_reference') or events.get('tran_return')
    if solved is None and elapsed-dispatch['elapsed_s']>=PHASE_S:
        return 'INITIAL_SOLUTION_WALL_LIMIT'
    return 'TRANSIENT_STAGNATION' if stagnant else None


OP_MESSAGES={'dynamic_gmin_started':'Starting dynamic gmin stepping',
             'dynamic_gmin_failed':'Dynamic gmin stepping failed',
             'dynamic_gmin_completed':'Dynamic gmin stepping completed',
             'true_gmin_started':'Starting true gmin stepping',
             'true_gmin_failed':'True gmin stepping failed',
             'source_stepping_started':'Starting source stepping'}


def last_time_ns(wave):
    if not wave.is_file():
        return None
    with wave.open('rb') as s:
        last=None
        for line in s:
            if line.strip():
                last=line
    try:
        return float(last.split()[0])*1e9
    except (AttributeError,ValueError):
        return None


def simulate(out):
    seal=out/'manifest.json'
    m=json.loads(seal.read_text())
    for prefix,items in ((ROOT,m['source_sha256']),(out,m['files_sha256'])):
        for name,digest in items.items():
            pinned(prefix/name,digest)
    require(model_closure(PDK)==json.loads((REFERENCE/'model_hashes.json').read_text()),'Model closure changed')
    cmd=['stdbuf','-o0','-e0','ngspice','-n','-b','bench.spice']
    version=subprocess.check_output(['ngspice','--version'],text=True,timeout=10).strip()
    write_json(out/'attempt.json',dict(command=cmd,manifest_sha256=sha256(seal),version=version,guards=m['guards']))
    usage=resource.getrusage(resource.RUSAGE_CHILDREN)
    start=time.monotonic()
    def stamp():
        return dict(wall=now(),elapsed_s=round(time.monotonic()-start,6))
    obs=Observations()
    inputs={'stdout':b'','stderr':b''}
    samples=[]
    reason=stop=error=None
    with (BUILD/'.eco_simulator.lock').open('a') as lock, selectors.DefaultSelector() as selector, \
         (out/'stdout.log').open('xb',buffering=0) as stdout, (out/'stderr.log').open('xb',buffering=0) as stderr, \
         (out/'samples.jsonl').open('x',buffering=1) as telemetry:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with subprocess.Popen(cmd,cwd=out,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,preexec_fn=ngspice_limits,
                env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}) as proc:
            launch=dict(stamp(),pid=proc.pid)
            selector.register(proc.stdout,selectors.EVENT_READ,('stdout',stdout))
            selector.register(proc.stderr,selectors.EVENT_READ,('stderr',stderr))
            next_sample=next_report=0.
            while proc.poll() is None or selector.get_map():
                info=stamp()
                elapsed=info['elapsed_s']
                if reason is None and proc.poll() is None:
                    reason=guard(elapsed,obs.events,error)
                    if reason:
                        stop=info
                        proc.terminate()
                if stop and elapsed-stop['elapsed_s']>=GRACE_S and proc.poll() is None:
                    proc.kill()
                for key,_ in selector.select(.20):
                    channel,log=key.data
                    data=os.read(key.fd,65536)
                    log.write(data)
                    obs.feed(channel,data,stamp(),eof=not data)
                    window=inputs[channel]+data
                    for event,text in OP_MESSAGES.items():
                        if text.encode() in window:
                            obs.events.setdefault(event,stamp())
                    if match:=FATAL.search(window):
                        error=match[0].decode()
                    inputs[channel]=window[-256:]
                    if not data:
                        selector.unregister(key.fileobj)
                if elapsed>=next_sample and proc.poll() is None:
                    data=proc_sample(proc.pid,info,obs.latest_ns,samples[-1] if samples else None)
                    if data:
                        samples.append(data)
                        telemetry.write(json.dumps(data)+'\n')
                        next_sample=elapsed+5
                if elapsed>=next_report:
                    phase='integration' if 'initial_solution_reported' in obs.events or obs.max_ns else (
                        'initial_solution' if 'tran_dispatch' in obs.events else 'deck_preparation')
                    print(f'{elapsed:.0f} s | {phase} | latest transient ns: {obs.latest_ns}',flush=True)
                    next_report=elapsed+60
            ended=stamp()
    spent=resource.getrusage(resource.RUSAGE_CHILDREN)
    end_ns=last_time_ns(out/'waveform.dat')
    ok=(not reason and not error and proc.returncode==0 and end_ns is not None and
        'tran_return' in obs.events and math.isclose(end_ns,HORIZON,abs_tol=1e-6,rel_tol=0.))
    write_json(out/'result.json',dict(status='COMPLETED' if ok else 'INCONCLUSIVE',termination=reason or 'PROCESS_EXIT',
        simulator_error=error,elapsed_s=ended['elapsed_s'],ngspice_exit_code=proc.returncode,verified_end_ns=end_ns,
        last_reference_ns=obs.max_ns,events=obs.events,launch=launch,ended=ended,stop_requested=stop,
        cpu_s=(spent.ru_utime+spent.ru_stime)-(usage.ru_utime+usage.ru_stime),
        peak_rss_kib=max((s['hwm_kib'] or 0 for s in samples),default=None),samples=len(samples),
        files_sha256={p.name:sha256(p) for p in out.iterdir()}))
    print('COMPLETED' if ok else 'INCONCLUSIVE',reason or 'PROCESS_EXIT',flush=True)
    return int(not ok)


def read_trace(out,m):
    with (out/'waveform.dat').open() as stream:
        vectors=m['ordered_vectors']
        require(stream.readline().lower().split()==['time',*vectors.values()],'Saved voltages/currents do not match manifest')
        data=np.loadtxt(stream,ndmin=2)
    require(data.shape[1]==len(vectors)+1 and len(data)>3 and np.all(np.isfinite(data)) and
        np.all(np.diff(data[:,0])>0) and abs(data[-1,0]*1e9-HORIZON)<1e-6,'Incomplete or ambiguous native samples')
    data[:,0]+=(INITIAL-OFFSET)*1e-9
    return Trace(data.tolist(),{n:i for i,n in enumerate(vectors,1)})


def storage_word(trace,row,when):
    values=[]
    for bit in range(8):
        q,qb=(logic_val(view(trace,f'cell{row}_{bit}_{k}',when)) for k in ('q','qb'))
        values.append(q if q is not None and qb==1-q else None)
    return read_word(values)


def measure_write(trace,row,word,rise,intervals):
    wl=f'wl{row}'
    start=rise+1.
    end=rise+9.8
    active=one_cross(trace,wl,start,end,.8)
    controls={n:view(trace,n,end) for n in ('write_enable','precharge',*(f'wl{i}' for i in range(4)))}
    correct_wl=bool(active is not None and controls[wl]>=HIGH and controls['write_enable']>=HIGH and
        controls['precharge']>=HIGH and all(trace.through(start,end,[le(trace.cols[f'wl{i}'],LOW)])
            for i in range(4) if i!=row))
    bitline=[]
    storage=[]
    for bit in range(8):
        expected=(word>>bit)&1
        pairs=[(f'b{bit}_bl_at_sense',expected),(f'b{bit}_blb_at_sense',1-expected)]
        levels={n:view(trace,n,end) for n,_ in pairs}
        spec=[(ge if val else le)(trace.cols[n],HIGH if val else LOW) for n,val in pairs]
        bitline.append(dict(bit=bit,end_v=levels,stable=trace.signal_window(start,end,spec,suffix=True)))
        pairs=[(f'cell{row}_{bit}_q',expected),(f'cell{row}_{bit}_qb',1-expected)]
        spec=[(ge if val else le)(trace.cols[n],HIGH if val else LOW) for n,val in pairs]
        storage.append(dict(bit=bit,stable_before_release=trace.signal_window(start,end,spec,suffix=True),
            retention=[dict(from_ns=a,through_ns=b,stable=trace.through(a,b,spec)) for a,b in intervals],
            checkpoints_v={str(t):{n:view(trace,n,t) for n,_ in pairs} for t in (end,*(b for _,b in intervals))}))
    after=storage_word(trace,row,intervals[0][0])
    confirmed=bool(correct_wl and after==word and all(k['stable'] for k in bitline) and
                   all(k['stable_before_release'] and all(z['stable'] for z in k['retention']) for k in storage))
    return dict(row=row,expected=word,clock_rise_reference_ns=rise,wl80_reference_ns=active,
        end_control_voltages=controls,selection_valid=correct_wl,bitlines=bitline,storage=storage,
        stored_after_write=after,stored_before_reads=[storage_word(trace,row,b) for _,b in intervals],confirmed=confirmed)


def final_verdict(reads,writes):
    if any(w['stored_after_write'] is not None and w['stored_after_write']!=w['expected'] for w in writes):
        return 'NOT_REPRODUCED'
    if len(writes)!=2 or not all(w['confirmed'] for w in writes):
        return 'INCONCLUSIVE'
    return control_verdict(reads)


def analyze(out):
    r_path=out/'result.json'
    result=json.loads(r_path.read_text())
    for n,h in result['files_sha256'].items():
        pinned(out/n,h)
    attempt=json.loads((out/'attempt.json').read_text())
    m=json.loads(pinned(out/'manifest.json',attempt['manifest_sha256']).read_text())
    previous=json.loads(pinned(BASE/'manifest.json',BASE_SHA).read_text())
    gate=dict(verdict='INCONCLUSIVE',result_sha256=sha256(r_path),manifest_sha256=sha256(out/'manifest.json'),
              driver_v1='NOT_RUN',qualification='NOT_CHARACTERIZED')
    if result['status']=='COMPLETED':
        try:
            trace=read_trace(out,m)
        except ValueError as exc:
            gate['waveform_evidence_error']=str(exc)
        else:
            writes=[measure_write(trace,2,0x0F,150.,[(161.,189.9)]),
                    measure_write(trace,3,0xF0,170.,[(181.,209.9),(225.,229.9),(245.,246.9)])]
            _,_,ref=load(REFERENCE,True)
            reads=[]
            for case in previous['cases']:
                read=reference_compare(trace,ref,previous,case)
                actual=case['conditioning_ns']
                read['stored_word_pre_read']=storage_word(trace,case['row'],actual)
                read['expected_bitcell3_v']={key:view(trace,f'cell{case["row"]}_3_{key}',actual) for key in ('q','qb')}
                for bit in read['bits']:
                    captured=bit['observed']['capture_ns']
                    expected=case['captures_ns'][bit['bit']]
                    bit['capture_delta_ps']=None if captured is None else (captured-expected)*1000
                delta_bl=read['bits'][3]['observed']['event']['activation']['difference_bl_v']
                read['sense3_differential_sign_ok']=bool(delta_bl>0) if case['cycle'] in (16,17) else None
                read['equivalent']=bool(read['equivalent'] and read['stored_word_pre_read']==case['expected_word']
                    and read['sense3_differential_sign_ok'] is not False and
                    all(b['capture_delta_ps'] is not None and abs(b['capture_delta_ps'])<=25 for b in read['bits']))
                reads.append(read)
            gate.update(samples=len(trace.rows),writes=writes,reads=reads,verdict=final_verdict(reads,writes))
    else:
        gate['reason']='Complete transient unavailable'
    write_json(out/'control_gate.json',gate)
    print(gate['verdict'],flush=True)
    return int(gate['verdict']!='VALIDATED')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('prepare','control','analyze'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    out=args.output.resolve()
    if args.stage=='prepare':
        prepare(out)
        return 0
    return simulate(out) if args.stage=='control' else analyze(out)


if __name__=='__main__':
    raise SystemExit(main())
