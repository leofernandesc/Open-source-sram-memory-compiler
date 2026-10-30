"""Protect net isolation and provenance; physical DRC/LVS are separate checks."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from build_layout import parse_devices
from compact_routing import compact_plan
import layout_provenance as provenance


class CompactRoutingTests(unittest.TestCase):
    def setUp(self):
        self.devices = parse_devices((Path(__file__).parent / 'row_decoder_import.spice').read_text())
        self.plan = compact_plan(self.devices)

    def test_shared_precharge_stack_columns_escape_to_different_nets(self):
        for pmos, upper, lower in ((5, 6, 7), (11, 12, 13), (16, 17, 18), (21, 22, 23)):
            p, n, next_n = (f'XM{i}' for i in (pmos, upper, lower))
            x = self.plan.placement[n][0]
            self.assertEqual(x, self.plan.placement[p][0])
            self.assertNotEqual(self.plan.gate_offset[p], self.plan.gate_offset[n])
            # Regression: an intermediate stack node must never use VDD's
            # vertical escape. Align it exactly with the next stack drain.
            self.assertNotEqual(self.plan.source_offset[p], self.plan.source_offset[n])
            self.assertEqual(x+self.plan.source_offset[n], self.plan.placement[next_n][0]-300)

    def test_local_tracks_are_finite_and_separate_on_shared_layers(self):
        for row in range(4):
            for net in (f'N{row}', f'net{row+1}', f'DEC{row}'):
                lo, hi = self.plan.extents[net]
                self.assertLess(hi-lo, 3500)
        for a, (lo, hi) in self.plan.extents.items():
            for b, (blo, bhi) in self.plan.extents.items():
                if a != b and self.plan.tracks[a] == self.plan.tracks[b]:
                    self.assertTrue(hi+120 <= blo or bhi+120 <= lo)

    def test_short_shared_via_islands_have_metal3_minimum_area(self):
        for lo, hi in self.plan.extents.values():
            self.assertGreaterEqual((hi-lo)*60*.005**2, .24)

    def test_nine_public_pins_preserve_logical_interface(self):
        self.assertEqual(set(self.plan.port_x), {'VDD','VSS','PCLK','A0','A1','DEC0','DEC1','DEC2','DEC3'})
        self.assertEqual(len(self.plan.placement), 29)


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        layout = root/'layout/row_decoder'
        (layout/'pex').mkdir(parents=True)
        (root/'cells/row_decoder').mkdir(parents=True)
        (root/'cells/row_decoder/row_decoder.sch').write_text('source circuit\n')
        (layout/'row_decoder_flat.mag').write_text('magic\ntimestamp 1\nrect 0 0 200 60\n')
        (layout/'pex/row_decoder_pex.spice').write_text('extracted test fixture\n')
        self.layout, self.root = layout, root
        for key, value in (('ROOT',root),('LAYOUT',layout),('STATE',layout/'pex/provenance.json')):
            patcher = patch.object(provenance, key, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def current(self):
        provenance.write_state(top_drc=0, flat_drc=0, lvs=True, current=True)

    def test_lvs_only_never_qualifies_historical_pex(self):
        provenance.write_state(top_drc=0, flat_drc=0, lvs=True)
        with self.assertRaisesRegex(ValueError, 'stale'):
            provenance.require_current_pex()

    def test_changed_layout_is_rejected(self):
        self.current()
        with (self.layout/'row_decoder_flat.mag').open('a') as stream:
            stream.write('rect 200 0 400 60\n')
        with self.assertRaisesRegex(ValueError, 'layout_sha256'):
            provenance.require_current_pex()

    def test_changed_schematic_is_rejected(self):
        self.current()
        (self.root/'cells/row_decoder/row_decoder.sch').write_text('different circuit\n')
        with self.assertRaisesRegex(ValueError, 'schematic_sha256'):
            provenance.require_current_pex()

    def test_replaced_pex_is_rejected(self):
        self.current()
        (self.layout/'pex/row_decoder_pex.spice').write_text('different extraction\n')
        with self.assertRaisesRegex(ValueError, 'pex_sha256'):
            provenance.require_current_pex()

    def test_eol_and_nonphysical_timestamp_changes_are_portable(self):
        self.current()
        (self.layout/'row_decoder_flat.mag').write_bytes(b'magic\r\ntimestamp 99\r\nrect 0 0 200 60\r\n')
        self.assertEqual(provenance.require_current_pex()['status'], 'current')

    def test_drc_or_lvs_failure_prevents_binding(self):
        for kwargs in (dict(top_drc=1,flat_drc=0,lvs=True),dict(top_drc=0,flat_drc=0,lvs=False)):
            with self.assertRaises(ValueError):
                provenance.write_state(current=True, **kwargs)


if __name__ == '__main__':
    unittest.main()
