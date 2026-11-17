"""Partial invariant observers. No enable deadline or external observation policy."""
import math
import numpy as np
from run_phase2_startup_review import levels
from analyze_phase2_extension_timing import crossing, valid

REFERENCES = {'stimulus', 'clock_public', 'clock_local', 'legacy_fixture', 'test_fixture'}


def interval(times_ns, values, expected, window):
    """A fixed diagnostic interval, not an approved A gate or a settling search."""
    if set(window) != {'reference', 'start_ns', 'end_ns'} or window['reference'] not in REFERENCES:
        raise ValueError('Unsupported/data-dependent temporal reference')
    lo, hi = window['start_ns'], window['end_ns']
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (lo, hi)) or lo >= hi:
        raise ValueError('Empty/invalid window')
    t, v = np.asarray(times_ns), np.asarray(values)
    if (t.ndim != 1 or v.shape != t.shape or not len(t) or expected not in (0, 1)
            or not np.all(np.isfinite(t)) or not np.all(np.isfinite(v)) or not np.all(np.diff(t)>0)
            or t[0] > lo or t[-1] < hi):
        raise ValueError('Incomplete/invalid interval evidence')
    mask = (t >= lo) & (t < hi)
    if np.count_nonzero(mask) < 2:
        raise ValueError('Empty sampled window')
    ok = levels(v[mask], expected)
    bad = mask & ~valid(v, expected)
    return dict(status='PASS' if ok else 'FAIL', samples=int(np.sum(mask)), expected=expected,
                first_bad_ns=float(t[np.flatnonzero(bad)[0]]) if np.any(bad) else None,
                observed_min_v=float(np.min(v[mask])), observed_max_v=float(np.max(v[mask])), window=window)


def retention(data, records, vectors, probes, state, stop_ns):
    """Q must not change before the next capture, including writes, idle and masks.

    Start at the *scheduled* previous readback (not at measured DATA/Q settling).
    The unqualified capture-to-readback gaps remain explicit in the parent profile.
    """
    t = data[:, 0]*1e9
    reads = [r for r in records if r['operation']=='read']
    observations = []
    for i, r in enumerate(reads):
        nxt = reads[i+1] if i+1 < len(reads) else None
        for bit in range(8):
            hi = stop_ns
            if nxt:
                clock = data[:, vectors.index(state['capture_clocks'][bit])+1]
                # Same local-edge locator as the Phase 2 observer, not a DATA deadline.
                hi = crossing(t, clock, .9, nxt['fall_ns']-.5, nxt['fall_ns']+1)
            observed = interval(t, data[:, vectors.index(probes[f'REG_Q{bit}'])+1],
                                (r['expected']>>bit)&1,
                                dict(reference='clock_local' if nxt else 'stimulus',
                                     start_ns=r['sample_ns'], end_ns=hi))
            observations.append(dict(property='A04', cycle=r['cycle'], bit=bit,
                identity=('A04', 'internal_retention', r['cycle'], r['row'], bit, 'REG_Q', 'sample_to_capture'),
                source='Q from scheduled readback until next local capture; partial interval', **observed))
    return observations
