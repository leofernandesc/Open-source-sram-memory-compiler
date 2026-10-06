set netlist "/work/layout/wl_driver/wl_driver_import.spice"

load __wl_driver_import_scratch__
magic::netlist_to_layout $netlist sky130

set physical_top wl_driver_sram6t
set physical_children [cellname list children $physical_top]
foreach child $physical_children {
    load $child
    save $child
}
load $physical_top
save wl_driver_import

select top cell
box select
puts "WL_DRIVER_IMPORT_BBOX=[box values]"
drc check
drc count total
quit -noprompt
