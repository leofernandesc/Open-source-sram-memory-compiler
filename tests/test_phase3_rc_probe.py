"""Guard the Phase 3 diagnostic probe's topology mapping."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))

from phase3_rc_probe import reference_node_map


class ProbeMappingTests(unittest.TestCase):
    @staticmethod
    def decks(reference_node='reference', resistance=True):
        pex = []
        baseline = []
        for i in range(1493):
            physical = 'left' if i == 0 else 'right' if i == 1 else 'other'
            equivalent = ('reference' if i == 0 else reference_node
                          if i == 1 else 'other')
            pex.append(f'X{i} {physical} VDD VDD VSS nmos w=1 l=1')
            baseline.append(f'X{i} {equivalent} VDD VDD VSS nmos w=1 l=1')
        if resistance:
            pex.append('Rsplit left right 42')
        return '\n'.join(pex), '\n'.join(baseline)

    def test_resistor_split_maps_both_terminals_to_original_net(self):
        pex, reference = self.decks()
        mapping = reference_node_map(pex, reference)
        self.assertEqual(mapping['left'], 'reference')
        self.assertEqual(mapping['right'], 'reference')

    def test_unconnected_reference_net_split_is_rejected(self):
        pex, reference = self.decks(resistance=False)
        with self.assertRaisesRegex(ValueError, 'split across RC components'):
            reference_node_map(pex, reference)

    def test_resistive_merge_of_distinct_reference_nets_is_rejected(self):
        pex, reference = self.decks(reference_node='other_reference')
        with self.assertRaisesRegex(ValueError, 'merges Phase 2 nets'):
            reference_node_map(pex, reference)


if __name__ == '__main__':
    unittest.main()
