# Initial SKY130A physical scaffold for the frozen precharge leaf.
set netlist "/work/layout/precharge/precharge_import.spice"

load __precharge_import_scratch__
magic::netlist_to_layout $netlist sky130

set physical_top precharge_sram6t
set physical_children [cellname list children $physical_top]
foreach child $physical_children {
    load $child
    save $child
}
load $physical_top
save precharge_import

select top cell
box select
puts "PRECHARGE_IMPORT_BBOX=[box values]"
drc check
drc count total
quit -noprompt
