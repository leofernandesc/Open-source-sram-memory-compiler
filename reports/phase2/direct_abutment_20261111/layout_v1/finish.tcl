set_thread_count 1
read_db /work/build/phase2/place-v3nwnvsg/routed.odb
filler_placement {sky130_fd_sc_hd__fill_8 sky130_fd_sc_hd__fill_4 sky130_fd_sc_hd__fill_2 sky130_fd_sc_hd__fill_1}
global_connect
check_placement -verbose
puts "FINAL_DELAY_STAGES=[llength [get_cells *phase_delay*]]"
write_def /work/build/phase2/finish-yqqyjrug/final.def
write_verilog /work/build/phase2/finish-yqqyjrug/final.v
write_verilog -include_pwr_gnd /work/build/phase2/finish-yqqyjrug/final_powered.v
write_db /work/build/phase2/finish-yqqyjrug/final.odb
exit
