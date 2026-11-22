#!/usr/bin/env python3
"""Resume the two sealed nominal SNM campaigns and independently audit their exports."""

import argparse
from collections import Counter
import json
from pathlib import Path
import time

import numpy as np

from phase3_snm_measure import read_vtc, butterfly
from run_digital_regression import atomic_text
from run_phase3_eco_pex import new_directory, pinned
from run_phase3_snm import ROOT, design, export, model_config, nominal_deck, reported_seed, result_for, run, sha256
from validate_phase3_snm_nominal_pilot import audit as audit_pilot


BUILD = ROOT/'build/phase3'
TARGET = 200
RUNS = {mode:BUILD/f'snm_nominal_{mode}_batch01_20261120' for mode in ('hold','read')}
CONTRAST = BUILD/'sclk_tt_contrast_run_20261120'


def config_for(mode, directory):
    receipt=json.loads((directory/'manifest.json').read_text())
    config=receipt['config']
    start={'hold':20001,'read':30001}[mode]
    if config!=design('nominal-proposed',mode,start,220):
        raise ValueError('Unexpected condition, model corner or seed range')
    for path,digest in receipt['sources'].items():
        pinned(ROOT/path,digest)
    return receipt,config


def inventory(directory, config):
    cases=config['cases']
    return Counter(r['status'] if (r:=result_for(directory,case)) else 'NOT_RUN' for case in cases)


def preflight(target):
    proofs={}
    for mode,directory in RUNS.items():
        receipt,cfg=config_for(mode,directory)
        if model_config(cfg)!=receipt['models']:
            raise ValueError('Mismatch/process settings or PDK closure changed')
        deck=nominal_deck(cfg['cases'][0],cfg)
        wl='0' if mode=='hold' else 'vdd'
        if (deck.count('\nXM')!=6 or f'XMAL out_l {wl} vdd 0 ' not in deck
                or f'XMAR vdd {wl} out_r 0 ' not in deck):
            raise ValueError('Unexpected access bias or incomplete 6T cell')
        proof=audit_pilot(directory)
        if not proof['first_lot_verified'] or proof['unique_valid']!=4:
            raise ValueError('Need four pinned pilot checkpoints per mode')
        proofs[mode]=proof
    output=new_directory(target)
    (output/'preflight.json').write_text(json.dumps(dict(status='VERIFIED_OFFLINE',modes=proofs),indent=2)+'\n')


