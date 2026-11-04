#!/usr/bin/env python3
"""Overview rendered from the actual final GDS; this image is not a DRC result."""
import json
from pathlib import Path
import sys
import gdstk
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection,PatchCollection
from matplotlib.patches import Rectangle
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_phase2_digital import ROOT,sha


def main():
    source=ROOT/'reports/phase2/final_gds';out=ROOT/'reports/phase2/layout_overview';out.mkdir(exist_ok=True)
    state=json.loads((source/'results.json').read_text())
    if state['status']!='PASS_GEOMETRY_LVS':raise ValueError('Verified final GDS required')
    path=source/'sram_4x8.gds';identity=sha(path);lib=gdstk.read_gds(path)
    top=next(c for c in lib.cells if c.name=='sram_4x8_wrapper')
    fig,ax=plt.subplots(figsize=(11,8));rectangles=[]
    for ref in top.references:
        if ref.cell.name=='leaf_fabric':continue
        box=ref.bounding_box()
        if box is None:continue
        a,b=box;rectangles.append(Rectangle(a,b[0]-a[0],b[1]-a[1]))
    ax.add_collection(PatchCollection(rectangles,facecolor='#d5d8dc',edgecolor='none',alpha=.65,zorder=0))
    for layer,label,color in [(71,'M4 routing / column access','#336bad'),(72,'M5 routing / rails','#d97c2b')]:
        polygons=top.get_polygons(layer=layer,datatype=20)
        ax.add_collection(PolyCollection([p.points for p in polygons],facecolor=color,edgecolor='none',alpha=.7,label=label))
    core=next(r for r in top.references if r.cell.name=='leaf_fabric');a,b=core.bounding_box()
    ax.add_patch(Rectangle(a,b[0]-a[0],b[1]-a[1],fill=False,edgecolor='#267447',lw=1.5,ls='--'))
    ax.text((a[0]+b[0])/2,b[1]+4,'401-MOS custom fabric',ha='center',color='#174d2d',fontsize=9)
    ax.text(10,377,'HD capture + phase logic + clock buffers + taps/fill',fontsize=9)
    ax.set(xlim=(-5,545),ylim=(-5,390),xlabel='x (µm)',ylabel='y (µm)',title='SRAM 4×8 — actual delivered GDSII, 1,493 MOS')
    ax.set_aspect('equal');ax.legend(loc='upper right',fontsize=8);fig.tight_layout();fig.savefig(out/'sram_4x8.png',dpi=170);plt.close(fig)
    if sha(path)!=identity:raise ValueError('GDS changed during rendering')
    (out/'results.json').write_text(json.dumps({'status':'RENDERED_FROM_VERIFIED_GDS','source_sha256':identity,
        'image_sha256':sha(out/'sram_4x8.png'),'scope':'Visual overview only; refer to final_gds DRC/LVS logs for verification'},indent=2)+'\n')


if __name__=='__main__':main()
