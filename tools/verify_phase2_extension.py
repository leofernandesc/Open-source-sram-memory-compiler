#!/usr/bin/env python3
"""Recompute new campaign evidence from native logs, stimulus and complete raw."""
import argparse
import json
import re
from pathlib import Path
import numpy as np
from run_phase2_digital import ROOT, sha
from run_phase2_startup_review import SOURCE, GDS, verify_pins
from phase2_extension import probes, deck, check


def verify_case(source):
    state = json.loads((source/'results.json').read_text())
    if state['status'] not in ('PASS', 'FAIL_ELECTRICAL_SCREEN') or state.get('error'):
        raise ValueError('Completed electrical scenario required')
    if state['condition'] != dict(corner='tt', vdd_v=1.8, temp_c=27):
        raise ValueError('Wrong experimental condition')
    baseline = json.loads((SOURCE/'results.json').read_text())
    design_path = ROOT/'reports/phase2/portable_raw/routed_reference.json'
    required = [SOURCE/n for n in ('binding.spice','fabric.spice','bench.spice','results.json')]
    required += [GDS/'final_extracted.spice', GDS/'final_flat.ext', design_path]
    required += [ROOT/'tools'/n for n in ('run_phase2_extension.py','phase2_extension.py',
                  'run_phase2_startup_review.py','run_phase2_directed_review.py',
                  'phase2_access_checks.py','phase2_resources.py')]
    if not set(map(str,required)).union(baseline['model_inputs']).issubset(state['inputs']):
        raise ValueError('Missing provenance input')
    verify_pins(state['inputs'])
    seal=json.loads((ROOT/'reports/phase2/review_20261104/acceptance/results.json').read_text())
    for path in required[:6]:
        if sha(path)!=seal['verified_files'][str(path.relative_to(ROOT))]:
            raise ValueError('Selected baseline changed')
    if any(state['inputs'].get(p)!=h for p,h in baseline['model_inputs'].items()):
        raise ValueError('PDK closure differs')
    original_design=[h for p,h in baseline['inputs'].items() if p.endswith('/routed_reference.json')]
    if original_design != [sha(design_path)]:raise ValueError('Routed design differs')
    vectors,extra=probes(baseline,json.loads(design_path.read_text()),state['campaign']=='bus')
    text,records,stop=deck(state['campaign'],state['pilot'],baseline,vectors)
    if (state['vectors']!=vectors or state['probes']!=extra or state['cycles']!=records
            or state['stop_ns']!=stop or (source/'bench.spice').read_text()!=text):
        raise ValueError('Declared stimulus or observations differ')
    mandatory={'bench.spice','binding.spice','fabric.spice','ngspice.txt','checks.json','waveform_excerpt.csv'}
    mandatory.update('source_snapshot/'+p.name for p in required if p.suffix=='.py')
    if not mandatory.issubset(state['artifacts']):raise ValueError('Missing mandatory artifact')
    for name,h in state['artifacts'].items():
        path=(source/name).resolve()
        if not path.is_relative_to(source.resolve()) or sha(path)!=h:
            raise ValueError('Changed campaign artifact: '+name)
    for path in required:
        if path.suffix=='.py' and sha(source/'source_snapshot'/path.name)!=sha(path):
            raise ValueError('Source snapshot differs')
    if set(state['simulation_inputs'])!={'bench.spice','binding.spice','fabric.spice'}:
        raise ValueError('Incomplete simulation inputs')
    build=(ROOT/state['build_directory']).resolve()
    if not build.is_relative_to((ROOT/'build/phase2').resolve()):raise ValueError('Unsafe raw path')
    for name,h in state['simulation_inputs'].items():
        if sha(source/name)!=h:raise ValueError('Simulation input differs')
    for name in ('binding.spice','fabric.spice'):
        if sha(source/name)!=sha(SOURCE/name):raise ValueError('DUT differs from selected circuit')
    log=(source/'ngspice.txt').read_text()
    if state['return_code']!=0 or 'ngspice-44.2 done' not in log:
        raise ValueError('Missing native successful simulator completion')
    raw=build/'waveform.dat'
    if sha(raw)!=state['raw_sha256']:raise ValueError('Raw changed')
    with raw.open() as f:
        if f.readline().split()!=['time',*vectors]:raise ValueError('Raw header differs')
    data=np.loadtxt(raw,skiprows=1)
    native_rows=re.findall(r'No\. of Data Rows\s*:\s*(\d+)',log)
    if len(native_rows)!=1 or int(native_rows[0])!=len(data):raise ValueError('Native data row count differs')
    checks,reference,metrics=check(data,records,vectors,extra,baseline,stop,state['campaign'])
    if json.loads((source/'checks.json').read_text())!=dict(checks=checks,capture_reference=reference):
        raise ValueError('Checks differ from complete raw reanalysis')
    failures=sum(c['status']=='FAIL' for c in checks)
    if (state['checks']!=len(checks) or state['failures']!=failures
            or state['metrics']!=metrics or state['rows']!=len(data)
            or state['status']!=('FAIL_ELECTRICAL_SCREEN' if failures else 'PASS')):
        raise ValueError('Counters/status differ from actual checks')
    verify_pins(state['inputs'])
    return dict(status=state['status'],checks=len(checks),failures=failures,
                read_bit_checks=metrics['read_bit_checks'],receipt_sha256=sha(source/'results.json'),
                raw_sha256=sha(raw),scope='Complete native raw reanalysis; not another circuit simulation')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sources',nargs='+',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();out=(ROOT/a.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2') or out.exists():p.error('Use a new report directory')
    out.mkdir(parents=True);result=dict(status='RUNNING',cases={})
    try:
        if len(a.sources)!=len(set(a.sources)):raise ValueError('Duplicate source')
        for source in a.sources:result['cases'][source]=verify_case(ROOT/source)
        result.update(status='PASS' if result['cases'] and all(r['status']=='PASS' for r in result['cases'].values()) else 'FAIL',
                      verifier_sha256=sha(Path(__file__)))
    except Exception as e:result.update(status='FAIL_OR_INCOMPLETE',error=str(e))
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
