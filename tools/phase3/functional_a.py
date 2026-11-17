"""Development-only A adapter: partial evidence may fail, but cannot approve A."""
from collections import Counter
import json
import math
from pathlib import Path
import re
from phase2_evidence import digest
from .functional_a_coverage import ADAPTER, DECISIONS, MATRIX, compare, verify_inventory, legacy_identity

CONTEXT_FIELDS = {'schema_version', 'adapter', 'baseline', 'selection', 'expected_inputs',
                  'decisions', 'gate_enabled', 'observation_windows'}


def validate_context(context):
    if (set(context) != CONTEXT_FIELDS or type(context['schema_version']) is not int
            or context['schema_version'] != 1 or context['adapter'] != ADAPTER):
        raise ValueError('Unknown/missing A context fields, identity or version')
    if context['gate_enabled'] is not False:
        raise ValueError('Functional A activation is not authorized')
    if context['decisions'] != {d: 'PENDING' for d in DECISIONS}:
        raise ValueError('O1-O4 must remain explicitly PENDING in this implementation')
    if context['observation_windows'] != []:
        raise ValueError('External/data-dependent windows are not authorized')
    if not isinstance(context['baseline'], str) or not context['baseline']:
        raise ValueError('Missing baseline')
    if (not isinstance(context['selection'], dict) or not isinstance(context['expected_inputs'], dict)
            or set(context['expected_inputs']) != {'deck','netlist','model'}):
        raise ValueError('Invalid A context selection/input identity')
    selection = context['selection']
    if (set(selection) != {'baseline','candidate','qualification','fixture','gds','gds_sha256','inputs'}
            or selection['baseline'] != context['baseline']
            or any(not isinstance(selection[k], str) or not selection[k].strip()
                   for k in ('candidate','qualification','fixture','gds'))
            or not isinstance(selection['inputs'], dict) or not selection['inputs']
            or not isinstance(selection['gds_sha256'], str)
            or not re.fullmatch('[a-f0-9]{64}', selection['gds_sha256'])):
        raise ValueError('Invalid A selection identity schema')
    for path, sha in selection['inputs'].items():
        if not isinstance(path,str) or not path or not isinstance(sha,str) or not re.fullmatch('[a-f0-9]{64}',sha):
            raise ValueError('Invalid A selection pin')
    for pin in context['expected_inputs'].values():
        if (not isinstance(pin, dict) or set(pin) != {'path','sha256'}
                or not isinstance(pin['path'], str) or not pin['path'].strip()
                or not isinstance(pin['sha256'], str) or not re.fullmatch('[a-f0-9]{64}',pin['sha256'])):
            raise ValueError('Invalid A input pin')
    return context


def context_for(baseline, selection, inputs):
    return validate_context(dict(schema_version=1, adapter=ADAPTER, baseline=baseline,
        selection=selection, expected_inputs=inputs, decisions={d:'PENDING' for d in DECISIONS},
        gate_enabled=False, observation_windows=[]))


def blocked_assessment():
    return dict(schema_version=1, adapter=ADAPTER, status='BLOCKED', gate_enabled=False,
                decisions={d:'PENDING' for d in DECISIONS}, reason='O1-O4 pending; complete A gate disabled',
                temporal_qualification=dict(status='NOT_CHARACTERIZED', reason='No approved B limits'))


def characterization_status(measurement_status, functional_status):
    """No implementation/approval of B exists, even if partial A or .meas pass."""
    from .functional import overall_status
    return overall_status(overall_status(measurement_status, functional_status, 'sram'),
                          'NOT_CHARACTERIZED', 'sram')


def validate_records(records):
    """Known read data is derived only from the stimulus writes, never the DUT."""
    memory, last = {}, -1
    for r in records:
        if (type(r['cycle']) is not int or r['cycle'] != last+1 or r['operation'] not in ('idle','write','read')
                or type(r['row']) is not int or not 0 <= r['row'] < 4
                or type(r['expected']) is not int or not 0 <= r['expected'] < 256
                or any(isinstance(r[k], bool) or not isinstance(r[k], (int,float)) or not math.isfinite(r[k])
                       for k in ('rise_ns','fall_ns','sample_ns'))
                or not r['rise_ns'] < r['fall_ns'] < r['sample_ns']):
            raise ValueError('Invalid stimulus record')
        if r['operation']=='write': memory[r['row']] = r['expected']
        if r['operation']=='read' and memory.get(r['row']) != r['expected']:
            raise ValueError('Known read not established by a stimulus write')
        last = r['cycle']
    if not records:
        raise ValueError('Empty stimulus')


