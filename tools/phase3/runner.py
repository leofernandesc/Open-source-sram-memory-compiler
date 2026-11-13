"""Pinned, isolated ngspice execution with durable receipts and bounded resources."""
import csv
import json
import os
from pathlib import Path
import re
import resource
import shlex
import signal
import shutil
import subprocess
import sys
import time

from phase2_evidence import digest
from phase2_resources import preflight
from .contract import FIELDS, rows, validate

ROOT = Path(__file__).resolve().parents[2]


class Blocked(Exception):
    pass


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def write_json(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    tmp.replace(path)


def snapshot(path, destination, inventory, copied):
    """Copy and rewrite the complete textual .include/.lib closure, including all corners.

    Unsupported dynamic paths fail closed. Original and rewritten bytes are hashed.
    """
    path = path.resolve(strict=True)
    if path in copied:
        return copied[path]
    target = destination / (str(len(copied)) + '.spice')
    copied[path] = target
    before = digest(path)
    inventory[str(path)] = before
    lines = []
    for line in path.read_text().splitlines():
        parts = shlex.split(line, comments=False) if re.match(r'^\s*\.(include|inc|lib)\b', line, re.I) else []
        if parts and (parts[0].lower() in ('.include', '.inc') or len(parts) >= 3):
            child = Path(parts[1])
            if '$' in str(child) or '{' in str(child):
                raise ValueError('Dynamic include unsupported: ' + line)
            child = child if child.is_absolute() else path.parent / child
            saved = snapshot(child, destination, inventory, copied)
            line = parts[0] + ' "' + saved.name + '"' + (' ' + ' '.join(parts[2:]) if len(parts) > 2 else '')
        lines.append(line)
    if digest(path) != before:
        raise ValueError('Input changed during snapshot: ' + str(path))
    target.write_text('\n'.join(lines) + '\n')
    return target


def run(config_path, output, dry_run=False):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / 'reports/phase3') or output == ROOT / 'reports/phase3':
        raise ValueError('Use a new directory below reports/phase3')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()  # atomic reservation; never reuse even failed directories
    receipt = dict(schema_version=1, run_id=output.name, status='ERROR', electrical_simulation_performed=False,
                   sram_characterized=False, dry_run=dry_run, inputs={}, evidence={}, measurements=[])
    c = None
    log_text = ''
    started = time.monotonic()
    def publish():
        receipt['elapsed_s'] = time.monotonic() - started
        receipt['evidence'] = {str(p.relative_to(output)): digest(p) for p in output.rglob('*')
                               if p.is_file() and p.name not in ('manifest.json', 'manifest.tmp')}
        write_json(output / 'manifest.json', receipt)
    publish()
    try:
        raw = Path(config_path).read_bytes()
        (output / 'config.json').write_bytes(raw)
        c = validate(json.loads(raw))
        code = output / 'source_snapshot'
        code.mkdir()
        for src in [Path(__file__), Path(__file__).with_name('contract.py'), ROOT/'tools/phase2_evidence.py', ROOT/'tools/phase2_resources.py', ROOT/'tools/run_phase3.py', Path(__file__).with_name('__init__.py')]:
            if src.is_file():
                shutil.copyfile(src, code/src.name)
                receipt['inputs'][str(src)] = digest(src)
        receipt['configuration'] = c
        receipt['git'] = dict(commit=git('rev-parse', 'HEAD'), branch=git('branch', '--show-current'),
                              dirty=bool(git('status', '--porcelain')))
        ref = c['baseline']
        base = git('rev-parse', '--verify', ref + '^{commit}')
        if subprocess.run(['git', '-C', str(ROOT), 'merge-base', '--is-ancestor', base, 'HEAD']).returncode:
            raise Blocked('Baseline is not an ancestor')
        receipt['baseline'] = dict(identifier=ref, commit=base)
        selector = ROOT / 'release/phase2_current.json'
        frozen = subprocess.check_output(['git', '-C', str(ROOT), 'show', base + ':release/phase2_current.json'])
        if selector.read_bytes() != frozen:
            raise Blocked('Release selector differs from baseline')
        receipt['inputs'][str(selector)] = digest(selector)
        try:
            receipt['resources'] = preflight(output)
        except ValueError as error:
            raise Blocked(str(error)) from error
        work = output / 'inputs'
        work.mkdir()
        copied = {}
        paths = {}
        for name in ('netlist', 'model', 'deck'):
            p = Path(c[name]['path'])
            p = p if p.is_absolute() else ROOT / p
            if not p.is_file():
                raise Blocked('Missing input: ' + str(p))
            if digest(p) != c[name]['sha256']:
                raise ValueError('Hash mismatch: ' + str(p))
            paths[name] = p
        if not re.search(r'^\s*\.lib\s+' + c['corner'] + r'\s*$', paths['model'].read_text(), re.M | re.I):
            raise Blocked('Corner not declared in selected model')
        netlist = snapshot(paths['netlist'], work, receipt['inputs'], copied)
        model = snapshot(paths['model'], work, receipt['inputs'], copied)
        # Deck dependencies use the same snapshot mechanism; placeholders remain literal.
        template = paths['deck'].read_text()
        if not all('{{' + key + '}}' in template for key in ('MODEL', 'CORNER', 'NETLIST')):
            raise ValueError('Deck must use pinned MODEL, CORNER and NETLIST placeholders')
        lines = []
        for line in template.splitlines():
            parts = shlex.split(line, comments=False) if re.match(r'^\s*\.(include|inc|lib)\b', line, re.I) else []
            if parts and (parts[0].lower() in ('.include', '.inc') or len(parts) >= 3) and '{{' not in parts[1]:
                dependency = Path(parts[1])
                if not dependency.is_absolute():
                    dependency = paths['deck'].parent / dependency
                line = parts[0] + ' \"' + str(dependency.resolve()) + '\"' + (' ' + ' '.join(parts[2:]) if len(parts) > 2 else '')
            lines.append(line)
        template = '\n'.join(lines) + '\n'
        receipt['inputs'][str(paths['deck'].resolve())] = digest(paths['deck'])
        values = dict(NETLIST=netlist.name, MODEL=model.name, CORNER=c['corner'], VDD=c['vdd_v'],
                      TEMP=c['temp_c'], PERIOD=c['period_ns'] * 1e-9, SLEW=c['slew_ps'] * 1e-12,
                      HIGH=c['period_ns'] * c['duty_cycle'] * 1e-9, LOAD=c['load_ff'] * 1e-15)
        for key, value in values.items():
            template = template.replace('{{' + key + '}}', str(value))
        if '{{' in template:
            raise ValueError('Unresolved deck placeholder')
        # Stage the rendered deck too, so every static dependency is captured.
        rendered = work / 'rendered.spice'
        rendered.write_text(template)
        # Includes generated above are already in work; resolve/rewrite any extra dependencies.
        deck = snapshot(rendered, work, receipt['inputs'], copied)
        receipt['input_snapshots'] = {str(p): str(q.relative_to(output)) for p,q in copied.items()}
        receipt['command'] = ['ngspice', '-n', '-b', deck.name]
        receipt['cwd'] = str(work)
        receipt['tools'] = {'python': sys.version, 'git': git('--version')}
        try:
            receipt['tools']['ngspice'] = subprocess.check_output(['ngspice', '--version'], stderr=subprocess.STDOUT, text=True, timeout=10).strip()
        except FileNotFoundError:
            receipt['tools']['ngspice'] = None
        executable = shutil.which('ngspice')
        if executable:
            receipt['tools']['ngspice_executable'] = dict(path=executable, sha256=digest(executable))
        if dry_run:
            receipt['status'] = 'NOT_CHARACTERIZED'
        else:
            if receipt['tools']['ngspice'] is None:
                raise Blocked('ngspice unavailable')
            def limits():
                resource.setrlimit(resource.RLIMIT_AS, (int(c['memory_mb']*2**20),) * 2)
                resource.setrlimit(resource.RLIMIT_CPU, (int(c['timeout_s']) + 1,) * 2)
                resource.setrlimit(resource.RLIMIT_FSIZE, (512*2**20,) * 2)
                os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
            with (output / 'ngspice.log').open('w') as log:
                publish()
                proc = subprocess.Popen(receipt['command'], cwd=work, stdout=log, stderr=subprocess.STDOUT,
                                        env=dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1'),
                                        preexec_fn=limits, start_new_session=True)
                receipt['electrical_simulation_performed'] = True
                publish()
                try:
                    receipt['return_code'] = proc.wait(timeout=c['timeout_s'])
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                    raise TimeoutError('ngspice timeout; process group killed; partial evidence retained')
            log_text = (output / 'ngspice.log').read_text(errors='replace')
            if proc.returncode or re.search(r'(?im)^\s*(fatal|error)(?:\b|:)', log_text):
                raise RuntimeError('Simulator error; inspect ngspice.log')
            receipt['status'] = 'PASS'
        for p, h in receipt['inputs'].items():
            if digest(p) != h:
                raise ValueError('Input changed during execution: ' + p)
        receipt['measurements'] = rows(c, output.name, log_text, dry_run)
        if not dry_run:
            statuses = {r['status'] for r in receipt['measurements']}
            if 'FAIL' in statuses:
                receipt['status'] = 'FAIL'
            elif not statuses or 'NOT_CHARACTERIZED' in statuses:
                receipt['status'] = 'NOT_CHARACTERIZED'
    except Blocked as e:
        receipt.update(status='BLOCKED', error=str(e))
    except Exception as e:
        receipt.update(status='ERROR', error=type(e).__name__ + ': ' + str(e))
    finally:
        # Partial values are not promoted after an execution/integrity error.
        if c and not receipt['measurements']:
            receipt['measurements'] = rows(c, output.name, '', True)
            for row in receipt['measurements']:
                row['reason'] = receipt.get('error', 'no completed measurements')
        with (output / 'metrics.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(receipt['measurements'])
        publish()
    return receipt
