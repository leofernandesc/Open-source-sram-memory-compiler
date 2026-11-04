set_thread_count 1
read_lef /opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef
read_lef /opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
read_lef /opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_ef_sc_hd.lef
read_lef /work/build/phase2/place-mhuandas/leaf_fabric.lef
read_liberty /opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_liberty /work/build/phase2/place-mhuandas/macro_interface.lib
read_verilog /work/build/phase2/place-mhuandas/binding.v
link_design sram_4x8_wrapper
initialize_floorplan -die_area {0 0 540 380} -core_area {10 10 530 370} -site unithd
source /opt/OpenROAD-flow-scripts/flow/platforms/sky130hd/make_tracks.tcl
place_inst -name macro_core.array_and_peripherals -origin {80 80} -orient R0 -status FIRM
add_global_connection -net VDD -pin_pattern {^(VPWR|VPB|VDD)$} -power
add_global_connection -net VSS -pin_pattern {^(VGND|VNB|VSS)$} -ground
global_connect
# This is the experimental transistor stimulus, not a characterized Fmax.
create_clock -name CLK -period 20 -waveform {0 10} [get_ports CLK]
set_dont_touch [get_cells *phase_delay*]
set_wire_rc -signal -layer met2
set_wire_rc -clock -layer met2
place_pins -hor_layers met3 -ver_layers met2
global_placement -density 0.20
detailed_placement
check_placement -verbose
write_db /work/build/phase2/place-mhuandas/placed.odb
write_def /work/build/phase2/place-mhuandas/placed.def
puts PHASE2_PLACEMENT_DONE
exit
