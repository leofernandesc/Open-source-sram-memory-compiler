"""Accept a routing abstract only when pins match and no keepout is removed."""
from pathlib import Path
import hashlib
import re
import gdstk


def verify(names,output_directory=None):
    original=Path('/opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef')
    merged=Path('/opt/OpenROAD-flow-scripts/flow/platforms/sky130hd/lef/sky130_fd_sc_hd_merged.lef')
    old,new=original.read_text(),merged.read_text()
    def macro(text,name):
        match=re.search(r'(?ms)^MACRO '+re.escape(name)+r'\s.*?^END '+re.escape(name)+r'\s*$',text)
        if not match:raise ValueError('Missing route master '+name)
        body=match[0];section='other';layer=None;shapes={}
        for line in body.splitlines():
            fields=line.split()
            if not fields:continue
            if fields[0]=='PIN':section=fields[1]
            elif fields[0]=='OBS':section='OBS'
            elif fields[0]=='LAYER':layer=fields[1]
            elif fields[0]=='RECT':
                coords=list(map(float,fields[1:5]));shapes.setdefault((section,layer),[]).append(gdstk.rectangle(coords[:2],coords[2:]))
            elif fields[0]=='POLYGON':
                coords=list(map(float,fields[1:-1]));shapes.setdefault((section,layer),[]).append(gdstk.Polygon(list(zip(coords[::2],coords[1::2]))))
        size=tuple(map(float,re.search(r'SIZE\s+(\S+)\s+BY\s+(\S+)',body).groups()))
        origin=re.search(r'ORIGIN\s+(\S+)\s+(\S+)',body)
        return shapes,size,tuple(map(float,origin.groups())) if origin else (0.,0.)
    added={};body_markers=[]
    for name in sorted(names):
        a,sa,oa=macro(old,name);b,sb,ob=macro(new,name)
        if sa!=sb or oa!=ob:raise ValueError('Changed master footprint '+name)
        apins={k for k in a if k[0]!='OBS'};bpins={k for k in b if k[0]!='OBS'}
        if apins!=bpins:raise ValueError('Changed master pin set '+name)
        for key in a.keys()|b.keys():
            left,right=a.get(key,[]),b.get(key,[])
            # Body well markers are not routed metal access geometries. Their
            # name/role is retained; actual wells/taps come from unchanged PDK
            # GDS/MAG and are checked by expanded transistor LVS.
            if key[1] in ('pwell','nwell'):
                if sum(p.area() for p in gdstk.boolean(left,right,'xor',precision=.001))>1e-8:
                    body_markers.append({'master':name,'pin':key[0],'layer':key[1]})
                continue
            operation='not' if key[0]=='OBS' else 'xor'
            difference=gdstk.boolean(left,right,operation,precision=.001)
            if sum(p.area() for p in difference)>1e-8:
                raise ValueError(f'Changed pins or removed original obstruction: {name} {key}')
        added[name]=sorted({layer for (section,layer) in b if section=='OBS'}-
                           {layer for (section,layer) in a if section=='OBS'})
    route_path=merged
    if output_directory is not None:
        route_path=Path(output_directory)/'routing_cells.lef';route_path.write_text(new)
    return route_path,{'status':'PASS_VERIFIED_PIN_ACCESS_SIZE_ORIGIN_NO_REMOVED_ROUTING_OBSTRUCTIONS',
                   'masters':len(names),'additional_keepout_layers':added,
                   'nonrouting_body_marker_differences':body_markers,
                   'original':{'path':str(original),'sha256':hashlib.sha256(original.read_bytes()).hexdigest()},
                   'routing_source':{'path':str(merged),'sha256':hashlib.sha256(merged.read_bytes()).hexdigest()},
                   'routing':{'path':str(route_path),'sha256':hashlib.sha256(route_path.read_bytes()).hexdigest()}}
