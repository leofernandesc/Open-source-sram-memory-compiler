"""Reject misleading numeric flags, missing probes and optimized-Python bypasses."""
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import freeze_keeper_revision as audit


class KeeperEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)
        original=ROOT/'sims/row_decoder/results/keeper_pex_pilot_20261029/tt_1_to_2'
        self.row=json.loads((original/'result.json').read_text())
        for name in ('checks.csv','intrinsic_magnitudes.csv'):shutil.copy2(original/name,self.directory/name)

    def mutate_checks(self,operation):
        path=self.directory/'checks.csv'
        with path.open() as handle:rows=list(csv.DictReader(handle))
        operation(rows)
        with path.open('w',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)

    def test_actual_49_device_pilot_passes(self):
        self.assertEqual(audit.check_case(self.directory,self.row,True),29)

    def test_pass_flag_cannot_hide_an_out_of_range_numeric_value(self):
        self.mutate_checks(lambda rows:rows[0].update(value='20'))
        with self.assertRaisesRegex(ValueError,'flag hides'):audit.check_case(self.directory,self.row,True)

    def test_missing_functional_check_is_rejected(self):
        self.mutate_checks(lambda rows:rows.pop())
        with self.assertRaisesRegex(ValueError,'check set'):audit.check_case(self.directory,self.row,True)

    def test_one_unprobed_device_is_rejected(self):
        path=self.directory/'intrinsic_magnitudes.csv';lines=path.read_text().splitlines()
        path.write_text('\n'.join(lines[:-4])+'\n')
        with self.assertRaisesRegex(ValueError,'device coverage'):audit.check_case(self.directory,self.row,True)

    def test_summary_cannot_understate_actual_intrinsic_magnitude(self):
        self.row['max_intrinsic_magnitude_v']=.1
        with self.assertRaisesRegex(ValueError,'Magnitude result differs'):audit.check_case(self.directory,self.row,True)

    def test_numeric_guard_survives_optimized_python(self):
        self.mutate_checks(lambda rows:rows[0].update(value='20'))
        (self.directory/'row.json').write_text(json.dumps(self.row))
        source=('import json,sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); '
            'import freeze_keeper_revision as a; p=Path(sys.argv[2]); '
            'a.check_case(p,json.loads((p/"row.json").read_text()),True)')
        for optimization in ([],['-O'],['-OO']):
            with self.subTest(optimization=optimization):
                result=subprocess.run([sys.executable,*optimization,'-c',source,str(ROOT/'tools'),str(self.directory)],capture_output=True,text=True)
                self.assertNotEqual(result.returncode,0);self.assertIn('flag hides',result.stderr)


if __name__=='__main__':unittest.main()
