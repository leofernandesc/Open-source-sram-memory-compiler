#!/usr/bin/env python3
"""Separate full R87 waveform fidelity, readback and causal interpretation."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_phase3_data3_tt import OLD_PROBES, levels, load, read, span, write, write_table
from analyze_phase3_integrated_ss import logic_word
from analyze_phase3_sclk_contrast import writes
from diagnose_phase3_sclk_startup import SOURCE, source_points, write_json
from phase3_rc_probe_report import read_waveform
from phase3_rc_read_path import HIGH, LOW, OUTPUT_ENABLES
from review_phase3_bus_ss import Trace, ge, le
from run_phase3_data3_tt import ARRAY, INDEX, PARENT
from run_phase3_eco_pex import new_directory, pinned
from run_phase3_integrated_ss import ADDR, EXTRA, LIMIT_A
from run_phase3_sclk_contrast import CYCLES, GATES, REFERENCE
from run_phase3_sclk_r87_full import FIDELITY, FULL_NS, WINDOWS, require, sha256


CONTROLS = ('public_clk','vdd','v(CSb)','v(OEb)','v(WEb)','host_enabled','weak_enabled',
            'precharge','evaluation','macro_core.release_phase.X','we_drive','sclk_root','capture_clock',
            'wl_row3','wl_at_q','wl_at_qb',*(f'{ARRAY}.wl_driver_{n}.WL' for n in range(3)),
            *OUTPUT_ENABLES,*(f'SCLK_SENSE_{n}' for n in range(8) if n!=3))
OTHER_READ = tuple(
    [f'{ARRAY}.write_driver_{n}.{side}' for n in range(8) if n!=3 for side in ('BL','BLB')]
    +[f'{ARRAY}.sense_amp_{n}.SA_OUTB' for n in range(8) if n!=3])
PREFIX_ONLY = (*ADDR,*GATES,'sense_out','sense_bar','read_d','read_q',
               'bl_at_sense','blb_at_sense',*(f'data{n}' for n in range(8)))


def view(trace,name,when):
    return trace.value(when,trace.cols[name])


def edges(time, voltage, threshold, rising):
    if not rising:
        voltage,threshold = -voltage,-threshold
    i = np.flatnonzero((voltage[:-1]<threshold)&(voltage[1:]>=threshold))
    return time[i]+(time[i+1]-time[i])*(threshold-voltage[i])/(voltage[i+1]-voltage[i])


def edge_table(trace, gate, start, stop, percentages, rising):
    points = trace.points(start,stop,[(trace.cols[gate],1.,0.)])
    t,v = np.asarray([(t,values[0]) for t,values in points]).T
    return {str(p):edges(t,v,p*.018,rising).tolist() for p in percentages}


def scalar(edge_list):
    return edge_list[0] if len(edge_list)==1 else None


def gate_shape(trace, name, start, end):
    rise = edge_table(trace,name,start,end,(10,20,50,80),True)
    fall = edge_table(trace,name,end,end+8,(80,50,20,10),False)
    r20,r50,r80 = (scalar(rise[str(p)]) for p in (20,50,80))
    f20,f50,f80 = (scalar(fall[str(p)]) for p in (20,50,80))
    lows = span(trace,(name,),start-.25,start)[name]
    highs = span(trace,(name,),end-.35,end)[name]
    return dict(rise_ns=rise,fall_ns=fall,
                slew20_80_ps=(r80-r20)*1000 if r80 is not None and r20 is not None else None,
                fall_slew80_20_ps=(f20-f80)*1000 if f20 is not None and f80 is not None else None,
                width50_ps=(f50-r50)*1000 if r50 is not None and f50 is not None else None,
                low_plateau_v=lows,high_plateau_v=highs,
                full_active_range_v=span(trace,(name,),r80,f80)[name] if r80 is not None and f80 is not None and f80>r80 else None)


def delta(a,b,factor=1.):
    return (b-a)*factor if a is not None and b is not None else None


def interpret_gate(old,new,tolerance):
    levels = [str(p) for p in tolerance['cross_percent']]
    rise = {p:delta(scalar(old['rise_ns'][p]),scalar(new['rise_ns'][p]),1000.) for p in levels}
    fall = {p:delta(scalar(old['fall_ns'][p]),scalar(new['fall_ns'][p]),1000.) for p in levels}
    shape = delta(old['slew20_80_ps'],new['slew20_80_ps'])
    width = delta(old['width50_ps'],new['width50_ps'])
    faithful = (all(d is not None and abs(d-tolerance['displacement_ps'])<=tolerance['each_rise_ps'] for d in rise.values())
                and all(d is not None and abs(d)<=tolerance['unchanged_fall_ps'] for d in fall.values())
                and shape is not None and abs(shape)<=tolerance['slew_difference_ps']
                and width is not None and abs(width+tolerance['displacement_ps'])<=tolerance['width_difference_ps']
                and new['low_plateau_v'][1]<=LOW and new['high_plateau_v'][0]>=HIGH)
    return dict(rise_delay_ps=rise,fall_delay_ps=fall,slew_difference_ps=shape,width_difference_ps=width,
                rise10_delay_ps=delta(scalar(old['rise_ns']['10']),scalar(new['rise_ns']['10']),1000.),
                fidelity_verified=faithful)


def logic_transitions(time,voltage,logic):
    """Date transitions that actually travel from one valid level to the other."""
    known = np.flatnonzero(logic>=0)
    result = []
    for a,b in zip(known[:-1],known[1:]):
        if logic[a]!=logic[b]:
            rising = logic[b]==1
            middle = edges(time[a:b+1],voltage[a:b+1],.9,rising)
            result.append((rising,float(middle[-1])))
    return result


def compare_signals(reference,contrast,signals,start,stop,tolerance_ps):
    results = []
    ta = np.asarray(reference.times)
    tb = np.asarray(contrast.times)
    t = np.union1d(np.r_[start,ta[(ta>start)&(ta<stop)]],np.r_[tb[(tb>start)&(tb<stop)],stop])
    for name in signals:
        va = [row[reference.cols[name]] for row in reference.rows]
        vb = [row[contrast.cols[name]] for row in contrast.rows]
        a,b = np.interp(t,ta,va),np.interp(t,tb,vb)
        # Find edges on each actual waveform. The common grid only measures differences.
        shifts, counts = [],[]
        for value in (LOW,.9,HIGH):
            for rising in (True,False):
                kl = edges(t,a,value,rising)
                kr = edges(t,b,value,rising)
                counts.append([len(kl),len(kr)])
                if len(kl)==len(kr):
                    shifts.extend((kr-kl)*1000)
        max_edge = max(map(abs,shifts),default=0.)
        logic_a = np.select([a<=LOW,a>=HIGH],[0,1],default=-1)
        logic_b = np.select([b<=LOW,b>=HIGH],[0,1],default=-1)
        # A brief threshold mismatch is accounted for by edge comparison.
        both_known_opposite = (logic_a+logic_b==1)
        longest_opposite = 0.
        t0 = None
        for tt,opposite in zip(t,both_known_opposite):
            if opposite:
                if t0 is None:
                    t0=tt
                longest_opposite=max(longest_opposite,tt-t0)
            else:
                t0=None
        ok = all(x==y for x,y in counts) and max_edge<=tolerance_ps and longest_opposite*1000<=tolerance_ps
        transitions_a,transitions_b = logic_transitions(t,a,logic_a),logic_transitions(t,b,logic_b)
        same_logic = (len(transitions_a)==len(transitions_b) and longest_opposite*1000<=tolerance_ps
                      and all(d0==d1 and abs(t1-t0)*1000<=tolerance_ps
                              for (d0,t0),(d1,t1) in zip(transitions_a,transitions_b)))
        peak = np.argmax(abs(a-b))
        results.append(dict(signal=name,start_ns=start,stop_ns=stop,max_difference_v=float(abs(a[peak]-b[peak])),
                            max_difference_at_ns=float(t[peak]),crossing_counts=counts,
                            max_crossing_shift_ps=float(max_edge),known_opposite_span_ps=float(longest_opposite*1000),
                            valid_logic_transition_counts=[len(transitions_a),len(transitions_b)],
                            equivalent_at_validated_logic_transitions=bool(same_logic),
                            equivalent_in_observed_logic_and_timing=bool(ok)))
    return results


def read_details(trace,rec):
    cycle = rec['cycle']
    shift = 20*(cycle-INDEX[cycle])
    fall = rec['fall_ns']-shift
    observation = rec['calibration']['weak_on_ns']-shift
    value = logic_word(trace.rows,observation*1e-9,list(range(2,10)))
    expected = f'0x{rec["expected"]:02X}'
    stable = None
    if value.startswith('0x'):
        word = int(value,16)
        spec = [ge(b+2,HIGH) if word>>b&1 else le(b+2,LOW) for b in range(8)]
        stable = trace.signal_window(fall,observation,spec,suffix=True)
    item = dict(origin_cycle=cycle,expected=expected,observed_word=value,probe_ns=observation,
                stable_external_word=stable,readback_status=('PASS' if value==expected else 'FAIL') if stable else 'INCONCLUSIVE')
    try:
        item.update(read(trace,rec,shift))
    except ValueError as err:
        item['internal_analysis_limitation']=str(err)
        return item
    capture = item['capture_ns']
    sampling = item.get('sclk_sampling_ns',{}).get('20',fall-5.)
    relevant = ('sense_out','sense_bar','read_d','read_q','data3','cell_q','cell_qb','bl_at_sense','blb_at_sense')
    item['internal_logic'] = {k: logic_word(trace.rows,(capture if k in ('sense_out','sense_bar','read_d')
                                 else observation)*1e-9,[trace.cols[k]]) for k in relevant}
    for label,k,begin,stop in [('d','read_d',sampling,capture),('q','read_q',capture,observation),
                               ('data3','data3',capture,observation)]:
        v = view(trace,k,stop)
        rule = ge(trace.cols[k],HIGH) if v>=HIGH else (le(trace.cols[k],LOW) if v<=LOW else None)
        item[f'{label}_valid_suffix']=trace.signal_window(begin,stop,[rule],suffix=True) if rule else None
    if cycle in CYCLES:
        # Keep the clock-low recovery observation clear of the following rising edge.
        names = ('bl_at_sense','blb_at_sense','precharge','sclk_sampler_bl','sclk_sampler_blb','sclk_tail')
        recovery_rules = [ge(trace.cols[name],HIGH) for name in names[:2]]+[le(trace.cols[name],LOW) for name in names[2:]]
        item['precharge_recovery']=trace.signal_window(fall,fall+9.90,recovery_rules,suffix=True)
        item['precharge_fall50_ns']=scalar(edge_table(trace,'precharge',fall,fall+9.90,(50,),False)['50'])
        item['tail_fall20_ns']=scalar(edge_table(trace,'sclk_tail',fall,fall+9.90,(20,),False)['20'])
        for key,t in item['sclk_tail_ns'].items():
            item[f'tail{key}_conditions']= {name:view(trace,name,t) for name in
                            ('wl_at_q','blb_minus_bl','sab_minus_sa','tail_vgs','sense_tail','sense_out','read_d')}
        item['latch_differential_zero_edges_ns'] = {
            'rise':edge_table(trace,'sab_minus_sa',sampling,capture,(0,),True)['0'],
            'fall':edge_table(trace,'sab_minus_sa',sampling,capture,(0,),False)['0']}
    return item


def functional_verdict(reads,write_checks,write_ok,storage,internal_ok):
    states = {item['readback_status'] for item in reads}
    wrong_write = any(not w['verified'] and w['din'].startswith('0x') and w['din']!=w['expected']
                      for w in write_checks)
    if 'FAIL' in states or storage is False or write_ok is False or wrong_write:
        return 'FAIL'
    if (len(reads)==4 and states=={'PASS'} and storage and write_ok and internal_ok
            and len(write_checks)==6 and all(w['verified'] for w in write_checks)):
        return 'PASS_IN_SCOPE'
    return 'INCONCLUSIVE'


def causal_verdict(before,faithful,equivalent,internal,external,had_target_failure):
    if not (before and faithful and equivalent and internal):
        return 'INCONCLUSIVE'
    if external=='PASS_IN_SCOPE':
        return 'CORROBORATED_IN_CONTRAST'
    if had_target_failure and external=='FAIL':
        return 'NOT_CORROBORATED'
    return 'INCONCLUSIVE'


def load_contrast(run,receipt):
    mapping = json.loads((run/'probes.json').read_text())
    wave = pinned(run/'waveform.dat',receipt['artifacts']['waveform.dat'])
    rows,cols = read_waveform(wave,sorted(set(mapping.values())),EXTRA,minimum_end=250e-9-1e-15)
    cols.update({alias:cols[val] for alias,val in mapping.items()})
    cols.update({alias:cols[val] for alias,val in OLD_PROBES.items()})
    public_columns(cols)
    n = len(rows[0])
    rows = [(*r,r[cols['blb_at_sense']]-r[cols['bl_at_sense']],r[cols['sab_sampling_out']]-r[cols['sa_sampling_out']],
             r[cols['sclk_tail']]-r[cols['tail_ground']]) for r in rows]
    cols.update(blb_minus_bl=n,sab_minus_sa=n+1,tail_vgs=n+2)
    return Trace(rows,cols)


def public_columns(columns):
    columns.update(public_clk=1,vdd=10)
    columns.update({f'data{i}':i+2 for i in range(8)})


def r87_currents(run,trace,branch):
    card = SOURCE.search((run/'norton_fixture.spice').read_bytes())
    require(card is not None,'Missing ideal source')
    t,c = np.asarray(source_points(card),dtype=float).T
    time = np.asarray(trace.times)
    command = np.interp(time,t,c)
    path = run/'r87_current.dat'
    actual = None
    if path.is_file():
        try:
            values = np.loadtxt(path,skiprows=1,ndmin=2)
        except ValueError:
            values = None
        if (values is not None and values.shape==(len(time),2) and np.all(np.isfinite(values))
                and np.allclose(values[:,0]*1e9,time,rtol=0,atol=1e-9)):
            actual = values[:,1]
    vin = np.asarray([r[trace.cols['r87_upstream']] for r in trace.rows])
    vout = np.asarray([r[trace.cols['r87_local']] for r in trace.rows])
    source_current = actual if actual is not None else command
    net = (vin-vout)/branch['resistance_ohm']+source_current
    before = time<WINDOWS[0][0]
    preflight = dict(prefix_cmd_abs_peak_a=float(max(abs(command[before]))),
                     prefix_measured_abs_peak_a=float(max(abs(actual[before]))) if actual is not None else None,
                     net_current_basis='measured_source' if actual is not None else 'ideal_piecewise_linear_source')
    result, rows = [], []
    for (start,end),cycle in zip(WINDOWS,CYCLES,strict=True):
        i = (time>=start)&(time<=end)
        result.append(dict(cycle=cycle,excluded_from_macro_power=True,
                           cmd_abs_peak_a=float(max(abs(command[i]))),
                           measured_abs_peak_a=float(max(abs(actual[i]))) if actual is not None else None,
                           max_cmd_vs_measured_a=float(max(abs(command[i]-actual[i]))) if actual is not None else None,
                           net_root_abs_peak_a=float(max(abs(net[i])))))
        for k in np.flatnonzero(i):
            rows.append(dict(cycle=cycle,time_ns=time[k],command_a=command[k],
                             measured_a=actual[k] if actual is not None else None,
                             resistor_a=(vin[k]-vout[k])/branch['resistance_ohm'],net_upstream_a=net[k],
                             upstream_v=vin[k],local_v=vout[k]))
    return result,rows,preflight


def stored_zero(trace,start,stop):
    if trace.through(start,stop,levels(trace,'cell_q','cell_qb')):
        return True
    wrong = [ge(trace.cols['cell_q'],HIGH),le(trace.cols['cell_qb'],LOW)]
    return False if trace.signal_window(start,stop,wrong) else None


def plot_cycles(path, reference, contrast):
    from matplotlib.figure import Figure

    fig = Figure(figsize=(12,8),layout='constrained')
    axes = fig.subplots(3,2)
    fields = (('sclk_tail','wl_at_q'),('blb_minus_bl','sab_minus_sa'),('read_d','data3'))
    titles = (('SCLK do tail','WL local'),('BLB − BL','SAB − SA'),('D do FF','DATA3'))
    for i,((begin,end),cycle) in enumerate(zip(WINDOWS,CYCLES,strict=True)):
        axes[0,i].set_title(f'Ciclo {cycle} · linha 3')
        for j,(names,labels) in enumerate(zip(fields,titles,strict=True)):
            lo,hi = (begin+2.55,begin+5.25) if j<2 else (end+.8,end+2.5)
            ax = axes[j,i]
            for signal,label,color in zip(names,labels,('#2860a5','#af472b'),strict=True):
                for trace,style,suffix in ((reference,'--','ref.'),(contrast,'-','contraste')):
                    points = trace.points(lo,hi,[(trace.cols[signal],1.,0.)])
                    ax.plot([t for t,_ in points],[v[0] for _,v in points],style,color=color,
                            label=f'{label} {suffix}',linewidth=1.3)
            ax.set(xlabel='Tempo (ns)',ylabel='Tensão (V)',xlim=(lo,hi))
            ax.grid(True,linewidth=.4,alpha=.4)
            ax.legend(loc='best',fontsize=8)
    fig.suptitle('SRAM 4×8 · TT · Resolução e captura do bit 3')
    fig.savefig(path,dpi=160)


def analyze(run,output,plots=False):
    pinned(run/'authorization.json',json.loads((run/'attempt.json').read_text())['authorization_sha256'])
    authority = json.loads((run/'authorization.json').read_text())
    receipt = json.loads((run/'result.json').read_text())
    require(receipt['status']=='COMPLETED' and authority['waveform_fidelity']==FIDELITY, 'Contrast did not complete as authorized')
    for name,h in receipt['artifacts'].items():
        pinned(run/name,h)
    _,base_receipt,ref = load(REFERENCE,True)
    require(authority['reference_waveform_sha256']==base_receipt['waveform_sha256'], 'Wrong reference waveform')
    public_columns(ref.cols)
    new = load_contrast(run,receipt)
    fixture = json.loads((PARENT/'fixture.json').read_text())['cycles']
    old_reads,new_reads = ([read_details(trace,fixture[c]) for c in (14,15,*CYCLES)] for trace in (ref,new))
    old_writes,new_writes = (writes(trace,fixture) for trace in (ref,new))
    write_evidence = write(new)
    trace_end = min(ref.times[-1],new.times[-1])
    retained = stored_zero(new,120.55,trace_end)
    shape = []
    for (start,end),cycle in zip(WINDOWS,CYCLES,strict=True):
        for name in (*GATES,'r87_upstream','r87_local'):
            sample = gate_shape(new,name,start,end)
            entry = dict(cycle=cycle,gate=name,contrast=sample)
            if name in GATES:
                old = gate_shape(ref,name,start,end)
                entry.update(reference=old,**interpret_gate(old,sample,FIDELITY))
            shape.append(entry)
    # Compare the ramp as analog evidence. Logic-edge equivalence starts
    # after the power ramp, as the contract has no reset.
    segments = [('before',1.25,211.),('c16',211.,219.),('between',219.,231.),
                ('c17',231.,239.),('after',239.,trace_end)]
    controls = {label:compare_signals(ref,new,CONTROLS+PREFIX_ONLY if label=='before' else CONTROLS,
                start,stop,FIDELITY['common_edge_ps']) for label,start,stop in segments}
    ramp = compare_signals(ref,new,('vdd','public_clk','sclk_root','precharge','cell_q','cell_qb'),0.,1.25,
                           FIDELITY['common_edge_ps'])
    non_target = {label:compare_signals(ref,new,OTHER_READ,start,stop,FIDELITY['common_edge_ps'])
                  for label,start,stop in segments if label in ('c16','c17')}
    current,current_rows,current_prefix = r87_currents(run,new,authority['branch'])
    prefix = (all(e['equivalent_in_observed_logic_and_timing'] for e in controls['before'])
              and all(a['readback_status']==b['readback_status']=='PASS' for a,b in zip(old_reads[:2],new_reads[:2],strict=True))
              and all(w['verified'] for w in (*old_writes,*new_writes)))
    local = all(x['fidelity_verified'] for x in shape if x['gate'] in GATES)
    no_shared = all(x['equivalent_in_observed_logic_and_timing'] for label,group in controls.items()
                    if label!='before' for x in group)
    no_other_read = all(x['equivalent_at_validated_logic_transitions'] for group in non_target.values() for x in group)
    no_host = new.through(210.,trace_end,[le(new.cols['host_enabled'],LOW),
                   *(rule for bit in range(8) for rule in (ge(new.cols[f'i(v_sense_host{bit})'],-LIMIT_A),
                                                          le(new.cols[f'i(v_sense_host{bit})'],LIMIT_A)))])
    targets = new_reads[-2:]
    target_chain = all(r.get('d_valid_suffix') and r.get('q_valid_suffix') and r.get('data3_valid_suffix')
                       and r.get('precharge_recovery') and r.get('cell_correct_from_before_wl_to_observation')
                       and r.get('captured_address')=='0x3' for r in targets)
    valid_internal = bool(target_chain and retained and no_host)
    target_logic_correct = all(r.get('internal_logic',{}).get(signal)=='0x0'
                               for r in targets for signal in ('sense_out','read_d','read_q','data3'))
    functional = functional_verdict(new_reads,new_writes,stored_zero(new,120.55,125.),retained,
                                     valid_internal and target_logic_correct)
    baseline_failed = all(r['readback_status']=='FAIL' and r['observed_word']=='0xF8' for r in old_reads[-2:])
    data3_failed = any(r['readback_status']=='FAIL' and r.get('internal_logic',{}).get('data3')=='0x1'
                       for r in targets)
    causal = causal_verdict(prefix and baseline_failed,local,no_shared and no_other_read,valid_internal,functional,data3_failed)
    out = new_directory(output)
    write_json(out/'contrast.json',dict(functional_verdict=functional,sclk_hypothesis=causal,
        scope='One 250 ns TT contrast on cell (3,3)',electrical_qualification='NOT_CHARACTERIZED',
        reference_waveform_sha256=base_receipt['waveform_sha256'],contrast_waveform_sha256=receipt['artifacts']['waveform.dat'],
        waveform_samples=dict(reference=len(ref.rows),contrast=len(new.rows)),
        analyzer_sha256=sha256(Path(__file__)),clocks_and_pvt=authority['reference_conditions'],tolerance=FIDELITY,
        gate_fidelity=shape,verified_local_delay=local,startup_prefix_equivalence=prefix,
        shared_controls_equivalence=no_shared,other_read_paths_equivalence=no_other_read,
        read_phase_strong_host_undriven=no_host,target_chain_evidence=valid_internal,
        storage_preserved_through_ns=trace_end if retained else None,storage_zero_retained=retained,
        baseline_reads=old_reads,contrast_reads=new_reads,
        baseline_writes=old_writes,contrast_writes=new_writes,contrast_write_cell33=write_evidence,
        analog_startup_comparison=ramp,shared_controls=controls,other_read_paths=non_target,r87_current=current,
        r87_current_prefix=current_prefix,
        insufficient_data=['Historical reference did not save the immediate R87 nodes rc8562 / rc8571.']))
    write_table(out/'r87_current_and_voltage.csv',current_rows)
    write_table(out/'read_events.csv',[dict(run=which,cycle=item['origin_cycle'],**event)
          for which,items in (('reference',old_reads),('contrast',new_reads))
          for item in items for event in item.get('observations',[])])
    if plots:
        plot_cycles(out/'read_waveforms.png',ref,new)
    print(functional,causal,flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--plots',action='store_true')
    args = parser.parse_args()
    analyze(args.run,args.output,args.plots)


if __name__=='__main__':
    main()
