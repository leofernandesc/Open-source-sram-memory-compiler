#!/usr/bin/env python3
"""Audit the archived tt_mm butterflies without running SPICE or editing checkpoints."""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import re

import numpy as np

from phase3_snm_measure import SQRT2, butterfly, read_vtc, statistics
from run_phase3_eco_pex import new_directory, pinned, sha256
from run_phase3_snm import ROOT, checked_attempt, nominal_deck, reported_seed


REJECTED = {30005, 30021, 30053, 30090, 30148, 30192}
ROUNDING = re.compile(r'[+-]?\d+\.(\d+)e([+-]\d+)', re.I)


def export_resolution(path):
    """Maximum half-ulp per output from ngspice's printed decimal literals."""
    exponents = [set(), set()]
    with path.open() as stream:
        next(stream)
        for row in stream:
            for seen, token in zip(exponents, row.split()[2:]):
                match = ROUNDING.fullmatch(token)
                if not match:
                    raise ValueError('Unknown precision of a VTC decimal literal')
                seen.add(int(match[2])-len(match[1]))
    return tuple(0.5*10.0**max(seen) for seen in exponents)


def composition(x, left, right):
    # R(L(x))-x is piecewise affine. Add the preimages of R's mesh
    # vertices wherever L is strictly decreasing. Plateaus add no knots.
    knots = [x]
    for i in np.flatnonzero(np.diff(left)<0):
        lo, hi = x.searchsorted([left[i+1], left[i]])
        if hi>lo:
            y = x[lo:hi]
            knots.append(x[i]+(left[i]-y)*(x[i+1]-x[i])/(left[i]-left[i+1]))
    k = np.unique(np.concatenate(knots))
    return k, np.interp(np.interp(k,x,left),x,right)-k


def crossing_brackets(x, left, right, eps):
    """Certify crossings of the rail-bounded linear interpolants under print rounding."""
    k, gap = composition(x,left,right)
    e_l,e_r = eps
    dx = np.diff(x)
    l_slope,r_slope = np.diff(left)/dx,np.diff(right)/dx
    # Lipschitz propagation of the independent output rounding errors.
    roundoff = 32*np.finfo(float).eps*max(1.,x[-1])
    uncertainty = e_r+max(abs(r_slope))*e_l+roundoff
    certain = np.where(abs(gap)>uncertainty,np.sign(gap),0)
    anchors = np.unique(np.r_[0,np.flatnonzero(certain),len(k)-1])
    weak_rail = {index for index in (0,len(k)-1) if certain[index]==0}
    # The passive DC supply bounds imply h(0)>=0 and h(VDD)<=0.
    certain[0],certain[-1] = 1,-1
    brackets = []
    for a,b in zip(anchors[:-1],anchors[1:]):
        if certain[a]==certain[b]:
            if b!=a+1 or a in weak_rail or b in weak_rail:
                raise ValueError('An ambiguous interior segment may hide a tangency or a crossing')
            continue
        lo,hi = k[a],k[b]
        # Move past portions of the first and last affine pieces whose
        # nominal gap already exceeds the enclosure on rounding error.
        if a not in weak_rail:
            lo += (k[a+1]-lo)*(gap[a]-certain[a]*uncertainty)/(gap[a]-gap[a+1])
        if b not in weak_rail:
            hi -= (hi-k[b-1])*(gap[b]-certain[b]*uncertainty)/(gap[b]-gap[b-1])
        start = max(0,x.searchsorted(lo,side='right')-1)
        stop = max(start+1,x.searchsorted(hi,side='left'))
        y0,y1 = np.interp([hi,lo],x,left)+np.array([-e_l,e_l])
        r_start = max(0,x.searchsorted(y0,side='left')-1)
        r_stop = min(len(dx),max(r_start+1,x.searchsorted(y1,side='right')))
        ls = slice(start,stop)
        rs = slice(r_start,r_stop)
        dl = np.array([min(l_slope[ls]-2*e_l/dx[ls]),max(l_slope[ls]+2*e_l/dx[ls])])
        dr = np.array([min(r_slope[rs]-2*e_r/dx[rs]),max(r_slope[rs]+2*e_r/dx[rs])])
        derivatives = np.outer(dl,dr)-1
        if ((certain[a]>0 and derivatives.max()>=-roundoff)
                or (certain[a]<0 and derivatives.min()<=roundoff)):
            raise ValueError('A sign-changing bracket lacks a certified monotonic crossing')
        brackets.append((a,b,float(lo),float(hi)))
    if len(brackets) not in (1,3):
        raise ValueError(f'Unexpected count of certified crossings: {len(brackets)}')
    roots = []
    for a,b,_,_ in brackets:
        direction = int(certain[b])
        roots.append(float(np.interp(0.,gap[a:b+1]*direction,k[a:b+1])))
    return np.array(roots), [[lo,hi] for _,_,lo,hi in brackets], float(uncertainty)


