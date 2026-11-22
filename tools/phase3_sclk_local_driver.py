#!/usr/bin/env python3
"""Run a SKY130 local SCLK driver against the sealed sense-3 replay."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import time

import numpy as np

from analyze_phase3_sclk_r87_full import edges, gate_shape, scalar, view
from analyze_phase3_sense3_isolation import assess_event, conditioning_valid, one_cross
from phase3_sclk_r87 import branch
from phase3_sense3_precondition import (
    BUILD, FILES, GATES, HIGH, LOW, PDK, REFERENCE, ROOT, START, STOP, TAIL_ON_A, TIMEOUT_S,
    grid, model_closure, new_directory, ngspice_limits, outside, pinned, rail_control_comparison,
    read_receipt, read_wave, require, sample, sha256, write_json,
)
from review_phase3_bus_ss import Trace, ge, le

BASE = BUILD/'sense3_preconditioned_20261120'
MANIFEST = '77c4074ee89750e32f2fa2cd7c8ff86ea784c5fcf06f96b4ce122444f7e6cea2'
GATE_HASHES = {'control':'9b98a8ed3e1eef0651f98b8db9dbefd2520692cfb293f96c0cb961a113589716',
               'contrast':'b6655d7adebfd0d0f2a86797899ac76af70d8dce3dc8495d61e567bbf385466b'}
DRIVER = ROOT/'characterization/phase3/experiments/sclk_local_driver_v1.spice'
LIB = PDK.parents[2]/'libs.ref/sky130_fd_sc_hd'
CELL = 'sky130_fd_sc_hd__inv_4'
EXTRA = {'input':'v(driver_input)', 'mid':'v(xlocal.mid)', 'supply_current':'i(vdriver_vdd)',
         'input_current':'i(vdriver_input)', 'prech_bl_gate':'v(rc8489)', 'prech_blb_gate':'v(rc8490)',
         'equalizer_gate':'v(rc8491)',
         'prech_bl_id':'@m.x1352.msky130_fd_pr__pfet_01v8[id]',
         'prech_blb_id':'@m.x1645.msky130_fd_pr__pfet_01v8[id]',
         'equalizer_id':'@m.x374.msky130_fd_pr__pfet_01v8[id]'}


def archived():
    sealed = json.loads(pinned(BASE/'manifest.json',MANIFEST).read_text())
    for name,digest in sealed['artifacts_sha256'].items():
        pinned(BASE/name,digest)
    for name,digest in sealed['source_sha256'].items():
        pinned(ROOT/name,digest)
    for stage,expected in [('control','VALIDATED'),('contrast','CORROBORATED')]:
        g = json.loads(pinned(BASE/f'{stage}_gate.json',GATE_HASHES[stage]).read_text())
        receipt = read_receipt(BASE,stage)
        pinned(BASE/stage/'result.json',g['result_sha256'])
        require(g['verdict']==expected and g['manifest_sha256']==MANIFEST and receipt['status']=='COMPLETED',
                'Archived baseline is not qualified for this comparison')
    return sealed


def library_cell(text):
    match = re.search(rf'(?mi)^\.subckt {CELL} A VGND VNB VPB VPWR Y\n(?:[^\n]*\n)*?\.ends(?: {CELL})?\s*?\n',text)
    require(match is not None, f'Missing or incompatible {CELL}')
    return match[0]


def instrument(bench):
    require(bench.count('tran 10p 59n 0 25p\n')==1 and bench.count('\nquit\n')==1
            and len(re.findall(r'^\.save ',bench,re.M))==1, 'Unexpected sealed benchmark')
    extra = ' '.join(EXTRA.values())
    bench = re.sub(r'(?m)^\.save [^\n]+$',lambda hit:hit[0]+' '+extra,bench)
    return bench.replace('\nquit\n',f'\nwrdata driver.dat {extra}\nquit\n')


def prepare(out,circuit):
    baseline = archived()
    require(model_closure(PDK)==json.loads((REFERENCE/'model_hashes.json').read_text()), 'TT model closure drifted')
    binding = REFERENCE/'binding.spice'
    proof = branch(binding.read_text(),json.loads((REFERENCE/'probes.json').read_text()))
    require(proof['upstream']=='rc8562' and proof['local']=='rc8571' and proof['resistance_ohm']==6.46438
            and {name for name,_ in proof['consumers']}=={'X235','X521','X351'}, 'Unexpected R87 load branch')
    cell_path = LIB/'spice/sky130_fd_sc_hd.spice'
    lef = LIB/'lef/sky130_fd_sc_hd.lef'
    size = re.search(rf'(?ms)^MACRO {CELL}\n.*?SIZE ([\d.]+) BY ([\d.]+) ;',lef.read_text())
    require(size is not None,'Library LEF lacks cell dimensions')
    width,height = map(float,size.groups())
    cell = library_cell(cell_path.read_text())
    module = circuit.read_text()
    require(re.search(r'(?m)^\.subckt phase3_sclk_local_v1 IN OUT VPWR VGND$',module) is not None,
            'Experimental driver pinout differs')
    new_directory(out)
    overlay = '''* Same R87 path and stimuli. Zero-volt meters only report current.
.include "driver_library.spice"
.include "driver_cell.spice"
VDRIVER_INPUT rc8562 driver_input 0
VDRIVER_VDD VDD driver_vdd 0
XLOCAL driver_input sclk_driver driver_vdd VSS phase3_sclk_local_v1
'''
    (out/'driver_cell.spice').write_text(module)
    (out/'driver_library.spice').write_text(cell)
    (out/'clk_delta.spice').write_text(overlay)
    (out/'bench.spice').write_text(instrument((BASE/'bench.spice').read_text()))
    for name in ('slice.spice','stimuli.spice'):
        (out/name).write_bytes((BASE/name).read_bytes())
    write_json(out/'manifest.json',dict(schema='phase3.sclk_local_driver.v1', baseline_manifest_sha256=MANIFEST,
        baseline_gate_sha256=GATE_HASHES, prepared_at=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        baseline_initial_state_limit_v=baseline['criteria']['latch_conditioning_error_v'],
        conditions=baseline['conditions'], branch=proof, driver_source=str(circuit.relative_to(ROOT)),
        driver_source_sha256=sha256(circuit), runner_sha256=sha256(Path(__file__)),
        pdk=dict(root=str(PDK.parents[2].resolve()),cell=CELL, library_file=str(cell_path),library_sha256=sha256(cell_path),
                 lef_sha256=sha256(lef), inv_4_footprint_um2=width*height),
        criteria=dict(v_low=LOW,v_high=HIGH,earliest_current_marker_a=TAIL_ON_A,
            required_cycles=[15,16,17], rise_target_ps_informative=182,
            rise='Positive additional delay at each gate20 and the first interval of tail channel current.',
            reset='All local gate20 falls before earliest precharge device gate80 fall. '
                  'No intersecting tail and precharge/equalizer channel current above 1 uA after capture.',
            activity='One complete pulse, no extra 20/50/80% crossings or recrossings per signal and cycle.',
            conditioning='c15 polarity preserved through its capture; c16/c17 NTAIL and four SA/SAB probes '
                         'match the existing gate conditioning limits at [209.9,229.9] ns.',
            result='c16/c17 expected complementary latch rails and D low, sustained to reference capture.',
            loading='Candidate rising net input charge versus R87 branch charging is a proxy. '
                    'An increase blocks a viability claim pending the loaded shared network.'),
        files_sha256={p.name:sha256(p) for p in out.iterdir()}))
    print(f'Prepared {out}',flush=True)


def simulate(out):
    manifest_path=out/'manifest.json'
    manifest=json.loads(manifest_path.read_text())
    require(manifest['schema']=='phase3.sclk_local_driver.v1','Unexpected driver manifest')
    pinned(Path(__file__),manifest['runner_sha256'])
    pinned(ROOT/manifest['driver_source'],manifest['driver_source_sha256'])
    for name,h in manifest['files_sha256'].items():
        pinned(out/name,h)
    archived()
    pinned(Path(manifest['pdk']['library_file']),manifest['pdk']['library_sha256'])
    require(model_closure(PDK)==json.loads((REFERENCE/'model_hashes.json').read_text()),'TT model closure drifted')
    command=['stdbuf','-o0','-e0','ngspice','-n','-b','bench.spice']
    simulator=subprocess.check_output(['ngspice','--version'],text=True,timeout=10).strip()
    with (BUILD/'.eco_simulator.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        write_json(out/'attempt.json',dict(command=command,timeout_s=TIMEOUT_S,simulator=simulator,
                   manifest_sha256=sha256(manifest_path)))
        result=None
        begin=time.monotonic()
        with (out/'ngspice.log').open('xb',buffering=0) as log:
            try:
                result=subprocess.run(command,cwd=out,stdout=log,stderr=subprocess.STDOUT,
                                      timeout=TIMEOUT_S,preexec_fn=ngspice_limits,check=False,
                                      env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'})
            except subprocess.TimeoutExpired:
                pass
        elapsed=time.monotonic()-begin
    log=(out/'ngspice.log').read_bytes()
    completed=(result is not None and result.returncode==0 and b'No. of Data Rows' in log
               and all((out/name).is_file() for name in ('waveform.dat','currents.dat','driver.dat'))
               and not re.search(rb'analysis aborted|timestep too small|fatal error:|transient op failed',log,re.I))
    status='COMPLETED' if completed else ('TIMEOUT' if result is None else 'INCOMPLETE')
    write_json(out/'result.json',dict(status=status,elapsed_s=elapsed,
        ngspice_exit_code=result.returncode if result is not None else None,
        artifacts={p.name:sha256(p) for p in out.iterdir() if p.is_file()}))
    print(status,flush=True)
    return int(not completed)


def augmented_wave(out):
    base=read_wave(out)
    with (out/'driver.dat').open() as stream:
        require(stream.readline().lower().split()==['time',*EXTRA.values()],'Wrong driver vector inventory')
        t=np.loadtxt(stream,ndmin=2)
    require(t.shape==(len(base.rows),len(EXTRA)+1) and np.all(np.isfinite(t)) and
            np.array_equal(t[:,0]+START*1e-9,[row[0] for row in base.rows]),'Invalid driver vector samples')
    data=np.column_stack((base.rows,t[:,1:]))
    return Trace(data.tolist(),dict(base.cols,**{key:len(base.rows[0])+i for i,key in enumerate(EXTRA)}))


def pulse_inventory(trace,signal,cases,limit=STOP):
    points=np.array(trace.times)
    values=np.array([row[trace.cols[signal]] for row in trace.rows])
    onset={}
    for percentage in (20,50,80):
        rising=edges(points,values,1.8*percentage/100,True).tolist()
        falling=edges(points,values,1.8*percentage/100,False).tolist()
        onset[percentage]=dict(rise_ns=rising,fall_ns=falling)
    valid=all(len(item['rise_ns'])==len(item['fall_ns'])==len(cases) and
        all(case['low_ns']<=r<case['capture_ns']<f<min(case['high_ns']+8,limit)
        for case,r,f in zip(cases,item['rise_ns'],item['fall_ns'],strict=True)) for item in onset.values())
    return dict(edges=onset,starts_and_ends_low=bool(values[0]<=LOW and values[-1]<=LOW),
                compatible=bool(valid and values[0]<=LOW and values[-1]<=LOW))


def intersect(a,b):
    return [[max(p,q),min(r,s)] for p,r in a for q,s in b if max(p,q)<min(r,s)]


def tail_edges(trace,case):
    t=grid(case['low_ns'],case['capture_ns'],trace)
    intervals=outside(t,sample(trace,'tail_id',t),TAIL_ON_A)
    return intervals[0] if intervals else None


def reset_measure(trace,case):
    after=case['capture_ns']
    end=min(case['high_ns']+8,STOP)
    t=grid(after,end,trace)
    tail=outside(t,sample(trace,'tail_id',t),TAIL_ON_A)
    precharge={key:outside(t,sample(trace,key,t),TAIL_ON_A)
               for key in ('prech_bl_id','prech_blb_id','equalizer_id')}
    gate80={key:one_cross(trace,key,after,end,.8,False)
            for key in ('prech_bl_gate','prech_blb_gate','equalizer_gate')}
    tail20=one_cross(trace,'sclk_tail',after,end,.2,False)
    overlaps={key:intersect(tail,current) for key,current in precharge.items()}
    margin=min(gate80.values())-tail20 if tail20 is not None and all(v is not None for v in gate80.values()) else None
    recovery=trace.signal_window(after,end,[ge(trace.cols['sense_out'],HIGH),ge(trace.cols['sense_bar'],HIGH)],suffix=True)
    return dict(tail20_ns=tail20,precharge_gate80_ns=gate80,tail_over_1ua_ns=tail,
                precharge_over_1ua_ns=precharge,overlap_ns=overlaps,tail20_to_first_gate80_ns=margin,
                recovered=recovery,adequate=bool(margin is not None and margin>0. and
                                                 not any(overlaps.values()) and recovery))


def energy_and_loading(control,trial,case,resistance):
    t=grid(case['low_ns'],case['high_ns'],control,trial)
    base_current=(sample(control,'sclk_driver',t)-sample(control,'sclk_local',t))/resistance
    input_current=sample(trial,'input_current',t)
    charge=lambda current:float(np.trapezoid(current,t*1e-9))
    a=case['low_ns']
    b=min(case['high_ns']+8,STOP)
    times=grid(a,b,trial)
    rail_current=sample(trial,'supply_current',times)
    return dict(archived_branch_charge_c=charge(base_current),driver_input_charge_c=charge(input_current),
        peak_input_current_a=float(max(abs(input_current))), peak_replaced_branch_current_a=float(max(abs(base_current))),
        supply_peak_a=float(max(abs(rail_current))),
        supply_energy_j=float(np.trapezoid(rail_current*sample(trial,'vdd',times),times*1e-9)),
        comparable_load=charge(input_current)<=charge(base_current))


def measures(trace,case):
    event=assess_event(trace,case)
    captured=case['capture_ns']
    start=case['low_ns']
    d_low=trace.signal_window(start,captured,[le(trace.cols['read_d'],LOW)],suffix=True)
    event['stable_d_low']=d_low
    event['first_tail_conduction']=tail_edges(trace,case)
    event['tail20_to_precharge_command50_ns']=None
    tail20=scalar(event['clock']['sclk_tail']['fall_ns']['20'])
    precharge50=one_cross(trace,'precharge',captured,min(case['high_ns']+8,STOP),.5,False)
    if tail20 is not None and precharge50 is not None:
        event['tail20_to_precharge_command50_ns']=precharge50-tail20
    marker=event['first_tail_conduction']
    if marker:
        a=marker[0]
        bl,blb=(view(trace,k,a) for k in ('bl_at_sense','blb_at_sense'))
        event['at_first_tail_conduction']=dict(blb_minus_bl_v=blb-bl,common_mode_v=(bl+blb)/2,
            sab_minus_sa_v=view(trace,'sab_sampling_out',a)-view(trace,'sa_sampling_out',a))
        t=grid(*marker,trace)
        event['first_tail_conduction_peak_a']=float(max(abs(sample(trace,'tail_id',t))))
    return event


def compare_gates(control,trial):
    offsets={}
    for gate in GATES:
        a,b=(case['clock'][gate] for case in (control,trial))
        shifts={}
        for direction in ('rise','fall'):
            shift={}
            for percent in ('20','50','80'):
                old,new=(scalar(v[f'{direction}_ns'][percent]) for v in (a,b))
                shift[percent]=(new-old)*1000 if old is not None and new is not None else None
            shifts[f'{direction}_delta_ps']=shift
        offsets[gate]=shifts
    return offsets


def classify(pulses,predecessor,cycles):
    if any(not item['compatible'] for item in pulses.values()):
        return 'NOT_VIABLE'
    if not predecessor['decision_preserved']:
        return 'NOT_VIABLE'
    if any(e['driver']['decision']!='CORRECT' or not e['driver']['stable_d_low'] or not e['reset']['adequate']
           or not e['additional_turn_on_verified'] for e in cycles):
        return 'NOT_VIABLE'
    if any(not e['conditioned'] or not e['externals']['compatible'] or not e['loading']['comparable_load']
           for e in cycles):
        return 'INCONCLUSIVE'
    return 'VIABLE_FOR_PHYSICAL_STUDY'


def analyze(out):
    baseline=archived()
    result_path=out/'result.json'
    receipt=json.loads(result_path.read_text())
    for name,h in receipt['artifacts'].items():
        pinned(out/name,h)
    attempt=json.loads((out/'attempt.json').read_text())
    manifest=json.loads(pinned(out/'manifest.json',attempt['manifest_sha256']).read_text())
    report=dict(verdict='INCONCLUSIVE', result_sha256=sha256(result_path),
                analysis_source_sha256=sha256(Path(__file__)), baseline_gate_sha256=GATE_HASHES)
    if receipt['status']!='COMPLETED':
        write_json(out/'analysis.json',dict(report,reason='Incomplete ngspice evidence'))
        return
    for name in ('slice.spice','stimuli.spice'):
        pinned(out/name,baseline['artifacts_sha256'][name])
    control=read_wave(BASE/'control')
    ideal=read_wave(BASE/'contrast')
    trial=augmented_wave(out)
    from analyze_phase3_data3_tt import load
    _,_,reference=load(REFERENCE,True)
    capture15=one_cross(reference,'capture_clock',200.,200.3,.5)
    require(capture15 is not None,'Missing cycle-15 capture marker')
    cycle15=dict(cycle=15,low_ns=191.,high_ns=199.,capture_ns=capture15,conditioning_ns=189.9)
    previous,candidate=(assess_event(w,cycle15) for w in (control,trial))
    predecessor=dict(control=previous,driver=candidate,decision_preserved=
                     previous['decision'] in ('CORRECT','WRONG') and previous['decision']==candidate['decision'],
                     reset=reset_measure(trial,cycle15))
    if not predecessor['reset']['adequate']:
        predecessor['decision_preserved']=False
    cases=baseline['criteria']['cases']
    pulses={name:pulse_inventory(trial,name,[cycle15,*cases]) for name in ('input','sclk_driver',*GATES)}
    threshold=manifest['baseline_initial_state_limit_v']
    cycles=[]
    for case,bounds in zip(cases,baseline['criteria']['tail_envelope_windows_ns'],strict=True):
        a,b,c=(measures(w,case) for w in (control,ideal,trial))
        delta=compare_gates(a,c)
        tail_delta=c['conditioning']['sense_tail']-a['conditioning']['sense_tail']
        turn_on=all(row['rise_delta_ps']['20'] is not None and row['rise_delta_ps']['20']>0
                    for row in delta.values()) and bool(a['first_tail_conduction'] and c['first_tail_conduction']
                                           and c['first_tail_conduction'][0]>a['first_tail_conduction'][0])
        cycles.append(dict(cycle=case['cycle'],control=a,ideal=b,driver=c,gates_vs_control=delta,
            driver_input=gate_shape(trial,'input',case['low_ns'],case['high_ns']),
            driver_output=gate_shape(trial,'sclk_driver',case['low_ns'],case['high_ns']),
            additional_turn_on_verified=turn_on,reset=reset_measure(trial,case),
            conditioning_tail_delta_v=tail_delta,conditioned=conditioning_valid(a,c,threshold) and abs(tail_delta)<=threshold,
            externals=rail_control_comparison(control,trial,bounds,baseline['criteria']),
            loading=energy_and_loading(control,trial,case,manifest['branch']['resistance_ohm'])))
    report.update(verdict=classify(pulses,predecessor,cycles),cycles=cycles,pulses=pulses,cycle15=predecessor,
                  waveform_rows=len(trial.rows))
    write_json(out/'analysis.json',report)
    print(report['verdict'],flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('prepare','simulate','analyze'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--circuit', type=Path, default=DRIVER)
    args=parser.parse_args()
    out=args.output.resolve()
    if args.stage=='prepare':
        prepare(out,args.circuit.resolve())
    elif args.stage=='simulate':
        return simulate(out)
    else:
        analyze(out)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
