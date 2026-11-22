#!/usr/bin/env python3
"""Loaded TT sense replay with a causal gate before inserting driver v1."""

import argparse
from collections import Counter, defaultdict, deque
import csv
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import time

import numpy as np

from analyze_phase3_data3_tt import load
from analyze_phase3_sclk_r87_full import edges, gate_shape, scalar, view
from analyze_phase3_sense3_isolation import assess_event, conditioning_valid, input_evidence, one_cross
from phase3_rc_probe import rc_node_map
from phase3_rc_read_path import HIGH, LOCAL_CLOCKS, LOW, WORDLINES
from phase3_sclk_local_driver import (
    BASE, CELL, DRIVER, GATE_HASHES, LIB, MANIFEST, archived, intersect, library_cell,
)
from phase3_sclk_r87 import branch
from phase3_sense3_precondition import (
    BUILD, GATES, PDK, REFERENCE, ROOT, START, STOP, TAIL_ON_A, compress, grid, model_closure,
    new_directory, ngspice_limits, outside, pinned, pwl, require, sample, sha256, write_json,
)
from review_phase3_bus_ss import Trace, ge, le
from run_phase3_data3_tt import ARRAY, PEX, PEX_SHA
from run_phase3_sense3_isolation import ResistanceGraph

INITIAL = 147.
PREFIX_END = 187.
BACKSHIFT = 60.
TIMEOUT = 720
CONTROL_MV = .030169318453526106
WINDOWS = [(15,191.,199.,189.9,0x0F,2),(16,211.,219.,209.9,0xF0,3),(17,231.,239.,229.9,0xF0,3)]
SCLK = 'macro_core.sense_drive.X'
PCH = 'macro_core.precharge_drive.X'
ISOLATED = BUILD/'sclk_local_driver_20261120_v1'
WRITE_BOUNDARIES = ('_83_.Q','_84_.Q','_85_.Q','_86_.Q',*(f'_{67+i}_.Q' for i in range(8)))
Q_NAMES = ('_75_.Q',*(f'_{87+i}_.A' for i in range(1,8)))


def inventory(text):
    return {line.split()[0]:line for line in text.splitlines() if re.match(r'^[XRC]\d+ ',line)}


def pull_region(cards,graph,targets,ports):
    """Follow physical MOS drain/source connections until reaching replay inputs/rails."""
    drivers=defaultdict(set)
    for key,card in cards.items():
        if key.startswith('X'):
            drivers[card[0]].add(key)
            drivers[card[2]].add(key)
    boundaries=set().union(*(graph.group(node) for node in ports))
    keep=set()
    loaded=set()
    todo=deque(sorted(targets))
    while todo:
        node=todo.popleft()
        if node in loaded or node in boundaries:
            continue
        group=graph.group(node)
        loaded.update(group)
        found=set().union(*(drivers[n] for n in group))
        require(found,f'No physical driver for {node}; cannot replay the shared control')
        for device in sorted(found-keep):
            keep.add(device)
            todo.extend(cards[device][:4])
    return keep,loaded,boundaries


def cycle_plan(ref,probes):
    plan=[]
    for cycle,start,high,condition,word,row in WINDOWS:
        captures=[]
        for name in LOCAL_CLOCKS:
            capture=one_cross(ref,name,high+1,high+1.35,.5)
            require(capture is not None and name in probes,f'Capture clock unavailable for cycle {cycle}')
            captures.append(capture)
        plan.append(dict(cycle=cycle,low_ns=start,high_ns=high,conditioning_ns=condition,
                         capture_ns=max(captures),captures_ns=captures,expected_word=word,row=row,
                         recovery_ns=min(high+8,STOP)))
    return plan


