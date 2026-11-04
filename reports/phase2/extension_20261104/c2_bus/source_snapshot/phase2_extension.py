"""Stimulus and independent observers for the two bounded Phase 2 campaigns."""
from collections import Counter
import json
import re
import numpy as np
from run_phase2_startup_review import SOURCE, GDS, make_probes, levels, validate_trace
from run_phase2_directed_review import observation_map
from phase2_access_checks import check as protocol_check


def campaign(name, pilot=False):
    seq=[('idle',0,0),('idle',0,0),('write',0,0xAA),('write',1,0x55),
         ('write',2,0x0F),('write',3,0xF0)]
    if name=='sequences':
        seq += [('read',0,0xAA),('read',0,0xAA),('write',0,0x55),('write',0,0xAA),
                ('read',0,0xAA),('read',1,0x55),('write',1,0xAA),('read',1,0xAA),
                ('write',2,0xF0),('read',2,0xF0),('read',3,0xF0),('idle',0,0),
                ('read',3,0xF0),('read',3,0xF0)]
    elif name=='bus':
        seq += [('read',0,0xAA),('read',1,0x55),('write',0,0xAA),('read',0,0xAA),
                ('write',1,0x55),('read',1,0x55),('idle',0,0),('read',0,0xAA),('read',1,0x55)]
    else:raise ValueError('Unknown campaign')
    if pilot and name!='sequences':raise ValueError('Only C1 has a pilot')
    return seq[:8] if pilot else seq


def probes(state,design,bus):
    vectors,extra=make_probes(state,design)
    probe=observation_map((GDS/'final_extracted.spice').read_text(),(SOURCE/'binding.spice').read_text(),(GDS/'final_flat.ext').read_text())
    top=design['modules']['sram_4x8_wrapper']
    for bit,q in enumerate(top['netnames']['control.DIN_Q']['bits']):
        ff=next(n for n,c in top['cells'].items() if c['type'].startswith('sky130_fd_sc_hd__df') and c['connections']['Q']==[q])
        extra[f'DIN_Q{bit}']=probe(ff+'.Q')
    for bit,q in enumerate(top['netnames']['control.ADDR_Q']['bits']):
        ff=next(n for n,c in top['cells'].items() if c['type'].startswith('sky130_fd_sc_hd__df') and c['connections']['Q']==[q])
        extra[f'ADDR_Q{bit}']=probe(ff+'.Q')
    for bit,node in enumerate(top['ports']['DATA']['bits']):
        name=next(n for n,c in top['cells'].items() if c['type']=='sky130_fd_sc_hd__ebufn_1' and c['connections']['Z']==[node])
        extra[f'TE_B{bit}']=probe(name+'.TE_B')
    extra['WEAK_EN']='v(HOST_WEAK_EN)'
    for bit in range(8):
        extra[f'HOST{bit}']=f'v(HOST{bit})'
        if bus:
            extra[f'I_HOST{bit}']=f'i(v_sense_host{bit})'
            extra[f'I_WEAK{bit}']=f'i(v_sense_weak{bit})'
    for v in extra.values():
        if v not in vectors:vectors.append(v)
    return vectors,extra


