#!/usr/bin/env python3
"""Generate and audit an offline TT shared-SCLK cut. This CLI has no simulator action."""

import argparse
from collections import Counter, defaultdict, deque
import csv
from decimal import Decimal, localcontext
from itertools import combinations
import json
from pathlib import Path
import re

import numpy as np

from phase3_sclk_loaded import (
    BUILD, GATES, PCH, PDK, PEX, PEX_SHA, Q_NAMES, REFERENCE, ROOT, SCLK,
    WORDLINES, WRITE_BOUNDARIES, bit_probes, branch, cycle_plan, inventory, load,
    model_closure, new_directory, pinned, pull_region, rc_node_map, require, sha256, write_json,
)
from phase3_sclk_loaded_ramp import CARD, HORIZON, INITIAL, JOIN, OFFSET, SUPPLY
from phase3_sense3_precondition import compress, pwl, pwl_tokens, write_knots
from run_phase3_data3_tt import points as public_pwl, value_at
from run_phase3_sense3_isolation import ResistanceGraph

PARENT = BUILD/'sclk_shared_loaded_20261120'
PARENT_SHA = '9e72e7e98baf18ff93901d4f1880cca4a3e452cdbbc427010140b3bca8edf854'
RAMP = BUILD/'sclk_shared_ramp_20261120'
RAMP_SHA = '92ed4fce4a3156c2b9533248f0df13b8fa1d74a9e4373f9acf768d67a7c5be76'
HISTORIC_ERROR = '68439bd68677ddf306e6f119e9ac89da67d6e552c7014f7db023ca04a03712be'
FAILED_NODE = 'rc7913'
UNKNOWN_INCLUDE = 'boundary_models_PENDING.spice'
RAILS = ('VDD','VSS')


def checked_inventory(text):
    data=inventory(text)
    identifiers=[l.split()[0] for l in text.splitlines() if re.match(r'^[XRC]\d+ ',l)]
    require(len(identifiers)==len(data),'Duplicate native card identifier')
    return data


def cap_ff(text):
    voltage=re.fullmatch(r'([+-]?[\d.]+(?:[Ee][+-]?\d+)?)([afpnumk]?)',text,re.I)
    require(voltage is not None,f'Unsupported capacitance {text}')
    number,unit=voltage.groups()
    scale={'a':-3,'f':0,'p':3,'n':6,'u':9,'m':12,'':15,'k':18}
    value=Decimal(number).scaleb(scale[unit.lower()])
    require(value>=0,f'Negative capacitance {text}')
    return value


def index_cards(cards):
    by_node=defaultdict(list)
    for name,card in cards.items():
        pins=card[:4] if name.startswith('X') else card[:2]
        for node in dict.fromkeys(pins):
            by_node[node].append(name)
    return by_node


def other_end(card,node):
    a,b=card[:2]
    require(a!=b and node in (a,b),'Invalid two-terminal topology')
    return b if a==node else a


def isolated_star(node,by_node,cards):
    edges=by_node[node]
    if not edges or any(not n.startswith('C') for n in edges):
        return None
    neighbors=defaultdict(Decimal)
    for n in edges:
        p=cards[n]
        if p[0]!=p[1] and (cap:=cap_ff(p[2])):
            neighbors[other_end(p,node)]+=cap
    return dict(sorted(neighbors.items()))


def eliminate_star(neighbors):
    """Reduce the capacitance matrix of a conductor with conserved free charge."""
    with localcontext() as ctx:
        ctx.prec=40
        total=sum(neighbors.values(),Decimal(0))
        require(total>0,'Empty capacitive star')
        return [(i,j,ci*cj/total) for (i,ci),(j,cj) in combinations(sorted(neighbors.items()),2)]


