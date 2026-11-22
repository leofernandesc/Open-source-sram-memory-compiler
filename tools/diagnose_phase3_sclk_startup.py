#!/usr/bin/env python3
"""Compare three sealed 14 ns TT decks with process and SPICE phase telemetry."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
from fractions import Fraction
import json
import os
from pathlib import Path
import re
import resource
import selectors
import subprocess
import time

from phase3_sclk_r87 import BUILD, PDK, REFERENCE, checked, model_closure, require, sha256
from run_phase3_eco_pex import new_directory, ngspice_limits


STOP_NS = 14
LIMIT_S = 180
SOURCE = re.compile(rb'(?m)^I_sclk_r87 (\S+) (\S+) PWL\(([^\n]*(?:\n\+[^\n]*)*)\)\n')
MARKERS = {
    b'__R87_DECK_READY__': 'deck_ready',
    b'__R87_TRAN_DISPATCH__': 'tran_dispatch',
    b'Note: Transient op started': 'op_fallback_started',
    b'Note: Transient op finished successfully': 'op_fallback_finished',
    b'Initial Transient Solution': 'initial_solution_reported',
    b'__R87_TRAN_RETURN__': 'tran_return',
}
PROGRESS = re.compile(rb'Reference value\s*:\s*(\S+)')
FATAL = re.compile(rb'analysis aborted|timestep too small|^\s*(?:Fatal|Error):', re.I|re.M)


def write_json(path, payload):
    with path.open('x') as stream:
        json.dump(payload, stream, indent=2)
        stream.write('\n')


def source_points(card):
    tokens = re.sub(rb'\n\+', b' ', card[3]).decode().split()
    require(len(tokens)>=4 and len(tokens)%2==0 and all(t.endswith('n') for t in tokens[::2]),
            'Unexpected PWL units or point count')
    points = [(Fraction(t[:-1]), Fraction(i)) for t,i in zip(tokens[::2],tokens[1::2])]
    require(all(a[0]<b[0] for a,b in zip(points,points[1:])), 'PWL times must be strictly increasing')
    return points


def audit_pwl(points, card):
    # A point on the exact line between its neighbors changes no linear segment.
    retained = []
    for c in points:
        while len(retained)>=2:
            a,b = retained[-2:]
            if (b[1]-a[1])*(c[0]-b[0])!=(c[1]-b[1])*(b[0]-a[0]):
                break
            retained.pop()
        retained.append(c)
    zero_interior = sum(a[1]==b[1]==c[1]==0 for a,b,c in zip(points,points[1:],points[2:]))
    intervals = Counter(b[0]-a[0] for a,b in zip(points,points[1:]))
    peak = max(points, key=lambda point: abs(point[1]))
    return dict(point_count=len(points), distinct_timestamps=len(points),
                distinct_current_values=len({current for _,current in points}),
                card_bytes=len(card[0]), continued_lines=card[0].count(b'\n')-1,
                zero_current_points=sum(i==0 for _,i in points), zero_run_interior_points=zero_interior,
                interval_ns={str(k):v for k,v in sorted(intervals.items())},
                time_jumps=0, min_spacing_ps=float(min(intervals)*1000),
                earliest_nonzero_sample_ns=float(next(t for t,i in points if i)),
                peak_current_a=float(peak[1]), peak_current_ns=float(peak[0]),
                exact_piecewise_linear_points=len(retained), exact_removable_points=len(points)-len(retained),
                question='Exact removal preserves I(t), but may change simulator breakpoints.')


def prepare(previous, output):
    old = checked(previous)
    models = json.loads((previous/'model_hashes.json').read_text())
    require(model_closure(PDK)==models, 'PDK closure differs from the archived deck')
    original = (previous/'binding.spice').read_bytes()
    long = (previous/'norton_fixture.spice').read_bytes()
    match = SOURCE.search(long)
    require(match is not None and SOURCE.sub(b'',long)==original, 'Unexpected circuit difference')
    points = source_points(match)
    require(len(points)==3203 and points[0]==(0,0) and points[1][0]>STOP_NS, 'Unexpected archived PWL')
    zero = b'I_sclk_r87 '+match[1]+b' '+match[2]+b' PWL(0n 0 239n 0)\n'
    short = (previous/'startup.spice').read_text()
    ref = (REFERENCE/'bench.spice').read_text()
    require(ref.replace('tran 10p 250n 0 25p','tran 10p 14n 0 25p').replace('binding.spice','norton_fixture.spice')==short
            and short.count('.control\n')==1 and short.count('tran 10p 14n 0 25p\n')==1,
            'Diagnostic bench is no longer the 14 ns projection of the reference')
    bench = short.replace('norton_fixture.spice','circuit.spice').replace('.control\n','.control\necho __R87_DECK_READY__\n')
    bench = bench.replace('tran 10p 14n 0 25p\n','echo __R87_TRAN_DISPATCH__\ntran 10p 14n 0 25p\necho __R87_TRAN_RETURN__\n')
    variants = [('A_reference',original),('B_zero',SOURCE.sub(zero,long)),('C_original_pwl',long)]
    for label,circuit in variants:
        path = new_directory(output/label)
        (path/'bench.spice').write_text(bench)
        (path/'circuit.spice').write_bytes(circuit)
        (path/'fabric.spice').write_bytes((previous/'fabric.spice').read_bytes())
    write_json(output/'preflight.json',dict(preflight_sha256=sha256(previous/'preflight.json'),
        candidate=old['candidate'],pex_sha256=old['pex_sha256'],model_count=len(models),
        pdk_closure_sha256=sha256(previous/'model_hashes.json'), horizon_ns=STOP_NS,limit_s=LIMIT_S,
        artifacts={str(p.relative_to(output)):sha256(p) for p in sorted(output.glob('*/*.spice'))},
        sources={str(p):sha256(p) for p in (previous/'binding.spice',previous/'norton_fixture.spice',
                  previous/'startup.spice',REFERENCE/'bench.spice',Path(__file__))},pwl=audit_pwl(points,match)))
    return [label for label,_ in variants]


class Observations:
    def __init__(self):
        self.events = {}
        self.buffers = {'stdout':b'', 'stderr':b''}
        self.latest_ns = None
        self.max_ns = None

    def feed(self, channel, chunk, stamp, eof=False):
        if chunk:
            self.events.setdefault('first_output', dict(stamp,stream=channel))
            self.events.setdefault(f'first_{channel}', stamp)
        records = re.split(rb'[\r\n]',self.buffers[channel]+chunk)
        self.buffers[channel] = b'' if eof else records.pop()
        for record in records:
            for marker,name in MARKERS.items():
                if marker in record:
                    self.events.setdefault(name,dict(stamp,stream=channel))
            value = PROGRESS.search(record)
            if value:
                self.latest_ns = float(value[1])*1e9
                self.max_ns = max(self.latest_ns,self.max_ns) if self.max_ns is not None else self.latest_ns
                if self.latest_ns>0:
                    self.events.setdefault('first_positive_reference',dict(stamp,stream=channel,ns=self.latest_ns))


def proc_sample(pid, stamp, latest, previous):
    proc = Path('/proc')/str(pid)
    try:
        stat = (proc/'stat').read_text().rsplit(')',1)[1].split()
        name = os.readlink(proc/'exe')
        status = dict(line.split(':',1) for line in (proc/'status').read_text().splitlines() if ':' in line)
    except (OSError, IndexError):
        return None
    try:
        io = {k:int(v) for k,v in (line.split(':',1) for line in (proc/'io').read_text().splitlines())}
        wchan = (proc/'wchan').read_text().strip()
    except OSError:
        io,wchan = None,None
    cpu = (int(stat[11])+int(stat[12]))/os.sysconf('SC_CLK_TCK')
    pct = 100*(cpu-previous['cpu_s'])/(stamp['elapsed_s']-previous['elapsed_s']) if previous else None
    memory = {key:int(status[key].split()[0]) if key in status else None for key in ('VmRSS','VmHWM')}
    return dict(stamp,pid=pid,exe=name,state=stat[0],wait_channel=wchan,cpu_s=cpu,cpu_pct=pct,
                rss_kib=memory['VmRSS'],hwm_kib=memory['VmHWM'],io=io,reference_ns=latest)


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def run(path, wrapper, version):
    def stamp():
        return dict(wall=now(),elapsed_s=round(time.monotonic()-started,6))

    cmd = ['stdbuf','-o0','-e0','ngspice','-n','-b','bench.spice']
    old = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.monotonic()
    start_stamp = stamp()
    obs,samples = Observations(),[]
    write_json(path/'attempt.json',dict(wrapper_started=wrapper,launch=start_stamp,command=cmd,version=version,
        process_timeout_s=LIMIT_S,artifacts={p.name:sha256(p) for p in path.glob('*.spice')}))
    reason = 'EXIT'
    with (path/'stdout.log').open('xb') as stdout, (path/'stderr.log').open('xb') as stderr, \
            (path/'samples.jsonl').open('x',buffering=1) as telemetry, selectors.DefaultSelector() as selector:
        with subprocess.Popen(cmd,cwd=path,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'},
                              preexec_fn=ngspice_limits) as proc:
            launched = dict(stamp(),pid=proc.pid)
            selector.register(proc.stdout,selectors.EVENT_READ,('stdout',stdout))
            selector.register(proc.stderr,selectors.EVENT_READ,('stderr',stderr))
            next_sample = 0.
            while proc.poll() is None or selector.get_map():
                elapsed = time.monotonic()-started
                if elapsed>=LIMIT_S-.5 and reason=='EXIT' and proc.poll() is None:
                    reason = 'WALL_TIMEOUT'
                    proc.terminate()
                if elapsed>=LIMIT_S and proc.poll() is None:
                    proc.kill()
                for key,_ in selector.select(.20):
                    channel,log = key.data
                    chunk = os.read(key.fd,65536)
                    log.write(chunk)
                    obs.feed(channel,chunk,stamp(),eof=not chunk)
                    if not chunk:
                        selector.unregister(key.fileobj)
                if elapsed>=next_sample:
                    sample = proc_sample(proc.pid,stamp(),obs.latest_ns,samples[-1] if samples else None)
                    if sample:
                        samples.append(sample)
                        telemetry.write(json.dumps(sample)+'\n')
                        next_sample = elapsed+5
            ended = stamp()
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    waveform = path/'waveform.dat'
    final_ns = None
    if waveform.is_file():
        with waveform.open('rb') as stream:
            rows = [line for line in stream if line.strip()]
        if len(rows)>1:
            final_ns = float(rows[-1].split()[0])*1e9
    raw = (path/'stdout.log').read_bytes()+(path/'stderr.log').read_bytes()
    completed = reason=='EXIT' and proc.returncode==0 and not FATAL.search(raw) and final_ns==STOP_NS
    result = dict(status='COMPLETED' if completed else ('TIMEOUT' if reason=='WALL_TIMEOUT' else 'ERROR'),
                  stop_reason=reason,wrapper_started=wrapper,ngspice_pid=proc.pid,process_launched=launched,
                  process_ended=ended,events={key:obs.events.get(key) for key in ('first_output','first_stdout',
                      'first_stderr',*MARKERS.values(),'first_positive_reference')},
                  max_reference_ns=obs.max_ns,waveform_end_ns=final_ns,
                  cpu_user_s=usage.ru_utime-old.ru_utime,cpu_system_s=usage.ru_stime-old.ru_stime,
                  peak_rss_kib_sampled=max((s['hwm_kib'] for s in samples if s['hwm_kib'] is not None),default=None),
                  sample_count=len(samples),exit_code=proc.returncode,
                  artifacts={p.name:sha256(p) for p in path.iterdir() if p.is_file()})
    write_json(path/'result.json',result)
    print(f'{path.name}: {result["status"]} in {ended["elapsed_s"]:.3f}s',flush=True)
    return result


def main():
    wrapper = now()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    output = new_directory(args.output.resolve())
    version = subprocess.check_output(['ngspice','--version'],text=True,timeout=10)
    variants = prepare(BUILD/'sclk_r87_20261120',output)
    results = {}
    with (BUILD/'.eco_simulator.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for label in variants:
            result = run(output/label,wrapper,version)
            results[label] = result
            if result['status']=='ERROR' or (label=='A_reference' and result['events']['tran_dispatch'] is None):
                break
    write_json(output/'comparison.json',dict(wrapper_started=wrapper,wrapper_ended=now(),results=results,
                   preflight_sha256=sha256(output/'preflight.json')))


if __name__=='__main__':
    main()
