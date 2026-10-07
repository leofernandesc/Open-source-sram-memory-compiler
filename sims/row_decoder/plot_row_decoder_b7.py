#!/usr/bin/env python3
"""Plot archived samples from the freshly netlisted B7 source."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-dir',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    sample=args.input_dir/'plot_samples.csv';metadata=args.input_dir/'plot_metadata.json'
    info=json.loads(metadata.read_text())
    with sample.open() as f:
        rows=list(csv.DictReader(f))
    data={key:np.array([float(r[key]) for r in rows]) for key in rows[0]}
    t=data['time_ns'];fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    for node in ['net3','x1.a0b','x1.a0t']:
        mask=(t>=17.8)&(t<=18.8)
        axes[0,0].plot(t[mask],data[f'v({node})'][mask],label={'net3':'A0','x1.a0b':'A0B','x1.a0t':'A0T'}[node])
    axes[0,0].set_title('Regenerated literals settle during precharge')
    for row in range(4):
        mask=(t>=19.94)&(t<=20.6)
        axes[0,1].plot(t[mask],data[f'v(x1.n{row})'][mask],label=f'N{row}')
    axes[0,1].axhline(1.95,color='firebrick',ls=':',label='1.95 V diagnostic')
    axes[0,1].set_title('Second evaluation: row 00 discharges')
    for node in ['DEC0','WL0','WL2']:
        mask=(t>=19.94)&(t<=21)
        axes[1,0].plot(t[mask],data[f'v({info["nodes"][node].lower()})'][mask],label=node)
    axes[1,0].set_title('Selected row and unselected WL reference')
    drain,gate,source,bulk=info['limiting_mos']
    trace=data[f'v({drain})']-(0 if source in ['gnd','0'] else data[f'v({source})'])
    mask=(t>=info['peak_time_ns']-.08)&(t<=info['peak_time_ns']+.08)
    axes[1,1].plot(t[mask],trace[mask],label='x4.mn1 external VDS')
    axes[1,1].axhline(1.95,color='firebrick',ls=':',label='1.95 V diagnostic')
    axes[1,1].scatter([info['peak_time_ns']],[info['peak_v']],s=20,color='black')
    axes[1,1].set_title(f'Priming row 11: unchanged WL buffer peak {info["peak_v"]:.6f} V')
    for ax in axes.flat:
        ax.set(xlabel='Time (ns)',ylabel='Voltage (V)')
        ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.suptitle('Retained B7, fresh canonical schematic: '+info['profile']+'\n17.4 fF per WL; Gear 1 ps, CHGTOL=1e-18 C. Pre-layout experiment.',fontsize=12)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    for extension in ['.png','.pdf']:
        fig.savefig(args.output.with_suffix(extension),dpi=180)
    args.output.with_suffix('.json').write_text(json.dumps(dict(script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        input_sha256={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [sample,metadata]},
        source_schematic_sha256=info['source_schematic_sha256']),indent=2)+'\n')


if __name__=='__main__':
    main()