def floating_audit(old_manifest,old_raw,records,cards,graph,names,incidence):
    cuts={node:(identifier,source) for identifier,node,source in
          re.findall(r'(?m)^(VCUT\d+) (\S+) (\S+) 0$',records)}
    require(cuts.keys()==old_manifest['boundaries'].keys(),'Historical boundary inventory differs')
    rows=[]
    for node,desc in sorted(old_manifest['boundaries'].items()):
        mode=desc['mode']
        group=graph.group(node)
        ids=incidence[node]
        types=Counter(x[0] for x in ids)
        caps=[x for x in ids if x.startswith('C') and cap_ff(cards[x][2])]
        kept=[x for x in caps if x in old_raw]
        omitted=[x for x in caps if x not in old_raw]
        if mode=='coupled_plate_fixed_to_vss':
            grade='Suspeita' if ids else 'Indeterminada'
            reason=('Floating native metal with no R or MOS was clamped' if isolated_star(node,incidence,cards) is not None
                    else 'Forced to VSS although native electrical network extends beyond the plate')
        elif mode=='captured_input_or_public_clock' and node=='CLK':
            grade,reason='Preservada','Same public stimulus port in the original topology'
        elif mode in ('captured_input_or_public_clock','coupled_plate_replay'):
            grade,reason='Aproximada','Recorded voltage applied with zero source impedance'
        else:
            grade,reason='Indeterminada','No accepted boundary characterization'
        identifier,source=cuts[node]
        rows.append(dict(card=identifier,node=node,physical_node=names.get(node,node),source=source,mode=mode,
            classification=grade,reason=reason,resistive_group_size=len(group),
            resistive_rail_path=sorted(group&set(RAILS)),native_card_types=dict(types),
            kept_caps=kept,omitted_caps=omitted,zero_caps=[n for n in ids if n.startswith('C') and not cap_ff(cards[n][2])],
            kept_ff=str(sum((cap_ff(cards[x][2]) for x in kept),Decimal(0))),
            omitted_ff=str(sum((cap_ff(cards[x][2]) for x in omitted),Decimal(0))),
            original_archive=desc.get('archived_node'),archived_trace=desc.get('archived_trace'),
            distance_to_proxy_ohm=desc.get('proxy_route_ohm')))
    return rows


def select_active(cards,graph,probes,previous,external_cone):
    stable={probes[k]:k for k in WRITE_BOUNDARIES}
    stable['CLK']='public_clk'
    stable.update({pin:None for pin in ('CSb','OEb','WEb')})
    # Column 3 retains the actual capture FF. Other columns retain D cones and input inverters.
    stable.update({probes[label]:label for b,label in enumerate(Q_NAMES) if b!=3})
    targets={probes[x] for x in (SCLK,PCH,*WORDLINES,Q_NAMES[3],'macro_core.evaluation.X',
             'macro_core.write_drive.X',*[f'_{75+b}_.D' for b in range(8)])}
    targets.update(probes[n] for n in probes if '.write_driver_' in n)
    targets.update(external_cone.values())
    selected,active,bounds=pull_region(cards,graph,targets,(*stable,*RAILS))
    inputs={}
    for b,path in enumerate(previous['bits']):
        if b==3:
            continue
        d=graph.group(path['read_d'])
        gates=[n for n,c in cards.items() if n.startswith('X') and c[1] in d]
        require(len(gates)==2 and all(n not in selected for n in gates),'FF input stage did not cut cleanly')
        n,p=(cards[k] for k in gates)
        require('nfet' in n[4] or 'nfet' in p[4],'Missing FF NMOS input load')
        require('pfet' in n[4] or 'pfet' in p[4],'Missing FF PMOS input load')
        native_outputs=[(a,z) for a in (n[0],n[2]) for z in (p[0],p[2]) if z in graph.group(a)]
        require(len(native_outputs)==1,'FF input inverter output is not unique')
        selected.update(gates)
        # Preserve physical RC groups for the native inverter, leaving downstream MOS loads outside.
        for k in gates:
            for a in cards[k][:4]:
                active.update(graph.group(a)-bounds)
        inputs[str(b)]={'native_mos':sorted(gates),'input_net':path['read_d'],
                        'inverter_output':native_outputs[0][0],'q_boundary':probes[Q_NAMES[b]]}
    return selected,active,bounds,stable,inputs


def known_sources(probes,ref):
    result={node:{'mode':'recorded','trace':name} for name,node in probes.items() if name in ref.cols}
    # Pin model of the parent controls is preserved. Public DATA positions are verified by load.
    result.update({f'DATA{i}':{'mode':'recorded','trace':f'public_data{i}'} for i in range(8)})
    ref.cols.update({f'public_data{i}':i+2 for i in range(8)})
    result.update({p:{'mode':'programmed_external','spice_source':f'V_{p}'} for p in ('CSb','OEb','WEb')})
    result.update({f'ADDR{i}':{'mode':'programmed_external','spice_source':f'V_ADDR{i}'} for i in range(2)})
    return result


