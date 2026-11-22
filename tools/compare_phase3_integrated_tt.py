#!/usr/bin/env python3
"""Compare sealed integrated operation/ownership evidence, with no simulation."""

import argparse
import json
from pathlib import Path

from phase3_rc_read_path import ARRAY, trace_read_path
from review_phase3_bus_ss import EXTRA, OUTPUT_ENABLES, currents, waveform
from run_phase3_eco_pex import new_directory, pinned, write_csv
from run_phase3_integrated_ss import checked_preparation, require, sha256


def read_run(run, review_path, corner):
    prep = checked_preparation(run)
    simulation, validation, review = [json.loads(p.read_text()) for p in
                                      (run/'simulation.json',run/'validation.json',review_path)]
    require(prep['conditions']['corner']==corner and simulation['simulator_status']=='PASS'
            and simulation['preparation_sha256']==sha256(run/'preparation.json')
            and simulation['waveform_sha256']==validation['source_waveform_sha256']==review['source_waveform_sha256'],
            f'Unexpected source identity for {corner}')
    pinned(run/'ngspice.log',simulation['log_sha256'])
    trace = waveform(run,simulation,EXTRA)
    require(len(trace.rows)==validation['samples'], 'Unexpected waveform length')
    fixt = json.loads((run/'fixture.json').read_text())['cycles']
    paths = trace_read_path(trace.rows,trace.cols,fixt,False)
    return prep,simulation,validation,review,trace,paths


def table(tt,ss):
    a,b = tt[2:4]
    c,d = ss[2:4]
    for t,s,to,so in zip(a['cycles'],c['cycles'],b['cycles'],d['cycles'],strict=True):
        require(t['cycle']==s['cycle']==to['cycle']==so['cycle']
                and all(t[k]==s[k] for k in ('operation','expected_address','expected_word')), 'Unmatched comparison row')
        yield dict(cycle=t['cycle'],operation=t['operation'],address=t['expected_address'],
                   expected=t['expected_word'],tt_observed=t['observed_word'],ss_observed=s['observed_word'],
                   tt_operation=t['operation_status'],ss_operation=s['operation_status'],
                   tt_bus=to['verdict'],ss_bus=so['verdict'],tt_window=t['historical_window'],ss_window=s['historical_window'],
                   tt_taccess_ns=t['tACCESS_ns'],ss_taccess_ns=s['tACCESS_ns'],
                   tt_after_fall_ns=t['CLKfall_to_valid_ns'],ss_after_fall_ns=s['CLKfall_to_valid_ns'],
                   tt_stable_since_ns=t['data_valid_from_ns'],tt_observed_through_ns=t['data_valid_through_ns'],
                   ss_stable_since_ns=s['data_valid_from_ns'],ss_observed_through_ns=s['data_valid_through_ns'],
                   tt_readback_cycle=t.get('readback_cycle'),ss_readback_cycle=s.get('readback_cycle'),
                   tt_first_divergence=t['first_divergence'])


def samples(tt, ss):
    # Use the archived native waveforms and trace_read_path's event references.
    for corner,run in (('tt',tt),('ss',ss)):
        trace,paths = run[4:]
        bl,blb = (trace.cols[f'{ARRAY}.write_driver_3.{side}'] for side in ('BL','BLB'))
        wl = trace.cols[f'{ARRAY}.bitcell_6t_24.WL']
        for read in (r for r in paths if r['cycle'] in (16,17) and r['bit']==3):
            sclk = read['sclk20_ns']
            for offset in (-150,-50,0,50,150,250,800,3000):
                time = sclk+offset/1000
                yield dict(corner=corner,cycle=read['cycle'],event='read_sclk20',offset_ps=offset,time_ns=time,
                           bl_v=trace.value(time,bl),blb_v=trace.value(time,blb),wl_v=trace.value(time,wl),
                           sclk_v=trace.value(time,trace.cols['SCLK_SENSE_3']),
                           sense_v=trace.value(time,trace.cols['_40_.A1']),
                           sense_b_v=trace.value(time,trace.cols[f'{ARRAY}.sense_amp_3.SA_OUTB']),
                           output_q_v=trace.value(time,trace.cols['_90_.A']),
                           data_pin_v=trace.value(time,5),din_q_v=trace.value(time,trace.cols['_70_.Q']))
        for time in (113.,115.,118.,119.95):
            yield dict(corner=corner,cycle=5,event='write_sample',offset_ps=None,time_ns=time,
                       bl_v=trace.value(time,bl),blb_v=trace.value(time,blb),wl_v=trace.value(time,wl),
                       sclk_v=None,sense_v=None,sense_b_v=None,output_q_v=None,
                       data_pin_v=trace.value(time,5),din_q_v=trace.value(time,trace.cols['_70_.Q']))


def main():
    args = argparse.ArgumentParser(description=__doc__)
    for key in ('tt','tt-review','ss','ss-review','output'):
        args.add_argument('--'+key,type=Path,required=True)
    opts = args.parse_args()
    tt,ss = read_run(opts.tt,opts.tt_review,'tt'),read_run(opts.ss,opts.ss_review,'ss')
    require(tt[0]['candidate']==ss[0]['candidate'] and tt[0]['pex_sha256']==ss[0]['pex_sha256']
            and tt[0]['artifacts']['fixture.json']==ss[0]['artifacts']['fixture.json']
            and tt[0]['conditions']=={**ss[0]['conditions'],'corner':'tt'}, 'Unmatched PEX or fixture')
    output = new_directory(opts.output)
    records = {'cycles_tt_vs_ss.csv':list(table(tt,ss)), 'data3_timeline.csv':list(samples(tt,ss)),
               'read_path_tt_ss.csv':[dict(corner=cr,**p) for cr,d in (('tt',tt),('ss',ss)) for p in d[5]]}
    t = tt[4]
    on = tt[3]['cycles'][2]['host_on_ns']
    values = []
    for bit in (4,7):
        host,macro,weak = currents(t.cols,bit,False)
        for offset in (-10,0,3,10,50,200):
            at = on+offset/1000
            values.append(dict(cycle=2,bit=bit,offset_ps=offset,time_ns=at,pad_v=t.value(at,bit+2),
                               te_b_v=t.value(at,t.cols[OUTPUT_ENABLES[bit]]),host_ua=1e6*t.value(at,host),
                               dut_ua=1e6*t.value(at,macro),weak_ua=1e6*t.value(at,weak)))
    records['tt_cycle2_switch.csv'] = values
    for name,entries in records.items():
        write_csv(output/name,entries,list(entries[0]))
    manifest = dict(mode='offline_existing_waveforms',electrical_qualification='NOT_CHARACTERIZED',
                    source_sha256={str(path):sha256(path) for path in
                                    (opts.tt/'validation.json',opts.tt_review,opts.ss/'validation.json',
                                     opts.ss_review,Path(__file__))},
                    waveform_sha256={corner:run[1]['waveform_sha256'] for corner,run in (('tt',tt),('ss',ss))},
                    artifacts={name:sha256(output/name) for name in records})
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':
    main()
