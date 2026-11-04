#!/usr/bin/env python3
"""Map a physically bound wrapper and export independent HD transistor reference.

The frozen fabric is expanded for electrical/LVS reference. No macro delay
model is invented; phase/capture functionality requires transistor simulation.
"""
from __future__ import annotations
from collections import Counter
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from run_digital_regression import atomic_text,output_lock
from run_phase2_digital import add_power,sha,HD,LIB

ROOT=Path(__file__).resolve().parents[1]


def spice_from_json(design, hd_text):
    top=design['modules']['sram_4x8_wrapper']
    ports=top['ports']; aliases={}
    for name,p in ports.items():
        for i,bit in enumerate(p['bits']):
            aliases[bit]=name if len(p['bits'])==1 else f'{name}{i}'
    # Internal IDs give deterministic legal SPICE names, independent of escaped
    # HDL hierarchy names. Boundary names take priority over internal aliases.
    def net(bit):
        if bit in ('0','1'):
            return 'VSS' if bit=='0' else 'VDD'
        if not isinstance(bit,int):raise ValueError('Unknown/high-Z internal constant')
        return aliases.get(bit,f'n{bit}')
    definitions=[]; formal_lists={}; counts={}
    for typ in sorted({c['type'] for c in top['cells'].values()}):
        if typ=='leaf_fabric':continue
        if not typ.startswith('sky130_fd_sc_hd__'):raise ValueError('Unmapped physical cell: '+typ)
        match=re.search(r'(?ms)^\.subckt '+re.escape(typ)+r' .*?^\.ends[^\n]*',hd_text)
        if not match:raise ValueError('Missing HD transistor definition: '+typ)
        text=match[0]; definitions.append(text+'\n')
        formal_lists[typ]=text.splitlines()[0].split()[2:]
        counts[typ]=sum(bool(re.match(r'(?i)^x\S+\s',line)) for line in text.splitlines())
    header=[net(bit) for p in ports.values() for bit in p['bits']]
    for supply in ('VDD','VSS'):
        if supply not in header:header.append(supply)
    if len(set(header))!=len(header):raise ValueError('Aliased top ports')
    lines=['.subckt sram_4x8_wrapper '+' '.join(header)]
    fabric_ports=['VDD','VSS','A0','A1','PCLK','PRECH','SCLK','WE',
                  *[f'DIN{b}' for b in range(8)],*[f'DIN_B{b}' for b in range(8)],
                  *[f'DOUT{b}' for b in range(8)],*[f'ROW{r}' for r in range(4)],*[f'DEC{r}' for r in range(4)]]
    for index,(name,cell) in enumerate(sorted(top['cells'].items())):
        typ=cell['type'];connections=cell['connections']
        if typ!='leaf_fabric' and counts[typ]==0:
            if not typ.startswith(('sky130_fd_sc_hd__tap','sky130_fd_sc_hd__fill','sky130_ef_sc_hd__fill')):
                raise ValueError('Unexpected zero-device standard cell: '+typ)
            continue
        nodes=[]
        for formal in fabric_ports if typ=='leaf_fabric' else formal_lists[typ]:
            if formal in ('VPWR','VPB'):nodes.append('VDD')
            elif formal in ('VGND','VNB'):nodes.append('VSS')
            elif typ=='leaf_fabric' and formal in ('VDD','VSS'):nodes.append(formal)
            else:
                if formal not in connections or len(connections[formal])!=1:
                    raise ValueError(f'Unbound/scalar HD port: {name}.{formal}')
                nodes.append(net(connections[formal][0]))
        lines.append(f'Xmapped{index} '+' '.join(nodes)+' '+typ)
    lines.append('.ends sram_4x8_wrapper')
    return '\n'.join(definitions+lines)+'\n',header,counts


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',default='reports/phase2/physical_binding')
    args=p.parse_args();output=(ROOT/args.output).resolve()
    if not output.is_relative_to(ROOT/'reports/phase2') or output==ROOT/'reports/phase2':p.error('Output under reports/phase2 required')
    output.mkdir(parents=True,exist_ok=True)
    with output_lock(output):
        receipt={'status':'RUNNING','CORE':'NOT_EVALUATED','F2_FIS':'NOT_EVALUATED'}
        def publish():atomic_text(output/'results.json',json.dumps(receipt,indent=2)+'\n')
        publish()
        try:
            root=ROOT/'build/phase2';root.mkdir(parents=True,exist_ok=True)
            build=Path(tempfile.mkdtemp(prefix='binding-',dir=root));receipt['build_directory']=str(build.relative_to(ROOT))
            inputs=['rtl/sram_controller.v','rtl/sram_4x8_wrapper.v','physical/phase2/macro_binding.v','synth/sky130_tristate.v']
            for name in inputs:
                path=build/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,path)
            script=f'''read_liberty -lib {LIB}
read_verilog {' '.join(inputs[:3])}
tribuf
synth -top sram_4x8_wrapper -flatten -noabc
dfflibmap -liberty {LIB}
techmap -map synth/sky130_tristate.v
techmap
abc -liberty {LIB}
clean
check -assert
stat -liberty {LIB}
write_json binding.json
write_verilog -noattr -noexpr binding.v
'''
            (build/'binding.ys').write_text(script)
            result=subprocess.run(['yosys','-Q','-T','-s','binding.ys'],cwd=build,capture_output=True,text=True,timeout=180)
            atomic_text(output/'yosys.txt',result.stdout+result.stderr)
            if result.returncode:raise ValueError('Physical binding mapping failed')
            design=json.loads((build/'binding.json').read_text());top=design['modules']['sram_4x8_wrapper']
            inventory=Counter(c['type'] for c in top['cells'].values())
            if inventory['leaf_fabric']!=1 or sum(v for k,v in inventory.items() if k.startswith('sky130_fd_sc_hd__df'))!=20:
                raise ValueError('Lost custom fabric or capture registers')
            delays=[c for name,c in top['cells'].items() if 'phase_delay' in name]
            if len(delays)!=80 or any(c['type']!='sky130_fd_sc_hd__inv_1' for c in delays):
                raise ValueError('Physical delay chain was optimized or changed')
            source=HD/'spice/sky130_fd_sc_hd.spice'
            reference,ports,counts=spice_from_json(design,source.read_text())
            (build/'binding.spice').write_text(reference)
            (build/'binding_powered.v').write_text(add_power((build/'binding.v').read_text()))
            for name in ('binding.spice','binding.v','binding_powered.v','binding.json','binding.ys'):
                shutil.copyfile(build/name,output/name)
            receipt.update(status='PASS_MAPPING_ONLY',ports=ports,cells=dict(sorted(inventory.items())),
                           hd_mos=sum(inventory[t]*counts[t] for t in counts),
                           inputs={n:sha(ROOT/n) for n in inputs},pdk={str(LIB):sha(LIB),str(source):sha(source)})
        except Exception as error:receipt.update(status='FAIL',error=str(error))
        receipt['artifacts']={p.name:sha(p) for p in output.iterdir() if p.is_file() and p.name not in ('results.json','.run.lock')}
        publish();print(json.dumps({k:receipt[k] for k in ('status','CORE','F2_FIS')},indent=2))
        if 'error' in receipt:print(receipt['error'])
        return 0 if receipt['status']=='PASS_MAPPING_ONLY' else 1


if __name__=='__main__':raise SystemExit(main())
