#!/usr/bin/env python3
"""Extract or simulate one independently reconstructed 4x8 ECO revision."""
import argparse
import csv
import fcntl
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import resource
import os

from phase3_rc_characterization import (
    PUBLIC, PDK, QUAL, COLUMNS, analyze, at, crossing, prepare_deck, bind_rc_deck, valid_suffix_start,
)
from phase3_rc_extraction import ROOT, inspect_dc_supply_paths, inspect_netlist, logical_cards, magic_script, sha256
from phase3_rc_probe import rc_node_map
from phase3_rc_probe_report import read_waveform
from phase3_rc_read_path import ARRAY, LOCAL_CLOCKS, OUTPUT_ENABLES, WORDLINES, trace_read_path
from phase3_rc_cap_audit import compare

PROTOCOL_VECTORS = ('v(HOST_EN)', *(f'i(v_sense_host{bit})' for bit in range(8)))
FIXTURE_RECEIPT = 'a559e9d90c3393b614c937b1e515717be8fc4fe624fc445fb21e05c8b76ec708'


def new_directory(path):
    path = path.resolve()
    if not path.is_relative_to(ROOT / 'build/phase3') or path == ROOT / 'build/phase3':
        raise ValueError('Use a fresh directory below build/phase3')
    path.mkdir(parents=True)
    return path


def finish(output, receipt):
    receipt['artifacts'] = {file.name: sha256(file) for file in sorted(output.iterdir())
                            if file.is_file() and file.name != 'manifest.json'}
    (output / 'manifest.json').write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
    print(json.dumps({key: receipt[key] for key in ('status', 'error', 'read_bits_checked',
                      'read_bits_failed', 'diagnostic_error') if key in receipt}), flush=True)


def pinned(path, expected):
    if sha256(path) != expected:
        raise ValueError(f'Input hash differs: {path}')
    return path


def extract(geometry, output, magic, capacitive_only=False, forced_rc_ports=(), rc_mindelay_ps=None):
    output = new_directory(output)
    source = json.loads((geometry / 'results.json').read_text())
    if source['status'] != 'PASS_GEOMETRY_LVS':
        raise ValueError('Extract only a geometry independently matched by DRC/LVS')
    gds = pinned(geometry / 'sram_4x8.gds', source['artifacts']['sram_4x8.gds'])
    netlist = output / 'extracted_rc.spice'
    if capacitive_only:
        ext = pinned(geometry / 'final_flat.ext', source['artifacts']['final_flat.ext'])
        # Export the independently reimported GDS capacitance view. The top name
        # follows the .ext basename, so the SPICE binder sees the same ports.
        (output / 'phase3_rc_flat.ext').write_bytes(ext.read_bytes())
        tcl = (
            'ext2spice default\next2spice hierarchy off\next2spice format ngspice\n'
            'ext2spice subcircuits top on\next2spice cthresh 0\next2spice rthresh 0\n'
            f'ext2spice extresist off\next2spice -o "{netlist}" phase3_rc_flat\n'
            'puts "PHASE3_EXTRACTION_COMPLETE=1"\nquit -noprompt\n'
        )
    else:
        tcl = magic_script(gds.resolve(), netlist)
        options = ''
        if rc_mindelay_ps is not None:
            options += f'extresist mindelay {rc_mindelay_ps:g}\n'
        if forced_rc_ports:
            options += ''.join('extresist force {' + port + '}\n' for port in forced_rc_ports)
        if options:
            tcl = tcl.replace('extract do resistance\n', options + 'extract do resistance\n')
        tcl = tcl.replace('puts "PHASE3_EXTRACTION_COMPLETE=1"',
                          f'ext2spice extresist off\next2spice -o "{output / "c_only.spice"}"\n'
                          'puts "PHASE3_EXTRACTION_COMPLETE=1"')
    (output / 'extract.tcl').write_text(tcl)
    rc = Path('/opt/pdks/sky130A/libs.tech/magic/sky130A.magicrc')
    command = [magic, '-dnull', '-noconsole', '-rcfile', str(rc), 'extract.tcl']
    profile = 'c_only' if capacitive_only else 'all'
    receipt = dict(schema_version=1, status='ERROR', profile=profile, command=command,
                   extraction='capacitance-only' if capacitive_only else 'distributed RC',
                   gds_path=str(gds), gds_sha256=sha256(gds),
                   geometry_receipt_sha256=sha256(geometry / 'results.json'), rcfile_sha256=sha256(rc),
                   mos=source['mos'], electrical_qualification='NOT_CHARACTERIZED')
    if forced_rc_ports:
        receipt['forced_rc_ports'] = list(forced_rc_ports)
    if rc_mindelay_ps is not None:
        receipt['rc_mindelay_ps'] = rc_mindelay_ps
    try:
        with (output / 'magic.log').open('x') as log:
            subprocess.run(command, cwd=output, stdout=log, stderr=subprocess.STDOUT,
                           check=True, timeout=3600)
        if 'PHASE3_EXTRACTION_COMPLETE=1' not in (output / 'magic.log').read_text():
            raise ValueError('Magic did not confirm complete extraction')
        pinned(gds, receipt['gds_sha256'])
        if capacitive_only:
            kinds = [card[0].upper() for card in logical_cards(netlist.read_text())
                     if not card.startswith('.')]
            if kinds.count('X') != receipt['mos'] or not kinds.count('C') or 'R' in kinds:
                raise ValueError('Unexpected devices in capacitance-only view')
            receipt['extraction_stats'] = dict(mos=kinds.count('X'), capacitors=kinds.count('C'), resistors=0)
        else:
            receipt['extraction_stats'] = inspect_netlist(netlist, expected_mos=receipt['mos'])
            if forced_rc_ports:
                extracted = netlist.read_text()
                coverage = {port: has_resistive_port(extracted, port) for port in forced_rc_ports}
                receipt['forced_port_coverage'] = coverage
                if not all(coverage.values()):
                    raise ValueError('Forced port resistance is absent in the extracted netlist')
        rails = inspect_dc_supply_paths(netlist.read_text())
        if rails['rails_short_through_resistors'] or any(not rails[rail]['mos_terminals_reachable']
                                                         for rail in ('VDD', 'VSS')):
            raise ValueError('Unusable extracted rail connectivity')
        receipt.update(status='PASS_C_ONLY_STRUCTURE' if capacitive_only else 'PASS_RC_STRUCTURE',
                       power_connectivity=rails)
    except Exception as error:
        receipt['error'] = str(error)
    finally:
        finish(output, receipt)
    return int(not receipt['status'].startswith('PASS_'))


