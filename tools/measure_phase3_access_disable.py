#!/usr/bin/env python3
"""Measure access and bus release from the sealed SS transients of the spaced 4x8 ECO."""

import argparse
import json
from pathlib import Path
import re
import sys

from phase3_rc_characterization import PDK, QUAL, at, bind_rc_deck, crossing, prepare_deck, valid_suffix_start
from phase3_rc_extraction import ROOT, sha256
from phase3_rc_probe_report import read_waveform
from phase3_rc_read_path import HIGH, LOW, LOCAL_CLOCKS, OUTPUT_ENABLES, WORDLINES, correct
from phase3_rc_turnaround import EXTRA, SCHEDULES, analyze_masks, deck_text
from run_phase3_eco_pex import FIXTURE_RECEIPT, PROTOCOL_VECTORS, new_directory, pinned, protocol_checks


BUILD = ROOT / 'build/phase3'
PHYSICAL = ROOT / 'reports/phase2/local'
CANDIDATE = 'phase3_danilo_ss_ff2_spaced'
GDS_SHA256 = 'b610c30b563c5830900792440e4f4295777029cfd9ab4496072f7d22fdab3365'
READ_CASES = {
    'standard': ('danilo_ss_ff2_spaced_pex', 'danilo_ss_ff2_spaced_pex_sealed', 'danilo_ss_ff2_spaced_ss_rc_probed'),
    'no_delay_pruning': ('data7_ref_nocut_pex', 'data7_ref_nocut_reconciled', 'data7_ref_nocut_ss'),
}
CONDITIONS = dict(corner='ss', vdd_v=1.8, temp_c=27, load_ff_per_bit=10,
                  maximum_step_ps=25, slew_ps=50)
READ_PERIOD_NS = 20


def require(condition, message):
    if not condition:
        raise ValueError(message)


def candidate(provenance):
    route = BUILD / 'danilo_ss_ff2_spaced_route'
    layout, gds, lef = (PHYSICAL / f'{CANDIDATE}_{view}' for view in ('layout', 'gds', 'lef'))

    def record(path, expected=None):
        if expected is not None:
            pinned(path, expected)
        provenance[str(path.relative_to(ROOT))] = sha256(path)
        return path

    proof_path = record(gds/'results.json')
    proof = json.loads(proof_path.read_text())
    require(proof['status'] == 'PASS_GEOMETRY_LVS' and proof['drc_markers'] == ['0']
            and proof['lvs'] == 'UNIQUE_MATCH_W_L_BODY_MODEL', 'Missing physical proof')
    layout_receipt = layout/'results.json'
    physical = json.loads(record(layout_receipt, proof['inputs'][f'/work/{layout_receipt.relative_to(ROOT)}']).read_text())
    route_receipt = json.loads(record(route/'results.json', physical['route_receipt_sha256']).read_text())
    selection = route_receipt['selection']
    require(selection['evaluation_tap'] == 48 and selection['capture_clock'] == 'public CLK'
            and selection['output_cell'] == 'ebufn_8' and selection['output_ff'] == 'dfxtp_2'
            and selection['data_pin_placement'] == 'distributed-spaced'
            and not selection.get('ownership_nand4bb'), 'Unexpected ECO selection')
    record(route/'routed.v', route_receipt['build_artifacts']['routed.v'])
    record(layout/'final.v', physical['artifacts']['final.v'])
    record(layout/'reference_mos.spice', proof['inputs'][f'/work/{(layout/"reference_mos.spice").relative_to(ROOT)}'])
    record(gds/'final_extracted.spice', proof['artifacts']['final_extracted.spice'])
    require(proof['artifacts']['sram_4x8.gds'] == GDS_SHA256, 'Unexpected geometry identity')
    record(gds/'sram_4x8.gds', GDS_SHA256)
    abstract = json.loads(record(lef/'results.json').read_text())
    require(abstract['status'] == 'PASS_GEOMETRY_ABSTRACT' and abstract['source_gds_sha256'] == GDS_SHA256,
            'LEF does not bind to the verified geometry')
    record(lef/'sram_4x8.lef', abstract['artifacts']['sram_4x8.lef'])
    return dict(gds_sha256=GDS_SHA256, physical_receipt_sha256=sha256(proof_path),
                reconstructed_from=route_receipt['reconstructed_from'], selection=selection,
                geometry_status='VERIFIED', electrical_status='PROVISIONAL')