def plan_boundaries(needed,kept,graph,known,names):
    by_group=defaultdict(list)
    for node in known:
        by_group[graph.group(node)].append(node)
    seen=set()
    will_retain=set()
    actions=[]
    # Keep one replay source for a resistive group, never a stiff source on every plate.
    for node in sorted(needed-kept):
        if node in seen:
            continue
        group=graph.group(node)
        require(not group&kept,'A cut crosses an already retained resistive net')
        touched=sorted(group&needed)
        seen.update(group)
        observed=sorted(by_group[group])
        chosen=None
        if observed:
            options=[(sum(graph.shortest(n,{x})[0] for n in touched),x) for x in observed]
            _,chosen=min(options)
            will_retain.update(group)
        actions.append(dict(nodes=sorted(group),plates=touched,physical_names=[names.get(n,n) for n in touched],
            available_recorded_nodes=observed,source_node=chosen,
            source=None if chosen is None else known[chosen],
            classification='Aproximada' if chosen else 'Indeterminada',
            proxy_path_ohm=None if chosen is None else max(graph.shortest(n,{chosen})[0] for n in touched)))
    return will_retain,actions


def old_replay_cards(text,m):
    cards={x[0].split()[1]:x[0] for x in CARD.finditer(text)}
    links=dict(re.findall(r'(?m)^VCUT\d+ (\S+) (archive_\d+) 0$',text))
    out={}
    for n,b in m['boundaries'].items():
        if label:=b['archived_trace']:
            out.setdefault(label,cards[links[n]])
    return out


def source_card(identifier,node,provider,ref,old_cards,reference_deck):
    if provider['mode']=='programmed_external':
        line=next(l for l in reference_deck.splitlines() if l.startswith(provider['spice_source']+' '))
        _,pts=public_pwl(line)
        native=[]
        for lo,hi,shift in ((0,46,0),(87,127,-40),(188,247,-100)):
            native.extend((Decimal(t+shift),value_at(pts,Decimal(t))) for t in (lo,hi))
            native.extend((t+shift,v) for t,v in pts if lo<t<hi)
        return write_knots(f'{identifier} {node} VSS',[(t,str(v)) for t,v in sorted(native)])
    label=provider['trace']
    if label in old_cards:
        return write_knots(f'{identifier} {node} VSS',pwl_tokens(old_cards[label])[1])
    def segment(a,b,shift):
        t,v=np.asarray([(t,y[0]) for t,y in ref.points(a,b,[(ref.cols[label],1.,0.)])]).T
        t,v=compress(t,v)
        return t+shift,v
    t,v=zip(*(segment(a,b,shift) for a,b,shift in ((0.,46.,0.),(87.,127.,-40.),(188.,247.,-100.))),strict=True)
    return pwl(identifier,node,'VSS',np.concatenate(t),np.concatenate(v))


def next_deck(config,values,pending):
    probes=' '.join(values)
    return '\n'.join(['* TT shared SCLK reduced control, offline only',*config,
        '.include "circuit.spice"','.include "stimuli.spice"',
        *([f'.include "{UNKNOWN_INCLUDE}"'] if pending else []),f'.save {probes}',
        '.control','set num_threads=1','set noaskquit','set wr_singlescale','set wr_vecnames','set numdgt=15',
        'echo __R87_DECK_READY__','echo __R87_TRAN_DISPATCH__',
        f'tran 10p {HORIZON:g}n 0 25p','echo __R87_TRAN_RETURN__',
        f'wrdata waveform.dat {probes}','quit','.endc','.end',''])


