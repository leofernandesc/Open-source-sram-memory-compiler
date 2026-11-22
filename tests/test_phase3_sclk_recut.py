"""Offline structural and capacitance-equivalence tests."""

from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from phase3_sclk_recut import (
    PCH, SCLK, UNKNOWN_INCLUDE, cap_ff, checked_inventory, eliminate_star,
    index_cards, isolated_star, next_deck, plan_boundaries, rail_paths_unchanged,
    source_card, unloaded_rail_leaves, unloaded_series,
)
from phase3_sclk_loaded import ARRAY, GATES, LOCAL_CLOCKS, Q_NAMES, bit_probes
from phase3_sense3_precondition import pwl_tokens
from run_phase3_sense3_isolation import ResistanceGraph


class CapacitanceTests(unittest.TestCase):
    def test_exact_star_matches_terminal_currents_for_independent_edge_slopes(self):
        weights={'WL':Decimal('6'),'VDD':Decimal('4'),'VSS':Decimal('2')}
        pairs=eliminate_star(weights)
        self.assertEqual(pairs,eliminate_star(dict(reversed(list(weights.items())))))
        slopes={'WL':Decimal('12'),'VDD':Decimal('6'),'VSS':Decimal(0)}
        floating_slope=sum(weights[n]*slopes[n] for n in weights)/sum(weights.values())
        direct={n:c*(slopes[n]-floating_slope) for n,c in weights.items()}
        result={n:Decimal(0) for n in weights}
        for a,b,c in pairs:
            result[a]+=c*(slopes[a]-slopes[b])
            result[b]+=c*(slopes[b]-slopes[a])
        for n in weights:
            self.assertLess(abs(result[n]-direct[n]),Decimal('1e-23'))

    def test_keep_all_native_positive_star_caps_and_refuse_resistive_or_active_nodes(self):
        cards={'C0':['plate','VDD','0.004p'],'C1':['VSS','plate','13f'],
               'C2':['plate','WL','0'],'C3':['plate','WL','6500a']}
        self.assertEqual(isolated_star('plate',index_cards(cards),cards),
                         {'VDD':Decimal('4'),'VSS':Decimal('13'),'WL':Decimal('6.5')})
        self.assertEqual(cap_ff('4.50e-3p'),Decimal('4.5'))
        with self.assertRaises(ValueError):
            cap_ff('-0.5f')
        for device,fields in (('R0',['plate','VSS','10']),('X0',['X','plate','Y','Z','n'])):
            changed=dict(cards)
            changed[device]=fields
            self.assertIsNone(isolated_star('plate',index_cards(changed),changed))