def assess(checks, template, records, internal=()):
    """Additive partial assessment. No decisions, windows or verdicts are inferred."""
    validate_records(records)
    comparison = compare(checks, template, records)
    reads = [r for r in records if r['operation']=='read']
    expected = [('A04','internal_retention',r['cycle'],r['row'],b,'REG_Q','sample_to_capture')
                for r in reads for b in range(8)]
    if expected:
        verify_inventory(expected, [tuple(o['identity']) for o in internal])
    pending_inventory = []
    for i, r in enumerate(records):
        if r['operation'] != 'read': continue
        props = ['A08', 'A09']
        if i and records[i-1]['operation']=='read': props.append('A05')
        if i and records[i-1]['operation'] in ('write','idle'): props.append('A10')
        if 'calibration' in r: props.append('A10')
        for occurrence, prop in enumerate(props):
            for bit in range(8):
                pending_inventory.append(dict(property=prop, cycle=r['cycle'], bit=bit,
                    identity=(prop,'pending_external',r['cycle'],r['row'],bit,occurrence,'O1-O4'),
                    status='BLOCKED', pending_decisions=list(MATRIX[prop][1])))
    properties = {}
    for prop, (source, pending) in MATRIX.items():
        facts = [m for m in comparison['mapping'] if m['property']==prop]
        usable = [f for f in facts if f['normative_disposition'] != 'PENDING']
        extra = [o for o in internal if o['property']==prop]
        if any(o['status'] not in ('PASS','FAIL') for o in extra):
            raise ValueError('Invalid internal observation verdict')
        observed = [f['legacy_status'] for f in usable] + [o['status'] for o in extra]
        # Complete coverage of A05/A08/A09/A10 is expressly not claimed.
        if 'FAIL' in observed:
            status = 'FAIL'
        elif pending:
            status = 'BLOCKED'
        else:
            status = 'PASS' if prop=='A12' or observed else 'BLOCKED'
        properties[prop] = dict(status=status, requirements=source, pending_decisions=list(pending),
            observation_status='FAIL' if 'FAIL' in observed else 'PASS' if observed or prop=='A12' else 'NOT_CHARACTERIZED',
            legacy_observations=len(facts), internal_observations=len(extra), complete=not pending,
            legacy_status_counts=dict(Counter(f['legacy_status'] for f in facts)),
            pending_legacy_status_counts=dict(Counter(f['legacy_status'] for f in facts
                                                     if f['normative_disposition']=='PENDING')),
            pending_opportunities=sum(o['property']==prop for o in pending_inventory),
            coverage_identities=[list(m['identity']) for m in facts] + [list(o['identity']) for o in extra])
    status = 'FAIL' if any(p['status']=='FAIL' for p in properties.values()) else 'BLOCKED'
    return dict(**{**blocked_assessment(), 'status':status}, properties=properties,
        internal_observations=list(internal), pending_inventory=pending_inventory, legacy_comparison=comparison,
        coverage=dict(complete=False, legacy_mapping_complete=True,
                      missing_operational_decisions=list(DECISIONS)))


def evaluate_waveform(data, receipt, state, template):
    """Use unchanged shared checkers, with additional Q retention observations."""
    from phase2_extension import check
    from run_phase2_startup_review import validate_trace
    from .functional_a_observers import retention
    validate_records(receipt['cycles'])
    validate_trace(data, receipt['vectors'], receipt['stop_ns'])
    checks, reference, coverage = check(data, receipt['cycles'], receipt['vectors'], receipt['probes'],
                                        state, receipt['stop_ns'], receipt['campaign'])
    if (dict(Counter(legacy_identity(c)[0] for c in checks)) != receipt['metrics']['checks_by_kind']
            or coverage['read_bit_checks'] != receipt['metrics']['read_bit_checks']):
        # Preserve failures even when coverage is corrupt; do not publish partial PASS.
        return dict(**{**blocked_assessment(), 'status':'ERROR'}, reason='Legacy coverage differs',
                    legacy_checks=checks, coverage=coverage)
    try:
        internal = retention(data, receipt['cycles'], receipt['vectors'], receipt['probes'],state,receipt['stop_ns'])
        result = assess(checks, template, receipt['cycles'], internal)
    except ValueError as error:
        return dict(**{**blocked_assessment(), 'status':'ERROR'}, reason=str(error), legacy_checks=checks)
    result['capture_reference'] = reference
    return result


def replay(root, run_directory, context, manifest_sha256):
    """Read-only offline replay, never a fresh electrical execution or CLI PASS."""
    import numpy as np
    from .provenance import selected_inputs
    validate_context(context)
    identity = selected_inputs(root, context['baseline'])
    if identity != context['selection']:
        raise ValueError('A replay selected candidate differs')
    directory = Path(run_directory)
    manifest_path = directory/'manifest.json'
    manifest_hash = digest(manifest_path)
    if manifest_hash != manifest_sha256:
        raise ValueError('Replay manifest hash differs')
    manifest = json.loads(manifest_path.read_text())
    from .functional import CONDITIONS
    if any(manifest['configuration'][k] != v for k,v in CONDITIONS.items()):
        raise ValueError('Replay conditions differ from the nominal A profile')
    raw = directory/'inputs/waveform.dat'
    raw_hash = digest(raw)
    if (manifest['evidence'].get('inputs/waveform.dat') != raw_hash
            or manifest['configuration']['scope'] != 'sram'
            or any(manifest['configuration'][k] != v for k,v in context['expected_inputs'].items())):
        raise ValueError('Replay input/raw identity differs')
    receipt_path = root/identity['qualification']
    receipt = json.loads(receipt_path.read_text())
    template = json.loads((receipt_path.parent/'checks.json').read_text())['checks']
    state = json.loads((root/identity['fixture']).read_text())
    with raw.open() as stream:
        if stream.readline().split() != ['time', *receipt['vectors']]:
            raise ValueError('Functional waveform header differs')
    result = evaluate_waveform(np.loadtxt(raw, skiprows=1), receipt, state, template)
    for name, sha in identity['inputs'].items():
        if digest(root/name) != sha: raise ValueError('Replay input changed: '+name)
    if digest(raw) != raw_hash or digest(manifest_path) != manifest_hash:
        raise ValueError('Replay source changed')
    result.update(assessment_mode='replay', electrical_simulation_performed=False,
                  source_execution=dict(path=str(directory), manifest_sha256=manifest_hash,
                                        waveform_sha256=raw_hash, status=manifest['status']))
    return result
