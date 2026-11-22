"""Qualification must preserve source evidence and reject altered legacy runs."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
import phase3_rc_requalify as rq


class RequalificationTests(unittest.TestCase):
    def legacy_fixture(self, base):
        source = base / 'legacy'
        source.mkdir()
        netlist = ('.subckt phase3_rc_flat ' + ' '.join(rq.inspect_netlist.__globals__['EXPECTED_PINS']) + '\n'
                   + ''.join(f'X{i} VDD CLK VSS VSS nmos w=1 l=.15\n' for i in range(1493))
                   + 'R1 CLK int 10\nC0 int VSS 0\nC1 int VDD 1f\n.ends phase3_rc_flat\n')
        files = {
            'extracted_rc.spice': netlist,
            'magic.log': '\n'.join(rq.MARKERS) + '\n',
            'extract.tcl': ('gds read baseline.gds\nextresist threshold 0\n'
                            'extresist all\next2spice extresist on\n'),
            'phase3_rc_flat.ext': 'dummy', 'phase3_rc_flat.mag': 'dummy',
            'phase3_rc_flat.nodes': 'dummy', 'phase3_rc_flat.res.ext': 'dummy',
            'phase3_rc_flat.sim': 'dummy',
        }
        for name, content in files.items():
            (source / name).write_text(content)
        data = {'status': 'FAIL', 'error': rq.LEGACY_ERROR,
                'baseline_commit': rq.EXPECTED_BASELINE,
                'baseline_ref': rq.BASE_REF, 'gds_sha256': rq.EXPECTED_GDS,
                'artifacts': {name: rq.sha256(source / name) for name in files}}
        (source / 'manifest.json').write_text(json.dumps(data))
        return source

    def test_requalifies_into_new_directory_without_editing_failed_run(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(rq, 'check_baseline'):
            base = Path(temp)
            source = self.legacy_fixture(base)
            original_sha = rq.sha256(source / 'manifest.json')
            dest, extraction = rq.requalify(source, base / 'approved')
            state = json.loads((dest / 'manifest.json').read_text())
            self.assertEqual(state['status'], 'PASS_RC_NETLIST_STRUCTURE')
            self.assertEqual(state['qualification'], 'RETROSPECTIVE_STRUCTURE_ONLY')
            self.assertEqual((extraction['resistors'], extraction['zero_capacitors']), (1, 1))
            self.assertEqual(rq.sha256(source / 'manifest.json'), original_sha)
            self.assertEqual(rq.sha256(dest / 'extracted_rc.spice'), extraction['netlist_sha256'])

    def test_rejects_modified_original_artifacts(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(rq, 'check_baseline'):
            source = self.legacy_fixture(Path(temp))
            (source / 'phase3_rc_flat.mag').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'Original extraction artifact changed'):
                rq.verify(source)


if __name__ == '__main__':
    unittest.main()
