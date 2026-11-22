#!/usr/bin/env python3
"""Replay a reduced TT sequence with passive probes at cell (3,3) and sense 3."""

import argparse
import fcntl
import json
import os
from decimal import Decimal
from pathlib import Path
import re
import subprocess
import time

from phase3_rc_characterization import bind_rc_deck, logical_cards
from phase3_rc_probe import rc_node_map
from run_phase3_eco_pex import new_directory, ngspice_limits, pinned
from run_phase3_integrated_ss import (
    BUILD, PDK, PEX, PEX_SHA, ROOT, checked_preparation, model_closure, require, sha256,
)


PARENT = BUILD/'integrated_tt_20261120'
RETAINED = (0,1,2,3,4,5,8,10,14,15,16,17)
INDEX = {old:new for new,old in enumerate(RETAINED)}
STOP_NS = 250
RAMP = Decimal('.05')
JOIN_NS = 127
ARRAY = 'macro_core.array_and_peripherals'


def node_roots(raw):
    """Identify the 6T cross-coupled pair by the two routed access devices."""
    devices = {c.split()[0]:c.split() for c in logical_cards(raw) if c.startswith('X')}

    def branch(card, root):
        return re.fullmatch(re.escape(root)+r'\.t\d+',card) is not None

    row = f'{ARRAY}.bitcell_6t_24.WL'
    bl = f'{ARRAY}.write_driver_3.BL'
    blb = f'{ARRAY}.write_driver_3.BLB'
    sclk = 'macro_core.sense_drive.X'

    def access(line):
        chosen = [x for x in devices.values() if branch(x[2],row) and
                  any(branch(p,line) for p in (x[1],x[3]))]
        require(len(chosen)==1, f'Ambiguous row 3 device on {line}')
        x, = chosen
        require(x[5]=='sky130_fd_pr__nfet_01v8' and 'w=0.6' in x and 'l=0.15' in x, 'Unexpected access sizing')
        storage, bitline = (x[3],x[1]) if branch(x[1],line) else (x[1],x[3])
        return x,storage,bitline

    a,q,cl = access(bl)
    b,qb,cr = access(blb)
    require(q!=qb and a[2]!=b[2], 'Ambiguous cell pair')
    inverter_cards = []
    for out,gate in ((q,qb),(qb,q)):
        for kind,rail,width in (('n','VSS','w=1.26'),('p','VDD','w=0.42')):
            cards = [x for x in devices.values() if x[2]==gate and out in (x[1],x[3])
                     and x[5]==f'sky130_fd_pr__{kind}fet_01v8' and width in x
                     and any(branch(p,rail) for p in (x[1],x[3]))]
            require(len(cards)==1, 'Cross-coupled pair failed connectivity verification')
            inverter_cards.append(cards[0][0])

    def sampler(line, sense):
        cards = [x for x in devices.values() if branch(x[2],sclk) and x[5]=='sky130_fd_pr__pfet_01v8'
                 and any(branch(p,line) for p in (x[1],x[3]))
                 and any(branch(p,sense) for p in (x[1],x[3]))]
        require(len(cards)==1, f'Ambiguous sense sampling device for {line}')
        x, = cards
        return x,next(p for p in (x[1],x[3]) if branch(p,line)),next(p for p in (x[1],x[3]) if branch(p,sense))

    sa,sl,la = sampler(bl,'_40_.A1')
    sb,sr,lb = sampler(blb,f'{ARRAY}.sense_amp_3.SA_OUTB')
    # Tail is the common source of the latch NMOS pair, verified against both outputs.
    roots = ('_40_.A1',f'{ARRAY}.sense_amp_3.SA_OUTB')
    latch = [x for x in devices.values() if x[5]=='sky130_fd_pr__nfet_01v8'
             and any(branch(x[2],root) and any(branch(p,other) for p in (x[1],x[3]))
                     for root,other in (roots,roots[::-1]))]
    common = set(latch[0][1:4])&set(latch[1][1:4]) if len(latch)==2 else set()
    require(len(common)==1, 'Ambiguous common node of sense latch')
    tail_node, = common
    tails = [x for x in devices.values() if x[5]=='sky130_fd_pr__nfet_01v8' and branch(x[2],sclk)
             and tail_node in (x[1],x[3])]
    require(len(tails)==1, 'Ambiguous sense tail device')
    tail, = tails
    gnd = next(p for p in (tail[1],tail[3]) if p!=tail_node)
    require(branch(gnd,'VSS'), 'Unexpected sense tail rail')
    labels = dict(cell_q=q,cell_qb=qb,wl_at_q=a[2],wl_at_qb=b[2],bl_at_cell=cl,blb_at_cell=cr,
                  bl_at_sense=sl,blb_at_sense=sr,sa_sampling_out=la,sab_sampling_out=lb,
                  sclk_sampler_bl=sa[2],sclk_sampler_blb=sb[2],sclk_tail=tail[2],
                  sense_tail=tail_node,tail_ground=gnd)
    return labels, {'cell':[a[0],b[0],*inverter_cards], 'sense_sampling':[sa[0],sb[0]], 'sense_tail':tail[0]}