def bit_probes(cards,graph,archived_nodes,selected,bit):
    bl=f'{ARRAY}.write_driver_{bit}.BL'
    blb=bl+'B'
    blnode,blbnode,sa,sab=(archived_nodes[n] for n in
            (bl,blb,f'_{43-bit}_.A1',f'{ARRAY}.sense_amp_{bit}.SA_OUTB'))
    clock=graph.group(archived_nodes[SCLK])
    def device(gate_group,a,b):
        out=[]
        for name,pins in selected.items():
            if pins[1] in gate_group and ((pins[0] in a and pins[2] in b) or (pins[2] in a and pins[0] in b)):
                out.append((name,pins))
        require(len(out)==1,f'Unexpected physical topology for bit {bit}: {out}')
        return out[0]
    bl_group,blb_group,sa_group,sab_group=(graph.group(n) for n in (blnode,blbnode,sa,sab))
    ba,x=device(clock,bl_group,sa_group)
    bb,y=device(clock,blb_group,sab_group)
    prech=graph.group(archived_nodes[PCH])
    p0,p1,eq=(device(prech,g0,g1) for g0,g1 in ((graph.group('VDD'),bl_group),
                                               (graph.group('VDD'),blb_group),(bl_group,blb_group)))
    ground=graph.group('VSS')
    outputs=sa_group|sab_group
    tail_candidates={graph.group(p[2] if p[0] in outputs else p[0])
                     for p in selected.values() if
                     any(p[1] in one and (p[0] in other or p[2] in other)
                         for one,other in ((sa_group,sab_group),(sab_group,sa_group))) and
                     'nfet' in p[4] and (p[0] in sa_group|sab_group or p[2] in sa_group|sab_group)}
    eligible=[(n,p) for n,p in selected.items() if p[1] in clock and
              (p[0] in ground or p[2] in ground) and
              graph.group(p[2] if p[0] in ground else p[0]) in tail_candidates]
    require(len(eligible)==1,f'Tail not unique at bit {bit}')
    tail,t=eligible[0]
    src=t[0] if t[0] in ground else t[2]
    other=lambda p,net: next(i for i in (p[0],p[2]) if i in net)
    return dict(bl_at_sense=blnode,blb_at_sense=blbnode,sense_out=sa,sense_bar=sab,
        sa_sampling_out=other(x,sa_group),sab_sampling_out=other(y,sab_group),
        sclk_sampler_bl=x[1],sclk_sampler_blb=y[1],sclk_tail=t[1],tail_ground=src,
        sense_tail=other(t,graph.group(t[2] if t[0] in ground else t[0])),
        read_d=archived_nodes[f'_{75+bit}_.D'],read_q=archived_nodes[Q_NAMES[bit]],
        capture_clock=archived_nodes[LOCAL_CLOCKS[bit]],precharge_bl_gate=p0[1][1],
        precharge_blb_gate=p1[1][1],equalizer_gate=eq[1][1],vdd_local=x[3],
        currents={'tail_id':tail,'precharge_bl_id':p0[0],'precharge_blb_id':p1[0],'equalizer_id':eq[0]},
        samplers=[ba,bb])


def replay(ref,trace_label):
    """Use last historical writes c4/c5 before keeping the archived c15–17 exactly."""
    def points(a,b,shift):
        native=ref.points(a,b,[(ref.cols[trace_label],1.,0.)])
        times,values=np.asarray([(t,v[0]) for t,v in native]).T
        t,v=compress(times,values)
        return t+shift-INITIAL,v
    ta,va=points(INITIAL-BACKSHIFT,PREFIX_END-BACKSHIFT,BACKSHIFT)
    tb,vb=points(START,STOP,0.)
    return np.r_[ta,tb],np.r_[va,vb]


def currents_key(card,model):
    return f'@m.{card.lower()}.m{model.lower()}[id]'


def render_bench(config,vectors):
    values=' '.join(vectors)
    return '\n'.join(['* Shared SCLK loaded cut',
        *config,'.include "slice.spice"','.include "stimuli.spice"','.include "local_driver.spice"',
        f'.save {values}', '.control','set num_threads=1','set noaskquit','set wr_singlescale',
        'set wr_vecnames',f'tran 10p {STOP-INITIAL:g}n 0 25p',f'wrdata waveform.dat {values}',
        'quit','.endc','.end',''])


