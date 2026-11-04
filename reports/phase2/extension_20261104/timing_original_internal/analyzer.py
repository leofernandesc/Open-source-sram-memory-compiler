#!/usr/bin/env python3
"""Full-raw nominal event/capture/current analysis; no timing specification."""
import argparse,csv,json
from pathlib import Path
import numpy as np
from run_phase2_digital import ROOT,sha
from run_phase2_startup_review import SOURCE,levels,validate_trace


def crossing(t,v,level,lo,hi,rising=True):
    event=((v[:-1]<level)&(v[1:]>=level)) if rising else ((v[:-1]>level)&(v[1:]<=level))
    ids=np.flatnonzero(event&(t[:-1]>=lo)&(t[:-1]<hi))
    if len(ids)!=1:raise ValueError(f'Expected one event, found {len(ids)} at {lo}..{hi}')
    k=int(ids[0]);return float(t[k]+(level-v[k])/(v[k+1]-v[k])*(t[k+1]-t[k]))


def valid(v,bit):return ((v>=1.44)&(v<=1.98)) if bit else ((v>=-.18)&(v<=.36))


def settle(t,v,bit,lo,hi):
    inside=(t>=lo)&(t<=hi);ids=np.flatnonzero(inside)
    if not len(ids) or not valid(v[ids[-1]:ids[-1]+1],bit)[0]:raise ValueError('Data not valid by observation end')
    bad=ids[~valid(v[ids],bit)]
    return (float(t[bad[-1]+1]),False) if len(bad) else (float(lo),True)


def current_event(t,v,lo,hi,on):
    # Last threshold crossing after which the condition stays satisfied.
    magnitude=np.abs(v);inside=np.flatnonzero((t>=lo)&(t<=hi));good=magnitude>50e-6 if on else magnitude<=50e-6
    if not len(inside) or not good[inside[-1]]:raise ValueError('Current did not settle into requested conduction state')
    bad=inside[~good[inside]]
    if not len(bad):return float(lo),True
    k=int(bad[-1]);x=float(t[k]+(50e-6-magnitude[k])/(magnitude[k+1]-magnitude[k])*(t[k+1]-t[k]))
    return x,False


