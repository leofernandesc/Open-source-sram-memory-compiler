#!/usr/bin/env python3
"""Reconstruct the documented Danilo ECO on the sealed abutted 4x8 inputs."""

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

from phase2_evidence import digest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'reports/phase2/direct_abutment_20261111'
DANILO = '42f0b5128d7e5dde4385731e85fa504a6ee005a7'


def edit_binding(source, tap=48, capture_cell='clkinv_1', output_cell='ebufn_8',
                 output_ff='dfxtp_1'):
    """Retain the original CTS for other domains and use public CLK for output capture."""
    # The placement flow creates taps anew. The historical routed.v already has them.
    source = re.sub(r'(?m)^\s*sky130_fd_sc_hd__tapvpwrvgnd_1 \S+ \(\);\n', '\n', source)
    source, count = re.subn(
        r'(\\macro_core\.evaluation\s*\([^;]+?\.C\(\\macro_core\.delay_clk )\[60\]',
        lambda match: match[1] + f'[{tap}]', source)
    if count != 1:
        raise ValueError('Expected one evaluation input on tap 60')
    source, count = re.subn(
        r'sky130_fd_sc_hd__clkinv_1 (_(?:33|6[0-6])_) '
        r'\(\.A\(clknet_1_[01]__leaf_CLK\)',
        lambda match: f'sky130_fd_sc_hd__{capture_cell} {match[1]} (.A(CLK)', source)
    if count != 8:
        raise ValueError('Expected eight historical output capture inverters')
    source, count = re.subn(r'sky130_fd_sc_hd__ebufn_1 (_(?:8[7-9]|9[0-4])_) ',
                           lambda match: f'sky130_fd_sc_hd__{output_cell} {match[1]} ', source)
    if count != 8:
        raise ValueError('Expected eight historical DATA drivers')
    source, count = re.subn(r'sky130_fd_sc_hd__dfxtp_1 (_(?:7[5-9]|8[0-2])_) ',
                           lambda match: f'sky130_fd_sc_hd__{output_ff} {match[1]} ', source)
    if count != 8:
        raise ValueError('Expected eight historical output flip-flops')
    return source


def run(output, command, log, timeout):
    with (output / log).open('x') as stream:
        return subprocess.run(command, cwd=output, stdout=stream, stderr=subprocess.STDOUT,
                              check=True, timeout=timeout)


def relocate_data_pins(flow, placement_profile):
    """Move only DATA pins on the existing bottom edge."""
    placement = 'place_pins -hor_layers met3 -ver_layers met2\n'
    if flow.count(placement) != 1:
        raise ValueError('Expected one automatic IO placement step')
    # Distributed coordinates follow the DATA driver and input mux pairs
    # from the automatic-binding DEF. The first cluster serves as a control.
    coordinates = {'clustered': range(373, 397, 3),
                   'distributed': (254, 271, 287, 319, 351, 377, 394, 385),
                   # Reduce the measured coupling of the DATA1 met2 drop to CLK.
                   'distributed-spaced': (254, 260, 287, 319, 351, 377, 394, 385)}
    commands = ''.join(
        f'place_pin -pin_name {{DATA[{bit}]}} -layer met2 -location {{{x} 0.242}} '
        '-pin_size {0.14 0.485} -force_to_die_boundary\n'
        for bit, x in enumerate(coordinates[placement_profile])
    )
    return flow.replace(placement, placement + commands)


def place_data7_pair(flow):
    """Place the DATA7 FF and driver together near the existing output pin."""
    anchor = '# Reserve well-tap sites before placing functional cells.'
    if flow.count(anchor) != 1:
        raise ValueError('Expected a single tap placement anchor')
    return flow.replace(anchor, 'place_inst -name _82_ -origin {378.58 27.20} -orient R0 -status FIRM\n'
                        'place_inst -name _94_ -origin {378.58 21.76} -orient R0 -status FIRM\n' + anchor)


def replace_output_enables(source, drive):
    """Keep captured READ and implement its four-input gate at each driver."""
    pattern = (r'sky130_fd_sc_hd__nand2_1 (_(?:35|5[3-9])_) \(\.A\(\\control\.READ_Q \),\s*'
               r'\.B\(live_read\),\s*\.Y\((_[0-9]+_)\)\);')

    def local(match):
        return (f'sky130_fd_sc_hd__nand4bb_{drive} {match[1]} (.A_N(OEb),\n'
                f'    .B_N(CSb),\n    .C(WEb),\n    .D(\\control.READ_Q ),\n    .Y({match[2]}));')

    replaced, count = re.subn(pattern, local, source)
    if count != 8 or '_84_ (.D(live_read)' not in replaced:
        raise ValueError('Expected eight driver enables and an independent READ capture')
    return replaced


