#!/usr/bin/env python3
"""Measure extracted WL capacitance of the representative physical 8-bit SRAM row."""
from __future__ import annotations
import argparse, csv, itertools, re, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from run_cbl_device_capacitance import MODEL_LIB, run_deck

ACCESS_RE = re.compile(
    r"^X\S+\s+(BLB?\d)(?:\.t\d+)?\s+WL(?:\.t\d+)?\s+(a_\d+_-?\d+(?:\.t\d+)?)\s+\S+\s+sky130_fd_pr__nfet_01v8\b",
    re.MULTILINE,
)

def load_pex(root: Path) -> tuple[str, str, dict[str, str]]:
    path = root / 'layout' / 'row_8_wl' / 'pex' / 'row_8_wl_pex.spice'
    text = path.read_text(encoding='utf-8')
    header = re.search(r"^\.subckt\s+(\S+)\s+(.+?)(?=\n[^+])", text, re.MULTILINE | re.DOTALL)
    if not header:
        raise RuntimeError(f'missing subcircuit header: {path}')
    pin_text = re.sub(r"\n\+\s*", " ", header.group(2)).strip()
    pins = tuple(pin_text.split())
    expected = ('VDD','VSS','WL') + tuple(x for i in range(8) for x in (f'BL{i}', f'BLB{i}'))
    if pins != expected:
        raise RuntimeError(f'unexpected row PEX pins: {pins}')
    access: dict[str, str] = {}
    for m in ACCESS_RE.finditer(text):
        access[m.group(1)] = m.group(2)
    if len(access) != 16:
        raise RuntimeError(f'expected 16 access storage nodes, got {len(access)}')
    return text, header.group(1), access

def make_deck(text: str, name: str, access: dict[str,str], corner: str, vdd: float, temp_c: float, state: int, freq: float) -> str:
    q = vdd if state else 0.0
    qb = 0.0 if state else vdd
    sources=[]
    inst=[]
    nodesets=[]
    for i in range(8):
        sources.append(f'VBL{i} bl{i} 0 {q:.12g}')
        sources.append(f'VBLB{i} blb{i} 0 {qb:.12g}')
        inst += [f'bl{i}', f'blb{i}']
        nodesets.append(f'.nodeset v(xrow.{access[f"BL{i}"]})={q:.12g}')
        nodesets.append(f'.nodeset v(xrow.{access[f"BLB{i}"]})={qb:.12g}')
    return f'''* Representative 8-bit physical-row WL capacitance.\n.lib "{MODEL_LIB}" {corner}\n.temp {temp_c:g}\n{text}\nVDD vdd 0 {vdd:g}\nVWL wl 0 DC 0 AC 1\n{chr(10).join(sources)}\nXROW vdd 0 wl {' '.join(inst)} {name}\n{chr(10).join(nodesets)}\n.ac lin 1 {freq:.12g} {freq:.12g}\n.print ac imag(i(VWL))\n.end\n'''

def main() -> int:
    root=Path(__file__).resolve().parent.parent
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corners', nargs='+', default=['tt','ff','ss','fs','sf'])
    p.add_argument('--vdd-values', nargs='+', type=float, default=[1.62,1.80])
    p.add_argument('--temps-c', nargs='+', type=float, default=[-40.0,27.0,125.0])
    p.add_argument('--states', nargs='+', type=int, choices=[0,1], default=[0,1])
    p.add_argument('--frequency-hz', type=float, default=1e6)
    p.add_argument('--timeout-s', type=float, default=60.0)
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--output', type=Path, default=root/'sims'/'row_8_wl_pex_capacitance_pvt.csv')
    a=p.parse_args()
    text,name,access=load_pex(root)
    cases=list(itertools.product(a.corners,a.vdd_values,a.temps_c,a.states))
    def execute(case):
        corner,vdd,temp,state=case
        row={'corner':corner,'vdd_v':vdd,'temp_c':temp,'state':state,'frequency_hz':a.frequency_hz,'cwl_pex_ff':'','status':'ERROR','error':''}
        try:
            c,_=run_deck('ngspice', make_deck(text,name,access,corner,vdd,temp,state,a.frequency_hz), a.timeout_s)
            row['cwl_pex_ff']=f'{c:.9f}'; row['status']='PASS'
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            row['error']=str(e).replace('\n',' | ')[:1000]
        return row
    rows=[]
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        futs=[pool.submit(execute,c) for c in cases]
        for i,f in enumerate(as_completed(futs),1):
            rows.append(f.result())
            if i%20==0 or i==len(futs): print(f'completed {i}/{len(futs)}', flush=True)
    rows.sort(key=lambda r:(r['corner'],float(r['vdd_v']),float(r['temp_c']),int(r['state'])))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('w',newline='',encoding='utf-8') as s:
        w=csv.DictWriter(s,fieldnames=list(rows[0]),lineterminator='\n'); w.writeheader(); w.writerows(rows)
    fails=[r for r in rows if r['status']!='PASS']
    vals=[(float(r['cwl_pex_ff']),r) for r in rows if r['status']=='PASS']
    if vals:
        lo=min(vals,key=lambda x:x[0]); hi=max(vals,key=lambda x:x[0])
        r=hi[1]
        print(f"C_WL_ROW8_PEX: min={lo[0]:.6f} fF max={hi[0]:.6f} fF at {r['corner']}/{r['vdd_v']}V/{r['temp_c']}C/q{r['state']}")
    print(f'PASS={len(rows)-len(fails)}/{len(rows)} CSV={a.output}')
    return 1 if fails else 0
if __name__=='__main__': raise SystemExit(main())