def deck(name,pilot,state,vectors):
    seq=campaign(name,pilot);bus=name=='bus'
    names=['CLK','CSb','OEb','WEb','ADDR0','ADDR1','HOST_EN','HOST_WEAK_EN',*[f'HOST{b}' for b in range(8)]]
    signals={n:[(0.,0.)] for n in names}
    for n in ('CSb','OEb','WEb'):signals[n].append((1.,1.))
    def event(n,t,v):
        if t<signals[n][-1][0]:raise ValueError('Nonmonotonic stimulus: '+n)
        signals[n].extend([(t,signals[n][-1][1]),(t+.05,float(v))])
    records=[];handoffs=0
    for i,(op,row,value) in enumerate(seq):
        edge=10+20*i;read=op=='read';write=op=='write';before=seq[i-1][0] if i else None
        ctl=(0,0,1) if read else (0,1,0) if write else (1,1,1)
        for n,v in zip(('CSb','OEb','WEb'),ctl):event(n,edge-3,v)
        for b in range(2):
            event(f'ADDR{b}',edge-3,(row>>b)&1)
            if not bus and op in ('read','write'):event(f'ADDR{b}',edge+3,((row^3)>>b)&1)
        record=dict(cycle=i,operation=op,row=row,expected=value,rise_ns=edge,fall_ns=edge+10,
                    sample_ns=edge+(11 if bus else 12))
        if bus:
            if write:
                for b in range(8):event(f'HOST{b}',edge-2.9,(value>>b)&1)
                guard=(.3 if handoffs%2==0 else .6) if before=='read' else 1.
                if before=='read':handoffs+=1
                event('HOST_EN',edge-3+guard,1)
                record.update(host_payload_ns=edge-2.9,host_enable_ns=edge-3+guard,handoff_guard_ns=guard)
            else:
                event('HOST_EN',edge-.1 if before=='write' else edge-2,0)
                if read:
                    for b in range(8):event(f'HOST{b}',edge+11.2,((value^255)>>b)&1)
                    event('HOST_WEAK_EN',edge+11.5,1)
                    event('CSb',edge+12.5,1);event('CSb',edge+14,0)
                    event('HOST_WEAK_EN',edge+15.5,0)
                    record['calibration']=dict(weak_on_ns=edge+11.5,mask_ns=edge+12.5,
                        restore_ns=edge+14,weak_off_ns=edge+15.5,current_floor_a=50e-6,ron_ohm=1000)
        else:
            for b in range(8):
                event(f'HOST{b}',edge-2.5,(value>>b)&1)
                if write:event(f'HOST{b}',edge+3,((value^255)>>b)&1)
            event('HOST_EN',edge-2,write);event('HOST_EN',edge+1,0)
        event('CLK',edge,1);event('CLK',edge+10,0);records.append(record)
    stop=10+20*len(seq)
    old=(SOURCE/'bench.spice').read_text().splitlines();start=next(i for i,l in enumerate(old) if l.startswith('V_CLK '))
    lines=old[:start]
    for n,events in signals.items():lines.append(f'V_{n} {n} 0 PWL('+' '.join(f'{t:.8g}n {v*1.8:.8g}' for t,v in events)+')')
    for l in old:
        if l.startswith(('S_HOST','S_WEAK')):
            if bus:
                f=l.split();bit=int(re.search(r'(\d+)$',f[0])[1]);weak=f[0].startswith('S_WEAK')
                meter=f'v_sense_{"weak" if weak else "host"}{bit}';node=f'METER_{"WEAK" if weak else "HOST"}{bit}'
                original=f[1];f[1]=node;lines.extend([' '.join(f),f'{meter} {node} {original} 0'])
            else:lines.append(l)
        elif l.startswith('XDUT '):lines.append(l)
    lines+=['.save '+' '.join(vectors),'.control','set num_threads=1','set noaskquit','set wr_singlescale','set wr_vecnames',
            f'tran 10p {stop}n 0 10p','wrdata waveform.dat '+' '.join(vectors),'quit','.endc','.end']
    return '\n'.join(lines)+'\n',records,stop