def capacitive_network(raw,cards,incidence,signal,kept,names):
    chosen={n for n,p in cards.items() if n[0]=='C' and cap_ff(p[2]) and
            (set(p[:2])&signal or set(p[:2])<=kept)}
    candidates={node for n in chosen for node in cards[n][:2] if node not in kept and
                isolated_star(node,incidence,cards) is not None}
    require(FAILED_NODE in candidates,'VCUT205 metal no longer belongs to the target network')
    reductions=[]
    reduced_cards={}
    all_eliminated=set()
    for node in sorted(candidates):
        weights=isolated_star(node,incidence,cards)
        require(weights and not set(weights)&candidates,'Capacitance-only island is not a single conductor')
        replacements=eliminate_star(weights)
        positive={n for n in incidence[node] if n[0]=='C' and cap_ff(cards[n][2])}
        all_eliminated.update(positive)
        nids=[]
        for i,j,value in replacements:
            key=f'CKRON{len(reduced_cards)+1}'
            reduced_cards[key]=f'{key} {i} {j} {value:.24g}f'
            nids.append(key)
        reductions.append(dict(node=node,physical_node=names.get(node,node),
            classification='Equivalente justificada',native_cards={n:raw[n] for n in sorted(positive)},
            total_native_cap_ff=str(sum(weights.values(),Decimal(0))),pairs=len(nids),generated_cards=nids,
            weights_ff={name:str(cap) for name,cap in weights.items()}))
    chosen-=all_eliminated
    return chosen,reduced_cards,reductions,all_eliminated


def add_frontier_evidence(frontiers,incidence,cards,cap_ids,retained,critical,derived):
    for group in frontiers:
        neighbors=set(group['plates'])
        metric=defaultdict(Decimal)
        touched=[]
        for node in neighbors:
            for name in incidence[node]:
                if name in cap_ids:
                    p=cards[name]
                    other=other_end(p,node)
                    if other in retained:
                        touched.append(name)
                        metric[critical.get(other,'other_retained')]+=cap_ff(p[2])
        for name,p in derived.items():
            _,a,b,val=p.split()
            if a in neighbors and b in retained or b in neighbors and a in retained:
                dest=b if a in neighbors else a
                touched.append(name)
                metric[critical.get(dest,'other_retained')]+=cap_ff(val)
        group['coupled_card_ids']=sorted(set(touched))
        group['direct_incident_cap_ff']={k:str(v) for k,v in sorted(metric.items())}
        group['total_direct_incident_cap_ff']=str(sum(metric.values(),Decimal(0)))


def unloaded_rail_leaves(cards,selected,rails,anchored):
    """A resistor to an otherwise unloaded degree-one node carries zero current."""
    anchors=set(anchored)
    links=defaultdict(set)
    for name in selected:
        pins=cards[name][:4] if name.startswith('X') else cards[name][:2]
        if name.startswith('R') and set(pins)<=rails:
            for node in pins:
                links[node].add(name)
        else:
            anchors.update(set(pins)&rails)
    todo=deque(sorted(n for n,adjacent in links.items() if len(adjacent)==1 and n not in anchors))
    gone=set()
    while todo:
        n=todo.popleft()
        if n in anchors or len(links[n])!=1:
            continue
        name=links[n].pop()
        other=other_end(cards[name],n)
        links[other].remove(name)
        gone.add(name)
        if len(links[other])==1 and other not in anchors:
            todo.append(other)
    return gone


def unloaded_series(cards,selected,protected):
    """Eliminate degree-two resistor nodes without any dynamic or measured load."""
    anchors=set(protected)
    links=defaultdict(set)
    values={}
    histories={}
    for name in sorted(selected):
        pins=cards[name][:4] if name.startswith('X') else cards[name][:2]
        if name.startswith('R'):
            values[name]=cards[name]
            histories[name]=([name],[])
            for node in pins:
                links[node].add(name)
        else:
            anchors.update(pins)
    queue=deque(sorted(n for n,adjacent in links.items() if len(adjacent)==2 and n not in anchors))
    counter=0
    while queue:
        node=queue.popleft()
        if node in anchors or len(links[node])!=2:
            continue
        first,second=sorted(links[node])
        if any(values[name][0]==values[name][1] for name in (first,second)):
            continue
        left,right=(other_end(values[name],node) for name in (first,second))
        if left==right:
            continue
        a,b=(Decimal(values[name][2]) for name in (first,second))
        require(min(a,b)>=0,'Series reduction encountered a negative resistance')
        counter+=1
        key=f'RSERIES{counter}'
        edges1,points1=histories.pop(first)
        edges2,points2=histories.pop(second)
        histories[key]=(sorted(edges1+edges2),sorted(points1+points2+[node]))
        values[key]=[left,right,str(a+b)]
        for n,name in ((left,first),(right,second)):
            links[n].remove(name)
            links[n].add(key)
            del values[name]
            if n not in anchors and len(links[n])==2:
                queue.append(n)
        links[node].clear()
    replacements={n:values[n] for n in sorted(values) if n.startswith('RSERIES')}
    derivation={n:dict(native_cards=histories[n][0],removed_nodes=histories[n][1],
                       endpoints=values[n][:2],ohm=values[n][2]) for n in replacements}
    removed={name for d in derivation.values() for name in d['native_cards']}
    return replacements,derivation,removed


