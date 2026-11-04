"""Geometry-derived OpenROAD macro abstract; no timing model is characterized."""
from pathlib import Path
import json
import re
import gdstk


def emit(source,output):
    source,output=Path(source),Path(output)
    proof=json.loads((source/'results.json').read_text())
    if proof['status']!='PASS_LEAF_FABRIC' or proof.get('reimport_drc')!=0:
        raise ValueError('Fabric GDS must pass reimport checks before abstraction')
    library=gdstk.read_gds(source/'leaf_fabric.gds')
    cell=next(c for c in library.cells if c.name=='leaf_fabric')
    if cell.references:raise ValueError('Expected the verified flat fabric')
    bbox=cell.bounding_box();dx,dy=-bbox[0][0],-bbox[0][1]
    for p in cell.polygons:p.translate(dx,dy)
    for p in cell.paths:p.translate(dx,dy)
    for label in cell.labels:label.origin=(label.origin[0]+dx,label.origin[1]+dy)
    output.mkdir(parents=True,exist_ok=True)
    library.write_gds(output/'leaf_fabric.gds')
    width,height=cell.bounding_box()[1]
    layers={68:'met1',69:'met2',70:'met3',71:'met4',72:'met5'}
    metal={name:[p for p in cell.polygons if p.layer==number and p.datatype==20]
           for number,name in layers.items()}
    text=(source/'leaf_fabric.mag').read_text()
    pins={}
    for match in re.finditer(r'rlabel (?:metal[45]|via4) (-?\d+) (-?\d+) (-?\d+) (-?\d+) \d+ (\S+)\nport \d+',text):
        x=(int(match[1])+int(match[3]))*.0025+dx;y=(int(match[2])+int(match[4]))*.0025+dy
        name=match[5]
        # Export the entire physical landing. Insetting the PORT and leaving
        # the remaining copper in OBS creates an enclosing, unroutable ring.
        # Only containment probes use an epsilon to avoid float boundary noise.
        hx,hy=(.7,.7) if 'rlabel via4 ' in match[0] else (.6,.4)
        corners=[(x-hx,y-hy),(x+hx,y-hy),(x+hx,y+hy),(x-hx,y+hy)]
        probes=[(x-hx+.001,y-hy+.001),(x+hx-.001,y-hy+.001),
                (x+hx-.001,y+hy-.001),(x-hx+.001,y+hy-.001)]
        if not all(gdstk.inside(probes,metal['met4'])):
            raise ValueError('Declared pin access pad is not real M4 geometry: '+name)
        shapes={'met4':[gdstk.rectangle(corners[0],corners[2])]}
        if name in ('VDD','VSS','PRECH','SCLK','WE'):
            rails=[p for p in metal['met5'] if gdstk.inside([(x,y)],[p])[0]]
            if not rails:raise ValueError('Missing physical PG rail: '+name)
            shapes['met5']=rails
        pins[name]=shapes
    if len(pins)!=40:raise ValueError(f'Expected 40 fabric boundary pins, got {len(pins)}')
    lines=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;',
           'MACRO leaf_fabric','  CLASS BLOCK ;','  ORIGIN 0 0 ;',
           f'  SIZE {width:.6f} BY {height:.6f} ;','  SYMMETRY X Y ;']
    def shape(poly):
        pts=poly.points
        if len(pts)==4 and len(set(pts[:,0]))==2 and len(set(pts[:,1]))==2:
            a,b=poly.bounding_box();return f'RECT {a[0]:.6f} {a[1]:.6f} {b[0]:.6f} {b[1]:.6f} ;'
        return 'POLYGON '+' '.join(f'{x:.6f} {y:.6f}' for x,y in pts)+' ;'
    for name,shapes in pins.items():
        direction='INOUT' if name in ('VDD','VSS') else 'OUTPUT' if name.startswith(('DEC','DOUT')) else 'INPUT'
        use='POWER' if name=='VDD' else 'GROUND' if name=='VSS' else 'SIGNAL'
        lines += [f'  PIN {name}',f'    DIRECTION {direction} ;',f'    USE {use} ;','    PORT']
        for layer,polys in shapes.items():
            lines.append(f'      LAYER {layer} ;')
            lines.extend('        '+shape(p) for p in polys)
        lines += ['    END',f'  END {name}']
    lines.append('  OBS')
    for layer,polys in metal.items():
        ports=[p for shapes in pins.values() for p in shapes.get(layer,[])]
        obs=gdstk.boolean(polys,ports,'not',precision=.001) if ports else polys
        if layer=='met4':
            for name,shapes in pins.items():
                if 'met5' in shapes:continue
                a,b=shapes['met4'][0].bounding_box();cx,cy=(a[0]+b[0])/2,(a[1]+b[1])/2
                outside=[(a[0]-.002,cy),(b[0]+.002,cy),(cx,a[1]-.002),(cx,b[1]+.002)]
                if all(gdstk.inside(outside,obs)):
                    raise ValueError('Pin enclosed by a leftover M4 obstruction ring: '+name)
        lines.append(f'    LAYER {layer} ;')
        lines.extend('      '+shape(p) for p in obs)
    lines += ['  END','END leaf_fabric','END LIBRARY']
    (output/'leaf_fabric.lef').write_text('\n'.join(lines)+'\n')
    result={'status':'GEOMETRY_ABSTRACT_ONLY','size_um':[width,height],
            'pin_obstruction_audit':'PASS_NO_ENCLOSING_M4_OBS_RING',
            'source_to_positive_gds_offset_um':[dx,dy],'pins':list(pins),
            'timing':'No macro timing model; Fmax/STA closure not claimed'}
    (output/'abstract.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
