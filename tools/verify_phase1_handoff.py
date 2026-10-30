#!/usr/bin/env python3
"""Audit the six-leaf handoff without changing either frozen delivery.

This checks stored evidence; it does not execute ngspice, DRC, LVS or PEX.
The legacy audit is run against a temporary copy because its original entry
point writes reports. A recorded owner disposition never overrides a failed
technical check or claims independent off-state model accuracy.
"""
import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import re
import shutil
import tempfile
import audit_phase1_release as legacy
import freeze_keeper_revision as current

ROOT=Path(__file__).resolve().parents[1]
DECISION=ROOT/'release/phase1_handoff_20261029/decision.json'


def require(condition,message):
    if not condition:raise ValueError(message)


def validate_decision(decision):
    require(decision['scope']=='PHASE1_SIX_LEAF_ENGINEERING_HANDOFF','Wrong handoff scope')
    require(decision['selected_manifest']=='release/phase1_keeper/manifest.json','Wrong selected revision')
    require(decision['model_coverage_disposition']=='DOCUMENTED_NON_BLOCKING_FOR_PHASE1' and
        decision['model_provider_response_required_for_this_handoff'] is False,'Owner disposition missing')
    require(decision['independent_off_state_model_accuracy']=='NOT_ESTABLISHED','Model limitation was erased')
    require(decision['local_reference_status']=='MEASURED_LEAF_HANDOFF_REFERENCE_ONLY','Macro timing was implicitly approved')
    require(decision['local_reference']==dict(pclk_low_ns=3,pclk_high_ns=2.5,external_address_lead_ns=2.1,
        ramps_ps=50,wl_load_ff=102.873935496,selected_high_dwell_screen_ns=.25,reset_dwell_screen_ns=.1,
        internal_literal_guard_ps=250,low_high_level_screens_vdd_fraction=[.1,.9],terminal_magnitude_screen_v=1.95),
        'Local reference differs from the qualified experimental campaign')


def audit():
    decision=json.loads(DECISION.read_text());validate_decision(decision)
    active=current.check()
    # The legacy verifier rechecks upstream Git objects, physical report/pin
    # bindings, all negative controls and the 129 archived electrical rows.
    # Its writes stay in a disposable copy, never release/phase1/ itself.
    with tempfile.TemporaryDirectory(prefix='.phase1-evidence-audit-',dir=ROOT) as scratch:
        destination=Path(scratch)/'baseline';shutil.copytree(ROOT/'release/phase1',destination)
        saved=legacy.DEST;stream=io.StringIO()
        try:
            legacy.DEST=destination
            with redirect_stdout(stream):legacy.main()
            baseline=json.loads((destination/'verification/release_audit.json').read_text())
        finally:legacy.DEST=saved
    manifest=json.loads((ROOT/decision['selected_manifest']).read_text());cells=[]
    for name,item in manifest['cells'].items():
        proof=json.loads((ROOT/item['physical_result']).read_text())
        require(proof['status']=='PASS' and proof['mos_count']==item['expected_mos'] and proof['drc_groups']==0 and
            proof['lvs']=='UNIQUE_MATCH_WITH_W_L_AND_TERMINALS','Invalid physical result: '+name)
        require(proof['negative_controls']==dict.fromkeys(('width','length','gate','bulk','model'),'REJECTED_AS_EXPECTED'),
            'Missing negative controls: '+name)
        for kind,key in [('schematic',None),('spice','source_sha256'),('symbol','symbol_sha256'),
                         ('layout','layout_sha256'),('pex','pex_sha256')]:
            info=item['files'][kind]
            require(current.sha(ROOT/info['path'])==info['sha256'],'Changed delivered file: '+name+'/'+kind)
            if key:require(proof[key]==info['sha256'],'Physical binding differs: '+name+'/'+kind)
        pins=re.findall(r'^B 5 .*?\{name=(\S+)\s+dir=',(ROOT/item['files']['symbol']['path']).read_text(),re.M)
        require(pins==proof['pins'],'Symbol pin order differs: '+name)
        cells.append(dict(cell=name,mos=proof['mos_count'],drc_groups=0,
            lvs=proof['lvs'],negative_controls_rejected=5,pex_binding=proof['pex_connectivity_binding'],
            evidence=item['physical_result'],evidence_sha256=current.sha(ROOT/item['physical_result'])))
    require(len(cells)==6,'Expected six selected cells')
    review=json.loads((ROOT/manifest['electrical_review']).read_text())
    active_after=current.check()
    require(active==active_after,'Audit changed the selected delivery')
    return dict(status='PASS',stage='READY_FOR_TEAM_REVIEW',scope=decision['scope'],
        audit_kind='READ_ONLY_STORED_EVIDENCE_CHECK',checked_utc=datetime.now(timezone.utc).isoformat(),
        disposition=decision['model_coverage_disposition'],decision_sha256=current.sha(DECISION),
        verifier_sha256=current.sha(Path(__file__)),
        helper_sha256={name:current.sha(ROOT/'tools'/name) for name in
            ('freeze_keeper_revision.py','audit_phase1_release.py','prepare_phase1_release.py')},
        active_manifest=dict(path=decision['selected_manifest'],sha256=current.sha(ROOT/decision['selected_manifest'])),
        active_index_sha256=current.sha(ROOT/'release/phase1_keeper/checksums.json'),
        historical_index_sha256=current.sha(ROOT/'release/phase1/checksums.json'),
        indexed_artifacts=active['indexed_files'],cells=cells,
        decoder=dict(mandatory_runs=review['mandatory_post_layout_cases'],passing_checks=review['mandatory_checks'],
            address_cases=review['functional_cases'],crossed_pvt_points=review['crossed_pvt_points'],
            deliberate_charge_boundary_failures=review['boundary_failures'],signed_gate_findings_retained=True),
        archived_legacy_electrical_rows=sum(r['cases'] for r in baseline['electrical']),
        archived_electrical_scope='Original G7 campaign; supports its five unchanged leaf inputs. Not a 33-MOS decoder macro test.',
        limits=decision['claims_not_granted'],new_simulation=False,new_physical_checks=False,new_rc_extraction=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.output:
        for frozen in (ROOT/'release/phase1',ROOT/'release/phase1_keeper'):
            require(not args.output.resolve().is_relative_to(frozen),'Do not write into a frozen delivery')
    try:result=audit()
    except Exception as error:
        result=dict(status='FAIL',error=f'{type(error).__name__}: {error}')
    text=json.dumps(result,indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        # Replace a previous PASS on failure; preserve no stale success receipt.
        with tempfile.NamedTemporaryFile(mode='w',dir=args.output.parent,delete=False) as handle:
            handle.write(text);temporary=Path(handle.name)
        temporary.replace(args.output)
    print(text,end='')
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
