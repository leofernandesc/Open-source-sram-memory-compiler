#!/usr/bin/env python3
"""Compare Magic RC and C-only exports of the same flattened extraction."""

import argparse
from collections import defaultdict
import csv
import json
import math
from pathlib import Path

from phase3_rc_characterization import idealize_supply_mesh
from phase3_rc_extraction import EXPECTED_PINS, logical_cards, sha256
from phase3_rc_probe import reference_node_map


FF_TOLERANCE = 0.0001
REL_TOLERANCE = 0.00001
SUFFIX_TO_FF = {'a': .001, 'f': 1., 'p': 1e3, 'n': 1e6, 'u': 1e9}


def capacitances_ff(spice, mapping):
    totals = defaultdict(list)
    for line in logical_cards(spice):
        if line[0].upper() != 'C':
            continue
        _, a, b, literal, *_ = line.split()
        suffix = literal[-1].lower()
        ff = (float(literal[:-1]) * SUFFIX_TO_FF[suffix] if suffix in SUFFIX_TO_FF
              else float(literal) * 1e15)
        if not math.isfinite(ff) or ff < 0:
            raise ValueError(f'Invalid capacitance {literal}')
        a, b = mapping.get(a, a), mapping.get(b, b)
        if ff and a != b:
            totals[tuple(sorted((a, b)))].append(ff)
    return {pair: math.fsum(caps) for pair, caps in totals.items()}


def compare(rc, c_only, *, expected_mos=1493):
    header = ['.subckt', 'phase3_rc_flat', *EXPECTED_PINS]
    for spice, allowed in ((rc, 'XRC'), (c_only, 'XC')):
        cards = logical_cards(spice)
        if (not cards or cards[0].split() != header or
                cards[-1].split()[0].lower() != '.ends' or
                any(line[0].upper() not in allowed for line in cards[1:-1])):
            raise ValueError('Expected matching flat macro ports and supported element cards')
    # Merge the rail subnodes, then use corresponding MOS terminals and the
    # remaining resistors to identify the logical net of each signal cap.
    # Cap-only conductors without a MOS or port retain their Magic node names.
    ideal, _ = idealize_supply_mesh(rc)
    mapping = reference_node_map(ideal, c_only, expected_mos=expected_mos)
    if any(mapping.get(pin, pin) != pin for pin in EXPECTED_PINS):
        raise ValueError('Capacitance reference disagrees with the public port map')
    exported = capacitances_ff(ideal, mapping)
    reference = capacitances_ff(c_only, {})
    return [{
        'net_a': pair[0], 'net_b': pair[1],
        'c_only_ff': reference.get(pair, 0.),
        'rc_ff': exported.get(pair, 0.),
        'rc_minus_c_only_ff': exported.get(pair, 0.) - reference.get(pair, 0.),
        'match': math.isclose(exported.get(pair, 0.), reference.get(pair, 0.),
                              rel_tol=REL_TOLERANCE, abs_tol=FF_TOLERANCE),
    } for pair in sorted(reference.keys() | exported.keys())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rc', type=Path, required=True)
    parser.add_argument('--c-only', type=Path, required=True)
    parser.add_argument('--expected-mos', type=int, default=1493,
                        help='device count from the verified layout')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.expected_mos < 1:
        parser.error('--expected-mos must be positive')
    rows = compare(args.rc.read_text(), args.c_only.read_text(), expected_mos=args.expected_mos)
    if not rows:
        raise ValueError('No capacitances to audit')
    bad = sum(not row['match'] for row in rows)
    summary = {
        'status': 'FAIL_CAPACITANCE_CONSERVATION' if bad else 'PASS_CAPACITANCE_CONSERVATION',
        'scope': 'Net-pair totals after merging resistive components; same extraction geometry and rules',
        'source_sha256': {str(p): sha256(p) for p in (args.rc, args.c_only)},
        'expected_mos': args.expected_mos,
        'absolute_tolerance_ff': FF_TOLERANCE, 'relative_tolerance': REL_TOLERANCE,
        'pairs': len(rows), 'mismatched_pairs': bad,
        'c_only_total_ff': math.fsum(row['c_only_ff'] for row in rows),
        'rc_total_ff': math.fsum(row['rc_ff'] for row in rows),
    }
    args.output.mkdir(parents=True, exist_ok=False)
    with (args.output / 'net_pairs.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = json.dumps(summary, indent=2) + '\n'
    (args.output / 'summary.json').write_text(result)
    print(result, end='')
    return int(bool(bad))


if __name__ == '__main__':
    raise SystemExit(main())
