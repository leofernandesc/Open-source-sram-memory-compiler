"""Reject narrow false-row pulses and incomplete recovery in waveform checks."""
import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path

import numpy as np
import run_row_decoder_contract as contract
import run_row_decoder_tt as screen
from generate_buffered_decoder_schematic import generate


class ContractWaveformRegression(unittest.TestCase):
    def test_energy_window_interpolates_both_boundaries(self):
        # P(t)=2t+1 has exact integral 4.8 from t=.2 to 1.8, even
        # when neither boundary belongs to the simulator's output grid.
        time = np.array([0., .5, 1., 1.5, 2.])
        self.assertAlmostEqual(contract.integrate_power_window(time, 2*time+1, .2, 1.8), 4.8)

    def test_energy_window_rejects_truncated_transient(self):
        with self.assertRaisesRegex(ValueError, "contained"):
            contract.integrate_power_window(np.array([0., 1.]), np.ones(2), .2, 1.2)

    @classmethod
    def setUpClass(cls):
        cls.netlist = (Path(__file__).parent / "results/feedthrough_b6_qualification/input_netlist.spice").read_text()
        cls.case = dict(label="synthetic", campaign="history", profile="tt", old=0, new=1)
        _, cls.nodes, cls.devices, cls.terminals, cls.schedule = contract.make_deck(cls.netlist, cls.case, Path("/models/lib.spice"))

    def raw(self):
        time = np.linspace(0, 30e-9, 30001)
        raw = {"time": time}
        for pins in self.terminals.values():
            for node in pins:
                if node not in {"0", "gnd"}:
                    raw.setdefault(f"v({node})", np.zeros_like(time))
        for name in ("vdd_src", "vpclk", "va0", "va1"):
            raw[f"i({name})"] = np.zeros_like(time)
        for row in range(4):
            active = ((time >= 5.2e-9) & (time <= 10.2e-9) & (row == 0)) | ((time >= 20.2e-9) & (time <= 25.2e-9) & (row == 1))
            for kind in ("DEC", "WL"):
                raw[f"v({self.nodes[kind+str(row)].lower()})"] = active.astype(float)*1.8
            raw[f"v(x1.n{row})"] = (1-active.astype(float))*1.8
        raw["v(net1)"][:] = 1.8
        return raw

    def analyze(self, raw):
        return contract.analyze(raw, self.case, self.nodes, self.devices, self.terminals, self.schedule)[0]

    def test_correct_reference_has_no_logic_failures(self):
        self.assertEqual(self.analyze(self.raw())["result"], "PASS")

    def test_wrong_row_pulse_before_the_settling_allowance_is_rejected(self):
        raw = self.raw()
        # A 5 ps wrong-WL pulse before 1 ns cannot be hidden by a late sample.
        raw[f"v({self.nodes['WL3'].lower()})"][(raw["time"] >= 20.10e-9) & (raw["time"] <= 20.105e-9)] = 1.8
        self.assertEqual(self.analyze(raw)["result"], "FAIL")

    def test_residual_row_during_precharge_is_rejected(self):
        raw = self.raw()
        raw[f"v({self.nodes['DEC0'].lower()})"][(raw["time"] >= 12e-9) & (raw["time"] <= 13e-9)] = .5
        self.assertEqual(self.analyze(raw)["result"], "FAIL")

    def test_incomplete_internal_recovery_is_rejected(self):
        raw = self.raw()
        raw["v(x1.n2)"][(raw["time"] >= 19e-9) & (raw["time"] <= 20e-9)] = 1.1
        self.assertEqual(self.analyze(raw)["result"], "FAIL")

    def test_truncated_raw_cannot_pass(self):
        raw = {k: v[:-10] for k, v in self.raw().items()}
        with self.assertRaisesRegex(ValueError, "Truncated"):
            self.analyze(raw)

    def test_nonfinite_voltage_cannot_pass(self):
        raw = self.raw()
        raw[f"v({self.nodes['WL0'].lower()})"][100] = np.nan
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            self.analyze(raw)

    def test_voltage_only_qualification_failure_sets_nonzero_exit(self):
        row = dict(campaign='robustness', result='PASS', model_upper_result='PASS',
                   magnitude_result='OUTSIDE_SCREEN')
        self.assertEqual(contract.campaign_exit_code([row], []), 1)
        row['campaign'] = 'charge'
        self.assertEqual(contract.campaign_exit_code([row], []), 0)
        self.assertEqual(contract.campaign_exit_code([], ['truncated raw']), 2)

    def test_geometry_overrides_preserve_the_connections_and_wl_buffers(self):
        baseline, nodes, _, terminals, schedule = contract.make_deck(self.netlist, self.case, Path('/models/lib.spice'))
        case = dict(self.case, footer_um=6, out_p_um=3, out_n_um=3, precharge_um=.75)
        deck, other_nodes, devices, other_terminals, other_schedule = contract.make_deck(self.netlist, case, Path('/models/lib.spice'))
        self.assertEqual(nodes, other_nodes)
        self.assertEqual(terminals, other_terminals)
        self.assertEqual(schedule, other_schedule)
        self.assertNotEqual(baseline, deck)
        self.assertEqual(len(devices), 25)
        _, before = screen.subcircuit(baseline, 'wl_driver')
        _, after = screen.subcircuit(deck, 'wl_driver')
        self.assertEqual(before, after)

    def test_recursive_model_change_invalidates_the_fingerprint(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'library.spice').write_text('.include "models.spice"\n.include models.spice\n')
            (root/'models.spice').write_text('.include library.spice\n* model A\n')
            before = contract.model_dependencies(root/'library.spice')
            self.assertEqual(len(before), 2)
            (root/'models.spice').write_text('* model B\n')
            after = contract.model_dependencies(root/'library.spice')
            self.assertNotEqual(before, after)

    def test_buffered_address_diagnostic_adds_only_two_static_inverters(self):
        case = dict(self.case, buffer_addresses=True, true_buffer_um=.75)
        deck, nodes, devices, terminals, schedule = contract.make_deck(self.netlist, case, Path('/models/lib.spice'))
        self.assertEqual(len(devices),29)
        self.assertEqual(len(terminals),45)
        self.assertEqual(devices['M26']['nodes'],['A0T','A0B','VDD','VDD'])
        self.assertEqual(devices['M27']['nodes'],['A0T','A0B','VSS','VSS'])
        self.assertEqual(devices['M28']['nodes'],['A1T','A1B','VDD','VDD'])
        self.assertEqual(devices['M29']['nodes'],['A1T','A1B','VSS','VSS'])
        self.assertEqual(devices['M13']['nodes'][1],'A0T')
        self.assertEqual(devices['M23']['nodes'][1],'A0T')
        self.assertEqual(devices['M17']['nodes'][1],'A1T')
        self.assertEqual(devices['M22']['nodes'][1],'A1T')
        self.assertEqual(devices['M8']['nodes'],['EVAL_GND','PCLK','VSS','VSS'])
        self.assertEqual(devices['M26']['W'],.75)
        self.assertIn('v(x1.a0t)',deck)
        self.assertEqual(set(nodes),set(self.nodes))
        # A fresh netlist from a saved 29-MOS schematic receives the same audit
        # and must not acquire duplicate diagnostic buffers.
        inspected_nodes, inspected = screen.inspect_netlist(deck, True)
        self.assertEqual(len(inspected),29)
        self.assertEqual(inspected['M26']['nodes'],devices['M26']['nodes'])
        again, _, repeated, repeated_terminals, _ = contract.make_deck(deck, case, Path('/models/lib.spice'))
        self.assertEqual(len(repeated),29)
        self.assertEqual(len(repeated_terminals),45)

    def test_matching_checkpoint_reuses_analysis_without_ngspice(self):
        import hashlib
        import json
        import os
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            model = Path(os.environ.get('PDK_ROOT', '/opt/pdks'))/'sky130A/libs.tech/combined/continuous/sky130.lib.spice'
            deck, *_ = contract.make_deck(self.netlist, self.case, model)
            record = dict(script_sha256=contract.SCRIPT_HASH, deck_sha256=hashlib.sha256(deck.encode()).hexdigest(),
                          environment_sha256='verified-models-tools-helpers', run=[{'case':'synthetic'}, [], []])
            checkpoints = root/'checkpoints'
            checkpoints.mkdir()
            (checkpoints/'synthetic.json').write_text(json.dumps(record))
            with patch.object(contract.subprocess, 'run', side_effect=AssertionError('unexpected simulation')):
                result = contract.simulate(self.case, self.netlist, root/'work', False, checkpoints,
                                           'verified-models-tools-helpers')
            self.assertEqual(result, record['run'])

    def test_changed_environment_does_not_reuse_checkpoint(self):
        import hashlib
        import json
        import os
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            model = Path(os.environ.get('PDK_ROOT', '/opt/pdks'))/'sky130A/libs.tech/combined/continuous/sky130.lib.spice'
            deck, *_ = contract.make_deck(self.netlist, self.case, model)
            checkpoints = root/'checkpoints'
            checkpoints.mkdir()
            (checkpoints/'synthetic.json').write_text(json.dumps(dict(script_sha256=contract.SCRIPT_HASH,
                deck_sha256=hashlib.sha256(deck.encode()).hexdigest(), environment_sha256='old-models', run=[{},[],[]])))
            with patch.object(contract.subprocess, 'run', side_effect=RuntimeError('new simulation requested')):
                with self.assertRaisesRegex(RuntimeError, 'new simulation requested'):
                    contract.simulate(self.case, self.netlist, root/'work', False, checkpoints, 'new-models')

    def test_schematic_generator_reproduces_the_retained_candidate(self):
        folder = Path(__file__).parent/'results/buffered_b7_candidate'
        original = (folder/'original_b6.sch').read_text()
        result = generate(original)
        self.assertEqual(result, (folder/'row_decoder.sch').read_text())
        self.assertIn('{name=M26\nW=2', result)
        self.assertIn('name=p3 lab=A0', result)
        self.assertIn('name=p8 lab=A1', result)

    def test_generator_rejects_an_already_buffered_source(self):
        folder = Path(__file__).parent/'results/buffered_b7_candidate'
        with self.assertRaisesRegex(ValueError, '25-MOS'):
            generate((folder/'row_decoder.sch').read_text())


if __name__ == "__main__":
    unittest.main()
