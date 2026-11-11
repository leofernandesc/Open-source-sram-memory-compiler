#!/usr/bin/env python3
"""Nominal isolated qualification of the frozen final sense and WL driver.

Run inside tools/sram-eda. New output directory required. --verify reparses
preserved full transients and checks their receipts without invoking ngspice.
No circuit edits, initial conditions, extraction or PVT characterization.
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import numpy as np

from phase2_resources import preflight
from run_phase2_extracted_access import model_closure

ROOT = Path(__file__).resolve().parents[1]
PDK = Path('/opt/pdks/sky130A')
LIB = PDK / 'libs.tech/ngspice/sky130.lib.spice'
EXPECTED = {
    'sense_amp': ('52f80d154ddddef14438fdb6196fac8adb78ad67cc3173a461c66710616e5147',
                  'ab60dc3ccfdcd7430ed169db89b6285757f3c035ffe94ec0d5774ecb3f56b653'),
    'wl_driver': ('843808b94414be032d114590c2c6d9a787ed5b13ed1c26dd4eba4b9173d68bdd',
                  'c6d099c1c7db764b88eb357bcde0bba9b1a53de91466b912442e8c1a767935f6'),
}
CRITERIA = {
    'condition': {'corner': 'tt', 'vdd_v': 1.8, 'temperature_c': 27},
    'supply_ramp_ns': 1, 'input_edge_ps': 50, 'max_step_ps': 5,
    'low_max_v': .18, 'high_min_v': 1.62, 'absolute_bounds_v': [-.18, 1.98],
    'sense_sample_error_max_v': .01, 'sense_sample_signed_delta_fraction_min': .5,
    'sense_resolution_deadline_ns': 3,
    'wl_propagation_deadline_ns': 2,
    'note': 'Deadlines and rails are bench acceptance criteria, not qualified timing specifications.',
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write_json(p, value):
    p.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def identities():
    pointer = ROOT / 'release/phase1_current.json'
    manifest = ROOT / 'release/phase1_keeper/manifest.json'
    if 'release/phase1_keeper/manifest.json' not in pointer.read_text():
        raise ValueError('Official library selection changed')
    selection = json.loads(manifest.read_text())['cells']
    inputs = {str(p.relative_to(ROOT)): sha(p) for p in (pointer, manifest)}
    cells = {}
    for cell in EXPECTED:
        item = selection[cell]
        views = {}
        for key in ('schematic', 'spice', 'pex'):
            f = item['files'][key]
            path = ROOT / f['path']
            if sha(path) != f['sha256']:
                raise ValueError('Selected artifact hash mismatch: ' + str(path))
            inputs[f['path']] = sha(path)
            if key in ('spice', 'pex'):
                expected = EXPECTED[cell][key == 'pex']
                if sha(path) != expected:
                    raise ValueError('Unexpected final netlist: ' + str(path))
                text = path.read_text()
                headers = re.findall(r'^\.subckt\s+(\S+)\s+(.+)$', text, re.M | re.I)
                mos = [x for x in text.splitlines() if re.match(r'^X\S+ .*sky130_fd_pr__[np]fet_01v8\b', x)]
                if len(headers) != 1 or len(mos) != item['expected_mos']:
                    raise ValueError('Unexpected hierarchy or MOS count')
                name, ports = headers[0]
                if ports.split() != item['pin_order']:
                    raise ValueError('Unexpected formal port order')
                dimensions = []
                for line in mos:
                    width = float(re.search(r'\bw=([\d.]+)', line, re.I)[1])
                    length = float(re.search(r'\bl=([\d.]+)', line, re.I)[1])
                    dimensions.append({'instance': line.split()[0], 'w_um': width, 'l_um': length})
                actual = sorted(d['w_um'] for d in dimensions)
                wanted = sorted(float(v) for v in item['widths'].values())
                if any(abs(a-b) > (.0051 if key == 'pex' else 1e-8) for a,b in zip(actual,wanted)):
                    raise ValueError('Unexpected transistor widths')
                if any(d['l_um'] != .15 for d in dimensions):
                    raise ValueError('Unexpected transistor length')
                views[key] = dict(path=f['path'], sha256=sha(path), subckt=name,
                                  ports=ports.split(), mos=dimensions,
                                  resistors=sum(bool(re.match(r'^R\d+\b', x)) for x in text.splitlines()),
                                  capacitors=sum(bool(re.match(r'^C\d+\b', x)) for x in text.splitlines()))
        proof = ROOT / item['physical_result']
        inputs[item['physical_result']] = sha(proof)
        old = json.loads(proof.read_text())
        if old['source_sha256'] != views['spice']['sha256'] or old['pex_sha256'] != views['pex']['sha256']:
            raise ValueError('Physical identity binding mismatch')
        cells[cell] = dict(schematic=item['files']['schematic'], views=views,
                           physical_identity_record=item['physical_result'])
    return inputs, cells


def cases():
    result = []
    for view in ('spice', 'pex'):
        for delta in (5, 50, 200):
            for polarity in (1, -1):
                for cap in (2, 10):
                    result.append(dict(cell='sense_amp', view=view, delta_mv=delta,
                                       polarity=polarity, cap_ff=cap,
                                       id=f'sa_{view}_d{delta}_p{polarity:+}_c{cap}'))
        for cap in (20, 50, 103):
            result.append(dict(cell='wl_driver', view=view, cap_ff=cap,
                               id=f'wl_{view}_c{cap}'))
    return result


def deck(case, view):
    if case['cell'] == 'sense_amp':
        delta = case['delta_mv'] / 1000
        a, b = ((1.8, 1.8-delta) if case['polarity'] == 1 else (1.8-delta, 1.8))
        sources = (f'VBL BL 0 PWL(0 0 1n 1.8 3n 1.8 3.05n {a} 10n {a} 10.05n {b})\n'
                   f'VBLB BLB 0 PWL(0 0 1n 1.8 3n 1.8 3.05n {b} 10n {b} 10.05n {a})\n'
                   'VSCLK SCLK 0 PWL(0 0 5n 0 5.05n 1.8 9n 1.8 9.05n 0 13n 0 13.05n 1.8 17n 1.8 17.05n 0)\n'
                   f'CA SA_OUT 0 {case["cap_ff"]}f\nCB SA_OUTB 0 {case["cap_ff"]}f\n')
        vectors = ['v(VDD)', 'v(BL)', 'v(BLB)', 'v(SCLK)', 'v(SA_OUT)', 'v(SA_OUTB)']
        stop = 18
    else:
        sources = ('VIN WL_IN 0 PULSE(0 1.8 3n 50p 50p 4.95n 8n)\n'
                   f'CW WL 0 {case["cap_ff"]}f\n')
        vectors = ['v(VDD)', 'v(WL_IN)', 'v(WL)']
        stop = 20
    nodes = ['0' if x == 'VSS' else x for x in view['ports']]
    text = (f'* Final frozen {case["cell"]}: isolated {case["view"]}; {case["id"]}\n'
            f'.lib {LIB} tt\n.include dut.spice\n.temp 27\n'
            '.options method=gear reltol=1e-5 abstol=1e-13 vntol=1e-7\n'
            'VPOWER VDD 0 PWL(0 0 1n 1.8)\n'
            f'XDUT {" ".join(nodes)} {view["subckt"]}\n' + sources +
            '.control\nset num_threads=1\nset wr_singlescale\nset wr_vecnames\n'
            'set numdgt=12\n' + f'tran 5p {stop}n 0 5p\n'
            f'wrdata waveform.dat {" ".join(vectors)}\nquit\n.endc\n.end\n')
    if re.search(r'(?im)^\s*\.(ic|nodeset)\b|\buic\b', text):
        raise ValueError('Artificial initialization forbidden')
    return text, vectors, stop


def crossing(t, y, level, rising, start, end):
    indices = np.where((t[:-1] >= start) & (t[1:] <= end) &
                       ((y[:-1] < level) & (y[1:] >= level) if rising else
                        (y[:-1] > level) & (y[1:] <= level)))[0]
    if not len(indices):
        raise ValueError('Missing voltage crossing')
    i = indices[0]
    return float(t[i] + (level-y[i])*(t[i+1]-t[i])/(y[i+1]-y[i]))


def evaluate(case, data, stop):
    if (data.ndim != 2 or data.shape[1] != (7 if case['cell']=='sense_amp' else 4)
            or len(data) < 500 or not np.all(np.isfinite(data))
            or np.any(np.diff(data[:,0]) <= 0) or data[0,0] > 1e-10
            or data[-1,0] < stop*1e-9-1e-12):
        raise ValueError('Incomplete or invalid full transient')
    t = data[:,0]*1e9
    checks, metrics = [], []
    def add(name, ok, **details):
        checks.append(dict(name=name, status='PASS' if bool(ok) else 'FAIL', **details))
    def window(start, end):
        m = (t >= start) & (t <= end)
        if np.count_nonzero(m) < 10:
            raise ValueError('Missing observation window')
        return m
    def logic(y, bit):
        return ((y >= 1.62) & (y <= 1.98) if bit else (y >= -.18) & (y <= .18))
    add('nominal_supply_after_ramp', np.all(abs(data[window(2,stop),1]-1.8) < 1e-5))
    if case['cell'] == 'sense_amp':
        for event, edge in enumerate((5,13)):
            sign = case['polarity'] * (-1 if event else 1)
            m = window(edge-.5, edge-.2)
            bl, blb, clk, a, b = (data[:,i] for i in range(2,7))
            add(f'{event}_sample_clock_low', np.all(clk[m] <= .18))
            add(f'{event}_input_delta', np.all(abs(sign*(bl[m]-blb[m])-case['delta_mv']/1000) < 1e-5))
            error = float(max(abs(a[m]-bl[m]).max(), abs(b[m]-blb[m]).max()))
            sampled = float(np.min(sign*(a[m]-b[m])))
            add(f'{event}_sampling_tracks_inputs', error <= .01 and sampled >= .5*case['delta_mv']/1000,
                maximum_error_v=error, minimum_signed_delta_v=sampled)
            clk50 = crossing(t,clk,.9,True,edge-.1,edge+.2)
            valid = logic(a,sign==1) & logic(b,sign==-1)
            end = edge+3.8
            idx = np.where((t >= clk50) & (t <= end))[0]
            # Earliest sampled point whose suffix remains valid, not a single glitch.
            suffix = np.logical_and.accumulate(valid[idx][::-1])[::-1]
            resolved = float(t[idx[np.where(suffix)[0][0]]]-clk50) if np.any(suffix) else None
            final = window(edge+3,edge+3.5)
            add(f'{event}_regeneration_polarity_and_rails', np.all(valid[final]))
            add(f'{event}_resolution_deadline', resolved is not None and 0 <= resolved <= 3)
            add(f'{event}_regeneration_clock_high', np.all(clk[final] >= 1.62))
            metrics.append(dict(event=event, expected_sa_out=int(sign==1),
                                bl_v=float(bl[final][-1]), blb_v=float(blb[final][-1]),
                                sclk_v=float(clk[final][-1]), sa_out_v=float(a[final][-1]),
                                sa_outb_v=float(b[final][-1]), resolution_ns=resolved,
                                sample_error_v=error, sample_signed_delta_v=sampled))
    else:
        inp, out = data[:,2], data[:,3]
        for j,(lo,hi,bit) in enumerate(((2,2.5,0),(7,7.5,1),(10,10.5,0),(15,15.5,1),(19,19.5,0))):
            m=window(lo,hi)
            add(f'{j}_noninverting_settled_output', np.all(logic(out[m],bit)) and np.all(logic(inp[m],bit)),
                minimum_v=float(out[m].min()), maximum_v=float(out[m].max()), expected=bit)
        for j,(edge,rise) in enumerate(((3,True),(8,False),(11,True),(16,False))):
            ci = crossing(t,inp,.9,rise,edge-.1,edge+.2)
            co = crossing(t,out,.9,rise,edge-.1,edge+2)
            a = crossing(t,out,.18 if rise else 1.62,rise,edge-.1,edge+2)
            b = crossing(t,out,1.62 if rise else .18,rise,edge-.1,edge+2)
            add(f'{j}_propagation', 0 <= co-ci <= 2)
            add(f'{j}_slew', 0 < b-a <= 2)
            metrics.append(dict(event=j, direction='rise' if rise else 'fall',
                                propagation_ps=(co-ci)*1000, slew_10_90_ps=(b-a)*1000))
    return dict(status='PASS' if all(x['status']=='PASS' for x in checks) else 'FAIL',
                checks=checks, metrics=metrics)


def read_data(path):
    with gzip.open(path, 'rt') as f:
        return np.loadtxt(f, skiprows=1)


def negative_controls(case, data, stop):
    mutated = data.copy()
    if case['cell'] == 'sense_amp':
        mutated[:,[5,6]] = mutated[:,[6,5]]
        stable = data.copy(); stable[:,5:7] = 1.8
    else:
        mutated[:,3] = 1.8-mutated[:,3]
        stable = data.copy(); stable[:,3] = 1.8
    result={}
    for name,d in (('wrong_polarity',mutated),('stuck_high',stable)):
        try:
            result[name]=evaluate(case,d,stop)['status']=='FAIL'
        except ValueError as exc:
            if str(exc) != 'Missing voltage crossing':raise
            result[name]=True
    return result


def verify(out):
    result = json.loads((out/'results.json').read_text())
    if result['status'] != 'PASS' or result['criteria'] != CRITERIA or [x['case'] for x in result['cases']] != cases():
        raise ValueError('Incomplete campaign or changed criteria/case matrix')
    for path, digest in result['inputs'].items():
        if sha(ROOT/path) != digest:
            raise ValueError('Input changed: '+path)
    for path,digest in result['artifacts'].items():
        if sha(out/path) != digest:
            raise ValueError('Artifact changed: '+path)
    if json.loads((out/'criteria.json').read_text()) != dict(criteria=CRITERIA,cases=cases()):
        raise ValueError('Changed predeclared criteria')
    for path,digest in result['model_inputs'].items():
        if sha(path)!=digest:raise ValueError('PDK model changed: '+path)
    _,selected=identities()
    if selected!=result['identities']:raise ValueError('Selected cell identity changed')
    total = 0
    for item in result['cases']:
        folder=out/item['case']['id']
        view=selected[item['case']['cell']]['views'][item['case']['view']]
        expected_deck,vectors,stop=deck(item['case'],view)
        if sha(folder/'dut.spice')!=view['sha256'] or (folder/'bench.spice').read_text()!=expected_deck:
            raise ValueError('Executed netlist/deck differs from frozen identity or stimuli')
        if vectors!=item['vectors'] or stop!=item['stop_ns']:
            raise ValueError('Changed transient metadata')
        native=(folder/'ngspice.txt').read_text()
        if item['returncode'] != 0 or 'No. of Data Rows' not in native or re.search(r'(?im)^\s*(fatal|error):',native):
            raise ValueError('Native simulation did not complete')
        waveform=read_data(folder/'waveform.dat.gz')
        with gzip.open(folder/'waveform.dat.gz','rb') as f:payload=f.read()
        if hashlib.sha256(payload).hexdigest()!=item['uncompressed_waveform_sha256']:
            raise ValueError('Changed full transient')
        rows=re.findall(r'No\. of Data Rows\s*:\s*(\d+)',native)
        if rows!=[str(len(waveform))]:raise ValueError('Native log/transient row count mismatch')
        derived=evaluate(item['case'],waveform,item['stop_ns'])
        if derived != json.loads((folder/'checks.json').read_text()) or derived['status']!='PASS':
            raise ValueError('Full-transient checks disagree')
        if not all(negative_controls(item['case'],waveform,item['stop_ns']).values()):
            raise ValueError('Negative control accepted incorrect output')
        total += len(derived['checks'])
    if total != result['functional_checks']:
        raise ValueError('Altered aggregate check count')
    if result['case_failures']!=0:raise ValueError('Altered aggregate failure count')
    return dict(status='PASS',cases=len(result['cases']),functional_checks=total,
                note='Full waveform replay plus input/artifact hashes; not a new simulation')


def run(out):
    out.mkdir(parents=True,exist_ok=False)
    result={'status':'RUNNING','criteria':CRITERIA,'cases':[]}
    write_json(out/'results.json',result)
    try:
        result['resources']=preflight(ROOT)
        inputs,cells=identities()
        for p in (Path(__file__), ROOT/'tools/phase2_resources.py',
                  ROOT/'tools/run_phase2_extracted_access.py'):
            inputs[str(p.relative_to(ROOT))]=sha(p)
        result.update(inputs=inputs, identities=cells,
                      base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                      model_inputs=model_closure(LIB),
                      ngspice_version=subprocess.check_output(['ngspice','--version'],text=True),
                      command=sys.argv, python=sys.version, numpy=np.__version__)
        write_json(out/'criteria.json',dict(criteria=CRITERIA,cases=cases()))
        write_json(out/'results.json',result)
        for case in cases():
            preflight(ROOT)
            folder=out/case['id'];folder.mkdir()
            view=cells[case['cell']]['views'][case['view']]
            shutil.copyfile(ROOT/view['path'], folder/'dut.spice')
            text,vectors,stop=deck(case,view)
            (folder/'bench.spice').write_text(text)
            with (folder/'ngspice.txt').open('w') as log:
                proc=subprocess.run(['ngspice','-n','-b','bench.spice'],cwd=folder,
                                    stdout=log,stderr=subprocess.STDOUT,timeout=120,
                                    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1'))
            item=dict(case=case,returncode=proc.returncode,vectors=vectors,stop_ns=stop)
            result['cases'].append(item)
            raw=folder/'waveform.dat'
            if proc.returncode or not raw.exists():
                raise ValueError('Simulation execution failure: '+case['id'])
            # Entire original wrdata payload is retained losslessly, without decimation.
            payload=raw.read_bytes()
            with (folder/'waveform.dat.gz').open('wb') as f:
                with gzip.GzipFile(fileobj=f,mode='wb',mtime=0,filename='') as g:g.write(payload)
            raw.unlink()
            item['uncompressed_waveform_sha256']=hashlib.sha256(payload).hexdigest()
            data=read_data(folder/'waveform.dat.gz')
            checks=evaluate(case,data,stop)
            write_json(folder/'checks.json',checks)
            item.update(status=checks['status'],negative_controls=negative_controls(case,data,stop))
            print(case['id'],checks['status'],flush=True)
            write_json(out/'results.json',result)
        result['functional_checks']=sum(len(json.loads((out/x['case']['id']/'checks.json').read_text())['checks']) for x in result['cases'])
        result['case_failures']=sum(x['status']!='PASS' for x in result['cases'])
        result['status']='PASS' if not result['case_failures'] and all(all(x['negative_controls'].values()) for x in result['cases']) else 'FAIL'
        with (out/'metrics.csv').open('w') as f:
            fields=['id','cell','view','cap_ff','delta_mv','polarity','event','direction','expected_sa_out','bl_v','blb_v','sclk_v','sa_out_v','sa_outb_v','resolution_ns','sample_error_v','sample_signed_delta_v','propagation_ps','slew_10_90_ps']
            writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
            for item in result['cases']:
                c=item['case']
                for m in json.loads((out/c['id']/'checks.json').read_text())['metrics']:
                    writer.writerow(dict(c,**m))
        result['artifacts']={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='results.json'}
        # Ensure no selected inputs or PDK models changed during execution.
        for p,h in inputs.items():
            if sha(ROOT/p)!=h:raise ValueError('Input changed during campaign: '+p)
        for p,h in result['model_inputs'].items():
            if sha(p)!=h:raise ValueError('PDK changed during campaign: '+p)
    except Exception as exc:
        result.update(status='FAIL_EXECUTION',error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        write_json(out/'results.json',result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--verify',action='store_true')
    a=p.parse_args();out=a.output.resolve()
    if not out.is_relative_to(ROOT/'reports/phase1') or out==ROOT/'reports/phase1':
        p.error('Use a new output directory under reports/phase1')
    result=verify(out) if a.verify else run(out)
    print(json.dumps({k:v for k,v in result.items() if k in ('status','cases','functional_checks','case_failures') and k!='cases'}))
    if result['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
