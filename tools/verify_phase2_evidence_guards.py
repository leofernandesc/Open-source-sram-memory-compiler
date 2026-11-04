#!/usr/bin/env python3
"""Prove that final electrical acceptance rejects plausible corrupted receipts."""
import csv
import argparse
import json
from pathlib import Path
import shutil
import tempfile
from audit_phase2 import electrical
from run_phase2_digital import ROOT,sha
from run_digital_regression import atomic_text,output_lock


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='reports/phase2/review_20261104/evidence_guards')
    args=parser.parse_args()
    selector=json.loads((ROOT/'physical/phase2/checkpoints.json').read_text())
    source=ROOT/selector['extracted_access'];out=(ROOT/args.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2') or out==ROOT/'reports/phase2':parser.error('Output under reports/phase2 required')
    out.mkdir(parents=True,exist_ok=True)
    with output_lock(out):
        result={'status':'RUNNING','scope':'Receipt corruption negatives against real electrical raw data; original evidence untouched','guards':[]}
        def publish():atomic_text(out/'results.json',json.dumps(result,indent=2)+'\n')
        publish()
        try:
            identity=sha(source/'results.json');baseline=electrical(source)
            state=json.loads((source/'results.json').read_text())
            build=Path(tempfile.mkdtemp(prefix='evidence-guards-',dir=ROOT/'build/phase2'))
            result.update(source_receipt_sha256=identity,baseline=baseline,build_directory=str(build.relative_to(ROOT)),
                          checker_sha256=sha(ROOT/'tools/audit_phase2.py'),
                          validator_inputs={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'tools/phase2_evidence.py',Path(__file__))})
            for kind,diagnostic in [('missing_read','Incomplete/duplicate read CSV coverage'),
                                    ('plausible_voltage','Read CSV differs from raw trace'),
                                    ('forged_protocol','Protocol receipt differs from raw reanalysis'),
                                    ('forged_counter','Electrical summary counters do not reconcile'),
                                    ('csv_nan','Nonfinite numeric evidence: CSV voltage_v'),
                                    ('missing_inventory','Missing mandatory evidence inventory'),
                                    ('post_run_netlist','Simulation input differs from pre-run identity: binding.spice'),
                                    ('missing_capture','Missing mandatory output capture probes'),
                                    ('wrong_condition','Electrical condition differs from the declared TT experiment'),
                                    ('wrong_probes','Probe metadata differs from the executed SPICE fixture')]:
                fixture=build/kind;fixture.mkdir()
                for name in state['artifacts']:shutil.copyfile(source/name,fixture/name)
                mutated=json.loads(json.dumps(state))
                if kind in ('missing_read','plausible_voltage','csv_nan'):
                    with (fixture/'checks.csv').open() as f:reader=csv.DictReader(f);rows=list(reader);fields=reader.fieldnames
                    if kind=='missing_read':rows.pop();mutated['read_checks']=len(rows)
                    else:rows[0]['voltage_v']='nan' if kind=='csv_nan' else str(float(rows[0]['voltage_v'])+.01)
                    with (fixture/'checks.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
                    mutated['artifacts']['checks.csv']=sha(fixture/'checks.csv')
                elif kind=='forged_protocol':
                    protocol=json.loads((fixture/'protocol.json').read_text());protocol['checks'][0]['status']='FAIL'
                    (fixture/'protocol.json').write_text(json.dumps(protocol)+'\n')
                    mutated['artifacts']['protocol.json']=sha(fixture/'protocol.json')
                elif kind=='missing_inventory':mutated['artifacts']={}
                elif kind=='missing_capture':mutated['capture_inputs']=[]
                elif kind=='wrong_condition':mutated['condition']['corner']='ss'
                elif kind=='wrong_probes':mutated['vectors'][0]='v(incorrect_node)'
                elif kind=='post_run_netlist':
                    (fixture/'binding.spice').write_text((fixture/'binding.spice').read_text().replace('w=0.42','w=4.2',1))
                    mutated['artifacts']['binding.spice']=sha(fixture/'binding.spice')
                else:mutated['read_checks']+=1
                (fixture/'results.json').write_text(json.dumps(mutated)+'\n')
                try:electrical(fixture)
                except ValueError as error:
                    if str(error)!=diagnostic:raise ValueError('Negative rejected for the wrong reason: '+kind+': '+str(error))
                    result['guards'].append({'mutation':kind,'status':'REJECTED','diagnostic':str(error)})
                else:raise ValueError('Evidence guard missed corruption: '+kind)
            if sha(source/'results.json')!=identity:raise ValueError('Original electrical receipt changed')
            for name,expected in state['artifacts'].items():
                if sha(source/name)!=expected:raise ValueError('Original evidence changed during guard tests')
            result['status']='PASS_EVIDENCE_GUARDS'
        except Exception as error:result.update(status='FAIL',error=str(error))
        publish();print(json.dumps(result,indent=2))
        return 0 if result['status']=='PASS_EVIDENCE_GUARDS' else 1


if __name__=='__main__':raise SystemExit(main())
