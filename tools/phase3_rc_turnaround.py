#!/usr/bin/env python3
"""Measure isolated SRAM output masks and a separate read/write handoff with full RC."""
import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from subprocess import run, STDOUT

from phase3_rc_characterization import PDK, PUBLIC, at, bind_rc_deck, crossing, valid_suffix_start
from phase3_rc_probe_report import read_waveform
from phase3_rc_read_path import OUTPUT_ENABLES
from run_phase3_eco_pex import finish, new_directory, ngspice_limits, pinned, probe_nodes, sha256, write_csv
from run_phase2_extracted_access import model_closure

@dataclass(frozen=True)
class Schedule:
    start_ns: tuple[float, float, float]
    mask_ns: float
    handoff_ns: float
    write_ns: float
    read_ns: float
    weak_off_ns: float

    @property
    def end_ns(self):
        return self.read_ns + 13

    @property
    def masks(self):
        return zip(('WEb', 'OEb', 'CSb'), self.start_ns, ('fall', 'rise', 'rise'))


SCHEDULES = {
    'v1': Schedule((42.5, 46., 49.5), 1.8, 52.5, 60., 80., 52.2),
    'v2': Schedule((42.5, 51., 59.5), 2.5, 68.5, 75., 95., 67.75),
}
EXTRA = ('v(OEb)', 'v(WEb)', 'v(CSb)', 'v(HOST_EN)', 'v(HOST_WEAK_EN)',
         *(f'i(vm{bit})' for bit in range(8)),
         *(f'i(vh{bit})' for bit in range(8)),
         *(f'i(vw{bit})' for bit in range(8)))


def ramp(initial, changes):
    points = [(0, initial)]
    old = initial
    for time, level in changes:
        points.extend(((time, old), (time + .05, level)))
        old = level
    return 'PWL(' + ' '.join(f'{time:.6f}n {1.8 * level:g}' for time, level in points) + ')'


def deck_text(corner, nodes, guard_ps, campaign='v2'):
    schedule = SCHEDULES[campaign]
    we, oe, cs = schedule.start_ns
    mask = schedule.mask_ns
    handoff, write, read = schedule.handoff_ns, schedule.write_ns, schedule.read_ns
    drives = {
        'CLK': (0, [(10, 1), (20, 0), (30, 1), (40, 0), (write, 1), (write+10, 0),
                    (read, 1), (read+10, 0)]),
        'WEb': (1, [(7, 0), (27, 1), (we, 0), (we+mask, 1), (handoff, 0), (read-3, 1)]),
        'OEb': (1, [(27, 0), (oe, 1), (oe+mask, 0), (handoff, 1), (read-3, 0)]),
        'CSb': (0, [(cs, 1), (cs+mask, 0)]),
        'HOST_EN': (0, [(7.4, 1), (26.5, 0), (handoff + guard_ps / 1000, 1), (read-3.5, 0)]),
        'HOST_WEAK_EN': (0, [(41.5, 1), (schedule.weak_off_ns, 0)]),
    }
    deck = ['* Independent bench with real write, separate masks, handoff and readback',
            f'.lib "{PDK}" {corner}', '.include "binding.spice"', '.temp 27',
            '.options klu method=gear reltol=1e-4 vabstol=1e-8 iabstol=1e-12',
            '.model strong sw ron=1 roff=1e12 vt=.9 vh=.1',
            '.model weak sw ron=1k roff=1e12 vt=.9 vh=.1',
            'VDD_SRC VDD 0 PWL(0 0 1n 1.8)', 'VGND VSS 0 0',
            'VA0 ADDR0 0 0', 'VA1 ADDR1 0 0']
    deck.extend(f'V_{name} {name} 0 {ramp(level, events)}' for name, (level, events) in drives.items())
    pads = []
    for bit in range(8):
        value = bit % 2
        pads.append(f'PAD{bit}')
        deck.extend([
            f'VM{bit} PAD{bit} DATA{bit} 0',
            f'CD{bit} DATA{bit} 0 10f',
            f'VS{bit} HS{bit} 0 {ramp(value, [(handoff-.2, 1-value)])}',
            f'VR{bit} HS_WEAK{bit} 0 {1.8 * (1-value):g}',
            f'SH{bit} HS{bit} MH{bit} HOST_EN 0 strong',
            f'SW{bit} HS_WEAK{bit} MW{bit} HOST_WEAK_EN 0 weak',
            f'VH{bit} MH{bit} DATA{bit} 0',
            f'VW{bit} MW{bit} DATA{bit} 0',
        ])
    deck.append('XDUT ADDR0 ADDR1 CLK CSb ' + ' '.join(pads) + ' OEb VDD VSS WEb sram_4x8_wrapper')
    saved = ' '.join((*PUBLIC, *EXTRA, *(f'v(xdut.{node})' for node in nodes)))
    deck.extend([f'.save {saved}', '.control', 'set wr_singlescale', 'set wr_vecnames',
                 f'tran 10p {schedule.end_ns:g}n 0 25p', f'wrdata waveform.dat {saved}', 'quit', '.endc', '.end'])
    return '\n'.join(deck) + '\n'


