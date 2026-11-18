"""Regression coverage for the saved Phase 3 diagnostic comparison."""

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))

from phase3_rc_characterization import PUBLIC
from phase3_rc_probe_report import read_waveform, voltage, incident_capacitance
from phase3_rc_read_path import settled_ns


class ProbeReportTests(unittest.TestCase):
    @staticmethod
    def waveform(path, public=None, internals=None, samples=None):
        header = ['time', *(p.lower() for p in PUBLIC)] if public is None else public
        header += ['v(xdut.bar)', 'v(xdut.foo)'] if internals is None else internals
        times = [129e-9, 133e-9, 164e-9, 170e-9]
        rows = []
        for index, time in enumerate(times):
            values = [0.] * (len(header) - 1)
            values[header.index('v(xdut.foo)') - 1] = (0., 1., 3., 5.)[index]
            values[header.index('v(xdut.bar)') - 1] = (1., 2., 4., 6.)[index]
            rows.append([time, *values])
        if samples is not None:
            rows = samples
        path.write_text(' '.join(header) + '\n' +
                        '\n'.join(' '.join(str(value) for value in row) for row in rows) + '\n')

    def test_probe_mapping_uses_actual_waveform_order(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'waveform.dat'
            self.waveform(path)
            rows, indices = read_waveform(path, ['foo', 'bar'])
            times = [row[0] for row in rows]
            self.assertEqual(indices, {'foo': 13, 'bar': 12})
            self.assertAlmostEqual(voltage(rows, times, 131, indices['foo']), .5)
            self.assertAlmostEqual(voltage(rows, times, 131, indices['bar']), 1.5)

    def test_ngspice_branch_alias_and_vector_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'waveform.dat'
            public = ['time', *(p.lower() for p in PUBLIC)]
            public[-1] = 'vdd_src#branch'
            self.waveform(path, public=public.copy())
            self.assertEqual(len(read_waveform(path, ['bar', 'foo'])[0]), 4)

            reordered = public.copy()
            reordered[2], reordered[3] = reordered[3], reordered[2]
            self.waveform(path, public=reordered)
            with self.assertRaisesRegex(ValueError, 'Unexpected waveform vectors'):
                read_waveform(path, ['foo', 'bar'])

            self.waveform(path)
            lines = path.read_text().splitlines()
            lines[0] = lines[0].replace('v(xdut.bar)', 'v(xdut.foo)')
            path.write_text('\n'.join(lines) + '\n')
            with self.assertRaisesRegex(ValueError, 'Unexpected waveform vectors'):
                read_waveform(path, ['foo', 'bar'])

    def test_incomplete_nonfinite_and_nonmonotonic_samples_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'waveform.dat'
            self.waveform(path)
            lines = path.read_text().splitlines()

            path.write_text('\n'.join([lines[0], *lines[1:-1], lines[-1] + ' 1']) + '\n')
            with self.assertRaisesRegex(ValueError, 'Incomplete waveform sample'):
                read_waveform(path, ['foo', 'bar'])

            nonfinite = lines.copy()
            nonfinite[1] = nonfinite[1].replace('0.0', 'nan', 1)
            path.write_text('\n'.join(nonfinite) + '\n')
            with self.assertRaisesRegex(ValueError, 'Nonfinite waveform sample'):
                read_waveform(path, ['foo', 'bar'])

            nonmonotonic = lines.copy()
            nonmonotonic[3] = nonmonotonic[2]
            path.write_text('\n'.join(nonmonotonic) + '\n')
            with self.assertRaisesRegex(ValueError, 'Nonmonotonic waveform time'):
                read_waveform(path, ['foo', 'bar'])

    def test_capacitance_totals_are_incident_not_equivalent_load(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'binding.spice'
            path.write_text('C1 foo VDD 3e-15\nC2 foo bar 4e-15\nC3 foo VSS 1e-15\n')
            self.assertEqual(incident_capacitance(path, ['foo'])['foo'],
                             {'rail_ff': 4., 'other_ff': 4., 'pairs': 3})

    def test_settling_requires_both_sense_outputs_to_hold_until_capture(self):
        times = [ns * 1e-9 for ns in range(1, 6)]
        rows = list(zip(times, [0., 1.8, 1.8, 1.8, 1.8], [1.8, 0., 1.8, 0., 0.]))
        pair = [(1, 1), (2, 0)]
        self.assertIsNone(settled_ns(rows, times, pair, 1., 3.))
        self.assertAlmostEqual(settled_ns(rows, times, pair, 1., 5.), 3.8)
        self.assertAlmostEqual(settled_ns(rows, times, pair, 4.5, 5.), 4.5)


if __name__ == '__main__':
    unittest.main()
