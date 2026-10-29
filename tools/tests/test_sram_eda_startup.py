"""Exercise launcher startup against a fake Docker daemon and temporary cookies."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'sram-eda'
DOCKER='''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
a=sys.argv[1:]
if a[0]=='inspect':
 if '--format' in a:
  f=a[a.index('--format')+1]
  print(os.environ['FAKE_STATE'] if '.State.Running' in f else
        os.environ['FAKE_WORKSPACE'] if '/work' in f else os.environ['FAKE_XAUTH'])
elif a[0]=='start':
 if not Path(os.environ['FAKE_XAUTH']).is_file():sys.exit(10)
 with open(os.environ['FAKE_CALLS'],'a') as h:h.write('start\\n')
elif a[0]=='exec':
 with open(os.environ['FAKE_CALLS'],'a') as h:h.write('exec\\n')
 print('FAKE_BACKEND_READY')
else:sys.exit(11)
'''


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        root=Path(self.temporary.name);self.repo=root/'repo';(self.repo/'tools').mkdir(parents=True)
        self.launcher=self.repo/'tools/sram-eda';shutil.copy2(SOURCE,self.launcher)
        binaries=root/'bin';binaries.mkdir();docker=binaries/'docker';docker.write_text(DOCKER);docker.chmod(0o755)
        self.cookie=root/'current-cookie';self.cookie.write_text('fixture-cookie')
        self.mount=root/'old-cookie';self.calls=root/'calls'
        self.env={**os.environ,'PATH':str(binaries)+os.pathsep+os.environ['PATH'],
                  'FAKE_STATE':'false','FAKE_WORKSPACE':str(self.repo),'FAKE_XAUTH':str(self.mount),
                  'FAKE_CALLS':str(self.calls),'XAUTHORITY':str(self.cookie)}

    def run_launcher(self,command='python3'):
        return subprocess.run(['bash',str(self.launcher),command,'--version'],env=self.env,capture_output=True,text=True)

    def test_headless_replaces_empty_stale_directory_with_current_cookie(self):
        self.mount.mkdir();r=self.run_launcher()
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(self.mount.read_text(),'fixture-cookie')
        self.assertEqual(self.mount.stat().st_mode&0o777,0o600)
        self.assertEqual(self.calls.read_text(),'start\nexec\n')

    def test_headless_without_graphical_session_creates_private_empty_bind(self):
        self.env.pop('XAUTHORITY');self.mount.mkdir();r=self.run_launcher()
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(self.mount.read_bytes(),b'')
        self.assertEqual(self.mount.stat().st_mode&0o777,0o600)

    def test_headless_without_session_preserves_existing_cookie(self):
        self.env.pop('XAUTHORITY');self.mount.write_text('existing');r=self.run_launcher()
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(self.mount.read_text(),'existing')

    def test_running_headless_does_not_touch_graphical_files(self):
        self.env['FAKE_STATE']='true';self.env.pop('XAUTHORITY');self.mount.mkdir()
        (self.mount/'keep').write_text('existing');r=self.run_launcher()
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(self.calls.read_text(),'exec\n')
        self.assertEqual((self.mount/'keep').read_text(),'existing')

    def test_nonempty_stale_directory_is_rejected_without_deleting_data(self):
        self.mount.mkdir();(self.mount/'keep').write_text('data');r=self.run_launcher()
        self.assertNotEqual(r.returncode,0);self.assertFalse(self.calls.exists())
        self.assertEqual((self.mount/'keep').read_text(),'data')

    def test_gui_still_requires_a_real_session_cookie(self):
        self.env.pop('XAUTHORITY');r=self.run_launcher('xschem')
        self.assertNotEqual(r.returncode,0);self.assertIn('XAUTHORITY',r.stderr)
        self.assertFalse(self.calls.exists())

    def test_wrong_checkout_is_rejected_before_cookie_repair(self):
        self.env['FAKE_WORKSPACE']=str(self.repo/'other');self.mount.mkdir();r=self.run_launcher()
        self.assertNotEqual(r.returncode,0);self.assertTrue(self.mount.is_dir());self.assertFalse(self.calls.exists())

    def test_dangling_symlink_is_rejected(self):
        self.mount.symlink_to(self.repo/'missing');r=self.run_launcher()
        self.assertNotEqual(r.returncode,0);self.assertTrue(self.mount.is_symlink());self.assertFalse(self.calls.exists())


if __name__=='__main__':unittest.main()
