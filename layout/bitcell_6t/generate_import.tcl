# Initial SKY130A physical scaffold for the frozen 6T bitcell.
#
# This intentionally stops before routing.  It imports the canonical SPICE
# netlist through Magic's SKY130 PCell generator so transistor geometry stays
# tied to WPU/WPD/WACC = 0.42/1.26/0.60 um.  DRC/LVS closure is a separate gate.

set project_root "/work"
set netlist "$project_root/layout/bitcell_6t/bitcell_6t_import.spice"

load __bitcell_6t_import_scratch__
magic::netlist_to_layout $netlist sky130

set physical_top bitcell_6t_import_sram6t
foreach child [cellname list children $physical_top] {
    load $child
    snap internal
    set params [property parameters]
    if {![regexp {(^| )w ([0-9.]+)} $params -> _ width]} {
        error "Unable to identify generated bitcell child $child"
    }

    # The SKY130 generator creates DRC-clean LI/M1 contacts except for the
    # two isolated gate M1 pads, whose native area is below met1.6.  Enlarge
    # those pads horizontally while staying inside the source/body spacing.
    lassign [property FIXED_BBOX] llx lly urx ury
    set cx [expr {($llx + $urx) / 2}]
    set gy_top [expr {$ury - 102}]
    set gy_bot [expr {$lly + 102}]
    foreach gy [list $gy_top $gy_bot] {
        box values [expr {$cx - 50}] [expr {$gy - 23}] \
                   [expr {$cx + 50}] [expr {$gy + 23}]
        paint metal1
    }

    # The repaired copy is a physical cell, not a parameterized generator.
    # Dropping gencell prevents a later save from regenerating the original
    # geometry and discarding the gate-pad repair.
    property gencell ""

    if {$width == 0.42} {
        set repaired bitcell_6t_pu_device
    } elseif {$width == 1.26} {
        set repaired bitcell_6t_pd_device
    } elseif {$width == 0.6} {
        set repaired bitcell_6t_acc_device
    } else {
        error "Unexpected generated bitcell width $width in $child"
    }
    save $repaired

    load $repaired
    drc euclidean on
    drc style drc(full)
    drc on
    select top cell
    expand
    drc catchup
    set child_errors [drc listall why]
    puts "BITCELL_DEVICE_DRC cell=$repaired errors=[llength $child_errors]"
    if {[llength $child_errors] > 0} {
        puts "BITCELL_DEVICE_DRC_DETAIL cell=$repaired detail=$child_errors"
    }
}
load $physical_top
save bitcell_6t_import

select top cell
box select
puts "BITCELL_IMPORT_BBOX=[box values]"
quit -noprompt