def open_waveform(extraction, run, design, profiles, provenance):
    source_file, manifest_file = extraction/'manifest.json', run/'manifest.json'
    source, manifest = (json.loads(path.read_text()) for path in (source_file, manifest_file))
    require(source['status'] == 'PASS_RC_STRUCTURE' and source['profile'] == 'all' and source['capacitance_audit']['different'] == 0,
            'Expected sealed distributed RC')
    require(source['geometry_receipt_sha256'] == design['physical_receipt_sha256']
            and source['gds_sha256'] == manifest['gds_sha256'] == design['gds_sha256'], 'Geometry or physical receipt differs')
    require(manifest['extraction_manifest_sha256'] == sha256(source_file)
            and manifest['simulator_status'] == 'PASS' and manifest['corner'] == 'ss', 'Waveform lacks the expected extraction or completed SS simulation')
    netlist = pinned(extraction/'extracted_rc.spice', source['artifacts']['extracted_rc.spice'])
    require(sha256(netlist) == manifest['netlist_sha256'] == source['extraction_stats']['netlist_sha256'],
            'Waveform netlist differs from verified PEX')
    for file in ('bench.spice', 'binding.spice', 'model_hashes.json', 'ngspice.log', 'waveform.dat', 'probes.json'):
        pinned(run/file, manifest['artifacts'][file])
        provenance[str((run/file).relative_to(ROOT))] = manifest['artifacts'][file]
    require((run/'binding.spice').read_text() == bind_rc_deck(netlist.read_text())[0], 'Bench binding differs from the pinned PEX')
    log = (run/'ngspice.log').read_text(errors='replace')
    require(re.search(r'^ngspice-\S+ done\s*$', log, re.M)
            and not re.search(r'analysis aborted|simulation interrupted|^\s*(?:Fatal|Error):', log, re.I | re.M),
            'Incomplete transient in source log')
    for path in (source_file, manifest_file, netlist):
        provenance[str(path.relative_to(ROOT))] = sha256(path)
    if profiles == PROTOCOL_VECTORS:
        probes = json.loads((run/'probes.json').read_text())['mapping']
        stop = manifest['stop_ns']
    else:
        probes = json.loads((run/'probes.json').read_text())
        stop = SCHEDULES[manifest['campaign']].end_ns
    nodes = sorted(set(probes.values()))
    rows, columns = read_waveform(run/'waveform.dat', nodes, profiles, minimum_end=stop*1e-9-1e-15)
    require(len(rows) == manifest['samples'], 'Unexpected number of waveform samples')
    columns.update({label: columns[node] for label, node in probes.items()})
    models = json.loads((run/'model_hashes.json').read_text())
    # The closure records the resolved path of the top model first.
    model_root = next(iter(models), '')
    require(Path(model_root).parts[-4:] == PDK.parts[-4:]
            and manifest.get('model_sha256', models[model_root]) == models[model_root],
            'Missing or conflicting PDK model identity')
    return manifest, rows, columns, nodes, models


def extraction_settings(raw, sealed, without_pruning, provenance):
    seal = json.loads((sealed/'manifest.json').read_text())
    raw_path = pinned(raw/'manifest.json', seal['original_rc_manifest_sha256'])
    original = json.loads(raw_path.read_text())
    tcl = pinned(raw/'extract.tcl', original['artifacts']['extract.tcl'])
    c_only = pinned(raw/'c_only.spice', original['artifacts']['c_only.spice'])
    expected_options = ['extresist mindelay 0', 'extresist force {DATA[7]}'] if without_pruning else []
    options = [line for line in tcl.read_text().splitlines()
               if line.startswith(('extresist mindelay ', 'extresist force '))]
    require(options == expected_options and original['gds_sha256'] == seal['gds_sha256'],
            'Unexpected extraction settings or geometry')
    for path in (raw_path, tcl, c_only):
        provenance[str(path.relative_to(ROOT))] = sha256(path)
    return dict(mindelay_ps=0 if without_pruning else 1, forced_rc_ports=original.get('forced_rc_ports', []),
                c_only_sha256=sha256(c_only), magic_command=original['command'],
                magic_rcfile_sha256=original['rcfile_sha256'])


