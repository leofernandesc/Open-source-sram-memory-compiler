#!/usr/bin/env python3
"""Export passive BL cut resistance and plot the archived sense-3 control."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_phase3_data3_tt import load
from analyze_phase3_sense3_isolation import read_wave
from diagnose_phase3_sclk_startup import write_json
from run_phase3_eco_pex import pinned, sha256
from run_phase3_sense3_isolation import REFERENCE, ResistanceGraph


def port_resistance(lines, io, ground):
    cards = {line.split()[0]:line.split()[1:] for line in lines if line.startswith('R')}
    nodes = ResistanceGraph(cards).group(io)
    if ground not in nodes:
        raise ValueError('Boundary point does not reach the sampler through retained resistors')
    index = {name:i for i,name in enumerate(sorted(nodes-{ground}))}
    conductance = np.zeros((len(index),len(index)))
    for a,b,r,*_ in cards.values():
        if a not in nodes or b not in nodes:
            continue
        g = 1/float(r)
        for left,right in [(a,b),(b,a)]:
            if left in index:
                conductance[index[left],index[left]] += g
                if right in index:
                    conductance[index[left],index[right]] -= g
    i = np.zeros(len(index))
    i[index[io]] = 1.
    return float(np.linalg.solve(conductance,i)[index[io]])


def plot(root,reference,control,report):
    from matplotlib.figure import Figure

    fig = Figure(figsize=(12,7.5),layout='constrained')
    ax = fig.subplots(3,2)
    quantities = [('BLB−BL',('blb_at_sense','bl_at_sense')),
                  ('NTAIL',('sense_tail',)),('SAB−SA',('sab_sampling_out','sa_sampling_out'))]
    for col,case in enumerate(report['comparisons']):
        k = case['window']['tail20_ns']
        start,stop = k-.4,k+1.55
        for row,(label,signals) in enumerate(quantities):
            for trace,style,legend in [(reference,'--','macro TT'),(control,'-','controle reduzido')]:
                pts = trace.points(start,stop,[(trace.cols[s],1. if i==0 else -1.,0.)
                                               for i,s in enumerate(signals)])
                ax[row,col].plot([t for t,_ in pts],[sum(v) for _,v in pts],style,
                                 color='#234276' if trace is reference else '#b85131',label=legend,linewidth=1.4)
            ax[row,col].axvline(k,color='#727984',alpha=.7,linewidth=.8)
            ax[row,col].axvline(case['isolated']['tail50']['at_ns'],color='#727984',alpha=.7,linewidth=.8)
            ax[row,col].set(xlim=(start,stop),ylabel=f'{label} (V)',xlabel='Tempo de referência (ns)')
            ax[row,col].grid(alpha=.24)
        ax[0,col].set_title(f"Ciclo {case['window']['cycle']} · linha 3")
        ax[0,col].legend(loc='best',fontsize=8)
    fig.suptitle('Controle isolado do sense 3 · marcadores de SCLK a 20% e 50%')
    fig.savefig(root/'control_comparison.png',dpi=160)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    root = parser.parse_args().output
    gate = root/'control_gate.json'
    report = json.loads(gate.read_text())
    result = json.loads(pinned(root/'control/result.json',report['control_result_sha256']).read_text())
    control = read_wave(root/'control',result)
    _,_,ref = load(REFERENCE,True)
    authority = json.loads((root/'manifest.json').read_text())
    lines = pinned(root/'slice.spice',authority['artifacts_sha256']['slice.spice']).read_text().splitlines()
    reductions = {sampler:dict(archived_boundary=path[-1],shortest_path_ohm=length,
                               equivalent_passive_dc_ohm=port_resistance(lines,sampler,path[-1]))
                  for sampler,(length,path) in authority['finite_bl_resistor_paths'].items()}
    write_json(root/'passive_bl_impedance.json',dict(resistance=reductions,control_gate_sha256=sha256(gate),
          method='Nodal conductance solve with 1 A at the sampler and remote boundary grounded. R only.',
          limitation='This is the retained passive mesh. The active, removed bitcell array is outside the model.'))
    plot(root,ref,control,report)


if __name__=='__main__':
    main()
