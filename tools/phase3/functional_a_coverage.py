"""Requirement identities and additive mapping, never a rewrite of legacy verdicts."""
from collections import Counter

ADAPTER = 'phase3_functional_a_v1'
DECISIONS = ('O1', 'O2', 'O3', 'O4')
MATRIX = {
    'A01': ('DIG-01/03/04; technical specification 4/6', ('O4',)),
    'A02': ('DIG-02/05; technical specification 16', ('O4',)),
    'A03': ('DIG-05; physical binding sequence 4', ('O2', 'O4')),
    'A04': ('DIG-07/08; timing contract 4', ('O2',)),
    'A05': ('DIG-08; consecutive reads', ('O2',)),
    'A06': ('DIG-06/07; technical specification 4', ('O2', 'O3')),
    'A07': ('technical specification 4/16; timing contract 6', ('O4',)),
    'A08': ('DIG-05/11; technical specification 15', ('O1', 'O2')),
    'A09': ('DIG-06/08; consecutive reads', ('O1', 'O2')),
    'A10': ('DIG-06/07/08; timing contract 4/6/8', ('O2', 'O3')),
    'A11': ('technical specification 6/8/14; physical binding', ('O4',)),
    'A12': ('DIG-09; Phase 3 evidence contract', ()),
}

KINDS = {
    'captured_operation': ('A01',), 'captured_address': ('A01',),
    'captured_write_data': ('A02',), 'known_storage': ('A02',),
    'output_ff_setup_hold_envelope': ('A03', 'A11'),
    'local_capture_edge': ('A03', 'A11'), 'captured_ff_q': ('A03',),
    'previous_ff_q_retained': ('A04',), 'mask_preserves_ff_q': ('A04',),
    'probe_observes_enabled_drive': ('A06',), 'masked_probe_current': ('A06',),
    'masked_probe_voltage': ('A06',), 'restored_drive_current': ('A06', 'A10'),
    'strong_master_steady_current': ('A07',), 'no_strong_host_ebuf_overlap': ('A07',),
    'read_data': ('A08',), 'data_after_probe_removed': ('A08', 'A10'),
    **{k: ('A11',) for k in (
        'one_hot_or_zero', 'write_precharge_nonoverlap', 'wordline_precharge_nonoverlap',
        'low_phase_wordlines', 'precharge_ready_before_next_access', 'inactive_wordlines',
        'inactive_phases', 'unselected_wordlines', 'selected_wordline_asserts',
        'write_sense_exclusion')},
}


def legacy_identity(check):
    # A missing local edge replaces that bit's envelope check in the old observer.
    kind = check['kind']
    if kind == 'local_capture_edge':
        kind = 'output_ff_setup_hold_envelope'
    return (kind, *(check.get(k) for k in ('cycle', 'bit', 'row', 'signal', 'time_ns')))


def verify_inventory(expected, actual):
    """Compare identities, not only totals; missing and duplicated PASS cannot cancel."""
    a, b = Counter(expected), Counter(actual)
    if not a or any(v != 1 for v in a.values()) or any(v != 1 for v in b.values()):
        raise ValueError('Empty/duplicated coverage identity')
    if a != b:
        raise ValueError('Coverage identities differ: missing=%d extra=%d' % (
            sum((a-b).values()), sum((b-a).values())))


def map_checks(checks, records):
    """Keep the original index/status; classification is explanatory metadata only."""
    cycles = {r['cycle']: r for r in records}
    if len(cycles) != len(records):
        raise ValueError('Duplicated cycle')
    previous = {r['cycle']: records[i-1]['operation'] if i else 'startup'
                for i, r in enumerate(records)}
    mapped = []
    for index, check in enumerate(checks):
        if check.get('status') not in ('PASS', 'FAIL'):
            raise ValueError('Invalid legacy verdict')
        kind, cycle = check['kind'], check.get('cycle')
        if cycle is not None and cycle not in cycles:
            raise ValueError('Unknown check cycle')
        scenario = previous[cycle] + '->' + cycles[cycle]['operation'] if cycle is not None else 'whole_trace'
        pending = False
        if kind == 'previous_data_visible_before_new_capture':
            properties = ('A05',) if previous[cycle] == 'read' else ('A10',)
            pending = True  # No deadline or observation window is ratified by mapping.
        else:
            if kind not in KINDS:
                raise ValueError('Unmapped legacy kind: ' + kind)
            properties = KINDS[kind]
        for prop in properties:
            identity = (prop, scenario, cycle, check.get('row', cycles.get(cycle, {}).get('row')),
                        check.get('bit'), check.get('signal'), kind, check.get('time_ns'))
            mapped.append(dict(identity=identity, property=prop, legacy_index=index,
                               legacy_status=check['status'], source_kind=kind,
                               source_window='unchanged phase2_extension/phase2_access_checks',
                               normative_disposition='PENDING' if pending else 'benchmark_observation',
                               requirements=MATRIX[prop][0]))
    return mapped


def compare(checks, template, records):
    """Template is the pinned qualification checks.json; its PASS values are unused."""
    verify_inventory([legacy_identity(c) for c in template], [legacy_identity(c) for c in checks])
    expected, mapped = map_checks(template, records), map_checks(checks, records)
    # local_capture_edge is an alternative diagnostic for the same opportunity.
    def identities(items):
        return [tuple('output_ff_setup_hold_envelope' if v == 'local_capture_edge' else v
                      for v in item['identity']) for item in items]
    verify_inventory(identities(expected), identities(mapped))
    return dict(schema_version=1, legacy_status='FAIL' if any(c['status']=='FAIL' for c in checks) else 'PASS',
                checks=checks, mapping=mapped, coverage_complete=True,
                counts=dict(Counter(c['status'] for c in checks)), total=len(checks))