def rail_paths_unchanged(cards,kept,derived,rails,series=None):
    graph=ResistanceGraph({**{n:cards[n] for n in kept},**(series or {})})
    roots={n:graph.group(n) for n in RAILS}
    require(not roots['VDD']&roots['VSS'],'Supply rails shorted by the cut')
    required={node for n in kept if not n.startswith('R') for node in
              (cards[n][:4] if n.startswith('X') else cards[n][:2]) if node in rails}
    required.update(node for card in derived.values() for node in card.split()[1:3] if node in rails)
    require(required<=roots['VDD']|roots['VSS'],'Physical supply path removed at a load')


def acceptance(ref,previous,plans):
    windows=[]
    for plan in plans:
        event={'cycle':plan['cycle'],'expected_word':f'0x{plan["expected_word"]:02X}',
               'reference_word':{15:'0x0F',16:'0xF8',17:'0xF8'}[plan['cycle']],
               'reference_capture_ns':plan['captures_ns'],
               'compare_precondition_at_ns':plan['conditioning_ns']}
        event['macro_sclk_sampler_bl20_ns']=[
            ref.edge(f'SCLK_SENSE_{i}',plan['low_ns'],plan['high_ns'],.36,True) for i in range(8)]
        marker=ref.edge('sclk_tail',plan['low_ns'],plan['high_ns'],.36,True)
        event['sense3_tail_sclk20_ns']=marker
        event['sense3_blb_minus_bl_v_at_sclk20']=(
            ref.value(marker,ref.cols['blb_at_sense'])-ref.value(marker,ref.cols['bl_at_sense']))
        event['reference_ntail_before_v']=ref.value(plan['conditioning_ns'],ref.cols['sense_tail'])
        windows.append(event)
    criteria=previous['gate_criteria']
    return dict(schema='phase3.sclk_recut_control_acceptance.v1',electrical_gate='NOT_RUN',
          source_reference='TT original, reduced sequence 250 ns, no R87 intervention',
          reference_time_transform_ns=100,windows=windows,
          historic_criteria=criteria,
          mandatory=['Complete waveform through 147 ns, two selected physical writes (rows 2/3), maintained storage.',
                     'Stable sense and D for 8 bits at the archived capture events in c15–c17; check real FF Q only at bit 3.',
                     'Expected 0x0F, 0xF8, 0xF8 and correct bitcell3 storage in c16/c17.',
                     'Native SCLK shared driver, 24 gates, BL/BLB, precharge/WL sequence and NTAIL fidelity.',
                     'Seal remaining boundary conditions and verify they cannot explain the logic decisions.'],
          method=dict(edge='Use existing 20/50/80% interpolation and old 25 ps diagnostic clock envelope. '
                    'Any crossing outside a reference sample bracket/envelope remains a comparability issue.',
              sense3_ntail='Use previous 30.169 mV envelope and continuous windows across conditioning and conduction.',
              bitline='Reuse prior differential/common-mode envelope and positive sign near evaluation for bit 3. '
                      'Compare co-sampled raw points on the same standard PEX; retain explicit waveform uncertainty.',
              logic='0.36/1.44 V, stable through the intended observation event. A single crossing does not establish a decision.',
              precision='25 ps is a maximum recorded solver step and a prior ramp-comparison envelope, '
                        'not an error bound or public timing limit. Do not treat another RC extraction as identical.',
              other_columns='Their Q is input replay only. Reference clock taps define the observation event there.'),
          allowed_next_step='Experiment blocked until manifest readiness is READY_FOR_CONTROL.')


def write_table(file,rows):
    with file.open('x',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,(list,dict)) else v
                             for k,v in row.items()})


