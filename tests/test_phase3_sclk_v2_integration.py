"""Focused offline checks for branch separation and pad-referred DC transfer."""

import unittest

import numpy as np

from audit_phase3_sclk_v2_integration import branch_forks, rail_matrix


class IntegrationPreflightTest(unittest.TestCase):
    def test_dc_transfer_exposes_common_return(self):
        resistors = {"R1": ["VSS", "a", "2"], "R2": ["a", "b", "3"]}
        np.testing.assert_allclose(rail_matrix("VSS", resistors, ["a", "b"]), [[2.,2.],[2.,5.]])

    def test_dc_transfer_preserves_parallel_paths(self):
        resistors = {"R1": ["VSS", "a", "10"], "R2": ["VSS", "a", "10"]}
        np.testing.assert_allclose(rail_matrix("VSS", resistors, ["a"]), [[5.]])

    def test_only_a_real_branch_bridge_is_accepted(self):
        rs = {"R87": ["shared", "local", "6"], "R68": ["local", "bl", "566"],
              "R60": ["local", "blb", "567"], "R76": ["local", "tail", "387"]}
        bitmap = [{"sampler_bl": "bl", "sampler_blb": "blb", "tail": "tail"}]
        keys = tuple(bitmap[0])
        nodes = {"shared","local","bl","blb","tail"}
        self.assertEqual(branch_forks(rs,nodes,bitmap,keys,"shared"),
                         {0:("R87","shared","local",6.)})
        rs["R100"] = ["shared", "tail", "1000"]
        with self.assertRaisesRegex(ValueError, "Unexpected branch"):
            branch_forks(rs,nodes,bitmap,keys,"shared")


if __name__ == "__main__":
    unittest.main()
