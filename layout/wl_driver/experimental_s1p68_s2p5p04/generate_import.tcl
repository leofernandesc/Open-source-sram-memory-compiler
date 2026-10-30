set netlist "/work/layout/wl_driver/experimental_s1p68_s2p5p04/wl_driver_s1p68_s2p5p04_import.spice"
load __wl_driver_s1p68_s2p5p04_scratch__
magic::netlist_to_layout $netlist sky130
set physical_top wl_driver_s1p68_s2p5p04
set physical_children [cellname list children $physical_top]
foreach child $physical_children {
    load $child
    snap internal
    lassign [property FIXED_BBOX] llx lly urx ury
    set cx [expr {($llx + $urx) / 2}]
    foreach gy [list [expr {$ury - 102}] [expr {$lly + 102}]] {
        box values [expr {$cx - 50}] [expr {$gy - 23}] \
                   [expr {$cx + 50}] [expr {$gy + 23}]
        paint metal1
    }
    property gencell ""
    save $child
}
load $physical_top
save wl_driver_s1p68_s2p5p04_import
select top cell
expand
drc euclidean on
drc style drc(full)
drc on
drc catchup
set import_errors [drc listall why]
puts "WLDRV_IMPORT_DRC_ERRORS=[llength $import_errors]"
if {[llength $import_errors] > 0} { puts "WLDRV_IMPORT_DRC_DETAIL=$import_errors" }
quit -noprompt
