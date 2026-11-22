#!/usr/bin/env python3
"""Prepare, run once, and inspect the legal-handoff SS benchmark for the spaced 4x8."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import time

from measure_phase3_access_disable import (
    BUILD, CONDITIONS, candidate, edge, measure_word, require, survives,
)
from phase3_rc_characterization import PDK, PUBLIC, QUAL, at, bind_rc_deck, crossing, prepare_deck, valid_suffix_start
from phase3_rc_extraction import ROOT, sha256
from phase3_rc_probe_report import read_waveform
from phase3_rc_read_path import HIGH, LOW, LOCAL_CLOCKS, OUTPUT_ENABLES, WORDLINES, correct
from phase3_rc_turnaround import current_below, ramp
from run_phase2_extracted_access import model_closure
from run_phase3_eco_pex import FIXTURE_RECEIPT, PROTOCOL_VECTORS, new_directory, ngspice_limits, pinned, probe_nodes, protocol_checks, write_csv


PEX = BUILD / 'danilo_ss_ff2_spaced_pex_sealed'
PEX_SHA = '12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a'
HISTORICAL_STRESS = BUILD / 'turnaround_ref_ss_v2_300/manifest.json'
GUARD_NS, STOP_NS, LIMIT_A = 1.5, 370, 50e-6
MODE = ('_83_.Q', '_84_.Q')
ADDR = ('_85_.Q', '_86_.Q')
EXTRA = (*PROTOCOL_VECTORS, 'v(HOST_WEAK_EN)', 'v(CSb)', 'v(OEb)', 'v(WEb)',
         *(f'i(v_sense_weak{i})' for i in range(8)), *(f'i(v_dut{i})' for i in range(8)))


def ns(t):
    return t * 1e-9


def plan_cycles(records):
    require(len(records) == 18 and [r['cycle'] for r in records] == list(range(18)), 'Expected 18 ordered cycles')
    require(all(r['rise_ns'] == 10+20*i and r['fall_ns'] == 20+20*i for i,r in enumerate(records)),
            'Unexpected public clock schedule')
    known, readback = {}, set()
    strong, weak = [], [(3.5, 46., 0xAA)]
    planned = []
    for index, original in enumerate(records):
        rec = dict(original)
        op, row = rec['operation'], rec['row']
        previous = records[index-1]['operation'] if index else 'idle'
        following = records[index+1]['operation'] if index+1 < len(records) else 'end'
        before_clock = rec['rise_ns'] - 3
        rec['previous_operation'], rec['following_operation'] = previous, following
        rec['control_start_ns'] = before_clock
        if op == 'write':
            known[row] = rec['expected']
            if previous != 'write':
                if previous == 'read':
                    rec['host_enable_ns'] = before_clock + GUARD_NS
                    rec['handoff_guard_ns'] = GUARD_NS
                strong.append((rec['host_enable_ns'], 1))
            if following != 'write':
                rec['host_off_ns'] = rec['rise_ns'] + 16.5
                strong.append((rec['host_off_ns'], 0))
        elif op == 'read':
            require(known.get(row) == rec['expected'], 'Read expectation disagrees with preceding writes')
            readback.add(row)
            cal = rec['calibration']
            weak_end = cal['weak_off_ns']
            if following == 'write':
                # Stop the weak probe before the strong driver. It remains
                # opposite to the previous read throughout the release test.
                weak_end = rec['rise_ns'] + 17 + GUARD_NS - .10
            elif following == 'idle':
                require(index+2 < len(records) and records[index+2]['operation'] == 'read',
                        'Idle following read must have a return-to-read event')
                weak_end = records[index+2]['rise_ns'] - 3.5
            rec['weak_off_ns'] = weak_end
            weak.append((cal['weak_on_ns'], weak_end, 255 ^ rec['expected']))
        else:
            require(op == 'idle', 'Unexpected operation in qualification fixture')
        planned.append(rec)
    require(readback == set(known) == {0,1,2,3}, 'Incomplete address coverage')
    require([sum(r['operation'] == op for r in planned) for op in ('read','write','idle')] == [9,6,3],
            'Unexpected read, write or idle counts')
    weak_edges = [(instant, value) for start, end, _ in weak for instant,value in ((start,1),(end,0))]
    for events in (strong, weak_edges):
        require(all(b[0]-a[0] > .05 for a,b in zip(events,events[1:])), 'Overlapping PWL ramps')
    high_spans = [(a[0],b[0]+.05) for a,b in zip(strong[::2],strong[1::2])]
    require(all(end+.05 < first or start > last for start,end,_ in weak for first,last in high_spans),
            'Weak probe conflicts with strong host drive')
    return planned, strong, weak


def deck_text(template, nodes, strong, weak):
    base = prepare_deck(template, 'ss', 10)
    lines = []
    vectors = ' '.join((*PUBLIC, *EXTRA, *(f'v(xdut.{node})' for node in nodes)))
    for original in base.splitlines():
        words = original.split()
        if original.startswith('V_HOST_EN '):
            original = f'V_HOST_EN HOST_EN 0 {ramp(0, strong)}'
        elif original.startswith('V_HOST_WEAK_EN '):
            events = [(instant, value) for start,end,_ in weak for instant,value in ((start,1),(end,0))]
            original = f'V_HOST_WEAK_EN HOST_WEAK_EN 0 {ramp(0, events)}'
        elif re.fullmatch(r'S_WEAK[0-7]', words[0] if words else ''):
            bit = int(words[0][-1])
            vals = [(start-.25, (value>>bit)&1) for start,_,value in weak]
            lines.append(f'V_WPAY{bit} WEAK{bit} 0 {ramp(0, vals)}')
            words[2] = f'WEAK{bit}'
            original = ' '.join(words)
        elif original.startswith('XDUT '):
            for bit in range(8):
                lines.append(f'V_DUT{bit} DUT_DATA{bit} DATA{bit} 0')
            original = re.sub(r'\bDATA([0-7])\b', r'DUT_DATA\1', original)
        elif original.startswith('.save '):
            original = '.save ' + vectors
        elif original.startswith('wrdata waveform.dat '):
            original = 'wrdata waveform.dat ' + vectors
        elif original == 'tran 10p 370n 0 10p':
            original = 'tran 10p 370n 0 25p'
        lines.append(original)
    text = '\n'.join(lines) + '\n'
    require(text.count('tran 10p 370n 0 25p') == 1 and text.count('\nV_DUT') == 8
            and text.count('\nV_WPAY') == 8 and text.count('\nXDUT ') == 1, 'Incomplete integrated deck')
    return text


def prepare(output):
    provenance = {}
    design = candidate(provenance)
    pex_receipt = PEX/'manifest.json'
    extraction = json.loads(pex_receipt.read_text())
    require(extraction['status'] == 'PASS_RC_STRUCTURE' and extraction['profile'] == 'all'
            and extraction.get('rc_mindelay_ps') is None and extraction['capacitance_audit']['different'] == 0
            and extraction['gds_sha256'] == design['gds_sha256']
            and extraction['geometry_receipt_sha256'] == design['physical_receipt_sha256']
            and extraction['artifacts']['extracted_rc.spice'] == PEX_SHA, 'Wrong distributed PEX')
    net, ext, resist = (pinned(PEX/name, extraction['artifacts'][name]) for name in
                        ('extracted_rc.spice', 'phase3_rc_flat.ext', 'phase3_rc_flat.res.ext'))
    fixture = pinned(QUAL/'results.json', FIXTURE_RECEIPT)
    info = json.loads(fixture.read_text())
    bench = pinned(QUAL/'bench.spice', info['artifacts']['bench.spice'])
    records, strong, weak = plan_cycles(info['cycles'])
    extracted = net.read_text()
    aliases, missing = probe_nodes(extracted, ext, resist, extra_labels=(*MODE,*ADDR))
    require(not missing, f'Unresolved electrical probes: {missing}')
    nodes = sorted(set(aliases.values()))
    binding = bind_rc_deck(extracted)[0]
    earlier = BUILD/'danilo_ss_ff2_spaced_ss_rc_probed'
    short = json.loads((earlier/'manifest.json').read_text())
    compared = pinned(earlier/'binding.spice', short['artifacts']['binding.spice'])
    require(short['netlist_sha256'] == PEX_SHA and binding == compared.read_text(), 'Binding differs from prior measured candidate')
    versions = subprocess.run(['ngspice','--version'], capture_output=True, text=True, timeout=10, check=True).stdout
    models = model_closure(PDK)
    expected = pinned(earlier/'model_hashes.json', short['artifacts']['model_hashes.json'])
    require(models == json.loads(expected.read_text()), 'PDK model closure differs from the SS reference')
    for path in (net, ext, resist, pex_receipt, fixture, bench, HISTORICAL_STRESS, compared, expected,
                 Path(__file__).resolve()):
        provenance[str(path.relative_to(ROOT))] = sha256(path)
    inputs = dict(cycles=records, strong_edges_ns=strong, weak_intervals_ns=weak)
    deck = deck_text(bench.read_text(), nodes, strong, weak)
    output = new_directory(output)
    items = {'bench.spice': deck, 'binding.spice': binding,
             'fabric.spice': '* Fabric included in flat PEX\n',
             'probes.json': json.dumps(aliases, indent=2),
             'fixture.json': json.dumps(inputs, indent=2),
             'model_hashes.json': json.dumps(models, indent=2)}
    for name, content in items.items():
        (output/name).write_text(content)
    receipt = dict(schema_version=1, candidate=design, pex_sha256=PEX_SHA, electrical_qualification='NOT_CHARACTERIZED',
                   conditions={**CONDITIONS, 'period_ns':20, 'clock_high_ns':10, 'stop_ns':370},
                   guard_ns=GUARD_NS, current_limit_a=LIMIT_A, ngspice_version=versions.strip(),
                   inputs_sha256=provenance, artifacts={name:sha256(output/name) for name in items},
                   coverage=dict(cycles=18, known_reads=9, writes=6, idle=3, addresses=[0,1,2,3]),
                   fixture_status='VERIFIED_OFFLINE', simulator_status='NOT_RUN')
    (output/'preparation.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(f'Prepared and verified {output}', flush=True)


def checked_preparation(output):
    path = output/'preparation.json'
    receipt = json.loads(path.read_text())
    require(receipt['pex_sha256'] == PEX_SHA and receipt['guard_ns'] == GUARD_NS
            and receipt['conditions']['stop_ns'] == STOP_NS, 'Unexpected run preparation')
    for name,digest in receipt['artifacts'].items():
        pinned(output/name, digest)
    for name,digest in receipt['inputs_sha256'].items():
        pinned(ROOT/name, digest)
    return receipt


def simulate(output, wall_timeout):
    receipt = checked_preparation(output)
    require(model_closure(PDK) == json.loads((output/'model_hashes.json').read_text()), 'PDK changed after preflight')
    command = ['ngspice','-n','-b','bench.spice']
    begin = time.monotonic()
    with (output/'attempt.json').open('x') as lock_receipt:
        json.dump(dict(command=command, timeout_s=wall_timeout, preparation_sha256=sha256(output/'preparation.json')),lock_receipt)
    result = dict(simulator_status='ERROR', functional_status='INCONCLUSIVO', electrical_qualification='NOT_CHARACTERIZED',
                  command=command, timeout_s=wall_timeout, preparation_sha256=sha256(output/'preparation.json'))
    log = output/'ngspice.log'
    try:
        with (BUILD/'.eco_simulator.lock').open('a') as lock, log.open('x') as stream:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            process = subprocess.run(command, cwd=output, stdout=stream, stderr=subprocess.STDOUT,
                                     env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'},
                                     preexec_fn=ngspice_limits, timeout=wall_timeout, check=False)
        result['simulator_returncode'] = process.returncode
        require(process.returncode == 0, 'ngspice returned an error')
        log_text = log.read_text(errors='replace')
        require(re.search(r'^ngspice-\S+ done\s*$',log_text,re.M)
                and not re.search(r'analysis aborted|simulation interrupted|^\s*(?:Fatal|Error):',log_text,re.I|re.M),
                'Incomplete ngspice transient')
        require((output/'waveform.dat').is_file(), 'Missing saved transient')
        checked_preparation(output)
        require(model_closure(PDK) == json.loads((output/'model_hashes.json').read_text()), 'PDK changed during run')
        result['waveform_sha256'] = sha256(output/'waveform.dat')
        result['simulator_status'] = 'PASS'
    except subprocess.TimeoutExpired:
        result.update(simulator_status='TIMEOUT', error='ngspice wall-time limit reached')
    except (OSError, ValueError) as error:
        result['error'] = str(error)
    finally:
        if log.exists():
            ticks = re.findall(rb'Reference value\s*:\s*(\S+)',log.read_bytes())
            result.update(log_sha256=sha256(log), last_progress_s=float(ticks[-1]) if ticks else None)
        result['elapsed_s'] = time.monotonic()-begin
        (output/'simulation.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)
    return int(result['simulator_status'] != 'PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare','simulate'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=2650)
    args = parser.parse_args()
    require(0 < args.timeout <= 2700, 'Use a timeout of at most 2700 seconds')
    if args.action == 'prepare':
        prepare(args.output)
        return 0
    return simulate(args.output.resolve(), args.timeout)


if __name__ == '__main__':
    raise SystemExit(main())
