#!/usr/bin/env python3
"""Real SKY130HD mapping and power-aware, zero-delay GLS. No macro STA claim."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from run_digital_regression import atomic_text, output_lock

ROOT = Path(__file__).resolve().parents[1]
HD = Path('/opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd')
LIB = HD / 'lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
MODELS = [HD / 'verilog/primitives.v', HD / 'verilog/sky130_fd_sc_hd.v']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mapped_inventory(design, top):
    cells = design['modules'][top].get('cells', {})
    inventory = Counter(c['type'] for c in cells.values())
    unknown = [name for name in inventory
               if not name.startswith('sky130_fd_sc_hd__') and name != 'sram_4x8_macro']
    if unknown:
        raise ValueError(f'Unmapped cells: {unknown}')
    if any('dlxt' in name or 'dlrt' in name for name in inventory):
        raise ValueError('Unexpected transparent latch')
    if top == 'sram_4x8_wrapper':
        if inventory['sram_4x8_macro'] != 1:
            raise ValueError('Expected exactly one custom SRAM macro')
        flops = sum(n for name, n in inventory.items() if name.startswith('sky130_fd_sc_hd__df'))
        if flops != 20 or inventory['sky130_fd_sc_hd__ebufn_1'] != 8:
            raise ValueError(f'Expected 20 capture/output FF and 8 tri-states: {inventory}')
    elif inventory['sky130_fd_sc_hd__ebufn_1'] != 1:
        raise ValueError('Pilot must contain exactly one mapped tri-state')
    return dict(sorted(inventory.items()))


def add_power(text):
    """Bind all mapped HD four-rail interfaces explicitly, including body rails."""
    return re.sub(r'(sky130_fd_sc_hd__\w+\s+\\?[^\s(]+\s*\()',
                  r'\1\n    .VPWR(VDD), .VGND(VSS), .VPB(VDD), .VNB(VSS),', text)


def run(output):
    receipt = {'status': 'RUNNING', 'F2_DIG': 'NOT_EVALUATED', 'F2_FIS': 'NOT_EVALUATED',
               'scope': 'SKY130HD mapping and power-aware zero-delay GLS; functional macro substitute',
               'timing': 'Custom macro has no characterized timing model; no SRAM timing closure',
               'commands': []}
    def publish():
        atomic_text(output / 'results.json', json.dumps(receipt, indent=2) + '\n')
    publish()
    try:
        for name in ('yosys', 'iverilog', 'vvp', 'openroad'):
            if shutil.which(name) is None:
                raise RuntimeError(f'Missing tool: {name}; run through tools/sram-eda')
        for path in [LIB, *MODELS]:
            if not path.is_file():
                raise RuntimeError(f'Missing PDK view: {path}')
        build_root = ROOT / 'build/phase2'
        build_root.mkdir(parents=True, exist_ok=True)
        build = Path(tempfile.mkdtemp(prefix='digital-', dir=build_root))
        receipt['build_directory'] = str(build.relative_to(ROOT))
        sources = [*ROOT.glob('rtl/*.v'), ROOT / 'tb/tb_sram_4x8.sv', ROOT / 'tb/sram_ref_model.sv',
                   *ROOT.glob('synth/*.v'), *ROOT.glob('verification/phase2/*.sv'),
                   ROOT / 'tools/run_phase2_digital.py', ROOT / 'tools/run_digital_regression.py',
                   ROOT / 'scripts/run_synth.sh', ROOT / 'tools/sram-eda']
        hashes = {}
        for source in sources:
            rel = source.relative_to(ROOT)
            target = build / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            hashes[str(rel)] = sha(source)
        receipt['inputs'] = hashes
        receipt['pdk'] = {str(p): sha(p) for p in [LIB, *MODELS]}
        def command(args, log, timeout=180, expected_exit=0):
            env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
            receipt['commands'].append({'argv': [str(a) for a in args], 'cwd': str(build), 'log': log})
            result = subprocess.run([str(a) for a in args], cwd=build, env=env,
                                    capture_output=True, text=True, timeout=timeout)
            atomic_text(output / log, result.stdout + result.stderr)
            if result.returncode != expected_exit:
                raise RuntimeError(f'{args[0]} failed ({result.returncode}); see {log}')
            return result.stdout + result.stderr
        receipt['versions'] = {name: command([name, option], name + '_version.txt').strip()
                               for name, option in [('yosys', '-V'), ('iverilog', '-V'), ('openroad', '-version')]}
        for top, names in [('tristate_pilot', ['synth/tristate_pilot.v']),
                           ('sram_4x8_wrapper', ['rtl/sram_controller.v', 'rtl/sram_4x8_macro_bb.v',
                                                 'rtl/sram_4x8_wrapper.v'])]:
            script = f'''read_liberty -lib {LIB}
read_verilog {' '.join(names)}
tribuf
synth -top {top} -flatten -noabc
dfflibmap -liberty {LIB}
techmap -map synth/sky130_tristate.v
techmap
abc -liberty {LIB}
clean
check -assert
stat -liberty {LIB}
write_json {top}.json
write_verilog -noattr -noexpr {top}.v
'''
            (build / f'{top}.ys').write_text(script)
            shutil.copyfile(build / f'{top}.ys', output / f'{top}.ys')
            command(['yosys', '-Q', '-T', '-s', top + '.ys'], top + '_synthesis.txt')
            design = json.loads((build / f'{top}.json').read_text())
            receipt[top] = mapped_inventory(design, top)
            powered = add_power((build / f'{top}.v').read_text())
            (build / f'{top}_powered.v').write_text(powered)
            shutil.copyfile(build / f'{top}_powered.v', output / f'{top}_powered.v')
            shutil.copyfile(build / f'{top}.json', output / f'{top}.json')
            common = ['iverilog', '-g2012', '-DFUNCTIONAL', '-DUSE_POWER_PINS', '-DUNIT_DELAY=#0',
                      *MODELS, build / f'{top}_powered.v']
            if top == 'tristate_pilot':
                command([*common, 'verification/phase2/tb_tristate.sv', '-s', 'tb_tristate', '-o', 'pilot.vvp'],
                        'tristate_compile.txt')
                transcript = command(['vvp', 'pilot.vvp'], 'tristate_gls.txt')
                if re.findall(r'^TRISTATE_RESULT checks=(\d+)$', transcript, re.M) != ['8']:
                    raise ValueError('Missing or unexpected tri-state checks')
                mutant, count = re.subn(r'\.TE_B\(([^)]+)\)', r'.TE_B(~(\1))', powered)
                if count != 1:
                    raise ValueError('Cannot inject isolated tri-state polarity defect')
                (build / 'tristate_mutant.v').write_text(mutant)
                command(['iverilog', '-g2012', '-DFUNCTIONAL', '-DUSE_POWER_PINS', '-DUNIT_DELAY=#0',
                         *MODELS, 'tristate_mutant.v', 'verification/phase2/tb_tristate.sv',
                         '-s', 'tb_tristate', '-o', 'mutant.vvp'], 'tristate_mutant_compile.txt')
                negative = command(['vvp', 'mutant.vvp'], 'tristate_mutant.txt', expected_exit=1)
                if (len(re.findall(r'^FATAL: .*tri-state DATA=', negative, re.M)) != 1 or
                        'Scope: tb_tristate.check' not in negative or 'watchdog' in negative):
                    raise ValueError('Unexpected tri-state mutant diagnostic')
                receipt['tristate_negative'] = 'POLARITY_DEFECT_REJECTED_BY_SCOREBOARD'
            else:
                command([*common, '-DTEST_WRAPPER', 'rtl/sram_4x8_macro_model.v',
                         'tb/sram_ref_model.sv', 'tb/tb_sram_4x8.sv', '-s', 'tb_sram_4x8', '-o', 'wrapper.vvp'],
                        'wrapper_compile.txt')
                transcript = command(['vvp', 'wrapper.vvp', '+seed=23063', '+random_ops=2048'], 'wrapper_gls.txt')
                records = re.findall(r'^RESULT (\{.*\})$', transcript, re.M)
                if len(records) != 1:
                    raise ValueError('Expected one raw GLS RESULT')
                result = json.loads(records[0])
                if (result['depth'] != 4 or result['seed'] != 23063 or result['random_ops'] != 2048
                        or result['control_transitions'] != 64 or result['checks'] <= 0
                        or any(n <= 0 for n in result['controls'] + result['read_addresses'] + result['write_addresses'])):
                    raise ValueError(f'Incomplete GLS coverage: {result}')
                receipt['gls_result'] = result
        for rel, expected in hashes.items():
            if sha(ROOT / rel) != expected or sha(build / rel) != expected:
                raise ValueError(f'Source changed during run: {rel}')
        if any(sha(Path(p)) != expected for p, expected in receipt['pdk'].items()):
            raise ValueError('PDK input changed during run')
        receipt.update(status='PASS', F2_DIG='PASS_FUNCTIONAL_MAPPING_GLS', F2_FIS='NOT_EVALUATED')
    except Exception as error:
        receipt.update(status='FAIL', error=str(error))
    receipt['artifacts'] = {p.name: sha(p) for p in output.iterdir()
                            if p.is_file() and p.name not in ('results.json', '.run.lock')}
    publish()
    print(json.dumps({k: receipt[k] for k in ('status', 'F2_DIG', 'F2_FIS')}, indent=2))
    if receipt.get('error'):
        print(receipt['error'])
    return 0 if receipt['status'] == 'PASS' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='reports/phase2/digital_checkpoint')
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    if not output.is_relative_to(ROOT / 'reports/phase2') or output == ROOT / 'reports/phase2':
        parser.error('Output must be a subdirectory of reports/phase2')
    output.mkdir(parents=True, exist_ok=True)
    with output_lock(output):
        return run(output)


if __name__ == '__main__':
    raise SystemExit(main())