def certify(x, left, right, eps):
    if any(np.any(np.diff(v)>0) or np.any((v<0)|(v>x[-1])) for v in (left,right)):
        raise ValueError('VTC not monotonically descending within the DC supply rails')
    roots,brackets,uncertainty = crossing_brackets(x,left,right,eps)
    lx,ly = (x-left)/SQRT2,(x+left)/SQRT2
    rx,ry = ((right-x)/SQRT2)[::-1],((right+x)/SQRT2)[::-1]
    nodes = np.union1d(lx,rx)
    nodes = nodes[(nodes>=max(lx[0],rx[0])) & (nodes<=min(lx[-1],rx[-1]))]
    gap = np.interp(nodes,lx,ly)-np.interp(nodes,rx,ry)
    result = dict(intersection_vin_v=roots.tolist(),brackets_v=brackets,
                  composition_uncertainty_v=uncertainty,rounding_v=eps,
                  rotated_endpoint_gaps_v=[float(gap[0]),float(gap[-1])])
    if len(roots)==1:
        return dict(result,verdict='PHYSICAL_FAILURE',snm_v=0.,lobes_v=[])
    u = (roots-np.interp(roots,x,left))/SQRT2
    lobes = []
    for a,b in zip(u,u[1:]):
        inside = abs(gap[(nodes>a)&(nodes<b)])/SQRT2
        if not inside.size or inside.max()<=max(uncertainty, sum(eps)):
            raise ValueError('A closed lobe has no resolved positive height')
        lobes.append(float(inside.max()))
    return dict(result,verdict='VALID',snm_v=min(lobes),lobes_v=lobes)


def inspect(mode, path, published):
    manifest_path = path/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    config = manifest['config']
    if (manifest['scope']!='SCHEMATIC_ONLY' or manifest['state']!='PROVISIONAL'
            or (config['profile'],config['mode'],config['vdd'],config['temp_c'],config['step'])
            != ('nominal-proposed',mode,1.8,27.,.001)
            or manifest['models']['sections']['tt_mm']
            != dict(mismatch=1,global_process=0,fet_parameters='parameters_fet_tt.spice')):
        raise ValueError(f'Unrecognized campaign domain: {path}')
    for name,digest in manifest['sources'].items():
        pinned(ROOT/name,digest)
    with (published/'attempts.csv').open(newline='') as stream:
        index = list(csv.DictReader(stream))
    cases = {c['id']:c for c in config['cases']}
    if len({row['seed'] for row in index})!=len(index) or len(index)!=(200 if mode=='hold' else 206):
        raise ValueError('Duplicate or incomplete published attempts')
    measured, archived, entries = [], [], []
    for row in index:
        case = cases[row['id']]
        attempt = path/row['attempt']
        entry = checked_attempt(path,case,attempt)
        log = (attempt/'ngspice.log').read_text()
        if (any(str(entry[key])!=row[key] for key in ('seed','corner','status','attempt'))
                or entry['corner']!='tt_mm' or entry['ngspice_returncode']!=0
                or (attempt/'bench.spice').read_text()!=nominal_deck(case,config)
                or reported_seed(log)!=case['seed']
                or not re.search(r'(?m)^No\. of Data Rows\s*:\s*1801\s*$',log)
                or not re.search(r'(?m)^ngspice-\S+ done\s*$',log)):
            raise ValueError(f'Checkpoint disagrees with the campaign export: {attempt}')
        vtc_path = attempt/'vtc.dat'
        vtc = read_vtc(vtc_path,config['vdd'],config['step'])
        try:
            old = butterfly(*vtc.T)['snm_v']
        except ValueError as error:
            old = None
            if (case['seed'] not in REJECTED or str(error)!=entry.get('error')
                    or str(error)!=row['error'] or entry['status']!='ERROR'):
                raise ValueError(f'Unreproduced original rejection: {attempt}') from error
        if old is not None:
            if entry['status']!='MEASURED' or not np.isclose(old,entry['snm_v'],atol=1e-14,rtol=0):
                raise ValueError(f'Original SNM differs from checkpoint: {attempt}')
            archived.append(old)
        x = np.arange(len(vtc))*config['step']
        try:
            audit = certify(x,*vtc[:,1:].T,export_resolution(vtc_path))
        except ValueError as error:
            audit = dict(verdict='NUMERICALLY_UNRESOLVED',snm_v=None,reason=str(error))
        if audit['snm_v'] is not None:
            measured.append(audit['snm_v'])
        entries.append(dict(seed=case['seed'],original_status=entry['status'],original_snm_v=old,
                            original_error=entry.get('error'),attempt=row['attempt'],
                            vtc_sha256=entry['artifacts']['vtc.dat'],point_count=len(vtc),**audit))
    old_result = statistics(archived)
    largest_difference = max((abs(e['snm_v']-e['original_snm_v']) for e in entries
                             if e['snm_v'] is not None and e['original_snm_v'] is not None),default=None)
    summary = dict(domain={k:v for k,v in config.items() if k!='cases'},
                   attempts=len(entries),classification=dict(Counter(e['verdict'] for e in entries)),
                   manifest_sha256=sha256(manifest_path),archive_index_sha256=sha256(published/'attempts.csv'),
                   historical_summary_sha256=sha256(published/'summary.json'),
                   sources_sha256=manifest['sources'],model_sections=manifest['models']['sections'],
                   historical=old_result,offline_revised=statistics(measured) if measured else None,
                   max_prior_valid_delta_v=largest_difference)
    return dict(summary=summary,entries=entries)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    result = {mode:inspect(mode,args.build/f'snm_nominal_{mode}_batch01_20261120',
                           args.build/f'snm_campaign_results_20261120/{mode}')
              for mode in ('hold','read')}
    if {e['seed'] for e in result['read']['entries'] if e['original_status']=='ERROR'}!=REJECTED:
        raise ValueError('Replayed rejection set differs from the historical campaign')
    out = new_directory(args.output)
    payload = dict(schema_version=1,method='rail-bounded piecewise-linear composition with decimal rounding',
                   simulator_invocations=0,analyzer_sha256=sha256(Path(__file__)),modes=result)
    (out/'audit.json').write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps({mode:entry['summary'] for mode,entry in result.items()},indent=2))


if __name__=='__main__':
    main()
