"""Contract and failure-path tests, isolated from frozen evidence and the real simulator."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phase3.contract import validate, normalize, rows, FIELDS
from phase3 import runner
from phase2_evidence import digest

ROOT = runner.ROOT


class Phase3Tests(unittest.TestCase):
    def setUp(self):
        self.c = json.loads((ROOT/'characterization/phase3/smoke.json').read_text())

    def test_strict_config(self):
        validate(self.c)
        for key, value in [('corner','sf'), ('vdd_v',True), ('slew_ps',float('nan')), ('configuration','2x8'), ('duty_cycle',1), ('extra',1)]:
            with self.subTest(key=key):
                c = dict(self.c); c[key] = value
                with self.assertRaises((ValueError, KeyError)):
                    validate(c)

    def test_units_and_missing(self):
        self.assertEqual(normalize(50,'ps','tACCESS'), (5e-11,'s'))
        with self.assertRaises(ValueError): normalize(1,'W','tACCESS')
        r = rows(self.c,'r','')[0]
        self.assertIsNone(r['value']); self.assertEqual(r['status'],'NOT_CHARACTERIZED')
        self.assertIsNone(rows(self.c,'r','smoke_low = 0.1',True)[0]['value'])
        self.assertEqual(rows(self.c,'r','smoke_low = 1.8')[0]['status'],'FAIL')
        self.assertEqual(rows(self.c,'r','smoke_low = 1e-4')[0]['value'],1e-4)
        with self.assertRaises(ValueError): rows(self.c,'r','smoke_low = NaN')
        with self.assertRaises(ValueError): rows(self.c,'r','smoke_low = 0\nsmoke_low = 0')

    def test_si_output_not_double_scaled(self):
        self.c['measurements'][0].update(metric='tACCESS',unit='ns',min=0,max=2)
        r=rows(self.c,'r','smoke_low = 1e-9')[0]
        self.assertEqual(r['value'],1e-9); self.assertEqual(r['unit'],'s'); self.assertEqual(r['status'],'PASS')

    def fixture(self, folder):
        lib=folder/'model.spice'; lib.write_text('.lib tt\n.endl tt\n')
        self.c['model']=dict(path=str(lib),sha256=digest(lib))
        config=folder/'config.json'; config.write_text(json.dumps(self.c))
        return config

    def test_closure_and_integrity(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'out').mkdir()
            (p/'a').write_text('.include "b"\n'); (p/'b').write_text('* dependency\n')
            inventory={}; runner.snapshot(p/'a',p/'out',inventory,{})
            self.assertEqual(len(inventory),2)
            (p/'b').write_text('* changed\n')
            self.assertNotEqual(digest(p/'b'),inventory[str(p/'b')])

    def test_library_dependency_and_cycle(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'out').mkdir()
            (p/'root').write_text('.lib \"lib\" tt\n')
            (p/'lib').write_text('.lib tt\n.include \"root\"\n.endl tt\n')
            inventory={}; copied={}
            runner.snapshot(p/'root',p/'out',inventory,copied)
            self.assertEqual(len(inventory),2)
            self.assertIn('.lib tt',copied[(p/'lib').resolve()].read_text())

    def test_lifecycle(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'reports/phase3').mkdir(parents=True)
            config=self.fixture(p)
            for name in ('deck','netlist'):
                self.c[name]['path']=str(ROOT/self.c[name]['path'])
            config.write_text(json.dumps(self.c))
            # Stub repository metadata and simulator; live runs exercise the real baseline guards.
            real_git=runner.git
            def git(*args): return real_git(*args)
            selector=p/'release'; selector.mkdir()
            (selector/'phase2_current.json').write_bytes((ROOT/'release/phase2_current.json').read_bytes())
            with patch.object(runner,'ROOT',p), patch.object(runner,'git',side_effect=git), patch.object(runner.subprocess,'run') as run, patch.object(runner.subprocess,'check_output') as check, patch.object(runner,'preflight',return_value={'test':True}):
                run.return_value.returncode=0
                check.side_effect=lambda cmd, **kwargs: (ROOT/'release/phase2_current.json').read_bytes() if 'show' in cmd else 'ngspice-test'
                out=p/'reports/phase3/dry'
                r=runner.run(config,out,True)
                self.assertEqual(r['status'],'NOT_CHARACTERIZED',r.get('error'))
                self.assertFalse(r['electrical_simulation_performed'])
                with self.assertRaises(FileExistsError): runner.run(config,out,True)
                with (out/'metrics.csv').open() as stream:
                    self.assertEqual(list(csv.DictReader(stream))[0]['value'],'')
                self.assertEqual(set(json.loads((out/'manifest.json').read_text())['evidence']),set(r['evidence']))
                for mode in ('success','bounds','fail','timeout','missing'):
                    class Proc:
                        pid=123456
                        returncode=1 if mode=='fail' else 0
                        def wait(self,timeout=None):
                            if mode=='timeout' and timeout is not None: raise subprocess.TimeoutExpired('ngspice',1)
                            return self.returncode
                    def popen(*args,**kwargs):
                        kwargs['stdout'].write(('smoke_low = 1.8\n' if mode=='bounds' else 'smoke_low = 0.001\n') if mode!='missing' else '')
                        kwargs['stdout'].flush()
                        return Proc()
                    with patch.object(runner.subprocess,'Popen',side_effect=popen), patch.object(runner.os,'killpg'):
                        r=runner.run(config,p/f'reports/phase3/{mode}')
                    expected={'success':'PASS','bounds':'FAIL','fail':'ERROR','timeout':'ERROR','missing':'NOT_CHARACTERIZED'}[mode]
                    self.assertEqual(r['status'],expected,r.get('error'))
                    self.assertTrue((p/f'reports/phase3/{mode}/ngspice.log').exists())
                    if mode in ('fail','timeout'): self.assertIsNone(r['measurements'][0]['value'])
                with patch.object(runner,'preflight',side_effect=ValueError('resources low')):
                    r=runner.run(config,p/'reports/phase3/resources',True)
                    self.assertEqual(r['status'],'BLOCKED')
                self.c['model']['path']=str(p/'missing.spice')
                config.write_text(json.dumps(self.c))
                r=runner.run(config,p/'reports/phase3/absent',True)
                self.assertEqual(r['status'],'BLOCKED')
                self.c['model']['path']=str(p/'model.spice')
                self.c['corner']='ff'; config.write_text(json.dumps(self.c))
                r=runner.run(config,p/'reports/phase3/corner',True)
                self.assertEqual(r['status'],'BLOCKED')
                self.c['corner']='tt'
                self.c['model']['sha256']='0'*64; config.write_text(json.dumps(self.c))
                r=runner.run(config,p/'reports/phase3/hash')
                self.assertEqual(r['status'],'ERROR'); self.assertIn('Hash mismatch',r['error'])
                config.write_text('{}')
                r=runner.run(config,p/'reports/phase3/invalid')
                self.assertEqual(r['status'],'ERROR')
                self.assertTrue((p/'reports/phase3/invalid/manifest.json').exists())

if __name__=='__main__': unittest.main()
