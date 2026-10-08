#!/usr/bin/env python3
"""Focused convergence and R/C isolation using the retained decoder PEX.

R/C removal is a diagnostic intervention, never a qualified physical design.
Fresh Xschem netlisting audits the baseline; no extraction or schematic editing.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

import run_row_decoder_pex_contract as pex

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / 'sims/row_decoder/results/row_decoder_pex_output_pfets_3um_20261008'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def transform_deck(deck, mode):
    match = pex.subckt_match(deck, 'row_decoder')
    body = match[2]
    removed_r = removed_c = 0
    if mode == 'no_r':
        body, removed_r = re.subn(r'(?im)^R\d+\s+[^\n]+\n?', '', body)
        pex.require(removed_r == pex.PEX_COUNTS['resistors'], 'Unexpected R removal count')
        # This extraction has only VSS resistors. Collapse their endpoints;
        # merely deleting them would leave disconnected MOS terminals.
        pex.require(all(re.fullmatch(r'VSS(?:\.[A-Za-z0-9_]+)?', node, re.I)
                        for line in match[2].splitlines() if re.match(r'^R\d+\s', line)
                        for node in line.split()[1:3]), 'R isolation requires a VSS-only R network')
        body = re.sub(r'\bVSS\.[A-Za-z0-9_]+\b', 'VSS', body, flags=re.I)
    elif mode == 'no_c':
        body, removed_c = re.subn(r'(?im)^C\d+\s+[^\n]+\n?', '', body)
        pex.require(removed_c == pex.PEX_COUNTS['capacitors'], 'Unexpected C removal count')
    else:
        pex.require(mode == 'full', f'Unknown mode {mode}')
    deck = deck[:match.start(2)] + body + deck[match.end(2):]
    if mode == 'no_r':
        deck = re.sub(r'v\(x1\.vss\.[A-Za-z0-9_]+\)', 'v(gnd)', deck, flags=re.I)
        deck = re.sub(r'(?im)^\.save\s+([^\n]+)',
                      lambda m: '.save ' + ' '.join(dict.fromkeys(m[1].split())), deck)
    pex.require(len(re.findall(r'(?im)^C_WL\d\s+\S+\s+\S+\s+1\.74e-14', deck)) == 4,
                'WL loads were changed or removed')
    return deck, dict(removed_resistors=removed_r, removed_capacitors=removed_c,
                      collapsed_vss_nodes=mode == 'no_r')


def load_inputs():
    pex.load_simulation_dependencies()
    recorded = json.loads((ARCHIVE / 'pex/manifest.json').read_text())
    pex.require(recorded['complete'] and not recorded['errors'], 'Archived campaign incomplete')
    pex.require(digest(pex.PEX_PATH) == recorded['pex_sha256'], 'Current PEX differs from archived PEX')
    source = (ARCHIVE / 'baseline_input_netlist.spice').read_text()
    # Windows/Linux byte hashes can differ. Require electrical netlist identity
    # with a fresh audited Xschem export rather than silently accepting drift.
    with tempfile.TemporaryDirectory(prefix='decoder-pex-source-audit-') as folder:
        fresh = pex.contract.netlist_current(Path(folder))
    def electrical_lines(text):
        return [line for line in pex.screen.logical_lines(text) if line.strip() and not line.startswith('*')]
    pex.require(electrical_lines(fresh) == electrical_lines(source),
                'Fresh electrical netlist differs from archived baseline')
    pex.SOURCE_NETLIST = source
    pex.SOURCE_NODES, pex.SOURCE_DEVICES = pex.ORIGINAL_INSPECT(source, True)
    pex.SOURCE_DEVICES['__pins__'] = pex.screen.subcircuit(source, 'row_decoder')[0]
    netlist, pex.PEX_COUNTS, pex.PEX_DYNAMIC_NODES, pex.PEX_DYNAMIC_SEGMENTS = pex.inject_pex(
        source, pex.PEX_PATH.read_text())
    pex.require(netlist == (ARCHIVE / 'pex_input_netlist.spice').read_text(),
                'Generated full PEX testbench differs from retained testbench')
    pex.screen.inspect_netlist = pex.inspect_netlist
    pex.contract.mos_instances = pex.mos_instances
    return netlist, recorded, fresh


def plot_runs(runs, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    profiles = tuple(name for name in ('slow_00_to_11', 'tt_11_to_00')
                     if any(run['original'] == name for run in runs))
    fig, axes = plt.subplots(len(profiles), 3, figsize=(13, 3.5*len(profiles)),
                             constrained_layout=True, squeeze=False)
    for row, original in enumerate(profiles):
        for run in runs:
            if run['original'] != original:
                continue
            raw = pex.read_raw(Path(run['raw_path']))
            times = raw['time'] * 1e9
            selected, previous = run['new'], run['old']
            panels = ((times - 20, raw[f'v(net{5+selected})'], -.1, 1.5),
                      (times - 10, raw[f'v(net{5+previous})'], -.1, 1.5),
                      (times, raw['v(x1.a0b)'], 17.8, 18.6))
            for col, (x, y, low, high) in enumerate(panels):
                mask = (x >= low) & (x <= high)
                axes[row, col].plot(x[mask], y[mask], label=run['variant'], linewidth=1.2)
                axes[row, col].grid(alpha=.25)
                axes[row, col].set_ylabel('Voltage (V)')
                axes[row, col].set_xlim(low, high)
        vdd = 1.62 if original.startswith('slow') else 1.8
        axes[row, 0].axhline(.9*vdd, color='gray', linestyle='--')
        axes[row, 1].axhline(.1*vdd, color='gray', linestyle='--')
        for col in (0, 1):
            axes[row, col].axvline(1, color='gray', linestyle=':')
            axes[row, col].set_xlabel('Time from PCLK 50% edge (ns)')
        axes[row, 2].axhline(vdd, color='gray', linestyle='--')
        axes[row, 2].axhline(0, color='gray', linestyle='--')
        axes[row, 2].set_xlabel('Absolute time (ns)')
        for col, title in enumerate(('Selected WL evaluation', 'Selected WL precharge', 'Address A0B')):
            axes[row, col].set_title(original + '\n' + title)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle('Existing decoder PEX: convergence and artificial R/C isolation\n'
                 'No R / no C curves are diagnostic only; WL buffers remain schematic')
    fig.savefig(output / 'waveforms.png', dpi=170)
    fig.savefig(output / 'waveforms.pdf')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--timeout-s', type=int, default=600)
    parser.add_argument('--refinement-only', action='store_true',
                        help='Only slow 00-to-11, 0.5/0.25 ps, explicit tight charge tolerance')
    args = parser.parse_args()
    netlist, recorded, fresh = load_inputs()
    output = args.output_dir.resolve()
    pex.require(not output.exists(), 'Use a new output directory')
    output.mkdir(parents=True)
    (output / 'fresh_baseline_audit.spice').write_text(fresh)
    model = Path(os.environ.get('PDK_ROOT', '/opt/pdks')) / 'sky130A/libs.tech/combined/continuous/sky130.lib.spice'
    dependencies = pex.contract.model_dependencies(model)
    pex.require(dependencies == recorded['model_dependencies_sha256'],
                'Installed model dependency hashes differ from retained campaign')
    snapshot_paths = [Path(__file__), Path(pex.__file__), Path(pex.contract.__file__),
                      Path(pex.screen.__file__), Path(__file__).with_name('plot_row_decoder_review.py')]
    for path in snapshot_paths:
        shutil.copyfile(path, output / path.name)
    source_hashes = {name: digest(ROOT / name) for name in recorded['source_sha256']}
    manifest = dict(started_utc=datetime.now(timezone.utc).isoformat(), complete=False,
                    pex_sha256=digest(pex.PEX_PATH), source_sha256=source_hashes,
                    script_sha256={p.name: digest(p) for p in snapshot_paths},
                    fresh_electrical_baseline_matches_archive=True,
                    historical_source_sha256=recorded['source_sha256'],
                    source_byte_hash_matches={name: digest(ROOT / name) == expected
                                              for name, expected in recorded['source_sha256'].items()},
                    model_dependencies_sha256=dependencies, tools={'ngspice': pex.screen.tool_version('ngspice')},
                    scope='Existing decoder PEX, schematic WL buffers, four 17.4 fF loads; no physical edit.',
                    diagnostic_caveat='No R / no C decks are artificial interventions, not qualified netlists.',
                    container=os.environ.get('HOSTNAME'), timeout_s=args.timeout_s, cases=[], errors=[])
    manifest_path = output / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    bases = [c for c in pex.case_matrix() if c['label'] in ('slow_00_to_11', 'tt_11_to_00')]
    variants = (('full_5ps', 'full', 5, {}), ('full_1ps', 'full', 1, {}),
                ('full_1ps_tight', 'full', 1, {'minbreak_fs': 1, 'chgtol_c': 1e-18}),
                ('no_r_5ps', 'no_r', 5, {}), ('no_c_5ps', 'no_c', 5, {}))
    if args.refinement_only:
        bases = [c for c in bases if c['label'] == 'slow_00_to_11']
        variants = tuple((f'full_{step:g}ps_tight', 'full', step,
                          {'minbreak_fs': 1, 'chgtol_c': 1e-18}) for step in (.5, .25))
    results, checks, extrema, plotted = [], [], [], []
    for base in bases:
        for variant, mode, step, extra in variants:
            label = base['label'] + '__' + variant
            case = {**base, **extra, 'label': label, 'step_ps': step}
            folder = output / 'artifacts' / label
            folder.mkdir(parents=True)
            started = time.monotonic()
            print(f'Starting {label}', flush=True)
            record = dict(label=label, original_case=base['label'], mode=mode, step_ps=step,
                          declared_case=case, status='RUNNING')
            manifest['cases'].append(record)
            try:
                deck, nodes, devices, terminals, schedule = pex.make_deck(netlist, case, model)
                archive_deck = ARCHIVE / 'artifacts/pex' / base['label'] / 'case.spice'
                record['matches_archived_deck'] = deck == archive_deck.read_text()
                if variant == 'full_5ps':
                    pex.require(record['matches_archived_deck'], '5 ps full deck does not reproduce archived stimulus')
                deck, intervention = transform_deck(deck, mode)
                record.update(intervention)
                deck_path = folder / 'case.spice'
                deck_path.write_text(deck)
                record['deck_sha256'] = digest(deck_path)
                proc = subprocess.run(['ngspice', '-n', '-b', str(deck_path)], cwd=folder,
                                      text=True, capture_output=True, timeout=args.timeout_s)
                log = proc.stdout + proc.stderr
                (folder / 'ngspice.log').write_text(log)
                record['ngspice_return_code'] = proc.returncode
                pex.require(proc.returncode == 0 and not re.search(r'Error:|failed!|aborted', log, re.I),
                            f'ngspice failure; inspect {folder}/ngspice.log')
                raw_path = folder / 'waveform.raw'
                raw = pex.read_raw(raw_path)
                if mode == 'no_r':
                    for pins in terminals.values():
                        for node in pins:
                            if node.startswith('x1.vss.'):
                                raw[f'v({node})'] = pex.np.zeros_like(raw['time'])
                result, case_checks, case_extrema = pex.analyze(raw, case, nodes, devices, terminals, schedule)
                a0b = raw['v(x1.a0b)']
                mask = (raw['time'] >= 17.8e-9) & (raw['time'] <= 18.6e-9)
                result.update(variant=variant, diagnostic_only=mode != 'full',
                              address_a0b_min_v=float(a0b[mask].min()), address_a0b_max_v=float(a0b[mask].max()))
                results.append(result)
                checks.extend(case_checks)
                extrema.extend(case_extrema)
                plotted.append(dict(original=base['label'], variant=variant, raw_path=str(raw_path),
                                    old=base['old'], new=base['new']))
                record.update(status='COMPLETE', result=result['result'],
                              magnitude_result=result['magnitude_result'], waveform_sha256=digest(raw_path),
                              waveform_samples=len(raw['time']))
                print(f"{label}: ngspice={proc.returncode}, {result['result']}, "
                      f"WL90={result['wl_delay90_ps']:.2f} ps, "
                      f"precharge10={result['wl_precharge10_ps']:.2f} ps, "
                      f"magnitude={result['terminal_magnitude_max_v']:.6f} V", flush=True)
            except subprocess.TimeoutExpired as error:
                logs = []
                for value in (error.stdout, error.stderr):
                    if value:
                        logs.append(value.decode(errors='replace') if isinstance(value, bytes) else value)
                (folder / 'ngspice.log').write_text('\n'.join(logs) + '\nTIMEOUT\n')
                record.update(status='ERROR', error=f'Timeout after {args.timeout_s} s')
                manifest['errors'].append(dict(case=label, error=record['error']))
                print(f'{label}: {record["error"]}', flush=True)
            except Exception as error:
                record.update(status='ERROR', error=f'{type(error).__name__}: {error}')
                manifest['errors'].append(dict(case=label, error=record['error']))
                print(f'{label}: {record["error"]}', flush=True)
            record['elapsed_s'] = time.monotonic() - started
            for name, rows in (('summary', results), ('checks', checks), ('terminals', extrema)):
                if rows:
                    pex.screen.write_csv(output / f'{name}.csv', rows)
            manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    pex.require(digest(pex.PEX_PATH) == manifest['pex_sha256'], 'PEX changed while simulating')
    pex.require(source_hashes == {name: digest(ROOT / name) for name in source_hashes},
                'Circuit sources changed while simulating')
    if plotted:
        plot_runs(plotted, output)
    manifest.update(completed_utc=datetime.now(timezone.utc).isoformat(),
                    complete=not manifest['errors'] and len(results) == len(bases)*len(variants),
                    completed_cases=len(results), circuits_unchanged=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Completed {len(results)}/{len(bases)*len(variants)}; evidence: {output}', flush=True)
    if not manifest['complete']:
        return 2
    # Artificial interventions must not qualify the physical circuit.
    return pex.contract.campaign_exit_code([r for r in results if not r['diagnostic_only']], [])


if __name__ == '__main__':
    raise SystemExit(main())
