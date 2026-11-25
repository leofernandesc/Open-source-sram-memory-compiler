"""Unit checks for physical-fault stimulus and native-sample detection.

Synthetic samples test the detector only. Physical evidence requires ngspice.
"""

import json
import tempfile
from pathlib import Path
import unittest

import numpy as np

from phase3_bus_physical_controls import CONTROL_WINDOWS, change_deck, check_witness
from phase3_rc_read_path import OUTPUT_ENABLES


ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / 'build/phase3/integrated_replay_247p5/FF/bench.spice'


class PhysicalControlsTest(unittest.TestCase):
    def test_fault_deck_edits_only_selected_cycle(self):
        baseline = BASELINE.read_text()
        for mode, (cycle, stop_ns, _, _) in CONTROL_WINDOWS.items():
            with self.subTest(mode=mode):
                deck = change_deck(baseline, mode)
                self.assertIn(f'tran 10p {stop_ns:g}n 0 25p', deck)
                self.assertNotIn('tran 10p 370n 0 25p', deck)
                self.assertEqual(deck.count('V_FAULT_SUPPLY4'),
                                 1 if mode.endswith('contention') else 0)
                if mode.endswith('contention'):
                    self.assertIn('v_sense_fault4 FAULT_METER4 DUT_DATA4 0', deck)
                if cycle == 10:
                    self.assertIn('48.050000n 1.8', deck)
                    self.assertIn('208.550000n 0' if mode.endswith('no_host')
                                  else '208.550000n 1.8', deck)
                    if mode == 'c10_stuck_weak':
                        self.assertIn('209.550000n 1.8 209.600000n 0', deck)
                    if mode == 'c10_delayed_release':
                        self.assertIn('207.05n 0 209.50n 0 209.55n 1.8', deck)
                        self.assertIn('207.05n 1.8 209.50n 1.8 209.55n 0', deck)
                        for signal in ('CSb', 'HOST_EN', 'ADDR0', 'ADDR1'):
                            source_line = next(line for line in baseline.splitlines()
                                               if line.startswith(f'V_{signal} '))
                            self.assertIn(source_line, deck)

    def test_detector_requires_conservative_current_and_duration(self):
        for mode, (_, stop_ns, start_ns, end_ns) in CONTROL_WINDOWS.items():
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                times_ns = np.arange(0, int(stop_ns * 100) + 1) / 100
                window = (times_ns >= start_ns) & (times_ns <= end_ns)
                host_en = np.zeros(len(times_ns))
                host_current = np.zeros(len(times_ns))
                if mode == 'c10_delayed_release':
                    macro_current = np.zeros(len(times_ns))
                    macro_gate = np.full(len(times_ns), 1.8)
                    host_en[window] = 1.8
                    host_current[window] = -0.001
                    macro_current[window] = 0.001
                    macro_gate[window] = 0.0
                    (Path(tmp) / 'probes.json').write_text(
                        json.dumps({OUTPUT_ENABLES[4]: 'control_te'}))
                    header = ('time v(host_en) i(v_sense_host4) i(v_dut4) '
                              'v(xdut.control_te)')
                    columns = [times_ns * 1e-9, host_en, host_current, macro_current,
                               macro_gate]
                elif mode == 'c10_stuck_weak':
                    host_weak_en = np.zeros(len(times_ns))
                    host_en[window] = 1.8
                    host_weak_en[window] = 1.8
                    header = 'time v(host_en) i(v_sense_host4) v(host_weak_en)'
                    columns = [times_ns * 1e-9, host_en, host_current, host_weak_en]
                elif mode.endswith('contention'):
                    fault_en = np.zeros(len(times_ns))
                    fault_current = np.zeros(len(times_ns))
                    macro_current = np.zeros(len(times_ns))
                    host_en[window] = 1.8
                    fault_en[window] = 1.8
                    host_current[window] = -0.001
                    macro_current[window] = 0.001
                    fault_current[window] = 0.001
                    header = ('time v(host_en) i(v_sense_host4) i(v_dut4) '
                              'v(fault_en4) i(v_sense_fault4)')
                    columns = [times_ns * 1e-9, host_en, host_current, macro_current,
                               fault_en, fault_current]
                else:
                    header = 'time v(host_en) i(v_sense_host4)'
                    columns = [times_ns * 1e-9, host_en, host_current]
                wave = Path(tmp) / 'waveform.dat'
                np.savetxt(wave, np.column_stack(columns), header=header, comments='')
                self.assertTrue(check_witness(wave, mode)['fault_detected'])

                if mode == 'c10_delayed_release':
                    columns[3][window] = -0.001  # Currents cease opposing.
                    np.savetxt(wave, np.column_stack(columns), header=header, comments='')
                    self.assertFalse(check_witness(wave, mode)['fault_detected'])
                    columns[3][window] = 0.001

                if mode.endswith('contention'):
                    columns[-1][window] = -0.001  # Same-direction currents.
                elif mode == 'c10_delayed_release':
                    columns[-1][window] = 1.8  # Read driver gate released.
                elif mode == 'c10_stuck_weak':
                    columns[-1][window] = 0.0  # Weak host released on schedule.
                else:
                    columns[1][window] = 1.8  # Host unexpectedly enabled.
                np.savetxt(wave, np.column_stack(columns), header=header, comments='')
                self.assertFalse(check_witness(wave, mode)['fault_detected'])


if __name__ == '__main__':
    unittest.main()
