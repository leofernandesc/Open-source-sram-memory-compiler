load write_driver_w5p04_placed
save write_driver_w5p04
snap internal

# Remove the seven placeholder import pins.
box values -10 -2500 210 210
select do labels
select area metal1
delete
select clear
select no labels

proc m3_rail {y} {
    box values -450 [expr {$y - 30}] 4500 [expr {$y + 30}]
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

set VDD_Y    -300
set WE_Y    -1700
set WEB_Y   -1850
set DATAB_Y -2000
set DATA_Y  -2150
set BL_Y    -2300
set BLB_Y   -2450
set NET1_Y  -2600
set NET2_Y  -2750
set NET3_Y  -2900
set NET4_Y  -3050
set VSS_Y   -5700

foreach y [list $VDD_Y $WE_Y $WEB_Y $DATAB_Y $DATA_Y $BL_Y $BLB_Y $NET1_Y $NET2_Y $NET3_Y $NET4_Y $VSS_Y] {
    m3_rail $y
}

# WE inverter.
# XMPWEB at (300,-1000): D=WE_B, G=WE, S=VDD.
terminal_to_m3 256 -1000 176 $WEB_Y
terminal_to_m3 300  -852 300 $WE_Y
terminal_to_m3 344 -1000 424 $VDD_Y
# XMNWEB at (600,-5000): D=WE_B, G=WE, S=VSS.
terminal_to_m3 556 -5000 476 $WEB_Y
terminal_to_m3 600 -4861 600 $WE_Y
terminal_to_m3 644 -5000 724 $VSS_Y

# BL PMOS stack.
# XMPENBL at (1100,-1000): D=net1, G=WE_B, S=VDD.
terminal_to_m3 1056 -1000  976 $NET1_Y
terminal_to_m3 1100  -432 1100 $WEB_Y
terminal_to_m3 1144 -1000 1224 $VDD_Y
# XMPDBL at (1900,-1000): D=BL, G=DATA_B, S=net1.
terminal_to_m3 1856 -1000 1776 $BL_Y
terminal_to_m3 1900  -432 1900 $DATAB_Y
terminal_to_m3 1944 -1000 2024 $NET1_Y

# BL NMOS stack.
# XMNDBL at (1400,-5000): D=BL, G=DATA_B, S=net2.
terminal_to_m3 1356 -5000 1276 $BL_Y
terminal_to_m3 1400 -4441 1400 $DATAB_Y
terminal_to_m3 1444 -5000 1524 $NET2_Y
# XMNENBL at (2200,-5000): D=net2, G=WE, S=VSS.
terminal_to_m3 2156 -5000 2076 $NET2_Y
terminal_to_m3 2200 -4441 2200 $WE_Y
terminal_to_m3 2244 -5000 2324 $VSS_Y

# BLB PMOS stack.
# XMPENBLB at (2700,-1000): D=net3, G=WE_B, S=VDD.
terminal_to_m3 2656 -1000 2576 $NET3_Y
terminal_to_m3 2700  -432 2700 $WEB_Y
terminal_to_m3 2744 -1000 2824 $VDD_Y
# XMPDBLB at (3500,-1000): D=BLB, G=DATA, S=net3.
terminal_to_m3 3456 -1000 3376 $BLB_Y
terminal_to_m3 3500  -432 3500 $DATA_Y
terminal_to_m3 3544 -1000 3624 $NET3_Y

# BLB NMOS stack.
# XMNDBLB at (3000,-5000): D=BLB, G=DATA, S=net4.
terminal_to_m3 2956 -5000 2876 $BLB_Y
terminal_to_m3 3000 -4441 3000 $DATA_Y
terminal_to_m3 3044 -5000 3124 $NET4_Y
# XMNENBLB at (3800,-5000): D=net4, G=WE, S=VSS.
terminal_to_m3 3756 -5000 3676 $NET4_Y
terminal_to_m3 3800 -4441 3800 $WE_Y
terminal_to_m3 3844 -5000 3924 $VSS_Y

# PMOS nwell body ties -> VDD.
guard_li_to_m3 300  -750  520  560 $VDD_Y
guard_li_to_m3 1100 -330 1320 1360 $VDD_Y
guard_li_to_m3 1900 -330 2120 2160 $VDD_Y
guard_li_to_m3 2700 -330 2920 2960 $VDD_Y
guard_li_to_m3 3500 -330 3720 3760 $VDD_Y

# NMOS substrate body ties -> VSS.
guard_li_to_m3 600  -4759  820  860 $VSS_Y
guard_li_to_m3 1400 -4339 1620 1660 $VSS_Y
guard_li_to_m3 2200 -4339 2420 2460 $VSS_Y
guard_li_to_m3 3000 -4339 3220 3260 $VSS_Y
guard_li_to_m3 3800 -4339 4020 4060 $VSS_Y

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

make_port DATA   0 -230 $DATA_Y
make_port DATA_B 1 -230 $DATAB_Y
make_port WE     2 -230 $WE_Y
make_port BL     3 -230 $BL_Y
make_port BLB    4 -230 $BLB_Y
make_port VDD    5 -230 $VDD_Y
make_port VSS    6 -230 $VSS_Y

drc check
puts "WRITE_W5P04_ROUTE_DRC_BEGIN"
drc count total
puts "WRITE_W5P04_ROUTE_DRC_END"
save write_driver_w5p04
quit -noprompt