def edge(rows, column, start_ns, end_ns, level, direction):
    found = crossing(rows, column, start_ns * 1e-9, end_ns * 1e-9, level, direction)
    return found[0] if len(found) == 1 else None


def current_below(rows, column, start, end, limit):
    points = [(start, at(rows, start, column)),
              *((row[0], row[column]) for row in rows if start < row[0] < end),
              (end, at(rows, end, column))]
    if abs(points[-1][1]) > limit:
        return None
    for (t0, v0), (t1, v1) in reversed(list(zip(points, points[1:]))):
        if abs(v0) > limit:
            target = limit if v0 > 0 else -limit
            return t0 + (target-v0) * (t1-t0) / (v1-v0)
    return start


def analyze_masks(rows, columns, reports, schedule):
    read_checks = []
    for sample, pattern in ((41., 0xAA), (schedule.read_ns+11, 0x55)):
        for bit in range(8):
            value = (pattern >> bit) & 1
            start, end = (sample - .1) * 1e-9, (sample + .1) * 1e-9
            read_checks.append(dict(sample_ns=sample, bit=bit, expected=value,
                                    status='PASS' if valid_suffix_start(rows, bit+2, start, end, value) == start
                                    else 'FAIL'))
    masks, handoff = [], []
    for control, start, direction in schedule.masks:
        reference = edge(rows, columns[f'v({control})'], start, start+.1, .9, direction)
        mask_end = start+schedule.mask_ns
        live = edge(rows, reports['_34_.Y'], start, mask_end, .9, 'fall')
        for bit, enable in enumerate(OUTPUT_ENABLES):
            weak = columns[f'i(vw{bit})']
            end = (mask_end-.15)*1e-9
            te = edge(rows, reports[enable], start, mask_end, 1.44, 'rise')
            start_s = start*1e-9
            switched = valid_suffix_start(rows, bit+2, start_s, end, 1-bit%2)
            weak_before = abs(at(rows, (start-.15)*1e-9, weak))
            off = current_below(rows, weak, start_s, end, 50e-6)
            active_before = at(rows, (start-.15)*1e-9, reports[enable]) <= .36 and weak_before > 50e-6
            weak_tail = [abs(row[weak]) for row in rows if end-.2e-9 <= row[0] <= end]
            restore_at = min(start+7.8, schedule.weak_off_ns-.35) if schedule.mask_ns > 2 else start+2.4
            restore_start, restore_end = restore_at*1e-9, (restore_at+.2)*1e-9
            turn_on = edge(rows, reports[enable], mask_end, restore_at+.2, .36, 'fall')
            restored_gate = valid_suffix_start(rows, reports[enable], restore_start, restore_end, 0)
            # The 1 kΩ opposite driver deliberately disturbs DATA. Observe the
            # resumed source/sink current here, and logic in the unloaded reads.
            restored_current = [abs(row[weak]) for row in rows
                                if restore_start <= row[0] <= restore_end]
            restored = (restored_gate == restore_start and restored_current and min(restored_current) > 50e-6)
            masks.append(dict(control=control, bit=bit,
                              live_read50_ps=(live-reference)*1e12 if live and reference else None,
                              te_b80_ps=(te-reference)*1e12 if te and reference else None,
                              weak_pull_valid_ps=(switched-reference)*1e12
                              if switched and reference and switched > start_s else None,
                              weak_current_release_ps=(off-reference)*1e12
                              if off and reference and active_before else None,
                              reenable_gate_ps=(turn_on-(mask_end+.025)*1e-9)*1e12 if turn_on else None,
                              active_before=active_before,
                              weak_before_ua=weak_before*1e6,
                              weak_tail_max_ua=max(weak_tail)*1e6 if weak_tail else None,
                              restored=bool(restored),
                              restored_weak_min_ua=min(restored_current)*1e6 if restored_current else None,
                              status='PASS' if (reference and live and te and switched and active_before
                                                and weak_tail and max(weak_tail) <= 50e-6
                                                and restored) else 'FAIL'))
    hand = schedule.handoff_ns
    hand_end = schedule.write_ns-1
    host = edge(rows, columns['v(HOST_EN)'], hand, hand_end, 1., 'rise')
    first_host_on = edge(rows, columns['v(HOST_EN)'], 7.4, 7.5, 1., 'rise')
    first_host_off = edge(rows, columns['v(HOST_EN)'], 26.5, 26.6, .8, 'fall')
    host_off = edge(rows, columns['v(HOST_EN)'], schedule.read_ns-3.5, schedule.read_ns-3.4, .8, 'fall')
    for bit, enable in enumerate(OUTPUT_ENABLES):
        active_before = at(rows, (hand-.15)*1e-9, reports[enable]) <= .36
        disabled = edge(rows, reports[enable], hand, hand_end, 1.44, 'rise')
        first = host if host is not None else hand_end*1e-9
        last = max(first, disabled) if disabled is not None else first
        dut_col = columns[f'i(vm{bit})']
        host_col = columns[f'i(vh{bit})']
        active = [(row[host_col], row[dut_col]) for row in rows if first < row[0] < last]
        if first < last:
            active.extend((at(rows, t, host_col), at(rows, t, dut_col)) for t in (first, last))
        margin = (host-disabled)*1e12 if host and disabled and active_before else None
        initial_isolated = (first_host_on and first_host_off and valid_suffix_start(
            rows, reports[enable], first_host_on, first_host_off, 1) == first_host_on)
        te_column = reports[enable]
        held_isolated = (disabled and host_off and disabled < host_off
                         and all(row[te_column] >= 1.44 for row in rows if disabled < row[0] < host_off)
                         and at(rows, host_off, te_column) >= 1.44)
        next_enable = edge(rows, reports[enable], schedule.read_ns-3, schedule.read_ns+5, 1.44, 'fall')
        return_margin = (next_enable-host_off)*1e12 if next_enable and host_off else None
        steady = [abs(row[host_col]) for row in rows if first+.25e-9 <= row[0] <= (schedule.write_ns+9)*1e-9]
        opposed = [min(abs(master), abs(dut)) for master, dut in active if master*dut < 0]
        early_end = first+.25e-9
        early = [(row[0], row[host_col], row[dut_col]) for row in rows if first < row[0] < early_end]
        early.insert(0, (first, at(rows, first, host_col), at(rows, first, dut_col)))
        early.append((early_end, at(rows, early_end, host_col), at(rows, early_end, dut_col)))
        early_opposed = [(time, min(abs(master), abs(dut)) if master*dut < 0 else 0.)
                         for time, master, dut in early]
        early_charge = sum((b-a)*(lo+hi)*.5 for (a,lo),(b,hi) in zip(early_opposed, early_opposed[1:]))
        sustained = {}
        for delay in (100, 200):
            instant = first+delay*1e-12
            master, dut = at(rows, instant, host_col), at(rows, instant, dut_col)
            sustained[f'opposed_at_{delay}ps_ua'] = (
                min(abs(master), abs(dut))*1e6 if master*dut < 0 else 0.) if host else None
        handoff.append(dict(bit=bit, host_on_ns=host*1e9 if host else None,
                            te_b80_ns=disabled*1e9 if disabled else None, guard_margin_ps=margin,
                            active_before=active_before,
                            initial_write_isolated=bool(initial_isolated),
                            held_isolated=bool(held_isolated),
                            write_to_read_margin_ps=return_margin,
                            overlap_proxy_ps=max(0., -margin) if margin is not None else None,
                            host_peak_ua=max(abs(master) for master, _ in active)*1e6 if active else None,
                            dut_pin_peak_ua=max(abs(dut) for _, dut in active)*1e6 if active else None,
                            opposed_peak_ua=max(opposed)*1e6 if opposed else None,
                            first_250ps_opposed_fc=early_charge*1e15 if host else None,
                            **sustained,
                            host_steady_peak_ua=max(steady)*1e6 if steady else None,
                            status='NOT_CHARACTERIZED' if margin is None else
                            'PASS' if (margin > 0 and steady and max(steady) <= 50e-6
                                       and initial_isolated and held_isolated and return_margin is not None
                                       and return_margin > 0) else 'FAIL'))
    return masks, handoff, read_checks


