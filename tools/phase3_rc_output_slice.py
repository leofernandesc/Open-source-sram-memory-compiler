#!/usr/bin/env python3
"""Isolate the public CLK → capture FF → DATA path at one process corner."""
import argparse
import os
from pathlib import Path
import re
import subprocess

from phase3_rc_characterization import PDK
from run_phase3_eco_pex import finish, new_directory
from phase3_rc_extraction import sha256

HD_SPICE = Path('/opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice')


def generate(corner, parallel_driver=0, extra_copies=1, capture_slice=False):
    parasitics = {'light': {'q_ff': 5, 'total_data_ff': 24},
                  'heavy': {'q_ff': 6, 'total_data_ff': 45}}
    if capture_slice:
        # Rounded incident C from the reference DATA7 audit. Reducing
        # coupling to grounded capacitors makes this a screening model.
        parasitics = {'data7': {'clock_ff': 2.545, 'q_ff': 5.630, 'total_data_ff': 24.166}}
    lines = ['* Diagnostic isolated output path, external read ownership held',
             f'.lib "{PDK}" {corner}', f'.include "{HD_SPICE}"',
             '.temp 27', '.options klu method=gear',
             'VDD VDD 0 PWL(0 0 1n 1.8)',
             'VCLK CLK 0 PULSE(0 1.8 10n 50p 50p 9.95n 20n)',
             'VD D 0 PWL(0 0 33n 0 33.05n 1.8 53n 1.8 53.05n 0)']
    for size in (1, 2, 4):
        for load, caps in parasitics.items():
            name = f'x{size}_{load}'
            capture_size, ff_size = (size, 2) if capture_slice else (1, size)
            lines.extend([
                f'XCLK_{name} CLK 0 0 VDD VDD ck_{name} sky130_fd_sc_hd__clkinv_{capture_size}',
                f'XQ_{name} ck_{name} D 0 0 VDD VDD q_{name} sky130_fd_sc_hd__dfxtp_{ff_size}',
                f'XDATA_{name} q_{name} 0 0 0 VDD VDD data_{name} sky130_fd_sc_hd__ebufn_8',
                f'CQ_{name} q_{name} 0 {caps["q_ff"]}f',
                f'CL_{name} data_{name} 0 {caps["total_data_ff"]}f',
                f'.meas tran q50_{name} TRIG v(CLK) VAL=.9 FALL=2 TARG v(q_{name}) VAL=.9 RISE=1 TD=39n',
                f'.meas tran data80_{name} TRIG v(CLK) VAL=.9 FALL=2 TARG v(data_{name}) VAL=1.44 RISE=1 TD=39n',
                f'.meas tran data20_{name} TRIG v(CLK) VAL=.9 FALL=3 TARG v(data_{name}) VAL=.36 FALL=1 TD=59n',
            ])
            if capture_slice:
                lines.append(f'CCK_{name} ck_{name} 0 {caps["clock_ff"]}f')
            if parallel_driver:
                for copy in range(extra_copies):
                    extra = f'XDATA_EXTRA_{name}' if copy == 0 else f'XDATA_EXTRA{copy+1}_{name}'
                    lines.append(f'{extra} q_{name} 0 0 0 VDD VDD data_{name} '
                                 f'sky130_fd_sc_hd__ebufn_{parallel_driver}')
    return '\n'.join(lines + ['.tran 5p 65n 0 10p', '.end']) + '\n', parasitics


