set netlist "/work/layout/sense_amp/experimental/sense_amp_scale1p5_import.spice"
load __sense_amp_scale1p5_scratch__
magic::netlist_to_layout $netlist sky130

set physical_top sense_amp_scale1p5_sram6t
foreach child [cellname list children $physical_top] {
    load $child
    save $child
}
load $physical_top
save sense_amp_scale1p5_import
drc check
puts "SCALE1P5_IMPORT_DRC_BEGIN"
drc count total
puts "SCALE1P5_IMPORT_DRC_END"
quit -noprompt