def write_observations(output, receipt, rows, columns, probes):
    reports = {label: columns[node] for label, node in probes.items()}
    names = ('masks', 'handoff', 'reads')
    for name, checks in zip(names, analyze_masks(rows, columns, reports, SCHEDULES[receipt['campaign']])):
        write_csv(output/f'{name}.csv', checks, list(checks[0]))
        receipt[name] = dict(total=len(checks), failed=sum(row['status']=='FAIL' for row in checks),
                             unmeasured=sum(row['status']=='NOT_CHARACTERIZED' for row in checks))
    receipt['status'] = 'FAIL' if any(receipt[k]['failed'] for k in names) else 'NOT_CHARACTERIZED'


def replay_observations(source, output):
    manifest_path = source/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('simulator_status') != 'PASS':
        raise ValueError('A completed turnaround transient is required')
    campaign = manifest.get('campaign', 'v1')
    probe_file, waveform = (pinned(source / name, manifest['artifacts'][name])
                            for name in ('probes.json', 'waveform.dat'))
    probes = json.loads(probe_file.read_text())
    rows, columns = read_waveform(waveform, sorted(set(probes.values())), EXTRA,
                                  minimum_end=SCHEDULES[campaign].end_ns*1e-9 - 1e-15)
    if len(rows) != manifest['samples']:
        raise ValueError('Unexpected sample count in turnaround waveform')
    output = new_directory(output)
    receipt = dict(schema_version=1, status='ERROR', source_status=manifest['status'],
                   source_manifest_sha256=sha256(manifest_path), waveform_sha256=sha256(waveform),
                   analyzer_sha256=sha256(Path(__file__)),
                   electrical_qualification='NOT_CHARACTERIZED', corner=manifest['corner'],
                   host_guard_ps=manifest['host_guard_ps'], campaign=campaign)
    try:
        write_observations(output, receipt, rows, columns, probes)
    finally:
        finish(output, receipt)
    return 1