def generate_disable_path(corner, enable_nand=1):
    """Compare the live-read gate driving the eight local ownership gates."""
    loads = {'live_read_ff': 35.60701, 'te_b_ff': 3.79}
    lines = ['* Diagnostic read-to-write disable path with concentrated interconnect loads',
             f'.lib "{PDK}" {corner}', f'.include "{HD_SPICE}"',
             '.temp 27', '.options klu method=gear', 'VDD VDD 0 PWL(0 0 1n 1.8)',
             'VOE OEb 0 PWL(0 0 10n 0 10.05n 1.8)',
             'VWE WEb 0 PWL(0 1.8 10n 1.8 10.05n 0)',
             'VHOST HOST_EN 0 PWL(0 0 10.30n 0 10.35n 1.8)']
    for size in (1, 2, 4):
        lines.extend([
            f'XRISE_{size} OEb 0 WEb 0 0 VDD VDD live{size} sky130_fd_sc_hd__nor3b_{size}',
            f'CL_{size} live{size} 0 {loads["live_read_ff"]}f',
            f'.meas tran live20_x{size} TRIG v(OEb) VAL=.9 RISE=1 TARG v(live{size}) VAL=.36 FALL=1 TD=9n',
            f'.meas tran te80_x{size} TRIG v(OEb) VAL=.9 RISE=1 TARG v(te{size}_0) VAL=1.44 RISE=1 TD=9n',
        ])
        for bit in range(8):
            suffix = f'{size}_{bit}'
            lines.extend([
                f'XTE_{suffix} VDD live{size} 0 0 VDD VDD te{suffix} sky130_fd_sc_hd__nand2_{enable_nand}',
                f'CTE_{suffix} te{suffix} 0 {loads["te_b_ff"]}f',
                f'XDATA_{suffix} VDD te{suffix} 0 0 VDD VDD data{suffix} sky130_fd_sc_hd__ebufn_8',
                f'CDATA_{suffix} data{suffix} 0 10f',
            ])
    return '\n'.join(lines + ['.tran 5p 12n 0 5p', '.end']) + '\n', loads


def generate_direct_disable(corner, native_masks=False, native_nand=False):
    """Test logically equivalent local OR4 ownership logic for three masks."""
    loads = {'te_b_ff': 3.79}
    lines = ['* Local OR4 alternative: TE_B = OEb | CSb | !WEb | !READ_Q',
             f'.lib "{PDK}" {corner}', f'.include "{HD_SPICE}"',
             '.temp 27', '.options klu method=gear', 'VDD VDD 0 PWL(0 0 1n 1.8)',
             'VOE OEb 0 PWL(0 0 10n 0 10.05n 1.8 12n 1.8 12.05n 0)',
             'VWE WEb 0 PWL(0 1.8 20n 1.8 20.05n 0 22n 0 22.05n 1.8)',
             'VCS CSb 0 PWL(0 0 30n 0 30.05n 1.8)']
    for size in (1, 2, 4):
        if not native_masks and not native_nand:
            lines.append(f'XWEINV_{size} WEb 0 0 VDD VDD write{size} sky130_fd_sc_hd__inv_1')
        inputs = 'OEb CSb WEb VDD' if native_masks or native_nand else f'OEb CSb write{size} 0'
        gate = f'nand4bb_{size}' if native_nand else f'or4bb_{size}' if native_masks else f'or4_{size}'
        for bit in range(1 if native_nand else 8):
            suffix = f'{size}_{bit}'
            # READ_Q is held active throughout these independent mask events.
            lines.extend([
                f'XTE_{suffix} {inputs} 0 0 VDD VDD te{suffix} sky130_fd_sc_hd__{gate}',
                f'CTE_{suffix} te{suffix} 0 {loads["te_b_ff"]}f',
                f'XDATA_{suffix} VDD te{suffix} 0 0 VDD VDD data{suffix} sky130_fd_sc_hd__ebufn_8',
                f'CDATA_{suffix} data{suffix} 0 10f',
            ])
        for control, direction, after in (('OEb', 'RISE', 9), ('WEb', 'FALL', 19), ('CSb', 'RISE', 29)):
            lines.append(f'.meas tran te80_x{size}_{control.lower()} TRIG v({control}) VAL=.9 '
                         f'{direction}=1 TD={after}n TARG v(te{size}_0) VAL=1.44 RISE=1 TD={after}n')
    return '\n'.join(lines + ['.tran 5p 32n 0 5p', '.end']) + '\n', loads


