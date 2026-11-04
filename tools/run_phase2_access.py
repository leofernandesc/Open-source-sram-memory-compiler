#!/usr/bin/env python3
"""Transistor write/read through mapped capture, real delay gates and selected fabric."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import numpy as np
import phase2_core as core
from phase2_access_checks import check as check_protocol
from run_digital_regression import atomic_text,output_lock
from run_phase2_digital import sha

ROOT=core.ROOT
PDK=Path('/opt/pdks/sky130A')


def raw_fabric():
    selected=core.selected_leaves();g=core.graph();core.audit(g)
    ports=['VDD','VSS','A0','A1','PCLK','PRECH','SCLK','WE',
           *[f'DIN{b}' for b in range(8)],*[f'DIN_B{b}' for b in range(8)],
           *[f'DOUT{b}' for b in range(8)],*[f'ROW{r}' for r in range(4)],*[f'DEC{r}' for r in range(4)]]
    lines=[]
    for item in selected.values():
        path=item['files'].get('netlist',item['files']['schematic'].with_suffix('.spice'))
        lines.append(path.read_text())
    lines.append('.subckt leaf_fabric '+' '.join(ports))
    for i in g['instances']:
        if i['cell'].startswith('sky130_'):continue
        lines.append('X'+i['name']+' '+' '.join(i['pins'][p] for p in selected[i['cell']]['pins'])+' '+i['cell'])
    lines.append('.ends leaf_fabric')
    return '\n'.join(lines)+'\n'


def bench(binding,design,quick,solver='klu'):
    top=design['modules']['sram_4x8_wrapper']
    alias={}
    for name,port in top['ports'].items():
        for i,bit in enumerate(port['bits']):alias[bit]=name if len(port['bits'])==1 else f'{name}{i}'
    def net(bit):return alias.get(bit,f'n{bit}')
    def internal(name):return net(top['netnames'][name]['bits'][0])
    phase_names={'PCLK':internal('macro_core.pclk'),'PRECH':internal('macro_core.prech'),
                 'SCLK':internal('macro_core.sclk'),'WE':internal('macro_core.write_enable')}
    cells=sorted(top['cells'].items())
    fabric=next(index for index,(_,cell) in enumerate(cells) if cell['type']=='leaf_fabric')
    cycles=[('idle',0,0),('idle',0,0),('unwritten',0,0)]
    rows=range(1) if quick else range(4)
    cycles += [('write',r,0xa7^(r*13)) for r in rows]
    cycles += [('read',r,0xa7^(r*13)) for r in rows]
    if not quick:
        cycles += [('idle',0,0)]*2+[('read',r,0xa7^(r*13)) for r in rows]
        patterns=[0x00,0xff,0xaa,0x55]
        cycles += [('write',r,patterns[r]) for r in range(4)]
        cycles += [('read',r,patterns[r]) for r in range(4)]
        # All six inactive/invalid controls must preserve the previously
        # written words. The master offers a payload but never drives on read.
        cycles += [(f'inactive{ctl:03b}',ctl%4,0x96) for ctl in (0,3,4,5,6,7)]
        cycles += [('read',r,patterns[r]) for r in range(4)]
    signals={name:[(0,0)] for name in ['CLK','CSb','OEb','WEb','ADDR0','ADDR1','HOST_EN','HOST_WEAK_EN',*[f'HOST{b}' for b in range(8)]]}
    for name in ('CSb','OEb','WEb'):signals[name].append((1,1))
    def event(name,t,value):
        old=signals[name][-1][1]
        signals[name].extend([(t,old),(t+.05,value)])
    records=[]
    for index,(op,row,payload) in enumerate(cycles):
        edge=10+20*index
        ctl=(0,1,0) if op=='write' else (0,0,1) if op in ('read','unwritten') else (1,1,1)
        if op.startswith('inactive'):ctl=tuple(int(c) for c in op[-3:])
        for name,value in zip(('CSb','OEb','WEb'),ctl):event(name,edge-3,value)
        for b in range(2):event(f'ADDR{b}',edge-3,(row>>b)&1)
        for b in range(8):event(f'HOST{b}',edge-2.5,(payload>>b)&1)
        event('HOST_EN',edge-2,op=='write');event('HOST_EN',edge+1,0)
        if op.startswith('inactive'):
            event('HOST_WEAK_EN',edge-2,1)
            for b in range(8):event(f'HOST{b}',edge+4,((~payload)>>b)&1)
            event('HOST_WEAK_EN',edge+12,0)
        event('CLK',edge,1);event('CLK',edge+10,0)
        records.append({'cycle':index,'operation':op,'row':row,'expected':payload,
                        'rise_ns':edge,'fall_ns':edge+10,'sample_ns':edge+11})
    lines=['* Mapped synchronous SRAM with real HD control and all 32 bitcells',
           f'.lib "{PDK}/libs.tech/ngspice/sky130.lib.spice" tt',
           '.include "binding.spice"','.include "fabric.spice"','.temp 27',
           '.options method=gear reltol=1e-4 vabstol=1e-8 iabstol=1e-12',
           'VSS_SRC VSS 0 0','VDD_SRC VDD 0 PWL(0 0 1n 1.8)',
           '.model HOST_SWITCH sw ron=1 roff=1e12 vt=.9 vh=.1',
           '.model HOST_WEAK_SWITCH sw ron=1k roff=1e12 vt=.9 vh=.1']
    if solver=='klu':lines.append('.options klu')
    for name,events in signals.items():
        lines.append(f'V_{name} {name} 0 PWL('+ ' '.join(f'{t:.6g}n {int(v)*1.8:.6g}' for t,v in events)+')')
    for bit in range(8):
        lines.append(f'S_HOST{bit} DATA{bit} HOST{bit} HOST_EN 0 HOST_SWITCH')
        lines.append(f'S_WEAK{bit} DATA{bit} HOST{bit} HOST_WEAK_EN 0 HOST_WEAK_SWITCH')
    lines.append('XDUT '+' '.join(binding['ports'])+' sram_4x8_wrapper')
    vectors=[*[f'v(DATA{b})' for b in range(8)],*[f'v(xdut.{phase_names[p]})' for p in phase_names],
             *[f'v(xdut.xmapped{fabric}.WL{r})' for r in range(4)]]
    # Save actual output-register inputs and local positive clock edges. All
    # output FFs are positive-edge HD cells with physically inverted clocks.
    raw=top['netnames'].get('raw_read_data',top['netnames'].get('macro_core.DOUT_RAW'))['bits']
    vectors += [f'v(xdut.{net(bit)})' for bit in raw]
    capture_clocks=sorted({net(c['connections']['CLK'][0]) for _,c in cells
                          if c['type'].startswith('sky130_fd_sc_hd__df') and net(c['connections']['CLK'][0])!='CLK'})
    vectors += [f'v(xdut.{n})' for n in capture_clocks]
    capture_inputs=[];bit_clocks=[]
    for q in top['netnames']['read_data_q']['bits']:
        ff=next(c for _,c in cells if c['type'].startswith('sky130_fd_sc_hd__df') and c['connections']['Q']==[q])
        name=f'v(xdut.{net(ff["connections"]["D"][0])})';capture_inputs.append(name)
        bit_clocks.append(f'v(xdut.{net(ff["connections"]["CLK"][0])})')
        if name not in vectors:vectors.append(name)
    lines += ['.save '+' '.join(vectors),'.control','set noaskquit','set wr_singlescale','set wr_vecnames',
              f'tran 10p {10+20*len(cycles)}n 0 10p','wrdata waveform.dat '+' '.join(vectors),
              'quit','.endc','.end']
    return '\n'.join(lines)+'\n',records,vectors,capture_inputs,bit_clocks


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--quick',action='store_true')
    p.add_argument('--solver',choices=['sparse','klu'],default='klu')
    p.add_argument('--output',default='reports/phase2/access');args=p.parse_args()
    output=(ROOT/args.output).resolve()
    if not output.is_relative_to(ROOT/'reports/phase2') or output==ROOT/'reports/phase2':p.error('Output under reports/phase2 required')
    output.mkdir(parents=True,exist_ok=True)
    with output_lock(output):
        receipt={'status':'RUNNING','CORE':'NOT_EVALUATED','F2_FIS':'NOT_EVALUATED',
                 'scope':'Mapped physical phases/capture and selected 32-bit fabric; schematic interconnect',
                 'condition':{'corner':'tt','vdd_v':1.8,'temp_c':27},'quick':args.quick,'solver':args.solver}
        def publish():atomic_text(output/'results.json',json.dumps(receipt,indent=2)+'\n')
        publish()
        try:
            source=ROOT/'reports/phase2/physical_binding';binding=json.loads((source/'results.json').read_text())
            if binding['status']!='PASS_MAPPING_ONLY':raise ValueError('Physical binding mapping not approved')
            for name,expected in binding['inputs'].items():
                if sha(ROOT/name)!=expected:raise ValueError('Binding source changed: '+name)
            design=json.loads((source/'binding.json').read_text())
            root=ROOT/'build/phase2';root.mkdir(parents=True,exist_ok=True)
            build=Path(tempfile.mkdtemp(prefix='access-',dir=root))
            shutil.copyfile(source/'binding.spice',build/'binding.spice')
            (build/'fabric.spice').write_text(raw_fabric())
            deck,records,vectors,capture_inputs,bit_clocks=bench(binding,design,args.quick,args.solver);(build/'bench.spice').write_text(deck)
            receipt.update(build_directory=str(build.relative_to(ROOT)),cycles=records,vectors=vectors,
                           capture_inputs=capture_inputs,capture_clocks=bit_clocks,
                           inputs={'binding.spice':sha(build/'binding.spice'),'fabric.spice':sha(build/'fabric.spice'),
                                   'bench.spice':sha(build/'bench.spice')})
            publish()
            for name in ('binding.spice','fabric.spice','bench.spice'):shutil.copyfile(build/name,output/name)
            with (output/'ngspice.txt').open('w') as log:
                result=subprocess.run(['ngspice','-n','-b','bench.spice'],cwd=build,stdout=log,
                                      stderr=subprocess.STDOUT,text=True,timeout=1800)
            if result.returncode or not (build/'waveform.dat').exists():raise ValueError('ngspice failed/no waveform')
            data=np.loadtxt(build/'waveform.dat',skiprows=1)
            if data.ndim!=2 or len(data)<100 or not np.all(np.isfinite(data)) or not np.all(np.diff(data[:,0])>0):
                raise ValueError('Invalid waveform')
            checks=[]
            for rec in records:
                if rec['operation']!='read':continue
                idx=np.searchsorted(data[:,0],rec['sample_ns']*1e-9)
                for bit in range(8):
                    expect=(rec['expected']>>bit)&1;v=float(data[idx,bit+1])
                    passed=1.44<=v<=1.98 if expect else -.18<=v<=.36
                    checks.append({**rec,'bit':bit,'voltage_v':v,'status':'PASS' if passed else 'FAIL'})
            with (output/'checks.csv').open('w') as f:
                writer=csv.DictWriter(f,fieldnames=list(checks[0]));writer.writeheader();writer.writerows(checks)
            receipt.update(checks=len(checks),failures=sum(c['status']=='FAIL' for c in checks),
                           status='PASS_NOMINAL_ACCESS_ONLY' if checks and all(c['status']=='PASS' for c in checks) else 'FAIL')
            protocol,reference=check_protocol(data,records,vectors,capture_inputs,bit_clocks)
            for rec in records:
                if not rec['operation'].startswith('inactive'):continue
                for offset,invert in [(1,False),(8,True)]:
                    idx=np.searchsorted(data[:,0],(rec['rise_ns']+offset)*1e-9)
                    for bit in range(8):
                        expected=((rec['expected']^(255 if invert else 0))>>bit)&1
                        voltage=float(data[idx,bit+1])
                        protocol.append(dict(kind='bus_release_1kohm_probe',cycle=rec['cycle'],bit=bit,
                                             sample_ns=rec['rise_ns']+offset,voltage_v=voltage,
                                             status='PASS' if abs(voltage-expected*1.8)<=.05 else 'FAIL'))
            atomic_text(output/'protocol.json',json.dumps({'checks':protocol,'capture_reference':reference},indent=2)+'\n')
            receipt['protocol_checks']=len(protocol);receipt['protocol_failures']=sum(c['status']=='FAIL' for c in protocol)
            if receipt['protocol_failures']:receipt['status']='FAIL'
            # Retain a real decimated waveform for diagnosis; full raw output
            # remains in its build directory. Endpoints/checks use full data.
            np.savetxt(output/'waveform_excerpt.csv',data[::10],delimiter=',',header=','.join(['time_s',*vectors]),comments='')
        except Exception as error:receipt.update(status='FAIL',error=str(error))
        publish();print(json.dumps({k:receipt[k] for k in ('status','CORE','F2_FIS')},indent=2))
        if 'error' in receipt:print(receipt['error'])
        return 0 if receipt['status']=='PASS_NOMINAL_ACCESS_ONLY' else 1


if __name__=='__main__':raise SystemExit(main())