def simulate(source, output, corner, guard_ps, timeout, campaign='v2'):
    receipt = dict(schema_version=1, status='ERROR', corner=corner, host_guard_ps=guard_ps,
                   scope='Diagnostic guard and independent masks. Benchmark and interface unchanged.',
                   electrical_qualification='NOT_CHARACTERIZED', campaign=campaign,
                   analyzer_sha256=sha256(Path(__file__)))
    output = new_directory(output)
    try:
        manifest = json.loads((source/'manifest.json').read_text())
        if manifest['status'] != 'PASS_RC_STRUCTURE' or manifest['profile'] != 'all':
            raise ValueError('An audited integral RC extraction is required')
        pinned(Path(manifest['gds_path']), manifest['gds_sha256'])
        names = ('extracted_rc.spice', 'phase3_rc_flat.ext', 'phase3_rc_flat.res.ext')
        net, ext, resist = (pinned(source/name, manifest['artifacts'][name]) for name in names)
        receipt.update(netlist_sha256=sha256(net), gds_sha256=manifest['gds_sha256'],
                       extraction_manifest_sha256=sha256(source/'manifest.json'))
        text = net.read_text()
        mapping, _ = probe_nodes(text, ext, resist, extra_labels=('_34_.Y',))
        needed = {*OUTPUT_ENABLES, '_34_.Y'}
        probes = {key: mapping[key] for key in sorted(needed)}
        nodes = sorted(set(probes.values()))
        (output/'probes.json').write_text(json.dumps(probes, indent=2)+'\n')
        (output/'binding.spice').write_text(bind_rc_deck(text)[0])
        (output/'bench.spice').write_text(deck_text(corner, nodes, guard_ps, campaign))
        models = model_closure(PDK)
        (output/'model_hashes.json').write_text(json.dumps(models, indent=2)+'\n')
        command = ['ngspice', '-n', '-b', 'bench.spice']
        receipt['command'] = command
        with (output/'ngspice.log').open('x') as log:
            run(command, cwd=output, stdout=log, stderr=STDOUT, check=True, timeout=timeout,
                preexec_fn=ngspice_limits,
                env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'})
        log_text = (output/'ngspice.log').read_text(errors='replace')
        if (not re.search(r'^ngspice-\S+ done\s*$', log_text, re.M)
                or re.search(r'analysis aborted|simulation interrupted|^\s*(?:Fatal|Error):', log_text, re.I | re.M)):
            raise ValueError('ngspice log does not demonstrate completed transient')
        rows, columns = read_waveform(output/'waveform.dat', nodes, EXTRA,
                                      minimum_end=SCHEDULES[campaign].end_ns*1e-9 - 1e-15)
        if model_closure(PDK) != models:
            raise ValueError('PDK model closure changed')
        pinned(net, receipt['netlist_sha256'])
        receipt.update(simulator_status='PASS', samples=len(rows))
        write_observations(output, receipt, rows, columns, probes)
    except Exception as error:
        receipt['error'] = str(error)
    finally:
        finish(output, receipt)
    return 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--replay', type=Path, help='Reanalyze a sealed diagnostic transient in a fresh directory')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--corner', choices=('tt', 'ss', 'ff'), default='ss')
    parser.add_argument('--host-guard-ps', type=int, choices=(300, 1500))
    parser.add_argument('--campaign', choices=SCHEDULES, default='v2')
    parser.add_argument('--timeout', type=int, default=1800)
    args = parser.parse_args()
    if args.replay:
        if args.host_guard_ps is not None:
            parser.error('Replay uses the source guard')
        raise SystemExit(replay_observations(args.replay, args.output))
    if args.host_guard_ps is None:
        parser.error('--host-guard-ps is required for a new simulation')
    raise SystemExit(simulate(args.source, args.output, args.corner, args.host_guard_ps, args.timeout,
                              args.campaign))
