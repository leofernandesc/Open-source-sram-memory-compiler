set netlist "/work/layout/sense_amp/experimental/sense_amp_scale1p5_import.spice"
load __sense_amp_scale1p5_scratch__
magic::netlist_to_layout $netlist sky130

set physical_top sense_amp_scale1p5_sram6t
foreach child [cellname list children $physical_top] {
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
save sense_amp_scale1p5_import
select top cell
expand
drc euclidean on
drc style drc(full)
drc on
drc catchup
set import_errors [drc listall why]
puts "SCALE1P5_IMPORT_DRC_ERRORS=[llength $import_errors]"
if {[llength $import_errors] > 0} { puts "SCALE1P5_IMPORT_DRC_DETAIL=$import_errors" }
quit -noprompt
