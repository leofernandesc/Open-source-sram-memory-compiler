#!/usr/bin/env python3
"""Read-only PEX inventory and passive DC rail audit for a future R87 bench."""

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import re

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu

from audit_phase3_sense3_diff_boundary import extract_cards
from phase3_rc_probe import rc_node_map
from phase3_sclk_recut import cap_ff
from phase3_sense3_precondition import pinned, sha256
from run_phase3_sense3_isolation import BUILD, PEX, REFERENCE, ROOT, ResistanceGraph


V2 = BUILD / "sclk_local_driver_20261121_v2"
SLICE = BUILD / "sense3_preconditioned_20261120"
RECUT = BUILD / "sclk_recut_audited_r2_20261120"
CONTROLS = {"SCLK": "rc8562", "PRECH": "rc8467"}
RAILS = ("VDD", "VSS")


def read(path):
    return json.loads(path.read_text())


def select(cards, prefix):
    return {k: v for k, v in cards.items() if k.startswith(prefix)}


def connected(cards, nodes):
    return {k: v for k, v in cards.items() if nodes.intersection(v[:2])}


def rail_matrix(ground, resistors, ports):
    """V/I with public pad held fixed, R cards alone. No capacitance is terminated."""
    nodes = {n for a,b,_ in resistors.values() for n in (a,b)}
    index = {n:i for i,n in enumerate(sorted(nodes-{ground}))}
    row, col, data = [], [], []
    for a,b,resistance in resistors.values():
        g=1/float(resistance)
        for u,v in ((a,b),(b,a)):
            if u==ground:
                continue
            row.append(index[u]); col.append(index[u]); data.append(g)
            if v!=ground:
                row.append(index[u]); col.append(index[v]); data.append(-g)
    shape = (len(index),len(index))
    matrix = coo_matrix((data,(row,col)),shape=shape).tocsc()
    rhs = np.zeros((len(index),len(ports)))
    ids = [index[port] for port in ports]
    rhs[ids,np.arange(len(ports))]=1
    solution=splu(matrix).solve(rhs)
    z=solution[ids,:]
    if not np.allclose(z,z.T,rtol=1e-8,atol=1e-8):
        raise ValueError(f"DC rail transfer is not reciprocal: {ground}")
    return z


def branch_forks(rs, component, bitmap, gate_keys, feed):
    """Find the bridge separating each triplet of local pins from the rest."""
    region = connected(rs,component)
    result = []
    for bit, mapping in enumerate(bitmap):
        gates = {mapping[key] for key in gate_keys}
        matches = []
        for edge, (a,b,resistance) in region.items():
            cut = ResistanceGraph({k:v for k,v in region.items() if k!=edge})
            branch = cut.group(sorted(gates)[0])
            if gates < branch and len(branch)==4 and feed not in branch:
                up,local=(b,a) if a in branch else (a,b)
                if local in branch and up not in branch:
                    matches.append((edge,up,local,float(resistance)))
        if len(matches)!=1:
            raise ValueError(f"Unexpected branch definition for {feed}, bit {bit}: {matches}")
        result.append((bit,matches[0]))
    return dict(result)


def control_driver(mos, graph, output, rails):
    g = graph.group(output)
    out = {key: p for key,p in mos.items() if g.intersection((p[0],p[2]))}
    inverter_inputs={p[1] for p in out.values()}
    if len(inverter_inputs)!=1:
        raise ValueError(f"Ambiguous native inverter at {output}")
    mid = inverter_inputs.pop()
    mids = set(graph.group(mid))
    # Gate drivers of MID include the series stack. Traverse its non-rail
    # diffusion only. Input gates are recorded as ports, never clamped.
    selected = {}
    while True:
        active={key:p for key,p in mos.items() if mids.intersection((p[0],p[2]))}
        if active.keys()==selected.keys():
            break
        selected=active
        mids.update(n for p in active.values() for i in (0,2)
                    if p[i] not in rails and p[i] not in g for n in graph.group(p[i]))
    inputs = sorted({p[1] for p in selected.values()})
    return dict(output_mos=out,mid=mid,logic_mos=selected,input_gate_nodes=inputs)


