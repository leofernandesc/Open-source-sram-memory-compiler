set netlist "/work/layout/write_driver/experimental_w5p04/write_driver_w5p04_import.spice"
load __write_driver_w5p04_scratch__
magic::netlist_to_layout $netlist sky130
set physical_top write_driver_w5p04_sram6t
set physical_children [cellname list children $physical_top]
foreach child $physical_children { load $child; save $child }
load $physical_top
save write_driver_w5p04_import
drc check
puts "WRITE_W5P04_IMPORT_DRC_BEGIN"
drc count total
puts "WRITE_W5P04_IMPORT_DRC_END"
quit -noprompt
