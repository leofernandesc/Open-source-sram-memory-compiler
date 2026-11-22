#!/usr/bin/env python3
"""Run one sealed R87 contrast with phase-aware process and output telemetry."""

import argparse
import fcntl
import json
import math
import os
from pathlib import Path
import re
import resource
import selectors
import subprocess
import time

from analyze_phase3_data3_tt import load
from diagnose_phase3_sclk_startup import Observations, SOURCE, now, proc_sample, source_points, write_json
from phase3_sclk_r87 import (BUILD, DELAY_PS, FULL_NS, PDK, REFERENCE, ROOT, WINDOWS, branch, checked,
                            current_points, model_closure, overlay, require, sha256)
from run_phase3_data3_tt import PARENT, checked_preparation
from run_phase3_eco_pex import new_directory, ngspice_limits, pinned


ORIGINAL = BUILD/'sclk_r87_20261120'
STARTUP = BUILD/'sclk_startup_diagnostic_20261120'
COMPARISON_SHA = '61e6e631d068aefafad9a09dcc6c2bda6d4d046c1254090c1e9fb1e7ab050493'
HISTORICAL_GATE_SHA = 'db8647623f18eed671a498613574290841abf4c82c916ab3668e351413748a46'
BUDGET = dict(wall_s=3000, preparation_s=300, integration_s=2850, termination_grace_s=2)
CURRENT = '@i.xdut.i_sclk_r87[current]'
FATAL = re.compile(rb'analysis aborted|timestep too small|\bfatal error:|out of memory|transient op failed',re.I)
FIDELITY = dict(vdd_v=1.8, cross_percent=[20,50,80], displacement_ps=182,
                each_rise_ps=25, unchanged_fall_ps=25, slew_difference_ps=50,
                width_difference_ps=50, common_edge_ps=25,
                logic_low_v=.36,logic_high_v=1.44)


def observed_deck(deck, extra):
    require(deck.count('tran 10p 250n 0 25p\n')==1 and deck.count('.control\n')==1
            and deck.count('\nquit\n')==1, 'Unexpected sealed control block')
    tokens = ' '.join(f'v(xdut.{name})' for name in extra)
    deck = deck.replace('.control\n','.control\necho __R87_DECK_READY__\n')
    deck = deck.replace('tran 10p 250n 0 25p\n',
                        'echo __R87_TRAN_DISPATCH__\ntran 10p 250n 0 25p\necho __R87_TRAN_RETURN__\n')
    deck, saves = re.subn(r'(?m)^\.save [^\n]+$', lambda m: f'{m[0]} {tokens} {CURRENT}',deck)
    deck, dumps = re.subn(r'(?m)^wrdata waveform\.dat [^\n]+$', lambda m: f'{m[0]} {tokens}',deck)
    require(saves==dumps==1,'Unexpected sealed waveform commands')
    return deck.replace('\nquit\n',f'\nwrdata r87_current.dat {CURRENT}\nquit\n')


