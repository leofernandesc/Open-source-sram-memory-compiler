load write_driver_w5p04
save write_driver_w5p04_routed_hier
flatten write_driver_w5p04_flat
load write_driver_w5p04_flat
drc check
puts "WRITE_W5P04_FLAT_DRC_BEGIN"
drc count total
puts "WRITE_W5P04_FLAT_DRC_END"
save write_driver_w5p04_flat
quit -noprompt
