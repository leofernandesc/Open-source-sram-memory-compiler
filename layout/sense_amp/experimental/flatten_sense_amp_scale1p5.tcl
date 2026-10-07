load sense_amp_scale1p5
save sense_amp_scale1p5_routed_hier
flatten sense_amp_scale1p5_flat
load sense_amp_scale1p5_flat
drc check
puts "SCALE1P5_FLAT_DRC_BEGIN"
drc count total
puts "SCALE1P5_FLAT_DRC_END"
save sense_amp_scale1p5_flat
quit -noprompt
