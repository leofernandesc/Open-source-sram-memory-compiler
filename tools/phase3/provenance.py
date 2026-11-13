"""Read-only identity chain from the selected Phase 2 candidate to its fixture."""
import json
from pathlib import Path
import subprocess
from phase2_evidence import digest

BASELINE = 'origin/release/phase2-acceptance-20261111'


def selected_inputs(root, baseline=BASELINE):
    root = Path(root).resolve()
    pins = {}

    def checked(relative, expected=None):
        path = (root / relative).resolve(strict=True)
        if not path.is_relative_to(root):
            raise ValueError('Historical path outside repository: ' + str(relative))
        actual = digest(path)
        if expected is not None and actual != expected:
            raise ValueError('Historical hash mismatch: ' + str(relative))
        pins[str(path.relative_to(root))] = actual
        return path

    def load(relative, expected=None):
        return json.loads(checked(relative, expected).read_text())

    def anchored(relative):
        path = checked(relative)
        approved = subprocess.check_output(['git', '-C', str(root), 'show', baseline + ':' + relative])
        if path.read_bytes() != approved:
            raise ValueError('Selection differs from baseline: ' + relative)
        return json.loads(approved)

    def local_name(name):
        p = Path(name)
        if p.is_absolute():
            if p.is_relative_to('/work'):
                p = p.relative_to('/work')
            elif p.is_relative_to(root):
                p = p.relative_to(root)
            else:
                return None  # PDK pins are handled by the runner's model closure.
        return str(p)

    def edge(receipt, relative, expected):
        found = [h for name,h in receipt['inputs'].items() if local_name(name) == relative]
        if found != [expected]:
            raise ValueError('Historical identity edge differs: ' + relative)

    selector = anchored('release/phase2_current.json')
    candidate = anchored(selector['candidate_manifest'])
    if (candidate['status'] != selector['candidate_manifest_status_at_approval'] or
            candidate['branch'] != selector['branch_of_selected_implementation']):
        raise ValueError('Candidate selection identity/status differs')
    receipts = {}
    for name, proof in candidate['proof'].items():
        receipts[name] = load(proof['path'], proof['sha256'])
        if receipts[name]['status'] != proof['status']:
            raise ValueError('Candidate proof status differs: ' + name)
    for relative, info in candidate['payload'].items():
        checked(relative, info['sha256'])
    for name in ('physical_override', 'pilot_gate'):
        checked(candidate[name]['path'], candidate[name]['sha256'])
    for key, proof in (('electric_qualification','electrical'), ('physical_qualification','gds'), ('gls_qualification','gls')):
        if selector[key] != candidate['proof'][proof]['path']:
            raise ValueError('Selector receipt differs: ' + key)
    if (candidate['payload'][selector['chosen_gds']]['sha256'] != selector['chosen_gds_sha256'] or
            receipts['gds']['artifacts']['sram_4x8.gds'] != selector['chosen_gds_sha256']):
        raise ValueError('Selected GDS identity differs')
    checked(selector['chosen_gds'], selector['chosen_gds_sha256'])
    for name in ('electrical', 'fixture', 'gds'):
        folder = Path(candidate['proof'][name]['path']).parent
        for artifact, sha in receipts[name]['artifacts'].items():
            checked(folder / artifact, sha)
        for path, sha in receipts[name]['inputs'].items():
            relative = local_name(path)
            if relative is not None:
                checked(relative, sha)
    electrical, fixture, gds = (receipts[n] for n in ('electrical','fixture','gds'))
    fixture_path = candidate['proof']['fixture']['path']
    gds_path = candidate['proof']['gds']['path']
    edge(electrical, fixture_path, pins[fixture_path])
    for receipt in (electrical, fixture):
        edge(receipt, gds_path, pins[gds_path])
        extracted = str(Path(gds_path).parent / 'final_extracted.spice')
        edge(receipt, extracted, candidate['payload'][extracted]['sha256'])
    source = Path(selector['electric_qualification']).parent
    for name in ('binding.spice', 'fabric.spice'):
        sha = electrical['artifacts'][name]
        if electrical['simulation_inputs'][name] != sha or fixture['artifacts'][name] != sha:
            raise ValueError('Fixture/simulation netlist identity differs: ' + name)
        edge(electrical, str(Path(fixture_path).parent / name), sha)
    if candidate['payload'][str(source/'binding.spice')]['sha256'] != electrical['artifacts']['binding.spice']:
        raise ValueError('Selected binding differs from electrical receipt')
    return dict(baseline=baseline, candidate=selector['candidate_manifest'],
                qualification=selector['electric_qualification'], fixture=fixture_path,
                gds=selector['chosen_gds'], gds_sha256=selector['chosen_gds_sha256'], inputs=pins)
