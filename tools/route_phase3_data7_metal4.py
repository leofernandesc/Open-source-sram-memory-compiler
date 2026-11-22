#!/usr/bin/env python3
"""Edit only the DATA7 pad access in the pinned spaced ECO DEF."""
import argparse
import json
from pathlib import Path
import shutil

from rebuild_phase3_danilo_eco import ROOT, run
from run_phase3_eco_pex import new_directory, pinned, sha256

REFERENCE = ROOT / 'build/phase3/danilo_ss_ff2_spaced_route'
DEF_SHA256 = 'd765a8dddb9e8afc66300536c87b95d26b7da4902520bb329699fd3f72abd3be'
OLD = '      NEW met2 ( 384790 340 0 ) ( * 61710 )\n'
PROMOTED = (
    '      NEW met2 ( 384790 340 0 ) ( * 2720 )\n'
    '      NEW met2 ( 384790 60700 ) ( * 61710 )\n'
    '      NEW met4 ( 384790 2720 ) ( * 60700 )\n'
    '      NEW met2 ( 384790 2720 ) M2M3_PR\n'
    '      NEW met2 ( 384790 60700 ) M2M3_PR\n'
    '      NEW met3 ( 384790 2720 ) M3M4_PR\n'
    '      NEW met3 ( 384790 60700 ) M3M4_PR\n'
    '      NEW met3 ( 384790 2720 ) ( 385330 * )\n'
    '      NEW met3 ( 384790 60700 ) ( 385330 * )\n'
)
EDGE_PIN = (
    '    - DATA[7] + NET DATA[7] + DIRECTION INOUT + USE SIGNAL\n'
    '      + PORT\n'
    '        + LAYER met2 ( -70 -245 ) ( 70 245 )\n'
    '        + FIXED ( 384790 245 ) N ;\n'
)
INNER_PIN = (
    '    - DATA[7] + NET DATA[7] + DIRECTION INOUT + USE SIGNAL\n'
    '      + PORT\n'
    '        + LAYER met3 ( -400 -220 ) ( 400 220 )\n'
    '        + FIXED ( 384790 61710 ) N ;\n'
)


def replace_drop(definition, replacement):
    anchor = '    - DATA[7] ( PIN DATA[7] ) ( _94_ Z ) ( _52_ A1 ) + USE SIGNAL\n'
    if definition.count(anchor) != 1:
        raise ValueError('Expected the pinned DATA7 driver and input branch')
    begin = definition.index(anchor)
    end = definition.index(' ;\n', begin)
    selected = definition[begin:end]
    if selected.count(OLD) != 1:
        raise ValueError('Expected one original met2 drop in DATA7')
    return definition[:begin] + selected.replace(OLD, replacement) + definition[end:]


def promote(definition):
    return replace_drop(definition, PROMOTED)


def relocate_access(definition):
    if definition.count(EDGE_PIN) != 1:
        raise ValueError('Expected the pinned DATA7 access at the bottom edge')
    return replace_drop(definition.replace(EDGE_PIN, INNER_PIN),
                        '      NEW met2 ( 384790 61160 ) ( * 61710 )\n'
                        '      NEW met2 ( 384790 61710 ) M2M3_PR\n')


def build(output, internal_port=False):
    reference_receipt = REFERENCE / 'results.json'
    source = json.loads(reference_receipt.read_text())
    old_def = pinned(REFERENCE / 'routed.def', DEF_SHA256)
    new_def = relocate_access(old_def.read_text()) if internal_port else promote(old_def.read_text())
    output = new_directory(output)
    (output/'input.def').write_text(new_def)
    inputs = {'routed.def': sha256(old_def), 'results.json': sha256(reference_receipt)}
    for name in ('leaf_fabric.gds', 'leaf_fabric.lef', 'routed.v'):
        artifact = pinned(REFERENCE/name, source['build_artifacts'][name])
        shutil.copyfile(artifact, output/name)
        inputs[name] = sha256(artifact)
    # The LEFs used by the pinned original routing snapshot are replayed here.
    cells = pinned(REFERENCE/'routing_cells.lef', source['routing_library']['routing']['sha256'])
    shutil.copyfile(cells, output/cells.name)
    inputs[cells.name] = sha256(cells)
    commands = (
        'read_lef /opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef\n'
        'read_lef routing_cells.lef\nread_lef leaf_fabric.lef\n'
        'read_def input.def\ncheck_placement -verbose\n'
        'write_db routed.odb\nwrite_def routed.def\n'
        'puts PHASE3_LOCAL_ROUTE_IMPORTED\nexit\n'
    )
    (output/'flow.tcl').write_text(commands)
    run(output, ['openroad', '-exit', 'flow.tcl'], 'openroad.log', 240)
    if 'PHASE3_LOCAL_ROUTE_IMPORTED' not in (output/'openroad.log').read_text():
        raise ValueError('OpenROAD did not import the local route')
    artifacts = {name: sha256(output/name) for name in
                 ('routed.odb', 'leaf_fabric.gds', 'leaf_fabric.lef', 'routed.v', 'input.def', 'routed.def')}
    info = dict(status='ROUTED_VERIFICATION_PENDING', build_directory=str(output.relative_to(ROOT)),
                selection=source['selection'], reference_inputs=inputs,
                data7_route=('Relocate the DATA7 pin to met3 at the output branch and remove the pad drop'
                             if internal_port else 'Replace only the pad drop with met4 and two via stacks'),
                build_artifacts=artifacts)
    (output/'results.json').write_text(json.dumps(info, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--internal-port', action='store_true',
                        help='Experimentally replace only the DATA7 pad access with an inner met3 port')
    args = parser.parse_args()
    build(args.output, args.internal_port)