def prepare(out):
    sealed=archived()
    pex=pinned(PEX/'extracted_rc.spice',PEX_SHA)
    pf,_,ref=load(REFERENCE,True)
    models=REFERENCE/'model_hashes.json'
    require(pf['pex_sha256']==PEX_SHA and model_closure(PDK)==json.loads(models.read_text()),'PEX or TT model closure changed')
    binding=REFERENCE/'binding.spice'
    nodes=json.loads((REFERENCE/'probes.json').read_text())
    names={v:k for k,v in rc_node_map(pex.read_text()).items()}
    raw=inventory(binding.read_text())
    cards={k:v.split()[1:] for k,v in raw.items()}
    graph=ResistanceGraph(cards)
    proof=branch(binding.read_text(),nodes)
    ports={nodes[k]:k for k in WRITE_BOUNDARIES}
    ports['CLK']='public_clk'
    targets={nodes[x] for x in (SCLK,PCH,*WORDLINES,*Q_NAMES,'macro_core.evaluation.X',
                               'macro_core.write_drive.X',*[f'_{75+i}_.D' for i in range(8)])}
    targets.update(nodes[n] for n in nodes if '.write_driver_' in n)
    selected,active,bound=pull_region(cards,graph,targets,(*ports,'VDD','VSS'))
    moses={n:cards[n] for n in sorted(selected)}
    bits=[bit_probes(cards,graph,nodes,moses,b) for b in range(8)]
    for bit in bits:
        require(all(n in active|bound for k,n in bit.items() if isinstance(n,str)), 'Bit probe lies outside cut')
    shared=graph.group(proof['upstream'])
    prech=graph.group(nodes[PCH])
    wordline=set().union(*(graph.group(nodes[n]) for n in WORDLINES))
    wl_loads=[n for n,c in moses.items() if c[1] in wordline and c[4].endswith('nfet_01v8')]
    require(len(wl_loads)==64,'Expected two native access MOS per bitcell')
    require(all(any(bit[g] in shared for g in GATES) for bit in bits) and not (bound&shared or bound&prech or bound&wordline),
            'A primary boundary would clamp a shared output')
    rails=graph.group('VDD')|graph.group('VSS')
    retained=active|bound
    scope=retained-rails
    keep={}
    omitted=[]
    attached=set()
    for name,card in cards.items():
        a,b=card[:2]
        retain=(name in selected if name[0]=='X' else ({a,b}<=retained if name[0]=='R' else
                       bool(({a,b}&scope or {a,b}<=rails) and float(re.match(r'[0-9.eE+-]+',card[2])[0])!=0.)))
        if retain:
            keep[name]=raw[name]
            if name[0]=='C':
                attached.update({a,b}-retained)
        else:
            omitted.append((name,'outside_loaded_cut',raw[name]))
    require(proof['card'] in keep,'R87 absent in loaded cut')
    trace_by_node={node:key for key,node in nodes.items() if key in ref.cols}
    probes_by_group=defaultdict(list)
    for node in trace_by_node:
        probes_by_group[graph.group(node)].append(node)
    sources_by_label={}
    strings=['VSS_BASE VSS 0 0\n','VDD_BASE VDD VSS 1.8\n']
    boundaries={}
    def boundary(node,label,mode,archived_node=None,route=None):
        number=len(boundaries)
        if label is None:
            strings.append(f'VCUT{number} {node} VSS 0\n')
        else:
            if label not in sources_by_label:
                t,v=replay(ref,label)
                source=f'archive_{len(sources_by_label)}'
                strings.append(pwl(f'VREPLAY{len(sources_by_label)}',source,'VSS',t,v))
                sources_by_label[label]=source
            strings.append(f'VCUT{number} {node} {sources_by_label[label]} 0\n')
        boundaries[node]=dict(mode=mode,archived_trace=label,archived_node=archived_node,
                             proxy_route_ohm=route,original_node=names.get(node,node))
    for node,key in ports.items():
        boundary(node,key,'captured_input_or_public_clock',node,0.)
    for node in sorted(attached):
        group=graph.group(node)
        if hits:=probes_by_group.get(group):
            d,path=graph.shortest(node,set(hits))
            boundary(node,trace_by_node[path[-1]],'coupled_plate_replay',path[-1],d)
        else:
            boundary(node,None,'coupled_plate_fixed_to_vss')
    require(not (set(boundaries)&(shared|prech|wordline|rails)), 'A generated control or rail would be clamped')
    base_vectors={'root':f'v({nodes[SCLK]})','r87_upstream':f'v({proof["upstream"]})','precharge':f'v({nodes[PCH]})',
                  'vdd':'v(vdd)','vss':'v(vss)','supply_a':'i(vdd_base)','clk':'v(clk)',
                  'write_enable':f'v({nodes["macro_core.write_drive.X"]})',
                  **{f'wl{i}':f'v({nodes[key]})' for i,key in enumerate(WORDLINES)}}
    for b,one in enumerate(bits):
        base_vectors.update({f'b{b}_{key}':f'v({value.lower()})' for key,value in one.items() if isinstance(value,str)})
        base_vectors.update({f'b{b}_{key}':currents_key(name,cards[name][4]) for key,name in one['currents'].items()})
    # Store the exact ordered columns even where two logical probes map to one node.
    config=[line for line in (BASE/'bench.spice').read_text().splitlines() if line.startswith(('.lib ','.temp ','.options '))]
    plans=cycle_plan(ref,nodes)
    original_sclk={f'b{b}':one['sclk_sampler_bl'] for b,one in enumerate(bits)}
    fixed_caps=sum(1 for n,l in keep.items() if n.startswith('C') and
                any(boundaries.get(p,{}).get('mode')=='coupled_plate_fixed_to_vss' for p in cards[n][:2]))
    library_file=LIB/'spice/sky130_fd_sc_hd.spice'
    physical_cell=library_cell(library_file.read_text())
    older=json.loads((ISOLATED/'manifest.json').read_text())
    require(sha256(DRIVER)==older['driver_source_sha256'] and
            sha256(library_file)==older['pdk']['library_sha256'] and
            physical_cell==(ISOLATED/'driver_library.spice').read_text(),'Driver or installed library changed')
    out=new_directory(out)
    (out/'slice.spice').write_text('\n'.join(keep.values())+'\n')
    (out/'stimuli.spice').write_text(''.join(strings))
    (out/'driver_library.spice').write_text(physical_cell)
    (out/'driver_cell.spice').write_bytes(DRIVER.read_bytes())
    with (out/'removed.csv').open('x',newline='') as stream:
        writer=csv.writer(stream)
        writer.writerow(('card','reason','original'))
        writer.writerows(omitted)
    use_sources=(binding,pex,models,REFERENCE/'waveform.dat',REFERENCE/'preflight.json',REFERENCE/'simulation.json',
                 REFERENCE/'probes.json',Path(__file__),DRIVER,BASE/'manifest.json',
                 BASE/'control_gate.json',BASE/'contrast_gate.json',ISOLATED/'manifest.json')
    write_json(out/'manifest.json',dict(schema='phase3.sclk_loaded.v1',pex_sha256=PEX_SHA,
        prepared=time.strftime('%Y-%m-%dT%H:%M:%S%z'),component_counts=dict(Counter(n[0] for n in keep)),
        excluded_card_count=len(omitted),preserved_mos=sorted(moses),scope_nodes=len(retained),
        archived_write_prefix=dict(source_ns=[INITIAL-BACKSHIFT,PREFIX_END-BACKSHIFT],
           replay_ns=[INITIAL,PREFIX_END],natural_writes=[dict(row=2,data='0x0F'),dict(row=3,data='0xF0')],
           join_ns=[PREFIX_END,START],original_evaluation_window_ns=[START,STOP]),
        conditions=dict(sealed['conditions'],ppa_transient_ns=STOP-INITIAL,timeout_s=TIMEOUT),
        baseline_manifest_sha256=MANIFEST,baseline_gate_sha256=GATE_HASHES,
        measurements=base_vectors,cases=plans,bits=bits,sclk=dict(branch=proof,nodes=sorted(shared),
             output_probe=nodes[SCLK],branch_sampler_gates=original_sclk),
        precharge=dict(command=nodes[PCH],nodes=sorted(prech)),
        wordlines=[nodes[n] for n in WORDLINES],physical_access_loads=wl_loads,
        supply=dict(vdd_pin='VDD',vss_pin='VSS',retained_rail_nodes=len(rails),
             proposed_local_vdd=bits[3]['vdd_local'],proposed_local_vss=bits[3]['tail_ground'],
             omitted_active_currents='omitted interface and captured-input circuitry'),
        boundaries=boundaries,unobserved_coupling_caps_fixed=fixed_caps,config=config,
        gate_criteria=dict(max_edge_error_ps=25, max_initial_tail_error_v=CONTROL_MV,
            clock_percent=[20,50,80], bit3_input_criteria=sealed['criteria'],
            other_inputs='Reference early differential and common mode within the documented replay envelope.',
            logic='Expected complementary sense rails and D through local capture, then Q confirmed.',
            reset_marker_a=TAIL_ON_A,
            interpretation='Stable logic is mandatory. Sole deviations of diagnostic headroom are separately reported.'),
        source_sha256={str(path.relative_to(ROOT)):sha256(path) for path in use_sources},
        library_sha256=sha256(library_file),
        files_sha256={p.name:sha256(p) for p in out.iterdir()}))
    print(f'Prepared {out}',flush=True)


