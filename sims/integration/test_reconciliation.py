"""Check that reconciliation preserves evidence and rejects stale simulations."""
import argparse
import ast
import contextlib
import csv
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'sims'))
import qualification_contract as contract
import run_leaf_peripheral_smoke as smoke

UPSTREAM='eb9217ee80c585cf952e14f6a13f6fc7230ba639'


class ReconciliationTests(unittest.TestCase):
    def test_original_owner_sources_and_reports_are_preserved(self):
        paths=['docs/relatorio_validacao_bitcell_6t_sky130.md','docs/cwl_pre_layout_estimate.md',
               'specs/sram_6t_cell.md','cells/bitcell_6t.sch','cells/bitcell_6t.sym',
               'cells/precharge.sch','cells/sense_amp.sch','cells/wl_driver.sch',
               'cells/write_driver.sch','cells/row_decoder_2to4.spice']
        for path in paths:
            with self.subTest(path=path):
                original=subprocess.check_output(['git','show',f'{UPSTREAM}:{path}'],cwd=ROOT)
                self.assertEqual((ROOT/path).read_bytes(),original)

    def test_upstream_pex_measurement_functions_are_not_downgraded(self):
        for name in ('run_integrated_column_read.py','run_integrated_column_write.py'):
            original=subprocess.check_output(['git','show',f'{UPSTREAM}:sims/{name}'],cwd=ROOT,text=True)
            old={n.name:ast.dump(n) for n in ast.parse(original).body if isinstance(n,ast.FunctionDef)}
            # One-thread execution changes resources, not the circuit, stimulus,
            # measurements or acceptance criteria retained from upstream.
            content=(ROOT/'sims'/name).read_text().replace('set num_threads=1\n','')
            new={n.name:ast.dump(n) for n in ast.parse(content).body if isinstance(n,ast.FunctionDef)}
            for function in old.keys()-{'main'}:
                with self.subTest(runner=name,function=function):
                    self.assertEqual(new[function],old[function])

    def test_smoke_uses_declared_pin_order_instead_of_assumed_order(self):
        text='.subckt wl_driver VSS WL_IN WL VDD\n.ends wl_driver\n'
        deck=smoke.wl_deck(text,'tt',1.8,27,50)
        self.assertIn('XWL 0 wl_in wl vdd wl_driver',deck)
        text='.subckt precharge PRECH VSS BLB VDD BL\n.ends precharge\n'
        self.assertIn('XPRE prech 0 blb vdd bl precharge',smoke.precharge_deck(text,'tt',1.8,27,60))

    def test_duplicate_pins_cannot_be_instantiated(self):
        with self.assertRaisesRegex(RuntimeError,'pin contract'):
            smoke.instance_line('.subckt bad VDD VSS VSS\n','X',{'VDD':'vdd','VSS':'0'})

    def test_blocks_and_custom_wl_pulse_remain_compatible(self):
        values=dict(wl_before=0,wl_high=1.8,wl_low=0,t_in_50=1e-9,t_wl_50=1.1e-9,t_wl_90=1.2e-9)
        with tempfile.TemporaryDirectory() as scratch:
            output=Path(scratch)/'smoke.csv'
            argv=['smoke','--blocks','wl_driver','--corners','tt','--vdd-values','1.8','--temps-c','27',
                  '--wl-cap-ff','50','--wl-pulse-width-ns','2.5','--wl-high-sample-ns','3',
                  '--wl-low-sample-ns','4.5','--output',str(output)]
            with patch.object(sys,'argv',argv),patch.object(smoke,'netlist_leaf',return_value=
                '.subckt wl_driver VSS WL_IN WL VDD\n.ends wl_driver\n') as netlist,patch.object(
                smoke,'run_deck',return_value=(0,values,'')) as simulator,contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(smoke.main(),0)
            self.assertEqual(netlist.call_count,1)
            self.assertIn('100p 100p 2.5n',simulator.call_args.args[0])
            with output.open() as stream:rows=list(csv.DictReader(stream))
            self.assertEqual(len(rows),1);self.assertEqual(rows[0]['status'],'PASS')

    def test_incomplete_or_duplicate_corner_matrix_is_rejected(self):
        import review_reconciliation as review
        rows=[dict(corner=c,vdd_v=str(v),temp_c=str(t),state=str(s),status='PASS',returncode='0',
                   cache_contract_sha256='same')
              for c in ('tt','ss','ff','sf','fs') for v in (1.62,1.8) for t in (-40,27,125) for s in (0,1)]
        self.assertEqual(len(review.matrix(rows,'state')),60)
        for incomplete in (rows[:-1],rows[:-1]+[rows[0]]):
            with self.assertRaisesRegex(ValueError,'Incomplete/duplicated'):review.matrix(incomplete,'state')

    def test_cache_tracks_electrical_changes_not_output_or_worker_choices(self):
        with tempfile.TemporaryDirectory() as scratch:
            root=Path(scratch);library=root/'models.lib';child=root/'device.spice'
            library.write_text('.include "device.spice"\n');child.write_text('.model n nmos\n')
            args=argparse.Namespace(vdd_values=[1.8],wl_extra_ff=93.35,output=root/'first.csv',workers=1)
            leaves={'bitcell':'original electrical circuit'}
            def digest():return contract.campaign_contract(args,leaves,ROOT/'sims/run_integrated_column_read.py',library)
            baseline=digest();args.output=root/'second.csv';args.workers=2
            self.assertEqual(digest(),baseline)
            args.wl_extra_ff=17
            self.assertNotEqual(digest(),baseline)
            args.wl_extra_ff=93.35;leaves['bitcell']='changed electrical circuit'
            self.assertNotEqual(digest(),baseline)
            leaves['bitcell']='original electrical circuit';child.write_text('.model n nmos level=2\n')
            self.assertNotEqual(digest(),baseline)

    def test_old_pass_rows_are_not_reused_for_a_changed_or_unknown_contract(self):
        expected=dict(corner='tt',vdd_v=1.8,temp_c=27,stored_q=0)
        row=dict(status='PASS',returncode='0',cache_contract_sha256='new',**expected)
        self.assertFalse(contract.reusable({'status':'PASS'},'new',expected))
        self.assertFalse(contract.reusable(dict(row,cache_contract_sha256='old'),'new',expected))
        self.assertFalse(contract.reusable(dict(row,status='FAIL'),'new',expected))
        self.assertTrue(contract.reusable(row,'new',expected))

    def test_another_corner_or_state_cannot_fill_a_cached_case(self):
        expected=dict(corner='tt',vdd_v=1.8,temp_c=27,stored_q=0)
        row=dict(status='PASS',returncode='0',cache_contract_sha256='same',**expected)
        for change in [dict(corner='ss'),dict(vdd_v='1.62'),dict(temp_c='125'),dict(stored_q='1'),
                       dict(stored_q='0.5'),dict(returncode='1'),dict(temp_c='nan')]:
            with self.subTest(change=change):
                self.assertFalse(contract.reusable(dict(row,**change),'same',expected))
        row.pop('stored_q')
        self.assertFalse(contract.reusable(row,'same',expected))

    def test_numeric_csv_formatting_preserves_the_correct_write_identity(self):
        expected=dict(corner='tt',vdd_v=1.8,temp_c=27,stored_q_before=1)
        row=dict(status='PASS',returncode='0',cache_contract_sha256='same',corner='TT',
                 vdd_v='1.800',temp_c='27.0',stored_q_before='1')
        self.assertTrue(contract.reusable(row,'same',expected))


if __name__=='__main__':unittest.main()
