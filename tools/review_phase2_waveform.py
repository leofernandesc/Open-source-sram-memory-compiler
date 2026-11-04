#!/usr/bin/env python3
"""Reanalyze immutable raw samples with explicit current protocol criteria."""
import argparse
import json
from pathlib import Path
import numpy as np
from run_digital_regression import atomic_text,output_lock
from run_phase2_access import ROOT
from run_phase2_digital import sha
from phase2_access_checks import check


def review(source,out):
    receipt=json.loads((source/'results.json').read_text());wave=ROOT/receipt['build_directory']/'waveform.dat'
    pinned={str(p):sha(p) for p in [source/'results.json',wave,ROOT/'tools/phase2_access_checks.py',Path(__file__)]}
    data=np.loadtxt(wave,skiprows=1)
    checks,ref=check(data,receipt['cycles'],receipt['vectors'],receipt['capture_inputs'],receipt['capture_clocks'])
    result={'status':'PASS_PROTOCOL_REANALYSIS' if all(c['status']=='PASS' for c in checks) else 'FAIL',
            'scope':'Fresh protocol analysis of unchanged raw waveform; original receipt is preserved',
            'F2_FIS':'NOT_EVALUATED','inputs':pinned,'checks':checks,'capture_reference':ref,'release_metrics':[]}
    t=data[:,0]*1e9
    for rec in receipt['cycles']:
        if rec['operation'] in ('idle',) or rec['operation'].startswith('inactive'):continue
        fall=rec['fall_ns'];row=rec['row'];mask=(t>=fall)&(t<fall+9)
        def down(col,threshold):
            indices=np.flatnonzero(mask&(data[:,col]<=threshold))
            return float(t[indices[0]]-fall) if len(indices) else None
        wl=down(13+row,.36);pre=down(10,1.44)
        result['release_metrics'].append({'cycle':rec['cycle'],'operation':rec['operation'],
             'wl_release_after_public_fall_ns':wl,'precharge_conduction_after_public_fall_ns':pre,
             'release_guard_ns':pre-wl if pre is not None and wl is not None else None})
    # One example from the actual full-resolution data, not an ideal timing plot.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    rec=next(r for r in receipt['cycles'] if r['operation']=='write');fall=rec['fall_ns'];mask=(t>=fall-.2)&(t<=fall+3.6)
    fig,ax=plt.subplots(figsize=(9,4))
    ax.plot(t[mask]-fall,data[mask,13+rec['row']],label='WL selected (actual extraction)')
    ax.plot(t[mask]-fall,data[mask,10],label='PRECH (low enables precharge)')
    ax.axhline(.36,color='gray',ls=':',lw=.8);ax.axhline(1.44,color='gray',ls=':',lw=.8)
    ax.axvline(0,color='black',ls='--',lw=.8,label='Public falling clock edge')
    ax.set(xlabel='Time after public falling edge (ns)',ylabel='Voltage (V)',title='Measured WL release before precharge')
    ax.legend(fontsize=8);ax.grid(alpha=.2);fig.tight_layout();fig.savefig(out/'release_guard.png',dpi=160);plt.close(fig)
    for p,expected in pinned.items():
        if sha(p)!=expected:raise ValueError('Reanalysis input changed')
    result['plot_sha256']=sha(out/'release_guard.png')
    atomic_text(out/'results.json',json.dumps(result,indent=2)+'\n')
    print(result['status'],len(checks),'checks',sum(c['status']=='FAIL' for c in checks),'failures')
    return result['status']!='PASS_PROTOCOL_REANALYSIS'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();out=(ROOT/a.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2') or out==ROOT/'reports/phase2':p.error('Output under reports/phase2 required')
    out.mkdir(parents=True,exist_ok=True)
    with output_lock(out):return review(ROOT/a.source,out)


if __name__=='__main__':raise SystemExit(main())