def generate(output):
    original=json.loads(pinned(PARENT/'manifest.json',PARENT_SHA).read_text())
    ramp=json.loads(pinned(RAMP/'manifest.json',RAMP_SHA).read_text())
    for base,m in ((PARENT,original),(RAMP,ramp)):
        for name,h in m['files_sha256'].items():
            pinned(base/name,h)
    failure=json.loads(pinned(RAMP/'startup_failure.json',HISTORIC_ERROR).read_text())
    for base,m in ((PARENT,original),(RAMP,ramp)):
        for name,h in m['source_sha256'].items():
            pinned(ROOT/name,h)
    pex=pinned(PEX/'extracted_rc.spice',PEX_SHA)
    model_file=REFERENCE/'model_hashes.json'
    models=json.loads(model_file.read_text())
    require(model_closure(PDK)==models,'SKY130A TT closure differs from the referenced PDK')
    _,receipt,ref=load(REFERENCE,True)
    raw=checked_inventory((REFERENCE/'binding.spice').read_text())
    cards={n:line.split()[1:] for n,line in raw.items()}
    nodes={v:k for k,v in rc_node_map(pex.read_text()).items()}
    incidence=index_cards(cards)
    graph=ResistanceGraph(cards)
    probes=json.loads((REFERENCE/'probes.json').read_text())
    # This check uses the physical graph, not the historical solver diagnostic node name.
    r87=branch((REFERENCE/'binding.spice').read_text(),probes)
    require(json.loads(json.dumps(r87))==original['sclk']['branch'] and r87['upstream'] in graph.group(probes[SCLK]),'R87 lineage changed')
    audit=floating_audit(original,checked_inventory((PARENT/'slice.spice').read_text()),
                        (RAMP/'stimuli.spice').read_text(),cards,graph,nodes,incidence)
    vcut=next(x for x in audit if x['card']=='VCUT205')
    require(vcut['node']==FAILED_NODE and vcut['omitted_caps']==['C6381','C6439'] and
            failure['termination_card']=='VCUT205 rc7913 VSS 0','Historical diagnostic mismatch')
    external_cone={}
    for root in ('_34_.Y','_44_.Y'):
        candidates=sorted(n for n,physical in nodes.items() if physical==root or physical.startswith(root+'.'))
        require(candidates and all(n in graph.group(candidates[0]) for n in candidates),
                f'Cannot uniquely retain {root}')
        external_cone[root]=candidates[0]
    mos,active,bound,drives,inputs=select_active(cards,graph,probes,original,external_cone)
    relevant=active|bound
    rails=set().union(*(graph.group(n) for n in RAILS))
    shared=graph.group(r87['upstream'])
    pch=graph.group(probes[PCH])
    wordline=set().union(*(graph.group(probes[n]) for n in WORDLINES))
    all_bl=set().union(*(graph.group(bit[key]) for bit in original['bits'] for key in ('bl_at_sense','blb_at_sense')))
    latch=set().union(*(graph.group(bit[key]) for bit in original['bits'] for key in ('sense_out','sense_bar','sense_tail')))
    physical_drivers=[n for n in mos if set(cards[n][:3:2])&shared]
    require(len(physical_drivers)==8 and set(shared|pch|wordline|all_bl|latch)<=active
            and not set(drives)&(shared|pch|wordline|all_bl|latch),'Protected analog net would be clamped')
    access=set(original['physical_access_loads'])
    require(access<=mos and len(access)==64,'A native access load was omitted')
    storage=set()
    for a in access:
        storage_node=next(n for n in cards[a][:3:2] if n not in all_bl)
        storage.update(graph.group(storage_node))
    storage_mos={n for n in mos if cards[n][1] in storage}
    require(len(storage_mos)==128 and not storage&set(drives),'Native 6T storage not retained')
    bits=[bit_probes(cards,graph,probes,{n:cards[n] for n in sorted(mos)},b) for b in range(8)]
    for b,bit in enumerate(bits):
        require(all(bit[k]==original['bits'][b][k] for k in (
            'bl_at_sense','blb_at_sense',*GATES,'read_d','sense_out','sense_bar','sense_tail','tail_ground','currents','samplers')),
            'Native sense terminals changed')
    local_gates={one[k] for one in bits for k in GATES}
    all_prech={one[k] for one in bits for k in ('precharge_bl_gate','precharge_blb_gate','equalizer_gate')}
    require(len(local_gates)==len(all_prech)==24 and local_gates<=shared and all_prech<=pch,
            'Sense clocks or precharge mapping incomplete')
    cap_ids,reduced,cap_plan,eliminated=capacitive_network(raw,cards,incidence,relevant-rails,relevant,nodes)
    needed={p for n in cap_ids for p in cards[n][:2]}
    needed.update(p for card in reduced.values() for p in card.split()[1:3])
    known=known_sources(probes,ref)
    extra,frontiers=plan_boundaries(needed,relevant,graph,known,nodes)
    critical={n:name for ids,name in ((shared,'SCLK'),(pch,'precharge'),(wordline,'WL'),
               (all_bl,'BL/BLB'),(latch,'sense'),(rails,'power'),(storage,'storage')) for n in ids}
    add_frontier_evidence(frontiers,incidence,cards,cap_ids,relevant,critical,reduced)
    not_ready=[g for g in frontiers if g['source'] is None]
    not_ready.sort(key=lambda g:(-Decimal(g['total_direct_incident_cap_ff']),g['nodes']))
    for group in frontiers:
        if group['source_node']:
            drives[group['source_node']]=group['source'].get('trace')
    complete=relevant|extra
    # Keep original capacitors only when both ends are part of the same known electrical domain,
    # or when they are on the explicit pending interface. No shunt created from an unknown signal.
    kept={n:line for n,line in raw.items() if n in mos or n in cap_ids or
                          n.startswith('R') and set(cards[n][:2])<=complete}
    require(r87['card'] in kept and not (set(reduced)&kept.keys()),'Native or derived card mis-identified')
    old_cards=old_replay_cards((RAMP/'stimuli.spice').read_text(),original)
    reference_deck=(REFERENCE/'bench.spice').read_text()
    source_lines=['VSS_BASE VSS 0 0\n',SUPPLY+'\n']
    source_map={}
    for i,(node,label) in enumerate(sorted(drives.items())):
        provider=known.get(node)
        if label is not None:
            provider={'mode':'recorded','trace':label}
        require(provider is not None and node not in shared|pch|wordline|all_bl|storage,
                'Stimulus is missing provenance or clamps an observed output')
        require(node not in rails,'Duplicated ideal power source')
        identifier=f'VREPLAY{i}'
        source_lines.append(source_card(identifier,node,provider,ref,old_cards,reference_deck))
        source_map[node]=dict(provider,source=identifier,classification='Preservada' if
                             node=='CLK' or provider['mode']=='programmed_external' else 'Aproximada')
    vectors={'shared_sclk':f'v({probes[SCLK]})','r87_upstream':f'v({r87["upstream"]})',
             'r87_local':f'v({r87["local"]})','precharge':f'v({probes[PCH]})','clk':'v(clk)','vdd':'v(vdd)',
             'supply_a':'i(vdd_base)', **{f'wl{i}':f'v({probes[name]})' for i,name in enumerate(WORDLINES)}}
    for b,bit in enumerate(bits):
        vectors.update({f'b{b}_{name}':f'v({value.lower()})' for name,value in bit.items()
                        if isinstance(value,str) and (name not in ('read_q','capture_clock') or b==3)})
        for key,x in bit['currents'].items():
            vectors[f'b{b}_{key}']=f'@m.{x.lower()}.m{cards[x][4].lower()}[id]'
    for key,p in ramp['storage_probes'].items():
        require(p['node'] in storage,'Storage probe has no retained 6T node')
        vectors[key]=f'v({p["node"].lower()})'
    observed={v[2:-1].upper() for v in vectors.values() if v.startswith('v(')}
    anchors=(set(drives)|set(RAILS)|{n for n in complete if n.upper() in observed}|
             {n for c in reduced.values() for n in c.split()[1:3]})
    critical_nodes=shared|pch|wordline|all_bl|latch|storage
    pruned=unloaded_rail_leaves(cards,set(kept),rails|extra,anchors|critical_nodes)
    for name in pruned:
        del kept[name]
    series,series_proof,series_removed=unloaded_series(cards,set(kept),anchors|critical_nodes)
    for name in series_removed:
        del kept[name]
    require(not set(drives)&set(external_cone.values()),'A retained driver output would be clamped')
    rail_paths_unchanged(cards,kept,reduced,rails,series)
    omitted=[dict(card=n,reason='exact_capacitance_reduction' if n in eliminated else
                  ('unloaded_resistive_leaf' if n in pruned else
                   ('exact_series_equivalent' if n in series_removed else 'outside_reduced_control')),native=line)
             for n,line in raw.items() if n not in kept]
    config=original['config']
    out=new_directory(output)
    circuit_cards=[*kept.values(),*reduced.values(),
                   *(f'{name} {" ".join(pins)}' for name,pins in series.items())]
    (out/'circuit.spice').write_text('\n'.join(circuit_cards)+'\n')
    (out/'stimuli.spice').write_text(''.join(source_lines))
    (out/'control.spice').write_text(next_deck(config,vectors.values(),bool(not_ready)))
    write_table(out/'old_frontiers.csv',audit)
    write_table(out/'removed.csv',omitted)
    write_json(out/'frontiers.json',dict(ideal_voltage_sources=source_map,resistive_groups=frontiers,
              unresolved_priority=not_ready,exact_capacitance_reductions=cap_plan,old_vcut205=vcut,
              archived_error_sha256=HISTORIC_ERROR))
    write_json(out/'series_resistors.json',series_proof)
    write_json(out/'node_map.json',{n:nodes.get(n,n) for n in sorted(complete|needed)})
    write_json(out/'acceptance.json',acceptance(ref,original,cycle_plan(ref,probes)))
    native=Counter(n[0] for n in kept)
    read_coverage={str(i):('native D, local capture and Q' if i==3 else 'native D, Q replay, archived capture instant')
                   for i in range(8)}
    all_sources=(PEX/'extracted_rc.spice',REFERENCE/'binding.spice',REFERENCE/'probes.json',
                 REFERENCE/'waveform.dat',REFERENCE/'bench.spice',model_file,
                 PARENT/'manifest.json',PARENT/'slice.spice',RAMP/'manifest.json',
                 RAMP/'stimuli.spice',RAMP/'startup_failure.json',Path(__file__))
    write_json(out/'manifest.json',dict(schema='phase3.sclk_recut.v1',
        readiness='NOT_READY' if not_ready else 'READY_FOR_CONTROL',electrical_gate='NOT_RUN',simulations=0,
        guard_include_missing=UNKNOWN_INCLUDE if not_ready else None,
        pex_sha256=PEX_SHA,archived_tt_waveform_sha256=receipt['waveform_sha256'],
        model_count=len(models),model_closure_sha256=sha256(model_file),
        prior_counts=original['component_counts'],preserved_native_counts=dict(native),
        exact_derived_cap_count=len(reduced),exact_derived_resistor_count=len(series),
        effective_card_counts=dict(native,C=native['C']+len(reduced),R=native['R']+len(series)),
        omitted_native_count=len(omitted),unresolved_resistive_groups=len(not_ready),
        retained_coupled_nor_cones=external_cone,pruned_unloaded_boundary_or_rail_resistors=sorted(pruned),
        native_vdd_rail_node_count=len(graph.group('VDD')),native_vss_rail_node_count=len(graph.group('VSS')),
        unresolved_direct_critical_groups=sum(any(k!='other_retained' for k in g['direct_incident_cap_ff'])
                                             for g in not_ready),
        native_sclk_driver_mos=sorted(physical_drivers),sclk_nodes=sorted(shared),r87=r87,
        precharge_nodes=sorted(pch),wordlines=original['wordlines'],bits=bits,native_6t_cells=32,
        bitlines_source_free=True,read_coverage=read_coverage,native_input_ff_loads=inputs,
        conditions=dict(corner='tt',temperature_c=27,max_step_ps=25,horizon_ns=HORIZON,
                        unique_control_timeout_s=1200,preparation_and_operating_point_timeout_s=300),
        ideal_voltage_sources=len(source_map)+2,old_frontier_classifications=dict(Counter(x['classification'] for x in audit)),
        source_sha256={str(p.relative_to(ROOT)):sha256(p) for p in all_sources},
        artifacts_sha256={f.name:sha256(f) for f in sorted(out.iterdir())}))
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    out=generate(args.output)
    data=json.loads((out/'manifest.json').read_text())
    print(f'{data["readiness"]}: {out}',flush=True)


if __name__=='__main__':
    main()
