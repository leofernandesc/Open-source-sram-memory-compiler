#!/usr/bin/env python3
"""Reproducible full-macro Magic distributed-RC extraction for Phase 3.

Run inside an environment with SKY130A Magic. It never updates Phase 2 data;
each attempt owns a unique output directory, including failed attempts.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

from phase2_resources import preflight


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'reports/phase2/direct_abutment_20261111/gds_v1'
GDS = BASE / 'sram_4x8.gds'
EXPECTED_GDS = '83e72aee8d45a9826751cdefd46dd062acc2a17ec0acfd33c07f218d20d8e64e'
EXPECTED_BASELINE = '89901e7e258b6955f6752163b918a296079466fa'
BASE_REF = 'origin/release/phase2-acceptance-20261111'
EXPECTED_PINS = ('ADDR[0]', 'ADDR[1]', 'CLK', 'CSb', *(f'DATA[{i}]' for i in range(8)),
                 'OEb', 'VDD', 'VSS', 'WEb')
MAGIC_RC = Path('/opt/pdks/sky130A/libs.tech/magic/sky130A.magicrc')
CRITICAL_NETS = (
    'CLK', 'CSb', 'OEb', 'WEb', 'ADDR[0]', 'ADDR[1]',
    *(f'DATA[{i}]' for i in range(8)),
    *(f'macro_core.array_and_peripherals.write_driver_{i}.{side}'
      for i in range(8) for side in ('BL', 'BLB')),
    *(f'macro_core.array_and_peripherals.wl_driver_{i}.WL' for i in range(4)),
)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for piece in iter(lambda: f.read(1024 * 1024), b''):
            h.update(piece)
    return h.hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def check_baseline():
    sha = git('rev-parse', '--verify', BASE_REF)
    if sha != EXPECTED_BASELINE:
        raise ValueError(f'Unexpected Phase 2 reference: {BASE_REF}={sha}')
    if subprocess.run(['git', 'merge-base', '--is-ancestor', sha, 'HEAD'], cwd=ROOT).returncode:
        raise ValueError('HEAD is not based on the accepted Phase 2 commit')
    state = json.loads((BASE / 'results.json').read_text())
    if state['status'] != 'PASS_GEOMETRY_LVS' or state['mos'] != 1493:
        raise ValueError('Unexpected Phase 2 physical qualification')
    for name, digest in state['artifacts'].items():
        if sha256(BASE / name) != digest:
            raise ValueError('Phase 2 artifact changed: ' + name)
    if sha256(GDS) != EXPECTED_GDS:
        raise ValueError('Selected Phase 2 GDS differs from pinned SHA-256')
    return state


def magic_script(gds, target, profile='all'):
    """Reimport GDS; optionally restrict expensive resistance extraction to named nets."""
    if profile not in ('all', 'critical_signals'):
        raise ValueError('Unsupported RC extraction profile: ' + profile)
    # TCL double-quoted paths reject unusual shell characters; GDS path is
    # repository-controlled, while output is generated under the run directory.
    for path in (gds, target):
        if any(char in str(path) for char in ('"', '\\', '\n', '$', '[', ']')):
            raise ValueError('Unsupported path character for Tcl: ' + str(path))
    # Magic 8.3.613's integrated extraction preserves VSS-to-substrate
    # connectivity on this GDS. The legacy ext2sim/extresist-all sequence
    # split the VSS resistive tree from the transistor body/source terminals.
    if profile == 'all':
        resistance = '''extract do local
extresist threshold 0
extresist tolerance 1
extresist simplify on
extresist extout on
extresist silent on
extract do resistance
extract all
puts "PHASE3_CONNECTIVITY_EXTRACTED=1"
puts "PHASE3_RESISTANCE_INTEGRATED=1"
puts "PHASE3_PROFILE=all"
puts "PHASE3_THRESHOLD=[extresist threshold]"
puts "PHASE3_TOLERANCE=[extresist tolerance]"
puts "PHASE3_SIMPLIFY=[extresist simplify]"
puts "PHASE3_EXTRESIST_COMPLETE=1"
'''
    else:
        # Keep the partial extraction profile available for comparison only.
        # Magic includes one selected net per invocation; braces protect [].
        selection = ''.join('extresist include {' + net + '}\n' for net in CRITICAL_NETS)
        resistance = f'''extract do local
extract all
puts "PHASE3_CONNECTIVITY_EXTRACTED=1"
ext2sim labels on
ext2sim
extresist threshold 0
extresist tolerance 1
extresist simplify on
extresist extout on
extresist silent on
{selection}puts "PHASE3_PROFILE={profile}"
puts "PHASE3_THRESHOLD=[extresist threshold]"
puts "PHASE3_TOLERANCE=[extresist tolerance]"
puts "PHASE3_SIMPLIFY=[extresist simplify]"
extresist all
extresist stats
puts "PHASE3_EXTRESIST_COMPLETE=1"
'''
    return f'''gds read "{gds}"
load sram_4x8_wrapper
select top cell
expand
flatten phase3_rc_flat
load phase3_rc_flat
select top cell
save phase3_rc_flat
puts "PHASE3_IMPORT_COMPLETE=1"
{resistance}
ext2spice default
ext2spice hierarchy off
ext2spice format ngspice
ext2spice subcircuits top on
ext2spice cthresh 0
ext2spice rthresh 0
ext2spice extresist on
ext2spice -o "{target}"
puts "PHASE3_EXTRACTION_COMPLETE=1"
quit -noprompt
'''


def logical_cards(text):
    result = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith('+') and result:
            result[-1] += ' ' + line[1:].strip()
        elif line and not line.startswith('*'):
            result.append(line)
    return result


def inspect_dc_supply_paths(extracted):
    """Audit power-pin connectivity to MOS terminals through DC resistances."""
    parent = {}

    def find(node):
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a, b):
        first, second = find(a), find(b)
        if first != second:
            parent[second] = first

    transistors = []
    for line in logical_cards(extracted):
        if line.startswith('.'):
            continue
        card = line.split()
        if card[0][0].upper() == 'R':
            union(card[1], card[2])
        elif card[0][0].upper() == 'X':
            transistors.append(card[1:5])
    terminals = Counter(find(node) for mos in transistors for node in mos)
    return {
        'VDD': {'mos_terminals_reachable': terminals[find('VDD')]},
        'VSS': {'mos_terminals_reachable': terminals[find('VSS')]},
        'rails_short_through_resistors': find('VDD') == find('VSS'),
    }


def inspect_netlist(path):
    cards = logical_cards(path.read_text())
    subckts = [c.split() for c in cards if c.lower().startswith('.subckt ')]
    if len(subckts) != 1 or subckts[0][1].lower() != 'phase3_rc_flat':
        raise ValueError(f'Unexpected extracted subcircuits: {subckts[:3]}')
    pins = subckts[0][2:]
    if len(pins) != len(EXPECTED_PINS) or set(pins) != set(EXPECTED_PINS):
        raise ValueError(f'Port mismatch: {pins}')
    parts = Counter(c[0][0].upper() for c in cards if c and not c.startswith('.'))
    if parts['X'] != 1493:
        raise ValueError(f'Expected 1493 extracted MOS; got {parts["X"]}')
    if parts['R'] <= 0 or parts['C'] <= 0:
        raise ValueError(f'Distributed R/C missing: R={parts["R"]}, C={parts["C"]}')
    zero_caps = 0
    positive_caps = 0
    for card in cards:
        if not card or card[0][0].upper() not in 'RC' or card.startswith('.'):
            continue
        cols = card.split()
        if len(cols) < 4 or cols[1] == cols[2]:
            raise ValueError('Invalid passive element: ' + card)
        # ngspice recognizes scientific notation, f/p/n/u suffixes, etc.
        if not re.fullmatch(r'(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+|[afpnumkMgGtT])?', cols[3]):
            raise ValueError('Invalid passive value: ' + card)
        value = float(re.match(r'(?:\d+(?:\.\d*)?|\.\d+)', cols[3]).group())
        if value < 0 or (card[0][0].upper() == 'R' and value == 0):
            raise ValueError('Nonpositive passive: ' + card)
        if card[0][0].upper() == 'C':
            zero_caps += (value == 0)
            positive_caps += (value > 0)
    if not positive_caps:
        raise ValueError('No positive parasitic capacitance')
    if not any(c.lower() == '.ends' or c.lower().startswith('.ends ') for c in cards):
        raise ValueError('Missing .ends in extracted netlist')
    return {'mos': parts['X'], 'resistors': parts['R'], 'capacitors': parts['C'],
            'zero_capacitors': zero_caps, 'positive_capacitors': positive_caps,
            'ports': pins, 'netlist_sha256': sha256(path), 'netlist_bytes': path.stat().st_size}


def run_magic(run, magic, rc, timeout, profile):
    cmd = [magic, '-dnull', '-noconsole', '-rcfile', str(rc), 'extract.tcl']
    log = run / 'magic.log'
    with log.open('wb') as out:
        try:
            proc = subprocess.run(cmd, cwd=run, stdout=out, stderr=subprocess.STDOUT,
                                  timeout=timeout, env={**os.environ, 'OMP_NUM_THREADS': '1'})
        except subprocess.TimeoutExpired as err:
            raise RuntimeError(f'Magic exceeded {timeout}s (see magic.log)') from err
    tail = log.read_text(errors='replace')
    if proc.returncode != 0 or 'PHASE3_EXTRACTION_COMPLETE=1' not in tail:
        raise RuntimeError(f'Magic extraction incomplete (exit={proc.returncode}); see {log}')
    for marker in ('PHASE3_IMPORT_COMPLETE=1', 'PHASE3_CONNECTIVITY_EXTRACTED=1',
                   'PHASE3_EXTRESIST_COMPLETE=1', 'PHASE3_THRESHOLD=0',
                   f'PHASE3_PROFILE={profile}'):
        if marker not in tail:
            raise RuntimeError(f'Magic did not confirm {marker}')
    if profile == 'all' and 'PHASE3_RESISTANCE_INTEGRATED=1' not in tail:
        raise RuntimeError('Magic did not confirm integrated resistance extraction')
    return cmd


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--magic', default='magic')
    parser.add_argument('--magic-rc', type=Path, default=MAGIC_RC)
    parser.add_argument('--timeout', type=int, default=3600)
    parser.add_argument('--profile', choices=('all', 'critical_signals'), default='all',
                        help='all: full distributed-R; critical_signals: targeted R plus all extracted C')
    parser.add_argument('--output-root', type=Path, default=ROOT / 'build/phase3/rc_runs')
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    check_baseline()
    resources = preflight(ROOT)
    rc = args.magic_rc.resolve(strict=True)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    parent = args.output_root.resolve()
    parent.mkdir(parents=True, exist_ok=True)
    run = parent / run_id
    run.mkdir(exist_ok=False)
    result = {
        'schema_version': 1, 'run_id': run_id, 'status': 'RUNNING',
        'scope': ('Full SRAM 4x8 GDS, all nets distributed RC' if args.profile == 'all'
                  else 'Full SRAM 4x8 GDS, distributed R on selected signal nets only'),
        'rc_profile': args.profile,
        'included_nets': list(CRITICAL_NETS) if args.profile == 'critical_signals' else None,
        'baseline_ref': BASE_REF, 'baseline_commit': EXPECTED_BASELINE,
        'head_commit': git('rev-parse', 'HEAD'),
        'branch': git('branch', '--show-current'),
        'working_tree_dirty': bool(git('status', '--porcelain')),
        'gds': str(GDS.relative_to(ROOT)), 'gds_sha256': EXPECTED_GDS,
        'magic_rc': str(rc), 'magic_rc_sha256': sha256(rc),
        'resources': resources, 'corner': 'NOT_CHARACTERIZED',
        'timing_power': 'NOT_CHARACTERIZED',
    }
    manifest = run / 'manifest.json'
    try:
        (run / 'extract.tcl').write_text(magic_script(GDS, run / 'extracted_rc.spice', args.profile))
        cmd = run_magic(run, args.magic, rc, args.timeout, args.profile)
        result['magic_command'] = cmd
        result['extraction'] = inspect_netlist(run / 'extracted_rc.spice')
        result['power_connectivity'] = inspect_dc_supply_paths(
            (run / 'extracted_rc.spice').read_text())
        disconnected = [rail for rail in ('VDD', 'VSS')
                        if not result['power_connectivity'][rail]['mos_terminals_reachable']]
        if disconnected:
            raise ValueError('Extracted supply port has no DC path to MOS terminals: '
                             + ', '.join(disconnected))
        if result['power_connectivity']['rails_short_through_resistors']:
            raise ValueError('Extracted VDD and VSS are shorted through resistors')
        result['status'] = ('PASS_RC_NETLIST_STRUCTURE' if args.profile == 'all'
                            else 'PASS_TARGETED_RC_NETLIST_STRUCTURE')
    except Exception as exc:
        result['status'] = 'FAIL'
        result['error'] = str(exc)
    finally:
        result['artifacts'] = {p.name: sha256(p) for p in sorted(run.iterdir())
                               if p.is_file() and p != manifest}
        manifest.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': result['status'], 'run': str(run),
                      'extraction': result.get('extraction'), 'error': result.get('error')}, indent=2))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    sys.exit(main())
