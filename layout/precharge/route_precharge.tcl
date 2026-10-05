# Parent-level route for the three-PMOS precharge/equalization leaf.
load precharge_placed
save precharge_layout
snap internal

# Remove the five placeholder import pins.
box values -10 -1700 210 210
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
    set xlo [expr {min($tx, $vx) - 20}]
    set xhi [expr {max($tx, $vx) + 20}]
    box values $xlo [expr {$ty - 20}] $xhi [expr {$ty + 20}]
    paint metal1

    set vxlo [expr {$vx - 30}]
    set vxhi [expr {$vx + 30}]
    set tylo [expr {$ty - 30}]
    set tyhi [expr {$ty + 30}]
    box values $vxlo $tylo $vxhi $tyhi
    paint metal1
    paint metal2
    contact m2contact

    set ylo [expr {min($ty, $track) - 30}]
    set yhi [expr {max($ty, $track) + 30}]
    box values $vxlo $ylo $vxhi $yhi
    paint metal2

    set trlo [expr {$track - 30}]
    set trhi [expr {$track + 30}]
    box values $vxlo $trlo $vxhi $trhi
    paint metal2
    paint metal3
    contact m3contact
}

proc guard_li_to_m3 {gx gy mx vx track} {
    set lxlo [expr {min($gx, $mx) - 20}]
    set lxhi [expr {max($gx, $mx) + 20}]
    box values $lxlo [expr {$gy - 20}] $lxhi [expr {$gy + 20}]
    paint locali

    set mxlo [expr {$mx - 30}]
    set mxhi [expr {$mx + 30}]
    set mylo [expr {$gy - 30}]
    set myhi [expr {$gy + 30}]
    box values $mxlo $mylo $mxhi $myhi
    paint locali
    paint metal1
    contact mcon

    terminal_to_m3 $mx $gy $vx $track
}

set VDD_Y   -300
set PRECH_Y -500
set BL_Y    -1500
set BLB_Y   -1650
set VSS_Y   -1850

foreach y [list $VDD_Y $PRECH_Y $BL_Y $BLB_Y $VSS_Y] {
    m3_rail $y
}

# XMPBL at (300,-1000): D=BL, G=PRECH, S=VDD.
terminal_to_m3 256 -1000  176 $BL_Y
terminal_to_m3 300  -894  300 $PRECH_Y
terminal_to_m3 344 -1000  424 $VDD_Y

# XMPBLB at (1100,-1000): D=BLB, G=PRECH, S=VDD.
terminal_to_m3 1056 -1000  976 $BLB_Y
terminal_to_m3 1100  -894 1100 $PRECH_Y
terminal_to_m3 1144 -1000 1224 $VDD_Y

# XMEQ at (1900,-1000): D=BL, G=PRECH, S=BLB.
terminal_to_m3 1856 -1000 1776 $BL_Y
terminal_to_m3 1900  -894 1900 $PRECH_Y
terminal_to_m3 1944 -1000 2024 $BLB_Y

# PMOS nwell guard-ring top contacts -> VDD.
guard_li_to_m3 300  -792  560  620 $VDD_Y
guard_li_to_m3 1100 -792 1360 1420 $VDD_Y
guard_li_to_m3 1900 -792 2160 2220 $VDD_Y

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

make_port VDD   0 -230 $VDD_Y
make_port BL    1 -230 $BL_Y
make_port BLB   2 -230 $BLB_Y
make_port PRECH 3 -230 $PRECH_Y
make_port VSS   4 -230 $VSS_Y

drc check
drc count total
save precharge_layout
quit -noprompt
