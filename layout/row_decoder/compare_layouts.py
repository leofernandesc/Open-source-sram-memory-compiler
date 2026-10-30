#!/usr/bin/env python3
"""Compare actual pre-compaction/compact Magic paint; no parasitic extraction."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
LAYOUT = ROOT / 'layout/row_decoder'


def paint(path):
    sections = {}
    layer = None
    for line in path.read_text().splitlines():
        if line.startswith('<< '):
            layer = line[3:-3]
            sections.setdefault(layer, [])
        match = re.fullmatch(r'rect (-?\d+) (-?\d+) (-?\d+) (-?\d+)', line)
        if match and layer != 'checkpaint':
            sections[layer].append(tuple(map(int, match.groups())))
    return sections


def metrics(sections):
    rects = [rect for layer in sections.values() for rect in layer]
    x1, y1 = min(r[0] for r in rects), min(r[1] for r in rects)
    x2, y2 = max(r[2] for r in rects), max(r[3] for r in rects)
    # Calibration read from Magic: box 2000 internal units = 10 micrometres.
    return dict(bbox_internal=[x1,y1,x2,y2], width_um=(x2-x1)*.005,
                height_um=(y2-y1)*.005, bbox_area_um2=(x2-x1)*(y2-y1)*.005**2)


def main():
    old = paint(LAYOUT/'archive/precompact_20261008/row_decoder_flat.mag')
    remote = paint(LAYOUT/'archive/remote_7ad0348/row_decoder_flat.mag')
    new = paint(LAYOUT/'row_decoder_flat.mag')
    before, after = metrics(old), metrics(new)
    remote_dims = metrics(remote)
    plan = json.loads((LAYOUT/'routing_plan.json').read_text())
    old_script = (LAYOUT/'archive/precompact_20261008/route_row_decoder.tcl').read_text()
    old_trunk = len(re.findall(r'(?m)^m3_track \d+$', old_script)) * (44500-400)
    new_trunk = plan['m3_trunk_length_internal_units']
    remote_script = (LAYOUT/'archive/remote_7ad0348/route_row_decoder.tcl').read_text()
    remote_trunk = sum(int(hi)-int(lo) for lo, hi, _ in
                       re.findall(r'(?m)^m3_track (\d+) (\d+) (-?\d+)$', remote_script))
    output = LAYOUT/'reports/compaction'
    output.mkdir(parents=True, exist_ok=True)
    results = dict(before=before, remote_7ad0348=remote_dims, after=after,
                   bbox_area_reduction_percent=100*(1-after['bbox_area_um2']/before['bbox_area_um2']),
                   m3_trunk_before_um=old_trunk*.005, m3_trunk_after_um=new_trunk*.005,
                   m3_trunk_reduction_percent=100*(1-new_trunk/old_trunk),
                   bbox_area_reduction_vs_remote_percent=100*(1-after['bbox_area_um2']/remote_dims['bbox_area_um2']),
                   m3_trunk_remote_um=remote_trunk*.005,
                   m3_trunk_reduction_vs_remote_percent=100*(1-new_trunk/remote_trunk),
                   note='Physical bbox and planned M3 trunk lengths, including new shields; not extracted C or timing.')
    (output/'metrics.json').write_text(json.dumps(results, indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PatchCollection
    from matplotlib.patches import Rectangle, Patch
    colors = {'nwell':'#e9e5bc','ndiff':'#74bd84','pdiff':'#dca891','poly':'#ba615e',
              'metal1':'#4389c4','metal2':'#51a999','metal3':'#995dbc'}
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), constrained_layout=True)
    views = ((axes[0],old,before,'Histórico 39f5ebc'),
             (axes[1],remote,remote_dims,'Atualização remota 7ad0348'),
             (axes[2],new,after,'Compactado sobre 7ad0348'))
    for ax, sections, dims, title in views:
        for layer, color in colors.items():
            shapes = [Rectangle((x*.005,y*.005),(xx-x)*.005,(yy-y)*.005)
                      for x,y,xx,yy in sections.get(layer,[])]
            ax.add_collection(PatchCollection(shapes, facecolor=color, edgecolor='none', alpha=.85))
        ax.set_xlim(0,225)
        ax.set_ylim(-15,65)
        ax.set_aspect('equal')
        ax.set_xlabel('x (µm)'); ax.set_ylabel('y (µm)')
        ax.set_title(f"{title}: {dims['width_um']:.2f} × {dims['height_um']:.2f} µm; bbox {dims['bbox_area_um2']:.2f} µm²")
        ax.grid(alpha=.15)
    axes[0].legend(handles=[Patch(color=color,label=name) for name,color in colors.items()],
                   loc='lower right',ncol=4,fontsize=8)
    fig.suptitle('Decoder dinâmico: geometria real dos arquivos Magic, na mesma escala\n'
                 '29 MOS; sizing de 7ad0348 preservado no compacto; DRC/LVS passam; novo PEX pendente')
    fig.savefig(output/'layout_comparison.png',dpi=180)
    fig.savefig(output/'layout_comparison.pdf')
    plt.close(fig)
    print(json.dumps(results,indent=2))


if __name__ == '__main__':
    main()
