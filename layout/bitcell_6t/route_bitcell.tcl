# Route the frozen 6T bitcell scaffold produced by generate_import.tcl.
# The six SKY130 PCells remain unchanged; only parent-level interconnect,
# body taps, labels, and ports are added here.

load bitcell_6t_import
save bitcell_6t
snap internal

# Remove the five placeholder metal1 pin rectangles/labels created by
# magic::netlist_to_layout.  They are not electrically connected to devices.
box values -10 -1610 210 210
select do labels
select area metal1
delete
select clear
select no labels

proc m3_rail {y} {
    box values -450 [expr {$y - 30}] 2600 [expr {$y + 30}]
    paint metal3
}

proc terminal_to_m3 {tx ty vx track} {
    # Extend the PCell metal1 terminal to a via column.
    set xlo [expr {min($tx, $vx) - 20}]
    set xhi [expr {max($tx, $vx) + 20}]
    box values $xlo [expr {$ty - 20}] $xhi [expr {$ty + 20}]
    paint metal1

    # M1 -> M2.
    set vxlo [expr {$vx - 30}]
    set vxhi [expr {$vx + 30}]
    set tylo [expr {$ty - 30}]
    set tyhi [expr {$ty + 30}]
    box values $vxlo $tylo $vxhi $tyhi
    paint metal1
    paint metal2
    contact m2contact

    # Vertical M2 branch.
    set ylo [expr {min($ty, $track) - 30}]
    set yhi [expr {max($ty, $track) + 30}]
    box values [expr {$vx - 30}] $ylo [expr {$vx + 30}] $yhi
    paint metal2

    # M2 -> M3 at the net rail.
    set trlo [expr {$track - 30}]
    set trhi [expr {$track + 30}]
    box values $vxlo $trlo $vxhi $trhi
    paint metal2
    paint metal3
    contact m3contact
}

proc body_tap_to_m3 {well diff contact_type cx cy mx vx track} {
    # Diffusion/well tap -> local interconnect.
    set cxlo [expr {$cx - 70}]
    set cxhi [expr {$cx + 70}]
    set cylo [expr {$cy - 70}]
    set cyhi [expr {$cy + 70}]
    box values $cxlo $cylo $cxhi $cyhi
    paint $well
    paint $diff
    paint locali
    contact $contact_type

    # Move in LI to a dedicated LI/M1 contact so the substrate/well contact
    # and mcon do not occupy the same cut area.
    set lxlo [expr {min($cx, $mx) - 20}]
    set lxhi [expr {max($cx, $mx) + 20}]
    box values $lxlo [expr {$cy - 20}] $lxhi [expr {$cy + 20}]
    paint locali

    set mxlo [expr {$mx - 30}]
    set mxhi [expr {$mx + 30}]
    set mylo [expr {$cy - 30}]
    set myhi [expr {$cy + 30}]
    box values $mxlo $mylo $mxhi $myhi
    paint locali
    paint metal1
    contact mcon

    terminal_to_m3 $mx $cy $vx $track
}

# One horizontal M3 rail per logical net.  M2 is used only for vertical
# branches, which allows crossings without accidental shorts.
set VDD_Y -760
set Q_Y   -880
set QB_Y  -1000
set VSS_Y -2080
set WL_Y  -2200
set BL_Y  -2320
set BLB_Y -2440

foreach y [list $VDD_Y $Q_Y $QB_Y $VSS_Y $WL_Y $BL_Y $BLB_Y] {
    m3_rail $y
}

# Left inverter: PU_L / PD_L and left access transistor.
# PU_L: source=VDD, drain=Q, gate=QB
terminal_to_m3 114 -1392   60 $VDD_Y
terminal_to_m3 202 -1392  260 $Q_Y
terminal_to_m3 158 -1286  160 $QB_Y

# PD_L: source=VSS, drain=Q, gate=QB
terminal_to_m3 852 -1423  780 $VSS_Y
terminal_to_m3 940 -1423 1020 $Q_Y
terminal_to_m3 896 -1242  900 $QB_Y

# ACC_L: source=Q, drain=BL, gate=WL
terminal_to_m3 1590 -1595 1520 $Q_Y
terminal_to_m3 1678 -1595 1760 $BL_Y
terminal_to_m3 1634 -1480 1640 $WL_Y

# Right inverter: PU_R / PD_R and right access transistor.
# PU_R: source=VDD, drain=QB, gate=Q
terminal_to_m3 483 -1445  420 $VDD_Y
terminal_to_m3 571 -1445  650 $QB_Y
terminal_to_m3 527 -1339  530 $Q_Y

# PD_R: source=VSS, drain=QB, gate=Q
terminal_to_m3 1221 -1476 1150 $VSS_Y
terminal_to_m3 1309 -1476 1390 $QB_Y
terminal_to_m3 1265 -1295 1260 $Q_Y

# ACC_R: source=QB, drain=BLB, gate=WL
terminal_to_m3 1959 -1648 1880 $QB_Y
terminal_to_m3 2047 -1648 2130 $BLB_Y
terminal_to_m3 2003 -1533 2000 $WL_Y

# PMOS nwell is continuous across PU_L/PU_R; add one n+ well tap on its left.
body_tap_to_m3 nwell nsubdiff nsc -105 -1392 -280 -380 $VDD_Y

# NMOS pwell is continuous across PD_L/PD_R/ACC_L/ACC_R; add one p+ tap
# on its right and tie it to VSS.
body_tap_to_m3 pwell psubdiff psc 2240 -1540 2420 2520 $VSS_Y

# Ports live on M3 rails, away from device-level routing.
proc make_port {name index x y} {
    set xlo [expr {$x - 25}]
    set xhi [expr {$x + 25}]
    set ylo [expr {$y - 25}]
    set yhi [expr {$y + 25}]
    box values $xlo $ylo $xhi $yhi
    label $name center metal3
    select clear
    select do labels
    select area metal3
    port make $index n
    select clear
    select no labels
}

make_port VDD 0 -230 $VDD_Y
make_port BL  1 -230 $BL_Y
make_port BLB 2 -230 $BLB_Y
make_port VSS 3 -230 $VSS_Y
make_port WL  4 -230 $WL_Y

drc check
drc count total

save bitcell_6t
quit -noprompt
