# Build a physical 32-row SRAM bitline column from the frozen 6T bitcell.
# The bitcells are stacked vertically at zero gap.  BL/BLB, VDD, VSS and the
# deselected wordlines are collected on dedicated metal4 trunks through via3.

path search +../bitcell_6t

load column_32_p2652
box values -100000 -100000 100000 100000
select area
delete
select clear
snap internal

set llx -450
set lly -2942
# The repaired routed-cell bbox is 2584 units tall.  Leave 68 units between
# rows so via3 landings and M3 rail edges both clear the neighboring row.
set pitch_y 2652
set rows 32

# Parent coordinates of the child M3 rails after aligning the routed-cell bbox
# lower-left corner to (0, row*pitch_y).
set x_bl    220
set x_blb   520
set x_vss   820
set x_vdd  1120
set x_wl   1420

set y_bl_offset   192
set y_blb_offset   42
set y_vss_offset  492
set y_vdd_offset 2542
set y_wl_offset   342

for {set row 0} {$row < $rows} {incr row} {
    set y [expr {$row * $pitch_y}]
    getcell bitcell_6t_flat child $llx $lly parent 0 $y
}

set column_top [expr {$rows * $pitch_y}]

proc m4_trunk {x ylo yhi} {
    box values [expr {$x - 40}] $ylo [expr {$x + 40}] $yhi
    paint metal4
}

proc m3_to_m4 {x y} {
    # Adjacent M3 rails are 150 units apart.  Keep this landing at 96 units
    # so its edge clears the next 72-unit-wide rail by the required 60 units.
    # The via3 cut must be at least 64 units wide.
    box values [expr {$x - 48}] [expr {$y - 48}] [expr {$x + 48}] [expr {$y + 48}]
    paint metal3
    paint metal4
    box values [expr {$x - 32}] [expr {$y - 32}] [expr {$x + 32}] [expr {$y + 32}]
    contact via3
}

foreach x [list $x_bl $x_blb $x_vss $x_vdd $x_wl] {
    m4_trunk $x -80 [expr {$column_top + 80}]
}

for {set row 0} {$row < $rows} {incr row} {
    set base [expr {$row * $pitch_y}]
    m3_to_m4 $x_bl  [expr {$base + $y_bl_offset}]
    m3_to_m4 $x_blb [expr {$base + $y_blb_offset}]
    m3_to_m4 $x_vss [expr {$base + $y_vss_offset}]
    m3_to_m4 $x_vdd [expr {$base + $y_vdd_offset}]
    m3_to_m4 $x_wl  [expr {$base + $y_wl_offset}]
}

proc make_m4_port {name index x y} {
    box values [expr {$x - 30}] [expr {$y - 30}] [expr {$x + 30}] [expr {$y + 30}]
    label $name center metal4
    select clear
    select do labels
    select area metal4
    port make $index n
    select clear
    select no labels
}

set port_y [expr {$column_top + 40}]
make_m4_port BL    0 $x_bl  $port_y
make_m4_port BLB   1 $x_blb $port_y
make_m4_port VSS   2 $x_vss $port_y
make_m4_port VDD   3 $x_vdd $port_y
make_m4_port WLOFF 4 $x_wl  $port_y

drc euclidean on
drc style drc(full)
drc on
select top cell
expand
box select
drc check
drc catchup
set column32_hier_errors 0
foreach {rule boxes} [drc listall why] {
    puts "COLUMN32_HIER_DRC_RULE=$rule BOXES=[llength $boxes]"
    if {[llength $boxes] > 0} { puts "COLUMN32_HIER_DRC_SAMPLES=[lrange $boxes 0 9]" }
    incr column32_hier_errors [llength $boxes]
}
puts "COLUMN32_HIER_DRC_ERRORS=$column32_hier_errors"
if {$column32_hier_errors != 0} { error "column_32 hierarchical DRC failed" }

save column_32_p2652
flatten column_32_p2652_flat
load column_32_p2652_flat
select top cell
expand
box select
drc check
drc catchup
set column32_flat_errors 0
foreach {rule boxes} [drc listall why] {
    puts "COLUMN32_FLAT_DRC_RULE=$rule BOXES=[llength $boxes]"
    incr column32_flat_errors [llength $boxes]
}
puts "COLUMN32_FLAT_DRC_ERRORS=$column32_flat_errors"
if {$column32_flat_errors != 0} { error "column_32 flat DRC failed" }
save column_32_p2652_flat

quit -noprompt
