#!/usr/bin/env python3
"""Seal a PEX sense-3 cut and run at most one control and one gated contrast."""

import argparse
from collections import defaultdict
import csv
import fcntl
import heapq
import json
import os
from pathlib import Path
import re
import subprocess
import time

import numpy as np

from analyze_phase3_data3_tt import load
from diagnose_phase3_sclk_startup import write_json
from phase3_rc_probe import rc_node_map
from phase3_sclk_r87 import branch
from run_phase3_data3_tt import BUILD, PARENT, PDK, PEX, ROOT, checked_preparation, model_closure
from run_phase3_eco_pex import new_directory, ngspice_limits, pinned, sha256
from run_phase3_sclk_contrast import GATES, REFERENCE


START, STOP = 208., 247.
SHIFT_PS, EDGE_PS, REPLAY_V = 182, 25, .0001
SHIFT_WINDOWS = ((213.85,216.35),(233.85,236.35))
TIMEOUT_S = 300
MOS = dict(latch=('X102','X234','X235','X351','X521','X1267','X1560'),
           mux=('X173','X428','X570','X589','X701','X795','X920','X1017','X1140','X1191','X1315','X1509'),
           d_load=('X1226','X1745'), precharge=('X374','X1352','X1645'),
           write_driver=('X323','X1619','X442','X1081','X1145','X611','X149','X1343','X751','X1632','X706','X1281'))
BOUNDARY = {'rc8202':'bl_at_cell','rc8216':'blb_at_cell','rc8510':'precharge','rc8657':'we_drive',
            'rc6111':'write_din_q','rc6243':'_84_.Q','rc6380':'read_q','rc8562':'sclk_root',
            'rc5874':'tail_ground','VDD':'vdd'}
OBSERVE = {'bl_at_sense':'rc8210','blb_at_sense':'rc8222','bl_at_cell':'rc8202','blb_at_cell':'rc8216',
           'sa_sampling_out':'rc5993','sab_sampling_out':'rc8025','sense_out':'rc5991','sense_bar':'rc8026',
           'read_d':'rc6372','sclk_sampler_bl':'rc8584','sclk_sampler_blb':'rc8586','sclk_tail':'rc8585',
           'tail_ground':'rc5874','sense_tail':'rc7187','precharge':'rc8510','sclk_root':'rc8562',
           'sclk_local':'rc8571','sclk_driver':'sclk_driver','vdd':'VDD',
           'sa_center':'rc5990','sab_center':'rc8022'}
MOS_CURRENTS = ('@m.x235.msky130_fd_pr__pfet_01v8[id]', '@m.x521.msky130_fd_pr__pfet_01v8[id]',
                '@m.x351.msky130_fd_pr__nfet_01v8[id]')


def require(condition, message):
    if not condition:
        raise ValueError(message)


class ResistanceGraph:
    def __init__(self, cards):
        self.links = defaultdict(list)
        for key,(a,b,*values) in cards.items():
            if key.startswith('R'):
                r = float(values[0])
                require(r>=0.,f'Invalid resistance {key}')
                self.links[a].append((b,r))
                self.links[b].append((a,r))
        self.groups = {}

    def group(self,node):
        if node in self.groups:
            return self.groups[node]
        seen,todo = set(),[node]
        while todo:
            here = todo.pop()
            if here not in seen:
                seen.add(here)
                todo.extend(n for n,_ in self.links[here] if n not in seen)
        seen = frozenset(seen)
        self.groups.update((n,seen) for n in seen)
        return seen

    def shortest(self,start,targets):
        todo,seen = [(0.,start,(start,))],set()
        while todo:
            distance,node,path = heapq.heappop(todo)
            if node in seen:
                continue
            if node in targets:
                return distance,path
            seen.add(node)
            for neighbor,resistance in self.links[node]:
                if neighbor not in seen:
                    heapq.heappush(todo,(distance+resistance,neighbor,(*path,neighbor)))
        raise ValueError(f'Resistor path from {start} to {targets} missing')


