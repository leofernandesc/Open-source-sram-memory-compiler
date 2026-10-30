# Build a representative physical 32-row SRAM column including the three
# bitline-connected peripheral leaves: precharge, write driver and sense amp.
# The already-validated 32-row bitcell core is reused and the bitline/power
# trunks are extended in metal4 through all peripherals.

path search +../column_32
path search +../precharge
path search +../write_driver
path search +../sense_amp

load column_32_full_v2
snap internal

# Align every child by its bbox lower-left corner.  The bitcell core occupies
# y=0..57760.  Peripheral blocks are stacked below it with routing channels.
getcell column_32_p1800_flat child 0 -80 parent 0 0
getcell precharge_flat          child -450 -2120 parent 0 -2500
getcell sense_amp_flat          child -450 -3630 parent 0 -6800
getcell write_driver_flat       child -450 -5730 parent 0 -13500

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
    box values [expr {$x - 40}] [expr {$y - 40}] [expr {$x + 40}] [expr {$y + 40}]
    paint metal3
    paint metal4
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
    m4_trunk $x -13580 57760
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
make_m4_port WLOFF 4 $X_WL 57720

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
make_m4_port BL  0 $X_BL  57720
make_m4_port BLB 1 $X_BLB 57720
make_m4_port VSS 2 $X_VSS 57720
make_m4_port VDD 3 $X_VDD 57720

drc check
puts "COLUMN32_FULL_HIER_DRC_BEGIN"
drc count total
puts "COLUMN32_FULL_HIER_DRC_END"

save column_32_full_v2
flatten column_32_full_v2_flat
load column_32_full_v2_flat
drc check
puts "COLUMN32_FULL_FLAT_DRC_BEGIN"
drc count total
puts "COLUMN32_FULL_FLAT_DRC_END"
save column_32_full_v2_flat

quit -noprompt