def restore_subatto(raw, source_ext, *, flat_nodes=False, selected_nodes=None):
    """Recover substrate capacitance lost to zero printing from the pinned Magic node table."""
    if 'scale 1000 1 500000' not in source_ext.splitlines()[:5]:
        raise ValueError('Unknown Magic node capacitance scale')
    node_pattern = r'(?m)^node "([^"]+)" \S+ (\S+)' if flat_nodes else r'(?m)^rnode "([^"]+)" 0 (\S+)'
    nodes = {}
    for name, literal in re.findall(node_pattern, source_ext):
        value = float(literal)
        if name in nodes and nodes[name] != value:
            raise ValueError('Conflicting node capacitance: ' + name)
        nodes[name] = value
    repairs = []

    def replace(match):
        card, node, prefix = match['card'], match['node'], match['prefix']
        value = nodes.get(node, 0.)
        if not 0 < value < 1 or (selected_nodes is not None and node not in selected_nodes):
            return match[0]
        repairs.append(dict(card=card, node=node, capacitance_attofarads=value))
        return f'{prefix}{value * 1e-18:.12g}'

    repaired = re.sub(r'(?m)^(?P<prefix>(?P<card>C\d+) (?P<node>\S+) VSS )0(?=\s|$)',
                      replace, raw)
    return repaired, repairs


