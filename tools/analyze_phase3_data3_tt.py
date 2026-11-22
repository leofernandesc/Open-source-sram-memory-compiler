#!/usr/bin/env python3
"""Compare the DATA3 path in a reduced TT diagnostic and two archived runs."""

import argparse
import csv
import json
from pathlib import Path

from analyze_phase3_integrated_ss import logic_word
from phase3_rc_characterization import crossing
from phase3_rc_probe_report import read_waveform
from phase3_rc_read_path import HIGH, LOW
from review_phase3_bus_ss import Trace, ge, le
from run_phase3_data3_tt import ARRAY, BUILD, INDEX, PARENT, ROOT, STOP_NS, require, sha256
from run_phase3_eco_pex import new_directory, pinned
from run_phase3_integrated_ss import ADDR, EXTRA, checked_preparation


SS = BUILD/'integrated_ss_20261119_preflight'
READ_CYCLES = (14,15,16,17)
OLD_PROBES = {
    'wl_row3':f'{ARRAY}.bitcell_6t_24.WL',
    'bl_at_sense':f'{ARRAY}.write_driver_3.BL','blb_at_sense':f'{ARRAY}.write_driver_3.BLB',
    'sclk_sampler_bl':'SCLK_SENSE_3','sense_out':'_40_.A1','sense_bar':f'{ARRAY}.sense_amp_3.SA_OUTB',
    'capture_clock':'_62_.Y','read_d':'_78_.D','read_q':'_90_.A','write_din_q':'_70_.Q',
    'precharge':'macro_core.precharge_drive.X','evaluation':'macro_core.evaluation.X',
    'we_drive':'macro_core.write_drive.X','sclk_root':'macro_core.sense_drive.X',
    'host_enabled':'v(HOST_EN)','weak_enabled':'v(HOST_WEAK_EN)',
}
PASSIVE = ('cell_q','cell_qb','wl_at_q','wl_at_qb','bl_at_cell','blb_at_cell','sa_sampling_out',
           'sab_sampling_out','sclk_sampler_blb','sclk_tail','sense_tail','tail_ground')


def load(run, is_reduced):
    model_file = run/('preflight.json' if is_reduced else 'preparation.json')
    source = json.loads(model_file.read_text())
    sim = json.loads((run/'simulation.json').read_text())
    require(sim[('preflight_sha256' if is_reduced else 'preparation_sha256')]==sha256(model_file)
            and sim.get('status',sim.get('simulator_status'))=='PASS','Expected complete source run')
    if is_reduced:
        require(source['conditions']['stop_ns']==STOP_NS,'Unexpected reduced horizon')
        for p,h in source['artifacts'].items():
            pinned(run/p,h)
        for p,h in source['sources'].items():
            pinned(ROOT/p,h)
    else:
        checked_preparation(run)
    wave = pinned(run/'waveform.dat',sim['waveform_sha256'])
    pinned(run/'ngspice.log',sim['log_sha256'])
    names = json.loads((run/'probes.json').read_text())
    rows,cols = read_waveform(wave,sorted(set(names.values())),EXTRA,minimum_end=source['conditions']['stop_ns']*1e-9-1e-15)
    cols.update((key,cols[name]) for key,name in names.items())
    cols.update((key,cols[name]) for key,name in OLD_PROBES.items())
    cols.update(data3=5,public_clk=1)
    if is_reduced:
        require(all(n in cols for n in PASSIVE),'Incomplete passive probes')
    # Offsets of these derived signals use physical terminal polarity.
    def delta(row):
        return (row[cols['blb_at_sense']]-row[cols['bl_at_sense']],
                row[cols.get('sab_sampling_out',cols['sense_bar'])]-row[cols.get('sa_sampling_out',cols['sense_out'])],
                row[cols['sclk_tail']]-row[cols['tail_ground']] if 'sclk_tail' in cols else 0.)
    count = len(rows[0])
    cols.update(blb_minus_bl=count,sab_minus_sa=count+1,tail_vgs=count+2)
    trace = Trace([(*r,*delta(r)) for r in rows],cols)
    return source,sim,trace


def event(trace, signal, start, stop, level, rising):
    edges = crossing(trace.rows,trace.cols[signal],start*1e-9,stop*1e-9,level,'rise' if rising else 'fall')
    require(len(edges)==1,f'Expected unique {signal} crossing of {level:g} V in {start}–{stop} ns')
    return edges[0]*1e9


