#!/usr/bin/env python3
"""Resumable, per-seed schematic SNM measurements in the project EDA environment."""

import argparse
import csv
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from phase3_rc_extraction import ROOT, sha256
from phase3_snm_measure import butterfly, read_vtc, statistics
from run_digital_regression import atomic_text
from run_phase2_extracted_access import model_closure
from run_phase3_eco_pex import new_directory, ngspice_limits, pinned

sys.path.insert(0,str(ROOT/'sims'))
from run_bitcell_snm_mismatch import MODEL_LIB, deck, paired_snm


LEAF = ROOT/'release/phase1/cells/bitcell_6t/bitcell_6t.spice'
MODEL = Path(MODEL_LIB)
SOURCES = (LEAF, ROOT/'sims/run_bitcell_snm_mismatch.py',
           Path(__file__).resolve(),Path(__file__).with_name('phase3_snm_measure.py').resolve())


def design(profile, mode, seed_base, count):
    if not 1<=seed_base<2**31 or not 1<=count<=1000 or seed_base+count>2**31:
        raise ValueError('Expected positive unique ngspice seeds and a supported sample count')
    if profile=='legacy-pilot':
        rows = [('reference','sf_mm',1001),('repeat','sf_mm',1001),('different','sf_mm',1002),
                ('deterministic_a','sf',1001),('deterministic_b','sf',1002)]
        return dict(profile=profile,mode=mode,vdd=1.62,temp_c=-40. if mode=='hold' else 125.,
                    step=.001,cases=[dict(id=tag,corner=corner,seed=seed) for tag,corner,seed in rows])
    if profile!='nominal-proposed' or count<200:
        raise ValueError('Proposed nominal series requires at least 200 predeclared seeds')
    return dict(profile=profile,mode=mode,vdd=1.8,temp_c=27.,step=.001,
                cases=[dict(id=str(seed),corner='tt_mm',seed=seed) for seed in range(seed_base,seed_base+count)])


def model_config(config):
    source = MODEL.read_text()
    cards = {}
    for corner in sorted({item['corner'] for item in config['cases']}):
        matches = re.findall(rf'^\.lib[ \t]+{corner}\s*\n(.*?)^\.endl(?:[ \t]+\w+)?[ \t]*$',
                             source,re.M|re.S|re.I)
        mm = int(corner.endswith('_mm'))
        fet = f'parameters_fet_{corner.split("_")[0]}.spice'
        if (len(matches)!=1 or not re.search(rf'(?im)^\.param\s+mc_mm_switch={mm}$',matches[0])
                or not re.search(r'(?im)^\.param\s+mc_pr_switch=0$',matches[0]) or fet not in matches[0]):
            raise ValueError(f'Unexpected statistical switches for {corner}')
        cards[corner] = dict(mismatch=mm,global_process=0,fet_parameters=fet)
    return dict(path=str(MODEL),resolved=str(MODEL.resolve()),sections=cards,sha256=model_closure(MODEL))


def nominal_deck(case, config):
    """Opening the feedback exposes two independent VTCs of the same 6T topology."""
    template = deck(config['mode'],case['corner'],config['vdd'],config['temp_c'],case['seed'],
                    Path('vtc.dat'),.42,1.26,.60,config['step'])
    parts = []
    names = {'XMPL','XMNL','XMPR','XMNR','XMAL','XMAR'}
    for line in LEAF.read_text().splitlines():
        card = line.split(maxsplit=5)
        if not card or card[0] not in names:
            continue
        name, drain, gate, source, bulk, model = card
        names.remove(name)
        nodes = {'Q':'out_l','QB':'out_r','VSS':'0','BL':'vdd','BLB':'vdd','VDD':'vdd',
                 'WL':'vdd' if config['mode']=='read' else '0'}
        parts.append(' '.join((name,nodes[drain],'in' if gate in ('Q','QB') else nodes[gate],
                               nodes[source],nodes[bulk],model)))
    if names:
        raise ValueError('Missing canonical 6T transistors')
    template = template.replace('* Two independent inverter VTCs for mismatch butterfly SNM.',
                                '* Open-loop VTCs from the canonical 6T leaf; BL/BLB clamped at VDD.')
    return re.sub(r'^XPU_L .*?^(?=\.options ngbehavior=)', '\n'.join(parts)+'\n', template, flags=re.M|re.S)