def restore(source, output):
    """Seal a repaired copy only if the per-pair conservation audit passes."""
    output = new_directory(output)
    receipt = json.loads((source / 'manifest.json').read_text())
    if receipt['status'] != 'PASS_RC_STRUCTURE' or receipt['profile'] != 'all':
        raise ValueError('Expected audited raw RC')
    sources = {}
    for name in ('extracted_rc.spice', 'phase3_rc_flat.res.ext', 'phase3_rc_flat.ext', 'c_only.spice'):
        sources[name] = pinned(source / name, receipt['artifacts'][name])
    receipt.update(status='ERROR', original_rc_manifest_sha256=sha256(source / 'manifest.json'))
    try:
        raw = sources['extracted_rc.spice'].read_text()
        reference = sources['c_only.spice'].read_text()
        alt, repairs = restore_subatto(raw, sources['phase3_rc_flat.res.ext'].read_text())
        audited = compare(alt, reference, expected_mos=receipt['mos'])
        # With more split nodes retained, the RC export can retain substrate
        # C that Magic printed as zero in the C-only reference. Recover only
        # the zero cards involved in a discrepancy from the original .ext.
        omitted = {next(net for net in (row['net_a'], row['net_b']) if net != 'VSS')
                   for row in audited if not row['match'] and row['c_only_ff'] == 0
                   and 0 < row['rc_ff'] < .001 and 'VSS' in (row['net_a'], row['net_b'])}
        if omitted:
            reference, reference_repairs = restore_subatto(
                reference, sources['phase3_rc_flat.ext'].read_text(), flat_nodes=True, selected_nodes=omitted)
            if reference_repairs:
                audited = compare(alt, reference, expected_mos=receipt['mos'])
                (output / 'c_only_restored.spice').write_text(reference)
                (output / 'c_only_subatto_caps.json').write_text(json.dumps(reference_repairs, indent=2) + '\n')
                receipt['c_only_subatto_repaired'] = len(reference_repairs)
        receipt['capacitance_audit'] = dict(
            pairs=len(audited), different=sum(not pair['match'] for pair in audited),
            repaired=len(repairs), restored_ff=math.fsum(p['capacitance_attofarads'] for p in repairs) / 1000)
        write_csv(output / 'capacitance_audit.csv', audited, list(audited[0]))
        (output / 'subatto_caps.json').write_text(json.dumps(repairs, indent=2) + '\n')
        (output / 'extracted_rc.spice').write_text(alt)
        shutil.copyfile(sources['phase3_rc_flat.ext'], output / 'phase3_rc_flat.ext')
        shutil.copyfile(sources['phase3_rc_flat.res.ext'], output / 'phase3_rc_flat.res.ext')
        if receipt['capacitance_audit']['different']:
            raise ValueError('Restoration did not reconcile RC and C-only pair totals')
        receipt['extraction_stats'] = inspect_netlist(output / 'extracted_rc.spice', expected_mos=receipt['mos'])
        receipt['status'] = 'PASS_RC_STRUCTURE'
    except Exception as error:
        receipt['error'] = str(error)
    finally:
        finish(output, receipt)
    return int(receipt['status'] != 'PASS_RC_STRUCTURE')


def probe_nodes(extracted, ext, resistance_ext=None, extra_labels=()):
    """Resolve exact aliases and report representative split-node probes."""
    names = rc_node_map(extracted)
    aliases = {}
    coordinates = {}
    for line in ext.read_text().splitlines():
        match = re.fullmatch(r'equiv "(.*)" "(.*)"', line)
        if match:
            left, right = match.groups()
            aliases.setdefault(left, set()).add(right)
            aliases.setdefault(right, set()).add(left)
        match = re.match(r'node "([^"]+)" \S+ \S+ (-?\d+) (-?\d+)', line)
        if match:
            coordinates[match[1]] = int(match[2]), int(match[3])

    def equivalents(label):
        checked = set()
        pending = {label}
        while pending:
            candidate = pending.pop()
            checked.add(candidate)
            pending.update(aliases.get(candidate, set()) - checked)
        return checked

    split_nodes = {}
    sense_devices = {}
    if resistance_ext:
        for line in resistance_ext.read_text().splitlines():
            match = re.match(r'rnode "([^"]+)" \S+ \S+ (-?\d+) (-?\d+)', line)
            if match and match[1] in names:
                node = match[1]
                root = re.sub(r'\.[nt]\d+$', '', node)
                split_nodes.setdefault(root, []).append((node, int(match[2]), int(match[3])))
            if line.startswith('device msubckt sky130_fd_pr__pfet_01v8 '):
                _, gate, first, second = re.findall(r'"([^"]+)"', line)[:4]
                if re.fullmatch(r'macro_core\.sense_drive\.X\.t\d+', gate):
                    for terminal in (first, second):
                        match = re.fullmatch(r'(.*\.write_driver_(\d+)\.BLB?)\.t\d+', terminal)
                        if match:
                            sense_devices.setdefault(match[1], []).append((terminal, gate))

    def resolve(label):
        if label in names:
            return names[label]
        checked = equivalents(label)
        matched = checked & names.keys()
        if len(matched) == 1:
            return names[matched.pop()]
        roots = checked & coordinates.keys()
        if len(roots) == 1:
            root = roots.pop()
            x, y = coordinates[root]
            candidates = split_nodes.get(root.removesuffix('#'), [])
            if candidates:
                node, _, _ = min(candidates, key=lambda item: ((item[1]-x)**2 + (item[2]-y)**2, item[0]))
                return names[node]
        return None

    labels = ['macro_core.evaluation.X', 'macro_core.sense_drive.X',
              'macro_core.precharge_drive.X', 'macro_core.release_phase.X',
              'macro_core.write_drive.X', *WORDLINES, *LOCAL_CLOCKS, *OUTPUT_ENABLES, *extra_labels]
    for bit in range(8):
        labels.extend([f'_{43-bit}_.A1', f'_{75+bit}_.D',
                       '_75_.Q' if bit == 0 else f'_{87+bit}_.A',
                       f'_{67+bit}_.Q',
                       f'{ARRAY}.sense_amp_{bit}.SA_OUTB',
                       f'{ARRAY}.write_driver_{bit}.BL', f'{ARRAY}.write_driver_{bit}.BLB'])
    mapping = {}
    missing = []
    for label in labels:
        choices = sense_devices.get(label, [])
        node = names.get(choices[0][0]) if len(choices) == 1 else resolve(label)
        if node is None:
            missing.append(label)
        else:
            mapping[label] = node
        if len(choices) == 1 and choices[0][1] in names and label.endswith('.BL'):
            bit = re.search(r'write_driver_(\d+)', label)[1]
            mapping['SCLK_SENSE_' + bit] = names[choices[0][1]]
    return mapping, missing