def edge(rows, col, start, end, direction):
    edges = crossing(rows, col, start, end, .9, direction)
    require(len(edges) == 1, f'Expected one {direction} 50% crossing for column {col}')
    return edges[0]


def survives(rows, col, start, end, expected):
    return valid_suffix_start(rows, col, start, end, expected) == start


def measure_word(rows, columns, rec):
    rise_start, fall_start = (rec[key]*1e-9 for key in ('rise_ns', 'fall_ns'))
    end = rec['calibration']['weak_on_ns']*1e-9
    rise = edge(rows, 1, rise_start, rise_start+.1e-9, 'rise')
    fall = edge(rows, 1, fall_start, fall_start+.1e-9, 'fall')
    require(rise < fall < end and rows[-1][0] >= end, 'Incomplete read observation window')
    high = [row for row in rows if rise <= row[0] <= fall]
    require(bool(high), 'No samples in read high phase')
    wordlines = [max(row[columns[wl]] for row in high) for wl in WORDLINES]
    selected = wordlines[rec['row']] >= HIGH and all(
        level <= LOW for row, level in enumerate(wordlines) if row != rec['row'])
    host_off = survives(rows, columns['v(HOST_EN)'], rise, end, 0)
    bits = []
    for bit, clock in enumerate(LOCAL_CLOCKS):
        expected = (rec['expected'] >> bit) & 1
        data = bit+2
        q = columns['_75_.Q' if bit == 0 else f'_{87+bit}_.A']
        capture = edge(rows, columns[clock], fall, end, 'rise')
        sense = at(rows, capture, columns[f'_{43-bit}_.A1'])
        d = at(rows, capture, columns[f'_{75+bit}_.D'])
        q_valid = valid_suffix_start(rows, q, capture, end, expected)
        valid = valid_suffix_start(rows, data, fall, end, expected)
        captured = (correct(sense, expected) and correct(d, expected) and q_valid is not None)
        enabled = survives(rows, columns[OUTPUT_ENABLES[bit]], fall, end, 0)
        direction = 'rise' if expected else 'fall'
        edges = crossing(rows, data, fall, end, .9, direction)
        changing = correct(at(rows, capture, q), 1-expected) and correct(at(rows, fall, data), 1-expected)
        observed = (changing and captured and enabled and host_off and selected and len(edges) == 1
                    and valid is not None and capture <= edges[0] <= valid)
        bits.append(dict(bit=bit, expected=expected, internal_capture_verified=captured, drive_enabled=enabled,
                         sense_at_capture_v=sense, d_at_capture_v=d, local_capture_s=capture,
                         q_valid_since_s=q_valid, data_valid_since_s=valid,
                         transition=direction if observed else None,
                         tCLK_TO_DATA_s=edges[0]-fall if observed else None,
                         status='PROVISIONAL' if observed else 'NOT_CHARACTERIZED'))
    verified = selected and host_off and all(b['internal_capture_verified'] and b['drive_enabled']
                                             and b['data_valid_since_s'] is not None for b in bits)
    word_time = max(b['data_valid_since_s'] for b in bits) if verified else None
    verified_from = max(word_time, *(b['local_capture_s'] for b in bits)) if verified else None
    stable = (verified and all(b['q_valid_since_s'] <= verified_from for b in bits)
              and any(verified_from < row[0] < end for row in rows))
    observed = stable and any(b['tCLK_TO_DATA_s'] is not None for b in bits)
    return dict(cycle=rec['cycle'], row=rec['row'], expected_word=f"0x{rec['expected']:02X}",
                selected_wordline_verified=selected, host_off_verified=host_off,
                status='PROVISIONAL' if observed else 'NOT_CHARACTERIZED',
                observation='MEASURED' if observed else 'NOT_CHARACTERIZED',
                word_verification='VERIFIED' if stable else 'NOT_CHARACTERIZED',
                clk_rise50_s=rise, clk_fall50_s=fall, stable_word_since_s=word_time if observed else None,
                word_verified_from_s=verified_from if stable else None,
                observation_end_s=end, stable_duration_s=end-word_time if observed else None,
                tACCESS_s=word_time-rise if observed else None,
                tREAD_VALID_s=word_time-fall if observed else None, bits=bits)