def snapshot(trace, now, label):
    optional = ('tail_vgs',) if 'sclk_tail' in trace.cols else ()
    probes = (*OLD_PROBES,*PASSIVE,*optional,'data3','blb_minus_bl','sab_minus_sa')
    return dict(event=label,time_ns=now,**{probe:trace.value(now,trace.cols[probe]) for probe in probes if probe in trace.cols})


def levels(trace, q, qb):
    return [le(trace.cols[q],LOW),ge(trace.cols[qb],HIGH)]


def span(trace, names, start, stop):
    values=trace.points(start,stop,[(trace.cols[name],1.,0.) for name in names])
    return {name:[min(samples),max(samples)] for name,samples
            in zip(names,zip(*(row for _,row in values)))}


def write(trace):
    rise = event(trace,'public_clk',109.99,110.1,.9,True)
    fall = event(trace,'public_clk',119.99,120.1,.9,False)
    we = event(trace,'we_drive',rise,fall,LOW,True)
    wl_signal = 'wl_at_q' if 'wl_at_q' in trace.cols else 'wl_row3'
    wl = event(trace,wl_signal,rise,fall,HIGH,True)
    marks = [('host_payload_stable',107.2),('clock_rise50',rise),('WE20',we),('WL80',wl),
             ('clock_fall50',fall),('post_write',121.),('idle_after_write',125.)]
    if 'cell_q' in trace.cols:
        for key,signal,direction in (('cell_Q_fall50','cell_q','fall'),('cell_QB_rise50','cell_qb','rise')):
            edges=crossing(trace.rows,trace.cols[signal],we*1e-9,fall*1e-9,.9,direction)
            if len(edges)==1:
                marks.append((key,edges[0]*1e9))
    marks.sort(key=lambda item:item[1])
    states = [snapshot(trace,t,key) for key,t in marks]
    return dict(origin_cycle=5,word_at_rise=logic_word(trace.rows,rise*1e-9,list(range(2,10))),
                captured_address=logic_word(trace.rows,((we+wl)/2)*1e-9,[trace.cols[key] for key in ADDR]),
                we20_ns=we,wl80_ns=wl,programmed_cell_zero=trace.through(fall+.5,125.,levels(trace,'cell_q','cell_qb'))
                if 'cell_q' in trace.cols else None,observations=states)


def read(trace, rec, shift):
    start,end = rec['rise_ns']-shift,rec['fall_ns']-shift
    probe = rec['calibration']['weak_on_ns']-shift
    rise = event(trace,'public_clk',start-.01,start+.1,.9,True)
    fall = event(trace,'public_clk',end-.01,end+.1,.9,False)
    capture = event(trace,'capture_clock',fall,probe,.9,True)
    result = dict(origin_cycle=rec['cycle'],expected=f"0x{rec['expected']:02X}",
                  captured_address=logic_word(trace.rows,(rise+5.)*1e-9,[trace.cols[k] for k in ADDR]),
                  observed_word=logic_word(trace.rows,probe*1e-9,list(range(2,10))),
                  capture_ns=capture,probe_ns=probe)
    if rec['cycle'] not in (16,17):
        result['observations'] = [snapshot(trace,rise-.1,'before_precharge_release'),
                                  snapshot(trace,capture,'capture50'),snapshot(trace,probe,'external_observation')]
        return result
    wl_source = 'wl_at_q' if 'wl_at_q' in trace.cols else 'wl_row3'
    wl = {label:event(trace,wl_source,rise,fall,level,True) for label,level in (('20',LOW),('50',.9),('80',HIGH))}
    sclk = {label:event(trace,'sclk_sampler_bl',rise,fall,level,True) for label,level in (('20',LOW),('50',.9),('80',HIGH))}
    tail = ({label:event(trace,'sclk_tail',rise,fall,level,True) for label,level in (('20',LOW),('50',.9),('80',HIGH))}
            if 'sclk_tail' in trace.cols else {})
    marks = [('precharge_end_observation',rise-.1),('clock_rise50',rise),('WL20',wl['20']),('WL50',wl['50']),
             ('WL80',wl['80']),('sampling_gate20_minus50ps',sclk['20']-.05),
             ('sampling_gate20',sclk['20']),('sampling_gate50',sclk['50']),
             ('sampling_gate80',sclk['80']),('capture50',capture),('external_observation',probe)]
    marks.extend((f'tail_gate{k}',t) for k,t in tail.items())
    positive = trace.regions(wl['20'],capture,[ge(trace.cols['blb_minus_bl'],0.)])
    settled_wrong = trace.signal_window(sclk['20'],capture,
                                        [ge(trace.cols['sense_out'],HIGH),le(trace.cols['sense_bar'],LOW)],suffix=True)
    settled_right = trace.signal_window(sclk['20'],capture,levels(trace,'sense_out','sense_bar'),suffix=True)
    if positive and positive[-1][1]==capture:
        marks.append(('last_BL_polarity_change',positive[-1][0]))
    if settled_wrong:
        marks.append(('sense_wrong_first_sample',settled_wrong['first_actual_ns']))
    if settled_right:
        marks.append(('sense_correct_first_sample',settled_right['first_actual_ns']))
    if 'cell_q' in trace.cols:
        result['cell_voltage_ranges_v']=span(trace,('cell_q','cell_qb'),rise-.1,probe)
    reversals=crossing(trace.rows,trace.cols['sab_minus_sa'],sclk['50']*1e-9,capture*1e-9,0.,'fall')
    if settled_wrong and len(reversals)==1:
        marks.append(('latch_differential_reverses',reversals[0]*1e9))
    result.update(wl_ns=wl,sclk_sampling_ns=sclk,sclk_tail_ns=tail,
                  continuous_correct_bl_polarity_from_ns=positive[-1][0] if positive and positive[-1][1]==capture else None,
                  sense_correct_suffix=settled_right,sense_wrong_suffix=settled_wrong,
                  wrong_data_sustained=trace.through(fall+.2,probe,[ge(trace.cols['data3'],HIGH)]),
                  cell_correct_from_before_wl_to_observation=trace.through(
                      rise-.1,probe,levels(trace,'cell_q','cell_qb')) if 'cell_q' in trace.cols else None,
                  observations=[snapshot(trace,t,key) for key,t in sorted(marks,key=lambda item:item[1])])
    return result


