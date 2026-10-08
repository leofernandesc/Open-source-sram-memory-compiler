"""Regressions for stale sizing and voltage probes in an all-net R-C deck."""
import re
import unittest
from pathlib import Path
from unittest.mock import patch

import run_row_decoder_pex_contract as runner


class PexContractRegressionTests(unittest.TestCase):
    def test_fast_hot_profile_contains_nine_matching_transition_cases(self):
        cases = runner.case_matrix(("fast",))
        self.assertEqual(len(cases), 9)
        self.assertTrue(all(case["profile"] == "fast" for case in cases))
        self.assertEqual({(case["old"], case["new"]) for case in cases},
                         {(0, 0), (0, 1), (1, 0), (0, 2), (2, 0),
                          (0, 3), (3, 0), (1, 2), (2, 1)})
        self.assertEqual(runner.contract.PROFILES["fast"], ("ff", 1.8, 125))

    @classmethod
    def setUpClass(cls):
        runner.load_simulation_dependencies()
        # Keep a real archived top-level decoder/WL testbench, but substitute
        # the current canonical decoder so the fixture follows its sizing.
        template = (runner.ROOT / "sims/row_decoder/results/"
                    "row_decoder_pex_20261007_234742/baseline_input_netlist.spice").read_text()
        imported = (runner.ROOT / "layout/row_decoder/row_decoder_import.spice").read_text()
        decoder = runner.subckt_match(imported, "row_decoder_sram6t")
        old = runner.subckt_match(template, "row_decoder")
        replacement = f".subckt row_decoder {decoder[1]}\n{decoder[2]}.ends row_decoder\n"
        cls.source = template[:old.start()] + replacement + template[old.end():]
        cls.pex = runner.PEX_PATH.read_text()

    def test_current_pex_matches_source_topology_and_sizing(self):
        _, counts, gates, segments = runner.inject_pex(self.source, self.pex)
        self.assertEqual(counts["mos"], 29)
        self.assertEqual(set(gates), {0, 1, 2, 3})
        self.assertTrue(all(segments.values()))

    def test_stale_precharge_sizing_is_rejected_with_same_interface(self):
        stale, changes = re.subn(r"(?im)^(XM5\b[^\n]*\bW=)\S+",
                                r"\g<1>0.5", self.source, count=1)
        self.assertEqual(changes, 1)
        with self.assertRaisesRegex(ValueError, "sizing/connectivity differs"):
            runner.inject_pex(stale, self.pex)

    def test_distributed_input_deck_saves_energy_source_voltages(self):
        netlist, _, gates, segments = runner.inject_pex(self.source, self.pex)
        nodes, devices = runner.ORIGINAL_INSPECT(self.source, True)
        devices["__pins__"] = runner.screen.subcircuit(self.source, "row_decoder")[0]
        with patch.object(runner, "SOURCE_NODES", nodes), \
                patch.object(runner, "SOURCE_DEVICES", devices), \
                patch.object(runner, "PEX_DYNAMIC_NODES", gates), \
                patch.object(runner, "PEX_DYNAMIC_SEGMENTS", segments), \
                patch.object(runner.screen, "inspect_netlist", runner.inspect_netlist), \
                patch.object(runner.contract, "mos_instances", runner.mos_instances):
            deck, _, _, _, schedule = runner.make_deck(
                netlist, runner.case_matrix()[0], Path("sky130.lib.spice"))
        saved = re.search(r"(?im)^\.save\s+([^\n]+)", deck)[1].split()
        for port in ("VDD", "PCLK", "A0", "A1"):
            self.assertIn(f"v({schedule['ports'][port].lower()})", saved)

    def coverage_fixture(self):
        _, _, _, segments = runner.inject_pex(self.source, self.pex)
        nodes = {f"{family}{row}": f"{family.lower()}{row}"
                 for family in ("DEC", "WL") for row in range(4)}
        raw = {"time": runner.contract.np.array([0., 1., 2., 3.])}
        raw.update({f"v({node})": runner.contract.np.zeros(4) for node in nodes.values()})
        schedule = dict(vdd=1.8, second_rise=1., second_fall=2.,
                        fall=.1, rise=.1, stop=3.)
        return raw, nodes, schedule, segments

    def test_missing_distributed_probe_cannot_silently_pass(self):
        raw, nodes, schedule, segments = self.coverage_fixture()
        node = next(node for group in segments.values() for node in group if "." in node)
        raw[f"v(x1.{node.lower()})"] = runner.contract.np.zeros(4)
        with patch.object(runner, "PEX_DYNAMIC_SEGMENTS", segments), \
                patch.object(runner, "ORIGINAL_ANALYZE", return_value=({}, [], [])):
            with self.assertRaisesRegex(ValueError, "Missing distributed dynamic-node probe"):
                runner.analyze(raw, {"new": 0, "label": "missing_probe"}, nodes, {}, {}, schedule)

    def test_baseline_is_not_reported_as_distributed_pex_coverage(self):
        raw, nodes, schedule, segments = self.coverage_fixture()
        for row in range(4):
            raw[f"v(x1.n{row})"] = runner.contract.np.ones(4)*1.8
        with patch.object(runner, "PEX_DYNAMIC_SEGMENTS", segments), \
                patch.object(runner, "ORIGINAL_ANALYZE", return_value=({}, [], [])):
            result, _, _ = runner.analyze(raw, {"new": 0}, nodes, {}, {}, schedule)
        self.assertNotIn("pex_dynamic_segment_count", result)


if __name__ == "__main__":
    unittest.main()
