# Build a representative physical 32-row SRAM column including the three
# bitline-connected peripheral leaves: precharge, write driver and sense amp.
# The already-validated 32-row bitcell core is reused and the bitline/power
# trunks are extended in metal4 through all peripherals.

path search +../column_32
path search +../precharge/experimental_w2p52
path search +../write_driver/experimental_w5p04
path search +../sense_amp/experimental

load column_32_full_g7_wpre2p52
box values -100000 -100000 100000 100000
select area
delete
select clear
snap internal

# Align every child by its bbox lower-left corner.  The repaired 32-row core
# uses pitch 2652 and occupies y=0..85024 after the -80 lower trunk is shifted
# to the parent origin.  Peripheral blocks stay below y=0.
getcell column_32_p2652_flat child 0 -80 parent 0 0
getcell precharge_w2p52_flat          child -450 -2120 parent 0 -2500
getcell sense_amp_scale1p5_flat          child -450 -3630 parent 0 -6800
getcell write_driver_w5p04_flat       child -450 -5730 parent 0 -13500

# Shared metal4 trunks.  x coordinates match the 32-row core.
set X_BL   220
set X_BLB  520
set X_VSS  820
set X_VDD 1120
set X_WL  1420

proc m4_trunk {x ylo yhi} {
    box values [expr {$x - 40}] $ylo [expr {$x + 40}] $yhi
    paint metal4
}

proc m3_to_m4 {x y} {
    box values [expr {$x - 48}] [expr {$y - 48}] [expr {$x + 48}] [expr {$y + 48}]
    paint metal3
    # Unconnected control stubs need at least 9600 units of metal4 area.
    box values [expr {$x - 60}] [expr {$y - 48}] [expr {$x + 60}] [expr {$y + 48}]
    paint metal4
    box values [expr {$x - 32}] [expr {$y - 32}] [expr {$x + 32}] [expr {$y + 32}]
    contact via3
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

# Extend the bitcell-core trunks down across the peripheral stack.
foreach x [list $X_BL $X_BLB $X_VSS $X_VDD] {
    m4_trunk $x -13580 85024
}

# Precharge placement shift: (+450, -380).
m3_to_m4 $X_BL  -1880
m3_to_m4 $X_BLB -2030
m3_to_m4 $X_VDD  -680
m3_to_m4 $X_VSS -2230

# Sense placement shift: (+450, -3170).
m3_to_m4 $X_BL  -3670
m3_to_m4 $X_BLB -3820
m3_to_m4 $X_VDD -3470
m3_to_m4 $X_VSS -6770

# Write-driver placement shift: (+450, -7770).
m3_to_m4 $X_BL  -10070
m3_to_m4 $X_BLB -10220
m3_to_m4 $X_VDD  -8070
m3_to_m4 $X_VSS -13470

# Promote the bitcell-core deselected wordline trunk to a top-level pin.
make_m4_port WLOFF 4 $X_WL 84984

# Peripheral controls are promoted through short local M4 stubs.
# Precharge PRECH: original y=-500 -> parent y=-880.
m3_to_m4 1700 -880
make_m4_port PRECH 5 1700 -880

# Sense SCLK: original y=-2350 -> parent y=-5520.
m3_to_m4 1700 -5520
make_m4_port SCLK 6 1700 -5520

# Write driver controls after shift -7770.
# WE=-1700, DATA_B=-2000, DATA=-2150.
m3_to_m4 1700 -9470
make_m4_port WE 7 1700 -9470
m3_to_m4 1950 -9770
make_m4_port DATA_B 8 1950 -9770
m3_to_m4 2200 -9920
make_m4_port DATA 9 2200 -9920

# External bitline/power ports at the top of their trunks.
make_m4_port BL  0 $X_BL  84984
make_m4_port BLB 1 $X_BLB 84984
make_m4_port VSS 2 $X_VSS 84984
make_m4_port VDD 3 $X_VDD 84984

drc euclidean on
drc style drc(full)
drc on
select top cell
expand
box select
drc check
drc catchup
set column32_g7_hier_errors 0
foreach {rule boxes} [drc listall why] {
    puts "COLUMN32_G7_HIER_DRC_RULE=$rule BOXES=[llength $boxes]"
    if {[llength $boxes] > 0} { puts "COLUMN32_G7_HIER_DRC_SAMPLES=[lrange $boxes 0 9]" }
    incr column32_g7_hier_errors [llength $boxes]
}
puts "COLUMN32_G7_HIER_DRC_ERRORS=$column32_g7_hier_errors"
if {$column32_g7_hier_errors != 0} { error "G7 hierarchical DRC failed" }

save column_32_full_g7_wpre2p52
flatten column_32_full_g7_wpre2p52_flat
load column_32_full_g7_wpre2p52_flat
select top cell
expand
box select
drc check
drc catchup
set column32_g7_flat_errors 0
foreach {rule boxes} [drc listall why] {
    puts "COLUMN32_G7_FLAT_DRC_RULE=$rule BOXES=[llength $boxes]"
    incr column32_g7_flat_errors [llength $boxes]
}
puts "COLUMN32_G7_FLAT_DRC_ERRORS=$column32_g7_flat_errors"
if {$column32_g7_flat_errors != 0} { error "G7 flat DRC failed" }
save column_32_full_g7_wpre2p52_flat

quit -noprompt
