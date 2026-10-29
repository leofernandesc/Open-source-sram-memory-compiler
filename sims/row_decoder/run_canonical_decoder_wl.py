#!/usr/bin/env python3
"""Screen the frozen decoder/WL PEX pair with controlled local address/PCLK.

This local leaf-interface campaign excludes capture registers, phase generation
and physical bitcell data access. Its windows/thresholds are experimental.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np
from plot_row_decoder_review import read_raw
from run_row_decoder_contract import model_dependencies, pwl
from run_row_decoder_capture_timing import crossing, load_wl_capacitance_evidence

ROOT=Path(__file__).resolve().parents[2]
RELEASE=ROOT/'release/phase1'
LOAD_CSV=ROOT/'sims/row_decoder/inputs/canonical_row_load_20261028.csv'
PROFILES={'tt':('tt',1.8,27),'ss':('ss',1.62,-40),'ff':('ff',1.8,125)}
NATIVE_MODEL=Path('/opt/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice')
RISE_NS,FALL_NS,ADDRESS_NS,STOP_NS=17.1,22.5,15.0,27.5
EDGE_PS=50.0
MAGNITUDE_SCREEN_V=1.95


def require(condition,message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def logical(text):
    return re.sub(r'\n\s*\+\s*',' ',text).splitlines()


def subcircuit(path):
    text='\n'.join(logical(path.read_text()))
    header=re.search(r'(?mi)^\.subckt\s+(\S+)\s+([^\n]+)',text)
    require(header is not None,f'Missing PEX subcircuit: {path}')
    devices=[line.split() for line in text.splitlines() if re.match(r'^X\S+\s',line,re.I)]
    return header[1],header[2].split(),devices


def instance(label,name,pins,nets):
    require(set(pins)==set(nets),f'{label}: port set differs: {pins} / {list(nets)}')
    return label+' '+' '.join(nets[pin] for pin in pins)+' '+name


def release_inputs(release=RELEASE):
    checksums=json.loads((release/'checksums.json').read_text())
    for path,expected in checksums.items():
        require(sha(ROOT/path)==expected,f'Release evidence changed: {path}')
    manifest=json.loads((release/'manifest.json').read_text())
    require(json.loads((release/'verification/release_audit.json').read_text())['status']=='PASS',
            'Frozen release audit is not PASS')
    selected={}
    for cell,count in [('row_decoder',29),('wl_driver',4)]:
        item=manifest['cells'][cell]
        for info in item['files'].values():
            require(sha(ROOT/info['path'])==info['sha256'],f'Changed {cell} input: {info["path"]}')
        path=ROOT/item['files']['pex']['path']
        name,pins,devices=subcircuit(path)
        require(len(devices)==count,f'{cell}: unexpected MOS count')
        text=path.read_text()
        require(re.search(r'^R\S+\s',text,re.M) and re.search(r'^C\S+\s',text,re.M),
                f'{cell}: expected distributed R and C')
        for line in logical(text):
            if re.match(r'^C\S+\s',line,re.I):
                require(not line.split()[3].startswith('-'),f'{cell}: negative capacitance')
        selected[cell]=dict(path=path,sha256=sha(path),subcircuit=name,pins=pins,devices=devices)
    return selected


def make_deck(inputs,profile,old,new,step_ps,cap_ff,decoder_mos=29):
    corner,vdd,temp=PROFILES[profile]
    require(0<=old<4 and 0<=new<4,'Address must be in 0..3')
    clock=pwl(0,[(c*1e-9-EDGE_PS*0.5e-12,c*1e-9+EDGE_PS*0.5e-12,v)
                 for c,v in [(5,vdd),(10,0),(RISE_NS,vdd),(FALL_NS,0)]],STOP_NS*1e-9)
    lines=[f'Frozen decoder/WL local interface: {profile} {old}->{new}',
           f'.lib "{NATIVE_MODEL}" {corner}',f'.temp {temp}',
           '.options method=gear reltol=1e-4 minbreak=1f chgtol=1e-18',
           f'VDD_SRC VDD 0 {vdd}',f'VPCLK PCLK 0 {clock}']
    for bit in range(2):
        oldbit,newbit=(old>>bit)&1,(new>>bit)&1
        ramp=[(ADDRESS_NS*1e-9-EDGE_PS*0.5e-12,ADDRESS_NS*1e-9+EDGE_PS*0.5e-12,newbit*vdd)]
        lines.append(f'VA{bit} A{bit} 0 '+pwl(oldbit*vdd,ramp,STOP_NS*1e-9))
    for info in inputs.values():
        lines.append(f'.include "{info["path"]}"')
    decoder=inputs['row_decoder'];driver=inputs['wl_driver']
    require(decoder_mos in (29,33) and len(decoder['devices'])==decoder_mos and len(driver['devices'])==4,
            'Expected explicit 29/33 decoder MOS count and four-MOS wordline driver')
    decoder_nets={pin:('0' if pin=='VSS' else pin) for pin in decoder['pins']}
    lines.append(instance('XDEC',decoder['subcircuit'],decoder['pins'],decoder_nets))
    terminals={}
    def register(prefix,info,nets):
        for device in info['devices']:
            require(len(device)>=6 and device[5] in ('sky130_fd_pr__nfet_01v8','sky130_fd_pr__pfet_01v8'),
                    f'Unsupported extracted MOS: {device}')
            terminals[prefix+'.'+device[0]]=dict(zip(('d','g','s','b'),
                [nets.get(node,prefix+'.'+node) for node in device[1:5]]))
    register('xdec',decoder,decoder_nets)
    for row in range(4):
        nets=dict(VDD='VDD',VSS='0',WL_IN=f'DEC{row}',WL=f'WL{row}')
        lines.append(instance(f'XWL{row}',driver['subcircuit'],driver['pins'],nets))
        lines.append(f'CWL{row} WL{row} 0 {cap_ff*1e-15:.14g}')
        register(f'xwl{row}',driver,nets)
    require(len(terminals)==decoder_mos+16,'Incomplete decoder/WL terminal coverage')
    saved={'VDD','PCLK','A0','A1',*[f'DEC{i}' for i in range(4)],*[f'WL{i}' for i in range(4)]}
    saved.update(node for pins in terminals.values() for node in pins.values() if node!='0')
    lines+=['.save '+' '.join(f'v({node})' for node in sorted(saved))+' i(VDD_SRC)',
        f'.tran {step_ps:g}p {STOP_NS:g}n 0 {step_ps:g}p uic',
        '.control','set filetype=binary','run','write waveform.raw','quit','.endc','.end']
    return '\n'.join(lines)+'\n',terminals


def analyze(raw,profile,old,new,terminals,settling_ns):
    time=raw['time'];vdd=PROFILES[profile][1]
    def trace(node):
        if node=='0':return np.zeros_like(time)
        signal=raw['v('+node.lower()+')']
        require(np.all(np.isfinite(signal)),f'Nonfinite waveform: {node}')
        return signal
    def window(start,end):
        mask=(time>=start*1e-9)&(time<=end*1e-9)
        require(np.count_nonzero(mask)>3,f'Incomplete measurement window: {start}..{end} ns')
        return mask
    require(time[-1]>=STOP_NS*1e-9-1e-14,'Incomplete transient record')
    checks=[]
    def check(label,value,low,high):
        passed=bool(math.isfinite(value) and low<=value<=high)
        checks.append(dict(check=label,value=float(value),min=low,max=high,status='PASS' if passed else 'FAIL'))
    for start,end in [(2,4.5),(12,14),(24,27)]:
        mask=window(start,end)
        for row in range(4):
            for family in ('DEC','WL'):
                check(f'{family}{row}_precharge_max_{start}ns',np.max(trace(family+str(row))[mask]),-0.1*vdd,0.1*vdd)
    for selected,start,end in [(old,8.8,9.975),(new,RISE_NS+settling_ns,FALL_NS-EDGE_PS*0.0005)]:
        mask=window(start,end)
        for row in range(4):
            for family in ('DEC','WL'):
                signal=trace(family+str(row))[mask]
                if row==selected:
                    check(f'{family}{row}_selected_min_{start:g}ns',np.min(signal),0.9*vdd,1.1*vdd)
                else:
                    check(f'{family}{row}_unselected_max_{start:g}ns',np.max(signal),-0.1*vdd,0.1*vdd)
    # Check unwanted row assertions over evaluation, including selected-row rise.
    evaluation=window(RISE_NS,FALL_NS-EDGE_PS*0.0005)
    for row in range(4):
        if row!=new:
            check(f'WL{row}_unselected_evaluation_peak',np.max(trace(f'WL{row}')[evaluation]),-0.1*vdd,0.1*vdd)
    metrics={}
    for family in ('DEC','WL'):
        signal=trace(family+str(new))
        edges={level:crossing(time,signal,level*vdd,True,RISE_NS*1e-9-25e-12,FALL_NS*1e-9)
               for level in (0.1,0.5,0.9)}
        for level in (0.5,0.9):
            metrics[f'{family.lower()}_delay{int(level*100)}_ps']=None if edges[level] is None else (edges[level]-RISE_NS*1e-9)*1e12
        metrics[family.lower()+'_rise_10_90_ps']=None if edges[0.1] is None or edges[0.9] is None else (edges[0.9]-edges[0.1])*1e12
    settled=trace(f'WL{new}')[window(RISE_NS+settling_ns,FALL_NS-EDGE_PS*0.0005)]
    metrics.update(wl_settled_min_v=float(np.min(settled)),wl_margin_over_screen_v=float(np.min(settled)-0.9*vdd))
    bias_window=window(2,27)
    extrema=[]
    for device,pins in terminals.items():
        for label,a,b in [('vgs','g','s'),('vgd','g','d'),('vds','d','s'),('vgb','g','b')]:
            values=(trace(pins[a])-trace(pins[b]))[bias_window]
            extrema.append(dict(device=device,voltage=label,min_v=float(np.min(values)),max_v=float(np.max(values)),abs_max_v=float(np.max(np.abs(values)))))
    worst=max(extrema,key=lambda r:r['abs_max_v'])
    logic=all(row['status']=='PASS' for row in checks)
    voltage=worst['abs_max_v']<=MAGNITUDE_SCREEN_V
    return dict(functional_status='PASS' if logic else 'FAIL',
        voltage_screen_status='PASS' if voltage else 'REVIEW_REQUIRED',
        status='PASS_SCREEN' if logic and voltage else ('REVIEW_REQUIRED' if logic else 'FAIL_SCREEN'),
        checks_pass=sum(r['status']=='PASS' for r in checks),checks_fail=sum(r['status']=='FAIL' for r in checks),
        worst_external_terminal_bias=worst,**metrics),checks,extrema


def write_csv(path,rows):
    require(bool(rows),'Refusing empty CSV')
    keys=list(dict.fromkeys(key for row in rows for key in row))
    with path.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=keys);writer.writeheader();writer.writerows(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--profiles',nargs='+',choices=PROFILES,default=list(PROFILES))
    parser.add_argument('--transitions',nargs='+',default=[f'{a}:{b}' for a in range(4) for b in range(4)])
    parser.add_argument('--step-ps',type=float,default=5)
    parser.add_argument('--settling-ns',type=float,default=3.8)
    parser.add_argument('--keep-raw',action='store_true')
    args=parser.parse_args()
    require(not args.output_dir.exists(),'Use a new campaign output directory')
    require(math.isfinite(args.step_ps) and 0<args.step_ps<=10,'Step must be in (0,10] ps')
    require(math.isfinite(args.settling_ns) and 0<args.settling_ns<FALL_NS-RISE_NS-0.1,'Invalid settling window')
    transitions=[tuple(map(int,item.split(':'))) for item in args.transitions]
    require(all(len(pair)==2 and all(0<=n<4 for n in pair) for pair in transitions),'Invalid address transition')
    inputs=release_inputs()
    provenance=json.loads(LOAD_CSV.with_suffix('.provenance.json').read_text())
    require(sha(LOAD_CSV)==provenance['sha256'],'Row-load provenance hash mismatch')
    load=load_wl_capacitance_evidence(LOAD_CSV,102.873935496)
    cap_ff=load['measured_max_ff']
    args.output_dir.mkdir(parents=True)
    (args.output_dir/'executed_script.py').write_bytes(Path(__file__).read_bytes())
    snapshots=args.output_dir/'helper_snapshots';snapshots.mkdir()
    for helper in ('plot_row_decoder_review.py','run_row_decoder_contract.py',
                   'run_row_decoder_capture_timing.py','run_row_decoder_tt.py'):
        shutil.copy2(Path(__file__).with_name(helper),snapshots/helper)
    manifest=dict(status='RUNNING',complete=False,profiles={key:PROFILES[key] for key in args.profiles},
        scope='Local frozen decoder/WL PEX screen; controlled address/PCLK; no capture registers, precharge leaf or bitcell data access.',
        acceptance='Experimental 0.1/0.9 VDD output windows and 1.95 V terminal-magnitude screen; no final timing/model/reliability approval.',
        schedule=dict(first_evaluation_ns=[5,10],address_transition_ns=ADDRESS_NS,evaluation_ns=[RISE_NS,FALL_NS],stop_ns=STOP_NS,edge_ps=EDGE_PS,settling_ns=args.settling_ns,step_ps=args.step_ps),
        initial_state='UIC zero-initialized internal nodes; full precharge before first evaluation; arbitrary power-up states not qualified.',
        inputs={key:{k:v for k,v in info.items() if k!='devices'} for key,info in inputs.items()},
        release_manifest_sha256=sha(RELEASE/'manifest.json'),release_checksums_sha256=sha(RELEASE/'checksums.json'),
        load_evidence=load,model_dependencies=model_dependencies(NATIVE_MODEL),
        runner_sha256=sha(Path(__file__)),ngspice_sha256=sha(shutil.which('ngspice')),
        helper_sha256={name:sha(Path(__file__).with_name(name)) for name in
            ('plot_row_decoder_review.py','run_row_decoder_contract.py','run_row_decoder_capture_timing.py','run_row_decoder_tt.py')},cases=[])
    # JSON metadata stores paths as text; the simulation includes the pinned files unchanged.
    for info in manifest['inputs'].values():info['path']=str(info['path'].relative_to(ROOT))
    path=args.output_dir/'manifest.json';path.write_text(json.dumps(manifest,indent=2)+'\n')
    results=[];all_checks=[]
    for profile in args.profiles:
        for old,new in transitions:
            name=f'{profile}_{old}_to_{new}';directory=args.output_dir/name;directory.mkdir()
            deck,terminals=make_deck(inputs,profile,old,new,args.step_ps,cap_ff)
            deck_path=(directory/'case.spice').resolve();deck_path.write_text(deck)
            command=['ngspice','-n','-b',str(deck_path)]
            result=subprocess.run(command,cwd=directory,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
            (directory/'ngspice.txt').write_text(result.stdout)
            raw_path=directory/'waveform.raw'
            require(result.returncode==0 and raw_path.exists() and not re.search(r'(?i)Error:|aborted|timestep too small',result.stdout),f'{name}: ngspice failed')
            raw=read_raw(raw_path)
            row,checks,extrema=analyze(raw,profile,old,new,terminals,args.settling_ns)
            row.update(case=name,profile=profile,old=old,new=new,deck_sha256=sha(deck_path),wl_cap_ff=cap_ff)
            (directory/'result.json').write_text(json.dumps(row,indent=2)+'\n')
            write_csv(directory/'checks.csv',checks);write_csv(directory/'bias_extrema.csv',extrema)
            if (old,new) in ((0,3),(1,2)):
                variables=['time','v(pclk)','v(a0)','v(a1)']+[f'v({family}{i})' for family in ('dec','wl') for i in range(4)]
                indices=np.linspace(0,len(raw['time'])-1,min(1800,len(raw['time']))).astype(int)
                write_csv(directory/'waveforms.csv',[{v:float(raw[v][i]) for v in variables} for i in indices])
            if not args.keep_raw:raw_path.unlink()
            results.append(row);all_checks.extend(dict(case=name,**check) for check in checks)
            manifest['cases']=results
            path.write_text(json.dumps(manifest,indent=2)+'\n')
            delay='missing' if row['wl_delay90_ps'] is None else f'{row["wl_delay90_ps"]:.2f}'
            print(f'{name}: {row["status"]}; WL90={delay} ps; min WL={row["wl_settled_min_v"]:.6f} V',flush=True)
    for key,info in inputs.items():require(sha(info['path'])==info['sha256'],f'{key} changed during campaign')
    manifest.update(complete=True,status='PASS_SCREEN' if all(r['status']=='PASS_SCREEN' for r in results) else 'COMPLETED_WITH_FINDINGS')
    path.write_text(json.dumps(manifest,indent=2)+'\n')
    write_csv(args.output_dir/'summary.csv',results);write_csv(args.output_dir/'checks.csv',all_checks)
    return 0 if manifest['status']=='PASS_SCREEN' else 2


if __name__=='__main__':
    raise SystemExit(main())
