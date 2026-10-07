#!/usr/bin/env python3
"""Measure WL input capacitance of the extracted selected 6T bitcell."""
from __future__ import annotations
import argparse,csv,itertools,re,subprocess
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from run_cbl_device_capacitance import MODEL_LIB,run_deck

def load_pex(root):
 p=root/'layout'/'bitcell_6t'/'pex'/'bitcell_6t_pex.spice'; t=p.read_text()
 m=re.search(r'^\.subckt\s+(\S+)\s+(.+)$',t,re.M)
 if not m: raise RuntimeError('missing bitcell PEX header')
 if tuple(m.group(2).split()) != ('VDD','BL','BLB','VSS','WL'): raise RuntimeError(m.group(2))
 return t,m.group(1)

def deck(text,name,corner,vdd,temp,state,freq):
 q=vdd if state else 0.0; qb=0.0 if state else vdd
 return f'''* Extracted selected-bitcell WL capacitance.\n.lib "{MODEL_LIB}" {corner}\n.temp {temp:g}\n{text}\nVDD vdd 0 {vdd:g}\nVBL bl 0 {q:.12g}\nVBLB blb 0 {qb:.12g}\nVWL wl 0 DC 0 AC 1\nXCELL vdd bl blb 0 wl {name}\n.nodeset v(xcell.a_173_n1434.t0)={q:.12g} v(xcell.a_126_n1530.t1)={qb:.12g}\n.ac lin 1 {freq:.12g} {freq:.12g}\n.print ac imag(i(VWL))\n.end\n'''

def main():
 root=Path(__file__).resolve().parent.parent; p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--corners',nargs='+',default=['tt','ff','ss','fs','sf']); p.add_argument('--vdd-values',nargs='+',type=float,default=[1.62,1.80]); p.add_argument('--temps-c',nargs='+',type=float,default=[-40.0,27.0,125.0]); p.add_argument('--states',nargs='+',type=int,choices=[0,1],default=[0,1]); p.add_argument('--frequency-hz',type=float,default=1e6); p.add_argument('--timeout-s',type=float,default=60); p.add_argument('--workers',type=int,default=4); p.add_argument('--output',type=Path,default=root/'sims'/'bitcell_pex_wordline_capacitance_pvt.csv'); a=p.parse_args()
 text,name=load_pex(root); cases=list(itertools.product(a.corners,a.vdd_values,a.temps_c,a.states))
 def ex(c):
  corner,vdd,temp,state=c; r={'corner':corner,'vdd_v':vdd,'temp_c':temp,'state':state,'frequency_hz':a.frequency_hz,'cwl_bitcell_pex_ff':'','status':'ERROR','error':''}
  try: x,_=run_deck('ngspice',deck(text,name,corner,vdd,temp,state,a.frequency_hz),a.timeout_s); r['cwl_bitcell_pex_ff']=f'{x:.9f}'; r['status']='PASS'
  except (RuntimeError,subprocess.TimeoutExpired) as e:r['error']=str(e).replace('\n',' | ')[:1000]
  return r
 rows=[]
 with ThreadPoolExecutor(max_workers=a.workers) as pool:
  fs=[pool.submit(ex,c) for c in cases]
  for i,f in enumerate(as_completed(fs),1): rows.append(f.result()); print(f'completed {i}/{len(fs)}',flush=True) if i%20==0 or i==len(fs) else None
 rows.sort(key=lambda r:(r['corner'],float(r['vdd_v']),float(r['temp_c']),int(r['state'])))
 with a.output.open('w',newline='',encoding='utf-8') as s:w=csv.DictWriter(s,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 vals=[(float(r['cwl_bitcell_pex_ff']),r) for r in rows if r['status']=='PASS']; fails=[r for r in rows if r['status']!='PASS']
 if vals:
  lo=min(vals,key=lambda x:x[0]);hi=max(vals,key=lambda x:x[0]);r=hi[1];print(f"C_WL_BITCELL_PEX: min={lo[0]:.6f} fF max={hi[0]:.6f} fF at {r['corner']}/{r['vdd_v']}V/{r['temp_c']}C/q{r['state']}")
 print(f'PASS={len(rows)-len(fails)}/{len(rows)} CSV={a.output}');return 1 if fails else 0
if __name__=='__main__':raise SystemExit(main())
