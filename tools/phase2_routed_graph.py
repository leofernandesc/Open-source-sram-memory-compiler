"""Independent graph audit: preserve binding, allowing only CLK buffers and fill/taps."""


def audit(original,routed):
    before=original['modules']['sram_4x8_wrapper'];after=routed['modules']['sram_4x8_wrapper']
    parent={}
    def find(n):
        parent.setdefault(n,n)
        if parent[n]!=n:parent[n]=find(parent[n])
        return parent[n]
    added=set(after['cells'])-set(before['cells']);buffers=[]
    for name in added:
        c=after['cells'][name];typ=c['type']
        if typ in ('sky130_fd_sc_hd__clkbuf_2','sky130_fd_sc_hd__clkbuf_4'):
            a=c['connections']['A'];x=c['connections']['X']
            if len(a)!=1 or len(x)!=1:raise ValueError('Non-scalar clock buffer')
            parent[find(x[0])]=find(a[0]);buffers.append(a[0])
        elif not typ.startswith(('sky130_fd_sc_hd__fill_','sky130_fd_sc_hd__tapvpwrvgnd_')):
            raise ValueError('Unexpected inserted functional cell: '+name)
    clk=after['ports']['CLK']['bits'][0]
    if any(find(bit)!=find(clk) for bit in buffers):raise ValueError('CTS buffer outside public CLK tree')
    mapping={}
    def compare(old,new):
        if len(old)!=len(new):raise ValueError('Changed port width')
        for a,b in zip(old,new):mapping.setdefault(a,set()).add(find(b))
    for name,c in before['cells'].items():
        if name not in after['cells']:raise ValueError('Lost original functional cell: '+name)
        other=after['cells'][name]
        if c['type']!=other['type']:raise ValueError('Changed functional master: '+name)
        supplies={'VDD','VSS','VPWR','VPB','VGND','VNB'}
        if set(c['connections'])-supplies!=set(other['connections'])-supplies:raise ValueError('Changed cell ports: '+name)
        for pin,nodes in c['connections'].items():
            if pin not in supplies:compare(nodes,other['connections'][pin])
    for name,p in before['ports'].items():
        if name in ('VDD','VSS'):continue # Explicitly checked by expanded body/rail LVS.
        if name not in after['ports']:raise ValueError('Lost public port')
        compare(p['bits'],after['ports'][name]['bits'])
    if any(len(group)!=1 for group in mapping.values()):raise ValueError('Routed binding net split/reconnection')
    roots=[next(iter(group)) for group in mapping.values()]
    if len(set(roots))!=len(roots):raise ValueError('Routed binding net short')
    return {'status':'PASS_GRAPH_PRESERVATION','original_instances':len(before['cells']),
            'inserted_clock_buffers':len(buffers),'other_inserted_instances':len(added)-len(buffers),
            'signal_groups':len(mapping),
            'scope':'All original signal pin connectivity/types preserved; added functional cells restricted to public CLK buffers; body/rail LVS remains mandatory'}
