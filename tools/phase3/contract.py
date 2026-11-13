"""Strict configuration and normalized measurement records (standard library only)."""
import math
import re

STATUSES = {'PASS', 'FAIL', 'ERROR', 'BLOCKED', 'NOT_CHARACTERIZED'}
FIELDS = 'run_id configuration corner vdd_v temp_c operation metric bit value unit status transition measure reason'.split()
UNITS = {'s': ('s', 1), 'ns': ('s', 1e-9), 'ps': ('s', 1e-12),
         'W': ('W', 1), 'mW': ('W', 1e-3), 'uW': ('W', 1e-6),
         'J': ('J', 1), 'pJ': ('J', 1e-12), 'fJ': ('J', 1e-15), 'V': ('V', 1)}
METRICS = {k: 's' for k in ('tACCESS', 'tCLK_TO_DATA', 'tREAD_INTERNAL', 'tWL_TO_SCLK',
           'tSETUP', 'tHOLD', 'tDATA_ENABLE', 'tDATA_DISABLE', 'tOUT_SETUP', 'tOUT_HOLD')}
METRICS.update({k: 'W' for k in ('P_STATIC', 'P_IDLE', 'P_READ_AVG', 'P_WRITE_AVG')})
METRICS.update(E_READ='J', E_WRITE='J', SMOKE_VOLTAGE='V')


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Expected finite JSON number')
    return value


def normalize(value, unit, metric):
    base, scale = UNITS[unit]
    if base != METRICS[metric]:
        raise ValueError('Inconsistent metric dimension')
    return number(value) * scale, base


def validate(c):
    required = {'schema_version', 'configuration', 'scope', 'baseline', 'pdk', 'corner', 'vdd_v',
                'temp_c', 'period_ns', 'duty_cycle', 'slew_ps', 'load_ff', 'extraction',
                'deck', 'netlist', 'model', 'stimuli', 'measurements', 'timeout_s', 'memory_mb'}
    if set(c) != required or c['schema_version'] != 1:
        raise ValueError('Unknown/missing configuration fields or schema')
    if c['configuration'] not in ('4x8', '8x8', '16x8', '32x8') or c['pdk'] != 'SKY130A':
        raise ValueError('Unsupported configuration/PDK')
    if c['corner'] not in ('tt', 'ss', 'ff') or c['scope'] not in ('infrastructure_smoke', 'sram'):
        raise ValueError('Unsupported corner/scope')
    if c['extraction'] not in ('schematic', 'devices/junctions', 'distributed RC'):
        raise ValueError('Unknown extraction type')
    for k in ('vdd_v', 'period_ns', 'slew_ps', 'load_ff', 'timeout_s', 'memory_mb'):
        if number(c[k]) <= 0:
            raise ValueError('Positive value required: ' + k)
    number(c['temp_c'])
    if not 0 < number(c['duty_cycle']) < 1 or c['slew_ps'] / 1000 >= c['period_ns'] * min(c['duty_cycle'], 1-c['duty_cycle']):
        raise ValueError('Invalid duty cycle/slew')
    for k in ('baseline', 'stimuli'):
        if not isinstance(c[k], str) or not c[k].strip():
            raise ValueError('Missing ' + k)
    for k in ('deck', 'netlist', 'model'):
        if set(c[k]) != {'path', 'sha256'} or not re.fullmatch(r'[a-f0-9]{64}', c[k]['sha256']):
            raise ValueError('Expected pinned input: ' + k)
    if not isinstance(c['measurements'], list):
        raise ValueError('Expected measurement list')
    names = set()
    for m in c['measurements']:
        if not {'measure', 'metric', 'operation', 'bit', 'unit', 'transition', 'definition'} <= set(m) or set(m) - {'measure', 'metric', 'operation', 'bit', 'unit', 'transition', 'definition', 'min', 'max'}:
            raise ValueError('Invalid measurement fields')
        if not re.fullmatch(r'[a-z][a-z0-9_]*', m['measure']) or m['measure'] in names:
            raise ValueError('Duplicate/invalid measure')
        names.add(m['measure'])
        normalize(0, m['unit'], m['metric'])
        if m['bit'] is not None and (type(m['bit']) is not int or not 0 <= m['bit'] < 8):
            raise ValueError('Invalid bit')
        if m['transition'] not in ('rise', 'fall', 'stable', 'na') or not m['definition']:
            raise ValueError('Missing transition/definition')
        if m['operation'] not in ('read', 'write', 'idle', 'static', 'bus', 'smoke'):
            raise ValueError('Invalid operation')
        if c['scope'] == 'sram' and m['metric'] == 'SMOKE_VOLTAGE':
            raise ValueError('Smoke metric cannot characterize SRAM')
        for key in ('min', 'max'):
            if key in m:
                number(m[key])
        if 'min' in m and 'max' in m and m['min'] > m['max']:
            raise ValueError('Reversed bounds')
    return c


def rows(c, run_id, log, dry_run=False):
    """Only bare ngspice numeric assignments; SPICE measurements are SI-valued."""
    result = []
    for m in c['measurements']:
        unit = METRICS[m['metric']]
        hits = re.findall(r'^\s*' + re.escape(m['measure']) + r'\s*=\s*([^\s]+)', log, re.M | re.I)
        row = dict(run_id=run_id, **{k: c[k] for k in ('configuration', 'corner', 'vdd_v', 'temp_c')},
                   **{k: m[k] for k in ('operation', 'metric', 'bit', 'transition', 'measure')},
                   value=None, unit=unit, status='NOT_CHARACTERIZED', reason='dry-run' if dry_run else 'measure absent')
        if hits and not dry_run:
            if len(hits) != 1:
                raise ValueError('Ambiguous repeated measure: ' + m['measure'])
            value = float(hits[0])
            number(value)
            row.update(value=value, status='PASS', reason='measured; no electrical qualification implied')
            for key, compare in (('min', lambda a,b: a < b), ('max', lambda a,b: a > b)):
                if key in m and compare(value, normalize(m[key], m['unit'], m['metric'])[0]):
                    row.update(status='FAIL', reason='outside configured bounds')
        result.append(row)
    return result
