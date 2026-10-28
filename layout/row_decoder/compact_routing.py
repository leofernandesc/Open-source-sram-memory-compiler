"""Placement and finite wire spans for the unchanged 29-MOS dynamic decoder."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RoutingPlan:
    placement: dict[str, tuple[int, int]]
    gate_offset: dict[str, int]
    source_offset: dict[str, int]
    tracks: dict[str, int]
    extents: dict[str, tuple[int, int]]
    port_x: dict[str, int]
    shields: tuple[int, ...]


def compact_plan(devices) -> RoutingPlan:
    # Address inverters/true buffers: aligned P/N pairs in four columns.
    # Each decode branch has precharge/upper-stack, lower-stack, output pair.
    columns = ((1, 2), (26, 27), (3, 4), (28, 29),
               (5, 6), (7,), (9, 10),
               (11, 12), (13,), (14, 15),
               (8,),
               (16, 17), (18,), (19, 20),
               (21, 22), (23,), (24, 25))
    by_name = {d.name: d for d in devices}
    if set(by_name) != {f'XM{i}' for i in range(1, 30)}:
        raise ValueError('Compact placement requires exactly XM1..XM29')
    placement, offsets, sources = {}, {}, {}
    for col, group in enumerate(columns):
        for number in group:
            name = f'XM{number}'
            pmos = 'pfet' in by_name[name].model.lower()
            placement[name] = (1500 + 1100*col, 1000 if pmos else -1000)
            # Distinct gate escape columns prevent PCLK/literal shorts when
            # precharge PFET and upper-stack NFET occupy the same column.
            offsets[name] = 150 if pmos else -150
            # The upper-stack source goes to an intermediate node, above the
            # P row. Escape toward the following lower-stack drain instead
            # of sharing the precharge PFET's VDD vertical column.
            sources[name] = 800 if number in (6, 12, 17, 22) else 300
    tracks = dict(VDD=1700, VSS=-1700, EVAL_GND=0, A0=200, A1=500,
                  PCLK=3200, A0B=3800, A1B=4400, A0T=5000, A1T=5600)
    for row in range(4):
        tracks[f'N{row}'] = 2000
        tracks[f'net{row+1}'] = 2300
        tracks[f'DEC{row}'] = 2600
    vias = {name: set() for name in tracks}
    for d in devices:
        x, _ = placement[d.name]
        for net, vx in ((d.drain, x-300), (d.gate, x+offsets[d.name]),
                        (d.source, x+sources[d.name]), (d.bulk, x+560)):
            vias[net].add(vx)
    port_x = {net: 500 for net in ('VDD', 'VSS', 'PCLK', 'A0', 'A1')}
    for row, output in enumerate((9, 14, 19, 24)):
        port_x[f'DEC{row}'] = placement[f'XM{output}'][0] + 700
    for net, x in port_x.items():
        vias[net].add(x)
    extents = {net: (min(xs)-60, max(xs)+60) for net, xs in vias.items()}
    # met3.6 minimum area is 0.24 um^2. At 60 internal units width,
    # avoid tiny islands when a shared source/drain has just one via column.
    for net, (lo, hi) in list(extents.items()):
        if hi-lo < 200:
            center = (lo+hi)//2
            extents[net] = (center-100, center+100)
    rail_end = max(x+560 for x, _ in placement.values()) + 140
    extents['VDD'] = extents['VSS'] = (100, rail_end)
    # VSS shields separate PCLK and each buffered address track. They share
    # one explicit M2 return trunk at x=200, connected to the lower VSS rail.
    shields = (3500, 4100, 4700, 5300)
    for net, (lo, hi) in extents.items():
        for other, (olo, ohi) in extents.items():
            if net != other and tracks[net] == tracks[other] and not (hi+120 <= olo or ohi+120 <= lo):
                raise ValueError(f'Overlapping same-layer tracks: {net}, {other}')
    return RoutingPlan(placement, offsets, sources, tracks, extents, port_x, shields)