def rebuild(output, tap, capture_cell, output_cell, output_ff, data_pin_placement='automatic', data7_pair=False,
            ownership_nand4bb=None):
    from phase2_lef_check import verify

    output = output.resolve()
    if not output.is_relative_to(ROOT / 'build/phase3') or output == ROOT / 'build/phase3':
        raise ValueError('Use a fresh directory below build/phase3')
    output.mkdir(parents=True)
    sources = {}

    def pinned(directory, name, field='artifacts'):
        folder = BASE / directory
        path = folder / name
        manifest = json.loads((folder / 'results.json').read_text())
        if digest(path) != manifest[field][name]:
            raise ValueError(f'Historical artifact does not match receipt: {path}')
        sources[str(path.relative_to(ROOT))] = digest(path)
        return path

    binding = edit_binding(pinned('route_v1', 'routed.v').read_text(),
                           tap, capture_cell, output_cell, output_ff)
    if ownership_nand4bb is not None:
        binding = replace_output_enables(binding, ownership_nand4bb)
    (output / 'binding.v').write_text(binding)
    route_pins = json.loads((BASE / 'route_v1/results.json').read_text())['build_artifacts']
    for name in ('leaf_fabric.gds', 'leaf_fabric.lef'):
        source = pinned('layout_v1', name)
        if digest(source) != route_pins[name]:
            raise ValueError(f'GDS/LEF from geometry differs from routed fabric: {name}')
        shutil.copyfile(source, output / name)
    shutil.copyfile(pinned('route_v1', 'macro_interface.lib'), output / 'macro_interface.lib')
    names = set(re.findall(r'(?m)^\s*(sky130_fd_sc_hd__\w+)\s', binding))
    names.update({'sky130_fd_sc_hd__tapvpwrvgnd_1',
                  *(f'sky130_fd_sc_hd__fill_{size}' for size in (1, 2, 4, 8))})
    _, lef_proof = verify(names, output)

    flow_path = pinned('route_v1', 'flow.tcl')
    flow = flow_path.read_text()
    historical_build = json.loads((flow_path.parent / 'results.json').read_text())['build_directory']
    flow = flow.replace('/work/' + historical_build, str(output))
    # The input is already post-CTS. A second CTS would reconnect the eight CLK pins.
    start, end = flow.index('set phase_nets {}'), flow.index('global_connect\nsource', flow.index('set phase_nets {}'))
    flow = flow[:start] + flow[end:]
    if data_pin_placement != 'automatic':
        flow = relocate_data_pins(flow, data_pin_placement)
    if data7_pair:
        flow = place_data7_pair(flow)
    (output / 'flow.tcl').write_text(flow)
    run(output, ['openroad', '-exit', 'flow.tcl'], 'openroad.log', 900)
    if 'PHASE2_ROUTING_DONE' not in (output / 'openroad.log').read_text():
        raise ValueError('Routing did not complete')
    routed = (output / 'routed.v').read_text()
    clocks = re.findall(r'sky130_fd_sc_hd__' + capture_cell + r' _(?:33|6[0-6])_ \(\.A\(CLK\)', routed)
    ffs = re.findall(r'sky130_fd_sc_hd__' + output_ff + r' _(?:7[5-9]|8[0-2])_ ', routed)
    if len(clocks) != 8 or len(ffs) != 8 or routed.count('sky130_fd_sc_hd__' + output_cell + ' ') != 8:
        raise ValueError('Routed ECO connectivity differs')
    if ownership_nand4bb is not None and routed.count(f'sky130_fd_sc_hd__nand4bb_{ownership_nand4bb} ') != 8:
        raise ValueError('Routed local driver enable count differs')
    receipt = dict(status='ROUTED_VERIFICATION_PENDING', build_directory=str(output.relative_to(ROOT)),
                   reconstructed_from=DANILO, original_routing_identity='independently reconstructed',
                   selection=dict(evaluation_tap=tap, capture_clock='public CLK',
                                  capture_cell=capture_cell, output_cell=output_cell, output_ff=output_ff,
                                  data_pin_placement=data_pin_placement, data7_pair_near_pin=data7_pair,
                                  ownership_nand4bb=ownership_nand4bb),
                   historical_inputs=sources, routing_library=lef_proof,
                   build_artifacts={name: digest(output / name) for name in
                                    ('routed.odb', 'leaf_fabric.gds', 'leaf_fabric.lef', 'routed.v')})
    (output / 'results.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tap', type=int, choices=range(42, 61, 2), default=48)
    parser.add_argument('--capture-cell', choices=('clkinv_1', 'clkinv_2', 'clkinv_4'), default='clkinv_1')
    parser.add_argument('--output-cell', choices=('ebufn_4', 'ebufn_8'), default='ebufn_8')
    parser.add_argument('--output-ff', choices=('dfxtp_1', 'dfxtp_2', 'dfxtp_4'), default='dfxtp_1')
    parser.add_argument('--data-pin-placement',
                        choices=('automatic', 'clustered', 'distributed', 'distributed-spaced'), default='automatic',
                        help='Experimental physical pin placement. Requires the resulting LEF for integration.')
    parser.add_argument('--data7-pair-near-pin', action='store_true')
    parser.add_argument('--ownership-nand4bb', type=int, choices=(2, 4))
    args = parser.parse_args()
    if args.data7_pair_near_pin and (args.data_pin_placement != 'distributed-spaced' or args.output_ff != 'dfxtp_2'):
        parser.error('The placement experiment requires distributed-spaced pins and dfxtp_2')
    rebuild(args.output, args.tap, args.capture_cell, args.output_cell, args.output_ff,
            args.data_pin_placement, args.data7_pair_near_pin, args.ownership_nand4bb)
