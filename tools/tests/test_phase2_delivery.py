"""Handoff identity and safe optional raw-transfer behavior."""
import hashlib
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
import subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_phase2_delivery import verify_entries, verify_index
from bundle_phase2_raw import verify


class DeliveryTests(unittest.TestCase):
    def test_reject_changed_payload_and_byte_count(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'top.gds';p.write_bytes(b'actual GDS fixture')
            record={'path':'top.gds','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
            self.assertEqual(verify_entries(record,root),['top.gds'])
            record['bytes']+=1
            with self.assertRaisesRegex(ValueError,'byte count'):verify_entries(record,root)
            record['bytes']-=1;p.write_bytes(b'altered')
            with self.assertRaisesRegex(ValueError,'Changed/missing'):verify_entries(record,root)

    def test_empty_manifest_rejected(self):
        with self.assertRaisesRegex(ValueError,'Empty'):verify_entries({})

    def test_index_gate_rejects_worktree_bytes_changed_after_staging(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);subprocess.run(['git','init','-q',str(root)],check=True)
            p=root/'proof.txt';p.write_text('audited bytes\n')
            subprocess.run(['git','add','proof.txt'],cwd=root,check=True)
            verify_index(root,['proof.txt'])
            p.write_text('different bytes after staging\n')
            with self.assertRaisesRegex(ValueError,'staged publication blobs'):verify_index(root,['proof.txt'])

    def archive(self,root,name='case/waveform.dat',payload=b'full trace fixture'):
        archive=root/'bundle.tar.gz'
        with tarfile.open(archive,'w:gz') as t:
            info=tarfile.TarInfo(name);info.size=len(payload);t.addfile(info,io.BytesIO(payload))
        expected=[dict(member='case/waveform.dat',target='build/phase2/cache/waveform.dat',sha256=hashlib.sha256(payload).hexdigest())]
        return archive,expected

    def test_lossless_restore_missing_cache_and_skip_identical_existing(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);archive,expected=self.archive(root)
            self.assertEqual(verify(archive,expected,True,root),['build/phase2/cache/waveform.dat'])
            self.assertEqual((root/expected[0]['target']).read_bytes(),b'full trace fixture')
            self.assertEqual(verify(archive,expected,True,root),[])

    def test_conflicting_cache_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);archive,expected=self.archive(root);dest=root/expected[0]['target'];dest.parent.mkdir(parents=True);dest.write_bytes(b'preserve me')
            with self.assertRaisesRegex(ValueError,'Conflicting'):verify(archive,expected,True,root)
            self.assertEqual(dest.read_bytes(),b'preserve me')

    def test_archive_path_traversal_and_wrong_raw_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);archive,expected=self.archive(root,'../../outside')
            with self.assertRaisesRegex(ValueError,'Unexpected'):verify(archive,expected,True,root)
            archive,expected=self.archive(root);expected[0]['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'identity differs'):verify(archive,expected,False,root)


if __name__=='__main__':unittest.main()