def points(line):
    prefix,card = line.split('PWL(',1)
    tokens = card.removesuffix(')').split()
    require(len(tokens)%2==0 and all(k.endswith('n') for k in tokens[::2]),'Malformed PWL')
    native = [(Decimal(t[:-1]),Decimal(v)) for t,v in zip(tokens[::2],tokens[1::2])]
    require(all(v[0]>u[0] for u,v in zip(native,native[1:])),'Nonincreasing PWL')
    return prefix,native


def reduced_points(native):
    before = [p for p in native if p[0]<JOIN_NS]
    after = [p for p in native if p[0]>=JOIN_NS]
    require(len(after)%2==0,'Unexpected PWL cut inside a ramp')
    reduced = before[:]
    for (start,_),(end,new) in zip(after[::2],after[1::2],strict=True):
        require(end-start==RAMP,'Expected original 50 ps PWL ramp')
        cycle = int((start-7)//20)
        if cycle in INDEX:
            cut = 20*(cycle-INDEX[cycle])
            reduced.extend([(start-cut,reduced[-1][1]),(end-cut,new)])
    require(all(v[0]>u[0] for u,v in zip(reduced,reduced[1:])), 'Reduced PWL events conflict')
    return reduced


def value_at(p,t):
    for (a,u),(b,v) in zip(p,p[1:]):
        if a<=t<=b:
            return u+(v-u)*(t-a)/(b-a)
    require(t>=p[-1][0],'PWL does not cover observation')
    return p[-1][1]


def cyclic_preflight(drives, original, records):
    history = {}
    for old in RETAINED:
        rec = records[old]
        offset = Decimal(20*(old-INDEX[old]))
        at = Decimal(rec['rise_ns'])+Decimal('.1')-offset
        pair = (value_at(drives['V_ADDR0'],at),value_at(drives['V_ADDR1'],at))
        require(sum(int(v==Decimal('1.8'))<<i for i,v in enumerate(pair))==rec['row'], 'Reduced address differs')
        op = rec['operation']
        expected = {'idle':(1,1,1),'write':(0,1,0),'read':(0,0,1)}[op]
        require(all(value_at(drives['V_'+key],at)==Decimal('1.8')*level
                    for key,level in zip(('CSb','OEb','WEb'),expected)), 'Reduced mode differs')
        require(value_at(drives['V_CLK'],at)==Decimal('1.8'), 'Missing high clock phase')
        require(value_at(drives['V_HOST_EN'],at)==(Decimal('1.8') if op=='write' else 0), 'Host direction differs')
        if op=='write':
            word = sum(int(value_at(drives[f'V_HOST{i}'],at)==Decimal('1.8'))<<i for i in range(8))
            require(word==rec['expected'],'Reduced write data differs')
            history[rec['row']] = word
        elif op=='read':
            require(history[rec['row']]==rec['expected'],'Reduced read loses a preceding write')
            for name in drives:
                start = Decimal(rec['control_start_ns'])+Decimal('.1')
                end = Decimal(str(rec['weak_off_ns']))+RAMP
                if name.startswith('V_WPAY') and old==14:
                    # The prior payload may differ before the c14 weak source is connected.
                    start = Decimal(str(rec['calibration']['weak_on_ns']))
                instants = {start,end}|{t for t,_ in original[name] if start<t<end}
                if name.startswith('V_HOST') and name not in ('V_HOST_EN','V_HOST_WEAK_EN'):
                    # The unused strong payload may remember a different previous pattern.
                    continue
                require(all(value_at(drives[name],t-offset)==value_at(original[name],t) for t in instants),
                        f'Reduced read stimulus differs at c{old}, {name}')
    require(history=={0:0x55,1:0xAA,2:0x0F,3:0xF0},'Final array contents differ')


def reduced_deck(source, labels, records):
    rewritten = []
    drives, original = {}, {}
    for line in source.splitlines():
        if line.startswith(('V_CLK ','V_CSb ','V_OEb ','V_WEb ','V_ADDR','V_HOST','V_WPAY')):
            name = line.split()[0]
            prefix, native = points(line)
            reduced = reduced_points(native)
            original[name],drives[name] = native,reduced
            line = prefix+'PWL('+' '.join(f'{t}n {v}' for t,v in reduced)+')'
        elif line.startswith(('.save ','wrdata waveform.dat ')):
            vectors = ' '.join(f'v(xdut.{n})' for n in sorted(set(labels.values())))
            filtered = ' '.join(v for v in vectors.split() if v not in line.split())
            line = f'{line} {filtered}'.rstrip()
        elif line=='tran 10p 370n 0 25p':
            line = f'tran 10p {STOP_NS}n 0 25p'
        rewritten.append(line)
    for name in drives:
        require([p for p in original[name] if p[0]<JOIN_NS]==[p for p in drives[name] if p[0]<JOIN_NS],
                'Write prefix differs')
    cyclic_preflight(drives,original,records)
    for time,_ in drives['V_HOST_EN']+drives['V_HOST_WEAK_EN']:
        require(not (value_at(drives['V_HOST_EN'],time)>0 and value_at(drives['V_HOST_WEAK_EN'],time)>0),
                'Weak and strong drive overlap')
    return '\n'.join(rewritten)+'\n'


def prepare(output):
    receipt = checked_preparation(PARENT)
    sim = json.loads((PARENT/'simulation.json').read_text())
    require(receipt['conditions']['corner']=='tt' and sim['simulator_status']=='PASS' and
            sim['preparation_sha256']==sha256(PARENT/'preparation.json'), 'Invalid parent TT run')
    pinned(PARENT/'waveform.dat',sim['waveform_sha256'])
    raw = pinned(PEX/'extracted_rc.spice',PEX_SHA).read_text()
    aliases,devices = node_roots(raw)
    names = rc_node_map(raw)
    parents = json.loads((PARENT/'probes.json').read_text())
    mapping = {key:names[val] for key,val in aliases.items()}
    require(mapping['bl_at_sense']==parents[f'{ARRAY}.write_driver_3.BL']
            and mapping['blb_at_sense']==parents[f'{ARRAY}.write_driver_3.BLB']
            and mapping['sclk_sampler_bl']==parents['SCLK_SENSE_3'],'Parent BL/sense probe identity differs')
    aliases_to_save = {**parents,**mapping}
    require(bind_rc_deck(raw)[0]==(PARENT/'binding.spice').read_text(), 'Circuit binding changed')
    fixture = json.loads((PARENT/'fixture.json').read_text())
    bench = reduced_deck((PARENT/'bench.spice').read_text(),aliases_to_save,fixture['cycles'])
    output = new_directory(output)
    for name in ('binding.spice','fabric.spice','model_hashes.json'):
        (output/name).write_bytes((PARENT/name).read_bytes())
    (output/'bench.spice').write_text(bench)
    (output/'probes.json').write_text(json.dumps(aliases_to_save,indent=2)+'\n')
    source = {str(p.relative_to(ROOT)):sha256(p) for p in
              (PARENT/'preparation.json',PARENT/'simulation.json',Path(__file__).resolve())}
    result = dict(status='VERIFIED_OFFLINE',role='diagnostic_only',
                  conditions={**receipt['conditions'],'stop_ns':STOP_NS},
                  parent_cycles=RETAINED,cycle_index=INDEX,identical_stimulus_until_ns=JOIN_NS,
                  candidate=receipt['candidate'],pex_sha256=PEX_SHA,
                  parent_waveform_sha256=sim['waveform_sha256'],
                  probe_pex_nodes=aliases,probe_devices=devices,sources=source,
                  artifacts={p.name:sha256(p) for p in output.iterdir()})
    (output/'preflight.json').write_text(json.dumps(result,indent=2)+'\n')
    print(output,flush=True)


def simulate(output, timeout_s):
    checked_preparation(PARENT)
    mf = output/'preflight.json'
    receipt = json.loads(mf.read_text())
    require(receipt['status']=='VERIFIED_OFFLINE' and receipt['conditions']['corner']=='tt'
            and receipt['conditions']['stop_ns']==STOP_NS, 'Expected sealed reduced TT deck')
    for rel,digest in receipt['sources'].items():
        pinned(ROOT/rel,digest)
    for name,digest in receipt['artifacts'].items():
        pinned(output/name,digest)
    require(model_closure(PDK)==json.loads((output/'model_hashes.json').read_text()),'PDK changed')
    command = ['ngspice','-n','-b','bench.spice']
    with (output/'attempt.json').open('x') as attempt:
        json.dump(dict(command=command,timeout_s=timeout_s,preflight_sha256=sha256(mf)),attempt)
    begin = time.monotonic()
    result = dict(status='ERROR',electrical_qualification='NOT_CHARACTERIZED',command=command,
                  preflight_sha256=sha256(mf),timeout_s=timeout_s)
    log = output/'ngspice.log'
    try:
        with (BUILD/'.eco_simulator.lock').open('a') as lock, log.open('x') as stream:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            proc = subprocess.run(command,cwd=output,stdout=stream,stderr=subprocess.STDOUT,
                                  timeout=timeout_s,check=False,preexec_fn=ngspice_limits,
                                  env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'})
        result['returncode'] = proc.returncode
        text = log.read_text(errors='replace')
        require(proc.returncode==0 and re.search(r'^ngspice-\S+ done\s*$',text,re.M)
                and not re.search(r'analysis aborted|simulation interrupted|^\s*(?:Fatal|Error):',text,re.I|re.M),
                'Reduced TT transient did not complete')
        result.update(status='PASS',waveform_sha256=sha256(output/'waveform.dat'))
    except subprocess.TimeoutExpired:
        result.update(status='TIMEOUT',error='Reduced TT exceeded timeout')
    except (OSError,ValueError) as error:
        result.update(error=str(error))
    finally:
        result['elapsed_s'] = time.monotonic()-begin
        if log.exists():
            ticks = re.findall(rb'Reference value\s*:\s*(\S+)',log.read_bytes())
            result.update(log_sha256=sha256(log),last_progress_s=float(ticks[-1]) if ticks else None)
        (output/'simulation.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)
    return int(result['status']!='PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','simulate'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--timeout',type=int,default=2100)
    args = parser.parse_args()
    if args.action=='prepare':
        prepare(args.output.resolve())
        return 0
    require(0<args.timeout<=2100,'Use a wall timeout of at most 2100 s')
    return simulate(args.output.resolve(),args.timeout)


if __name__=='__main__':
    raise SystemExit(main())