def gate_authorization(out):
    gate_file=out/'control_gate.json'
    gate=json.loads(gate_file.read_text())
    require(gate['verdict']=='VALIDATED','Loaded control did not validate; v1 insertion blocked')
    pinned(out/'manifest.json',gate['manifest_sha256'])
    pinned(out/'control/result.json',gate['result_sha256'])
    for name,digest in gate['control_artifacts'].items():
        pinned(out/'control'/name,digest)
    return gate_file


def phase_deck(out,manifest,case):
    stage=new_directory(out/case)
    for name in ('slice.spice','stimuli.spice'):
        (stage/name).write_bytes((out/name).read_bytes())
    vectors=dict(manifest['measurements'])
    shared=manifest['sclk']['branch']
    local=shared['local']
    if case=='candidate':
        a,b=shared['upstream'],shared['local']
        original=f'R87 {a} {b} {shared["resistance_ohm"]}'
        net=stage/'slice.spice'
        original_net=net.read_text()
        require(original_net.splitlines().count(original)==1,'Original R87 card mismatch')
        net.write_text(original_net.replace(original,f'R87 driver_output {b} {shared["resistance_ohm"]}'))
        for name in ('driver_library.spice','driver_cell.spice'):
            (stage/name).write_bytes((out/name).read_bytes())
        rails=manifest['supply']
        driver=f'''* v1 local only. Input and supply meters are transparent.
.include "driver_library.spice"
.include "driver_cell.spice"
VIN_V1 {a} driver_input 0
VPWR_V1 {rails['proposed_local_vdd']} driver_power 0
XLOCAL driver_input driver_output driver_power {rails['proposed_local_vss']} phase3_sclk_local_v1
'''
        vectors.update(driver_input='v(driver_input)',driver_output='v(driver_output)',
                       driver_power='v(driver_power)',driver_a='i(vpwr_v1)',driver_input_a='i(vin_v1)')
    else:
        driver='* Original R87 wired directly in the unchanged loaded slice.\n'
    vectors.update(r87_downstream=f'v({local})')
    (stage/'local_driver.spice').write_text(driver)
    (stage/'bench.spice').write_text(render_bench(manifest['config'],vectors.values()))
    return stage,vectors