def measure(source,internal_only=False):
    s=json.loads((source/'results.json').read_text());path=ROOT/s['build_directory']/'waveform.dat';rawkey='raw_sha256' if 'raw_sha256' in s else 'raw_waveform_sha256'
    if sha(path)!=s[rawkey]:raise ValueError('Full raw identity differs')
    if s['status'] not in ('PASS','PASS_DIRECTED_NOMINAL','PASS_EXTRACTED_NOMINAL_ACCESS','FAIL_ELECTRICAL_SCREEN'):raise ValueError('Complete electrical scenario required')
    d=np.loadtxt(path,skiprows=1);t=d[:,0]*1e9;vectors=s['vectors'];validate_trace(d,vectors,s.get('stop_ns',max(r['fall_ns'] for r in s['cycles'])+10));extra=s.get('probes',s.get('extra_probes',{}));base=json.loads((SOURCE/'results.json').read_text())
    if d.shape[1]!=len(vectors)+1 or not np.all(np.isfinite(d)) or not np.all(np.diff(t)>0):raise ValueError('Invalid trace')
    def col(n):return vectors.index(extra[n])+1
    phase=[];capture=[];bus=[];checks=[];previous=None
    def put(kind,ok,**detail):checks.append(dict(kind=kind,status='PASS' if ok else 'FAIL',**detail))
    for r in s['cycles']:
        op=r['operation'];edge=r['rise_ns'];fall=r['fall_ns']
        if op not in ('read','write'):continue
        before=(t>=edge-.8)&(t<=edge-.2)
        if all(f'N{i}' in extra for i in range(4)):
            for i in range(4):put('decoder_precharged_each_access',levels(d[before,col(f'N{i}')],1),cycle=r['cycle'],row=i)
        if all(f'BL{i}' in extra for i in range(8)):
            for i in range(8):
                for line in ('BL','BLB'):put('bitline_precharged_each_access',levels(d[before,col(f'{line}{i}')],1),cycle=r['cycle'],bit=i,line=line)
        pre_off=crossing(t,d[:,10],1.44,edge,fall,True);pre_on=crossing(t,d[:,10],1.44,fall,edge+19,False)
        wl_on=crossing(t,d[:,13+r['row']],1.44,edge,fall,True);wl_off=crossing(t,d[:,13+r['row']],.36,fall,edge+19,False)
        pclk=crossing(t,d[:,9],.36,edge,fall,True)
        a=dict(source=str(source.relative_to(ROOT)),cycle=r['cycle'],operation=op,row=r['row'],pclk_on20_ns=pclk,
               precharge_release_ns=pre_off,wordline_active80_ns=wl_on,wordline_release20_ns=wl_off,
               precharge_resume80_ns=pre_on,wl_release_guard_ns=pre_on-wl_off,write_release_guard_ns=None,
               write_on_guard_ns=None,wl_to_sense_ns=None,minimum_signed_bl_at_sense_v=None)
        if op=='write':
            we_on=crossing(t,d[:,12],.36,edge,fall,True);we_off=crossing(t,d[:,12],.36,fall,edge+19,False)
            a.update(write_on20_ns=we_on,write_off20_ns=we_off,write_on_guard_ns=we_on-pre_off,write_release_guard_ns=pre_on-we_off)
        else:
            sense=crossing(t,d[:,11],.36,edge,fall,True);a['wl_to_sense_ns']=sense-wl_on;a['sense_on20_ns']=sense
            if 'BL0' in extra:
                a['minimum_signed_bl_at_sense_v']=min(float(np.interp(sense,t,d[:,col(f'BL{i}')])-np.interp(sense,t,d[:,col(f'BLB{i}')]))*(1 if (r['expected']>>i)&1 else -1) for i in range(8))
                a['minimum_signed_bl_50ps_before_sense_v']=min(float(np.interp(sense-.05,t,d[:,col(f'BL{i}')])-np.interp(sense-.05,t,d[:,col(f'BLB{i}')]))*(1 if (r['expected']>>i)&1 else -1) for i in range(8))
            public=crossing(t,d[:,col('CLK')],.9,fall-.1,fall+.2,False) if 'CLK' in extra else fall+.025
            for bit in range(8):
                expected=(r['expected']>>bit)&1;clockcol=vectors.index(base['capture_clocks'][bit])+1;fdcol=vectors.index(base['capture_inputs'][bit])+1
                local=crossing(t,d[:,clockcol],.9,fall-.5,fall+1,True)
                raw_start,raw_lower=settle(t,d[:,17+bit],expected,edge,local)
                fd_start,fd_lower=settle(t,d[:,fdcol],expected,edge,local)
                holdmask=(t>=local)&(t<=local+2)
                put('raw_hold_window_2ns',levels(d[holdmask,17+bit],expected),cycle=r['cycle'],bit=bit)
                put('ff_d_hold_window_2ns',levels(d[holdmask,fdcol],expected),cycle=r['cycle'],bit=bit)
                row=dict(source=str(source.relative_to(ROOT)),cycle=r['cycle'],bit=bit,expected=expected,
                         public_falling50_ns=public,local_capture50_ns=local,clock_arrival_from_public_ns=local-public,
                         raw_valid_before_capture_ns=local-raw_start,raw_start_lower_bound=raw_lower,
                         fd_valid_before_capture_ns=local-fd_start,fd_start_lower_bound=fd_lower,
                         raw_valid_time_ns=raw_start,fd_valid_time_ns=fd_start,
                         raw_from_sense20_ns=raw_start-sense,fd_from_raw_valid_ns=fd_start-raw_start,
                         ff_q_from_local_ns=None,data_from_public_fall_ns=None,
                         transition='unknown_previous_register' if previous is None else 'unchanged' if ((previous>>bit)&1)==expected else 'changed')
                if row['transition']=='changed' and f'REG_Q{bit}' in extra:
                    q_start,q_lower=settle(t,d[:,col(f'REG_Q{bit}')],expected,local,fall+1.25)
                    row.update(ff_q_from_local_ns=q_start-local,q_already_valid_at_edge=q_lower)
                    if not internal_only:
                        data_start,data_lower=settle(t,d[:,bit+1],expected,public,fall+1.25)
                        row.update(data_from_public_fall_ns=data_start-public,data_already_valid_at_edge=data_lower)
                capture.append(row)
            previous=r['expected']
        phase.append(a)
        if 'calibration' in r:
            cal=r['calibration'];disable=crossing(t,d[:,col('CSb')],.9,cal['mask_ns']-.1,cal['mask_ns']+.2,True)
            enable=crossing(t,d[:,col('CSb')],.9,cal['restore_ns']-.1,cal['restore_ns']+.2,False)
            for bit in range(8):
                off,off_bound=current_event(t,d[:,col(f'I_WEAK{bit}')],disable,cal['restore_ns']-.1,False)
                on,on_bound=current_event(t,d[:,col(f'I_WEAK{bit}')],enable,cal['weak_off_ns']-.1,True)
                bus.append(dict(cycle=r['cycle'],bit=bit,metric='live_CSb_probe_current',
                    disable_from_control50_ns=off-disable,enable_from_control50_ns=on-enable,
                    disable_lower_bound=off_bound,enable_lower_bound=on_bound,current_floor_a=50e-6,probe_ohm=1000,
                    interpretation='Conduction threshold under opposing 1k load; not full logic validity or guaranteed I/O timing'))
        if s.get('campaign')=='bus' and op=='write' and r.get('handoff_guard_ns') in (.3,.6):
            host=crossing(t,d[:,col('HOST_EN')],.36,r['host_enable_ns']-.1,r['host_enable_ns']+.2,True)
            for bit in range(8):
                release=crossing(t,d[:,col(f'TE_B{bit}')],1.44,edge-3-.1,edge-2,True)
                bus.append(dict(cycle=r['cycle'],bit=bit,metric='read_to_write_handoff',
                    stimulus_guard_ns=r['handoff_guard_ns'],measured_release_to_host20_ns=host-release,
                    interpretation='Observed enable-screen separation; master current separately checked'))
    return dict(source_receipt_sha256=sha(source/'results.json'),raw_sha256=sha(path),phase=phase,capture=capture,bus=bus,checks=checks)


