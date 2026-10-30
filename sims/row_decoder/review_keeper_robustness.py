#!/usr/bin/env python3
"""Bind completed keeper studies, summarize real results and render evidence plots."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import run_keeper_pex as study
import audit_sky130_measurements as measured
pair=study.pair
ROOT=pair.ROOT
RESULTS=ROOT/'sims/row_decoder/results'


def read(path):
    with path.open() as handle:return list(csv.DictReader(handle))


def audit_campaign(folder,expected):
    path=folder/'manifest.json';m=json.loads(path.read_text())
    pair.require(m['complete'] and len(m['cases'])==expected,f'Incomplete {folder.name}')
    pair.require(pair.sha(folder/'executed_script.py')==m['runner_sha256'],'Runner snapshot differs')
    for name,digest in m.get('helper_sha256',{}).items():
        pair.require(pair.sha(folder/'helper_snapshots'/name)==digest,'Helper snapshot differs')
    for source,digest in m.get('models',{}).items():
        pair.require(pair.sha(Path(source))==digest,'Native model changed')
    for item in m['inputs'].values():
        pair.require(pair.sha(ROOT/item['path'])==item['sha256'],'Input PEX changed')
    for r in m['cases']:
        pair.require(r['status']=='MEASURED',f'Simulation error: {r}')
        directory=folder/r['case'];pair.require(pair.sha(directory/'case.spice')==r['deck_sha256'],'Deck changed')
        if 'physical_proof' in m:
            entry=m['physical_proof']
            pair.require(pair.sha(ROOT/entry['path'])==entry['sha256'],'Physical proof changed since simulation')
        checks=read(directory/'checks.csv')
        pair.require(len(checks)==29 and sum(x['status']=='FAIL' for x in checks)==r['checks_fail'],'Check/result mismatch')
        wave=read(directory/'waveforms.csv');time=np.array([float(x['time']) for x in wave])
        pair.require(np.isfinite(time).all() and np.all(np.diff(time)>0),'Invalid saved waveform')
        r['_folder']=str(directory.relative_to(ROOT));r['_campaign']=folder.name
    return m


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True)
    args=p.parse_args();out=args.output_dir;pair.require(not out.exists(),'Use a new directory')
    # Recheck every historical baseline byte and the independent new physical proof.
    inputs,proof=study.revision_inputs()
    dataset=ROOT/'sims/row_decoder/inputs/sky130_measured_20261029'
    dm=json.loads((dataset/'manifest.json').read_text());pair.require(dm['complete'] and dm['mdm_files']==208,'Incomplete independent data')
    for r in dm['files']:
        data=(dataset/'upstream'/r['path']).read_bytes()
        pair.require(measured.sha(data)==r['sha256'] and measured.git_blob_sha(data)==r['git_blob_sha'],'Measured source changed')
    queuepath=RESULTS/'keeper_campaign_queue_20261029.json';queue=json.loads(queuepath.read_text())
    pair.require(queue['complete'] and len(queue['cases'])==10,'Complementary campaigns incomplete')
    names={f'keeper_pex_functional_{s}_20261029':16 for s in ('tt','ss','ff')}
    names.update(keeper_pex_pilot_20261029=1,keeper_pex_leak_20261029=5)
    names.update({f'keeper_pex_{s}_20261029':n for s,n in
        [('pvt_1',9),('pvt_2',9),('pvt_3',9),('charge',5),('pullup',5),('retention',3),('op',3),('anchored_uic',3),('early_charge',5),('charge_boundary',5)]})
    campaigns={name:audit_campaign(RESULTS/name,n) for name,n in names.items()}
    for r in queue['cases']:
        pair.require(pair.sha(ROOT/r['manifest'])==r['manifest_sha256'],'Queued manifest changed')
    baseline=audit_campaign(RESULTS/'robustness_baseline_pvt_20261029',36)
    hybrid=audit_campaign(RESULTS/'robustness_keeper_pvt_20261029',36)
    skew=audit_campaign(RESULTS/'robustness_keeper_skew_20261029',24)
    boundary=[];normal=[]
    for name,m in campaigns.items():
        (boundary if 'charge_boundary' in name else normal).extend(m['cases'])
    pair.require(all(r['timing_screen']=='PASS' and r['voltage_screen']=='PASS' and r['max_intrinsic_magnitude_v']<=1.95
                     for r in normal),'Unexpected failure in mandatory experimental screens')
    functional=[r for name,m in campaigns.items() if '_functional_' in name for r in m['cases']]
    pvt=[r for r in functional if (r['old'],r['new'])==(1,2)]
    pvt +=[r for name,m in campaigns.items() if '_pvt_' in name for r in m['cases']]
    pair.require(len(pvt)==30 and len({r['profile'] for r in pvt})==30,'Crossed PVT coverage missing/duplicated')
    signed=[];magnitudes=[]
    for r in normal+boundary:
        directory=ROOT/r['_folder']
        signed.extend(dict(case=r['case'],campaign=r['_campaign'],**x) for x in read(directory/'signed_bias.csv') if x['window']=='after_2ns')
        magnitudes.extend(dict(case=r['case'],campaign=r['_campaign'],**x) for x in read(directory/'intrinsic_magnitudes.csv'))
    unexpected=[r for r in signed if 'charge_boundary' not in r['campaign'] and r['metric']!='VGS' and r['status']=='OUTSIDE_PUBLISHED_RANGE']
    boundary_signed=[r for r in signed if 'charge_boundary' in r['campaign'] and r['metric']!='VGS' and r['status']=='OUTSIDE_PUBLISHED_RANGE']
    pair.require(not unexpected,'New signed VDS/VBS issue requires engineering review')
    comparisons=[]
    for profile in ('tt','ss','ff'):
        original=next(r for r in baseline['cases'] if r['profile']==profile and r['value']==0)
        new=next(r for r in functional if r['profile']==profile and (r['old'],r['new'])==(1,2))
        comparisons.append(dict(profile=profile,old_wl90_ps=original['wl90_delay_ps'],new_wl90_ps=new['wl90_delay_ps'],
            delta_wl90_ps=new['wl90_delay_ps']-original['wl90_delay_ps'],
            delay_increase_pct=100*(new['wl90_delay_ps']/original['wl90_delay_ps']-1),
            old_core_energy_fj=original['core_supply_energy_fj'],new_core_energy_fj=new['core_supply_energy_fj'],
            energy_increase_pct=100*(new['core_supply_energy_fj']/original['core_supply_energy_fj']-1)))
    out.mkdir(parents=True);pair.write_csv(out/'matched_comparison.csv',comparisons)
    pair.write_csv(out/'crossed_pvt.csv',pvt);pair.write_csv(out/'post_layout_cases.csv',normal+boundary)
    pair.write_csv(out/'signed_bias.csv',signed)
    initialization=[]
    for profile in ('tt','ss','ff'):
        points={k:next(r for r in campaigns[f'keeper_pex_{k}_20261029']['cases'] if r['profile']==profile) for k in ('op','anchored_uic')}
        reference=read(ROOT/points['anchored_uic']['_folder']/'waveforms.csv')
        rt=np.array([float(r['time']) for r in reference])
        candidate=read(ROOT/points['op']['_folder']/'waveforms.csv');ct=np.array([float(r['time']) for r in candidate])
        # Adaptive grids differ. Use a stated interpolation comparison at the
        # saved samples after first full precharge; this is not a bitwise test.
        deltas={name:np.abs(np.interp(rt,ct,[float(r[name]) for r in candidate])-
            np.array([float(r[name]) for r in reference])) for name in reference[0] if name!='time'}
        name=max(deltas,key=lambda k:float(deltas[k][rt>=2e-9].max()))
        indices=np.flatnonzero(rt>=2e-9);peak=int(indices[np.argmax(deltas[name][indices])])
        delta=float(deltas[name][peak])
        initialization.append(dict(profile=profile,op_minus_anchored_uic_wl90_ps=points['op']['wl90_delay_ps']-points['anchored_uic']['wl90_delay_ps'],
            max_saved_waveform_interpolation_difference_v=delta,max_difference_node=name,max_difference_time_ns=float(rt[peak]*1e9),
            note='Different floating EVAL_GND startup states; priming and second-access checks pass. Saved-grid interpolation is not a full-raw equality test.'))
    pair.write_csv(out/'initialization_comparison.csv',initialization)
    summary=dict(status='PASS_PROJECT_SCREENS_WITH_MODEL_COVERAGE_LIMITATION',
        independent_measured_files=208,independent_measured_points=sum(v['rows'] for v in dm['coverage'].values()),
        physical_proof_sha256=pair.sha(proof),new_pex_sha256=inputs['row_decoder']['sha256'],
        functional_cases=len(functional),functional_checks=sum(r['checks_pass'] for r in functional),
        crossed_pvt_points=len(pvt),mandatory_post_layout_cases=len(normal),
        mandatory_checks=sum(r['checks_pass'] for r in normal),boundary_cases=len(boundary),
        boundary_failures=sum(r['timing_screen']=='FAIL' for r in boundary),
        worst_intrinsic_magnitude_v=max(r['max_intrinsic_magnitude_v'] for r in normal),
        min_selected_high90_dwell_ns=min(r['selected_high90_dwell_ns'] for r in normal),
        min_reset_dwell_ns=min(r['reset_dwell_ns'] for r in normal),
        max_wl90_delay_ps=max(r['wl90_delay_ps'] for r in functional+pvt),
        signed_vds_vbs_outside_after_2ns=len(unexpected),
        boundary_signed_vds_vbs_outside_after_2ns=len(boundary_signed),
        signed_gate_findings_remain=any(r['status']=='OUTSIDE_PUBLISHED_RANGE' for r in signed),
        effective_vgs_bounds_v={kind:dict(min=min(float(r['intrinsic_min_v']) for r in signed if r['kind']==kind and r['metric']=='VGS'),
            max=max(float(r['intrinsic_max_v']) for r in signed if r['kind']==kind and r['metric']=='VGS')) for kind in ('n','p')},
        original_no_fault_pass=sum(r['timing_screen']=='PASS' for r in baseline['cases'] if r['value']==0),
        original_10ua_fail=sum(r['timing_screen']=='FAIL' for r in baseline['cases'] if r['value']==10),
        hybrid_042_pass=sum(r['timing_screen']=='PASS' for r in hybrid['cases']+skew['cases']),
        comparison=comparisons,initialization=initialization,
        limitation='No independent validation of negative-NFET/positive-PFET gate-bias accuracy; no statistical mismatch/yield or foundry reliability signoff.',
        reviewer_sha256=pair.sha(Path(__file__)),campaigns={name:dict(path=str((RESULTS/name/'manifest.json').relative_to(ROOT)),
            sha256=pair.sha(RESULTS/name/'manifest.json')) for name in campaigns})
    render(out,dataset,campaigns,baseline,summary)
    summary['artifact_sha256']={p.name:pair.sha(p) for p in out.iterdir() if p.is_file()}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'executed_review.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({k:v for k,v in summary.items() if k not in ('campaigns','artifact_sha256')},indent=2))


def render(out,dataset,campaigns,baseline,summary):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    coverage=read(dataset/'file_coverage.csv')
    fig,ax=plt.subplots(figsize=(9,3.6))
    ax.axvspan(-1.95,0,color='#ef8f8f',alpha=.15);ax.axvspan(0,1.95,color='#6eacbc',alpha=.12)
    for y,kind,color in [(1,'n','#126b83'),(0,'p','#b34e38')]:
        group=[r for r in coverage if r['kind']==kind]
        lo=min(float(r['vgs_min_v']) for r in group);hi=max(float(r['vgs_max_v']) for r in group)
        ax.plot([lo,hi],[y,y],lw=12,color=color,solid_capstyle='butt')
        ax.text((lo+hi)/2,y+.15,f'{sum(int(r["rows"]) for r in group):,} measured points',ha='center')
    ax.set(yticks=[0,1],yticklabels=['PFET','NFET'],xlabel='Measured VGS (V)',ylim=(-.45,1.55),xlim=(-2,2),
        title='Pinned public measurements do not cover opposite-sign off-state VGS')
    ax.axvline(0,color='gray',lw=.8);fig.tight_layout();fig.savefig(out/'measured_gate_coverage.png',dpi=180);plt.close(fig)
    # True saved waveforms: same schedule, same 10 uA/node stress and same SS profile.
    old=next(r for r in baseline['cases'] if r['profile']=='ss' and r['value']==10)
    new=next(r for r in campaigns['keeper_pex_leak_20261029']['cases'] if r['profile']=='ss')
    fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True)
    for result,label,color in [(old,'29 MOS, original PEX','#b34e38'),(new,'33 MOS, new keeper PEX','#126b83')]:
        wave=read(ROOT/result['_folder']/'waveforms.csv');t=np.array([float(x['time'])*1e9 for x in wave])
        minimum=np.min([[float(x[f'v(xdec.n{r})']) for x in wave] for r in (0,1,3)],axis=0)
        peak=np.max([[float(x[f'v(dec{r})']) for x in wave] for r in (0,1,3)],axis=0)
        axes[0].plot(t,minimum,label=label,color=color);axes[1].plot(t,peak,label=label,color=color)
    axes[0].axhline(.9*1.62,color='gray',ls=':',label='0.9 VDD reference')
    axes[1].axhline(.1*1.62,color='gray',ls=':',label='unselected DEC screen')
    axes[0].set(ylabel='Lowest unselected N (V)',title='SS, 1.62 V, -40 C: EXTRA 10 uA pulled from each unselected row node')
    axes[1].set(ylabel='Highest unselected DEC (V)',xlabel='Time (ns)',xlim=(12.7,16))
    for ax in axes:ax.legend(loc='best');ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(out/'leakage_restoration.png',dpi=180);plt.close(fig)
    dc=read(RESULTS/'keeper_contention_20261029/curves.csv')
    fig,ax=plt.subplots(figsize=(9,4.6))
    for width in (0,.42,.84,1.25,3):
        group=[r for r in dc if r['profile']=='fs_1.62_125' and float(r['keeper_width_um'])==width]
        ax.plot([float(r['node_v']) for r in group],[float(r['net_discharge_ua']) for r in group],label=f'W={width:g} um')
    ax.axhline(0,color='black',lw=.8);ax.set(xlabel='Forced row-node voltage (V)',ylabel='Net current discharging selected node (uA)',
        title='Schematic DC sizing: too strong a keeper can prevent evaluation')
    ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(out/'keeper_discharge_tradeoff.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(9,5.7),sharex=True)
    for label,color,campaign in [('16 fC: passes','#126b83','charge'),('32 fC: boundary failure','#b34e38','charge_boundary')]:
        result=next(r for r in campaigns[f'keeper_pex_{campaign}_20261029']['cases'] if r['profile']=='ff')
        wave=read(ROOT/result['_folder']/'waveforms.csv');t=np.array([float(x['time'])*1e9 for x in wave])
        node=np.min([[float(x[f'v(xdec.n{r})']) for x in wave] for r in (0,1,3)],axis=0)
        dec=np.max([[float(x[f'v(dec{r})']) for x in wave] for r in (0,1,3)],axis=0)
        axes[0].plot(t,node,color=color,label=label);axes[1].plot(t,dec,color=color,label=label)
    axes[0].set(ylabel='Lowest unselected N (V)',title='Actual keeper PEX, FF: 100 ps charge-removal pulses, three nodes')
    axes[1].axhline(.18,color='gray',ls=':',label='unselected DEC screen')
    axes[1].set(ylabel='Highest unselected DEC (V)',xlabel='Time (ns)',xlim=(14.2,15.3))
    for ax in axes:ax.grid(alpha=.2);ax.legend(loc='best')
    fig.tight_layout();fig.savefig(out/'charge_boundary.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    x=np.arange(3);w=.35;compare=summary['comparison']
    for ax,oldkey,newkey,title,ylabel in [
        (axes[0],'old_wl90_ps','new_wl90_ps','Matched 1 -> 2 transition','WL90 delay (ps)'),
        (axes[1],'old_core_energy_fj','new_core_energy_fj','Core VDD energy; input sources excluded','Energy (fJ)')]:
        ax.bar(x-w/2,[r[oldkey] for r in compare],w,label='29 MOS PEX',color='#b34e38')
        ax.bar(x+w/2,[r[newkey] for r in compare],w,label='33 MOS PEX',color='#126b83')
        ax.set(xticks=x,xticklabels=['TT','SS','FF'],ylabel=ylabel,title=title);ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(out/'physical_cost_comparison.png',dpi=180);plt.close(fig)


if __name__=='__main__':main()
