#!/usr/bin/env python3
"""Compare a sealed local SCLK playback with its unmodified TT control."""

import argparse
import json
from pathlib import Path

from analyze_phase3_data3_tt import PARENT, event, levels, load, native_read_samples, read, write_table
from analyze_phase3_integrated_ss import logic_word
from phase3_rc_read_path import HIGH, LOW
from review_phase3_bus_ss import ge, le
from run_phase3_data3_tt import INDEX, RETAINED, require, sha256
from run_phase3_eco_pex import new_directory
from run_phase3_integrated_ss import ADDR
from run_phase3_sclk_contrast import CYCLES, GATES, REFERENCE


def view(trace,label,when):
    return trace.value(when,trace.cols[label])


def gate_fidelity(reference,contrast,sealed):
    delay=sealed['displacement_ps']/1000
    result=[]
    for cyc,(start,end) in zip(CYCLES,sealed['intervention_intervals_ns'],strict=True):
        lo,hi=start+.025,end-.025
        for gate in GATES:
            col=contrast.cols[gate]
            error=max(abs(v[0]-view(reference,gate,t-delay))
                      for t,v in contrast.points(lo,hi,[(col,1.,0.)]))
            late=[event(contrast,gate,lo,hi,v,True)-event(reference,gate,lo,hi,v,True) for v in (.36,.9,1.44)]
            result.append(dict(cycle=cyc,gate=gate,peak_error_v=error,
                               shifts_ps=[v*1000 for v in late]))
    return result


def replicated_reads(trace,fixture):
    results=[]
    for cycle in (14,15,16,17):
        rec=fixture[cycle]
        shift=20*(cycle-INDEX[cycle])
        item=read(trace,rec,shift)
        desired=int(rec['expected'])
        fall_nominal=rec['fall_ns']-shift
        fall=event(trace,'public_clk',fall_nominal-.01,fall_nominal+.12,.9,False)
        pin_start=trace.signal_window(fall,item['probe_ns'],
              [ge(i+2,HIGH) if desired>>i&1 else le(i+2,LOW) for i in range(8)],suffix=True)
        cap=item['capture_ns']
        if cycle in CYCLES:
            rise=item['sclk_tail_ns']['20']
            sclk_fall=event(trace,'sclk_tail',fall,fall+8.,.36,False)
            sclk_fall50=event(trace,'sclk_tail',fall,fall+8.,.9,False)
            pch=event(trace,'precharge',fall,fall+8.,.36,False)
            pch50=event(trace,'precharge',fall,fall+8.,.9,False)
            # Check that both bitlines really recover after the deassertion.
            before_next=fall_nominal+9.9
            recovery=trace.signal_window(pch,before_next,
                       [ge(trace.cols['bl_at_sense'],HIGH),ge(trace.cols['blb_at_sense'],HIGH),
                        le(trace.cols['sclk_tail'],LOW),le(trace.cols['precharge'],LOW)],suffix=True)
            capture=trace.signal_window(rise,cap,
                       [*levels(trace,'sense_out','sense_bar'),le(trace.cols['read_d'],LOW)],suffix=True)
            opposing=trace.signal_window(rise,cap,[ge(trace.cols['sense_out'],HIGH),le(trace.cols['sense_bar'],LOW)])
            sense_ramp=item['sclk_tail_ns']['80']
            item.update(valid_sense_and_d_onset=capture, sclk_tail20_fall_ns=sclk_fall,
                        sclk_tail50_fall_ns=sclk_fall50,pch_low20_ns=pch,pch_fall50_ns=pch50,
                        precharge_recovery=recovery,opposite_logic_during_evaluation=opposing,
                        low_phase_recovery_at_ns=before_next,
                        correct_input_during_tail_ramp=trace.through(rise,sense_ramp,[ge(trace.cols['blb_minus_bl'],0.)]),
                        blb_minus_bl_tail20_minus50ps_v=view(trace,'blb_minus_bl',rise-.05),
                        blb_minus_bl_tail20_v=view(trace,'blb_minus_bl',rise),
                        blb_minus_bl_tail50_v=view(trace,'blb_minus_bl',item['sclk_tail_ns']['50']),
                        latch_delta_tail50_v=view(trace,'sab_minus_sa',item['sclk_tail_ns']['50']),
                        tail50_pulse_width_ns=sclk_fall50-item['sclk_tail_ns']['50'],
                        sense_and_d_margin_to_capture_ns=cap-capture['first_actual_ns'] if capture else None)
        item['stable_external_word']=pin_start
        results.append(item)
    return results