def write_csv(path, rows, columns):
    with path.open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def ngspice_limits():
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3,) * 2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024**2,) * 2)


def localize_failures(rows, columns, checks, records):
    by_cycle = {cycle['cycle']: cycle for cycle in records}

    def sample(label, time):
        return at(rows, time, columns[label]) if label in columns and time is not None else None

    failures = []
    for check in checks:
        if check['status'] != 'FAIL':
            continue
        cycle = by_cycle[check['cycle']]
        bit, expected = check['bit'], check['expected']
        rise, fall, observe = (cycle[key] * 1e-9 for key in ('rise_ns', 'fall_ns', 'sample_ns'))
        clock = columns.get(LOCAL_CLOCKS[bit])
        edges = crossing(rows, clock, fall, observe, .9, 'rise') if clock is not None else []
        capture = edges[0] if len(edges) == 1 else None
        sense = columns.get('SCLK_SENSE_' + str(bit), columns.get('macro_core.sense_drive.X'))
        sense_edges = crossing(rows, sense, rise, fall, .36, 'rise') if sense is not None else []
        sclk = sense_edges[0] if len(sense_edges) == 1 else None
        wl = columns.get(WORDLINES[cycle['row']])
        wl_edges = crossing(rows, wl, rise, fall, 1.44, 'rise') if wl is not None else []
        d = sample(f'_{75+bit}_.D', capture)
        q = sample('_75_.Q' if bit == 0 else f'_{87+bit}_.A', observe)
        sa = sample(f'_{43-bit}_.A1', capture)
        enable = sample(OUTPUT_ENABLES[bit], observe)
        bl = sample(f'{ARRAY}.write_driver_{bit}.BL', sclk - 50e-12 if sclk else None)
        blb = sample(f'{ARRAY}.write_driver_{bit}.BLB', sclk - 50e-12 if sclk else None)

        def valid(voltage):
            return voltage is not None and (voltage >= 1.44 if expected else voltage <= .36)

        if capture is None:
            stage = 'CAPTURE_EDGE_UNRESOLVED'
        elif sa is not None and not valid(sa):
            stage = 'SENSE_INVALID_AT_CAPTURE'
        elif d is not None and not valid(d):
            stage = 'D_INVALID_AT_CAPTURE'
        elif q is not None and not valid(q):
            stage = 'Q_INVALID_AT_OBSERVATION'
        elif d is None or q is None:
            stage = 'INTERNAL_EVIDENCE_MISSING'
        elif enable is not None and enable > .36:
            stage = 'OUTPUT_ENABLE_INVALID'
        else:
            stage = 'DATA_INVALID_WITH_VALID_D_Q'
        failures.append(dict(cycle=check['cycle'], row=cycle['row'], bit=bit, expected=expected,
                             stage=stage, wl80_ns=wl_edges[0] * 1e9 if len(wl_edges) == 1 else None,
                             sclk20_ns=sclk * 1e9 if sclk else None,
                             signed_delta_50ps_before_sclk_v=(bl-blb) * (2*expected-1)
                                 if bl is not None and blb is not None else None,
                             capture_ns=capture * 1e9 if capture else None,
                             pclk_at_sense_v=sample('macro_core.evaluation.X', sclk),
                             prech_at_sense_v=sample('macro_core.precharge_drive.X', sclk),
                             sense_at_capture_v=sa, d_at_capture_v=d, q_at_observation_v=q,
                             enable_at_observation_v=enable,
                             data_at_window_start_v=at(rows, observe - .1e-9, bit + 2),
                             data_at_observation_v=check['observed_v'],
                             data_at_window_end_v=at(rows, observe + .1e-9, bit + 2)))
    return failures


