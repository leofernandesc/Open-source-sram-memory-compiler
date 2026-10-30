#!/usr/bin/env python3
"""Independently reconcile new measurements with their pinned sources."""
import argparse
import csv
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import freeze_keeper_revision as frozen
require=frozen.ensure


def load(path):return json.loads(path.read_text())


def table(path):
    with path.open() as stream:return list(csv.DictReader(stream))


def matrix(rows,state):
    indexed={(r['corner'],float(r['vdd_v']),float(r['temp_c']),int(r[state])):r for r in rows}
    expected={(c,v,t,s) for c in ('tt','ss','ff','sf','fs') for v in (1.62,1.8) for t in (-40,27,125) for s in (0,1)}
    require(len(indexed)==len(rows)==60 and set(indexed)==expected,'Incomplete/duplicated G7 matrix')
    require(all(r['status']=='PASS' and r['returncode']=='0' for r in rows),'G7 case failed')
    require(len({r['cache_contract_sha256'] for r in rows})==1,'Mixed simulation contracts')
    return indexed


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--suite',type=Path,required=True);p.add_argument('--decoder',type=Path,required=True)
    p.add_argument('--boundary',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--smoke-retry',type=Path,
        help='Separately recorded retry of a source-smoke CLI compatibility failure.')
    args=p.parse_args();suite=args.suite.resolve();decoder=args.decoder.resolve();boundary=args.boundary.resolve()
    require(not args.output.exists(),'Preserve previous reviews')
    audit=frozen.check();manifest=load(ROOT/'release/phase1_keeper/manifest.json')
    run=load(suite/'manifest.json')
    require(run['complete'],'Reconciliation incomplete')
    failures=[r for r in run['commands'] if r['status']!='PASS']
    if failures:
        require(args.smoke_retry is not None and len(failures)==1 and failures[0]['label']=='source_smoke'
                and failures[0]['returncode']==2,'Unexpected suite failure')
        console=(suite/'source_smoke_console.txt').read_text()
        require('unrecognized arguments: --blocks' in console,'Not the recorded CLI compatibility failure')
    else:require(run['status']=='PASS','Reconciliation did not pass')
    for path,digest in run['artifact_sha256'].items():require(frozen.sha(suite/path)==digest,'Changed suite evidence: '+path)
    require(len(run['physical'])==6,'Missing fresh physical checks')
    for proof in run['physical']:
        item=manifest['cells'][proof['cell']]
        require(proof['status']=='PASS' and proof['mos_count']==item['expected_mos'] and proof['drc_groups']==0
                and proof['lvs']=='UNIQUE_MATCH_WITH_W_L_AND_TERMINALS','Physical requalification failed')
        require(proof['negative_controls']==dict.fromkeys(('width','length','gate','bulk','model'),'REJECTED_AS_EXPECTED'),
                'Missing physical negative controls')
        for kind,key in [('layout','layout_sha256'),('pex','pex_sha256'),('spice','source_sha256')]:
            require(proof[key]==item['files'][kind]['sha256'],'Wrong physical source: '+proof['cell'])
    electrical={}
    for mode,state in [('read','stored_q'),('write','stored_q_before')]:
        rows=table(suite/f'g7_{mode}.csv');indexed=matrix(rows,state)
        names={'bitcell':'bitcell_6t','precharge':'precharge','wl_driver':'wl_driver',
               'sense':'sense_amp'} if mode=='read' else {
               'bitcell':'bitcell_6t','precharge':'precharge','wl_driver':'wl_driver','write_driver':'write_driver'}
        for row in rows:
            for field,leaf in names.items():
                require(row[field+'_source_sha256']==manifest['cells'][leaf]['files']['pex']['sha256'],
                        'G7 used an unselected PEX: '+field)
        filename='g7_read_requal_latch_t0_20261008.csv' if mode=='read' else 'g7_write_requal_casewise_wlsetup1p2ns_20261008.csv'
        baseline=table(ROOT/'release/phase1/electrical'/filename)
        old={(r['corner'],float(r['vdd_v']),float(r['temp_c']),int(r[state])):r for r in baseline}
        metrics=(['delta_at_sclk_v','t_res_from_sclk50_ns','read_disturb_peak_v','precharge_recovery_ns'] if mode=='read'
                 else ['full_flip_from_wl50_ns','wl_margin_30pct_ns','precharge_recovery_ns'])
        comparison={}
        for metric in metrics:
            # A missing historical diagnostic is unknown, never an assumed zero.
            a=[float(r[metric]) for r in baseline if r[metric]!=''];b=[float(r[metric]) for r in rows]
            require(all(math.isfinite(v) for v in a+b),'Missing/nonfinite G7 metric: '+metric)
            paired=[k for k in indexed if old[k][metric]!='']
            comparison[metric]=dict(old_min=min(a),old_max=max(a),new_min=min(b),new_max=max(b),
                historical_missing=60-len(a),compared_pairs=len(paired),
                max_abs_pair_difference=max(abs(float(indexed[k][metric])-float(old[k][metric])) for k in paired))
        if mode=='write':
            require(all(v['max_abs_pair_difference']<=.002 for v in comparison.values()),
                    'Write reproduction changed by more than the 2 ps numerical comparison tolerance')
        electrical[mode]=dict(cases=60,metrics=comparison,
            comparison_scope='New explicit 3 ns WL input; historical CSV lacks the complete pulse contract. Not a matched timing claim.' if mode=='read'
                else 'Recorded historical load, WE=2.2 ns, WL_IN=3.4 ns/1 ns; numerical comparison tolerance 2 ps.')
    smoke_path=suite/'source_smoke.csv'
    if args.smoke_retry:
        retry=args.smoke_retry.resolve();receipt=load(retry/'manifest.json')
        smoke_path=retry/'source_smoke.csv'
        require(receipt['status']=='PASS' and receipt['returncode']==0 and frozen.sha(smoke_path)==receipt['csv_sha256'],
                'Source-smoke retry failed or changed')
        require(frozen.sha(retry/'executed_script.py')==receipt['runner_sha256'],'Changed smoke runner snapshot')
        for path,digest in receipt['source_sha256'].items():require(frozen.sha(ROOT/path)==digest,'Source-smoke input changed')
    smoke=table(smoke_path)
    require(len(smoke)==12 and all(r['status']=='PASS' for r in smoke),'Source-path smoke failed')
    fresh=load(decoder/'manifest.json')
    require(fresh['complete'] and fresh['status']=='PASS_EXPERIMENTAL_SCREEN' and len(fresh['cases'])==48,'Decoder incomplete')
    original={}
    for profile in ('tt','ss','ff'):
        directory=ROOT/f'sims/row_decoder/results/keeper_pex_functional_{profile}_20261029'
        campaign=load(directory/'manifest.json')
        require(campaign['models']==fresh['models'] and campaign['inputs']==fresh['inputs'],'Decoder models/PEX changed')
        for row in campaign['cases']:original[(row['profile'],row['old'],row['new'])]=row
    require({(r['profile'],r['old'],r['new']) for r in fresh['cases']}==set(original),'Decoder address matrix differs')
    checks=0;deltas=[]
    for row in fresh['cases']:
        folder=decoder/row['case'];old=original[(row['profile'],row['old'],row['new'])]
        require(frozen.sha(folder/'case.spice')==row['deck_sha256']==old['deck_sha256'],'Decoder stimulus/circuit differs')
        checks+=frozen.check_case(folder,row,True)
        deltas.append(abs(row['wl90_delay_ps']-old['wl90_delay_ps']))
    require(checks==1392 and max(deltas)<=1,'Decoder reproduction changed beyond 1 ps comparison tolerance')
    cli=load(boundary/'cli_results.json')
    require(len(cli)==2 and [r['returncode'] for r in cli]==[2,0] and all(r['complete'] for r in cli),
            'Mandatory/expected-boundary exit codes were not verified')
    require([r['status'] for r in cli]==['FAIL_EXPERIMENTAL_SCREEN','MEASURED_BOUNDARY'],'Boundary labels incorrect')
    result=dict(status='PASS',scope='PHASE1_REPOSITORY_RECONCILIATION_NOT_FULL_MACRO',
        frozen_audit=audit,fresh_physical_cells=6,physical_negative_controls_rejected=30,
        g7=electrical,source_path_smoke_cases=12,
        decoder=dict(cases=48,checks=checks,max_abs_wl90_difference_ps=max(deltas),identical_decks_and_models=True),
        boundary_cli=cli,new_rc_extraction=False,
        recorded_cli_compatibility_failure_preserved=bool(failures),
        source_smoke_sha256=frozen.sha(smoke_path),
        suite_manifest_sha256=frozen.sha(suite/'manifest.json'),decoder_manifest_sha256=frozen.sha(decoder/'manifest.json'),
        reviewer_sha256=frozen.sha(Path(__file__)))
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