def writes(trace,fixture):
    result=[]
    for c in RETAINED:
        rec=fixture[c]
        if rec['operation']!='write':
            continue
        shift=20*(c-INDEX[c])
        rise=rec['rise_ns']-shift
        event_clk=event(trace,'public_clk',rise-.005,rise+.1,.9,True)
        we=event(trace,'we_drive',event_clk,rise+9.,LOW,True)
        din=logic_word(trace.rows,we*1e-9,[trace.cols[f'_{67+b}_.Q'] for b in range(8)])
        observed=logic_word(trace.rows,event_clk*1e-9,list(range(2,10)))
        address=logic_word(trace.rows,we*1e-9,[trace.cols[k] for k in ADDR])
        intended=f"0x{rec['expected']:02X}"
        result.append(dict(cycle=c,addr=address,payload=observed,din=din,expected=intended,we20_ns=we,
                           verified=din==observed==intended and address==f"0x{rec['row']:X}"))
    return result


def classify(old,new,controls,gate_check,reference_failed):
    # 1 mV is waveform replay fidelity, not a sensing/design limit.
    faithful=all(r['peak_error_v']<.001 for r in gate_check)
    target=new[-2:]
    pre=new[:2]
    recovered=all(r['observed_word']=='0xF0' and r['stable_external_word']
                  and r['valid_sense_and_d_onset'] and r['cell_correct_from_before_wl_to_observation']
                  and r['correct_input_during_tail_ramp'] and not r['opposite_logic_during_evaluation']
                  for r in target)
    protection=all(r['sclk_tail20_fall_ns']<r['pch_fall50_ns'] and r['precharge_recovery'] for r in target)
    same_pre=all(a['observed_word']==b['observed_word']==b['expected'] and b['stable_external_word']
                 for a,b in zip(old[:2],pre,strict=True))
    if not (faithful and reference_failed):
        return 'INCONCLUSIVE'
    if recovered and protection and same_pre and all(r['verified'] for r in controls):
        return 'SUPPORTED'
    if all(r['observed_word']=='0xF8' and r['wrong_data_sustained'] for r in target):
        return 'NOT_SUPPORTED'
    return 'INCONCLUSIVE'


def analyze(run,output):
    ref_prep,ref_sim,ref_trace=load(REFERENCE,True)
    exp_prep,exp_sim,exp_trace=load(run,True)
    require(exp_prep['contrast_waveform_sha256']==ref_sim['waveform_sha256']
            and exp_prep['candidate']==ref_prep['candidate'] and exp_prep['pex_sha256']==ref_prep['pex_sha256'],
            'SCLK contrast lacks comparable physical reference')
    require((run/'bench.spice').read_text().replace('sclk_fixture.spice','binding.spice')
            ==(REFERENCE/'bench.spice').read_text(),'Unexpected change to external bench')
    fixture=json.loads((PARENT/'fixture.json').read_text())['cycles']
    old,new=([*replicated_reads(trace,fixture)] for trace in (ref_trace,exp_trace))
    shape=gate_fidelity(ref_trace,exp_trace,exp_prep)
    write_controls=writes(exp_trace,fixture)
    storage=exp_trace.through(120.55,new[-1]['probe_ns'],levels(exp_trace,'cell_q','cell_qb'))
    failed=all(r['observed_word']=='0xF8' and r['wrong_data_sustained'] for r in old[-2:])
    verdict=classify(old,new,write_controls,shape,failed) if storage else 'INCONCLUSIVE'
    out=new_directory(output)
    status=dict(status=verdict,scope='one_fixture_only_local_SCLK_activation_displacement',
                electrical_qualification='NOT_CHARACTERIZED',
                source_waveform_sha256=ref_sim['waveform_sha256'],contrast_waveform_sha256=exp_sim['waveform_sha256'],
                contrast_native_samples=len(exp_trace.rows),original_native_samples=len(ref_trace.rows),
                analyzer_sha256=sha256(Path(__file__)),displacement_ps=exp_prep['displacement_ps'],
                valid_storage_from_c5_through_c17=storage,baseline=old,contrast=new,writes=write_controls,gate_fidelity=shape)
    (out/'contrast.json').write_text(json.dumps(status,indent=2,allow_nan=False)+'\n')
    samples=[*native_read_samples(ref_trace,old,'baseline'),*native_read_samples(exp_trace,new,'contrast')]
    write_table(out/'read_transition_samples.csv',samples)
    print(verdict,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    analyze(args.run,args.output)


if __name__=='__main__':
    main()
