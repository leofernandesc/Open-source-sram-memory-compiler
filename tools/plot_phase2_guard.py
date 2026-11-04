#!/usr/bin/env python3
"""Plot actual retained phase traces; do not turn an access PASS into phase approval."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_phase2_digital import sha

ROOT=Path(__file__).resolve().parents[1]


def main():
    output=ROOT/'reports/phase2/phase_guard_review';output.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True)
    result={'scope':'Experimental TT/1.8V/27C phase guard; 20% WE vs 80% PRECH thresholds',
            'CORE':'NOT_EVALUATED','F2_FIS':'NOT_EVALUATED','cases':[]}
    for ax,name,title in zip(axes,['access_pilot_klu','access_guard40_pilot'],
                             ['Initial phase binding','Write enable delayed to tap 40']):
        source=ROOT/'reports/phase2'/name;receipt=json.loads((source/'results.json').read_text())
        raw=ROOT/receipt['build_directory']/'waveform.dat'
        data=np.loadtxt(raw,skiprows=1)
        case=next(c for c in receipt['cycles'] if c['operation']=='write')
        selected=data[(data[:,0]>=case['rise_ns']*1e-9)&(data[:,0]<(case['rise_ns']+4)*1e-9)]
        def cross(column,voltage):
            i=np.flatnonzero((selected[:-1,column]<voltage)&(selected[1:,column]>=voltage))[0]
            a,b=selected[i],selected[i+1]
            return float((a[0]+(voltage-a[column])/(b[column]-a[column])*(b[0]-a[0]))*1e9-case['rise_ns'])
        released=cross(10,1.44);enabled=cross(12,.36);margin=(enabled-released)*1000
        ax.plot((selected[:,0]*1e9-case['rise_ns']),selected[:,10],label='PRECH (low = precharge)',color='#1767a6')
        ax.plot((selected[:,0]*1e9-case['rise_ns']),selected[:,12],label='WE',color='#d06125')
        ax.axvline(released,color='#1767a6',linestyle='--',alpha=.7)
        ax.axvline(enabled,color='#d06125',linestyle='--',alpha=.7)
        ax.axvspan(min(released,enabled),max(released,enabled),color='green' if margin>0 else 'red',alpha=.12)
        ax.set_title(f'{title}: margin {margin:+.1f} ps',loc='left')
        ax.set_ylabel('Voltage (V)');ax.set_ylim(-.1,1.95);ax.grid(alpha=.2);ax.legend(loc='lower right')
        result['cases'].append({'source':str(source.relative_to(ROOT)),
                                'receipt_sha256':sha(source/'results.json'),'raw_sha256':sha(raw),
                                'margin_ps':margin,'disposition':'PHASE_GUARD_PASS' if margin>0 else 'REJECTED_PHASE_OVERLAP'})
    axes[-1].set_xlabel('Time after rising external clock (ns)')
    fig.tight_layout();fig.savefig(output/'write_precharge_guard.svg');fig.savefig(output/'write_precharge_guard.png',dpi=150)
    (output/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
