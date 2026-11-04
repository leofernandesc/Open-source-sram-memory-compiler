#!/usr/bin/env python3
"""Nominal phase-event measurements from completed startup traces, not limits."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from run_phase2_digital import ROOT, sha
from run_phase2_startup_review import validate_trace


def crossing(t, values, threshold, lo, hi, rising):
    mask = ((values[:-1] < threshold) & (values[1:] >= threshold)) if rising else (
        (values[:-1] > threshold) & (values[1:] <= threshold))
    indices = np.flatnonzero(mask & (t[:-1] >= lo) & (t[:-1] < hi))
    if len(indices) != 1:
        raise ValueError(f'Ambiguous phase event ({len(indices)} crossings)')
    i = indices[0]
    return float(t[i]+(threshold-values[i])/(values[i+1]-values[i])*(t[i+1]-t[i]))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sources', nargs='+', required=True); p.add_argument('--output', required=True)
    args = p.parse_args(); out = (ROOT/args.output).resolve()
    if not out.is_relative_to(ROOT/'reports/phase2') or out.exists():
        p.error('A new report directory is required')
    out.mkdir(parents=True); rows = []; result = {'status': 'RUNNING'}
    try:
        sources = {}
        for name in args.sources:
            source = ROOT/name; state = json.loads((source/'results.json').read_text())
            if state['status'] != 'PASS':
                raise ValueError('Completed passing startup scenario required')
            sources[name] = sha(source/'results.json')
            raw = ROOT/state['build_directory']/'waveform.dat'
            if sha(raw) != state['raw_waveform_sha256']:
                raise ValueError('Changed raw waveform')
            data = np.loadtxt(raw, skiprows=1); t = data[:, 0]*1e9
            validate_trace(data, state['vectors'], state['stop_ns'])
            def col(n): return state['vectors'].index(state['probes'][n])+1
            for r in state['cycles']:
                if r['operation'] not in ('write', 'read'):
                    continue
                edge, fall = r['rise_ns'], r['fall_ns']
                pre_on = crossing(t, data[:, 10], 1.44, fall, edge+19, False)
                wl_off = crossing(t, data[:, 13+r['row']], .36, fall, edge+19, False)
                row = dict(scenario=source.name, cycle=r['cycle'], operation=r['operation'], row=r['row'],
                           wl_release_before_precharge_ns=pre_on-wl_off,
                           write_release_before_precharge_ns=None, precharge_release_before_write_ns=None,
                           selected_wl80_before_sclk20_ns=None, minimum_signed_bl_differential_at_sclk20_v=None)
                if r['operation'] == 'write':
                    pre_off = crossing(t, data[:, 10], 1.44, edge, fall, True)
                    we_on = crossing(t, data[:, 12], .36, edge, fall, True)
                    we_off = crossing(t, data[:, 12], .36, fall, edge+19, False)
                    row.update(write_release_before_precharge_ns=pre_on-we_off,
                               precharge_release_before_write_ns=we_on-pre_off)
                else:
                    sense = crossing(t, data[:, 11], .36, edge, fall, True)
                    wl_on = crossing(t, data[:, 13+r['row']], 1.44, edge, fall, True)
                    delta = [float(np.interp(sense, t, data[:, col(f'BL{b}')])-np.interp(sense, t, data[:, col(f'BLB{b}')]))
                             * (1 if (r['expected'] >> b)&1 else -1) for b in range(8)]
                    row.update(selected_wl80_before_sclk20_ns=sense-wl_on,
                               minimum_signed_bl_differential_at_sclk20_v=min(delta))
                rows.append(row)
        with (out/'events.csv').open('w') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        keys = [k for k in rows[0] if k.endswith(('_ns', '_v'))]
        result = dict(status='MEASURED', scope='Interpolated 20%/80% nominal phase events; no new acceptance limits',
                      sources=sources, analyzer_sha256=sha(Path(__file__)), events=len(rows),
                      ranges={k: dict(min=min(r[k] for r in rows if r[k] is not None),
                                      max=max(r[k] for r in rows if r[k] is not None)) for k in keys},
                      table_sha256=sha(out/'events.csv'))
    except Exception as error:
        result = dict(status='FAIL', error=str(error))
    (out/'results.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'MEASURED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
