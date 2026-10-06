# Build a physical 32-row SRAM bitline column from the frozen 6T bitcell.
# The bitcells are stacked vertically at zero gap.  BL/BLB, VDD, VSS and the
# deselected wordlines are collected on dedicated metal4 trunks through via3.

path search +../bitcell_6t

load column_32_p1800
snap internal

set llx -450
set lly -2470
# The routed-cell bbox is 1740 units tall.  A 60-unit vertical channel keeps
# the top VDD M3 rail of one row from touching the bottom BLB M3 rail of the
# next row while preserving a compact physical column.
set pitch_y 1800
set rows 32

# Parent coordinates of the child M3 rails after aligning the routed-cell bbox
# lower-left corner to (0, row*pitch_y).
set x_bl    220
set x_blb   520
set x_vss   820
set x_vdd  1120
set x_wl   1420

set y_bl_offset   150
set y_blb_offset   30
set y_vss_offset  390
set y_vdd_offset 1710
set y_wl_offset   270

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
    # Keep enough enclosure around via3 on both residues.
    box values [expr {$x - 40}] [expr {$y - 40}] [expr {$x + 40}] [expr {$y + 40}]
    paint metal3
    paint metal4
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

drc check
puts "COLUMN32_HIER_DRC_BEGIN"
drc count total
puts "COLUMN32_HIER_DRC_END"

save column_32_p1800
flatten column_32_p1800_flat
load column_32_p1800_flat
drc check
puts "COLUMN32_FLAT_DRC_BEGIN"
drc count total
puts "COLUMN32_FLAT_DRC_END"
save column_32_p1800_flat

quit -noprompt
