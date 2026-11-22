"""Validate DC traces and measure the smaller butterfly lobe for a 6T cell."""

import numpy as np


SQRT2 = np.sqrt(2.)
# Numerical resolution of wrdata at volt-scale values, not a stability margin.
TRACE_EPS_V = 1e-7


def read_vtc(path, vdd, step):
    with path.open() as stream:
        if stream.readline().lower().split() != ['v-sweep','v(in)','v(out_l)','v(out_r)']:
            raise ValueError('Unexpected ngspice VTC columns')
        data = np.loadtxt(stream)
    expected = np.arange(round(vdd/step)+1)*step
    if (data.shape != (len(expected),4) or not np.all(np.isfinite(data))
            or not np.allclose(data[:,0],expected,rtol=0,atol=TRACE_EPS_V)
            or not np.allclose(data[:,1],expected,rtol=0,atol=TRACE_EPS_V)):
        raise ValueError('Incomplete, nonfinite or discontinuous DC sweep')
    return data[:,1:]


def butterfly(vin, left, right):
    """Intersect the piecewise-linear VTCs, then maximize each enclosed lobe."""
    vin, left, right = map(np.asarray,(vin,left,right))
    if (vin.ndim!=1 or len(vin)<3 or left.shape!=vin.shape or right.shape!=vin.shape
            or not np.all(np.isfinite([vin,left,right])) or np.any(np.diff(vin)<=0)
            or any(np.any(np.diff(v)>TRACE_EPS_V) for v in (left,right))):
        raise ValueError('Invalid or nonmonotone VTCs')
    lx, ly = (vin-left)/SQRT2, (vin+left)/SQRT2
    rx, ry = ((right-vin)/SQRT2)[::-1], ((right+vin)/SQRT2)[::-1]
    low, high = max(lx[0],rx[0]),min(lx[-1],rx[-1])
    if not low<high or np.any(np.diff(lx)<=0) or np.any(np.diff(rx)<=0):
        raise ValueError('No common unambiguous butterfly domain')
    nodes = np.union1d(lx,rx)
    nodes = nodes[(nodes>=low)&(nodes<=high)]
    gap = np.interp(nodes,lx,ly)-np.interp(nodes,rx,ry)
    significant = np.flatnonzero(np.abs(gap)>TRACE_EPS_V)
    if len(significant)<2 or np.sign(gap[significant[0]])==np.sign(gap[significant[-1]]):
        raise ValueError('Butterfly endpoint signs are ambiguous')
    # Hold VTCs can meet at rails to within the decimal precision of wrdata.
    # A rail root requires both curves to agree there, not just a small gap
    # somewhere near the end of the common domain.
    rail_u = (vin[-1]-vin[0])/SQRT2
    left_rail = abs(gap[0])<=TRACE_EPS_V and abs(low+rail_u)<=TRACE_EPS_V
    right_rail = abs(gap[-1])<=TRACE_EPS_V and abs(high-rail_u)<=TRACE_EPS_V
    # A tangent away from the expected intersections can hide a collapsed
    # lobe at the current resolution. Preserve it for a finer convergence test.
    neighbors = zip(significant,significant[1:])
    bounds = [float(low)] if left_rail else []
    for a,b in neighbors:
        if gap[a]*gap[b]>0:
            if b>a+1:
                raise ValueError('Near-tangent butterfly needs a finer sweep')
            continue
        if b>a+2:
            raise ValueError('Coincident butterfly segments need a finer sweep')
        if b==a+2:
            bounds.append(float(nodes[a+1]))
        else:
            bounds.append(float(nodes[a]-gap[a]*(nodes[b]-nodes[a])/(gap[b]-gap[a])))
    if right_rail:
        bounds.append(float(high))
    if len(bounds)==1 and ((significant[0]>0 and not left_rail) or
                           (significant[-1]<len(nodes)-1 and not right_rail)):
        raise ValueError('An endpoint intersection is unresolved')
    if len(bounds)==1:
        return dict(classification='MONOSTABLE_ZERO',snm_v=0.,intersection_u_v=bounds,lobes_v=[])
    if len(bounds)!=3:
        raise ValueError(f'Ambiguous butterfly with {len(bounds)} intersections')
    lobes = []
    for a,b in zip(bounds,bounds[1:]):
        inside = gap[(nodes>a)&(nodes<b)]
        if not inside.size:
            raise ValueError('An enclosed lobe is unresolved')
        lobes.append(float(np.max(np.abs(inside))/SQRT2))
    return dict(classification='BISTABLE',snm_v=min(lobes),intersection_u_v=bounds,lobes_v=lobes)


def statistics(values, *, draws=10000, seed=20261120):
    """Summarize the measured distribution and a percentile bootstrap mean CI."""
    a = np.asarray(values,dtype=float)
    if a.ndim!=1 or not a.size or not np.all(np.isfinite(a)) or np.any(a<0):
        raise ValueError('Expected finite nonnegative SNM values in volts')
    rng = np.random.default_rng(seed)
    ci = np.quantile(rng.choice(a,size=(draws,len(a))).mean(axis=1),[.025,.975]) if len(a)>1 else None
    return dict(count=len(a),zero_count=int(np.count_nonzero(a==0)),mean_v=float(a.mean()),
                sample_std_v=float(a.std(ddof=1)) if len(a)>1 else None,
                min_v=float(a.min()),max_v=float(a.max()),median_v=float(np.median(a)),
                percentiles_v=dict(zip(('p05','p25','p75','p95'),map(float,np.quantile(a,[.05,.25,.75,.95])))),
                mean_ci95_v=None if ci is None else ci.tolist(),
                bootstrap=dict(method='percentile',draws=draws,seed=seed),
                ci_interpretation='Uncertainty of the mean for this sampled condition, not a yield estimate')
