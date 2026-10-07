set netlist "/work/layout/wl_driver/experimental_s1p68_s2p5p04/wl_driver_s1p68_s2p5p04_import.spice"
load __wl_driver_s1p68_s2p5p04_scratch__
magic::netlist_to_layout $netlist sky130
set physical_top wl_driver_s1p68_s2p5p04
set physical_children [cellname list children $physical_top]
foreach child $physical_children { load $child; save $child }
load $physical_top
save wl_driver_s1p68_s2p5p04_import
drc check
drc count total
quit -noprompt