def check(data,records,vectors,extra,state,stop,name):
    validate_trace(data,vectors,stop);t=data[:,0]*1e9
    checks,reference=protocol_check(data[t>=3],records,vectors,state['capture_inputs'],state['capture_clocks'])
    def col(n):return vectors.index(extra[n])+1
    def at(ns):return int(np.searchsorted(t,ns))
    def window(a,b):return (t>=a)&(t<=b)
    def put(kind,ok,**detail):checks.append(dict(kind=kind,status='PASS' if ok else 'FAIL',**detail))
    memory={};previous_read=None;read_bits=0
    for r in records:
        op=r['operation'];edge=r['rise_ns'];fall=r['fall_ns'];sample=at(r['sample_ns'])
        high=window(edge+1,fall-.5)
        for n,expected in [('READ_Q',op=='read'),('WRITE_Q',op=='write')]:
            put('captured_operation',levels(data[high,col(n)],expected),cycle=r['cycle'],signal=n)
        if op in ('read','write'):
            for b in range(2):put('captured_address',levels(data[high,col(f'ADDR_Q{b}')],(r['row']>>b)&1),cycle=r['cycle'],bit=b)
        if op=='write':
            for b in range(8):put('captured_write_data',levels(data[high,col(f'DIN_Q{b}')],(r['expected']>>b)&1),cycle=r['cycle'],bit=b)
            memory[r['row']]=r['expected']
        for row,word in memory.items():
            for b in range(8):put('known_storage',levels(data[sample:sample+1,col(f'CELL_{row}_{b}')],(word>>b)&1),cycle=r['cycle'],row=row,bit=b)
        if previous_read is not None:
            for b in range(8):
                put('previous_ff_q_retained',levels(data[high,col(f'REG_Q{b}')],(previous_read>>b)&1),cycle=r['cycle'],bit=b)
                if op=='read':put('previous_data_visible_before_new_capture',levels(data[high,b+1],(previous_read>>b)&1),cycle=r['cycle'],bit=b)
        if op=='read':
            if memory.get(r['row'])!=r['expected']:raise ValueError('Read expectation not established by a write')
            read_bits+=8
            for b in range(8):
                expected=(r['expected']>>b)&1
                put('read_data',levels(data[sample:sample+1,b+1],expected),cycle=r['cycle'],bit=b)
                put('captured_ff_q',levels(data[sample:sample+1,col(f'REG_Q{b}')],expected),cycle=r['cycle'],bit=b)
            previous_read=r['expected']
        if name=='bus' and op=='read':
            cal=r['calibration'];enabled=window(edge+12,edge+12.35);disabled=window(edge+13.2,edge+13.8);restored=window(edge+14.7,edge+15.2)
            for b in range(8):
                current=data[:,col(f'I_WEAK{b}')];target=(r['expected']>>b)&1
                put('probe_observes_enabled_drive',bool(np.any(enabled)) and bool(np.all(np.abs(current[enabled])>50e-6)),cycle=r['cycle'],bit=b)
                put('masked_probe_current',bool(np.any(disabled)) and bool(np.all(np.abs(current[disabled])<=50e-6)),cycle=r['cycle'],bit=b)
                put('masked_probe_voltage',bool(np.any(disabled)) and bool(np.all(np.abs(data[disabled,b+1]-1.8*(1-target))<=.05)),cycle=r['cycle'],bit=b)
                put('restored_drive_current',bool(np.any(restored)) and bool(np.all(np.abs(current[restored])>50e-6)),cycle=r['cycle'],bit=b)
                for offset in (12.0,13.5,14.8,16.3):
                    k=at(edge+offset);put('mask_preserves_ff_q',levels(data[k:k+1,col(f'REG_Q{b}')],target),cycle=r['cycle'],bit=b,time_ns=edge+offset)
                k=at(edge+16.3);put('data_after_probe_removed',levels(data[k:k+1,b+1],target),cycle=r['cycle'],bit=b)
        if name=='bus' and op=='write':
            steady=window(max(r['host_enable_ns'],r['host_payload_ns'])+.25,fall-1)
            for b in range(8):put('strong_master_steady_current',bool(np.any(steady)) and bool(np.all(np.abs(data[steady,col(f'I_HOST{b}')])<=50e-6)),cycle=r['cycle'],bit=b)
    if name=='bus':
        active=(t>=3)&(data[:,col('HOST_EN')]>.36)
        for b in range(8):
            overlap=active&(data[:,col(f'TE_B{b}')]<1.44)
            put('no_strong_host_ebuf_overlap',not bool(np.any(overlap)),bit=b,bad_samples=int(np.sum(overlap)))
    return checks,reference,dict(read_bit_checks=read_bits,checks_by_kind=dict(Counter(c['kind'] for c in checks)),
        coverage=[dict(before=a['operation'],after=b['operation'],same_row=a['row']==b['row']) for a,b in zip(records,records[1:])])
