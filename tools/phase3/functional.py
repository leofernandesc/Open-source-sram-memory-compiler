"""Adapter only: electrical assertions remain in the existing Phase 2 checkers."""
from collections import Counter
import json
from pathlib import Path
from phase2_evidence import digest
from .provenance import selected_inputs

ADAPTER = 'phase2_qualification_v1'
CONDITIONS = dict(configuration='4x8', scope='sram', corner='tt', vdd_v=1.8, temp_c=27,
                  period_ns=20, duty_cycle=.5, slew_ps=50, load_ff=10, extraction='devices/junctions')


def prepare_context(root, c):
    """Validate and pin the checker context before starting a future simulator."""
    spec = c.get('functional_validation')
    if spec is None:
        return None
    path = Path(spec['path'])
    path = path if path.is_absolute() else root/path
    if digest(path) != spec['sha256']:
        raise ValueError('Functional context hash mismatch')
    context = json.loads(path.read_text())
    from .functional_a import ADAPTER as A_ADAPTER, validate_context
    is_a = context.get('adapter') == A_ADAPTER
    if is_a:
        validate_context(context)
    is_nominal=context.get('adapter')=='phase3_nominal_bench_v1'
    if is_nominal:
        from .nominal_operational import validate_context as validate_nominal
        nominal_pins=validate_nominal(root,c,context)
    if context['adapter'] not in (ADAPTER, A_ADAPTER, 'phase3_nominal_bench_v1') or context['baseline'] != c['baseline']:
        raise ValueError('Functional adapter/baseline differs')
    for key, expected in CONDITIONS.items():
        if c[key] != expected:
            raise ValueError('Phase 2 functional adapter supports nominal conditions only: ' + key)
    for key in ('deck', 'netlist', 'model'):
        if c[key] != context['expected_inputs'][key]:
            raise ValueError('Functional context input differs: ' + key)
    identity = selected_inputs(root, c['baseline'])
    if context['selection'] != identity:
        raise ValueError('Functional context selected candidate differs')
    prepared = dict(context=context, path=path, pins={**{str(root/p):h for p,h in identity['inputs'].items()},
                                                     str(path.resolve()):spec['sha256']})
    if is_a:
        prepared['activation_blocked'] = 'O1-O4 pending; phase3_functional_a_v1 gate disabled'
    if is_nominal:
        prepared['pins'].update(nominal_pins)
        prepared['operational_nominal']=True
    return prepared


def check_waveform(root, work, context, execution=None):
    """Consume only this execution's fresh full-resolution waveform, never old raw."""
    if context.get('adapter') == 'phase3_functional_a_v1':
        from .functional_a import blocked_assessment, validate_context
        validate_context(context)
        return blocked_assessment()  # Real A executions are refused before ngspice.
    if context.get('adapter')=='phase3_nominal_bench_v1':
        from .nominal_operational import check_fresh
        return check_fresh(root,work,context,execution)
    import numpy as np
    from phase2_extension import check
    selection = context['selection']
    receipt = json.loads((root/selection['qualification']).read_text())
    state = json.loads((root/selection['fixture']).read_text())
    raw = work/'waveform.dat'
    with raw.open() as stream:
        if stream.readline().split() != ['time', *receipt['vectors']]:
            raise ValueError('Functional waveform header differs')
    data = np.loadtxt(raw, skiprows=1)
    checks, reference, coverage = check(data, receipt['cycles'], receipt['vectors'], receipt['probes'],
                                        state, receipt['stop_ns'], receipt['campaign'])
    if not checks or any(c['status'] not in ('PASS', 'FAIL') for c in checks):
        raise ValueError('Empty/invalid functional checks')
    counts = dict(Counter(c['kind'] for c in checks))
    if counts != receipt['metrics']['checks_by_kind'] or coverage['read_bit_checks'] != receipt['metrics']['read_bit_checks']:
        raise ValueError('Functional check coverage differs from the selected qualification profile')
    return dict(status='FAIL' if any(c['status']=='FAIL' for c in checks) else 'PASS',
                adapter=ADAPTER, checks=checks, capture_reference=reference, coverage=coverage,
                waveform_sha256=digest(raw))


def overall_status(measurement_status, functional_status, scope):
    if scope != 'sram':
        return measurement_status
    for status in ('ERROR', 'FAIL', 'BLOCKED'):
        if status in (measurement_status, functional_status):
            return status
    return 'PASS' if measurement_status == functional_status == 'PASS' else 'NOT_CHARACTERIZED'
