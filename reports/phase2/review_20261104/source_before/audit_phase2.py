#!/usr/bin/env python3
"""Reconcile selected Phase 2 checkpoints against raw artifacts and live inputs.

This approves only the explicitly tested experimental 4x8 scope, never RC/PVT
characterization or advisor/foundry signoff.
"""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import numpy as np
from run_digital_regression import atomic_text,output_lock
from run_phase2_digital import ROOT,LIB,sha
from phase2_access_checks import check as protocol_check
from phase2_routed_graph import audit as graph_audit


def location(value):
    if value.startswith('/work/'):p=ROOT/value[6:]
    else:
        p=Path(value)
        if not p.is_absolute():p=ROOT/p
    if not p.exists() and p.is_relative_to(ROOT/'build/phase2'):
        proof=json.loads((ROOT/'reports/phase2/portable_raw/results.json').read_text())
        entry=proof.get('archived_build_inputs',{}).get(str(p.relative_to(ROOT)))
        if proof['status']=='PASS_LOSSLESS_RAW' and entry:
            candidate=ROOT/entry['path']
            if not candidate.is_relative_to(ROOT/'reports/phase2/portable_raw') or sha(candidate)!=entry['sha256']:
                raise ValueError('Portable build input mismatch')
            return candidate
    return p


def verify_hashes(entries):
    for path,expected in entries.items():
        if sha(location(path))!=expected:raise ValueError('Changed/missing evidence input: '+path)


def unique_lvs(path):
    text=path.read_text()
    if 'Final result: Circuits match uniquely.' not in text or re.search(r'(?i)property errors|do not match|black.box|placeholder|failed to open',text):
        raise ValueError('Unqualified LVS transcript: '+str(path))


def negative_lvs(text,kind):
    if re.search(r'(?i)failed to open|placeholder|black.box',text):raise ValueError('Invalid LVS negative run')
    if kind=='gate':
        if 'Final result: Netlists do not match.' not in text or 'INJECTED_GATE' not in text:
            raise ValueError('LVS gate negative lacks the intended mismatch')
    elif kind=='width':
        # Netgen reports structural uniqueness even with W/L mismatches.
        # Rejection must come from the actual parameter diagnostic, not from
        # requiring an unrelated topology failure.
        cells=re.search(r'The following cells had property errors:\s*(.*?)\s*$',text,re.S)
        widths=re.findall(r'W circuit1:\s*([\d.eE+-]+)\s+circuit2:\s*([\d.eE+-]+)',text)
        if (not cells or cells[1].strip()!='pilot_flat' or len(widths)!=1
                or abs(float(widths[0][0])/float(widths[0][1])-1.2)>1e-8
                or 'Property errors were found.' not in text):
            raise ValueError('LVS width negative lacks the intended 20-percent parameter mismatch')
    else:raise ValueError('Unknown LVS negative')