def init(args):
    config = design(args.profile,args.mode,args.seed_base,args.count)
    models = model_config(config)
    version = subprocess.run(['ngspice','--version'],check=True,timeout=10,text=True,capture_output=True)
    source_hashes = {str(p.relative_to(ROOT)):sha256(p) for p in SOURCES}
    git = subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True,check=True,timeout=10).stdout.strip()
    output = new_directory(args.output)
    receipt = dict(schema_version=1, scope='SCHEMATIC_ONLY', state='PROVISIONAL',
                   config=config, checkout_commit=git, sources=source_hashes, models=models,
                   ngspice_version=version.stdout.strip())
    (output/'manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')


def attempts(output, case):
    base = output/case['id']
    return sorted(base.glob('attempt-*'))


def checked_attempt(output, case, directory):
    path = directory/'result.json'
    if not path.is_file():
        return {**case,'status':'ERROR','error':'interrupted attempt','attempt':str(directory.relative_to(output))}
    entry = json.loads(path.read_text())
    if any(entry.get(key)!=value for key,value in case.items()):
        raise ValueError(f'Seed checkpoint identity mismatch: {path}')
    if entry['manifest_sha256']!=sha256(output/'manifest.json') or entry['attempt']!=str(path.parent.relative_to(output)):
        raise ValueError(f'Seed checkpoint manifest mismatch: {path}')
    for name,digest in entry['artifacts'].items():
        pinned(path.parent/name,digest)
    return entry


def result_for(output, case):
    previous = attempts(output,case)
    return checked_attempt(output,case,previous[-1]) if previous else None


def reported_seed(log_text):
    reported = re.search(r'(?im)^\s*seed value for random number generator is set to\s+(\d+)',log_text)
    return int(reported[1]) if reported else None


