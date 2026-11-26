#!/usr/bin/env python3
"""Summarize nominal bit/polarity coverage from the pinned v6 tCLK pilot."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PEX = 'a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f'


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def summarize(source: Path) -> dict:
    data = json.loads(source.read_text())
    assert data['schema'] == 'phase3-v6-tclk-to-data-pilot-v1'
    assert data['status'] == 'PROVISIONAL' and data['qualification'] == 'NOT_CHARACTERIZED'
    assert data['conditions']['pex_sha256'] == PEX
    assert set(data['corners']) == {'TT', 'SS', 'FF'}
    corners = {}
    for corner, report in data['corners'].items():
        assert report['status'] == 'PROVISIONAL'
        for relative, expected in report['inputs'].items():
            path = ROOT / relative
            assert path.is_file() and sha(path) == expected, f'{corner}: input changed: {relative}'
        measured = defaultdict(list)
        stable = []
        for event in report['events']:
            assert len(event['lanes']) == 8
            for lane in event['lanes']:
                key = f'DATA{lane["bit"]}/{"rise" if lane["expected"] else "fall"}'
                if lane['status'] == 'MEASURED':
                    measured[key].append(lane['tclk_to_data_ns'])
                else:
                    assert lane['status'] == 'NOT_CHARACTERIZED'
                    stable.append({'cycle': event['cycle'], 'bit': lane['bit'],
                                   'expected': lane['expected'], 'reason': lane['reason']})
        arcs = {}
        for bit in range(8):
            for polarity in ('rise', 'fall'):
                key = f'DATA{bit}/{polarity}'
                samples = measured[key]
                arcs[key] = {'count': len(samples), 'min_ns': min(samples) if samples else None,
                             'mean_ns': sum(samples) / len(samples) if samples else None,
                             'max_ns': max(samples) if samples else None}
        assert sum(a['count'] for a in arcs.values()) == report['measured_transitions'] == 48
        assert len(stable) == report['not_characterized_lanes'] == 24
        corners[corner] = {'arcs': arcs, 'arcs_with_transition': sum(a['count'] > 0 for a in arcs.values()),
                           'measured_events': 48, 'stable_events': stable,
                           'source_inputs': report['inputs']}
    return {'schema': 'phase3-v6-tclk-arc-coverage-v1', 'status': 'PROVISIONAL',
            'electrical_qualification': 'NOT_CHARACTERIZED', 'pex_sha256': PEX,
            'source_report_sha256': sha(source), 'analyzer_sha256': sha(Path(__file__)),
            'corners': corners}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=ROOT / 'build/phase3/timing_v6_tclk_to_data.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('refusing to overwrite existing report')
    result = summarize(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({corner: {'arcs_with_transition': report['arcs_with_transition'],
                               'measured_events': report['measured_events'],
                               'stable_events': len(report['stable_events'])}
                      for corner, report in result['corners'].items()}, indent=2))


if __name__ == '__main__':
    main()