def electrical(source):
    state=json.loads((source/'results.json').read_text())
    if state['status']!='PASS_EXTRACTED_NOMINAL_ACCESS' or state['quick']:
        raise ValueError('Complete final-extracted electrical campaign has not passed')
    verify_hashes(state['inputs']);verify_hashes(state['model_inputs'])
    for name,expected in state['artifacts'].items():
        if sha(source/name)!=expected:raise ValueError('Changed electrical artifact: '+name)
    build=ROOT/state['build_directory'];wave=build/'waveform.dat'
    if wave.is_file():
        wave_hash=sha(wave)
        data=np.loadtxt(wave,skiprows=1)
    else:
        portable=ROOT/'reports/phase2/portable_raw';proof=json.loads((portable/'results.json').read_text())
        wave=portable/'waveform.dat.gz'
        if (proof['status']!='PASS_LOSSLESS_RAW' or proof['source_receipt_sha256']!=sha(source/'results.json')
                or sha(wave)!=proof['compressed_sha256']):raise ValueError('Portable raw evidence mismatch')
        digest=hashlib.sha256()
        with gzip.open(wave,'rb') as stream:
            while chunk:=stream.read(1024*1024):digest.update(chunk)
        wave_hash=digest.hexdigest()
        data=np.loadtxt(wave,skiprows=1)
    if wave_hash!=state['raw_waveform_sha256']:raise ValueError('Changed electrical raw waveform')
    cycles=state['cycles'];vectors=state['vectors']
    if len(cycles)!=35 or len(data)<100 or data[-1,0]<709e-9:raise ValueError('Incomplete transient/cycles')
    rows=list(csv.DictReader((source/'checks.csv').open()))
    read_cycles=[c for c in cycles if c['operation']=='read']
    expected_keys={(c['cycle'],b) for c in read_cycles for b in range(8)}
    observed={(int(r['cycle']),int(r['bit'])) for r in rows}
    if len(rows)!=128 or len(observed)!=len(rows) or observed!=expected_keys:raise ValueError('Incomplete/duplicate read CSV coverage')
    by_cycle={c['cycle']:c for c in cycles}
    for row in rows:
        rec=by_cycle[int(row['cycle'])];bit=int(row['bit']);index=np.searchsorted(data[:,0],rec['sample_ns']*1e-9)
        for key,expected_metadata in rec.items():
            observed_metadata=row[key] if isinstance(expected_metadata,str) else float(row[key])
            if observed_metadata!=expected_metadata:raise ValueError('Read CSV metadata differs from recorded stimulus')
        value=float(data[index,bit+1]);expected=(rec['expected']>>bit)&1
        if abs(value-float(row['voltage_v']))>1e-12:raise ValueError('Read CSV differs from raw trace')
        valid=1.44<=value<=1.98 if expected else -.18<=value<=.36
        if not valid or row['status']!='PASS':raise ValueError('Raw electrical read failed')
    checks,ref=protocol_check(data,cycles,vectors,state['capture_inputs'],state['capture_clocks'])
    for rec in cycles:
        if not rec['operation'].startswith('inactive'):continue
        for offset,invert in ((1,False),(8,True)):
            index=np.searchsorted(data[:,0],(rec['rise_ns']+offset)*1e-9)
            for bit in range(8):
                expected=((rec['expected']^(255 if invert else 0))>>bit)&1;v=float(data[index,bit+1])
                checks.append(dict(kind='bus_release_1kohm_probe',cycle=rec['cycle'],bit=bit,voltage_v=v,status='PASS' if abs(v-expected*1.8)<=.05 else 'FAIL'))
    saved=json.loads((source/'protocol.json').read_text())
    if checks!=saved['checks'] or ref!=saved['capture_reference']:raise ValueError('Protocol receipt differs from raw reanalysis')
    if any(c['status']!='PASS' for c in checks):raise ValueError('Raw electrical protocol failed')
    if state['read_checks']!=len(rows) or state['read_failures'] or state['protocol_checks']!=len(checks) or state['protocol_failures']:
        raise ValueError('Electrical summary counters do not reconcile')
    verify_hashes({ref['path']:ref['sha256']})
    return {'read_checks':len(rows),'protocol_checks':len(checks),'condition':state['condition'],
            'waveform_sha256':wave_hash,'startup':'Ramp plus two inactive cycles; no internal IC; minimum/statistical startup not characterized'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',default='reports/phase2/acceptance')
    a=p.parse_args();out=(ROOT/a.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2') or out==ROOT/'reports/phase2':p.error('Output under reports/phase2 required')
    out.mkdir(parents=True,exist_ok=True)
    with output_lock(out):
        result={'status':'RUNNING','F2_DIG':'NOT_EVALUATED','CORE':'NOT_EVALUATED','F2_FIS':'NOT_EVALUATED',
                'scope':'Experimental 4x8 integration acceptance; no R-C/PVT/Fmax/reliability qualification',
                'checks':[]}
        def publish():atomic_text(out/'results.json',json.dumps(result,indent=2)+'\n')
        publish()
        try:
            selector=ROOT/'physical/phase2/checkpoints.json';paths=json.loads(selector.read_text())
            folders={k:ROOT/v for k,v in paths.items() if k not in ('schema_version','scope','phase1_selection')}
            receipts={k:json.loads((d/'results.json').read_text()) for k,d in folders.items()}
            result['receipt_sha256']={k:sha(d/'results.json') for k,d in folders.items()}
            d=receipts['digital']
            if d['status']!='PASS' or d['F2_DIG']!='PASS_FUNCTIONAL_MAPPING_GLS':raise ValueError('Digital checkpoint not approved')
            verify_hashes(d['inputs']);verify_hashes(d['pdk'])
            raw=re.findall(r'^RESULT (\{.*\})$',(folders['digital']/'wrapper_gls.txt').read_text(),re.M)
            if len(raw)!=1 or json.loads(raw[0])!=d['gls_result']:raise ValueError('Digital GLS raw result mismatch')
            for name,h in d['artifacts'].items():
                if sha(folders['digital']/name)!=h:raise ValueError('Digital evidence changed')
            result['F2_DIG']='PASS_FUNCTIONAL_MAPPING_GLS'
            result['checks'].append({'name':'mapped_digital_and_raw_gls','status':'PASS','checks':d['gls_result']['checks']})
            verified=json.loads((folders['rtl_regression']/'verification_checks.json').read_text())
            if receipts['rtl_regression']['status']!='PASS' or verified['status']!='PASS':raise ValueError('RTL/evidence verification incomplete')
            result['checks'].append({'name':'rtl_evidence_verification','status':'PASS','python_tests':verified['python_tests_passed']})
            for key,expected in [('physical_pilot','PASS'),('fabric','PASS_LEAF_FABRIC'),('binding','PASS_MAPPING_ONLY'),
                                 ('route','ROUTED_VERIFICATION_PENDING'),('integrated_layout','LAYOUT_MATCH_REIMPORT_PENDING'),
                                 ('final_gds','PASS_GEOMETRY_LVS'),('routed_gls','PASS_FUNCTIONAL_ROUTED_GLS'),
                                 ('top_abstract','PASS_GEOMETRY_ABSTRACT')]:
                r=receipts[key]
                if r['status']!=expected:raise ValueError('Checkpoint incomplete: '+key)
                if 'inputs' in r:verify_hashes(r['inputs'])
                for name,h in r.get('artifacts',{}).items():
                    if sha(folders[key]/name)!=h:raise ValueError('Checkpoint artifact changed: '+key+'/'+name)
            for key,prefix in [('physical_pilot','PILOT'),('fabric','FABRIC'),('integrated_layout','INTEGRATED')]:
                text=(folders[key]/'magic.txt').read_text()
                if re.findall(r'^'+prefix+r'_DRC=(\d+)$',text,re.M)!=['0']:raise ValueError('DRC raw transcript mismatch: '+key)
                unique_lvs(folders[key]/'lvs.txt')
            for key,prefix in [('physical_pilot','REIMPORT'),('fabric','REIMPORT'),('final_gds','FINAL_GDS')]:
                logfile='magic.txt' if key=='final_gds' else 'reimport_magic.txt'
                if re.findall(r'^'+prefix+r'_DRC=(\d+)$',(folders[key]/logfile).read_text(),re.M)!=['0']:raise ValueError('GDS reimport DRC incomplete')
                unique_lvs(folders[key]/('lvs.txt' if key=='final_gds' else 'reimport_lvs.txt'))
            pilot=receipts['physical_pilot']
            if pilot['negative_controls']!={'gate':'REJECTED','width':'REJECTED'}:raise ValueError('Pilot LVS negative controls incomplete')
            for name in ('gate','width'):
                negative_lvs((folders['physical_pilot']/('negative_'+name+'.txt')).read_text(),name)
            route=folders['route']
            if 'PHASE2_ROUTING_DONE' not in (route/'openroad.txt').read_text() or (route/'route_drc.rpt').read_text().strip():raise ValueError('Detailed route incomplete or DRC report nonempty')
            layout=folders['integrated_layout'];build=ROOT/receipts['integrated_layout']['build_directory']
            route_build=ROOT/receipts['route']['build_directory']
            if sha(location(str(route_build/'binding.v')))!=sha(folders['binding']/'binding.v'):raise ValueError('Route used a different binding')
            graph_build=Path(tempfile.mkdtemp(prefix='graph-audit-',dir=ROOT/'build/phase2'))
            script=f'''read_liberty -lib {LIB}
read_verilog {ROOT}/physical/phase2/macro_binding.v {folders['binding']}/binding.v
hierarchy -check -top sram_4x8_wrapper
write_json {graph_build}/original_named.json
'''
            r=subprocess.run(['yosys','-Q','-T','-p',script],text=True,capture_output=True,timeout=90)
            atomic_text(out/'graph_yosys.txt',r.stdout+r.stderr)
            if r.returncode:raise ValueError('Cannot independently elaborate routed graph source')
            proof=graph_audit(json.loads((graph_build/'original_named.json').read_text()),json.loads(location(str(build/'routed_reference.json')).read_text()))
            atomic_text(out/'graph_preservation.json',json.dumps(proof,indent=2)+'\n')
            result['checks'].append({'name':'routed_binding_preservation',**proof})
            for key,child in [('final_gds','integrated_layout'),('routed_gls','integrated_layout')]:
                r=receipts[key]
                expected=r.get('layout_receipt_sha256',r.get('inputs',{}).get(str(folders[child]/'results.json')))
                if expected!=sha(folders[child]/'results.json'):raise ValueError('Mixed layout/checkpoint identities')
            if sha(folders['final_gds']/'sram_4x8.gds')!=sha(layout/'sram_4x8.gds'):raise ValueError('Delivered GDS mismatch')
            if (receipts['top_abstract']['source_gds_sha256']!=sha(folders['final_gds']/'sram_4x8.gds')
                    or receipts['top_abstract']['actual_metal_rectangles_checked']!=46):
                raise ValueError('Top LEF does not cover every delivered GDS pin/PG port')
            if sha(folders['routed_gls']/'gls.txt')!=receipts['routed_gls']['artifacts']['gls.txt']:raise ValueError('Routed GLS raw log mismatch')
            raw=re.findall(r'^RESULT (\{.*\})$',(folders['routed_gls']/'gls.txt').read_text(),re.M)
            if len(raw)!=1 or json.loads(raw[0])!=receipts['routed_gls']['coverage']:raise ValueError('Routed GLS coverage mismatch')
            result['checks'].append({'name':'delivered_geometry_and_routed_gls','status':'PASS','mos':receipts['final_gds']['mos']})
            measured=electrical(folders['extracted_access'])
            result['checks'].append({'name':'final_extracted_electrical_raw_reconciliation','status':'PASS',**measured})
            guard_path=ROOT/'reports/phase2/evidence_guards/results.json'
            guards=json.loads(guard_path.read_text())
            if (guards['status']!='PASS_4_TAMPERS_REJECTED' or len(guards['guards'])!=4
                    or guards['source_receipt_sha256']!=sha(folders['extracted_access']/'results.json')
                    or guards['checker_sha256']!=sha(__file__)):
                raise ValueError('Final electrical evidence negatives incomplete/stale')
            result['checks'].append({'name':'raw_evidence_corruption_guards','status':'PASS','rejected':4})
            preserve=subprocess.run(['python3',ROOT/'tools/verify_phase1_handoff.py'],capture_output=True,text=True,timeout=180)
            atomic_text(out/'phase1_preservation.txt',preserve.stdout+preserve.stderr)
            if preserve.returncode:raise ValueError('Frozen Phase 1 preservation failed')
            result.update(status='PASS_EXPERIMENTAL_4X8',CORE='PASS_INTEGRATED_NOMINAL',F2_FIS='PASS_EXPERIMENTAL_4X8',
                          remaining=['Advisor review of experimental acceptance and open timing criteria',
                                     'Detailed interconnect R-C PEX and PVT/statistical characterization',
                                     'Fmax/Liberty characterization and Phase 1 model/reliability limitations remain open'])
        except Exception as e:result.update(status='FAIL_OR_INCOMPLETE',error=str(e))
        result['artifacts']={s.name:sha(s) for s in out.iterdir() if s.is_file() and s.name not in ('results.json','.run.lock')}
        publish();print(json.dumps(result,indent=2))
        return 0 if result['status']=='PASS_EXPERIMENTAL_4X8' else 1


if __name__=='__main__':raise SystemExit(main())
