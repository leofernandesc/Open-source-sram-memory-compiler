set netlist "/work/layout/row_decoder/row_decoder_import.spice"
load __row_decoder_import_scratch__
magic::netlist_to_layout $netlist sky130
set physical_top row_decoder_sram6t
set physical_children [cellname list children $physical_top]
puts "ROWDEC_CHILDREN=$physical_children"
foreach child $physical_children { load $child; save $child }
load $physical_top
save row_decoder_import
select top cell
drc style drc(full)
drc check
drc catchup
drc count total
quit -noprompt