def native_read_samples(trace, checks, source):
    keys=('wl_at_q','wl_row3','sclk_sampler_bl','sclk_tail','tail_vgs','cell_q','cell_qb',
          'blb_minus_bl','sab_minus_sa','sense_out','sense_bar','precharge','read_d','data3')
    for check in checks[-2:]:
        anchor=check['sclk_sampling_ns']['20']
        cols={key:trace.cols[key] for key in keys if key in trace.cols}
        for time,row in zip(trace.times,trace.rows):
            if anchor-.4<=time<=anchor+1.4:
                yield dict(source=source,origin_cycle=check['origin_cycle'],time_ns=time,
                           since_sclk20_ps=1000*(time-anchor),**{key:row[col] for key,col in cols.items()})


def write_table(path, rows):
    with path.open('x',newline='') as stream:
        fields=list(dict.fromkeys(k for row in rows for k in row))
        writer=csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,help='Include the reduced diagnostic when complete')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    records=json.loads((PARENT/'fixture.json').read_text())['cycles']
    suites = [('archived_tt',PARENT,False),('archived_ss',SS,False)]
    if args.run:
        suites.append(('reduced_tt',args.run,True))
    result,rows,native={},[],[]
    for name,path,reduced in suites:
        source,sim,trace=load(path,reduced)
        checks = [write(trace)]
        checks.extend(read(trace,records[i],20*(i-INDEX[i]) if reduced else 0) for i in READ_CYCLES)
        item=dict(candidate=source['candidate'],conditions=source['conditions'],waveform_sha256=sim['waveform_sha256'],
                  samples=len(trace.rows),checks=checks)
        if reduced:
            c16,c17=checks[-2:]
            item['reproduced_same_readback_failure'] = all(c['observed_word']=='0xF8' for c in (c16,c17))
            item['cell_correct_through_all_reduced_observations']=trace.through(
                120.55,c17['probe_ns'],levels(trace,'cell_q','cell_qb'))
        result[name]=item
        native.extend(native_read_samples(trace,checks,name))
        for check in checks:
            rows.extend(dict(source=name,origin_cycle=check['origin_cycle'],**s) for s in check['observations'])
    directory=new_directory(args.output)
    write_table(directory/'events.csv',rows)
    write_table(directory/'read_transition_samples.csv',native)
    status=dict(scope='diagnostic',overall_electrical='NOT_CHARACTERIZED',
                analyzer_sha256=sha256(Path(__file__)),cases=result)
    (directory/'diagnosis.json').write_text(json.dumps(status,indent=2,allow_nan=False)+'\n')
    print(directory,flush=True)


if __name__=='__main__':
    main()
