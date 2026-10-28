#!/usr/bin/env python3
"""Review the retained two-device probe; run inside the project EDA environment."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'sims/row_decoder'))
import run_row_decoder_contract as contract
from audit_signed_device_domain import parse_leaf_devices, read_raw

FOLDER = Path(__file__).resolve().parent
ARCHIVE = ROOT / 'sims/row_decoder/results/compact_decoder_fast_opinit_screen_refinement_0p5ps'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((ARCHIVE / 'baseline/manifest.json').read_text())
    for name, expected in manifest['model_dependencies_sha256'].items():
        if digest(Path(name)) != expected:
            raise ValueError(f'Model dependency changed: {name}')
    raw, raw_hash = read_raw(FOLDER / 'waveform.raw')
    previous, _ = read_raw(ARCHIVE / 'artifacts/baseline/fast_11_to_00/waveform.raw')
    time = raw['time']
    if not np.all(np.isfinite(time)) or not np.all(np.diff(time) > 0):
        raise ValueError('Invalid waveform timestamps')
    mask = time >= 1e-9
    devices = parse_leaf_devices(ARCHIVE / 'baseline/input_netlist.spice')
    records, peaks = [], []
    for label in ('x1.m12', 'x1.m1'):
        kind, nodes = devices[label]
        polarity = 1 if kind == 'n' else -1
        pins = [np.zeros_like(time) if n == '0' else raw[f'v({n})'] for n in nodes]
        d, g, s, b = pins
        model = 'nfet' if kind == 'n' else 'pfet'
        instance = label.replace('.m', '.xm')
        prefix = f'@m.{instance}.msky130_fd_pr__{model}_01v8'
        ng, nd, nb = [raw[f'v({prefix}[{q}])'] for q in ('vgs', 'vds', 'vbs')]
        if not all(np.isfinite(v).all() for v in (*pins, ng, nd, nb)):
            raise ValueError(f'Nonfinite probe on {label}')
        effective = np.minimum(d, s) if kind == 'n' else np.maximum(d, s)
        external = {'VGS': g-effective, 'VDS': polarity*np.abs(d-s), 'VBS': b-effective}
        intrinsic = {'VGS': polarity*(ng-np.minimum(nd, 0)),
                     'VDS': polarity*np.abs(nd), 'VBS': polarity*(nb-np.minimum(nd, 0))}
        for metric in external:
            a, z = external[metric][mask], intrinsic[metric][mask]
            records.append(dict(device=label, metric=metric,
                                external_min_v=float(a.min()), external_max_v=float(a.max()),
                                intrinsic_min_v=float(z.min()), intrinsic_max_v=float(z.max()),
                                max_abs_difference_v=float(np.abs(a-z).max())))
        i = int(np.argmax(np.abs(g-d)))
        peaks.append(dict(device=label, time_ns=float(time[i]*1e9),
                          external_vgd_v=float((g-d)[i]), external_vgs_v=float(external['VGS'][i]),
                          intrinsic_vgs_v=float(intrinsic['VGS'][i]),
                          external_vds_v=float(external['VDS'][i]), intrinsic_vds_v=float(intrinsic['VDS'][i])))
    case = next(c for c in json.loads((ARCHIVE / 'cases.json').read_text()) if c['label'] == 'fast_11_to_00')
    _, nodes, devs, terminals, schedule = contract.make_deck(
        (ARCHIVE / 'baseline/input_netlist.spice').read_text(), case,
        Path('/opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice'))
    functional, _, _ = contract.analyze(raw, case, nodes, devs, terminals, schedule)
    if functional['check_fail']:
        raise ValueError('Functional checks failed on the probe waveform')
    source = ARCHIVE / 'artifacts/baseline/fast_11_to_00/case.spice'
    result = dict(
        scope='One FF/1.8V/125C baseline 11-to-00 case; OP initialization; 0.5ps maximum step; two devices only',
        source_deck=str(source.relative_to(ROOT)), source_deck_sha256=digest(source),
        probe_deck_sha256=digest(FOLDER / 'case.spice'), raw_sha256=raw_hash,
        ngspice_log_sha256=digest(FOLDER / 'ngspice.log'), analysis_script_sha256=digest(Path(__file__)),
        contract_script_sha256=digest(Path(contract.__file__)),
        model_state_convention='@vgs/@vds/@vbs are polarity-normalized intrinsic differences; reverse orientation subtracts normalized vds when vds<0; multiply by polarity for physical signed values',
        window_start_ns=1, model_include_hashes_match_archive=True,
        functional_checks={'pass': functional['check_pass'], 'fail': functional['check_fail']},
        all_original_saved_traces_bitwise_equal=all(np.array_equal(raw[k], v) for k, v in previous.items()),
        records=records, external_vgd_peak_samples=peaks)
    (FOLDER / 'summary.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result['functional_checks']), 'external traces identical:', result['all_original_saved_traces_bitwise_equal'])


if __name__ == '__main__':
    main()