def simulate(out,case):
    obj=out/'manifest.json'
    manifest=json.loads(obj.read_text())
    require(manifest['schema']=='phase3.sclk_loaded.v1','Unexpected loaded cut manifest')
    for name,digest in manifest['source_sha256'].items():
        pinned(ROOT/name,digest)
    for name,digest in manifest['files_sha256'].items():
        pinned(out/name,digest)
    pinned(LIB/'spice/sky130_fd_sc_hd.spice',manifest['library_sha256'])
    require(model_closure(PDK)==json.loads((REFERENCE/'model_hashes.json').read_text()),'TT model closure changed')
    gate=gate_authorization(out) if case=='candidate' else None
    command=['stdbuf','-o0','-e0','ngspice','-n','-b','bench.spice']
    with (BUILD/'.eco_simulator.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        stage,vectors=phase_deck(out,manifest,case)
        write_json(stage/'attempt.json',dict(command=command,manifest_sha256=sha256(obj),
            simulator=subprocess.check_output(['ngspice','--version'],text=True,timeout=10).strip(),
            inputs_sha256={p.name:sha256(p) for p in stage.iterdir()},output_vectors=vectors,
            timeout_s=TIMEOUT,control_gate_sha256=sha256(gate) if gate else None))
        begin=time.monotonic()
        with (stage/'ngspice.log').open('xb',buffering=0) as log:
            try:
                result=subprocess.run(command,cwd=stage,stdout=log,stderr=subprocess.STDOUT,timeout=TIMEOUT,
                    preexec_fn=ngspice_limits,check=False,
                    env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'})
            except subprocess.TimeoutExpired:
                result=None
        duration=time.monotonic()-begin
    log=(stage/'ngspice.log').read_bytes()
    full=bool(result is not None and result.returncode==0 and b'No. of Data Rows' in log and
              (stage/'waveform.dat').is_file() and not
              re.search(rb'analysis aborted|timestep too small|fatal error:|transient op failed',log,re.I))
    status='COMPLETED' if full else ('TIMEOUT' if result is None else 'INCOMPLETE')
    write_json(stage/'result.json',dict(status=status,elapsed_s=duration,
       ngspice_exit_code=result.returncode if result is not None else None,
       artifacts={p.name:sha256(p) for p in stage.iterdir() if p.is_file()}))
    print(case,status,flush=True)
    return int(not full)


def read_stage(out,case):
    stage=out/case
    receipt=json.loads((stage/'result.json').read_text())
    for name,digest in receipt['artifacts'].items():
        pinned(stage/name,digest)
    attempt=json.loads((stage/'attempt.json').read_text())
    for name,digest in attempt['inputs_sha256'].items():
        pinned(stage/name,digest)
    manifest=json.loads(pinned(out/'manifest.json',attempt['manifest_sha256']).read_text())
    trace=None
    if receipt['status']=='COMPLETED':
        cols=attempt['output_vectors']
        with (stage/'waveform.dat').open() as stream:
            require(stream.readline().lower().split()==['time',*cols.values()],'Waveform column mismatch')
            data=np.loadtxt(stream,ndmin=2)
        require(data.shape[1]==len(cols)+1 and len(data)>3 and np.all(np.isfinite(data)) and
                np.all(np.diff(data[:,0])>0) and abs(data[-1,0]*1e9-(STOP-INITIAL))<1e-5,
                'Waveform incomplete or invalid')
        data[:,0]+=INITIAL*1e-9
        trace=Trace(data.tolist(),{n:i for i,n in enumerate(cols,1)})
    return manifest,receipt,trace


def subtrace(trace,names):
    # Keep common rows without copying the complete native waveform.
    result=object.__new__(Trace)
    result.rows=trace.rows
    result.times=trace.times
    result.cols=names
    return result


def bit_trace(trace,bit):
    prefix=f'b{bit}_'
    names={k.removeprefix(prefix):v for k,v in trace.cols.items() if k.startswith(prefix)}
    names['precharge']=trace.cols['precharge']
    names['vdd']=names['vdd_local']
    return subtrace(trace,names)


def compare_edges(a,b,tolerance):
    shifts={}
    for direction in ('rise','fall'):
        deltas={}
        for level in ('20','50','80'):
            x,y=(scalar(shape[f'{direction}_ns'][level]) for shape in (a,b))
            deltas[level]=(y-x)*1000 if x is not None and y is not None else None
        shifts[direction]=deltas
    result=[n for event in shifts.values() for n in event.values()]
    return dict(delta_ps=shifts,within=all(n is not None and abs(n)<=tolerance for n in result))


def reset(trace,case):
    end=case['recovery_ns']
    t=grid(case['capture_ns'],end,trace)
    current={n:outside(t,sample(trace,n,t),TAIL_ON_A) for n in
             ('tail_id','precharge_bl_id','precharge_blb_id','equalizer_id')}
    gap=None
    charging=[a for name,spans in current.items() if name!='tail_id' for a,_ in spans]
    tail_ends=[b for _,b in current['tail_id']]
    if charging and tail_ends:
        gap=(min(charging)-max(tail_ends))*1000
    overlaps={n:intersect(current['tail_id'],spans) for n,spans in current.items() if n!='tail_id'}
    prech_gate={key:one_cross(trace,key,case['capture_ns'],end,.8,False) for key in
                ('precharge_bl_gate','precharge_blb_gate','equalizer_gate')}
    recovery=trace.signal_window(case['capture_ns'],end,[ge(trace.cols[n],HIGH) for n in
             ('bl_at_sense','blb_at_sense','sense_out','sense_bar')],suffix=True)
    return dict(currents_over_marker_ns=current,overlap=overlaps,tail_current_to_precharge_ps=gap,
                local_pch80_ns=prech_gate,recovery=recovery,
                current_overlap=any(overlaps.values()),evaluated=bool(charging and all(prech_gate.values())))


def logic_window(trace,name,value,a,b):
    rule=ge(trace.cols[name],HIGH) if value==1 else le(trace.cols[name],LOW)
    return trace.signal_window(a,b,[rule],suffix=True)


def logic_val(v):
    return 1 if v>=HIGH else (0 if v<=LOW else None)


def check_bit(trace,plan,bit):
    t=bit_trace(trace,bit)
    end=plan['recovery_ns']
    c_clk=one_cross(t,'capture_clock',plan['high_ns']+1,plan['high_ns']+1.35,.5)
    case=dict(plan,capture_ns=c_clk or plan['captures_ns'][bit])
    event=assess_event(t,case)
    d=logic_val(event['captured_observation']['read_d'])
    expected_latch_d={'WRONG':1,'CORRECT':0}.get(event['decision'])
    q=logic_val(view(t,'read_q',case['capture_ns']+1.2))
    stable_d=logic_window(t,'read_d',d,case['low_ns'],case['capture_ns']) if d is not None else None
    stable_q=logic_window(t,'read_q',q,case['capture_ns']+.1,case['capture_ns']+1.2) if q is not None else None
    tail20=event['activation']['at_ns']
    ts=grid(case['low_ns'],case['capture_ns'],t)
    id_=sample(t,'tail_id',ts)
    conduction=outside(ts,id_,TAIL_ON_A)
    peak=float(max(abs(id_)))
    def limits(signal):
        times=grid(case['low_ns'],end,trace)
        sampled=sample(trace,signal,times)
        levels={str(p):dict(rises_ns=edges(times,sampled,p*.018,True).tolist(),
                            falls_ns=edges(times,sampled,p*.018,False).tolist()) for p in (20,50,80)}
        single=all(len(e['rises_ns'])==len(e['falls_ns'])==1 and
                   e['rises_ns'][0]<case['capture_ns']<e['falls_ns'][0] for e in levels.values())
        return dict(edges=levels,single_pulse=single)
    return dict(event=event,d=d,q=q,read_consistent=d is not None and q==d==expected_latch_d and bool(stable_d and stable_q and c_clk),
                d_stable=stable_d,q_stable=stable_q,capture_ns=c_clk,tail_peak_a=peak,tail_conduction=conduction,
                logical_clocks={g:limits(f'b{bit}_{g}') for g in GATES},reset=reset(t,case),
                sampled_supplies=dict(vdd_at_tail20_v=view(t,'vdd_local',tail20),vss_at_tail20_v=view(t,'tail_ground',tail20)))


def archived_bit(ref,plan,bit):
    names=dict(bl_at_sense=f'{ARRAY}.write_driver_{bit}.BL',
        blb_at_sense=f'{ARRAY}.write_driver_{bit}.BLB',sense_out=f'_{43-bit}_.A1',
        sense_bar=f'{ARRAY}.sense_amp_{bit}.SA_OUTB',sclk_sampler_bl=f'SCLK_SENSE_{bit}',
        read_d=f'_{75+bit}_.D',precharge=PCH,read_q=Q_NAMES[bit])
    # Extra direct terminal probes were archived only in column 3.
    if bit==3:
        names.update({k:k for k in (*GATES,'sense_tail','sa_sampling_out','sab_sampling_out','tail_ground')})
    alias=subtrace(ref,{k:ref.cols[v] for k,v in names.items()})
    capture=plan['captures_ns'][bit]
    return alias,dict(clock={g:gate_shape(alias,g,plan['low_ns'],plan['high_ns'])
                            for g in GATES if g in alias.cols}, d=logic_val(view(alias,'read_d',capture)),
                      q=logic_val(view(alias,'read_q',capture+1.2)))


def check_controls(trace,plan):
    begin,high=plan['low_ns'],plan['high_ns']
    timing={name:gate_shape(trace,name,begin,high) for name in ('root','precharge',*(f'wl{i}' for i in range(4)))}
    expected=plan['row']
    states=[logic_val(view(trace,f'wl{i}',high)) for i in range(4)]
    return dict(edges=timing,selected=states,wordline_correct=states==[int(i==expected) for i in range(4)] and
                all(trace.through(begin,high,[le(trace.cols[f'wl{i}'],LOW)]) for i in range(4) if i!=expected))


def read_word(values):
    return sum(x<<i for i,x in enumerate(values)) if all(x is not None for x in values) else None


def control_verdict(points):
    if len(points)!=3:
        return 'INCONCLUSIVE'
    if any(p['observed_word']!=p['archived_word'] and p['observed_word'] is not None for p in points):
        return 'NOT_REPRODUCED'
    if all(p['logical_reference'] and p['equivalent'] for p in points):
        return 'VALIDATED'
    return 'INCONCLUSIVE'


def reference_compare(trace,ref,manifest,plan):
    toler=manifest['gate_criteria']['max_edge_error_ps']
    criteria=manifest['gate_criteria']['bit3_input_criteria']
    current=check_controls(trace,plan)
    live=plan['row']
    ref_names={'root':SCLK,'precharge':PCH,f'wl{live}':WORDLINES[live]}
    controls={n:compare_edges(gate_shape(ref,r,plan['low_ns'],plan['high_ns']),current['edges'][n],toler)
              for n,r in ref_names.items()}
    bit_results=[]
    for bit in range(8):
        t=bit_trace(trace,bit)
        a,original=archived_bit(ref,plan,bit)
        measured=check_bit(trace,plan,bit)
        g=measured['event']['clock']
        clock={name:compare_edges(wave,g[name],toler) for name,wave in original['clock'].items()}
        clock_ref=original['clock'].get('sclk_tail',original['clock']['sclk_sampler_bl'])
        tail=scalar(clock_ref['rise_ns']['20'])
        comparison=None
        if tail is not None:
            comparison=input_evidence(a,t,dict(plan,capture_ns=plan['captures_ns'][bit],
                                               early_input_window_ns=[tail-.05,tail+.05]),criteria)
        same_tail=None
        if bit==3 and plan['cycle'] in (16,17):
            times=grid(plan['conditioning_ns'],plan['recovery_ns'],a,t)
            diff=sample(t,'sense_tail',times)-sample(a,'sense_tail',times)
            i=int(np.argmax(abs(diff)))
            same_tail=dict(peak_delta_v=float(diff[i]),at_ns=float(times[i]),limit_v=CONTROL_MV,
                           initial_delta_v=float(diff[0]),compatible=bool(abs(diff[i])<=CONTROL_MV))
        logical=measured['read_consistent'] and original['d']==original['q']==measured['d']
        reset_result=measured['reset']
        equal=(all(v['within'] for v in clock.values()) and comparison and comparison['eligible'] and
               (same_tail is None or same_tail['compatible']) and
               all(mark['single_pulse'] for mark in measured['logical_clocks'].values()) and
               bool(reset_result['recovery']) and reset_result['evaluated'])
        bit_results.append(dict(bit=bit,archived=original,observed=measured,timing=clock,bl_comparison=comparison,
                                tail_comparison=same_tail,logical_reference=logical,equivalent=bool(equal)))
    return dict(cycle=plan['cycle'],expected_word=plan['expected_word'],
               archived_word=read_word([b['archived']['d'] for b in bit_results]),
               observed_word=read_word([b['observed']['d'] for b in bit_results]),
               controls=current,control_edges=controls,bits=bit_results,
               logical_reference=all(k['logical_reference'] for k in bit_results) and current['wordline_correct'],
               equivalent=all(k['equivalent'] for k in bit_results) and all(v['within'] for v in controls.values()))


def rail_summary(trace,plan):
    t=grid(plan['low_ns'],plan['recovery_ns'],trace)
    current=-sample(trace,'supply_a',t)
    result=dict(aggregate_rail_peak_a=float(max(current)),
                aggregate_rail_energy_j=float(np.trapezoid(current*sample(trace,'vdd',t),t*1e-9)),
                sum_abs_tail_peak_a=float(max(sum(abs(sample(trace,f'b{b}_tail_id',t)) for b in range(8)))),
                local_vdd_min_v=[float(min(sample(trace,f'b{b}_vdd_local',t))) for b in range(8)],
                local_vss_max_v=[float(max(sample(trace,f'b{b}_tail_ground',t))) for b in range(8)])
    if 'driver_a' in trace.cols:
        driver=sample(trace,'driver_a',t)
        voltage=sample(trace,'driver_power',t)-sample(trace,'b3_tail_ground',t)
        result.update(driver_peak_a=float(max(abs(driver))),
                      driver_energy_j=float(np.trapezoid(driver*voltage,t*1e-9)))
    return result


def driver_compare(base,trial,manifest,plan):
    tol=manifest['gate_criteria']['max_edge_error_ps']
    ref_control=check_controls(base,plan)
    new_control=check_controls(trial,plan)
    controls={n:compare_edges(shape,new_control['edges'][n],tol)
              for n,shape in ref_control['edges'].items() if not n.startswith('wl') or n==f'wl{plan["row"]}'}
    results=[]
    for b in range(8):
        a,v=(check_bit(w,plan,b) for w in (base,trial))
        g={name:compare_edges(a['event']['clock'][name],v['event']['clock'][name],tol) for name in GATES}
        expected=(plan['expected_word']>>b)&1
        time_delta=v['d_stable']['first_actual_ns']-a['d_stable']['first_actual_ns'] if v['d_stable'] and a['d_stable'] else None
        initial_n=abs(a['event']['conditioning']['sense_tail']-v['event']['conditioning']['sense_tail'])
        reset_ok=v['reset']['evaluated'] and not v['reset']['current_overlap'] and bool(v['reset']['recovery'])
        results.append(dict(bit=b,control=a,candidate=v,gates=g,expected=expected,first_d_valid_delta_ns=time_delta,
                            logical_ok=v['read_consistent'] and v['d']==expected,reset_ok=reset_ok,
                            initial_tail_delta_abs_v=initial_n,
                            conditioning_ok=initial_n<=CONTROL_MV and conditioning_valid(a['event'],v['event'],CONTROL_MV),
                            no_extra_clock_crossings=all(x['single_pulse'] for x in v['logical_clocks'].values())))
    return dict(cycle=plan['cycle'],word=read_word([r['candidate']['d'] for r in results]),
               rows=new_control,shared_edges=controls,bits=results,
               current={name:rail_summary(w,plan) for name,w in [('control',base),('candidate',trial)]})


def candidate_verdict(cases):
    if len(cases)!=3:
        return 'INCONCLUSIVE'
    if any(not c['rows']['wordline_correct'] or any(
            (not b['logical_ok'] and b['candidate']['d'] is not None) or
            not b['no_extra_clock_crossings'] for b in c['bits']) for c in cases):
        return 'NOT_VIABLE'
    if all(all(b['logical_ok'] and b['reset_ok'] and b['conditioning_ok'] and
               (b['bit']==3 or all(g['within'] for g in b['gates'].values())) for b in c['bits']) and
           all(s['within'] for s in c['shared_edges'].values()) for c in cases):
        return 'VIABLE_FOR_ECO_LAYOUT_STUDY'
    return 'INCONCLUSIVE'


def analyze(out,case):
    manifest,receipt,trace=read_stage(out,case)
    stage=out/case
    report=dict(verdict='INCONCLUSIVE',stage=case,result_sha256=sha256(stage/'result.json'),
                manifest_sha256=sha256(out/'manifest.json'),electrical_qualification='NOT_CHARACTERIZED')
    if case=='control':
        report['control_artifacts']=receipt['artifacts']
    if trace is None:
        report['reason']='Incomplete or timed-out simulator evidence'
    else:
        report['samples']=len(trace.rows)
        if case=='control':
            _,_,reference=load(REFERENCE,True)
            observed=[reference_compare(trace,reference,manifest,plan) for plan in manifest['cases']]
            report.update(cases=observed,verdict=control_verdict(observed),
                          current=[rail_summary(trace,plan) for plan in manifest['cases']])
        else:
            authority=gate_authorization(out)
            pinned(authority,json.loads((stage/'attempt.json').read_text())['control_gate_sha256'])
            _,_,control=read_stage(out,'control')
            observed=[driver_compare(control,trace,manifest,plan) for plan in manifest['cases']]
            report.update(cases=observed,verdict=candidate_verdict(observed))
    write_json(out/f'{case}_gate.json',report)
    print(case,report['verdict'],flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','control','candidate','analyze-control','analyze-candidate'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    out=args.output.resolve()
    if args.action=='prepare':
        prepare(out)
    elif args.action.startswith('analyze-'):
        analyze(out,args.action.removeprefix('analyze-'))
    else:
        return simulate(out,args.action)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