def simulate(output, corner, parallel_driver=0, disable_path=False, enable_nand=1,
             direct_disable=False, native_masks=False, native_nand=False, extra_copies=1,
             capture_slice=False):
    output = new_directory(output)
    if direct_disable:
        deck, caps = generate_direct_disable(corner, native_masks, native_nand)
        measure_names, expected = r'te80_x\S+', 9
    elif disable_path:
        deck, caps = generate_disable_path(corner, enable_nand)
        measure_names, expected = r'(?:live20|te80)_x\S+', 6
    else:
        deck, caps = generate(corner, parallel_driver, extra_copies, capture_slice)
        measure_names, expected = r'(?:q50|data80|data20)_x\S+', 9 if capture_slice else 18
    (output / 'bench.spice').write_text(deck)
    command = ['ngspice', '-n', '-b', 'bench.spice']
    receipt = dict(status='ERROR', corner=corner, command=command, capacitive_loads=caps,
                   parallel_driver=parallel_driver, extra_copies=extra_copies if parallel_driver else 0,
                   disable_path=disable_path, direct_disable=direct_disable,
                   scope='isolated output path with explicit lumped loads; not macro RC or characterization',
                   models={str(path): sha256(path) for path in (HD_SPICE, PDK)})
    if disable_path:
        receipt['enable_nand'] = enable_nand
    if direct_disable:
        receipt['native_inverted_masks'] = native_masks
        receipt['native_nand'] = native_nand
    if capture_slice:
        receipt['capture_slice'] = 'DATA7 with fixed dfxtp_2 and concentrated incident capacitances'
    try:
        log = output / 'ngspice.log'
        with log.open('x') as stream:
            subprocess.run(command, cwd=output, stdout=stream, stderr=subprocess.STDOUT,
                           env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
                           check=True, timeout=300)
        measures = re.findall(r'(?m)^(' + measure_names + r')\s*=\s*([+0-9.e-]+)', log.read_text())
        receipt['measurements_s'] = {name: float(value) for name, value in measures}
        if len(measures) != expected or len(receipt['measurements_s']) != expected:
            raise ValueError('Unexpected measurement coverage in output-slice diagnostic')
        receipt.update(status='COMPLETE_DIAGNOSTIC', electrical_qualification='NOT_CHARACTERIZED')
    except Exception as error:
        receipt['error'] = str(error)
    finally:
        finish(output, receipt)
    return int(receipt['status'] != 'COMPLETE_DIAGNOSTIC')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--corner', required=True, choices=('tt', 'ss', 'ff'))
    variant = p.add_mutually_exclusive_group()
    variant.add_argument('--parallel-driver', type=int, choices=(0, 2, 4, 8), default=0)
    variant.add_argument('--disable-path', action='store_true')
    variant.add_argument('--direct-disable', action='store_true')
    variant.add_argument('--capture-slice', action='store_true')
    p.add_argument('--extra-copies', type=int, choices=(1, 2), default=1,
                   help='Count of additional drivers in a parallel-driver test')
    p.add_argument('--enable-nand', type=int, choices=(1, 2, 4), default=1,
                   help='Local NAND2 size when testing --disable-path')
    direct = p.add_mutually_exclusive_group()
    direct.add_argument('--native-masks', action='store_true', help='Use OR4BB with --direct-disable')
    direct.add_argument('--native-nand', action='store_true', help='Use NAND4BB with --direct-disable')
    args = p.parse_args()
    if not args.disable_path and args.enable_nand != 1:
        p.error('--enable-nand requires --disable-path')
    if (args.native_masks or args.native_nand) and not args.direct_disable:
        p.error('A native mask gate requires --direct-disable')
    if args.extra_copies != 1 and not args.parallel_driver:
        p.error('--extra-copies requires --parallel-driver')
    raise SystemExit(simulate(args.output, args.corner, args.parallel_driver, args.disable_path,
                              args.enable_nand, args.direct_disable, args.native_masks, args.native_nand,
                              args.extra_copies, args.capture_slice))
