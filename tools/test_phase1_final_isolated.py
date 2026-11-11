#!/usr/bin/env python3
"""Adversarial receipt tests, exclusively on disposable copies of a completed run."""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from run_phase1_final_isolated import read_data, evaluate, verify

EVIDENCE = None


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phase1-receipt-')
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)/'copy'
        shutil.copytree(EVIDENCE,self.out)
        self.result = json.loads((self.out/'results.json').read_text())

    def receipt(self):
        (self.out/'results.json').write_text(json.dumps(self.result))

    def test_original_replays(self):
        result=verify(self.out)
        self.assertEqual(result['status'],'PASS_EVIDENCE_INTEGRITY')
        self.assertEqual(result['functional_status'],self.result['status'])

    def test_forged_check_counter_rejected(self):
        self.result['functional_checks'] += 1
        self.receipt()
        with self.assertRaisesRegex(ValueError,'aggregate check count'):verify(self.out)

    def test_altered_dut_rejected_even_with_rehashed_artifact(self):
        case=self.result['cases'][0]['case']['id']
        relative=case+'/dut.spice';p=self.out/relative
        p.write_text(p.read_text().replace('W=1.89','W=1.26'))
        self.result['artifacts'][relative]=hashlib.sha256(p.read_bytes()).hexdigest()
        self.receipt()
        with self.assertRaisesRegex(ValueError,'Executed netlist/deck'):verify(self.out)

    def test_missing_native_log_rejected(self):
        p=self.out/(self.result['cases'][0]['case']['id']+'/ngspice.txt')
        p.unlink()
        with self.assertRaises(FileNotFoundError):verify(self.out)

    def test_truncated_waveform_rejected_without_receipt(self):
        case=self.result['cases'][0]
        data=read_data(self.out/case['case']['id']/'waveform.dat.gz')
        with self.assertRaisesRegex(ValueError,'Incomplete or invalid'):
            evaluate(case['case'],data[:len(data)//2],case['stop_ns'])

    def test_wrong_output_rejected_despite_resealed_hashes(self):
        item=copy.deepcopy(self.result['cases'][0]);c=item['case'];relative=c['id']+'/waveform.dat.gz'
        p=self.out/relative
        with gzip.open(p,'rt') as f:lines=f.readlines()
        # Exchange the two actual output vectors; input vectors are unchanged.
        swapped=[lines[0]]
        for line in lines[1:]:
            fields=line.split();fields[5],fields[6]=fields[6],fields[5]
            swapped.append(' '.join(fields)+'\n')
        payload=''.join(swapped).encode()
        with gzip.open(p,'wb') as f:f.write(payload)
        self.result['artifacts'][relative]=hashlib.sha256(p.read_bytes()).hexdigest()
        self.result['cases'][0]['uncompressed_waveform_sha256']=hashlib.sha256(payload).hexdigest()
        self.receipt()
        with self.assertRaisesRegex(ValueError,'Full-transient checks disagree'):verify(self.out)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence',required=True,type=Path)
    args=p.parse_args();EVIDENCE=args.evidence.resolve()
    unittest.main(argv=['receipt-tests'],verbosity=2)