def cut(binding,nodes,reference_probes):
    originals = {line.split()[0]:line for line in binding.splitlines() if re.match(r'^[XRC]\d+ ',line)}
    cards = {name:line.split()[1:] for name,line in originals.items()}
    resist = ResistanceGraph(cards)
    rtl = {name for family in MOS.values() for name in family}
    local_branch = branch(binding,reference_probes)
    require({name for name,_ in local_branch['consumers']}=={'X235','X521','X351'}, 'Wrong SCLK branch')
    sclk = resist.group('rc8562')
    local = {'rc8562','rc8571',*(reference_probes[name] for name in GATES)}
    pins = {pin for name in rtl for pin in cards[name][:4]}
    signal_nodes = set(local)
    rail_paths = {}
    rail_nodes = {'VDD','VSS'}
    for pin in sorted(pins):
        if rail := resist.group(pin)&{'VDD','VSS'}:
            require(len(rail)==1, f'Ambiguous rail at {pin}')
            d,path = resist.shortest(pin,rail)
            rail_nodes.update(path)
            rail_paths[pin] = dict(total_ohm=d, nodes=path)
        elif pin not in sclk:
            signal_nodes.update(resist.group(pin))
    require(set(BOUNDARY)<=signal_nodes|rail_nodes, 'Port missing from selected networks')
    # Include the capacitance of the active slice, its explicit supply pins,
    # and the physically retained rail paths. External capacitor plates keep
    # their original value and node name, with a documented termination.
    kept_nodes = signal_nodes|rail_nodes
    core_clock_pairs = {'R60','R68','R76','R87'}
    keep = set(rtl)
    attached = set()
    for name,card in cards.items():
        a,b = card[:2]
        if name.startswith('R') and {a,b}<=kept_nodes:
            if {a,b}&local:
                require(name in core_clock_pairs, 'Unexpected crosslink on SCLK cut')
            keep.add(name)
        if name.startswith('C') and ({a,b}&(signal_nodes|pins) or {a,b}<=rail_nodes) and card[2]!='0':
            keep.add(name)
            attached.update({a,b}-kept_nodes)
    require(core_clock_pairs<=keep, 'Incomplete four-resistor SCLK branch')
    by_ref_node = {n:key for key,n in reference_probes.items()}
    ports = {}
    for n,s in BOUNDARY.items():
        trace_node = 'rc8605' if n=='rc8562' else n
        ports[n] = dict(trace=s,archived_node=trace_node,
                        mode='shared_clock_proxy' if n=='rc8562' else 'recorded_boundary')
    for n in sorted(attached):
        group = resist.group(n)
        other = group&by_ref_node.keys()
        if rail := group & {'VSS','VDD'}:
            ports[n] = dict(mode='ideal_rail_termination',rail=sorted(rail)[0])
        elif other:
            d,path = resist.shortest(n,other)
            r = path[-1]
            ports[n] = dict(trace=by_ref_node[r],archived_node=r,route_ohm=d,
                            mode='exact_recorded_aggressor' if n==r else 'same_resistive_net_proxy')
        else:
            ports[n] = dict(mode='constant_unobserved_aggressor',rail='VSS')
    for n,p in ports.items():
        p['pex_node_name'] = nodes.get(n,n)
    outside = {name for name,card in cards.items() if name.startswith('X') and name not in rtl
               and signal_nodes&set(card[:4])}
    removed = [(name,'cut_mos_on_retained_signal' if name in outside else
                ('zero_capacitance' if name.startswith('C') and cards[name][2]=='0' else
                 'outside_retained_network'), originals[name]) for name in originals if name not in keep]
    attached_caps = {name:dict(terminal=next(iter(set(cards[name][:2])&attached)),value=cards[name][2])
                     for name in keep if name.startswith('C') and set(cards[name][:2])&attached}
    meters = {name:line for name,line in originals.items() if name in keep}
    for key in OBSERVE.values():
        require(key in kept_nodes or key=='sclk_driver', f'Unconnected probe {key}')
    require(not ({OBSERVE[k] for k in ('bl_at_sense','blb_at_sense','sa_sampling_out','sab_sampling_out',
                                      'sense_out','sense_bar','sense_tail','read_d')}&set(ports)),
            'Fixture would pin a sampler, latch or generated output')
    manifest = dict(preserved_mos_by_role=MOS,kept_cards=meters,ports=ports,rail_resistor_paths=rail_paths,
                    r87=local_branch,cap_boundary_terminations=attached_caps,cut_connected_mos=sorted(outside),
                    observations=OBSERVE,finite_bl_resistor_paths={n:resist.shortest(n,{src})
                    for n,src in [('rc8210','rc8202'),('rc8222','rc8216')]},removed_count=len(removed),
                    limits=['The remote two BL boundary sources do not recreate the active impedance of the omitted 6T array.',
                            'External rail load currents and unobserved aggressor slew are not replayed.',
                            'rc8562 lacks a historical direct probe, so its shared source is replayed from rc8605.',
                            'Q feedback is external, but SA, SAB and D all emerge from retained MOS.'])
    return manifest,removed