def batch_limit(counts,remaining_s,timeout_s):
    # Reserve wall time even in the worst case where every seed times out.
    return max(0,min(50,TARGET-counts['MEASURED'],counts['NOT_RUN'],int((remaining_s-15)//timeout_s)))


def advance(out,budget_s,timeout_s):
    finish=time.monotonic()+budget_s
    seal=json.loads((out/'preflight.json').read_text())
    if seal['status']!='VERIFIED_OFFLINE':
        raise ValueError('Campaign preflight is missing')
    contrast=json.loads((CONTRAST/'simulation.json').read_text())
    if contrast.get('status') not in ('PASS','ERROR','TIMEOUT'):
        raise ValueError('TT simulation still in progress')
    configs={}
    for mode,directory in RUNS.items():
        _,config=config_for(mode,directory)
        if sha256(directory/'manifest.json')!=seal['modes'][mode]['campaign_manifest_sha256']:
            raise ValueError('Preflight referred to a different campaign')
        configs[mode]=config
    with (out/'batches.jsonl').open('x') as journal:
        progress=True
        while progress:
            progress=False
            for mode,directory in RUNS.items():
                config=configs[mode]
                before=inventory(directory,config)
                limit=batch_limit(before,finish-time.monotonic(),timeout_s)
                if not limit:
                    continue
                begun=time.monotonic()
                status=run(argparse.Namespace(output=directory,retry_failed=False,limit=limit,timeout=timeout_s))
                after=inventory(directory,config)
                record=dict(mode=mode,limit=limit,timeout_s=timeout_s,before=dict(before),after=dict(after),
                            returncode=status,elapsed_s=time.monotonic()-begun)
                journal.write(json.dumps(record)+'\n')
                journal.flush()
                print(json.dumps(record),flush=True)
                progress |= after['NOT_RUN']<before['NOT_RUN']
    state={mode:dict(inventory(path,configs[mode])) for mode,path in RUNS.items()}
    (out/'checkpoints.json').write_text(json.dumps(state,indent=2)+'\n')


def verify_series(mode,directory,config,destination):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt

    measured=[]
    other=[]
    for case in config['cases']:
        row=result_for(directory,case)
        if row is None:
            continue
        if row['status']!='MEASURED':
            other.append(row)
            continue
        path=directory/row['attempt']
        if reported_seed((path/'ngspice.log').read_text())!=case['seed']:
            raise ValueError('Recorded seed mismatch')
        if (path/'bench.spice').read_text()!=nominal_deck(case,config):
            raise ValueError('Seed deck differs from the canonical stimulus')
        curves=read_vtc(path/'vtc.dat',config['vdd'],config['step'])
        recalculated=butterfly(*curves.T)
        if any(row[k]!=v for k,v in recalculated.items()):
            raise ValueError('SNM recomputation differs from checkpoint')
        measured.append((row,curves))
    if not measured:
        return dict(no_valid_samples=True,invalid=other)
    ordered=sorted(measured,key=lambda item:item[0]['snm_v'])
    median=np.median([r['snm_v'] for r,_ in ordered])
    representatives=[('Mínimo',ordered[0]),('Próximo da mediana',min(ordered,key=lambda v:abs(v[0]['snm_v']-median))),
                     ('Máximo',ordered[-1])]
    fig, axes=plt.subplots(1,3,figsize=(12,4.1),layout='constrained',sharex=True,sharey=True)
    specimens=[]
    for ax,(caption,(row,curves)) in zip(axes,representatives,strict=True):
        v,l,r=(column*1000 for column in curves.T)
        ax.plot(v,l,color='#266578',label='VTC esquerda')
        ax.plot(r,v,color='#a3442a',label='VTC direita espelhada')
        ax.set(title=f'{caption} · seed {row["seed"]}\nSNM {row["snm_v"]*1000:.3f} mV',
               xlabel='Q (mV)',aspect='equal',xlim=(0,1800),ylim=(0,1800))
        ax.grid(alpha=.17)
        specimens.append(dict(role=caption,**row))
    axes[0].set_ylabel('QB (mV)')
    axes[-1].legend(loc='upper right',frameon=False,fontsize=7)
    fig.suptitle(f'{mode.title()} SNM · tt_mm · 1,8 V · 27 °C')
    fig.savefig(destination/'butterflies.png',dpi=155)
    plt.close(fig)
    control=dict(verified_vtcs=len(measured),distinct_trace_sha256=len({r['artifacts']['vtc.dat'] for r,_ in measured}),
                 specimens=specimens,invalid=other,
                 n_bistable=sum(r['classification']=='BISTABLE' for r,_ in measured),
                 n_physical_zero=sum(r['classification']=='MONOSTABLE_ZERO' for r,_ in measured))
    control['butterflies_sha256']=sha256(destination/'butterflies.png')
    return control


def export_all(target):
    out=new_directory(target)
    for mode,directory in RUNS.items():
        _,config=config_for(mode,directory)
        dest=out/mode
        export(directory,dest)
        result=verify_series(mode,directory,config,dest)
        atomic_text(dest/'vtc_audit.json',json.dumps(result,indent=2,allow_nan=False)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('preflight','advance','export'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--budget',type=int,default=1100)
    parser.add_argument('--timeout',type=int,default=15)
    opts=parser.parse_args()
    output=opts.output.resolve()
    if opts.action=='preflight':
        preflight(output)
    elif opts.action=='advance':
        if not 0<opts.budget<=1800 or not 1<=opts.timeout<=45:
            parser.error('Use a batch budget of at most 1800 s and per-seed timeout of 1–45 s')
        advance(output,opts.budget,opts.timeout)
    else:
        export_all(output)


if __name__=='__main__':
    main()
