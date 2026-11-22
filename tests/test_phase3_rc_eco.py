"""ECO reconstruction and waveform diagnostic regressions. No simulator needed."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from rebuild_phase3_danilo_eco import BASE, edit_binding, place_data7_pair, relocate_data_pins, replace_output_enables
from run_phase3_eco_pex import PROTOCOL_VECTORS, has_resistive_port, localize_failures, protocol_checks, restore_subatto
from phase3_rc_output_slice import generate
from phase3_rc_read_path import OUTPUT_ENABLES
from phase3_rc_turnaround import current_below, deck_text
from route_phase3_data7_metal4 import EDGE_PIN, INNER_PIN, OLD, PROMOTED, promote, relocate_access


class EcoTests(unittest.TestCase):
    def test_subatto_restoration_uses_only_zero_substrate_cards(self):
        raw = 'C0 node VSS 0 ; **FLOATING\nC1 node VDD 0\nC2 other VSS 1f\nR0 node other 10\n'
        source = 'scale 1000 1 500000\nrnode "node" 0 0.5 0 0 0\nrnode "other" 0 0.8 0 0 0\n'
        fixed, repairs = restore_subatto(raw, source)
        self.assertEqual(fixed, raw.replace('C0 node VSS 0', 'C0 node VSS 5e-19'))
        self.assertEqual(repairs, [dict(card='C0', node='node', capacitance_attofarads=.5)])

    def test_flat_reference_restores_only_discrepant_exported_zero_caps(self):
        raw = 'C0 selected VSS 0\nC1 unselected VSS 0\nC2 selected VDD 0\nC3 above VSS 0\n'
        source = ('timestamp 123\nversion 8.3\ntech sky130A\nstyle ngspice()\nscale 1000 1 500000\n'
                  'node "selected" 197 0.75 20 30 pdif\nnode "unselected" 1 0.9 40 50 pdif\n'
                  'node "above" 2 1.5 60 70 pdif\n')
        fixed, repairs = restore_subatto(raw, source, flat_nodes=True,
                                        selected_nodes={'selected', 'above', 'missing'})
        self.assertEqual(fixed, raw.replace('C0 selected VSS 0', 'C0 selected VSS 7.5e-19'))
        self.assertEqual(repairs, [dict(card='C0', node='selected', capacitance_attofarads=.75)])

    def test_inner_port_changes_only_data7_pin_and_drop(self):
        net = '    - DATA[7] ( PIN DATA[7] ) ( _94_ Z ) ( _52_ A1 ) + USE SIGNAL\n'
        drop = '      NEW met2 ( 384790 61160 ) ( * 61710 )\n      NEW met2 ( 384790 61710 ) M2M3_PR\n'
        other = '    - DATA[6] + NET DATA[6] + DIRECTION INOUT + USE SIGNAL\n'
        source = other + EDGE_PIN + net + OLD + ' ;\n'
        self.assertEqual(relocate_access(source), other + INNER_PIN + net + drop + ' ;\n')
        with self.assertRaisesRegex(ValueError, 'pinned DATA7 access'):
            relocate_access(source.replace(EDGE_PIN, INNER_PIN))

    def test_capture_slice_holds_other_cells_and_loads_constant(self):
        deck, loads = generate('ss', capture_slice=True)
        self.assertEqual(deck.count('sky130_fd_sc_hd__dfxtp_2'), 3)
        self.assertEqual(deck.count('sky130_fd_sc_hd__ebufn_8'), 3)
        self.assertEqual(deck.count('24.166f'), 3)
        self.assertEqual(deck.count('2.545f'), 3)
        self.assertEqual(loads['data7']['q_ff'], 5.630)
        self.assertTrue(all(deck.count(f'sky130_fd_sc_hd__clkinv_{size}') == 1 for size in (1, 2, 4)))

    def test_binding_preserves_public_and_input_domains(self):
        original = (BASE / 'route_v1/routed.v').read_text()
        eco = edit_binding(original)
        self.assertEqual(eco.count('sky130_fd_sc_hd__ebufn_8 '), 8)
        self.assertEqual(eco.count('sky130_fd_sc_hd__clkinv_1 '), 8)
        self.assertEqual(eco.count('(.A(CLK)'), original.count('(.A(CLK)') + 8)
        self.assertIn('.C(\\macro_core.delay_clk [48])', eco)
        self.assertEqual(eco.count('sky130_fd_sc_hd__dfxtp_1 '), 20)
        strengthened = edit_binding(original, output_ff='dfxtp_2')
        self.assertEqual(strengthened.count('sky130_fd_sc_hd__dfxtp_2 '), 8)
        self.assertEqual(strengthened.replace('sky130_fd_sc_hd__dfxtp_2 ',
                                             'sky130_fd_sc_hd__dfxtp_1 '), eco)
        with self.assertRaisesRegex(ValueError, 'evaluation'):
            edit_binding(eco)

    def test_classify_independent_sense_and_data_failures(self):
        t = [139.99e-9, 140e-9, 140.1e-9, 141e-9, 141.2e-9]
        for sense, d, q, expected_stage in (
                (0, 0, 0, 'SENSE_INVALID_AT_CAPTURE'),
                (1.8, 0, 0, 'D_INVALID_AT_CAPTURE'),
                (1.8, 1.8, 0, 'Q_INVALID_AT_OBSERVATION'),
                (1.8, 1.8, 1.8, 'DATA_INVALID_WITH_VALID_D_Q')):
            with self.subTest(stage=expected_stage):
                rows = [(time, *([1.2] * 9), 1.8 if i >= 2 else 0, sense, d, q, 0)
                        for i, time in enumerate(t)]
                columns = {'_33_.Y': 10, '_43_.A1': 11, '_75_.D': 12, '_75_.Q': 13,
                           '_87_.TE_B': 14}
                checks = [{'status': 'FAIL', 'cycle': 6, 'bit': 0, 'expected': 1, 'observed_v': 1.2}]
                cycles = [{'cycle': 6, 'row': 0, 'rise_ns': 130, 'fall_ns': 140, 'sample_ns': 141}]
                self.assertEqual(localize_failures(rows, columns, checks, cycles)[0]['stage'],
                                 expected_stage)

    def test_relocate_only_data_pins_with_existing_flow(self):
        placement = 'place_pins -hor_layers met3 -ver_layers met2\n'
        commands = relocate_data_pins(placement + 'global_placement\n', 'distributed').splitlines()
        self.assertEqual(commands[0], placement.strip())
        self.assertEqual(commands[-1], 'global_placement')
        self.assertEqual(len(commands[1:-1]), 8)
        for bit, command in enumerate(commands[1:-1]):
            self.assertIn(f'-pin_name {{DATA[{bit}]}} -layer met2', command)
        spaced = relocate_data_pins(placement + 'global_placement\n', 'distributed-spaced').splitlines()
        self.assertEqual([old for old, new in zip(commands, spaced) if old != new], [commands[2]])
        self.assertIn('-pin_name {DATA[1]} -layer met2 -location {260 0.242}', spaced[2])

    def test_write_readiness_and_overlap_are_independent(self):
        din = [f'_{67+bit}_.Q' for bit in range(8)]
        we = 'macro_core.write_drive.X'
        columns = {label: col for col, label in enumerate(
            [*din, *OUTPUT_ENABLES, *PROTOCOL_VECTORS, we], 1)}
        records = [dict(operation='write', cycle=2, expected=255, rise_ns=50, fall_ns=60,
                        host_enable_ns=47, host_payload_ns=48)]
        for late_data in (False, True):
            rows = []
            for ns in [45, 47, 48, 50, 51.1, 52, 53, 54, 59.5, 60]:
                row = [ns * 1e-9] + [0.] * len(columns)
                for name in din:
                    row[columns[name]] = 1.8 if ns >= (54 if late_data else 52) else 0.
                for name in OUTPUT_ENABLES:
                    row[columns[name]] = 1.8 if ns >= 48 else 0.
                row[columns[we]] = 1.8 if ns >= 53 else 0.
                row[columns['v(HOST_EN)']] = 1.8 if ns >= 47 else 0.
                rows.append(row)
            checks = protocol_checks(rows, columns, records)
            self.assertEqual([c['status'] for c in checks if c['kind'] == 'no_strong_host_ebuf_overlap'],
                             ['FAIL'] * 8)
            self.assertEqual([c['status'] for c in checks if c['kind'] == 'write_data_ready_before_we20'],
                             ['FAIL' if late_data else 'PASS'] * 8)
            self.assertEqual([c['status'] for c in checks if c.get('scope') == 'diagnostic'], ['FAIL'] * 8)

    def test_data7_pair_only_fixes_the_two_intended_instances(self):
        flow = '# Reserve well-tap sites before placing functional cells.\ntapcell\n'
        placed = place_data7_pair(flow)
        self.assertEqual(placed.splitlines()[2:], flow.splitlines())
        self.assertIn('place_inst -name _82_', placed.splitlines()[0])
        self.assertIn('place_inst -name _94_', placed.splitlines()[1])
        with self.assertRaisesRegex(ValueError, 'single tap'):
            place_data7_pair(flow + flow)

    def test_diagnostic_guard_changes_only_the_strong_host_enable(self):
        short = deck_text('ss', ['rc32'], 300).splitlines()
        long = deck_text('ss', ['rc32'], 1500).splitlines()
        changed = [(a, b) for a, b in zip(short, long) if a != b]
        self.assertEqual(len(changed), 1)
        a, b = changed[0]
        self.assertTrue(a.startswith('V_HOST_EN ') and b.startswith('V_HOST_EN '))
        self.assertIn('68.800000n 0', a)
        self.assertIn('70.000000n 0', b)

    def test_nand4bb_replaces_only_the_outputs_and_keeps_read_capture(self):
        baseline = edit_binding((BASE / 'route_v1/routed.v').read_text(), output_ff='dfxtp_2')
        modified = replace_output_enables(baseline, 4)
        self.assertEqual(modified.count('sky130_fd_sc_hd__nand4bb_4 '), 8)
        self.assertEqual(modified.count('.A_N(OEb),\n    .B_N(CSb),\n    .C(WEb),\n    .D(\\control.READ_Q )'), 8)
        self.assertIn('_84_ (.D(live_read)', modified)
        self.assertEqual(baseline.count('live_read') - modified.count('live_read'), 8)
        with self.assertRaisesRegex(ValueError, 'independent READ'):
            replace_output_enables(baseline.replace('_84_ (.D(live_read)', '_84_ (.D(OEb)'), 4)

    def test_current_settling_uses_last_crossing_and_current_polarity(self):
        for polarity in (1., -1.):
            rows = [(ns*1e-9, polarity*ua*1e-6) for ns, ua in ((0, 100), (1, 0), (2, 100), (3, 0), (4, 10))]
            self.assertAlmostEqual(current_below(rows, 1, 0., 4e-9, 50e-6), 2.5e-9, delta=1e-15)
            self.assertIsNone(current_below(rows, 1, 0., 2e-9, 50e-6))

    def test_metal4_promotion_changes_only_the_pinned_data7_drop(self):
        source = ('NETS 2 ;\n    - DATA[7] ( PIN DATA[7] ) ( _94_ Z ) ( _52_ A1 ) + USE SIGNAL\n'
                  '      + ROUTED met1 ( 384790 61710 ) ( 395370 * )\n' + OLD
                  + '      NEW met1 ( 384790 61710 ) M1M2_PR ;\n'
                  '    - DATA[6] ( PIN DATA[6] ) + USE SIGNAL ;\nEND NETS\n')
        modified = promote(source)
        self.assertEqual(modified.replace(PROMOTED, OLD), source)
        self.assertEqual(modified.count(PROMOTED), 1)
        with self.assertRaisesRegex(ValueError, 'met2 drop'):
            promote(modified)

    def test_required_rc_port_needs_a_resistor_connected_to_the_pin(self):
        extracted = 'C2 DATA[7] VSS 15f\nR1 DATA[7].n0 DATA[7].n1 10\n'
        self.assertFalse(has_resistive_port(extracted, 'DATA[7]'))
        self.assertTrue(has_resistive_port(extracted + 'R2 DATA[7].n0 DATA[7] 20\n', 'DATA[7]'))