def compress(t,v,tolerance=REPLAY_V):
    selected = {0,len(t)-1}
    todo = [(0,len(t)-1)]
    while todo:
        a,b = todo.pop()
        if b<=a+1:
            continue
        error = abs(v[a:b+1]-(v[a]+(v[b]-v[a])/(t[b]-t[a])*(t[a:b+1]-t[a])))
        i = int(np.argmax(error))
        if error[i]>tolerance:
            k = a+i
            selected.add(k)
            todo.extend(((a,k),(k,b)))
    idx = sorted(selected)
    require(np.max(abs(np.interp(t,t[idx],v[idx])-v))<=tolerance+1e-12, 'PWL compression bound violated')
    return t[idx],v[idx]


def pwl(name,a,b,t,v):
    parts = [f'{x:.10g}n {y:.12g}' for x,y in zip(t,v,strict=True)]
    lines = [' '.join(parts[i:i+6]) for i in range(0,len(parts),6)]
    return f'{name} {a} {b} PWL({lines[0]}\n'+''.join(f'+ {line}\n' for line in lines[1:])+'+ )\n'


def archived_points(trace,name):
    points = np.asarray([(t,v[0]) for t,v in trace.points(START,STOP,[(trace.cols[name],1.,0.)])])
    return points[:,0],points[:,1]


def prepare(output):
    parent = checked_preparation(PARENT)
    ref,sim,trace = load(REFERENCE,True)
    trace.cols['vdd']=10
    require(ref['pex_sha256']==parent['pex_sha256'], 'PEX reference differs from physical receipt')
    pex = PEX/'extracted_rc.spice'
    pinned(pex,ref['pex_sha256'])
    binding = (REFERENCE/'binding.spice').read_text()
    original_probes = json.loads((REFERENCE/'probes.json').read_text())
    nodes = {v:k for k,v in rc_node_map(pex.read_text()).items()}
    manifest,removed = cut(binding,nodes,original_probes)
    model_file = REFERENCE/'model_hashes.json'
    model_hashes = json.loads(model_file.read_text())
    require(model_closure(PDK)==model_hashes, 'Model closure has changed')
    cfg = [line for line in (REFERENCE/'bench.spice').read_text().splitlines()
           if line.startswith(('.lib ','.temp ','.options '))]
    require(any(l.endswith(' tt') for l in cfg) and '.temp 27' in cfg, 'Expected original TT at 27 C')
    stimuli = ['VSS_REF VSS 0 0\n']
    archive = {}
    for index,(node,info) in enumerate(manifest['ports'].items()):
        if name := info.get('trace'):
            if name not in archive:
                archive[name] = archived_points(trace,name)
            t,v = archive[name]
            knots,signal = compress(t,v)
            stimuli.append(pwl(f'VPORT{index}',node,'VSS',knots-START,signal))
            info.update(knots=len(knots),max_replay_error_v=float(np.max(abs(v-np.interp(t,knots,signal)))))
        else:
            stimuli.append(f'VPORT{index} {node} {info["rail"]} 0\n')
    circuit = list(manifest['kept_cards'].values())
    circuit[circuit.index(manifest['kept_cards']['R87'])] = 'R87 sclk_driver rc8571 6.46438'
    vars = ' '.join(f'v({node})' for node in OBSERVE.values())
    devices = ' '.join(MOS_CURRENTS)
    deck = '\n'.join(['* Isolated PEX sense 3 in TT',*cfg,'.include "slice.spice"','.include "stimuli.spice"',
                      '.include "clk_delta.spice"',f'.save {vars} {devices}', '.control','set num_threads=1',
                      'set noaskquit','set wr_singlescale','set wr_vecnames',f'tran 10p {STOP-START:g}n 0 25p',
                      f'wrdata waveform.dat {vars}',f'wrdata currents.dat {devices}', 'quit','.endc','.end',''])
    out = new_directory(output)
    for name,text in [('slice.spice','\n'.join(circuit)+'\n'),('stimuli.spice',''.join(stimuli)),('bench.spice',deck)]:
        (out/name).write_text(text)
    with (out/'removed.csv').open('x',newline='') as stream:
        w = csv.writer(stream)
        w.writerow(('element','reason','original_card'))
        w.writerows(removed)
    from analyze_phase3_sense3_isolation import reference_criteria
    write_json(out/'manifest.json',dict(manifest,control_status='NOT_RUN',source_sha256={
        str(p.relative_to(ROOT)):sha256(p) for p in (pex,model_file,REFERENCE/'binding.spice',REFERENCE/'waveform.dat',
           REFERENCE/'preflight.json',REFERENCE/'simulation.json',Path(__file__),
           Path(__file__).with_name('analyze_phase3_sense3_isolation.py'))},
        reference_waveform_sha256=sim['waveform_sha256'],model_count=len(model_hashes),
        conditions=dict(corner='tt',temperature_c=27,nominal_vdd_v=1.8,start_reference_ns=START,stop_reference_ns=STOP,
                        horizon_ns=STOP-START,max_step_ps=25,timeout_s=TIMEOUT_S),
        replay_limit_v=REPLAY_V,criteria=reference_criteria(trace),
        sclk_displacement=dict(programmed_ps=SHIFT_PS,edge_tolerance_ps=EDGE_PS,windows_ns=SHIFT_WINDOWS,
           unchanged_original_resistor='R87 rc8562 rc8571 6.46438',
           fixture_resistor='R87 sclk_driver rc8571 6.46438',
           control_source='VSHIFT sclk_driver rc8562 0',
           note='Zero series source is transparent. Clock aggressor at rc8562 is fixed for both cases.'),
        artifacts_sha256={p.name:sha256(p) for p in out.iterdir()}))
    print('Prepared',out,flush=True)