def protocol_checks(rows, columns, records):
    """Observe captured write data and output ownership using the existing fixture."""
    import numpy as np
    from run_phase2_startup_review import levels

    we_signal = 'macro_core.write_drive.X'
    missing = {*(f'_{67+bit}_.Q' for bit in range(8)), *OUTPUT_ENABLES,
               *PROTOCOL_VECTORS, we_signal} - columns.keys()
    if missing:
        raise ValueError('Missing write/ownership probes: ' + ', '.join(sorted(missing)))
    data = np.asarray(rows)
    time = data[:, 0] * 1e9
    active = (time >= 3) & (data[:, columns['v(HOST_EN)']] > .36)
    checks = []
    for bit in range(8):
        enable = data[:, columns[OUTPUT_ENABLES[bit]]]
        overlap = active & (enable < 1.44)
        checks.append(dict(kind='no_strong_host_ebuf_overlap', cycle=None, bit=bit,
                           status='FAIL' if np.any(overlap) else 'PASS',
                           first_bad_ns=float(time[overlap][0]) if np.any(overlap) else None,
                           last_bad_ns=float(time[overlap][-1]) if np.any(overlap) else None,
                           peak_host_current_ua=float(np.max(abs(data[overlap, columns[f'i(v_sense_host{bit})']])) * 1e6)
                               if np.any(overlap) else None))
    for record in records:
        if record['operation'] != 'write':
            continue
        rise, fall = record['rise_ns'], record['fall_ns']
        stable = (time >= rise + 1) & (time <= fall - .5)
        we_edges = crossing(rows, columns[we_signal], rise * 1e-9, (fall - .5) * 1e-9, .36, 'rise')
        for bit in range(8):
            col = columns[f'_{67+bit}_.Q']
            expected = (record['expected'] >> bit) & 1
            ready = valid_suffix_start(rows, col, rise * 1e-9, (fall - .5) * 1e-9, expected)
            # Keep the inherited +1ns observation visible and separately
            # check readiness from the circuit's own WE event.
            checks.append(dict(kind='din_q_legacy_plus_1ns', cycle=record['cycle'], bit=bit,
                               scope='diagnostic', status='PASS' if levels(data[stable, col], expected) else 'FAIL'))
            safe = len(we_edges) == 1 and ready is not None and ready < we_edges[0]
            checks.append(dict(kind='write_data_ready_before_we20', cycle=record['cycle'], bit=bit,
                               status='PASS' if safe else 'FAIL',
                               din_valid_ns=ready*1e9 if ready is not None else None,
                               we20_ns=we_edges[0]*1e9 if len(we_edges) == 1 else None))
            start = max(record['host_enable_ns'], record['host_payload_ns']) + .25
            steady = (time >= start) & (time <= fall - 1)
            current = abs(data[:, columns[f'i(v_sense_host{bit})']])
            indices = np.flatnonzero(steady)
            peak = indices[np.argmax(current[indices])] if len(indices) else None
            bad = steady & (current > 50e-6)
            checks.append(dict(kind='no_steady_host_current', cycle=record['cycle'], bit=bit,
                               status='PASS' if peak is not None and not np.any(bad) else 'FAIL',
                               first_bad_ns=float(time[bad][0]) if np.any(bad) else None,
                               last_bad_ns=float(time[bad][-1]) if np.any(bad) else None,
                               peak_host_current_ua=float(current[peak] * 1e6) if peak is not None else None,
                               peak_ns=float(time[peak]) if peak is not None else None,
                               te_b_at_peak_v=float(data[peak, columns[OUTPUT_ENABLES[bit]]])
                               if peak is not None else None))
    return checks