class FrontierTests(unittest.TestCase):
    def test_one_known_source_per_resistive_group_missing_group_stays_pending(self):
        resistors={'R0':['tap','middle','20'],'R1':['middle','plate','30'],
                   'R2':['source2','plate','100']}
        rg=ResistanceGraph(resistors)
        keep,groups=plan_boundaries({'plate','middle','unknown'},{'WL'},rg,
                          {'tap':{'trace':'wave'},'source2':{'trace':'wave2'}},{})
        self.assertEqual(keep,{'tap','middle','plate','source2'})
        measured,unknown=groups
        self.assertEqual(measured['source_node'],'tap')
        self.assertEqual(measured['proxy_path_ohm'],50.)
        self.assertEqual(unknown['classification'],'Indeterminada')
        self.assertIsNone(unknown['source'])

    def test_upstream_replay_does_not_retime_samples_and_pending_deck_is_blocked(self):
        old={'clock':'VREPLAY0 archive_0 VSS PWL(0n 0 1.125n 1.8 147n 0\n+ )'}
        result=source_card('VREPLAY8','CLK',{'mode':'recorded','trace':'clock'},None,old,'')
        self.assertEqual(pwl_tokens(result)[0],'VREPLAY8 CLK VSS')
        self.assertEqual(pwl_tokens(result)[1],pwl_tokens(old['clock'])[1])
        self.assertIn(f'.include "{UNKNOWN_INCLUDE}"',next_deck([],['v(clk)'],True))
        self.assertNotIn(UNKNOWN_INCLUDE,next_deck([],['v(clk)'],False))

    def test_no_silent_duplicate_native_identifier(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            checked_inventory('R1 a b 10\nR1 c d 15\n')
        self.assertEqual(checked_inventory('R1 a b 10\nC2 a b 1f\n'),
                         {'R1':'R1 a b 10','C2':'C2 a b 1f'})

    def test_remove_only_unloaded_rail_leaves_and_keep_parallel_supply_paths(self):
        r={'R0':['VDD','x','1'],'R1':['x','y','2'],'R2':['y','floating','3'],
           'R3':['x','loaded','1'],'R4':['VDD','y','4'],'R5':['y','observed','2'],
           'C0':['loaded','VSS','1f']}
        rail={'VDD','VSS','x','y','floating','observed','loaded'}
        removed=unloaded_rail_leaves(r,set(r),rail,{'VDD','VSS','observed'})
        self.assertEqual(removed,{'R2'})
        kept=set(r)-removed
        rail_paths_unchanged(r,kept,{},rail)
        with self.assertRaisesRegex(ValueError,'Supply path|supply path'):
            rail_paths_unchanged(r,kept-{'R3'}, {},rail)


    def test_series_equivalent_preserves_measurement_nodes_and_parallel_paths(self):
        cards={'R0':['VDD','p','4.5'],'R1':['p','q','5'],
               'R2':['q','load','3.5'],'R3':['VDD','load','100'],
               'C0':['load','VSS','10f']}
        equivalent,proof,removed=unloaded_series(cards,set(cards),{'VDD','VSS'})
        self.assertEqual(removed,{'R0','R1','R2'})
        self.assertEqual(len(equivalent),1)
        synthetic, pins=next(iter(equivalent.items()))
        self.assertEqual(set(pins[:2]),{'VDD','load'})
        self.assertEqual(Decimal(pins[2]),Decimal(13))
        self.assertEqual(proof[synthetic]['removed_nodes'],['p','q'])
        self.assertNotIn('R3',removed)
        partial,_,_=unloaded_series(cards,set(cards),{'VDD','VSS','q'})
        self.assertIn('q',next(iter(partial.values()))[:2])


class SenseTopologyTests(unittest.TestCase):
    def test_all_eight_branches_have_native_sampler_tail_and_precharge(self):
        cards={}
        probes={SCLK:'SCLK',PCH:'PCH'}
        for i in range(8):
            a,b,sa,sab,nt,s0,s1,s2=(f'{n}{i}' for n in ('bl','blb','sa','sab','nt','s0_','s1_','s2_'))
            probes.update({f'{ARRAY}.write_driver_{i}.BL':a,f'{ARRAY}.write_driver_{i}.BLB':b,
                f'_{43-i}_.A1':sa,f'{ARRAY}.sense_amp_{i}.SA_OUTB':sab,
                f'_{75+i}_.D':f'D{i}',Q_NAMES[i]:f'Q{i}',LOCAL_CLOCKS[i]:f'cap{i}'})
            cards.update({f'R{i*3+k}':['SCLK',node,'1'] for k,node in enumerate((s0,s1,s2))})
            devices=[(sa,s0,a,'VDD','pfet'),(sab,s1,b,'VDD','pfet'),
                     (nt,s2,'VSS','VSS','nfet'),(sa,sab,nt,'VSS','nfet'),
                     (sab,sa,nt,'VSS','nfet'),(a,'PCH','VDD','VDD','pfet'),
                     (b,'PCH','VDD','VDD','pfet'),(a,'PCH',b,'VDD','pfet')]
            cards.update({f'X{i*8+k}':list(p) for k,p in enumerate(devices)})
        graph=ResistanceGraph(cards)
        devices={n:c for n,c in cards.items() if n[0]=='X'}
        valid=[bit_probes(cards,graph,probes,devices,i) for i in range(8)]
        self.assertEqual(len({s[k] for s in valid for k in GATES}),24)
        self.assertEqual(valid[3]['sense_tail'],'nt3')
        self.assertEqual(valid[3]['bl_at_sense'],'bl3')
        self.assertEqual(valid[3]['currents'],dict(tail_id='X26',precharge_bl_id='X29',
                         precharge_blb_id='X30',equalizer_id='X31'))
        with self.assertRaises(ValueError):
            bit_probes(cards,graph,probes,{k:v for k,v in devices.items() if k!='X31'},3)


if __name__=='__main__':
    unittest.main()
