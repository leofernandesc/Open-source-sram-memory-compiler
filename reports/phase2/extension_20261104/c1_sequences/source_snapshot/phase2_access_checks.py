"""Independent electrical sequencing/capture checks on full-resolution traces."""
from pathlib import Path
import sys
import numpy as np


def check(data,records,vectors,capture_inputs=None,capture_clocks=None):
    if data.ndim!=2 or data.shape[1]!=len(vectors)+1 or not np.all(np.isfinite(data)):
        raise ValueError('Waveform columns/values differ from declared probes')
    if not np.all(np.diff(data[:,0])>0):raise ValueError('Nonmonotonic transient time')
    t=data[:,0];wl=data[:,13:17];checks=[]
    def put(kind,passed,**evidence):checks.append(dict(kind=kind,status='PASS' if passed else 'FAIL',**evidence))
    put('one_hot_or_zero',not np.any(np.sum(wl>1.44,axis=1)>1))
    # Both devices may conduct before their signals reach valid logic levels;
    # require PRECH >=80% before WE passes 20%, and until WE has released.
    selected=(t>=2e-9)
    overlap=selected&(data[:,12]>.36)&(data[:,10]<1.44)
    put('write_precharge_nonoverlap',not np.any(overlap),bad_samples=int(np.sum(overlap)))
    overlap=selected&np.any(wl>.36,axis=1)&(data[:,10]<1.44)
    put('wordline_precharge_nonoverlap',not np.any(overlap),bad_samples=int(np.sum(overlap)))
    ref=None
    if capture_inputs and capture_clocks:
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'sims/row_decoder'))
        import run_row_address_setup_hold as library_reader
        ref=library_reader.liberty_constraints('tt')
        setup=max(float(np.max(tab[2])) for tab in ref['setup'].values())
        hold=max(0.,max(float(np.max(tab[2])) for tab in ref['hold'].values()))
    for rec in records:
        begin,end=rec['rise_ns']*1e-9,rec['fall_ns']*1e-9
        window=(t>=begin+1e-9)&(t<end-.5e-9)
        # CTS adds legitimate clock arrival delay after the public falling
        # edge. Require WL release before precharge conduction, rather than
        # inheriting an arbitrary 0.5-ns schematic-only release bound.
        low=(t>=end)&(t<begin+19e-9)&(data[:,10]<1.44)
        put('low_phase_wordlines',not np.any(wl[low]>.36),cycle=rec['cycle'])
        ready=(t>=begin+18e-9)&(t<begin+19e-9)
        put('precharge_ready_before_next_access',bool(np.any(ready)) and
            not np.any(data[ready][:,[9,10,11,12]]>.36) and not np.any(wl[ready]>.36),cycle=rec['cycle'])
        if rec['operation']=='idle' or rec['operation'].startswith('inactive'):
            put('inactive_wordlines',not np.any(wl[window]>.36),cycle=rec['cycle'])
            put('inactive_phases',not np.any(data[window][:,[9,11,12]]>.36),cycle=rec['cycle'])
        else:
            wrong=[r for r in range(4) if r!=rec['row']]
            put('unselected_wordlines',not np.any(wl[window][:,wrong]>.36),cycle=rec['cycle'])
            put('selected_wordline_asserts',bool(np.any(wl[window,rec['row']]>1.44)),cycle=rec['cycle'])
            forbidden=11 if rec['operation']=='write' else 12
            put('write_sense_exclusion',not np.any(data[window,forbidden]>.36),cycle=rec['cycle'])
        if rec['operation']!='read' or ref is None:continue
        for bit in range(8):
            data_col=vectors.index(capture_inputs[bit])+1
            clock_col=vectors.index(capture_clocks[bit])+1
            clock=data[:,clock_col]
            rising=np.flatnonzero((clock[:-1]<.9)&(clock[1:]>=.9))
            nearby=[i for i in rising if end-.5e-9<t[i]<end+1e-9]
            if len(nearby)!=1:
                put('local_capture_edge',False,cycle=rec['cycle'],bit=bit,edges=len(nearby));continue
            i=nearby[0];edge=float(t[i]+(.9-clock[i])/(clock[i+1]-clock[i])*(t[i+1]-t[i]))
            mask=(t>=edge-setup*1e-9)&(t<=edge+hold*1e-9)
            expected=(rec['expected']>>bit)&1;v=data[mask,data_col]
            valid=((v>=1.44)&(v<=1.98)) if expected else ((v>=-.18)&(v<=.36))
            put('output_ff_setup_hold_envelope',bool(len(v) and np.all(valid)),cycle=rec['cycle'],bit=bit,
                local_edge_ns=edge*1e9,setup_guard_ns=setup,hold_guard_ns=hold,
                data_min_v=float(min(v)) if len(v) else None,data_max_v=float(max(v)) if len(v) else None)
    return checks,{'path':str(ref['path']),'sha256':ref['sha256'],
                   'interpretation':'Conservative TT/25C library table envelope against TT/27C transistor run; no PVT characterization'} if ref else None
