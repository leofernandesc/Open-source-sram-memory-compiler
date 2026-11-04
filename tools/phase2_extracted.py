"""Name-only probe binding for the LVS-approved, flat extracted transistor netlist.

No circuit connection is repaired from HDL. Every original extracted MOS and
junction parameter is retained; ext equivalences only locate observation nodes.
"""
import re


def bind(extracted,ext,design):
    parent={}
    def clean(s):return s.replace('\\','')
    def find(s):
        s=clean(s);parent.setdefault(s,s)
        if parent[s]!=s:parent[s]=find(parent[s])
        return parent[s]
    for line in ext.splitlines():
        q=re.findall(r'"([^"]*)"',line)
        if line.startswith('node ') and q:find(q[0])
        elif line.startswith('equiv ') and len(q)==2:parent[find(q[1])]=find(q[0])
    lines=[]
    for line in extracted.splitlines():
        if line.startswith('+'):lines[-1]+=' '+line[1:].strip()
        else:lines.append(line)
    header=next(l.split()[2:] for l in lines if l.lower().startswith('.subckt '))
    cards=[l.split() for l in lines if re.match(r'(?i)^x\S+\s',l)]
    if not cards:raise ValueError('Empty extracted circuit')
    raw_nodes=set(header)|{n for c in cards for n in c[1:5]}
    representatives={}
    for node in raw_nodes:representatives.setdefault(find(node),set()).add(node)
    def actual(label):
        if clean(label) not in parent:raise ValueError('Missing extracted observation label: '+label)
        group=representatives.get(find(label),set())
        if len(group)!=1:raise ValueError('Ambiguous/missing extracted net representative: '+label)
        return next(iter(group))
    public={n:re.sub(r'^(ADDR|DATA)\[(\d+)\]$',r'\1\2',clean(n)) for n in header}
    legal={n:public.get(n,f'e{i}') for i,n in enumerate(sorted(raw_nodes))}
    if len(set(legal.values()))!=len(legal):raise ValueError('Extracted net naming collision')
    top=design['modules']['sram_4x8_wrapper'];bit_groups={}
    # Cross-check all physical signal-pin aliases against the reference graph.
    # Reject both split connections and shorts instead of compensating for them.
    for name,cell in top['cells'].items():
        for pin,bits in cell['connections'].items():
            if len(bits)!=1:raise ValueError('Expected scalar physical cell port')
            if pin in ('VDD','VSS','VPWR','VPB','VGND','VNB'):continue
            bit_groups.setdefault(bits[0],set()).add(actual(name+'.'+pin))
    for name,port in top['ports'].items():
        for i,bit in enumerate(port['bits']):
            bit_groups.setdefault(bit,set()).add(actual(name if len(port['bits'])==1 else f'{name}[{i}]'))
    if any(len(group)!=1 for group in bit_groups.values()):raise ValueError('Extracted signal net split')
    bit_nodes={bit:next(iter(group)) for bit,group in bit_groups.items()}
    if len(set(bit_nodes.values()))!=len(bit_nodes):raise ValueError('Extracted signal net short')
    aliases={}
    for name,port in top['ports'].items():
        for i,bit in enumerate(port['bits']):aliases[bit]=name if len(port['bits'])==1 else f'{name}{i}'
    probes={f'v(xdut.{aliases.get(bit,f"n{bit}")})':f'v(xdut.{legal[node]})' for bit,node in bit_nodes.items()}
    for name in public.values():probes[f'v({name})']=f'v({name})'
    cells=sorted(top['cells'].items());fabric=next(i for i,(_,c) in enumerate(cells) if c['type']=='leaf_fabric')
    fabric_name=cells[fabric][0]
    for r in range(4):
        node=actual(fabric_name+f'.wl_driver_{r}.WL')
        probes[f'v(xdut.xmapped{fabric}.WL{r})']=f'v(xdut.{legal[node]})'
    result=['* Actual flat GDS extraction; nodes renamed only',
            '.subckt sram_4x8_wrapper '+' '.join(legal[n] for n in header)]
    for card in cards:
        result.append(' '.join([card[0],*[legal[n] for n in card[1:5]],*card[5:]]))
    result.append('.ends sram_4x8_wrapper')
    return '\n'.join(result)+'\n',probes,{'mos':len(cards),'signal_nets_checked':len(bit_nodes),
                                             'interpretation':'Name-only observation binding; MOS connectivity and parameters unchanged'}
