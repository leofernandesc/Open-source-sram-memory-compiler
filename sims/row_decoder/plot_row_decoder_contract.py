#!/usr/bin/env python3
"""Export measured decoder contract and robustness comparisons as PNG/PDF.

Read archived CSVs only; rejected points are retained. These figures are
experimental pre-layout screens, not a macro timing/noise specification.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def read(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tables', type=Path, required=True)
    parser.add_argument('--suite', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='Output stem; emits PNG, PDF and provenance JSON')
    args = parser.parse_args()
    sources = [args.tables/'boundary_grid.csv', args.tables/'robustness_candidates.csv', args.suite/'summary.csv']
    grid, candidates, suite = [read(p) for p in sources]
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), constrained_layout=True)
    ax = axes[0, 0]
    profiles = ['tt', 'slow', 'fast']
    for profile in profiles:
        points = sorted((r for r in grid if r['campaign']=='timing' and r['profile']==profile), key=lambda r: float(r['value']))
        ax.plot([float(r['value']) for r in points], [100*int(r['combined_screen_pass'])/int(r['cases']) for r in points], 'o-', label=profile)
    ax.set(xlabel='Address completes before evaluation (ps)', ylabel='Combined screen pass (%)', title='B6: arrival grid, 12 ordered changes per point', ylim=(-4,104))
    ax.legend()
    ax = axes[0, 1]
    for profile in profiles:
        for campaign, style in [('low_phase','-'), ('high_phase','--')]:
            points = sorted((r for r in grid if r['campaign']==campaign and r['profile']==profile), key=lambda r: float(r['value']))
            ax.plot([float(r['value']) for r in points], [100*int(r['combined_screen_pass'])/int(r['cases']) for r in points], style, marker='.', label=f'{profile} {campaign.split("_")[0]}')
    ax.set(xlabel='Phase length between 50% crossings (ns)', ylabel='Combined screen pass (%)', title='B6: phase grid, four repeated addresses', xscale='log', ylim=(-4,104))
    ax.legend(fontsize=8, ncol=2)
    ax = axes[1, 0]
    for profile in profiles:
        values = {}
        for r in suite:
            if r['campaign']=='charge' and r['profile']==profile:
                q=float(r['charge_fc'])
                values[q]=max(values.get(q,0), float(r['wrong_row_peak_v'])/float(r['vdd_v']))
        ax.plot(sorted(values), [values[q] for q in sorted(values)], 'o-', label=profile)
    ax.axhline(.1,color='firebrick',ls=':',label='10% wrong-row screen')
    ax.set(xlabel='Withdrawn charge, 120 ps trapezoid (fC)', ylabel='Worst unselected DEC/WL peak / VDD', title='B6: both injected nodes, finite perturbation experiment')
    ax.legend(fontsize=8)
    ax = axes[1, 1]
    points=sorted((r for r in candidates if r['campaign']=='robustness'), key=lambda r: float(r['diagnostic_headroom_mv']),reverse=True)[:12]
    baseline=[r for r in candidates if r['campaign']=='robustness' and r['candidate']=='B6']
    if baseline and baseline[0] not in points:
        points.append(baseline[0])
    points.reverse()
    values=[float(r['diagnostic_headroom_mv']) for r in points]
    ax.barh(range(len(points)), values, color=['#238b45' if r['eligible']=='True' else '#cb181d' for r in points])
    ax.set_yticks(range(len(points)), [r['candidate'] for r in points], fontsize=8)
    ax.axvline(0,color='black',lw=.8)
    ax.set(xlabel='1.95 V minus largest terminal magnitude (mV)', title='Refined candidate screens: differing declared case sets')
    for a in axes.flat:
        a.grid(True,alpha=.2)
    fig.suptitle('Dynamic 2-to-4 decoder — measured pre-layout comparisons\nCoarse B6 grids; refined candidate diagnostics. No signed-domain/reliability or Fmax clearance.',fontsize=12)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    for extension in ('.png','.pdf'):
        fig.savefig(args.output.with_suffix(extension),dpi=180)
    args.output.with_suffix('.json').write_text(json.dumps(dict(
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        note='Green means all declared screens pass in that candidate case set; differing sets do not constitute a common final qualification.'),indent=2)+'\n')


if __name__=='__main__':
    main()