def run_case(output, candidate, config, timeout_s):
    base = output/candidate['id']
    base.mkdir(exist_ok=True)
    work = new_directory(base/f'attempt-{len(attempts(output,candidate))+1:03}')
    if config['profile']=='legacy-pilot':
        text = deck(config['mode'],candidate['corner'],config['vdd'],config['temp_c'],candidate['seed'],
                    Path('vtc.dat'),.42,1.26,.60,config['step'])
    else:
        text = nominal_deck(candidate,config)
    (work/'bench.spice').write_text(text)
    command = ['ngspice','-n','-b','bench.spice']
    summary = {**candidate,'attempt':str(work.relative_to(output)),'command':command,
               'timeout_s':timeout_s,'manifest_sha256':sha256(output/'manifest.json'),
               'status':'ERROR','snm_v':None}
    begin = time.monotonic()
    try:
        with (work/'ngspice.log').open('x') as log:
            proc = subprocess.run(command,cwd=work,stdout=log,stderr=subprocess.STDOUT,check=False,timeout=timeout_s,
                                  env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'},
                                  preexec_fn=ngspice_limits)
        summary['ngspice_returncode'] = proc.returncode
        log_text = (work/'ngspice.log').read_text(errors='replace')
        summary['seed_reported'] = reported_seed(log_text)
        if (proc.returncode or not re.search(r'^ngspice-\S+ done\s*$',log_text,re.M)
                or re.search(r'dc simulation aborted|analysis aborted|no convergence|timestep too small|^\s*(?:fatal|error):',
                             log_text,re.I|re.M)):
            raise ValueError('Failed or incomplete DC analysis')
        if summary['seed_reported']!=candidate['seed']:
            raise ValueError('ngspice did not confirm the configured seed')
        curves = read_vtc(work/'vtc.dat',config['vdd'],config['step'])
        if config['profile']=='legacy-pilot':
            summary['legacy_snm_v'] = paired_snm(*curves.T)
        measured = butterfly(*curves.T)
        summary.update(status='MEASURED', **measured)
    except subprocess.TimeoutExpired:
        summary.update(status='TIMEOUT',error='ngspice timeout')
    except (OSError,ValueError,RuntimeError) as exc:
        summary.update(error=str(exc))
    summary['elapsed_s'] = time.monotonic()-begin
    summary['artifacts'] = {p.name:sha256(p) for p in work.iterdir() if p.is_file()}
    atomic_text(work/'result.json',json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(f'{candidate["id"]}: {summary["status"]}',flush=True)
    return summary['status']=='MEASURED'


def run(args):
    output = args.output.resolve()
    receipt = json.loads((output/'manifest.json').read_text())
    config = receipt['config']
    cases = config['cases']
    expected = design(config['profile'],config['mode'],cases[0]['seed'],len(cases))
    if config!=expected or model_config(config)!=receipt['models']:
        raise ValueError('Campaign design or model closure changed')
    for name,digest in receipt['sources'].items():
        pinned(ROOT/name,digest)
    version = subprocess.run(['ngspice','--version'],check=True,timeout=10,text=True,capture_output=True)
    if version.stdout.strip()!=receipt['ngspice_version']:
        raise ValueError('Simulator changed since initialization')
    if args.retry_failed and config['profile']=='legacy-pilot':
        raise ValueError('Pilot attempts are limited to one per predeclared case')
    with (output/'.run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        due = [case for case in cases if not (entry:=result_for(output,case))
               or args.retry_failed and entry['status']!='MEASURED']
        successes = [run_case(output,case,config,args.timeout) for case in due[:args.limit]]
        return int(not all(successes))


def export(output, target):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    receipt = json.loads((output/'manifest.json').read_text())
    config = receipt['config']
    rows, history = [], []
    for case in config['cases']:
        chain = [checked_attempt(output,case,p) for p in attempts(output,case)]
        history.extend(chain)
        rows.append(chain[-1] if chain else {**case,'status':'NOT_RUN'})
    target = new_directory(target)
    fields = ('id','corner','seed','status','classification','snm_v','legacy_snm_v','attempt','elapsed_s','error')
    for name,entries in (('samples.csv',rows),('attempts.csv',history)):
        with (target/name).open('x',newline='') as stream:
            writer = csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore')
            writer.writeheader()
            writer.writerows(entries)
    measured = [r['snm_v'] for r in rows if r['status']=='MEASURED']
    # A pilot pools neither repeated seeds nor the two different corners.
    data = statistics(measured) if measured and config['profile']=='nominal-proposed' else None
    info = dict(status='PROVISIONAL' if data else 'NOT_CHARACTERIZED',profile=config['profile'],mode=config['mode'],
                vdd_v=config['vdd'],temp_c=config['temp_c'],count_expected=len(rows),count_measured=len(measured),
                count_attempts=len(history),count_unrun=sum(r['status']=='NOT_RUN' for r in rows),
                count_invalid=sum(r['status'] not in ('NOT_RUN','MEASURED') for r in rows),
                manifest_sha256=sha256(output/'manifest.json'),statistics=data)
    if data:
        fig, ax = plt.subplots()
        ax.hist([v*1000 for v in measured],bins='auto')
        ax.set(xlabel='SNM (mV)',ylabel='Amostras',title=f'{config["mode"].title()} SNM · tt_mm · N={len(measured)}')
        fig.savefig(target/'snm.png',dpi=150,bbox_inches='tight')
        plt.close(fig)
    info['artifacts_sha256'] = {p.name:sha256(p) for p in target.iterdir()}
    (target/'summary.json').write_text(json.dumps(info,indent=2,allow_nan=False)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action',required=True)
    a = sub.add_parser('init')
    a.add_argument('--profile',choices=('legacy-pilot','nominal-proposed'),required=True)
    a.add_argument('--mode',choices=('hold','read'),required=True)
    a.add_argument('--seed-base',type=int,default=1001)
    a.add_argument('--count',type=int,default=200)
    b = sub.add_parser('run')
    b.add_argument('--limit',type=int,default=5)
    b.add_argument('--timeout',type=int,default=60)
    b.add_argument('--retry-failed',action='store_true')
    c = sub.add_parser('export')
    c.add_argument('--target',type=Path,required=True)
    for cmd in a,b,c:
        cmd.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if args.action=='init':
        init(args)
    elif args.action=='run':
        if not 1<=args.limit<=50 or not 1<=args.timeout<=120:
            parser.error('Use a batch of 1–50 cases and a per-case timeout of 1–120 seconds')
        return run(args)
    else:
        export(args.output.resolve(),args.target)


if __name__ == '__main__':
    raise SystemExit(main())
