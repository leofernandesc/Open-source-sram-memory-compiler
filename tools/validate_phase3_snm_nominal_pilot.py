#!/usr/bin/env python3
"""Reproduce one seed of a four-seed tt_mm batch and audit the five observations."""

import argparse
import fcntl
import json
from pathlib import Path
import subprocess

import numpy as np

from phase3_snm_measure import TRACE_EPS_V, butterfly, read_vtc
from run_digital_regression import atomic_text
from run_phase3_eco_pex import new_directory, pinned
from run_phase3_snm import ROOT, design, model_config, reported_seed, result_for, run_case, sha256


def batch(output):
    manifest = output/'manifest.json'
    receipt = json.loads(manifest.read_text())
    cfg = receipt['config']
    cases = cfg['cases']
    if cfg!=design('nominal-proposed',cfg['mode'],cases[0]['seed'],len(cases)):
        raise ValueError('Expected sealed tt_mm nominal design')
    all_results = [result_for(output,case) for case in cases]
    if any(all_results[4:]) or any(r is None for r in all_results[:4]):
        raise ValueError('Expected exactly the first four cases of the pilot')
    return manifest,receipt,cases[:4],all_results[:4]


def repeat(output, timeout_s):
    with (output/'.run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        manifest,receipt,cases,results = batch(output)
        if results[0]['status']!='MEASURED':
            raise ValueError('The first seed did not produce a valid observation to reproduce')
        if model_config(receipt['config'])!=receipt['models']:
            raise ValueError('Installed statistical models differ')
        for name,digest in receipt['sources'].items():
            pinned(ROOT/name,digest)
        version = subprocess.run(['ngspice','--version'],timeout=10,check=True,capture_output=True,text=True)
        if version.stdout.strip()!=receipt['ngspice_version']:
            raise ValueError('Simulator differs from the sealed nominal batch')
        target = new_directory(output/'repeat_first_seed')
        (target/'manifest.json').write_bytes(manifest.read_bytes())
        return int(not run_case(target,cases[0],receipt['config'],timeout_s))


def audit(output):
    manifest,receipt,cases,results = batch(output)
    recheck = output/'repeat_first_seed'
    pinned(recheck/'manifest.json',sha256(manifest))
    repeated = result_for(recheck,cases[0])
    eligible = []
    rows = []
    cfg = receipt['config']
    for trial,base_dir in [(item,output) for item in results]+[(repeated,recheck)]:
        if trial is None:
            raise ValueError('No recorded repeat attempt')
        kind = 'repeat_first_seed' if base_dir==recheck else 'unique'
        row = {**trial,'kind':kind}
        if trial['status']=='MEASURED':
            work = base_dir/trial['attempt']
            vin,left,right = read_vtc(work/'vtc.dat',cfg['vdd'],cfg['step']).T
            reread = butterfly(vin,left,right)
            reflected = butterfly(vin,right,left)
            coarse = butterfly(vin[::2],left[::2],right[::2])
            if (any(trial[k]!=v for k,v in reread.items())
                    or abs(reread['snm_v']-reflected['snm_v'])>TRACE_EPS_V
                    or reported_seed((work/'ngspice.log').read_text())!=trial['seed']):
                raise ValueError(f'Inconsistent measurement for seed {trial["seed"]}')
            row.update(trip_left_v=float(np.interp(0,vin-left,vin)),
                       trip_right_v=float(np.interp(0,vin-right,vin)),
                       points=len(vin),coarse_grid_snm_v=coarse['snm_v'],
                       maximum_left_right_difference_v=float(np.max(np.abs(left-right))))
            if kind=='unique':
                eligible.append(row)
        rows.append(row)
    hashes = {r['artifacts']['vtc.dat'] for r in eligible}
    replay = (repeated['status']==results[0]['status']=='MEASURED'
              and repeated['artifacts']['vtc.dat']==results[0]['artifacts']['vtc.dat'])
    return dict(scope='schematic_6T_experimental_nominal',status='PROVISIONAL',
                mode=cfg['mode'],corner='tt_mm',vdd=cfg['vdd'],temp_c=cfg['temp_c'],
                closure=receipt['models']['sections']['tt_mm'],campaign_manifest_sha256=sha256(manifest),
                repeat_same_waveform=replay,unique_valid=len(eligible),
                unique_invalid=len(cases)-len(eligible),
                distinct_vtc_sha256=len(hashes),
                first_lot_verified=(len(hashes)==len(eligible)==len(cases) and replay),
                theoretical_statistical_independence_proven=False,
                validated_points_target=200,cases=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('repeat','audit'))
    parser.add_argument('run',type=Path)
    parser.add_argument('--timeout',type=int,default=60)
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    if args.action=='repeat':
        if not 1<=args.timeout<=120:
            parser.error('Timeout must be between 1 and 120 s')
        return repeat(args.run.resolve(),args.timeout)
    if not args.output:
        parser.error('Audit requires a new --output directory')
    result = audit(args.run.resolve())
    target = new_directory(args.output)
    atomic_text(target/'audit.json',json.dumps(result,indent=2,allow_nan=False)+'\n')
    verb = 'VERIFIED' if result['first_lot_verified'] else 'INCONCLUSIVE'
    print(f'{result["mode"]}: {verb} ({result["unique_valid"]} distinct valid seeds)')
    return int(not result['first_lot_verified'])


if __name__=='__main__':
    raise SystemExit(main())