def authorize(output):
    old = checked(ORIGINAL)
    parent = checked_preparation(PARENT)
    ref,sim,trace = load(REFERENCE,True)
    require(ref['candidate']==parent['candidate']==old['candidate'] and
            ref['pex_sha256']==parent['pex_sha256']==old['pex_sha256'] and
            sim['waveform_sha256']==old['reference_waveform_sha256'], 'Provenance mismatch')
    model_file = ORIGINAL/'model_hashes.json'
    models = json.loads(model_file.read_text())
    require(model_closure(PDK)==models, 'Model closure has drifted')
    gate_file = pinned(ORIGINAL/'startup_gate.json',HISTORICAL_GATE_SHA)
    require(json.loads(gate_file.read_text())['status']=='BLOCKED', 'Unexpected historical gate')
    comparison_file = pinned(STARTUP/'comparison.json',COMPARISON_SHA)
    comparison = json.loads(comparison_file.read_text())
    pinned(STARTUP/'preflight.json',comparison['preflight_sha256'])
    diagnostic = comparison['results']['C_original_pwl']
    case = STARTUP/'C_original_pwl'
    require(diagnostic==json.loads((case/'result.json').read_text()) and diagnostic['status']=='TIMEOUT'
            and diagnostic['events']['deck_ready'] and diagnostic['events']['initial_solution_reported']
            and diagnostic['events']['first_positive_reference']['ns']>0 and diagnostic['max_reference_ns']>=10,
            'Missing 14 ns benchmark evidence of numerical progress')
    for name,h in diagnostic['artifacts'].items():
        pinned(case/name,h)

    mapping = json.loads((ORIGINAL/'probes.json').read_text())
    binding = (ORIGINAL/'binding.spice').read_text()
    source = (ORIGINAL/'norton_fixture.spice').read_bytes()
    proof = branch(binding,mapping)
    special = SOURCE.search(source)
    require(special is not None and SOURCE.sub(b'',source)==binding.encode()
            and source==(case/'circuit.spice').read_bytes() and json.loads(json.dumps(proof))==old['branch']
            and tuple(special.groups()[:2])==tuple(proof[k].encode() for k in ('upstream','local')),
            'Instrumented R87 branch differs from the verified topology')
    points = source_points(special)
    require(old['delay_ps']==DELAY_PS==FIDELITY['displacement_ps'] and old['windows_ns']==[list(w) for w in WINDOWS]
            and old['edge_fidelity_tolerance_ps']==FIDELITY['each_rise_ps']
            and len(points)==3203 and points[1][0]==211 and points[-1][0]==239
            and overlay(binding,proof,current_points(trace,proof['resistance_ohm'])).encode()==source,
            'PWL does not reconstruct from the sealed reference and 182 ps displacement')
    raw = (ORIGINAL/'full.spice').read_text()
    require(raw.replace('norton_fixture.spice','binding.spice')==(REFERENCE/'bench.spice').read_text(),
            'Full deck differs from the reference beyond the intended include')
    extra = {'r87_upstream':proof['upstream'],'r87_local':proof['local']}
    require(not(set(extra.values()) & set(mapping.values())), 'Unexpected overlap of added probes')
    target = new_directory(output)
    (target/'norton_fixture.spice').write_bytes(source)
    (target/'fabric.spice').write_bytes((ORIGINAL/'fabric.spice').read_bytes())
    (target/'bench.spice').write_text(observed_deck(raw,extra.values()))
    write_json(target/'probes.json',{**mapping,**extra})
    version = subprocess.check_output(['ngspice','--version'],text=True,timeout=10)
    physical = {name:digest for name,digest in parent['inputs_sha256'].items()
                if name.endswith(('.gds','.lef','/extracted_rc.spice'))}
    write_json(target/'authorization.json',dict(status='NUMERICAL_PROGRESS_VERIFIED',
        scope='Authorization for one full contrast. Functional and electrical equivalence are untested.',
        historical_gate_status='BLOCKED', historical_gate_sha256=sha256(gate_file),
        diagnostic_receipt_sha256=sha256(comparison_file), numerical_progress_ns=diagnostic['max_reference_ns'],
        sealed_preflight_sha256=sha256(ORIGINAL/'preflight.json'),
        reference_waveform_sha256=sim['waveform_sha256'], reference_conditions=ref['conditions'],
        physical_sha256=physical, binding_sha256=sha256(ORIGINAL/'binding.spice'),
        verified_models=len(models),model_closure_sha256=sha256(model_file),branch=proof,
        waveform_fidelity=FIDELITY, windows_ns=WINDOWS, source_peak_abs_a=max(float(abs(i)) for _,i in points),
        observation_notes=dict(baseline_r87_terminals='Not recorded. Compare the archived shared SCLK probes.',
                               source_current_file='Additional, separate wrdata. The ideal PWL is the fallback.'),
        artifacts={p.name:sha256(p) for p in target.iterdir()},
        monitor_sources_sha256={p.name:sha256(p) for p in (Path(__file__),Path(__file__).with_name('diagnose_phase3_sclk_startup.py'))},
        ngspice_version=version.strip()))
    return target


def stop_reason(elapsed, events, error, budget=BUDGET):
    if error:
        return 'PROVEN_SIMULATOR_ERROR'
    if elapsed>=budget['wall_s']-budget['termination_grace_s']:
        return 'TOTAL_WALL_LIMIT'
    if 'tran_dispatch' not in events and elapsed>=budget['preparation_s']:
        return 'PREPARATION_WALL_LIMIT'
    progress = events.get('first_positive_reference')
    if progress and elapsed-progress['elapsed_s']>=budget['integration_s']:
        return 'INTEGRATION_WALL_LIMIT'
    return None


