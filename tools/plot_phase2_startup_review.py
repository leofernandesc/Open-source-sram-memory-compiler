#!/usr/bin/env python3
"""Plot actual full-resolution startup traces; never generate synthetic evidence."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_phase2_digital import ROOT, sha
from run_phase2_startup_review import validate_trace


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True); p.add_argument('--output', required=True)
    args = p.parse_args(); source = ROOT/args.source; out = (ROOT/args.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2') or out.exists():
        p.error('A new output directory under reports/phase2 is required')
    state = json.loads((source/'results.json').read_text())
    wave = ROOT/state['build_directory']/'waveform.dat'
    if sha(wave) != state['raw_waveform_sha256']:
        raise ValueError('Raw transient changed')
    data = np.loadtxt(wave, skiprows=1)
    vectors, probes = state['vectors'], state['probes']
    validate_trace(data, vectors, state['stop_ns'])
    def col(name): return vectors.index(probes[name])+1
    base = json.loads((ROOT/'reports/phase2/extracted_access_singlethread/results.json').read_text())
    panels = [
        [('VDD', col('VDD')), ('CLK público', col('CLK'))],
        [(n, col(n)) for n in ('CSb', 'OEb', 'WEb')],
        [(n, col(n)) for n in ('READ_Q', 'WRITE_Q')]+[('PCLK', 9)],
        [('PRECH (baixo ativo)', 10), ('WE', 12), ('SCLK', 11)],
        [(f'WL{r}', 13+r) for r in range(4)],
        [(n, col(n)) for n in ('BL0', 'BLB0')],
        [(f'Decoder N{r}', col(f'N{r}')) for r in range(4)],
        [('SA_OUT/DOUT_RAW[0]', 17),
         ('FF_D[0]', vectors.index(base['capture_inputs'][0])+1),
         ('FF_Q[0]', col('REG_Q0')), ('DATA[0]', 1)],
    ]
    out.mkdir(parents=True)
    time = data[:, 0]*1e9
    first = next(r for r in state['cycles'] if r['operation'] == 'write')
    for name, limits in [('startup', (0, first['rise_ns']+45)),
                         ('capture', (first['rise_ns']+17, first['rise_ns']+35))]:
        fig, axes = plt.subplots(len(panels), 1, sharex=True, figsize=(12, 13))
        selected = (time >= limits[0]) & (time <= limits[1])
        for ax, panel in zip(axes, panels):
            for label, column in panel:
                ax.plot(time[selected], data[selected, column], label=label, linewidth=1)
            ax.set_ylim(-.15, 2.05); ax.set_ylabel('V'); ax.grid(alpha=.25)
            ax.legend(loc='upper right', ncol=3, fontsize=7)
        axes[-1].set_xlabel('Tempo da simulação (ns)')
        fig.suptitle(f"{source.name}: rampa {state['scenario']['ramp_ns']} ns, "
                     f"{state['scenario']['idle_cycles']} ciclos inativos — TT / 1,8 V / 27 °C\n"
                     'Transiente real do circuito extraído; sem wire RC; não é caracterização PVT', fontsize=11)
        fig.tight_layout(rect=(0, 0, 1, .96)); fig.savefig(out/f'{name}.svg'); plt.close(fig)
    result = dict(status='ACTUAL_TRANSIENT_PLOTS', source_receipt_sha256=sha(source/'results.json'),
                  raw_sha256=sha(wave), plotter_sha256=sha(Path(__file__)),
                  artifacts={p.name: sha(p) for p in out.iterdir() if p.is_file()})
    (out/'results.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    sys.exit(main())