def main():
    p=argparse.ArgumentParser();p.add_argument('--sources',nargs='+',required=True);p.add_argument('--output',required=True);p.add_argument('--internal-only',action='store_true',help='Exclude DATA availability for benches whose live output enable is masked around capture');a=p.parse_args();out=(ROOT/a.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2') or out.exists():p.error('New report directory required')
    out.mkdir(parents=True);record=dict(status='RUNNING',scope='Nominal raw-based event measurements, no qualified timing limits')
    try:
        allrows={k:[] for k in ('phase','capture','bus','checks')};inputs={}
        for rel in a.sources:
            data=measure(ROOT/rel,a.internal_only);inputs[rel]={k:data[k] for k in ('source_receipt_sha256','raw_sha256')}
            for k in allrows:allrows[k].extend(data[k])
        for key in ['phase','capture','bus']:
            rows=allrows[key]
            if not rows:continue
            fields=list(dict.fromkeys(k for r in rows for k in r))
            with (out/(key+'.csv')).open('w') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
        (out/'checks.json').write_text(json.dumps(allrows['checks'],indent=2)+'\n')
        ranges={}
        for table,fields in [('phase',['write_on_guard_ns','wl_to_sense_ns','wl_release_guard_ns','write_release_guard_ns','minimum_signed_bl_at_sense_v','minimum_signed_bl_50ps_before_sense_v']),('capture',['raw_valid_before_capture_ns','fd_valid_before_capture_ns','ff_q_from_local_ns','data_from_public_fall_ns','clock_arrival_from_public_ns']),('bus',['disable_from_control50_ns','enable_from_control50_ns','measured_release_to_host20_ns'])]:
            for key in fields:
                rows=[r for r in allrows[table] if r.get(key) is not None]
                if rows:ranges[key]=dict(min=min(r[key] for r in rows),max=max(r[key] for r in rows),samples=len(rows),worst_case=min(rows,key=lambda r:r[key]))
        record.update(status='PASS_MEASURED' if not any(r['status']=='FAIL' for r in allrows['checks']) else 'FAIL_SCREEN',
            inputs=inputs,ranges=ranges,internal_only=a.internal_only,additional_checks=len(allrows['checks']),failures=sum(r['status']=='FAIL' for r in allrows['checks']),
            methodology='10ps maximum step; crossing interpolation; valid-level settling sample quantization. 2ns post-capture window is a lower bound, not hold requirement.',
            analyzer_sha256=sha(Path(__file__)))
    except Exception as e:record.update(status='FAIL_ANALYSIS',error=str(e))
    record['artifacts']={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='results.json'}
    (out/'results.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:v for k,v in record.items() if k not in ['inputs','artifacts','ranges']},indent=2));return 0 if record['status']=='PASS_MEASURED' else 1


if __name__=='__main__':raise SystemExit(main())
