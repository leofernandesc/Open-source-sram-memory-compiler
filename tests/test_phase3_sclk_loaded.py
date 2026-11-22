"""Software checks for loaded-cut lineage, preservation and authorization."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from phase3_sclk_loaded import (
    INITIAL, START, STOP, control_verdict, gate_authorization, inventory, phase_deck,
    pull_region, replay, write_json,
)
from review_phase3_bus_ss import Trace
from run_phase3_eco_pex import sha256
from run_phase3_sense3_isolation import ResistanceGraph


class CutTests(unittest.TestCase):
    def test_retain_physical_driver_and_stop_at_upstream_source(self):
        cards=inventory('''X0 driver upstream VSS VSS n
X1 upstream omitted VSS VSS n
X2 latch load VSS VSS n
R0 driver local 1
R1 local load 10
''')
        tokens={k:v.split()[1:] for k,v in cards.items()}
        g=ResistanceGraph(tokens)
        keep,nets,bound=pull_region(tokens,g,{'local','latch'},('upstream','VSS'))
        self.assertEqual(keep,{'X0','X2'})
        self.assertEqual(nets,{'driver','local','load','latch'})
        self.assertEqual(bound,{'upstream','VSS'})

    def test_replay_preserves_evaluation_and_uses_write_prefix(self):
        time=[86.,87.,90.,110.,127.,188.,190.,210.,230.,247.,248.]
        volts=[0.,0.,1.,0.,0.,0.,1.,0.,1.,0.,0.]
        trace=Trace([(t*1e-9,v) for t,v in zip(time,volts)],{'test':1})
        # Trace interpolation includes the original measurement times.
        t,v=replay(trace,'test')
        self.assertEqual((t[0],t[-1]),(0.,STOP-INITIAL))
        for pos,val in ((150.,1.),(170.,0.),(START,0.),(210.,0.),(230.,1.)):
            i=min(range(len(t)),key=lambda i:abs(t[i]-(pos-INITIAL)))
            self.assertAlmostEqual(t[i],pos-INITIAL)
            self.assertAlmostEqual(v[i],val)

    def test_candidate_changes_only_r87_and_adds_immutable_driver(self):
        with tempfile.TemporaryDirectory() as path:
            p=Path(path)
            original='X1 rc8571 input VSS VSS model\nR87 rc8562 rc8571 6.46438\n'
            (p/'slice.spice').write_text(original)
            (p/'stimuli.spice').write_text('V1 CLK VSS 0\n')
            for n in ('driver_library.spice','driver_cell.spice'):
                (p/n).write_text(f'* sealed {n}\n')
            manifest=dict(measurements={},config=[],sclk={'branch':dict(upstream='rc8562',local='rc8571',
                          resistance_ohm=6.46438)},supply=dict(proposed_local_vdd='rc2114',proposed_local_vss='rc5874'))
            def directory(q):
                q.mkdir()
                return q
            with patch('phase3_sclk_loaded.new_directory',side_effect=directory):
                a,_=phase_deck(p,manifest,'control')
                b,_=phase_deck(p,manifest,'candidate')
            self.assertEqual((a/'slice.spice').read_text(),original)
            self.assertEqual((b/'slice.spice').read_text(),original.replace('R87 rc8562','R87 driver_output'))
            self.assertEqual((a/'stimuli.spice').read_bytes(),(b/'stimuli.spice').read_bytes())
            self.assertIn('XLOCAL driver_input driver_output driver_power rc5874', (b/'local_driver.spice').read_text())


class AuthorizationTests(unittest.TestCase):
    def test_gate_distinguishes_logical_reproduction_and_electrical_fidelity(self):
        good=[dict(observed_word=word,archived_word=word,logical_reference=True,equivalent=True)
              for word in (15,248,248)]
        self.assertEqual(control_verdict(good),'VALIDATED')
        good[1]['equivalent']=False
        self.assertEqual(control_verdict(good),'INCONCLUSIVE')
        good[1]['observed_word']=240
        self.assertEqual(control_verdict(good),'NOT_REPRODUCED')

    def test_gate_requires_sealed_receipt_and_waveform(self):
        with tempfile.TemporaryDirectory() as path:
            p=Path(path)
            (p/'control').mkdir()
            (p/'manifest.json').write_text('{}')
            (p/'control/result.json').write_text('{}')
            wave=p/'control/waveform.dat'
            wave.write_text('sealed')
            gate=p/'control_gate.json'
            authority=dict(verdict='INCONCLUSIVE',manifest_sha256=sha256(p/'manifest.json'),
                           result_sha256=sha256(p/'control/result.json'),control_artifacts={'waveform.dat':sha256(wave)})
            write_json(gate,authority)
            with self.assertRaisesRegex(ValueError,'did not validate'):
                gate_authorization(p)
            gate.write_text(json.dumps(dict(authority,verdict='VALIDATED')))
            self.assertEqual(gate_authorization(p),gate)
            wave.write_text('changed')
            with self.assertRaisesRegex(ValueError,'hash differs'):
                gate_authorization(p)


if __name__=='__main__':
    unittest.main()
