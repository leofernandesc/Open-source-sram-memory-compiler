#!/usr/bin/env python3
"""Recheck local raw probes and export a bounded, reproducible model-domain review."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np

import run_canonical_intrinsic_bias as probe
pair=probe.pair


def rows(path):
    with path.open() as handle:return list(csv.DictReader(handle))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaigns',nargs='+',type=Path,required=True)
    parser.add_argument('--sensitivity-campaigns',nargs='*',type=Path,default=[])
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    cases=[];all_rows=[];events=[];sources={};metadata={};raws={}
    model_hashes=None
    for directory in args.campaigns:
        directory=directory.resolve()
        path=directory/'manifest.json';m=json.loads(path.read_text())
        pair.require(m['complete'] and m['errors']==0,'Incomplete intrinsic campaign')
        pair.require(pair.sha(directory/'executed_script.py')==m['runner_sha256'],'Changed runner snapshot')
        for name,digest in m['helper_sha256'].items():
            pair.require(pair.sha(directory/'helper_snapshots'/name)==digest,'Changed helper snapshot')
        if model_hashes is None:
            model_hashes=m['models']
            for name,digest in model_hashes.items():pair.require(pair.sha(Path(name))==digest,'Native model changed')
        else:pair.require(model_hashes==m['models'],'Probe campaigns use different models')
        sources[str(path.relative_to(pair.ROOT))]=pair.sha(path)
        pair.require(len(m['probes'])==45,'Wrong intrinsic-device coverage')
        expected={(p,a,b,init) for p in m['profiles'] for a,b in m['transitions'] for init in m['initializations']}
        observed={(r['profile'],r['old'],r['new'],r['initialization']) for r in m['cases']}
        pair.require(expected==observed and len(m['cases'])==len(expected),'Missing or duplicate requested case')
        for case in m['cases']:
            key=(case['profile'],case['old'],case['new'],case['initialization'])
            pair.require(key not in metadata,'Overlapping review cases')
            folder=directory/case['case'];rawpath=folder/'waveform.raw'
            pair.require(case['status']=='MEASURED' and pair.sha(rawpath)==case['raw_sha256'],'Missing/changed raw probe')
            pair.require(pair.sha(folder/'case.spice')==case['deck_sha256'],'Changed native deck')
            pair.require(json.loads((folder/'result.json').read_text())==case,'Result/manifest mismatch')
            for leaf in m['inputs'].values():pair.require(pair.sha(pair.ROOT/leaf['path'])==leaf['sha256'],'Changed PEX')
            raw=pair.read_raw(rawpath)
            _,terminals=probe.timing.make_deck(pair.release_inputs(),case['profile'],case['old'],case['new'],
                                              m['step_ps'],m['row_load']['measured_max_ff'],m['schedule'])
            measured,peaks,magnitudes,windows=probe.measure(raw,terminals,m['probes'],m['schedule'])
            for filename,actual in [('signed_bias.csv',measured),('intrinsic_magnitudes.csv',magnitudes),
                                    ('events.csv',peaks),('event_windows.csv',windows)]:
                if not actual:continue
                retained=rows(folder/filename)
                pair.require(retained==[{k:str(v) for k,v in r.items()} for r in actual],f'Raw/CSV mismatch: {filename}')
            if case['initialization']=='uic':
                match=probe.compare_reference(raw,case['profile'],case['old'],case['new'],m['schedule'],m['step_ps'])
                pair.require(match['saved_plot_samples_bitwise_equal'] and match==case['reference'],'UIC reference changed')
            functional,checks,_=probe.timing.analyze(raw,case['profile'],case['old'],case['new'],terminals,m['schedule'],250)
            functional.pop('literal_settling')
            pair.require(functional==case['functional'] and not functional['checks_fail'],'Functional recheck failed')
            all_rows.extend(dict(case=case['case'],profile=case['profile'],initialization=case['initialization'],**r) for r in measured)
            events.extend(dict(case=case['case'],profile=case['profile'],initialization=case['initialization'],**r) for r in peaks)
            cases.append(case);metadata[key]=(directory,m,terminals);raws[key]=raw
    pair.require(len(cases)==18,'Expected 18 focused probes (three profiles, two transitions, three initializations)')
    sensitivity=[];sensitivity_details=[]
    for directory in args.sensitivity_campaigns:
        directory=directory.resolve();path=directory/'manifest.json';m=json.loads(path.read_text())
        pair.require(m['complete'] and m['errors']==0 and m['models']==model_hashes,'Invalid sensitivity/model input')
        pair.require(pair.sha(directory/'executed_script.py')==m['runner_sha256'],'Changed sensitivity runner snapshot')
        sources[str(path.relative_to(pair.ROOT))]=pair.sha(path)
        for case in m['cases']:
            key=(case['profile'],case['old'],case['new'],'op')
            nominal_dir,nominal_meta,terminals=metadata[key]
            pair.require(case['initialization']=='op' and m['schedule']==nominal_meta['schedule']
                         and m['inputs']==nominal_meta['inputs'] and m['probes']==nominal_meta['probes']
                         and m['step_ps']==nominal_meta['step_ps'],'Sensitivity has unmatched circuit/schedule')
            folder=directory/case['case'];rawpath=folder/'waveform.raw'
            pair.require(case['status']=='MEASURED' and pair.sha(rawpath)==case['raw_sha256'],'Changed sensitivity raw')
            pair.require(pair.sha(folder/'case.spice')==case['deck_sha256'],'Changed sensitivity deck')
            raw=pair.read_raw(rawpath)
            measured,_,_,_=probe.measure(raw,terminals,m['probes'],m['schedule'])
            pair.require(rows(folder/'signed_bias.csv')==[{k:str(v) for k,v in r.items()} for r in measured],
                         'Sensitivity raw/CSV mismatch')
            nominal=next(c for c in cases if (c['profile'],c['old'],c['new'],c['initialization'])==key)
            original={(r['device'],r['metric']):r for r in all_rows if r['case']==nominal['case'] and r['window']=='after_2ns'}
            details=[]
            for r in measured:
                if r['window']!='after_2ns':continue
                previous=original[(r['device'],r['metric'])]
                details.append(dict(case=case['case'],device=r['device'],metric=r['metric'],
                    nominal_r_ohm=nominal_meta['dc_anchor_ohm'],sensitivity_r_ohm=m['dc_anchor_ohm'],
                    min_delta_v=r['intrinsic_min_v']-previous['intrinsic_min_v'],
                    max_delta_v=r['intrinsic_max_v']-previous['intrinsic_max_v']))
            sensitivity_details.extend(details)
            functional,checks,_=probe.timing.analyze(raw,case['profile'],case['old'],case['new'],terminals,m['schedule'],250)
            functional.pop('literal_settling')
            pair.require(functional==case['functional'] and not functional['checks_fail'],'Sensitivity functional recheck failed')
            sensitivity.append(dict(case=case['case'],nominal_r_ohm=nominal_meta['dc_anchor_ohm'],sensitivity_r_ohm=m['dc_anchor_ohm'],
                max_signed_extremum_change_v=max(max(abs(r['min_delta_v']),abs(r['max_delta_v'])) for r in details),
                wl90_delay_change_ps=functional['wl90_delay_ps']-nominal['functional']['wl90_delay_ps'],
                functional_checks=case['functional']['checks_pass'],max_dc_anchor_current_a=case['dc_anchor_peak_current_a']))
    if sensitivity_details:pair.write_csv(out/'dc_anchor_sensitivity.csv',sensitivity_details)
    frozen=json.loads((pair.RELEASE/'checksums.json').read_text())
    for path,digest in frozen.items():
        pair.require(pair.sha(pair.ROOT/path)==digest,'Frozen physical package changed')
    summary=[]
    for profile in ('tt','ss','ff'):
        for initialization in ('uic','anchored_uic','op'):
            for window in ('full_transient','after_2ns'):
                for kind in ('n','p'):
                    for metric in ('VGS','VDS','VBS'):
                        subset=[r for r in all_rows if (r['profile'],r['initialization'],r['window'],r['kind'],r['metric'])
                                ==(profile,initialization,window,kind,metric)]
                        worst_min=min(subset,key=lambda r:r['intrinsic_min_v']);worst_max=max(subset,key=lambda r:r['intrinsic_max_v'])
                        summary.append(dict(profile=profile,initialization=initialization,window=window,kind=kind,metric=metric,
                            intrinsic_min_v=worst_min['intrinsic_min_v'],intrinsic_max_v=worst_max['intrinsic_max_v'],
                            worst_min_case=worst_min['case'],worst_min_device=worst_min['device'],
                            worst_max_case=worst_max['case'],worst_max_device=worst_max['device'],
                            max_external_intrinsic_difference_v=max(r['max_external_intrinsic_difference_v'] for r in subset),
                            outside_device_metrics=sum(r['status']=='OUTSIDE_PUBLISHED_RANGE' for r in subset)))
    pair.write_csv(out/'summary.csv',summary)
    pair.write_csv(out/'events.csv',events)
    # All curves compare the same device/transition across the three initial conditions.
    fig,axes=plt.subplots(2,3,figsize=(13,7),layout='constrained');plot_rows=[]
    for column,profile in enumerate(('tt','ss','ff')):
        for row_index,(kind,side) in enumerate((('n','lower'),('p','upper'))):
            candidates=[e for e in events if e['profile']==profile and e['initialization']=='op'
                        and (e['kind'],e['metric'],e['side'])==(kind,'VGS',side)]
            event=max(candidates,key=lambda e:e['excursion_v'])
            reference=next(c for c in cases if c['case']==event['case']);label=event['device']
            axis=axes[row_index,column]
            for initialization,style in [('uic','--'),('anchored_uic',':'),('op','-')]:
                key=(profile,reference['old'],reference['new'],initialization);raw=raws[key]
                _,m,terminals=metadata[key];q=m['probes'][label]['queries']
                states={name:probe.state_trace(raw,query) for name,query in q.items()}
                signal=probe.oriented_states(kind,states['vgs'],states['vds'],states['vbs'])['VGS']
                mask=(raw['time']>=2e-9)&(raw['time']<=20e-9)
                if kind=='p':mask&=np.abs(raw['time']-event['time_ns']*1e-9)<=0.25e-9
                indices=np.flatnonzero(mask)
                if len(indices)>1000:indices=indices[np.linspace(0,len(indices)-1,1000).astype(int)]
                axis.plot(raw['time'][indices]*1e9,signal[indices],style,label=initialization)
                plot_rows.extend(dict(profile=profile,initialization=initialization,device=label,kind=kind,
                    old=reference['old'],new=reference['new'],time_ns=float(raw['time'][i]*1e9),vgs_intrinsic_v=float(signal[i])) for i in indices)
            axis.axhline(0,color='firebrick',lw=1)
            axis.set(title=f'{profile.upper()} {reference["old"]}:{reference["new"]}, {label}',
                     xlabel='Time (ns)',ylabel='Signed intrinsic VGS (V)')
            axis.grid(alpha=0.25);axis.legend(fontsize=8)
    fig.suptitle('Measured VGS findings after 2 ns, on the same device in each initialization\n'
                 'NMOS below zero / PMOS above zero lie outside the published signed-range screen',fontsize=12)
    fig.savefig(out/'intrinsic_vgs_initialization.png',dpi=150,bbox_inches='tight');plt.close(fig)
    pair.write_csv(out/'plotted_vgs.csv',plot_rows)
    fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    for axis,window in zip(axes,('full_transient','after_2ns')):
        for offset,initialization in enumerate(('uic','anchored_uic','op')):
            data=[next(r['intrinsic_min_v'] for r in summary if (r['profile'],r['initialization'],r['window'],r['kind'],r['metric'])
                       ==(p,initialization,window,'p','VBS')) for p in ('tt','ss','ff')]
            axis.bar(np.arange(3)+(offset-1)*0.24,data,0.24,label=initialization)
        axis.axhline(-0.1,color='firebrick',ls='--',label='Published -0.10 V screen')
        axis.set(xticks=range(3),xticklabels=['TT','SS','FF'],ylabel='Minimum intrinsic PFET VBS (V)',title=window)
        axis.grid(axis='y',alpha=0.25);axis.legend(fontsize=8)
    fig.suptitle('Separate forced-startup excursions from post-startup body bias',fontsize=12)
    fig.savefig(out/'intrinsic_vbs_startup.png',dpi=150,bbox_inches='tight');plt.close(fig)
    columns=[(p,i) for p in ('tt','ss','ff') for i in ('uic','anchored_uic','op')]
    metrics=[(k,v) for k in ('n','p') for v in ('VGS','VDS','VBS')]
    values=np.array([[next(r['outside_device_metrics'] for r in summary if
        (r['profile'],r['initialization'],r['window'],r['kind'],r['metric'])==(p,i,'after_2ns',k,v))
        for p,i in columns] for k,v in metrics])
    fig,axis=plt.subplots(figsize=(12,5),layout='constrained')
    axis.imshow(values>0,aspect='auto',vmin=0,vmax=1,cmap=ListedColormap(['#4d9368','#c85c4e']))
    for a in range(6):
        for b in range(9):axis.text(b,a,'OUT' if values[a,b] else 'IN',ha='center',va='center',color='white')
    axis.set_yticks(range(6),[f'{k.upper()}FET {v}' for k,v in metrics])
    axis.set_xticks(range(9),[p.upper()+'\n'+i.replace('anchored_uic','UIC+R').upper() for p,i in columns])
    axis.set_title('Published signed-range screen after 2 ns\nTwo transitions per profile; IN is a measured screen, not model or reliability signoff',fontsize=12)
    fig.savefig(out/'intrinsic_domain_screen.png',dpi=150,bbox_inches='tight');plt.close(fig)
    outside=any(r['status']=='OUTSIDE_PUBLISHED_RANGE' for r in all_rows if r['window']=='after_2ns')
    result=dict(status='MEASURED_REVIEW_REQUIRED' if outside else 'MEASURED_INSIDE_SCREEN',cases=len(cases),devices_per_case=45,
        device_cases=len(cases)*45,signed_metric_rows=len(all_rows),functional_checks=sum(c['functional']['checks_pass'] for c in cases),
        raw_sha_verified=True,retained_signed_csvs_reproduced=True,frozen_files_unchanged=len(frozen),
        native_model_hashes_verified=True,sensitivity=sensitivity,
        uic_reference_cases=sum(c['reference'] is not None for c in cases),
        uic_saved_plot_samples_all_bitwise_equal=all(c['reference']['saved_plot_samples_bitwise_equal'] for c in cases if c['reference']),
        max_intrinsic_magnitude_v=max(c['max_intrinsic_magnitude_v'] for c in cases),
        raw_storage='Ignored local waveform.raw files; hashes are retained. Rerun --keep-raw before this review on another machine.',
        scope='18 focused probes, not an all-address or full PVT intrinsic qualification. Signed-range mapping is an engineering screen.',
        runner_sha256=pair.sha(Path(__file__)),inputs=sources,
        plots={p.name:pair.sha(p) for p in sorted(out.glob('*.png'))})
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
