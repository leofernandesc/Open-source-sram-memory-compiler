#!/usr/bin/env python3
"""Reconcile diagnostic stages, derive event-level tables and plot actual data."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from investigate_sense_pex import ROOT, PROBES, SOURCE, topology, variant, verify
from run_phase1_final_isolated import read_data, sha, write_json
from analyze_phase2_extension_timing import crossing


def table(path,rows):
    with path.open('w') as f:
        fields=list(dict.fromkeys(k for r in rows for k in r))
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sources',type=Path,nargs='+',required=True)
    p.add_argument('--top-context',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve()
    if not out.is_relative_to(ROOT/'reports/phase1'):p.error('Output under reports/phase1 required')
    out.mkdir(parents=True,exist_ok=False)
    inputs={str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))}
    allcases=[];events=[];replayed=[]
    for source in a.sources:
        source=source.resolve();receipt=verify(source);replayed.append(dict(source=str(source.relative_to(ROOT)),**receipt))
        inputs[str((source/'results.json').relative_to(ROOT))]=sha(source/'results.json')
        data=json.loads((source/'results.json').read_text())
        for item in data['cases']:
            c=item['case'];folder=source/c['id'];checks=json.loads((folder/'checks.json').read_text())
            allcases.append(dict(source=str(source.relative_to(ROOT)),**c,status=item['status'],
                                 failed_checks=sum(x['status']!='PASS' for x in checks['checks'])))
            for metric in checks['metrics']:
                index=metric['event'];checkmap={x['name']:x for x in checks['checks']}
                events.append(dict(source=str(source.relative_to(ROOT)),**c,**metric,
                                   expected_sign=1 if metric['expected_sa_out'] else -1,
                                   sample_pass=checkmap[f'{index}_sampling_tracks_inputs']['status']=='PASS',
                                   decision_pass=checkmap[f'{index}_regeneration_polarity_and_rails']['status']=='PASS',
                                   all_event_checks_pass=all(x['status']=='PASS' for x in checks['checks'] if x['name'].startswith(f'{index}_'))))
    table(out/'cases.csv',allcases);table(out/'events.csv',events)
    sensitivity=[]
    for cap in (2,10):
        for sign in (1,-1):
            rows=[r for r in events if r['mode']=='full' and r['high_v']==1.8 and r['slew_ps']==50 and r['cap_ff']==cap and r['expected_sign']==sign]
            deltas=sorted({r['delta_mv'] for r in rows})
            passed=[d for d in deltas if all(x['all_event_checks_pass'] for x in rows if x['delta_mv']==d)]
            failed=[d for d in deltas if not all(x['all_event_checks_pass'] for x in rows if x['delta_mv']==d)]
            minimum=min(passed) if passed else None
            below=[d for d in failed if minimum is not None and d<minimum]
            sensitivity.append(dict(cap_ff=cap,expected_sign=sign,smallest_pass_tested_mv=minimum,
                                    largest_failure_below_mv=max(below) if below else None,
                                    passed_tested_mv=' '.join(f'{d:g}' for d in passed),
                                    failed_tested_mv=' '.join(f'{d:g}' for d in failed)))
    table(out/'decision_limits.csv',sensitivity)
    _,caps,_=variant('full');mapping,_=topology(SOURCE.read_text());coupling={'SA_OUT':0.,'SA_OUTB':0.}
    for line in SOURCE.read_text().splitlines():
        if not line.startswith('C'):continue
        w=line.split();nodes={mapping.get(n,n) for n in w[1:3]}
        for side in coupling:
            if nodes=={'SCLK',side}:coupling[side]+=float(w[3][:-1])
    write_json(out/'capacitance_groups.json',dict(output_ground_ff=caps['original_output_ground_totals_ff'],
                                               direct_clock_output_ff=coupling,
                                               note='Explicit extracted capacitances only; excludes intrinsic MOS capacitance and external loads'))
    top=a.top_context.resolve();context=json.loads((top/'results.json').read_text())
    inputs[str((top/'results.json').relative_to(ROOT))]=sha(top/'results.json')
    for n,h in context['artifacts'].items():
        if sha(top/n)!=h:raise ValueError('Top context artifact changed')
    for path,h in context['inputs'].items():
        if sha(ROOT/path)!=h:raise ValueError('Top context input changed')
    # Replay the specific measurements from preserved complete edge windows.
    # This does not require the 100 MB full-top transient in a fresh clone.
    excerpt=np.load(top/'top_edge_windows.npz')['data']
    clocks=list(csv.DictReader((top/'clock_edges.csv').open()))
    pins=list(csv.DictReader((top/'pins_at_sense.csv').open()))
    original=json.loads((ROOT/'reports/phase2/direct_abutment_20261111/qualification_v1/results.json').read_text())
    for clock in clocks:
        edge=float(clock['t20']);m=(excerpt[:,0]>=edge-.3)&(excerpt[:,0]<=edge+.7)
        window=excerpt[m];t=window[:,0];clk=window[:,1]
        if not np.all(np.diff(t)<.010001):raise ValueError('Missing native edge-window samples')
        for level,voltage in ((10,.18),(20,.36),(50,.9),(80,1.44),(90,1.62)):
            actual=crossing(t,clk,voltage,t[0],t[-1])
            if abs(actual-float(clock[f't{level}']))>1e-10:raise ValueError('Clock edge disagreement in excerpt')
        for pin in (p for p in pins if p['cycle']==clock['cycle']):
            time=float(pin['time_ns']);bit=int(pin['bit']);expected=int(pin['expected'])
            bl=float(np.interp(time,t,window[:,2+2*bit]));blb=float(np.interp(time,t,window[:,3+2*bit]))
            for name,value in [('bl_v',bl),('blb_v',blb),('signed_delta_v',(bl-blb)*(1 if expected else -1)),('common_mode_v',(bl+blb)/2)]:
                if abs(value-float(pin[name]))>1e-10:raise ValueError('Pin measurement disagreement in excerpt')
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    ax=axes[0,0];deltas=sorted({r['delta_mv'] for r in events if r['mode']=='full' and r['high_v']==1.8 and r['slew_ps']==50})
    image=[];labels=[]
    for cap in (2,10):
        for sign in (1,-1):
            row=[]
            for d in deltas:
                values=[r['all_event_checks_pass'] for r in events if r['mode']=='full' and r['high_v']==1.8 and r['slew_ps']==50 and r['cap_ff']==cap and r['expected_sign']==sign and r['delta_mv']==d]
                row.append(float(all(values)))
            image.append(row);labels.append(f'{cap} fF, '+('BL > BLB' if sign==1 else 'BLB > BL'))
    ax.imshow(image,cmap=matplotlib.colors.ListedColormap(['#e7b5ad','#b5c9de']),vmin=0,vmax=1,aspect='auto')
    ax.set(xticks=range(len(deltas)),xticklabels=[f'{d:g}' for d in deltas],yticks=range(4),yticklabels=labels,
           xlabel='Diferencial testado (mV)',title='PEX completa — decisão nas duas ordens de avaliação')
    for row in range(4):
        for col in range(len(deltas)):ax.text(col,row,'PASS' if image[row][col] else 'FAIL',ha='center',va='center',fontsize=8)
    ax=axes[0,1]
    colors={'full':'#1d4b73','no_c':'#667d38','no_r':'#a25d2d','no_rc':'#6c5b8c','no_output_ground':'#338c83','no_clock_output':'#a74b6f','equal_output_ground':'#444444','no_r_mirror_outputs':'#b08825'}
    for mode in ['full','no_c','no_r','no_rc','no_output_ground','no_clock_output','equal_output_ground','no_r_mirror_outputs']:
        item=next((r for r in allcases if r['mode']==mode and r['delta_mv']==5 and r['polarity']==1 and r['cap_ff']==2 and r['high_v']==1.8 and r['slew_ps']==50),None)
        if not item:continue
        d=read_data(ROOT/item['source']/item['id']/'waveform.dat.gz');t=d[:,0]*1e9
        ax.plot((t-5)*1000,d[:,5]-d[:,6],label=mode,color=colors[mode])
    ax.axhline(0,color='#aaaaaa',lw=.7)
    ax.set(xlim=(-20,400),ylim=(-.25,.25),xlabel='Tempo após início de SCLK (ps)',ylabel='SA_OUT − SA_OUTB (V)',
           title='Intervenções diagnósticas — ΔBL = +5 mV, 2 fF')
    ax.legend(fontsize=7,loc='upper left');ax.grid(alpha=.2)
    ax=axes[1,0]
    for high,slew,label,color in [(1.8,50,'High 1,8 V / borda 50 ps','#1d4b73'),(1.6,50,'High 1,6 V / borda 50 ps','#667d38'),(1.8,200,'High 1,8 V / borda 200 ps','#a25d2d')]:
        item=next((r for r in allcases if r['mode']=='full' and r['delta_mv']==5 and r['polarity']==1 and r['cap_ff']==2 and r['high_v']==high and r['slew_ps']==slew),None)
        if item:
            d=read_data(ROOT/item['source']/item['id']/'waveform.dat.gz');t=d[:,0]*1e9
            ax.plot((t-5)*1000,d[:,5]-d[:,6],label=label,color=color)
    ax.axhline(0,color='#aaaaaa',lw=.7);ax.grid(alpha=.2);ax.legend(fontsize=8)
    ax.set(xlim=(-20,800),ylim=(-1.9,1.9),xlabel='Tempo após início de SCLK (ps)',ylabel='SA_OUT − SA_OUTB (V)',title='PEX completa — common-mode e slew, +5 mV / 2 fF')
    ax=axes[1,1]
    for clock in clocks:
        edge=float(clock['t20']);cycle=next(r for r in original['cycles'] if r['cycle']==int(clock['cycle']))
        m=(excerpt[:,0]>=edge-.3)&(excerpt[:,0]<=edge+.7);t=(excerpt[m,0]-edge)*1000
        for bit in range(8):
            signed=(excerpt[m,2+2*bit]-excerpt[m,3+2*bit])*(1 if cycle['expected']>>bit&1 else -1)
            ax.plot(t,signed,color='#1d4b73',alpha=.22,lw=.7)
    ax.axvline(0,color='#888888',lw=.8);ax.axhline(.02,color='#a25d2d',ls='--',label='20 mV: ponto isolado testado')
    ax.set(xlim=(-150,250),ylim=(0,2.05),xlabel='Tempo relativo a SCLK20 físico (ps)',ylabel='Diferencial assinado BL/BLB (V)',title='4×8 com abutment — 72 bits / nove leituras')
    ax.text(.02,.08,'Conectividade/junções extraídas; sem RC de interconexão',transform=ax.transAxes,fontsize=8)
    ax.legend(fontsize=7,loc='lower right');ax.grid(alpha=.2)
    fig.suptitle('Diagnóstico nominal do sense — TT / 1,8 V / 27 °C',fontsize=13)
    fig.savefig(out/'diagnostic_summary.png',dpi=160);plt.close(fig)
    result=dict(status='PASS_ANALYSIS_INTEGRITY',inputs=inputs,replayed=replayed,
                top_edge_window_measurements_replayed=True,
                cases=len(allcases),events=len(events),case_failures=sum(r['status']!='PASS' for r in allcases),
                functional_failures_preserved=True,decision_limits=sensitivity,
                artifacts={str(p.relative_to(out)):sha(p) for p in sorted(out.iterdir()) if p.is_file()})
    write_json(out/'results.json',result);print(json.dumps({k:result[k] for k in ('status','cases','events','case_failures')}))


if __name__=='__main__':main()