def write_protocol_checks(output, rows, columns, records):
    checks = protocol_checks(rows, columns, records)
    fields = list(dict.fromkeys(key for check in checks for key in check))
    write_csv(output / 'write_ownership_checks.csv', checks, fields)
    measured = [check for check in checks if check.get('scope') != 'diagnostic']
    failed = sum(check['status'] == 'FAIL' for check in measured)
    return dict(status='FAIL' if failed else 'PASS', checked=len(measured), failed=failed,
                legacy_diagnostic_checks=len(checks) - len(measured),
                legacy_diagnostic_failures=sum(check['status'] == 'FAIL' for check in checks
                                               if check.get('scope') == 'diagnostic'))


def recheck_protocol(source, output):
    """Add a separate protocol report to a sealed transient. Never rerun ngspice."""
    manifest = source / 'manifest.json'
    previous = json.loads(manifest.read_text())
    if previous['schema_version'] != 1 or previous['simulator_status'] != 'PASS':
        raise ValueError('Expected a completed transient')
    probes, waveform = (pinned(source / name, previous['artifacts'][name])
                        for name in ('probes.json', 'waveform.dat'))
    if previous['cycle_records_sha256'] != FIXTURE_RECEIPT:
        raise ValueError('Source run uses a different fixture')
    stimulus = pinned(QUAL / 'results.json', FIXTURE_RECEIPT)
    records = json.loads(stimulus.read_text())['cycles'][:previous['cycles']]
    mapping = json.loads(probes.read_text())['mapping']
    output = new_directory(output)
    receipt = dict(schema_version=1, scope='Offline protocol diagnostics of a completed transient',
                   source_manifest_sha256=sha256(manifest), waveform_sha256=sha256(waveform),
                   source_qualification=previous['qualification'], source_status=previous['status'],
                   source_functional_status=previous['functional_status'], status='ERROR')
    try:
        nodes = sorted(set(mapping.values()))
        with waveform.open() as stream:
            has_ownership = 'v(host_en)' in stream.readline().lower().split()
        rows, columns = read_waveform(waveform, nodes, PROTOCOL_VECTORS if has_ownership else ())
        if len(rows) != previous['samples'] or rows[-1][0] < previous['stop_ns'] * 1e-9 - 1e-15:
            raise ValueError('Waveform does not cover the pinned transient')
        if not has_ownership:
            receipt.update(status='NOT_CHARACTERIZED', reason='Source lacks write/ownership vectors')
            return 1
        receipt.update(write_protocol_checks(output, rows, {
            **{label: columns[node] for label, node in mapping.items()},
            **{vector: columns[vector] for vector in PROTOCOL_VECTORS},
        }, records))
    except ValueError as error:
        receipt['error'] = str(error)
    finally:
        finish(output, receipt)
    return int(receipt['status'] != 'PASS')


def has_resistive_port(extracted, port):
    return any(parts[0].upper().startswith('R') and port in parts[1:3]
               for parts in (line.split() for line in logical_cards(extracted)))