def simulate(out):
    cmd = ['stdbuf','-o0','-e0','ngspice','-n','-b','bench.spice']
    manifest = out/'authorization.json'
    for name,digest in json.loads(manifest.read_text())['artifacts'].items():
        pinned(out/name,digest)
    obs = Observations()
    samples = []
    write_json(out/'attempt.json',dict(command=cmd,budget=BUDGET,wrapper_wall=now(),
                                     authorization_sha256=sha256(manifest)))
    reason,error,stop_wall = None,None,None
    previous_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.monotonic()

    def stamp():
        return dict(wall=now(),elapsed_s=time.monotonic()-start)

    with (BUILD/'.eco_simulator.lock').open('a') as lock, selectors.DefaultSelector() as selector, \
         (out/'stdout.log').open('xb',buffering=0) as stdout, (out/'stderr.log').open('xb',buffering=0) as stderr, \
         (out/'samples.jsonl').open('x',buffering=1) as samples_out:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with subprocess.Popen(cmd,cwd=out,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'},
                              preexec_fn=ngspice_limits) as proc:
            launched = dict(stamp(),pid=proc.pid)
            print(f'Launched ngspice PID {proc.pid}',flush=True)
            selector.register(proc.stdout,selectors.EVENT_READ,('stdout',stdout))
            selector.register(proc.stderr,selectors.EVENT_READ,('stderr',stderr))
            next_sample,next_report = 0.,0.
            fatal_windows = {'stdout':b'','stderr':b''}
            while proc.poll() is None or selector.get_map():
                elapsed = time.monotonic()-start
                if reason is None and proc.poll() is None:
                    reason = stop_reason(elapsed,obs.events,error)
                    if reason:
                        stop_wall = stamp()
                        proc.terminate()
                if stop_wall and proc.poll() is None and elapsed-stop_wall['elapsed_s']>=BUDGET['termination_grace_s']:
                    proc.kill()
                for key,_ in selector.select(.20):
                    channel,log = key.data
                    chunk = os.read(key.fd,65536)
                    log.write(chunk)
                    obs.feed(channel,chunk,stamp(),eof=not chunk)
                    search = fatal_windows[channel]+chunk
                    if match := FATAL.search(search):
                        error = match[0].decode()
                    fatal_windows[channel] = search[-64:]
                    if not chunk:
                        selector.unregister(key.fileobj)
                if elapsed>=next_sample and proc.poll() is None:
                    sample = proc_sample(proc.pid,stamp(),obs.latest_ns,samples[-1] if samples else None)
                    if sample:
                        samples.append(sample)
                        samples_out.write(json.dumps(sample)+'\n')
                        next_sample = elapsed+5
                if elapsed>=next_report:
                    print(f'{elapsed:.0f} s wall, last transient marker {obs.latest_ns} ns',flush=True)
                    next_report = elapsed+30
            ended = stamp()
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    wave = out/'waveform.dat'
    end_ns = None
    if wave.is_file():
        with wave.open('rb') as stream:
            for line in stream:
                if line.strip():
                    last = line
        try:
            end_ns = float(last.split()[0])*1e9
        except (ValueError, UnboundLocalError):
            pass
    good = not (reason or error or proc.returncode) and end_ns is not None and math.isclose(end_ns,FULL_NS,abs_tol=1e-6)
    result = dict(status='COMPLETED' if good else 'INCONCLUSIVE', termination=reason or 'PROCESS_EXIT',
        stop_requested=stop_wall, simulator_error=error, exit_code=proc.returncode,
        process_launched=launched,process_ended=ended,events=obs.events,
        last_reported_transient_ns=obs.max_ns,waveform_end_ns=end_ns,
        cpu_s=usage.ru_utime+usage.ru_stime-previous_usage.ru_utime-previous_usage.ru_stime,
        peak_rss_kib=max((s['hwm_kib'] or 0 for s in samples),default=None),sample_count=len(samples),
        artifacts={p.name:sha256(p) for p in out.iterdir() if p.is_file()})
    write_json(out/'result.json',result)
    print(result['status'],result['termination'],flush=True)
    return int(not good)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    return simulate(authorize(args.output))


if __name__=='__main__':
    raise SystemExit(main())
