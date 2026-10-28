#!/usr/bin/env python3
"""Export measured boundary maps and failing/passing address waveforms."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaigns',nargs='+',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    provenance=dict(script_sha256=sha(Path(__file__)),inputs={},plots={})
    campaigns={};confirmations=[]
    for directory in args.campaigns:
        path=directory/'manifest.json';manifest=json.loads(path.read_text())
        if not manifest['complete'] or manifest['errors']:
            raise ValueError(f'Incomplete/error campaign: {directory}')
        campaigns[manifest['axis']]=(directory,manifest)
        if manifest['axis']=='confirm':confirmations.append((directory,manifest))
        provenance['inputs'][str(directory)]=sha(path)
        if manifest['axis'] not in ('address','precharge'):continue
        rows=manifest['cases']
        keys=sorted({(r['profile'],r['old'],r['new']) for r in rows})
        values=sorted({r['value'] for r in rows})
        data=np.full((len(keys),len(values)),np.nan)
        for r in rows:data[keys.index((r['profile'],r['old'],r['new'])),values.index(r['value'])]=int(r['timing_screen']=='PASS')
        fig,axis=plt.subplots(figsize=(max(6,len(values)*1.4),max(3,len(keys)*0.5)),layout='constrained')
        axis.imshow(data,aspect='auto',vmin=0,vmax=1,cmap=ListedColormap(['#c85c4e','#4d9368']))
        for i in range(len(keys)):
            for j in range(len(values)):
                if np.isfinite(data[i,j]):axis.text(j,i,'PASS' if data[i,j] else 'FAIL',ha='center',va='center',color='white',fontsize=9)
        axis.set_yticks(range(len(keys)),[f'{p.upper()} {a}:{b}' for p,a,b in keys])
        labels=[f'{value:g}' for value in values]
        axis.set_xticks(range(len(values)),labels)
        axis.set_xlabel('Address center lead before PCLK50 (ps)' if manifest['axis']=='address' else
                        ('PCLK low duration (ns)' if manifest['axis']=='precharge' else 'Combined candidate'))
        axis.set_title(f'Frozen decoder/WL: {manifest["axis"]} timing screen\n'
                       'Fixed high90 dwell 0.25 ns; reset dwell 0.10 ns\n'
                       'Diagnostic limits; not an SRAM access guarantee',fontsize=11)
        target=args.output_dir/(manifest['axis']+'_screen.png');fig.savefig(target,dpi=160,bbox_inches='tight');plt.close(fig)
        provenance['plots'][target.name]=sha(target)
    if confirmations:
        groups={}
        for directory,manifest in confirmations:
            when=manifest['cases'][0]['schedule']
            key=tuple(when[k] for k in ('low_ns','high_ns','address_lead_ps'))
            groups.setdefault(key,[]).extend((directory,row) for row in manifest['cases'])
        profiles=sorted({r['profile'] for _,m in confirmations for r in m['cases']})
        measured={}
        for key,rows in groups.items():
            by_case={}
            for directory,row in rows:
                case_key=(row['profile'],row['old'],row['new'])
                if case_key in by_case:raise ValueError(f'Duplicate combined candidate case: {key}/{case_key}')
                path=directory/row['case']/'literal_settling.csv'
                provenance['inputs'][str(path)]=sha(path)
                with path.open() as handle:guard=min(float(r['stable_lead_ps']) for r in csv.DictReader(handle))
                by_case[case_key]=(row,guard)
            measured[key]=by_case
            fig,axes=plt.subplots(1,len(profiles),figsize=(4*len(profiles),4.5),squeeze=False,layout='constrained')
            cmap=ListedColormap(['#c85c4e','#4d9368']);cmap.set_bad('#dddddd')
            for column,profile in enumerate(profiles):
                axis=axes[0,column];data=np.full((4,4),np.nan)
                for (p,old,new),(row,guard) in by_case.items():
                    if p!=profile:continue
                    data[old,new]=int(row['timing_screen']=='PASS')
                    axis.text(new,old,f'{row["timing_screen"]}\n{guard:.0f} ps',ha='center',va='center',color='white',fontsize=9)
                axis.imshow(np.ma.masked_invalid(data),vmin=0,vmax=1,cmap=cmap)
                axis.set(xticks=range(4),yticks=range(4),xlabel='New address',ylabel='Old address',title=profile.upper())
            low,high,lead=key
            fig.suptitle(f'Combined timing screen: low {low:g} ns / high {high:g} ns / address lead {lead:g} ps\n'
                         'Cell: timing result and minimum internal-literal lead; gray = untested',fontsize=12)
            target=args.output_dir/f'confirm_{lead:g}ps_screen.png';fig.savefig(target,dpi=160,bbox_inches='tight');plt.close(fig)
            provenance['plots'][target.name]=sha(target)
        fig,axis=plt.subplots(figsize=(8,4),layout='constrained')
        width=0.8/len(groups)
        common=set.intersection(*(set(rows) for rows in measured.values()))
        for index,(key,rows) in enumerate(measured.items()):
            guards=[]
            for profile in profiles:
                values=[guard for case,(_,guard) in rows.items() if case in common and case[0]==profile]
                guards.append(min(values))
            lead=key[2]
            bars=axis.bar(np.arange(len(profiles))+(index-(len(groups)-1)/2)*width,
                          guards,width,label=f'Low {key[0]:g} ns / address lead {lead:g} ps')
            axis.bar_label(bars,fmt='%.0f',padding=3,fontsize=9)
        guards={m['requested']['literal_guard_ps'] for _,m in confirmations}
        for guard in guards:
            axis.axhline(guard,color='firebrick',ls='--',label=f'Experimental guard {guard:g} ps')
        axis.set_xticks(range(len(profiles)),[p.upper() for p in profiles])
        axis.set(ylabel='Minimum internal-literal stable lead (ps)',
                 title='Measured candidate margin before PCLK50\nMinimum across matched transitions and literal-terminal segments')
        axis.margins(y=0.2);axis.grid(axis='y',alpha=0.25);axis.legend(fontsize=8)
        target=args.output_dir/'candidate_literal_guards.png';fig.savefig(target,dpi=160,bbox_inches='tight');plt.close(fig)
        provenance['plots'][target.name]=sha(target)
    for axis_name in ('evaluation','retention'):
        if axis_name not in campaigns:continue
        _,manifest=campaigns[axis_name]
        fig,axis=plt.subplots(figsize=(8,4),layout='constrained')
        keys=sorted({(r['profile'],r['old'],r['new']) for r in manifest['cases']})
        for profile,old,new in keys:
            rows=sorted((r for r in manifest['cases'] if (r['profile'],r['old'],r['new'])==(profile,old,new)),key=lambda r:r['value'])
            axis.plot([r['value'] for r in rows],[r['selected_high90_dwell_ns'] for r in rows],
                      'o-',label=f'{profile.upper()} {old}:{new}')
        axis.axhline(0.25,color='firebrick',ls='--',label='Fixed high90 dwell screen')
        axis.set(xlabel='PCLK high duration (ns)',ylabel='Selected DEC/WL valid high90 duration (ns)',
                 title=f'Frozen decoder/WL: {axis_name} sweep')
        axis.grid(alpha=0.25);axis.legend(fontsize=8)
        target=args.output_dir/(axis_name+'_dwell.png');fig.savefig(target,dpi=160,bbox_inches='tight');plt.close(fig)
        provenance['plots'][target.name]=sha(target)
    if 'address' in campaigns:
        directory,manifest=campaigns['address']
        rows=[r for r in manifest['cases'] if r['profile']=='ss' and (r['old'],r['new'])==(1,2)]
        failing=sorted((r for r in rows if r['timing_screen']=='FAIL'),key=lambda r:r['value'])
        passing=sorted((r for r in rows if r['timing_screen']=='PASS'),key=lambda r:r['value'])
        if failing and passing:
            selected=[failing[0],passing[-1]]
            fig,axes=plt.subplots(2,2,figsize=(12,6),sharex=True,layout='constrained')
            for column,row in enumerate(selected):
                source=directory/row['case']/'waveforms.csv'
                provenance['inputs'][str(source)]=sha(source)
                with source.open() as handle:data=list(csv.DictReader(handle))
                def series(name):return np.array([float(x[name]) for x in data])
                time=series('time')*1e9
                for node in ('pclk','a0','a1'):axes[0,column].plot(time,series(f'v({node})'),label=node.upper())
                for index in range(4):axes[1,column].plot(time,series(f'v(wl{index})'),label=f'WL{index}')
                axes[0,column].set_title(f'Address lead {row["value"]:g} ps: {row["timing_screen"]}')
                for axis in axes[:,column]:
                    axis.axvspan(row['schedule']['rise_ns'],row['schedule']['fall_ns'],color='gray',alpha=0.1)
                    axis.set_xlim(14,25);axis.set_ylabel('Voltage (V)');axis.grid(alpha=0.25);axis.legend(fontsize=8,ncols=4)
                axes[1,column].set_xlabel('Time (ns)')
            fig.suptitle('SS, 1.62 V, -40 C: measured address 1 to 2\n'
                         'Insufficient address lead can discharge an additional dynamic row node')
            target=args.output_dir/'address_waveform_comparison.png';fig.savefig(target,dpi=160,bbox_inches='tight');plt.close(fig)
            provenance['plots'][target.name]=sha(target)
    (args.output_dir/'plots.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(f'Exported {len(provenance["plots"])} measured boundary figures.')


if __name__=='__main__':
    main()
