"""Offline checks for the reduced TT PWL and per-seed failure handling."""

from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from run_phase3_data3_tt import points, reduced_points, value_at
from run_phase3_snm import design, run_case
from validate_phase3_snm_nominal_pilot import batch


class ReplayTests(unittest.TestCase):
    def test_reduced_card_keeps_prefix_and_removes_nonretained_cycles(self):
        example = ('V_CLK CLK 0 PWL(0n 0 110n 0 110.05n 1.8 120n 1.8 120.05n 0 '
                   '130n 0 130.05n 1.8 140n 1.8 140.05n 0 '
                   '170n 0 170.05n 1.8 180n 1.8 180.05n 0)')
        _, original = points(example)
        actual = reduced_points(original)
        self.assertEqual(actual[:5],original[:5])
        self.assertEqual([t for t,_ in actual[5:]],list(map(Decimal,('130','130.05','140','140.05'))))
        self.assertEqual(value_at(actual,Decimal('130.025')),Decimal('.9'))

    def test_join_preserves_the_previous_voltage_before_the_next_ramp(self):
        _, original = points('V_ADDR0 ADDR0 0 PWL(0n 0 107n 0 107.05n 1.8 '
                             '127n 1.8 127.05n 0 167n 0 167.05n 0 207n 0 207.05n 1.8)')
        actual = reduced_points(original)
        self.assertEqual(value_at(actual,Decimal('126.9')),Decimal('1.8'))
        self.assertEqual(value_at(actual,Decimal('127.025')),Decimal('.9'))
        self.assertEqual(value_at(actual,Decimal('147.025')),Decimal('.9'))

    def test_rejects_a_ramp_with_changed_slew(self):
        _, original = points('V_CLK CLK 0 PWL(0n 0 170n 0 170.1n 1.8)')
        with self.assertRaisesRegex(ValueError,'50 ps'):
            reduced_points(original)


class SNMPilotTests(unittest.TestCase):
    def setUp(self):
        self.config = design('nominal-proposed','hold',20001,220)

    def test_pilot_rejects_a_fifth_unique_simulation_in_the_campaign(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'manifest.json').write_text(json.dumps({'config':self.config}))
            with patch('validate_phase3_snm_nominal_pilot.result_for') as results:
                results.side_effect=lambda root,c: {'status':'MEASURED'} if int(c['id'])<20006 else None
                with self.assertRaisesRegex(ValueError,'first four'):
                    batch(root)

    def check_invalid_attempt(self, failure, expected):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'build/phase3/batch'
            root.mkdir(parents=True)
            (root/'manifest.json').write_text(json.dumps({'config':self.config}))
            case = self.config['cases'][0]

            def invalid(command, *, cwd, stdout, **options):
                stdout.write('Seed value for random number generator is set to 20001\n')
                if failure=='timeout':
                    raise subprocess.TimeoutExpired(command,options['timeout'])
                stdout.write('DC simulation aborted\nngspice-44.2 done\n')
                (cwd/'vtc.dat').write_text('Partial trace retained\n')
                return subprocess.CompletedProcess(command,0)

            with patch('run_phase3_snm.subprocess.run',side_effect=invalid), \
                    patch('run_phase3_eco_pex.ROOT',Path(tmp)):
                self.assertFalse(run_case(root,case,self.config,5))
            work = root/'20001'/'attempt-001'
            result = json.loads((work/'result.json').read_text())
            self.assertEqual(result['status'],expected)
            self.assertIsNone(result['snm_v'])
            self.assertTrue({'ngspice.log','bench.spice'}<=result['artifacts'].keys())
            if failure!='timeout':
                self.assertIn('vtc.dat',result['artifacts'])

    def test_convergence_error_with_zero_process_exit_is_invalid(self):
        self.check_invalid_attempt('convergence','ERROR')

    def test_timeout_retains_evidence_without_creating_zero_snm(self):
        self.check_invalid_attempt('timeout','TIMEOUT')


if __name__=='__main__':
    unittest.main()