def normalized_deck(text):
    return [line for line in text.splitlines() if not line.startswith(('.save ', 'wrdata waveform.dat '))]


def measure_reads(source, run, design, fixture, bench, provenance):
    manifest, rows, columns, _, models = open_waveform(source, run, design, PROTOCOL_VECTORS, provenance)
    require(all(manifest[key] == CONDITIONS[key] for key in CONDITIONS if key != 'slew_ps')
            and manifest['period_ns'] == READ_PERIOD_NS
            and manifest['cycle_records_sha256'] == FIXTURE_RECEIPT and manifest['fixture_sha256'] == sha256(bench),
            'Read fixture or conditions differ from the selected scope')
    deck = prepare_deck(bench.read_text(), 'ss', 10).replace('tran 10p 370n 0 10p', 'tran 10p 170n 0 25p')
    require(normalized_deck((run/'bench.spice').read_text()) == normalized_deck(deck)
            and manifest['cycles'] == 8 and manifest['stop_ns'] == 170, 'Unexpected read stimulus')
    records = fixture['cycles'][:manifest['cycles']]
    checks = protocol_checks(rows, columns, records)
    writes = {(c['cycle'], c['kind'], c['bit']): c['status'] for c in checks if c['cycle'] is not None}
    expected_contents, words = {}, []
    for rec in records:
        if rec['operation'] == 'write':
            valid = all(writes[rec['cycle'], kind, bit] == 'PASS' for bit in range(8)
                        for kind in ('write_data_ready_before_we20', 'no_steady_host_current'))
            expected_contents[rec['row']] = rec['expected'] if valid else None
        if rec['operation'] == 'read':
            require(expected_contents.get(rec['row']) == rec['expected'], 'Read not preceded by a verified write stimulus')
            words.append(measure_word(rows, columns, rec))
    return dict(source=run.name, historical_result=manifest['status'], conditions={**CONDITIONS, 'period_ns': READ_PERIOD_NS},
                pex_sha256=manifest['netlist_sha256'], words=words,
                write_checks={kind: sum(k[1] == kind and value == 'PASS' for k, value in writes.items())
                              for kind in ('write_data_ready_before_we20', 'no_steady_host_current')}), models


def joint_release(mask):
    """Both pad voltage and current must have a valid suffix under the opposing probe."""
    current = mask['weak_current_release_ps']
    voltage = mask['weak_pull_valid_ps']
    if mask['status'] != 'PASS' or current is None or current < 0:
        return None
    # A PASS without a voltage entry means the pad was already within the
    # probe's band throughout this mask. Initial drive is still checked by current.
    return max(current, voltage) if voltage is not None else current


def measure_disable(source, run, guard, design, expected_models, provenance):
    manifest, rows, columns, nodes, models = open_waveform(source, run, design, EXTRA, provenance)
    require(models == expected_models and manifest['campaign'] == 'v2' and manifest['host_guard_ps'] == guard
            and (run/'bench.spice').read_text() == deck_text('ss', nodes, guard), 'Unexpected mask or handoff stimulus')
    masks, handoff, reads = analyze_masks(rows, columns, columns, SCHEDULES['v2'])
    for mask in masks:
        value = joint_release(mask)
        mask.update(tDIS_s=value*1e-12 if value is not None else None,
                    status='PROVISIONAL' if value is not None else 'NOT_CHARACTERIZED',
                    observation='MEASURED' if value is not None else 'NOT_CHARACTERIZED',
                    mask_verification='VERIFIED' if value is not None else 'NOT_CHARACTERIZED')
    controls = {}
    for control, start, direction in SCHEDULES['v2'].masks:
        bits = [item for item in masks if item['control'] == control]
        observed = len(bits) == 8 and all(b['tDIS_s'] is not None for b in bits)
        controls[control] = dict(direction=direction, status='PROVISIONAL' if observed else 'NOT_CHARACTERIZED',
            observation='MEASURED' if observed else 'NOT_CHARACTERIZED',
            tDIS_s=max(b['tDIS_s'] for b in bits) if observed else None,
            range_s=[min(b['tDIS_s'] for b in bits), max(b['tDIS_s'] for b in bits)] if observed else None,
            observation_end_s=(start + SCHEDULES['v2'].mask_ns - .15)*1e-9, bits=bits)
    handoff_fields = ('bit', 'status', 'host_on_ns', 'te_b80_ns', 'guard_margin_ps', 'overlap_proxy_ps',
                      'opposed_at_100ps_ua', 'opposed_at_200ps_ua', 'host_steady_peak_ua', 'write_to_read_margin_ps')
    return dict(source=run.name, historical_result=manifest['status'], pex_sha256=manifest['netlist_sha256'],
                guard_ps=guard, conditions=CONDITIONS, schedule=manifest['campaign'],
                previous_read_word='0xAA', opposing_probe_ohm=1000, current_limit_a=50e-6,
                controls=controls, handoff=[{key: bit[key] for key in handoff_fields} for bit in handoff], reads=reads)


