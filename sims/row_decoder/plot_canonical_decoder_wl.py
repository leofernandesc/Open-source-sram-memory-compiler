#!/usr/bin/env python3
"""Export measured local-interface waveforms and campaign screen metrics."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('campaign',type=Path)
    args=parser.parse_args()
    path=args.campaign/'manifest.json'
    manifest=json.loads(path.read_text())
    if not manifest['complete']:
        raise ValueError('Campaign must be complete before exporting its summary')
    provenance=dict(script_sha256=sha(Path(__file__)),manifest_sha256=sha(path),plots={})
    rise,fall=manifest['schedule']['evaluation_ns']
    settled=rise+manifest['schedule']['settling_ns']
    for profile,(corner,vdd,temp) in manifest['profiles'].items():
        source=args.campaign/f'{profile}_1_to_2/waveforms.csv'
        if not source.exists():continue
        with source.open() as handle: rows=list(csv.DictReader(handle))
        def values(key):return np.array([float(row[key]) for row in rows])
        time=values('time')*1e9
        fig,axes=plt.subplots(3,1,figsize=(11,8),sharex=True,layout='constrained')
        for node in ('pclk','a0','a1'):
            axes[0].plot(time,values(f'v({node})'),label=node.upper())
        for row in range(4):
            for axis,family in ((axes[1],'dec'),(axes[2],'wl')):
                axis.plot(time,values(f'v({family}{row})'),label=family.upper()+str(row))
        for axis in axes:
            axis.axvspan(settled,fall-0.025,color='seagreen',alpha=0.12,label='Settled screen window')
            axis.axvline(rise,color='gray',ls=':',lw=0.8)
            axis.set_ylabel('Voltage (V)');axis.grid(alpha=0.25)
            axis.legend(loc='upper left',ncols=5,fontsize=8)
        axes[2].axhline(0.9*vdd,color='gray',ls='--',lw=0.8)
        axes[2].set_xlabel('Time (ns)');axes[2].set_xlim(0,27.5)
        fig.suptitle(f'Frozen decoder + WL PEX: {corner.upper()}, {vdd:g} V, {temp:g} C; address 1 to 2\n'
                     'Controlled local PCLK; 102.874 fF per WL; experimental voltage/window screen')
        output=args.campaign/f'waveforms_{profile}_1_to_2.png'
        fig.savefig(output,dpi=160);plt.close(fig)
        provenance['plots'][output.name]=dict(sha256=sha(output),waveforms_sha256=sha(source))
    cases=manifest['cases']
    transitions=sorted({(row['old'],row['new']) for row in cases})
    fig,axes=plt.subplots(3,1,figsize=(11,9),sharex=True,layout='constrained')
    for profile in manifest['profiles']:
        rows={(row['old'],row['new']):row for row in cases if row['profile']==profile}
        indices=[i for i,key in enumerate(transitions) if key in rows]
        ordered=[rows[transitions[i]] for i in indices]
        for axis,values in [(axes[0],[r['wl_delay90_ps'] for r in ordered]),
                            (axes[1],[r['wl_margin_over_screen_v']*1e3 for r in ordered]),
                            (axes[2],[r['worst_external_terminal_bias']['abs_max_v'] for r in ordered])]:
            axis.plot(indices,values,marker='o',ms=3,label=profile.upper())
    axes[0].set_ylabel('PCLK50 to WL90 (ps)')
    axes[1].set_ylabel('WL margin over 0.9 VDD (mV)')
    axes[1].axhline(0,color='firebrick',ls='--',lw=0.8)
    axes[2].set_ylabel('Peak external-terminal bias (V)')
    axes[2].axhline(1.95,color='firebrick',ls='--',lw=0.8,label='1.95 V screen')
    axes[2].set_xticks(range(len(transitions)),[f'{a}:{b}' for a,b in transitions])
    axes[2].set_xlabel('Old address : new address')
    for axis in axes:axis.grid(alpha=0.25);axis.legend(fontsize=8)
    fig.suptitle('Frozen decoder/WL PEX: local-interface measurements\n'
                 'Fixed stimulus and 3.8 ns settling allowance; experimental screens, not approved access margins')
    output=args.campaign/'matrix_metrics.png';fig.savefig(output,dpi=160);plt.close(fig)
    provenance['plots'][output.name]=dict(sha256=sha(output))
    (args.campaign/'plots.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(f'Exported {len(provenance["plots"])} measured figures.')


if __name__=='__main__':
    main()
