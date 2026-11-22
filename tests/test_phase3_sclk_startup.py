"""Offline tests for the phase markers and exact PWL audit."""

from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from diagnose_phase3_sclk_startup import Observations, SOURCE, audit_pwl, proc_sample, source_points


def stamp(elapsed):
    return {'elapsed_s':elapsed,'wall':'2026-11-20T16:00:00Z'}


class MonitorTests(unittest.TestCase):
    def test_silence_is_unknown_and_zero_point_is_not_positive_progress(self):
        obs = Observations()
        self.assertIsNone(obs.max_ns)
        obs.feed('stdout',b'__R87_DECK_READY__\n Reference value : 0.0\r',stamp(1))
        self.assertEqual(obs.max_ns,0.)
        self.assertNotIn('first_positive_reference',obs.events)
        self.assertEqual(obs.events['deck_ready']['elapsed_s'],1)

    def test_markers_handle_partial_pipe_reads_and_carriage_returns(self):
        obs = Observations()
        obs.feed('stdout',b'__R87_TRAN_DIS',stamp(1))
        obs.feed('stderr',b'Note: Transient op started\n',stamp(2))
        obs.feed('stdout',b'PATCH__\n Reference value : 2.5e-',stamp(3))
        obs.feed('stdout',b'10\r Reference value : 1e-10\r',stamp(4))
        self.assertEqual(obs.events['tran_dispatch']['elapsed_s'],3)
        self.assertEqual(obs.events['op_fallback_started']['stream'],'stderr')
        self.assertEqual(obs.events['first_positive_reference']['elapsed_s'],4)
        self.assertEqual(obs.max_ns,.25)
        self.assertEqual(obs.latest_ns,.1)

    def test_quiet_child_still_has_process_telemetry(self):
        with subprocess.Popen([sys.executable,'-c','import time; time.sleep(5)'],
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE) as proc:
            try:
                snap = proc_sample(proc.pid,stamp(1),None,None)
                self.assertEqual(snap['pid'],proc.pid)
                self.assertTrue(snap['exe'])
                self.assertGreater(snap['rss_kib'],0)
                self.assertIsNone(snap['reference_ns'])
            finally:
                proc.terminate()


class PwlTests(unittest.TestCase):
    def test_exact_collinearity_and_zero_interior_count(self):
        card = SOURCE.search(b'I_sclk_r87 a b PWL(0n 0 1n 0 2n 0\n+ 3n 0.5 4n 1 5n 0\n+ )\n')
        audit = audit_pwl(source_points(card),card)
        self.assertEqual(audit['point_count'],6)
        self.assertEqual(audit['zero_run_interior_points'],1)
        self.assertEqual(audit['exact_removable_points'],2)
        self.assertEqual(audit['peak_current_ns'],4.)

    def test_duplicate_timestamp_cannot_be_reported_as_continuous(self):
        card = SOURCE.search(b'I_sclk_r87 a b PWL(0n 0 2n 0 2n 1)\n')
        with self.assertRaisesRegex(ValueError,'strictly increasing'):
            source_points(card)


if __name__=='__main__':
    unittest.main()