def collect():
    provenance = {}
    design = candidate(provenance)
    fixture_path = pinned(QUAL/'results.json', FIXTURE_RECEIPT)
    fixture = json.loads(fixture_path.read_text())
    bench = pinned(QUAL/'bench.spice', fixture['artifacts']['bench.spice'])
    for path in (fixture_path, bench, Path(__file__).resolve()):
        provenance[str(path.relative_to(ROOT))] = sha256(path)
    try:
        raw, *standard = (BUILD / filename for filename in READ_CASES['standard'])
        raw_no_pruning, *no_pruning = (BUILD / filename for filename in READ_CASES['no_delay_pruning'])
        primary, models = measure_reads(*standard, design, fixture, bench, provenance)
        contrast, contrast_models = measure_reads(*no_pruning, design, fixture, bench, provenance)
        primary['extraction_settings'] = extraction_settings(raw, standard[0], False, provenance)
        contrast['extraction_settings'] = extraction_settings(raw_no_pruning, no_pruning[0], True, provenance)
        common = ('c_only_sha256', 'magic_command', 'magic_rcfile_sha256')
        require(models == contrast_models and all(primary['extraction_settings'][key] == contrast['extraction_settings'][key]
                                                   for key in common), 'Access PEX or PDK extraction conditions differ')
        deltas = []
        for a, b in zip(primary['words'], contrast['words'], strict=True):
            require((a['cycle'], a['expected_word']) == (b['cycle'], b['expected_word']), 'Read cycles differ')
            valid = a['observation'] == b['observation'] == 'MEASURED'
            deltas.append(dict(cycle=a['cycle'], status='PROVISIONAL' if valid else 'NOT_CHARACTERIZED',
                               no_pruning_minus_standard_tACCESS_s=b['tACCESS_s']-a['tACCESS_s'] if valid else None,
                               no_pruning_minus_standard_tREAD_VALID_s=b['tREAD_VALID_s']-a['tREAD_VALID_s'] if valid else None))
        short = measure_disable(standard[0], BUILD/'turnaround_ref_ss_v2_300', 300, design, models, provenance)
        long = measure_disable(standard[0], BUILD/'turnaround_ref_ss_v2_1500', 1500, design, models, provenance)
        return dict(schema_version=1, mode='offline_waveform_replay', electrical_simulation_performed=False,
                    electrical_qualification='NOT_CHARACTERIZED', candidate=design, inputs_sha256=provenance,
                    thresholds=dict(clock_control_50_v=.9, valid_low_max_v=LOW, valid_high_min_v=HIGH),
                    model_sha256=next(iter(models.values())), access=dict(standard=primary, no_delay_pruning=contrast, delta=deltas),
                    disable=long, handoff_stress_300ps=short,
                    pending={name: 'NOT_CHARACTERIZED' for name in
                             ('tDIS_rc_sensitivity', 'setup_hold', 'phase_widths', 'Fmax', 'power', 'PVT', 'SNM', 'Liberty')})
    except KeyError as error:
        raise ValueError(f'Missing required source field or probe: {error}') from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError('Output already exists')
        report = collect()
        encoded = json.dumps(report, indent=2, allow_nan=False) + '\n'
        output = new_directory(args.output)
        (output/'observations.json').write_text(encoded)
        print(output/'observations.json')
    except (OSError, ValueError, KeyError) as error:
        print(f'Replay failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
