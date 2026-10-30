#!/usr/bin/env python3
"""Requalify unchanged leaf masks and restored G7 runners in a fresh directory.

This repository-integration check is not a full SRAM macro test. Physical
checks work on copies and never regenerate distributed R-C parasitics.
"""
import argparse
import copy
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import freeze_keeper_revision as freeze
import verify_phase1_physical as physical


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();out=args.output_dir.resolve()
    freeze.ensure(out.is_relative_to(ROOT),'Keep reviewable evidence in this checkout')
    freeze.ensure(not out.exists(),'Use a new output directory')
    freeze.check();out.mkdir(parents=True)
    manifest=json.loads((ROOT/'release/phase1_keeper/manifest.json').read_text())
    state=dict(status='RUNNING',complete=False,started_utc=datetime.now(timezone.utc).isoformat(),
        branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
        runner_sha256=freeze.sha(Path(__file__)),
        active_manifest_sha256=freeze.sha(ROOT/'release/phase1_keeper/manifest.json'),
        new_rc_extraction=False,physical=[],commands=[])
    record=out/'manifest.json'
    def save():record.write_text(json.dumps(state,indent=2)+'\n')
    save();shutil.copy2(__file__,out/'executed_script.py')
    physical.RELEASE=out/'physical'
    try:
        for name,item in manifest['cells'].items():
            selected=copy.deepcopy(item);folder=out/'physical/cells'/name;folder.mkdir(parents=True)
            for kind,info in selected['files'].items():
                source=ROOT/info['path'];destination=folder/source.name;shutil.copy2(source,destination)
                info['path']=str(destination.relative_to(ROOT))
            result=physical.verify(name,selected,True)
            state['physical'].append(result);save()
            print(f'{name}: fresh DRC 0, dimension/terminal LVS and 5 negative controls PASS',flush=True)
        def command(label,options):
            script=ROOT/'sims'/options[0]
            source=out/'scripts'/script.name;source.parent.mkdir(exist_ok=True);shutil.copy2(script,source)
            cmd=[sys.executable,str(script),*options[1:]]
            case=dict(label=label,argv=cmd,runner_sha256=freeze.sha(script),status='RUNNING')
            state['commands'].append(case);save()
            process=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            console=out/f'{label}_console.txt';console.write_text(process.stdout)
            case.update(returncode=process.returncode,status='PASS' if process.returncode==0 else 'FAIL',
                        console_sha256=freeze.sha(console));save()
            print(label,case['status'],flush=True)
        (out/'scripts').mkdir(exist_ok=True)
        for filename in ('qualification_contract.py','pex_access_nodes.py'):
            shutil.copy2(ROOT/'sims'/filename,out/'scripts'/filename)
        pdk='/opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice'
        sys.path.insert(0,str(ROOT/'sims'))
        from qualification_contract import model_hashes
        state['model_sha256']=model_hashes(pdk)
        state['tools']={name:dict(path=shutil.which(name),sha256=freeze.sha(shutil.which(name)))
                        for name in ('xschem','magic','netgen','ngspice')}
        common=['--pex','--cbl-total-ff','597.056240839','--wl-extra-ff','93.351918068',
            '--precharge-pex-netlist','layout/precharge/experimental_w2p52/pex/precharge_w2p52_pex.spice',
            '--wl-driver-pex-netlist','layout/wl_driver/experimental_s1p68_s2p5p04/pex/wl_driver_s1p68_s2p5p04_pex.spice']
        command('g7_read',['run_integrated_column_read.py',*common,
            '--sense-pex-netlist','layout/sense_amp/experimental/pex/sense_amp_scale1p5_pex.spice',
            '--pex-cell-access-ceff-ff','6.112663899','--pex-precharge-ceff-ff','11.469723791',
            '--pex-sense-ceff-ff','31.644459025','--sclk-at-ns','4.6','--wl-in-width-ns','3',
            '--workers','1','--parts-dir',str(out/'g7_read_parts'),'--output',str(out/'g7_read.csv')])
        command('g7_write',['run_integrated_column_write.py',*common,
            '--write-pex-netlist','layout/write_driver/experimental_w5p04/pex/write_driver_w5p04_pex.spice',
            '--bitcell-capacitance-csv','sims/bitcell_pex_bitline_capacitance_latch_t0_requal_20261008.csv',
            '--precharge-capacitance-csv','sims/precharge_w2p52_pex_capacitance_provenance_20261008.csv',
            '--write-capacitance-csv','sims/write_driver_w5p04_pex_capacitance_provenance_20261008.csv',
            '--wl-in-at-ns','3.4','--workers','1',
            '--parts-dir',str(out/'g7_write_parts'),'--output',str(out/'g7_write.csv')])
        command('source_smoke',['run_leaf_peripheral_smoke.py','--blocks','precharge','wl_driver',
            '--corners','tt','ss','ff','--vdd-values','1.8','--temps-c','27',
            '--precharge-cap-ff','16','60','--wl-cap-ff','17.4','50',
            '--output',str(out/'source_smoke.csv')])
        freeze.check()
        good=all(c['status']=='PASS' for c in state['commands'])
        state.update(complete=True,status='PASS' if good else 'FAIL')
    except Exception as error:
        state.update(status='FAIL',error=f'{type(error).__name__}: {error}')
        raise
    finally:
        state['finished_utc']=datetime.now(timezone.utc).isoformat()
        state['artifact_sha256']={str(p.relative_to(out)):freeze.sha(p) for p in sorted(out.rglob('*'))
                                  if p.is_file() and p!=record}
        save()
    return 0 if state['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
