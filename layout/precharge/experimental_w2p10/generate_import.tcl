set netlist "/work/layout/precharge/experimental_w2p10/precharge_w2p10_import.spice"
load __precharge_w2p10_scratch__
magic::netlist_to_layout $netlist sky130
set physical_top precharge_w2p10_sram6t
set physical_children [cellname list children $physical_top]
foreach child $physical_children { load $child; save $child }
load $physical_top
save precharge_w2p10_import
drc check
puts "PRECH_W2P10_IMPORT_DRC_BEGIN"
drc count total
puts "PRECH_W2P10_IMPORT_DRC_END"
quit -noprompt
