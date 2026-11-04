set_thread_count 1
read_lef /opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef
read_lef /opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
read_lef /opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_ef_sc_hd.lef
read_lef /work/build/phase2/place-ltnunjhm/leaf_fabric.lef
read_liberty /opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_liberty /work/build/phase2/place-ltnunjhm/macro_interface.lib
read_verilog /work/build/phase2/place-ltnunjhm/binding.v
link_design sram_4x8_wrapper
initialize_floorplan -die_area {0 0 540 380} -core_area {10 10 530 370} -site unithd
source /opt/OpenROAD-flow-scripts/flow/platforms/sky130hd/make_tracks.tcl
place_inst -name macro_core.array_and_peripherals -origin {80 80} -orient R0 -status FIRM
# Reserve well-tap sites before placing functional cells. Inserting taps
# after detailed placement can put a tap on an already occupied FF site.
tapcell -distance 14 -tapcell_master sky130_fd_sc_hd__tapvpwrvgnd_1
add_global_connection -net VDD -pin_pattern {^(VPWR|VPB|VDD)$} -power
add_global_connection -net VSS -pin_pattern {^(VGND|VNB|VSS)$} -ground
global_connect
# This is the experimental transistor stimulus, not a characterized Fmax.
create_clock -name CLK -period 20 -waveform {0 10} [get_ports CLK]
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
write_db /work/build/phase2/place-ltnunjhm/placed.odb
write_def /work/build/phase2/place-ltnunjhm/placed.def
puts PHASE2_PLACEMENT_DONE
clock_tree_synthesis -root_buf sky130_fd_sc_hd__clkbuf_2 -buf_list {sky130_fd_sc_hd__clkbuf_2 sky130_fd_sc_hd__clkbuf_4}
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
global_route
detailed_route -output_drc /work/build/phase2/place-ltnunjhm/route_drc.rpt -droute_end_iter 30 -verbose 0
write_def /work/build/phase2/place-ltnunjhm/routed.def
write_verilog /work/build/phase2/place-ltnunjhm/routed.v
write_db /work/build/phase2/place-ltnunjhm/routed.odb
puts PHASE2_ROUTING_DONE
exit
