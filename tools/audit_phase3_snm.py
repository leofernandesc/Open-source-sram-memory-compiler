#!/usr/bin/env python3
"""Audit historical SNM CSVs and remeasure the sealed pilot DC traces offline."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from phase3_rc_extraction import ROOT, sha256
from phase3_snm_measure import butterfly, read_vtc, statistics
from run_phase3_snm import design, paired_snm, reported_seed, result_for
from run_phase3_eco_pex import new_directory, pinned


HISTORY = {
    'hold': ROOT/'sims/bitcell_hold_snm_mismatch_sf_1p62_minus40.csv',
    'read': ROOT/'sims/bitcell_read_snm_mismatch_sf_1p62_125.csv',
}


def historical(mode, temp_c):
    path = HISTORY[mode]
    with path.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    indexed = {}
    for i,row in enumerate(rows,1):
        v = float(row['snm_v'])
        conditions = [float(row[k]) for k in ('vdd_v','temp_c','wpu_um','wpd_um','wacc_um')]
        if (int(row['sample'])!=i or int(row['seed'])!=1000+i or row['mode']!=mode or row['corner']!='sf_mm'
                or conditions!=[1.62,temp_c,.42,1.26,.60] or not np.isfinite(v) or v<0
                or abs(float(row['snm_mv'])-v*1000)>.000501):
            raise ValueError(f'Unexpected historical record {i} in {path}')
        indexed[int(row['seed'])] = v
    if len(indexed)!=200:
        raise ValueError(f'Expected 200 historical rows in {path}')
    return indexed


def pilot(output, archive_sources, mode):
    manifest = output/'manifest.json'
    receipt = json.loads(manifest.read_text())
    cfg = receipt['config']
    if cfg!=design('legacy-pilot',mode,1001,5):
        raise ValueError('Expected five predeclared pilot cases')
    for name,h in receipt['sources'].items():
        source = ROOT/name
        pinned(source if sha256(source)==h else archive_sources/source.name,h)
    results, curves = {}, {}
    for case in cfg['cases']:
        attempt = result_for(output,case)
        if not attempt or attempt['status']!='MEASURED':
            raise ValueError(f'Missing sealed VTC: {case["id"]}')
        work = output/attempt['attempt']
        if (attempt['ngspice_returncode']!=0 or
                reported_seed((work/'ngspice.log').read_text())!=case['seed']):
            raise ValueError(f'Unconfirmed simulator or seed: {case["id"]}')
        vin,left,right = read_vtc(work/'vtc.dat',cfg['vdd'],cfg['step']).T
        measured = butterfly(vin,left,right)
        coarse = butterfly(vin[::2],left[::2],right[::2])
        trip = [float(np.interp(0,vin-v,vin)) for v in (left,right)]
        results[case['id']] = {**case,**measured,'trip_v':trip,'seed_confirmed':True,
                               'coarsened_snm_v':coarse['snm_v'],
                               'legacy_snm_v':paired_snm(vin,left,right),
                               'trace_sha256':attempt['artifacts']['vtc.dat'],'elapsed_s':attempt['elapsed_s']}
        curves[case['id']] = (vin,left,right)
    hashes = {key:r['trace_sha256'] for key,r in results.items()}
    return dict(manifest_sha256=sha256(manifest),cases=results,
                repeated_seed_same_trace=hashes['reference']==hashes['repeat'],
                different_seed_different_trace=hashes['reference']!=hashes['different'],
                deterministic_different_seeds_same_trace=hashes['deterministic_a']==hashes['deterministic_b'],
                vdd_v=cfg['vdd'],temp_c=cfg['temp_c']), curves


def audit(args):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt

    combined = {}
    fig, axes = plt.subplots(2,2,figsize=(10,7),layout='constrained')
    for index,(mode,temp_c) in enumerate((('hold',-40.),('read',125.))):
        result, curves = pilot(getattr(args,mode),args.initial_sources,mode)
        old = historical(mode,temp_c)
        against = {tag:dict(seed=result['cases'][tag]['seed'],
                            historical_v=old[result['cases'][tag]['seed']],
                            difference_v=result['cases'][tag]['snm_v']-old[result['cases'][tag]['seed']])
                   for tag in ('reference','different')}
        combined[mode] = dict(status='PROVISIONAL',historical_count=len(old),historical_sha256=sha256(HISTORY[mode]),
                              historical_statistics=statistics(list(old.values())),
                              pilot=result,against_historical=against,qualified_for_nominal_count=0)
        ax = axes[index,0]
        ax.hist([v*1000 for v in old.values()],bins='auto',color='#246576')
        ax.set(xlabel='SNM (mV)',ylabel='Amostras',
               title=f'{mode.title()} histórico · sf_mm · {temp_c:g} °C · N=200')
        ax = axes[index,1]
        for tag,color in (('reference','#246576'),('different','#b65922')):
            v,l,r = (arr*1000 for arr in curves[tag])
            ax.plot(v,l,color=color,label=f'seed {result["cases"][tag]["seed"]}')
            ax.plot(r,v,color=color,linestyle='--')
        ax.legend(loc='best',frameon=False)
        ax.set(xlabel='Nó de armazenamento Q (mV)',ylabel='Nó QB (mV)',
               title=f'{mode.title()} · borboletas do piloto')
        ax.set_aspect('equal')
    dest = new_directory(args.output)
    fig.savefig(dest/'snm_historico_e_piloto.png',dpi=160)
    plt.close(fig)
    evidence = dict(schema_version=1, status='PROVISIONAL',
                    scope='Separate schematic SF local mismatch screening conditions',
                    reanalysis_sha256=sha256(Path(__file__)),extractor_sha256=sha256(Path(__file__).with_name('phase3_snm_measure.py')),
                    modes=combined)
    (dest/'audit.json').write_text(json.dumps(evidence,indent=2,allow_nan=False)+'\n')
    print(dest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('hold','read','initial-sources','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    audit(parser.parse_args())


if __name__ == '__main__':
    main()
