#!/usr/bin/env python3
"""Independent stream/terminal checks and extracted-cell write/read pilot."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import numpy as np
import gdstk

from run_direct_abutment import ROOT,RC,SETUP,sha,run,normal_mos
from run_phase2_extracted_access import model_closure
from phase2_resources import preflight


def cards(text):
    return [line.split() for line in text.splitlines() if re.match(r'(?i)^x\S+\s',line)]


def inspect_array(text, rows, cols):
    """Derive storage from access device gates/bitlines, not cell instance names."""
    devices=cards(text)
    if len(devices)!=6*rows*cols:raise ValueError('Wrong array device count')
    states={};used=set()
    for row in range(rows):
        accesses=[f for f in devices if f[2]==f'WL{row}']
        if len(accesses)!=2*cols:raise ValueError('Wordlines alias or access count differs')
        for bit in range(cols):
            pair=[]
            for line in ('BL','BLB'):
                found=[f for f in accesses if f'{line}{bit}' in (f[1],f[3])]
                if len(found)!=1:raise ValueError('Column bitline alias/missing access')
                f=found[0];p=dict(re.findall(r'(\w+)=([^\s]+)',' '.join(f)))
                if f[4]!='VSS' or f[5]!='sky130_fd_pr__nfet_01v8' or abs(float(p['w'])-.6)>1e-10 or float(p['l'])!=.15:
                    raise ValueError('Access body/type/dimension changed')
                pair.append(f[3] if f[1]==f'{line}{bit}' else f[1]);used.add(f[0])
            q,qb=pair
            if q==qb or q in states.values() or qb in states.values():raise ValueError('Storage nodes alias')
            states[f'Q_{row}_{bit}']=q;states[f'QB_{row}_{bit}']=qb
            for node,gate in ((q,qb),(qb,q)):
                for rail,model,width in [('VDD','sky130_fd_pr__pfet_01v8',.42),('VSS','sky130_fd_pr__nfet_01v8',1.26)]:
                    matches=[f for f in devices if f[2]==gate and set((f[1],f[3]))=={node,rail} and f[4]==rail and f[5]==model]
                    if len(matches)!=1:raise ValueError('6T cross-coupling/rail/body error')
                    p=dict(re.findall(r'(\w+)=([^\s]+)',' '.join(matches[0])))
                    if float(p['w'])!=width or float(p['l'])!=.15:raise ValueError('Storage sizing changed')
                    used.add(matches[0][0])
    if len(used)!=len(devices):raise ValueError('Unaccounted/duplicated storage MOS')
    return states


def stream(source, out, rows, cols):
    state=json.loads((source/'results.json').read_text())
    if state['status']!='PASS_PHYSICAL':raise ValueError('Need passing physical input')
    for n,h in state['artifacts'].items():
        if sha(source/n)!=h:raise ValueError('Changed physical artifact '+n)
    gds=next(source.glob('*.gds'));lib=gdstk.read_gds(gds)
    tops=lib.top_level()
    if len(tops)!=1:raise ValueError('Wrong GDS top')
    top=tops[0];leaf=next(c for c in lib.cells if c.name=='bitcell_6t_abut')
    box=np.asarray(leaf.bounding_box());w,h=box[1]-box[0]
    if not np.allclose(box[0],[0,0]) or not np.allclose(top.bounding_box(),[[0,0],[cols*w,rows*h]]):raise ValueError('Unexpected physical bounds/gap')
    if rows*cols>1:
        origins=sorted(tuple(ref.origin) for ref in top.references)
        if origins!=sorted((b*w,r*h) for r in range(rows) for b in range(cols)):raise ValueError('Gap or orientation in tile placement')
        if any(ref.rotation or ref.x_reflection or ref.magnification!=1 for ref in top.references):raise ValueError('Unexpected transform')
    # Derive tracks from actual labels and polygon membership across seams.
    labels={l.text:np.asarray(l.origin) for l in leaf.labels};contacts=0
    for row in range(rows):
        for bit in range(cols-1):
            for name in ('WL','VDD','VSS'):
                layer=70 if name=='WL' else 71
                # Power crosses the horizontal seam on M3 at its real rail y,
                # not the vertical M4 access label near the bottom edge.
                y=labels[name][1]+row*h if name=='WL' else (13.25 if name=='VDD' else 3.)+row*h
                pts=[((bit+1)*w-.001,y),((bit+1)*w+.001,y)]
                if not all(gdstk.inside(pts,top.get_polygons(layer=70,datatype=20))):raise ValueError('Missing horizontal seam '+name)
                contacts+=1
    for row in range(rows-1):
        for bit in range(cols):
            for name in ('BL','BLB','VDD','VSS'):
                x=labels[name][0]+bit*w;pts=[(x,(row+1)*h-.001),(x,(row+1)*h+.001)]
                if not all(gdstk.inside(pts,top.get_polygons(layer=71,datatype=20))):raise ValueError('Missing vertical seam '+name)
                contacts+=1
    build=Path(tempfile.mkdtemp(prefix='stream-',dir=ROOT/'build/direct_abutment'))
    commands=f'''gds read {gds}
load {top.name}
select top cell
expand
flatten stream_flat
load stream_flat
drc euclidean on
drc style drc(full)
drc on
drc check
drc catchup
puts "STREAM_DRC=[llength [drc listall why]]"
puts "STREAM_DETAILS=[drc listall why]"
save stream_flat
extract all
ext2spice lvs
ext2spice scale off
ext2spice -o {out}/stream_extracted.spice
quit -noprompt
'''
    (out/'stream.tcl').write_text(commands)
    log=run(['magic','-dnull','-noconsole','-rcfile',RC],build,out/'magic.txt',commands)
    if re.findall(r'^STREAM_DRC=(\d+)$',log,re.M)!=['0']:raise ValueError('GDS stream DRC failed')
    text=(out/'stream_extracted.spice').read_text();normalized,count=normal_mos(text,top.name)
    if count!=rows*cols*6:raise ValueError('Wrong streamed MOS count')
    (out/'layout_mos.spice').write_text(normalized);shutil.copyfile(source/'reference.spice',out/'reference.spice')
    run(['netgen','-batch','lvs',f'{out}/layout_mos.spice {top.name}',f'{out}/reference.spice {top.name}',SETUP,out/'lvs.txt'],build,out/'netgen.txt')
    lvs=(out/'lvs.txt').read_text()
    if 'Final result: Circuits match uniquely.' not in lvs or re.search(r'(?i)property errors|do not match|black.box',lvs):raise ValueError('Stream LVS failed')
    states=inspect_array(text,rows,cols) if rows*cols>1 else {}
    return dict(status='PASS_STREAM_AND_INDEPENDENT_STRUCTURE',drc=0,lvs='EXPANDED_MATCH',mos=count,
                gds_sha256=sha(gds),bbox_um=top.bounding_box(),tile_dimensions_um=[w,h],
                seam_contacts_checked=contacts,storage_nodes=states)


def electrical(source,out,rows,cols):
    if (rows,cols)!=(2,2):raise ValueError('This focused electrical fixture is the 2x2 gate only')
    prior=json.loads((source/'results.json').read_text())
    if prior['status']!='PASS_STREAM_AND_INDEPENDENT_STRUCTURE':raise ValueError('Stream qualification required first')
    text=(source/'stream_extracted.spice').read_text();states=inspect_array(text,rows,cols);fs=cards(text)
    ports=['VDD','VSS','WL0','WL1','BL0','BLB0','BL1','BLB1']
    internal=sorted({n for f in fs for n in f[1:5]}-set(ports));aliases={n:f'n{i}' for i,n in enumerate(internal)}
    binding=['.subckt array_2x2 '+ ' '.join(ports)]
    binding+=[' '.join([f[0],*[aliases.get(n,n) for n in f[1:5]],*f[5:]]) for f in fs]
    binding+=['.ends array_2x2'];(out/'binding.spice').write_text('\n'.join(binding)+'\n')
    operations=[('write',0,1),('write',1,2),('read',0,1),('read',1,2),
                ('write',0,2),('read',0,2),('read',1,2),('idle',0,0),('idle',0,0),
                ('write',1,1),('read',0,2),('read',1,1)]
    signals={n:[(0,0),(1,0)] for n in ['WL0','WL1','WE','PRE','D0','DB0','D1','DB1']}
    signals['PRE']=[(0,0),(1,1.8)]
    def event(n,t,v):signals[n].extend([(t,signals[n][-1][1]),(t+.05,v)])
    records=[];known={}
    for i,(op,row,word) in enumerate(operations):
        edge=10+20*i
        if op!='idle':
            event('PRE',edge-1,0);event('WE',edge-.5,1.8 if op=='write' else 0)
            for b in range(2):event(f'D{b}',edge-2,1.8*((word>>b)&1));event(f'DB{b}',edge-2,1.8*(1-((word>>b)&1)))
            event(f'WL{row}',edge+1,1.8);event(f'WL{row}',edge+4,0);event('WE',edge+5,0);event('PRE',edge+6,1.8)
        if op=='write':known[row]=word
        records.append(dict(cycle=i,operation=op,row=row,word=word,edge_ns=edge,known=dict(known)))
    models=ROOT  # Keep actual PDK path, no simplified device substitutes.
    model=Path('/opt/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice');model_hashes=model_closure(model)
    vectors=['v(VDD)','v(WL0)','v(WL1)','v(BL0)','v(BLB0)','v(BL1)','v(BLB1)']+[f'v(xdut.{aliases[n]})' for n in states.values()]
    deck=['* New 2x2 extracted abutment: external drivers only; no internal initialization',
          f'.lib "{model}" tt','.include "binding.spice"','.temp 27',
          '.options method=gear klu','.model WSW SW(Ron=50 Roff=1e12 Vt=.9 Vh=.1)',
          '.model PSW SW(Ron=100 Roff=1e12 Vt=.9 Vh=.1)','VDD_SRC VDD 0 PWL(0 0 1n 1.8)']
    deck += [f'V_{n} {n} 0 PWL('+ ' '.join(f'{t:g}n {v:g}' for t,v in ev)+')' for n,ev in signals.items()]
    for b in range(2):
        for line,driver in [('BL','D'),('BLB','DB')]:
            deck += [f'SP_{line}{b} {line}{b} VDD PRE 0 PSW',f'SW_{line}{b} {line}{b} {driver}{b} WE 0 WSW',f'C_{line}{b} {line}{b} 0 10f']
    deck += ['XDUT VDD 0 WL0 WL1 BL0 BLB0 BL1 BLB1 array_2x2','.control','set num_threads=1','set wr_singlescale','set wr_vecnames',
             'tran 10p 250n 0 10p','wrdata waveform.dat '+' '.join(vectors),'quit','.endc','.end']
    (out/'bench.spice').write_text('\n'.join(deck)+'\n')
    build=Path(tempfile.mkdtemp(prefix='electrical2x2-',dir=ROOT/'build/direct_abutment'))
    for n in ('binding.spice','bench.spice'):shutil.copyfile(out/n,build/n)
    log=run(['ngspice','-n','-b','bench.spice'],build,out/'ngspice.txt',timeout=180)
    if 'ngspice-44.2 done' not in log:raise ValueError('No successful native completion')
    raw=build/'waveform.dat';data=np.loadtxt(raw,skiprows=1)
    if data.shape[1]!=len(vectors)+1 or not np.all(np.isfinite(data)) or data[-1,0]<249.9e-9 or not np.all(np.diff(data[:,0])>0):raise ValueError('Incomplete/invalid raw')
    checks=[]
    def level(value,bit):return 1.44<=value<=1.98 if bit else -.18<=value<=.36
    for r in records:
        sample=np.searchsorted(data[:,0],(r['edge_ns']+12)*1e-9)
        for row,word in r['known'].items():
            for b in range(2):
                for prefix,invert in [('Q',False),('QB',True)]:
                    name=f'{prefix}_{row}_{b}';v=float(data[sample,7+list(states).index(name)+1]);bit=((word>>b)&1)^invert
                    checks.append(dict(kind='stored_after_access_or_idle',cycle=r['cycle'],node=name,expected=bit,voltage_v=v,status='PASS' if level(v,bit) else 'FAIL'))
        if r['operation']=='read':
            sample=np.searchsorted(data[:,0],(r['edge_ns']+2.5)*1e-9)
            for b in range(2):
                delta=float(data[sample,4+2*b]-data[sample,5+2*b])*(1 if (r['word']>>b)&1 else -1)
                checks.append(dict(kind='signed_differential_read',cycle=r['cycle'],bit=b,differential_v=delta,status='PASS' if delta>=.1 else 'FAIL'))
    (out/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    np.savetxt(out/'waveform_excerpt.csv',data[::40],delimiter=',',header=','.join(['time',*vectors]),comments='')
    return dict(status='PASS_ELECTRICAL' if all(c['status']=='PASS' for c in checks) else 'FAIL_ELECTRICAL',
                condition=dict(corner='tt',vdd_v=1.8,temp_c=27,bitline_cap_ff=10),checks=len(checks),failures=sum(c['status']!='PASS' for c in checks),
                cycles=records,vectors=vectors,raw_sha256=sha(raw),build_directory=str(build.relative_to(ROOT)),model_inputs=model_hashes,
                scope='Physical 2x2 storage and differential read with external ideal controls; no peripheral/sense/capture claim; no wire RC')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--electrical',action='store_true');p.add_argument('--rows',type=int,default=2);p.add_argument('--cols',type=int,default=2);a=p.parse_args()
    source=(ROOT/a.source).resolve();out=(ROOT/a.output).resolve()
    if not out.is_relative_to(ROOT/'reports/direct_abutment') or out.exists():p.error('New output directory under reports/direct_abutment required')
    out.mkdir(parents=True);record=dict(status='RUNNING',resources=preflight(ROOT),source_receipt_sha256=sha(source/'results.json'),script_sha256=sha(Path(__file__)))
    try:record.update(electrical(source,out,a.rows,a.cols) if a.electrical else stream(source,out,a.rows,a.cols))
    except Exception as e:record.update(status='FAIL',error=f'{type(e).__name__}: {e}')
    record['artifacts']={q.name:sha(q) for q in out.iterdir() if q.is_file() and q.name!='results.json'}
    (out/'results.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:v for k,v in record.items() if k not in ('artifacts','model_inputs','cycles','vectors')},indent=2))
    return 0 if record['status'].startswith('PASS') else 1


if __name__=='__main__':raise SystemExit(main())
