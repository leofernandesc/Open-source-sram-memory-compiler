#!/usr/bin/env python3
"""Measured extension figures from selected complete raw files, no EDA rerun."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_phase2_digital import ROOT,sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=(ROOT/a.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2') or out.exists():p.error('New figure directory required')
    out.mkdir(parents=True);meta={};palette=['#245c91','#24756c','#ad6c22','#776aa3']
    def source(name):
        receipt=ROOT/f'reports/phase2/extension_20261104/{name}/results.json';s=json.loads(receipt.read_text());raw=ROOT/s['build_directory']/'waveform.dat'
        if sha(raw)!=s['raw_sha256'] or s['status'] not in ('PASS','FAIL_ELECTRICAL_SCREEN'):raise ValueError('Wrong raw/incomplete source')
        d=np.loadtxt(raw,skiprows=1);col=lambda n:s['vectors'].index(s['probes'][n])+1
        return s,d,col,dict(receipt=str(receipt.relative_to(ROOT)),receipt_sha256=sha(receipt),raw_sha256=sha(raw))
    def plot(name,d,origin,groups,limits,title):
        t=d[:,0]*1e9;mask=(t>=limits[0])&(t<=limits[1]);fig,axes=plt.subplots(len(groups),1,figsize=(12,4.8),sharex=True)
        axes=np.atleast_1d(axes)
        for ax,(unit,signals) in zip(axes,groups):
            for k,(label,c,scale) in enumerate(signals):ax.plot(t[mask],d[mask,c]*scale,label=label,lw=1.5,color=palette[k])
            ax.set_ylabel(unit,fontsize=10);ax.legend(loc='upper right',ncol=len(signals),frameon=False,fontsize=9);ax.grid(alpha=.18)
            if unit=='V':ax.set_ylim(-.15,2.05);ax.set_yticks([0,1.8])
            if unit=='µA':ax.set_yscale('symlog',linthresh=30);ax.set_ylabel('µA (symlog)',fontsize=10)
        axes[-1].set_xlabel('Tempo (ns)');axes[-1].set_xlim(*limits);axes[0].set_title(title,fontsize=11,loc='left')
        fig.tight_layout(pad=.6);fig.savefig(out/name,dpi=180);plt.close(fig)
        meta[name]=dict(kind='Measured full raw trace, unchanged 1493 MOS',**origin,window_ns=limits,columns_and_scaling=groups,
                        condition='TT/1.8V/27C; 20ns clock; 50ps source transitions; no wire RC',
                        current_axis='symlog, linear region +/-30uA; unmodified samples' if any(g[0]=='µA' for g in groups) else None,sha256=sha(out/name))
    s,d,c,o=source('c1_sequences')
    plot('consecutive_access.png',d,o,[('V',[(f'WL{i}',13+i,1) for i in range(4)]),
        ('V',[('CELL[0,0]',c('CELL_0_0'),1),('CELL[1,0]',c('CELL_1_0'),1)]),
        ('V',[('RAW0',17,1),('FF_Q0',c('REG_Q0'),1),('DATA0',1,1)])],
        [128,288],'C1: leituras repetidas, reescritas complementares e readback')
    r=next(r for r in s['cycles'] if r['cycle']==14);e=r['rise_ns']
    plot('write_guard.png',d,o,[('V',[('PRECH (ativo baixo)',10,1),('WE',12,1)]),
        ('V',[('PCLK',9,1),('WL2',15,1)])],[e+1.1,e+2.8],'C1 ciclo 14: liberação de precharge, escrita e seleção física')
    s,d,c,o=source('c2_bus');r=next(r for r in s['cycles'] if r['cycle']==7);e=r['rise_ns'];b=json.loads((ROOT/'reports/phase2/extracted_access_singlethread/results.json').read_text())
    fd=s['vectors'].index(b['capture_inputs'][0])+1;ck=s['vectors'].index(b['capture_clocks'][0])+1
    plot('read_path.png',d,o,[('V',[('PCLK',9,1),('WL1',14,1),('SCLK',11,1)]),
        ('V',[('BL0',c('BL0'),1),('BLB0',c('BLB0'),1)]),
        ('V',[('SA_OUT = RAW0',17,1),('FF_D0',fd,1)]),
        ('V',[('FF_Q0',c('REG_Q0'),1),('DATA0',1,1),('CLK público',c('CLK'),1)])],
        [e-.5,e+11.2],'C2 ciclo 7: leitura da linha 1, AA anterior → 55 capturado')
    plot('bus_mask_current.png',d,o,[('V',[('CSb',c('CSb'),1),('TE_B0',c('TE_B0'),1),('WEAK_EN',c('WEAK_EN'),1)]),
        ('V',[('FF_Q0',c('REG_Q0'),1),('DATA0',1,1),('probe oposto',c('HOST0'),1)]),
        ('µA',[('I_WEAK0',c('I_WEAK0'),1e6),('I_HOST0',c('I_HOST0'),1e6)])],
        [e+11.1,e+16.5],'C2 ciclo 7: calibração de 1 kΩ, máscara viva e restauração; não dois mestres fortes')
    plot('capture_to_data.png',d,o,[('V',[('CLK público',c('CLK'),1),('CLK local FF0',ck,1)]),
        ('V',[('RAW0',17,1),('FF_D0',fd,1)]),('V',[('FF_Q0',c('REG_Q0'),1),('DATA0',1,1)])],
        [e+9.8,e+11.1],'C2 ciclo 7: descida pública, captura local e novo DATA0')
    (out/'sources.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status='PASS',figures=list(meta))))


if __name__=='__main__':main()
