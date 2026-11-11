#!/usr/bin/env python3
"""Plot full preserved transients and derived metrics, after receipt verification."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from run_phase1_final_isolated import read_data, verify


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence',required=True,type=Path)
    a=p.parse_args();root=a.evidence.resolve()
    verify(root)
    figure=root/'nominal_waveforms.png'
    if figure.exists():raise FileExistsError(figure)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,2,figsize=(12,7.2),layout='constrained')
    for ax,view in zip(axes[0],('spice','pex')):
        data=read_data(root/f'sa_{view}_d5_p+1_c10/waveform.dat.gz')
        t=data[:,0]*1e9
        for col,label,color in ((4,'SCLK','#999999'),(5,'SA_OUT','#144d80'),(6,'SA_OUTB','#be682a')):
            ax.plot(t,data[:,col],label=label,color=color,lw=1.4)
        ax.set(title=f'Sense — {view.upper()}, ΔBL = ±5 mV, 10 fF/saída',
               xlabel='Tempo (ns)',ylabel='Tensão (V)',xlim=(2.7,17))
        ax.legend(fontsize=8,ncol=3,loc='center right');ax.grid(alpha=.2)
        ax.text(.02,.97,'BL > BLB na 1ª avaliação; BLB > BL na 2ª',transform=ax.transAxes,va='top',fontsize=8)
        if view=='pex':
            ax.text(.02,.85,'FAIL: polaridade incorreta na 1ª avaliação',transform=ax.transAxes,va='top',fontsize=8,color='#a32626')
    ax=axes[1,0]
    for cap,color in ((20,'#144d80'),(50,'#be682a'),(103,'#567a3b')):
        data=read_data(root/f'wl_pex_c{cap}/waveform.dat.gz')
        ax.plot(data[:,0]*1e9,data[:,3],label=f'WL, {cap} fF',color=color)
    ax.plot(data[:,0]*1e9,data[:,2],'--',color='#999999',label='WL_IN')
    ax.set(title='WL driver — PEX, bordas de subida e descida',xlabel='Tempo (ns)',ylabel='Tensão (V)',xlim=(2.9,8.8))
    ax.legend(fontsize=8);ax.grid(alpha=.2)
    ax=axes[1,1]
    for view,color in (('spice','#144d80'),('pex','#be682a')):
        for direction,style in (('rise','-o'),('fall','--s')):
            caps=[20,50,103]
            values=[]
            for cap in caps:
                checks=json.loads((root/f'wl_{view}_c{cap}'/'checks.json').read_text())
                values.append(max(m['propagation_ps'] for m in checks['metrics'] if m['direction']==direction))
            ax.plot(caps,values,style,color=color,label=f'{view.upper()} {direction}')
    ax.set(title='WL driver — maior atraso das duas bordas ensaiadas',xlabel='Carga externa (fF)',ylabel='Atraso a 50% (ps)')
    ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.suptitle('Células finais isoladas — TT / 1,8 V / 27 °C; dados completos preservados',fontsize=13)
    fig.savefig(figure,dpi=160)
    plt.close(fig)


if __name__=='__main__':main()