def simulate(source, output, corner, cycles, timeout, slot=0, maximum_step_ps=25, required_rc_ports=()):
    from run_phase2_extracted_access import model_closure

    output = new_directory(output)
    extraction = json.loads((source / 'manifest.json').read_text())
    profiles = {'PASS_RC_STRUCTURE': 'all', 'PASS_C_ONLY_STRUCTURE': 'c_only'}
    if profiles.get(extraction['status']) != extraction['profile']:
        raise ValueError('Missing audited extraction input')
    gds = pinned(Path(extraction['gds_path']), extraction['gds_sha256'])
    netlist, ext = [pinned(source / name, extraction['artifacts'][name]) for name in
                    ('extracted_rc.spice', 'phase3_rc_flat.ext')]
    receipt = dict(schema_version=1, status='ERROR', simulator_status='NOT_CHARACTERIZED',
                   functional_status='NOT_CHARACTERIZED', qualification='NOT_CHARACTERIZED',
                   gds_sha256=sha256(gds), extraction_manifest_sha256=sha256(source / 'manifest.json'),
                   corner=corner, vdd_v=1.8, temp_c=27, load_ff_per_bit=10, period_ns=20,
                   maximum_step_ps=maximum_step_ps, model_sha256=sha256(PDK), netlist_sha256=sha256(netlist),
                   scope='Reconstructed 4x8 ECO, benchmark diagnostics',
                   extraction=extraction['extraction'], profile=extraction['profile'])
    try:
        extracted = netlist.read_text()
        coverage = {port: has_resistive_port(extracted, port) for port in required_rc_ports}
        if coverage:
            receipt['required_rc_ports'] = coverage
        if coverage and (extraction['profile'] != 'all' or not all(coverage.values())):
            receipt.update(status='BLOCKED', reason='Required distributed port resistance is absent')
            return 1
        fixture_receipt = pinned(QUAL / 'results.json', FIXTURE_RECEIPT)
        fixture = json.loads(fixture_receipt.read_text())
        bench = pinned(QUAL / 'bench.spice', fixture['artifacts']['bench.spice'])
        models = model_closure(PDK)
        (output / 'model_hashes.json').write_text(json.dumps(models, indent=2) + '\n')
        binding, _ = bind_rc_deck(extracted)
        (output / 'binding.spice').write_text(binding)
        (output / 'fabric.spice').write_text('* Fabric included in flat PEX\n')
        resistance_ext = source / 'phase3_rc_flat.res.ext'
        if resistance_ext.name in extraction['artifacts']:
            pinned(resistance_ext, extraction['artifacts'][resistance_ext.name])
        else:
            resistance_ext = None
        mapping, missing = probe_nodes(extracted, ext, resistance_ext)
        (output / 'probes.json').write_text(json.dumps(dict(mapping=mapping, missing=missing), indent=2) + '\n')
        nodes = sorted(set(mapping.values()))
        vectors = list(PUBLIC) + list(PROTOCOL_VECTORS) + [f'v(xdut.{node})' for node in nodes]
        deck = prepare_deck(bench.read_text(), corner, 10)
        records = fixture['cycles']
        records = [cycle for cycle in records if cycle['cycle'] < cycles]
        if not records or len(records) != cycles:
            raise ValueError('Invalid cycle count')
        stop = 20 * cycles + 10
        if deck.count('tran 10p 370n 0 10p') != 1:
            raise ValueError('Unexpected transient declaration in pinned fixture')
        deck = deck.replace('tran 10p 370n 0 10p', f'tran 10p {stop}n 0 {maximum_step_ps}p')
        deck = re.sub(r'(?m)^\.save .+$', '.save ' + ' '.join(vectors), deck)
        deck = re.sub(r'(?m)^wrdata waveform.dat .+$', 'wrdata waveform.dat ' + ' '.join(vectors), deck)
        (output / 'bench.spice').write_text(deck)
        command = ['ngspice', '-n', '-b', 'bench.spice']
        receipt.update(command=command, cycles=cycles, stop_ns=stop,
                       fixture_sha256=sha256(bench), cycle_records_sha256=FIXTURE_RECEIPT)
        log_path = output / 'ngspice.log'
        receipt['simulator_status'] = 'ERROR'
        lock_name = '.eco_simulator.lock' if slot == 0 else f'.eco_simulator_{slot}.lock'
        with (ROOT / 'build/phase3' / lock_name).open('a') as lock, log_path.open('x') as log:
            fcntl.flock(lock, fcntl.LOCK_EX)
            subprocess.run(command, cwd=output, stdout=log, stderr=subprocess.STDOUT,
                           env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
                           preexec_fn=ngspice_limits, check=True, timeout=timeout)
        log_text = log_path.read_text(errors='replace')
        if (not re.search(r'^ngspice-\S+ done\s*$', log_text, re.M)
                or re.search(r'analysis aborted|simulation interrupted|^\s*(?:Fatal|Error):', log_text, re.I | re.M)):
            raise ValueError('ngspice log does not demonstrate completed transient')
        raw = output / 'waveform.dat'
        if model_closure(PDK) != models:
            raise ValueError('PDK model closure changed during simulation')
        pinned(netlist, receipt['netlist_sha256'])
        pinned(fixture_receipt, FIXTURE_RECEIPT)
        pinned(bench, receipt['fixture_sha256'])
        rows, columns = read_waveform(raw, nodes, PROTOCOL_VECTORS)
        if rows[-1][0] < stop * 1e-9 - 1e-15:
            raise ValueError('Incomplete transient')
        receipt.update(simulator_status='PASS', samples=len(rows))
        metrics, checks = analyze(rows, records, corner, output.name)
        write_csv(output / 'metrics.csv', metrics, COLUMNS)
        write_csv(output / 'read_checks.csv', checks, list(checks[0]))
        failures = sum(item['status'] == 'FAIL' for item in checks)
        receipt.update(status='FAIL' if failures else 'NOT_CHARACTERIZED', read_bits_checked=len(checks),
                       read_bits_failed=failures, functional_status='FAIL' if failures else 'PASS',
                       functional_scope='new DATA word at fixed bench samples ±100 ps only')
        probes = {label: columns[node] for label, node in mapping.items()}
        try:
            receipt['write_ownership'] = write_protocol_checks(output, rows, {
                **probes, **{v: columns[v] for v in PROTOCOL_VECTORS},
            }, records)
            receipt['functional_scope'] += '; captured write data and strong host ownership'
            if receipt['write_ownership']['status'] == 'FAIL':
                receipt.update(status='FAIL', functional_status='FAIL')
        except ValueError as error:
            receipt['write_ownership'] = dict(status='NOT_CHARACTERIZED', reason=str(error))
            if receipt['functional_status'] != 'FAIL':
                receipt['functional_status'] = 'NOT_CHARACTERIZED'
        classified = localize_failures(rows, probes, checks, records)
        if classified:
            write_csv(output / 'failure_stages.csv', classified, list(classified[0]))
        try:
            diagnostics = trace_read_path(rows, probes, records, weak_disabled=False)
            write_csv(output / 'read_path.csv', diagnostics, list(diagnostics[0]))
        except (KeyError, ValueError) as error:
            receipt['diagnostic_error'] = str(error)
    except Exception as error:
        receipt['error'] = str(error)
    finally:
        finish(output, receipt)
    return 1  # Full electrical qualification is outside this diagnostic.


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    e = commands.add_parser('extract')
    e.add_argument('--geometry', type=Path, required=True)
    e.add_argument('--magic', required=True)
    e.add_argument('--capacitive-only', action='store_true')
    data_ports = tuple(f'DATA[{i}]' for i in range(8))
    e.add_argument('--force-rc-port', action='append', default=[], choices=data_ports,
                   help='Select a named port for export even below Magic cutoffs')
    e.add_argument('--rc-mindelay-ps', type=float,
                   help='Set the Magic delay threshold. Zero disables delay pruning.')
    s = commands.add_parser('simulate')
    s.add_argument('--source', type=Path, required=True)
    s.add_argument('--corner', choices=('tt', 'ss', 'ff'), required=True)
    s.add_argument('--cycles', type=int, choices=range(8, 19), default=18)
    s.add_argument('--max-step-ps', type=int, choices=(5, 10, 25), default=25)
    s.add_argument('--require-rc-port', action='append', default=[], choices=data_ports,
                   help='Block the run if this port has no distributed resistance in the PEX')
    s.add_argument('--timeout', type=int,
                   help='Simulation time limit in seconds. Defaults to 2400 for 8 cycles, up to 4800 for 18.')
    s.add_argument('--slot', type=int, choices=(0, 1), default=0,
                   help='Use slot 1 only with RAM headroom and an independent CPU affinity')
    r = commands.add_parser('restore-subatto')
    r.add_argument('--source', type=Path, required=True)
    p = commands.add_parser('recheck-protocol')
    p.add_argument('--source', type=Path, required=True)
    for command in (e, r, s, p):
        command.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.action == 'extract':
        if args.capacitive_only and (args.force_rc_port or args.rc_mindelay_ps is not None):
            parser.error('Resistance options require distributed extraction')
        if args.rc_mindelay_ps is not None and (not math.isfinite(args.rc_mindelay_ps) or args.rc_mindelay_ps < 0):
            parser.error('--rc-mindelay-ps must be finite and nonnegative')
        raise SystemExit(extract(args.geometry.resolve(), args.output, args.magic, args.capacitive_only,
                                 tuple(dict.fromkeys(args.force_rc_port)), args.rc_mindelay_ps))
    if args.action == 'restore-subatto':
        raise SystemExit(restore(args.source.resolve(), args.output))
    if args.action == 'recheck-protocol':
        raise SystemExit(recheck_protocol(args.source.resolve(), args.output))
    timeout = args.timeout if args.timeout is not None else 2400 + (args.cycles - 8) * 240
    if timeout <= 0:
        parser.error('--timeout must be positive')
    raise SystemExit(simulate(args.source.resolve(), args.output, args.corner, args.cycles, timeout,
                              args.slot, args.max_step_ps, args.require_rc_port))
