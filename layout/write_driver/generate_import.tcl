set netlist "/work/layout/write_driver/write_driver_import.spice"

load __write_driver_import_scratch__
magic::netlist_to_layout $netlist sky130

set physical_top write_driver_sram6t
set physical_children [cellname list children $physical_top]
foreach child $physical_children {
    load $child
    save $child
}
load $physical_top
save write_driver_import

select top cell
box select
puts "WRITE_DRIVER_IMPORT_BBOX=[box values]"
drc check
drc count total
quit -noprompt