def write_csv(path, rows):
    with path.open("x",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def audit(output):
    pex=PEX/"extracted_rc.spice"
    binding=REFERENCE/"binding.spice"
    preflight=read(REFERENCE/"preflight.json")
    raw=pinned(pex,preflight["pex_sha256"]).read_text()
    cards=extract_cards(pinned(binding,preflight["artifacts"]["binding.spice"]).read_text())
    names=rc_node_map(raw)
    physical={v:k for k,v in names.items()}
    direct=extract_cards(raw)
    v2=read(V2/"manifest.json")
    if v2["pex_sha256"]!=sha256(pex):
        raise ValueError("Driver receipt PEX changed")
    for name,h in v2["inputs_sha256"].items():
        pinned(V2/"run"/name,h)
    v2_run=read(V2/"run/result.json")
    if v2_run["status"]!="COMPLETED":
        raise ValueError("Reduced driver reference is incomplete")
    for name,h in v2_run["artifacts"].items():
        pinned(V2/"run"/name,h)
    bitmap=read(RECUT/"manifest.json")["bits"]
    history=read(SLICE/"manifest.json")
    ref_probes=read(pinned(REFERENCE/"probes.json",preflight["artifacts"]["probes.json"]))
    observed=set(ref_probes.values()) | set(RAILS)
    rs,cs,mos=(select(cards,x) for x in "RCX")
    graph=ResistanceGraph(rs)
    groups={label:graph.group(n) for label,n in {**CONTROLS,**{x:x for x in RAILS}}.items()}
    if groups["SCLK"] & groups["PRECH"] or groups["VDD"] & groups["VSS"]:
        raise ValueError("Unexpected resistive short")
    control_nodes=groups["SCLK"] | groups["PRECH"]
    all_rails=groups["VDD"] | groups["VSS"]
    configs={
        "SCLK": ("sclk_sampler_bl","sclk_sampler_blb","sclk_tail"),
        "PRECH": ("precharge_bl_gate","precharge_blb_gate","equalizer_gate"),
    }
    drivers={label:control_driver(mos,graph,n,all_rails) for label,n in CONTROLS.items()}
    precharge_phase=control_driver(mos,graph,"rc8512",all_rails)
    if "rc8464" not in drivers["SCLK"]["input_gate_nodes"] or "rc8464" not in precharge_phase["input_gate_nodes"]:
        raise ValueError("SCLK and precharge_phase did not share the native tap80")
    branches=[]
    device_rows=[]
    for label,n in CONTROLS.items():
        fork_map=branch_forks(rs,groups[label],bitmap,configs[label],n)
        native={**drivers[label]["output_mos"],**drivers[label]["logic_mos"]}
        for k,p in native.items():
            device_rows.append(dict(network=label,role="driver",bit="",card=k,nodes=" ".join(p[:4]),
                                    physical=" ".join(physical[x] for x in p[:4]),model=p[4],geometry=" ".join(p[5:])))
        for bit,fork in fork_map.items():
            edge,up,local,bottleneck=fork
            for role in configs[label]:
                gate=bitmap[bit][role]
                consumers=[(k,p) for k,p in mos.items() if p[1]==gate]
                if len(consumers)!=1:
                    raise ValueError(f"Unexpected gate load at {gate}")
                k,p=consumers[0]
                resistance,path=graph.shortest(gate,set(drivers[label]["output_mos"][d][i]
                                      for d in drivers[label]["output_mos"] for i in (0,2)
                                      if drivers[label]["output_mos"][d][i] in groups[label]))
                branches.append(dict(network=label,bit=bit,branch=edge,upstream=up,local=local,branch_ohm=bottleneck,
                    role=role,gate=gate,physical_gate=physical[gate],device=k,shortest_path_ohm=resistance,
                    path_gate_to_driver=" ".join(path),exact_tt_voltage=gate in observed))
                device_rows.append(dict(network=label,role=role,bit=bit,card=k,nodes=" ".join(p[:4]),
                                        physical=" ".join(physical[x] for x in p[:4]),model=p[4],geometry=" ".join(p[5:])))
    cap_rows,res_rows=[],[]
    cap_sums=defaultdict(Counter)
    boundaries=defaultdict(set)
    external_groups=defaultdict(lambda: {"plates":set(), "cards":set()})
    native_rs=connected(rs,control_nodes)
    native_cs={k:p for k,p in connected(cs,control_nodes).items() if cap_ff(p[2])>0}
    for k,p in {**native_rs,**native_cs}.items():
        if [names[x] for x in direct[k][:2]]+direct[k][2:] != p:
            raise ValueError(f"PEX to binding mismatch for {k}")
        a,b,value=p[:3]
        row=dict(card=k,a=a,b=b,physical_a=physical[a],physical_b=physical[b],value=value)
        if k.startswith("R"):
            res_rows.append(row)
            continue
        def classification(node):
            return next((name for name,group in groups.items() if node in group),"external")
        sides=classification(a),classification(b)
        cap_rows.append(dict(row,a_group=sides[0],b_group=sides[1],a_exact_tt=a in observed,b_exact_tt=b in observed))
        for label,nodes in ((k,groups[k]) for k in CONTROLS):
            if a not in nodes and b not in nodes:
                continue
            peer=b if a in nodes else a
            category=classification(peer)
            cap_sums[label][category]+=float(cap_ff(value))
            if category=="external":
                group=graph.group(peer)
                boundaries[label].add(min(group))
                entry=external_groups[group]
                entry["plates"].add(peer)
                entry["cards"].add(k)
    for row in device_rows:
        k=row["card"]
        if [names[x] for x in direct[k][:4]]+direct[k][4:]!=cards[k]:
            raise ValueError(f"PEX to binding mismatch for device {k}")
    write_csv(output/"branches.csv",branches)
    write_csv(output/"active_devices.csv",device_rows)
    write_csv(output/"control_resistors.csv",res_rows)
    write_csv(output/"control_couplings.csv",cap_rows)
    frontier_rows=[]
    for group,entry in sorted(external_groups.items(),key=lambda item:min(item[0])):
        nodes=sorted(entry["plates"])
        frontier_rows.append(dict(group_root=min(group),physical_root=physical[min(group)],
            plates=" ".join(nodes),observed_exact_plates=" ".join(sorted(entry["plates"]&observed)),
            observed_in_resistive_group=" ".join(sorted(group&observed)),cards=" ".join(sorted(entry["cards"])),
            incident_ff=sum(float(cap_ff(cs[k][2])) for k in sorted(entry["cards"])),
            termination="UNRESOLVED"))
    write_csv(output/"frontier_inventory.csv",frontier_rows)
    ports={
        "VDD":{"sense3_latch_X1267":"rc1713","sense3_latch_X1560":"rc3090","sense3_sampler_X235_bulk":"rc2114",
               "precharge3_X1352":"rc1935","precharge3_X1645":"rc1937","sclk_driver_X614":"rc2927",
               "prech_driver_X1456":"rc2916"},
        "VSS":{"sense3_tail_X351":"rc5874","sclk_driver_X881":"rc5423","prech_driver_X560":"rc5401"},
    }
    for row in branches:
        if row["role"]=="sclk_tail" and row["bit"]!="3":
            a,_,b,*_=mos[row["device"]]
            rail,=set((a,b)) & groups["VSS"]
            ports["VSS"][f"sense{row['bit']}_tail_{row['device']}"]=rail
    rail_results={}
    rail_rows=[]
    for rail,terminals in ports.items():
        group=groups[rail]
        assert set(terminals.values()) < group
        r=connected(rs,group)
        for k,p in r.items():
            if [names[x] for x in direct[k][:2]]+direct[k][2:]!=p:
                raise ValueError(f"Rail resistor {k} differs from the PEX")
        z=rail_matrix(rail,r,list(terminals.values()))
        rail_caps={k:p for k,p in connected(cs,group).items() if cap_ff(p[2])>0}
        rail_results[rail]=dict(ports=terminals,resistor_count=len(r),node_count=len(group),
            incident_nonzero_caps=len(rail_caps),incident_sum_ff=sum(float(cap_ff(p[2])) for p in rail_caps.values()),
            zdc_ohm=z.tolist())
        for (role,node),diagonal in zip(terminals.items(),z.diagonal(),strict=True):
            length,path=graph.shortest(node,{rail})
            rail_rows.append(dict(rail=rail,role=role,terminal=node,physical_node=physical[node],
                                  rdc_to_public_rail_ohm=diagonal,shortest_r_path_ohm=length,
                                  path_to_pad=" ".join(path),exact_tt_probe=node in observed))
    write_csv(output/"supply_paths.csv",rail_rows)
    stats={label:dict(nodes=len(groups[label]),resistors=len(connected(rs,groups[label])),
                      distinct_external_rc_groups=len(boundaries[label]),cap_ff=dict(cap_sums[label]),
                      input_physical=[physical[n] for n in drivers[label]["input_gate_nodes"]]) for label in CONTROLS}
    rail_to_rail=[float(cap_ff(value)) for a,b,value in cs.values()
                  if ((a in groups["VDD"] and b in groups["VSS"]) or
                      (b in groups["VDD"] and a in groups["VSS"])) and cap_ff(value)>0]
    result=dict(assessment="COMPACT_BOUNDARY_PARTIALLY_DEFINED",simulation_authorized=False,spice_runs=0,
        pex_sha256=sha256(pex),stats=stats,rail_dc=rail_results,
        distinct_external_rc_groups=len(frontier_rows),
        groups_with_archived_voltage_on_exact_or_peer_node=sum(bool(row["observed_in_resistive_group"])
                                                               for row in frontier_rows),
        shared_logic=dict(tap80="rc8464",prech_phase="rc8512",precharge_phase_mos=precharge_phase),
        vdd_vss_caps=dict(cards=len(rail_to_rail),sum_ff=sum(rail_to_rail)),
        rail_dc_scope="Pure passive resistors, public pad anchored, unit DC current at native terminal, no device currents",
        local_slice_replay={n:history["ports"][n] for n in ("rc8562","rc8510","rc8202","rc8216","rc5874","VDD")},
        reference_exact_voltage_nodes=sorted(observed & control_nodes),
        termination_models_approved=False, deck_generated=False, source_sha256={str(p.relative_to(ROOT)):sha256(p) for p in
            (pex,binding,REFERENCE/"preflight.json",REFERENCE/"probes.json",RECUT/"manifest.json",
             V2/"manifest.json",SLICE/"manifest.json",V2/"run/clk_delta.spice",V2/"run/result.json")})
    with (output/"manifest.json").open("x") as f:
        json.dump(result,f,indent=2,allow_nan=False)
        f.write("\n")
    print(result["assessment"],flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    audit(parser.parse_args().output)
