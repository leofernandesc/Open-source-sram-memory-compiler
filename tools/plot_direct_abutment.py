#!/usr/bin/env python3
"""Figures from actual old/new GDS and the new complete qualification raw."""
import argparse,json
from pathlib import Path
import gdstk
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch
from run_phase2_digital import ROOT,sha

BASE=ROOT/'reports/phase2/direct_abutment_20261111'
COLORS={64:('#e8c8dc','nwell'),66:('#ae5f45','poly'),68:('#7e8791','M1'),
        69:('#488baa','M2'),70:('#bd9a35','M3'),71:('#557f59','M4')}


def render(ax,cell,box,title):
    clip=gdstk.rectangle(box[0],box[1])
    for layer,(color,_) in COLORS.items():
        polys=cell.get_polygons(layer=layer,datatype=20)
        if not polys:continue
        clipped=gdstk.boolean(polys,[clip],'and',precision=.001)
        ax.add_collection(PolyCollection([p.points for p in clipped],facecolors=color,edgecolors='none',alpha=.8))
    ax.set_xlim(box[0][0],box[1][0]);ax.set_ylim(box[0][1],box[1][1]);ax.set_aspect('equal')
    ax.set_title(title,fontsize=10);ax.set_xlabel('x / µm');ax.set_ylabel('y / µm')


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=(ROOT/a.output).resolve()
    if not out.is_relative_to(BASE) or out.exists():p.error('Use a new candidate figure directory')
    out.mkdir(parents=True)
    old=ROOT/'reports/phase2/fabric/leaf_fabric.gds';new=BASE/'fabric_v3/leaf_fabric.gds'
    pilot=ROOT/'reports/direct_abutment/20261111/pilot_v2/array_2x2_abut.gds'
    oldcell=gdstk.read_gds(old).top_level()[0];newcell=gdstk.read_gds(new).top_level()[0]
    fig,axs=plt.subplots(2,1,figsize=(11,8),layout='constrained')
    render(axs[0],oldcell,[[-2.25,165.29],[225,253.21]],'Matriz anterior: pitch 30 × 25 µm; envelope 227,25 × 87,92 µm')
    render(axs[1],newcell,[[0,180],[138,236]],'Abutment direto: pitch 17,25 × 14 µm; envelope 138 × 56 µm')
    for ax in axs:ax.legend(handles=[Patch(color=c,label=n) for c,n in COLORS.values()],loc='upper right',ncol=6,fontsize=7)
    fig.savefig(out/'array_comparison.png',dpi=190);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,7),layout='constrained')
    render(ax,gdstk.read_gds(pilot).top_level()[0],[[0,0],[34.5,28]],'Protótipo 2×2 — geometria do GDS verificado')
    ax.axvline(17.25,color='black',ls='--',lw=.8);ax.axhline(14,color='black',ls='--',lw=.8)
    ax.set_title('Protótipo 2×2 — tracejado indica fronteiras das células',fontsize=10)
    fig.savefig(out/'pilot_2x2.png',dpi=190);plt.close(fig)
    source=BASE/'qualification_v1';receipt=json.loads((source/'results.json').read_text());raw=ROOT/receipt['build_directory']/'waveform.dat'
    if receipt['status']!='PASS' or sha(raw)!=receipt['raw_sha256']:raise ValueError('New complete C2 waveform required')
    data=np.loadtxt(raw,skiprows=1);t=data[:,0]*1e9;mask=(t>=146)&(t<=167)
    v=receipt['vectors'];extra=receipt['probes']
    def signal(name):return data[mask,v.index(extra[name])+1]
    fig,axs=plt.subplots(5,1,figsize=(10,9),sharex=True,layout='constrained')
    for name in ('CLK','CSb'):axs[0].plot(t[mask],signal(name),label=name)
    for col,name in [(9,'PCLK'),(10,'PRECH'),(11,'SCLK'),(14,'WL1')]:axs[1].plot(t[mask],data[mask,col],label=name)
    for name in ('BL0','BLB0'):axs[2].plot(t[mask],signal(name),label=name)
    axs[3].plot(t[mask],signal('REG_Q0'),label='FF_Q[0]');axs[3].plot(t[mask],data[mask,1],label='DATA[0]')
    axs[4].plot(t[mask],signal('I_WEAK0')*1e6,label='I probe[0]');axs[4].set_yscale('symlog',linthresh=30);axs[4].set_ylabel('µA')
    for ax in axs:
        ax.grid(alpha=.2);ax.legend(loc='upper right',ncol=4,fontsize=8)
    for ax in axs[:-1]:ax.set_ylabel('V')
    axs[-1].set_xlabel('Tempo / ns')
    fig.suptitle('Novo top — qualificação, leitura e máscara viva; TT, 1,8 V, 27 °C\nProbe de oposição de 1 kΩ após a captura: calibração, não carga lógica nominal',fontsize=10)
    fig.savefig(out/'read_and_bus.png',dpi=190);plt.close(fig)
    (out/'sources.json').write_text(json.dumps(dict(inputs={str(q.relative_to(ROOT)):sha(q) for q in [old,new,pilot,source/'results.json',raw,Path(__file__)]},
        interpretation='Actual GDS polygons; 2x2 dashed boundaries are explanatory. Actual full-raw qualification excerpt, no idealized waveform.',
        figures={q.name:sha(q) for q in out.glob('*.png')}),indent=2)+'\n')


if __name__=='__main__':main()
