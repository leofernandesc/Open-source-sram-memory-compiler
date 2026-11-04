"""Regressions for defects reproduced during the November Phase 2 audit."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase2_evidence import digest,finite,hashes,seal,stage_inventory,verify_seal


class EvidenceIntegrityTests(unittest.TestCase):
    def test_nonfinite_csv_numbers_are_never_equal_to_a_real_sample(self):
        for value in ('nan','NaN','inf','-inf',float('nan'),True,None):
            with self.subTest(value=value),self.assertRaises(ValueError):finite(value,'voltage')
        self.assertEqual(finite('1.8','voltage'),1.8)

    def test_empty_and_incomplete_hash_inventories_fail(self):
        for entries in ({},None,{'other':'a'*64},{'bench.spice':'not-a-hash'}):
            with self.subTest(entries=entries),self.assertRaises(ValueError):hashes(entries,('bench.spice',))

    def test_changed_gds_rejected_before_package(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);gds=root/'top.gds';gds.write_bytes(b'original layout')
            accepted={'verified_files':seal(root,[gds])}
            verify_seal(root,accepted,['top.gds'])
            gds.write_bytes(b'changed geometry after DRC')
            with self.assertRaisesRegex(ValueError,'Delivery artifact changed since audit: top.gds'):
                verify_seal(root,accepted,['top.gds'])

    def test_missing_required_delivery_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'log';p.write_text('PASS')
            with self.assertRaisesRegex(ValueError,'mandatory evidence inventory'):
                verify_seal(root,{'verified_files':seal(root,[p])},['top.gds'])

    def test_missing_stage_output_does_not_inherit_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'results.json';p.write_text('{"status":"PASS"}')
            with self.assertRaises(ValueError):stage_inventory(root,root,{'artifacts':{}},('top.gds',))

    def test_legacy_inventory_must_match_both_receipt_and_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);stage=root/'reports/stage';stage.mkdir(parents=True)
            record=stage/'results.json';record.write_text('{"status":"PASS"}')
            artifact=stage/'top.gds';artifact.write_bytes(b'geometry')
            history=root/'physical/phase2/history';history.mkdir(parents=True)
            (history/'legacy_artifacts_20261104.json').write_text(json.dumps({'stages':{'reports/stage':{'receipt_sha256':digest(record),'artifacts':{'top.gds':digest(artifact)}}}}))
            self.assertEqual(stage_inventory(root,stage,{},('top.gds',)),[artifact])
            artifact.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Changed stage artifact'):stage_inventory(root,stage,{},('top.gds',))

    def test_partial_execution_or_changed_receipt_cannot_reuse_legacy_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);stage=root/'reports/stage';stage.mkdir(parents=True)
            record=stage/'results.json';record.write_text('RUNNING')
            history=root/'physical/phase2/history';history.mkdir(parents=True)
            (history/'legacy_artifacts_20261104.json').write_text(json.dumps({'stages':{'reports/stage':{'receipt_sha256':'0'*64,'artifacts':{'top.gds':'a'*64}}}}))
            with self.assertRaisesRegex(ValueError,'no matching review inventory'):stage_inventory(root,stage,{},('top.gds',))


if __name__=='__main__':unittest.main()
