#!/usr/bin/env python3
"""Explore full 32-bit transistor connectivity with explicit phase stimuli.

This harness screens a phase window. Ideal phase sources are NOT a physical
phase generator, so PASS cannot approve CORE or F2-FIS.
"""
from __future__ import annotations
import argparse
import bisect
import csv
import json
from pathlib import Path
import re
import subprocess
import tempfile

import phase2_core
from run_digital_regression import atomic_text, output_lock

ROOT=phase2_core.ROOT
PDK=Path('/opt/pdks/sky130A')


def make_deck(directory,design,solver='sparse'):
    # Timing is deliberately slow exploratory stimulus, not a target frequency.
    # Sources separate the phases to discover whether a physical implementation
    # can reproduce a usable interval. No internal initial conditions are used.
    cycles=[('unwritten',0,0)]+[('write',r,0xa7^(r*13)) for r in range(4)]
    cycles += [('read',r,0xa7^(r*13)) for r in range(4)]
    cycles += [('idle',0,0)]*3+[('read',r,0xa7^(r*13)) for r in reversed(range(4))]
    cycles += [('write',r,0xaa if r%2 else 0x55) for r in range(4)]
    cycles += [('read',r,0xaa if r%2 else 0x55) for r in range(4)]
    signals={'CLK':[(0,0)],'PCLK':[(0,0)],'PRECH':[(0,0)],'SCLK':[(0,0)],
             'WE':[(0,0)],'WL_EN':[(0,0)],'A0':[(0,0)],'A1':[(0,0)]}
    signals.update({f'DIN{b}':[(0,0)] for b in range(8)})
    samples=[]
    def event(name,t,value):
        old=signals[name][-1][1]
        signals[name].extend([(t,old),(t+.05,value)])
    for i,(op,row,data) in enumerate(cycles):
        t=10+20*i
        for b in range(2):event(f'A{b}',t-2,(row>>b)&1)
        for b in range(8):event(f'DIN{b}',t-2,(data>>b)&1)
        event('CLK',t,1);event('CLK',t+10,0)
        if op!='idle':
            event('PRECH',t+.2,1);event('PRECH',t+10.5,0)
            event('PCLK',t+1,1);event('PCLK',t+9,0)
            event('WL_EN',t+1.5,1);event('WL_EN',t+9,0)
            if op=='write':
                event('WE',t+.5,1);event('WE',t+9,0)
            else:
                event('SCLK',t+6,1);event('SCLK',t+11,0)
        samples.append({'operation':op,'row':row,'expected':data,'sample_ns':t+10.4})
    lines=['* Full 4x8 phase-window fixture; ideal phases, NOT a qualified macro',
           f'.lib "{PDK}/libs.tech/ngspice/sky130.lib.spice" tt',
           '.include "core.spice"','.include "capture_ff.spice"','.temp 27',
           '.options method=gear reltol=1e-4 vabstol=1e-8 iabstol=1e-12',
           'VSS_SRC VSS 0 0','VDD_SRC VDD 0 PWL(0 0 1n 1.8)']
    if solver=='klu':lines.append('.options klu')
    for name,events in signals.items():
        lines.append(f'V_{name} {name} 0 PWL('+ ' '.join(f'{t:.6g}n {v*1.8:.6g}' for t,v in events)+')')
    lines.append('XCORE '+' '.join(design['ports'])+' '+design['name'])
    lines.append('XCLKINV CLK VSS VSS VDD VDD CLKB sky130_fd_sc_hd__inv_1')
    for bit in range(8):
        # Real HD FF clock/data loading, clocked at external falling edge via
        # an actual HD inverter. No output enable/hold mux in this fixture.
        lines.append(f'XFF{bit} CLKB DOUT{bit} VSS VSS VDD VDD Q{bit} sky130_fd_sc_hd__dfxtp_1')
        lines.append(f'C_Q{bit} Q{bit} VSS 1f')
    stop=10+20*len(cycles)
    vectors=[*[f'v(Q{b})' for b in range(8)],*[f'v(DOUT{b})' for b in range(8)],
             'v(PRECH)','v(SCLK)','v(WL_EN)']
    lines.append('.save '+' '.join(vectors))
    lines.extend(['.control','set noaskquit','set wr_singlescale','set wr_vecnames',
                  f'tran 10p {stop}n 0 10p',
                  'wrdata waveform.dat '+' '.join([*[f'v(Q{b})' for b in range(8)],
                         *[f'v(DOUT{b})' for b in range(8)],'v(PRECH)','v(SCLK)','v(WL_EN)']),
                  'quit','.endc','.end'])
    return '\n'.join(lines)+'\n',samples


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='reports/phase2/core_window')
    parser.add_argument('--solver',choices=['sparse','klu'],default='sparse')
    args=parser.parse_args(); output=(ROOT/args.output).resolve()
    if not output.is_relative_to(ROOT/'reports/phase2') or output==ROOT/'reports/phase2':
        parser.error('Output must be under reports/phase2')
    output.mkdir(parents=True,exist_ok=True)
    with output_lock(output):
        receipt={'status':'RUNNING','CORE':'NOT_EVALUATED','F2_FIS':'NOT_EVALUATED',
                 'scope':'401 selected leaf MOS plus row qualification, data complements and HD output FF load',
                 'limitations':['Ideal phase/address/data sources; no physical capture/phase-generator binding',
                                'Schematic connectivity, no interconnect RC; no STA/Fmax/reliability claim'],
                 'condition':{'corner':'tt','vdd_v':1.8,'temp_c':27},'solver':args.solver}
        def publish():atomic_text(output/'results.json',json.dumps(receipt,indent=2)+'\n')
        publish()
        try:
            directory=ROOT/'build/phase2'; directory.mkdir(parents=True,exist_ok=True)
            build=Path(tempfile.mkdtemp(prefix='core-window-',dir=directory))
            design=phase2_core.emit(build,PDK/'libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice')
            # Include only instantiated HD definitions, retaining their exact
            # source parameters; avoid parsing hundreds of unused cells.
            hd=(PDK/'libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice').read_text()
            ff=re.search(r'(?ms)^\.subckt sky130_fd_sc_hd__dfxtp_1 .*?^\.ends[^\n]*',hd)[0]
            (build/'capture_ff.spice').write_text(ff+'\n')
            deck,samples=make_deck(build,design,args.solver); (build/'bench.spice').write_text(deck)
            receipt['build_directory']=str(build.relative_to(ROOT)); receipt['samples']=samples
            for name in ('core.spice','capture_ff.spice','graph.json','topology.json','bench.spice'):
                atomic_text(output/name,(build/name).read_text())
            with (output/'ngspice.txt').open('w') as log:
                run=subprocess.run(['ngspice','-n','-b','bench.spice'],cwd=build,stdout=log,
                                   stderr=subprocess.STDOUT,text=True,timeout=240)
            if run.returncode or not (build/'waveform.dat').exists():
                raise RuntimeError('ngspice failed/no waveform')
            import numpy as np
            data=np.loadtxt(build/'waveform.dat',skiprows=1)
            checks=[]
            for sample in samples:
                if sample['operation']!='read':continue
                index=bisect.bisect_left(data[:,0],sample['sample_ns']*1e-9)
                for b in range(8):
                    expected=(sample['expected']>>b)&1; voltage=float(data[index,b+1])
                    passed=voltage>=1.44 if expected else voltage<=.36
                    checks.append({**sample,'bit':b,'voltage_v':voltage,'status':'PASS' if passed else 'FAIL'})
            with (output/'checks.csv').open('w') as f:
                writer=csv.DictWriter(f,fieldnames=list(checks[0]));writer.writeheader();writer.writerows(checks)
            receipt.update(checks=len(checks),failures=sum(c['status']=='FAIL' for c in checks),
                           status='PASS_PHASE_FIXTURE' if checks and all(c['status']=='PASS' for c in checks) else 'FAIL')
        except Exception as error:receipt.update(status='FAIL',error=str(error))
        publish();print(json.dumps(receipt,indent=2));return 0 if receipt['status']=='PASS_PHASE_FIXTURE' else 1


if __name__=='__main__':raise SystemExit(main())