def delay_source(trace):
    name = 'sclk_root'
    dt = SHIFT_PS/1000
    t,v = archived_points(trace,name)
    tr,vr = compress(t,v)
    lines = [(0.,0.)]
    for start,end in SHIFT_WINDOWS:
        grid = np.union1d(tr[(tr>start)&(tr<end)],tr[(tr+dt>start)&(tr+dt<end)]+dt)
        grid = np.unique(np.r_[start,start+.025,grid,end-.025,end])
        mask = np.clip(np.minimum(grid-start,end-grid)/.025,0.,1.)
        shift = mask*(np.interp(grid-dt,tr,vr)-np.interp(grid,tr,vr))
        lines.extend(zip(grid-START,shift))
    t,v = np.asarray(lines).T
    return pwl('VSHIFT','sclk_driver','rc8562',t,v)


def authorized_gate(gate, result, gate_path):
    require(gate['verdict']=='REPRODUCED' and gate['control_result_sha256']==sha256(result),
            f'Contrast blocked by control gate {gate_path}')


def run(root,stage):
    mf = root/'manifest.json'
    manifest = json.loads(mf.read_text())
    for file,digest in manifest['source_sha256'].items():
        pinned(ROOT/file,digest)
    for file,digest in manifest['artifacts_sha256'].items():
        pinned(root/file,digest)
    require(model_closure(PDK)==json.loads((REFERENCE/'model_hashes.json').read_text()), 'Model closure has drifted')
    gate = root/'control_gate.json'
    if stage=='contrast':
        authorized_gate(json.loads(gate.read_text()),root/'control/result.json',gate)
        _,_,ref = load(REFERENCE,True)
        shift = delay_source(ref)
    else:
        shift = 'VSHIFT sclk_driver rc8562 0\n'
    out = new_directory(root/stage)
    for key in ('slice.spice','stimuli.spice','bench.spice'):
        (out/key).write_bytes((root/key).read_bytes())
    (out/'clk_delta.spice').write_text(shift)
    cmd = ['stdbuf','-o0','-e0','ngspice','-n','-b','bench.spice']
    version = subprocess.check_output(['ngspice','--version'],text=True,timeout=10)
    write_json(out/'attempt.json',dict(command=cmd,simulator=version.strip(),timeout_s=TIMEOUT_S,
                   manifest_sha256=sha256(mf),inputs_sha256={p.name:sha256(p) for p in out.iterdir()},
                   control_gate_sha256=sha256(gate) if stage=='contrast' else None))
    begin=time.monotonic()
    status,result='INCONCLUSIVE',None
    with (BUILD/'.eco_simulator.lock').open('a') as lock, (out/'ngspice.log').open('xb',buffering=0) as log:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            result = subprocess.run(cmd,cwd=out,stdout=log,stderr=subprocess.STDOUT,
                        env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'},
                        preexec_fn=ngspice_limits,timeout=TIMEOUT_S,check=False)
        except subprocess.TimeoutExpired:
            status='TIMEOUT'
    waveform = out/'waveform.dat'
    text = (out/'ngspice.log').read_bytes()
    if (result and result.returncode==0 and b'No. of Data Rows' in text and waveform.is_file()
            and not re.search(rb'analysis aborted|timestep too small|fatal error:|transient op failed',text,re.I)):
        status='COMPLETED'
    write_json(out/'result.json',dict(status=status,elapsed_s=time.monotonic()-begin,
        ngspice_exit_code=result.returncode if result else None,
        artifacts={p.name:sha256(p) for p in out.iterdir() if p.is_file()}))
    print(stage,status,flush=True)
    return int(status!='COMPLETED')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','control','contrast'))
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.action=='prepare':
        prepare(args.output.resolve())
        return 0
    return run(args.output.resolve(),args.action)


if __name__=='__main__':
    raise SystemExit(main())
