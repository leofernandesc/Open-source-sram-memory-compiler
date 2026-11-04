#!/usr/bin/env python3
"""OpenROAD control placement; interface-only macro Liberty has no timing arcs."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from run_phase2_digital import sha
from phase2_abstract import emit
from phase2_lef_check import verify as verify_route_lef
from run_digital_regression import atomic_text,output_lock

ROOT=Path(__file__).resolve().parents[1]
HD=Path('/opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd')


def macro_interface(abstract):
    lines=['library (phase2_uncharacterized_interface) {','  delay_model : table_lookup;',
           '  time_unit : "1ns";','  capacitive_load_unit (1,pf);','  voltage_unit : "1V";',
           '  current_unit : "1mA";','  leakage_power_unit : "1nW";',
           '  nom_voltage : 1.8;','  nom_temperature : 25;','  nom_process : 1;',
           '  cell (leaf_fabric) {','    dont_touch : true;',
           f'    area : {abstract["size_um"][0]*abstract["size_um"][1]:.6f};']
    # Match HD's parser/measurement conventions. These thresholds supply no
    # delay arc, pin capacitance or characterized custom-macro timing value.
    thresholds=[]
    for edge in ('rise','fall'):
        for quantity,value in [('input_threshold_pct',50),('output_threshold_pct',50),
                               ('slew_lower_threshold_pct',20),('slew_upper_threshold_pct',80)]:
            thresholds.append(f'  {quantity}_{edge} : {value};')
    lines[1:1]=thresholds
    for pin in abstract['pins']:
        if pin in ('VDD','VSS'):
            role='primary_power' if pin=='VDD' else 'primary_ground'
            lines.append(f'    pg_pin ({pin}) {{ pg_type : {role}; voltage_name : "{pin}"; }}')
        else:
            direction='output' if pin.startswith(('DEC','DOUT')) else 'input'
            lines.append(f'    pin ({pin}) {{ direction : {direction}; }}')
    return '\n'.join(lines+['  }','}'])+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='reports/phase2/placement')
    parser.add_argument('--route',action='store_true')
    parser.add_argument('--fabric-report',default='reports/phase2/fabric')
    parser.add_argument('--binding-report',default='reports/phase2/physical_binding')
    parser.add_argument('--emit-only',action='store_true',help='Prepare deterministic inputs/Tcl only; never a placement/routing PASS')
    args=parser.parse_args();output=(ROOT/args.output).resolve()
    if not output.is_relative_to(ROOT/'reports/phase2') or output==ROOT/'reports/phase2':parser.error('Output under reports/phase2 required')
    fabric_source=(ROOT/args.fabric_report).resolve();binding_source=(ROOT/args.binding_report).resolve()
    if output in (fabric_source,binding_source):parser.error('Output cannot replace an input checkpoint')
    output.mkdir(parents=True,exist_ok=True)
    with output_lock(output):
        receipt={'status':'RUNNING','CORE':'NOT_EVALUATED','F2_FIS':'NOT_EVALUATED',
                 'timing':'Interface-only macro Liberty: no timing arcs/caps; no full SRAM STA closure'}
        def publish():atomic_text(output/'results.json',json.dumps(receipt,indent=2)+'\n')
        publish()
        try:
            root=ROOT/'build/phase2';root.mkdir(parents=True,exist_ok=True)
            build=Path(tempfile.mkdtemp(prefix='place-',dir=root));receipt['build_directory']=str(build.relative_to(ROOT))
            publish()
            abstract=emit(fabric_source,build)
            (build/'macro_interface.lib').write_text(macro_interface(abstract))
            source=binding_source;status=json.loads((source/'results.json').read_text())
            if status['status']!='PASS_MAPPING_ONLY':raise ValueError('Missing physical binding')
            names=set(status['cells'])-{'leaf_fabric'}
            names.update({'sky130_fd_sc_hd__clkbuf_2','sky130_fd_sc_hd__clkbuf_4',
                          'sky130_fd_sc_hd__tapvpwrvgnd_1',*[f'sky130_fd_sc_hd__fill_{n}' for n in (1,2,4,8)]})
            routing_lef,proof=verify_route_lef(names,build)
            receipt['routing_library']=proof
            atomic_text(output/'routing_library_check.json',json.dumps(proof,indent=2)+'\n')
            netlist=source/'binding.v'
            if not netlist.exists():netlist=ROOT/status['build_directory']/'binding.v'
            shutil.copyfile(netlist,build/'binding.v')
            sdc=ROOT/'physical/phase2/experimental.sdc'
            receipt['inputs']={str(p.relative_to(ROOT)):sha(p) for p in (source/'results.json',netlist,fabric_source/'results.json',fabric_source/'leaf_fabric.gds',fabric_source/'leaf_fabric.mag',sdc,Path(__file__))}
            commands=f'''set_thread_count 1
read_lef {HD}/techlef/sky130_fd_sc_hd__nom.tlef
read_lef {routing_lef}
read_lef {build}/leaf_fabric.lef
read_liberty {HD}/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_liberty {build}/macro_interface.lib
read_verilog {build}/binding.v
link_design sram_4x8_wrapper
initialize_floorplan -die_area {{0 0 540 380}} -core_area {{10 10 530 370}} -site unithd
source /opt/OpenROAD-flow-scripts/flow/platforms/sky130hd/make_tracks.tcl
place_inst -name macro_core.array_and_peripherals -origin {{80 80}} -orient R0 -status FIRM
# Reserve well-tap sites before placing functional cells. Inserting taps
# after detailed placement can put a tap on an already occupied FF site.
tapcell -distance 14 -tapcell_master sky130_fd_sc_hd__tapvpwrvgnd_1
add_global_connection -net VDD -pin_pattern {{^(VPWR|VPB|VDD)$}} -power
add_global_connection -net VSS -pin_pattern {{^(VGND|VNB|VSS)$}} -ground
global_connect
# This is the experimental transistor stimulus, not a characterized Fmax.
read_sdc {sdc}
# Phase pulses are data/control outputs, not register clocks. CTS must not
# balance away the intentional delay between request capture and evaluation.
set phase_clock_boundary [concat [get_pins -quiet *phase_delay*/A] [get_pins -quiet {{macro_core.release_phase/A macro_core.evaluation/B macro_core.write_drive/B}}]]
if {{[llength $phase_clock_boundary] != 83}} {{error "Missing physical phase clock boundary"}}
set_sense -type clock -stop_propagation $phase_clock_boundary
# Protect delay-chain internal connectivity while allowing CTS to attach a
# clock buffer to its first input. Freezing the entire instance forbids that
# legal clock-tree connection. Recount all 80 delay stages after routing.
set_dont_touch [get_nets -quiet *delay_clk*]
set_wire_rc -signal -layer met2
set_wire_rc -clock -layer met2
place_pins -hor_layers met3 -ver_layers met2
global_placement -density 0.20
detailed_placement
check_placement -verbose
write_db {build}/placed.odb
write_def {build}/placed.def
puts PHASE2_PLACEMENT_DONE
'''
            if args.route:
                commands+=f'''set phase_nets {{}}
foreach phase_net [get_nets -quiet macro_core.*] {{
    set phase_net_name [get_full_name $phase_net]
    if {{$phase_net_name ne "CLK"}} {{lappend phase_nets $phase_net_name}}
}}
set_cts_config -skip_nets $phase_nets -delay_buffer_derate 0.0
clock_tree_synthesis -clk_nets CLK -no_insertion_delay -dont_use_dummy_load -root_buf sky130_fd_sc_hd__clkbuf_2 -buf_list {{sky130_fd_sc_hd__clkbuf_2 sky130_fd_sc_hd__clkbuf_4}}
detailed_placement
check_placement
global_connect
source /opt/OpenROAD-flow-scripts/flow/platforms/sky130hd/pdn.tcl
pdngen
# Match the installed SKY130HD platform: lower signal access on met1 is
# required for the li1 standard-cell pins; clock trunks start on met3.
set_routing_layers -signal met1-met5 -clock met3-met5
set_global_routing_layer_adjustment met1-met5 0.2
# Generate real standard-cell pin access before guides, as in the installed
# OpenROAD flow. Geometric pin centres alone are insufficient for li1 pins.
pin_access
puts PHASE2_PIN_ACCESS_DONE
global_route
write_db {build}/global_routed.odb
puts PHASE2_GLOBAL_ROUTE_DONE
detailed_route -output_drc {build}/route_drc.rpt -droute_end_iter 30 -verbose 0
write_def {build}/routed.def
write_verilog {build}/routed.v
write_db {build}/routed.odb
puts PHASE2_ROUTING_DONE
'''
            commands+='exit\n';(build/'flow.tcl').write_text(commands)
            if args.emit_only:
                for name in ('flow.tcl','leaf_fabric.lef','abstract.json','macro_interface.lib'):shutil.copyfile(build/name,output/name)
                receipt.update(status='EMITTED_FLOW_ONLY',abstract=abstract)
                receipt['artifacts']={p.name:sha(p) for p in output.iterdir() if p.is_file() and p.name not in ('results.json','.run.lock')}
                publish();print('EMITTED_FLOW_ONLY: no physical tool execution or acceptance');return 0
            with (output/'openroad.txt').open('w') as log:
                result=subprocess.run(['openroad','-exit','flow.tcl'],cwd=build,stdout=log,stderr=subprocess.STDOUT,timeout=900)
            text=(output/'openroad.txt').read_text()
            for name in ('flow.tcl','macro_interface.lib','leaf_fabric.lef','abstract.json','placed.def','routed.def','routed.v','route_drc.rpt'):
                if (build/name).is_file():shutil.copyfile(build/name,output/name)
            if result.returncode or 'PHASE2_PLACEMENT_DONE' not in text:
                stage='routing' if 'PHASE2_PLACEMENT_DONE' in text else 'placement'
                raise ValueError(f'OpenROAD {stage} failed; see openroad.txt')
            if args.route and 'PHASE2_ROUTING_DONE' not in text:raise ValueError('OpenROAD routing incomplete')
            receipt.update(status='ROUTED_VERIFICATION_PENDING' if args.route else 'PLACED_ONLY',abstract=abstract)
            receipt['build_artifacts']={n:sha(build/n) for n in ('routed.odb','leaf_fabric.gds','leaf_fabric.lef') if (build/n).is_file()}
        except Exception as error:receipt.update(status='FAIL',error=str(error))
        receipt['artifacts']={p.name:sha(p) for p in output.iterdir() if p.is_file() and p.name not in ('results.json','.run.lock')}
        publish();print(json.dumps({k:receipt[k] for k in ('status','CORE','F2_FIS')},indent=2))
        if 'error' in receipt:print(receipt['error'])
        return 0 if receipt['status'] in ('PLACED_ONLY','ROUTED_VERIFICATION_PENDING') else 1


if __name__=='__main__':raise SystemExit(main())
