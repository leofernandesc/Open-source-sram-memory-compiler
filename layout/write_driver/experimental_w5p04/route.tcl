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
    box values -450 [expr {$y - 42}] 4500 [expr {$y + 42}]
    paint metal3
}

proc terminal_to_m3 {tx ty vx track {sd_half_y 0} {via3_x ""}} {
    if {$via3_x eq ""} { set via3_x $vx }
    if {$sd_half_y > 0} {
        box values [expr {$tx - 23}] [expr {$ty - $sd_half_y}] \
                   [expr {$tx + 23}] [expr {$ty + $sd_half_y}]
        paint metal1
    }

    set xlo [expr {min($tx, $vx) - 20}]
    set xhi [expr {max($tx, $vx) + 20}]
    box values $xlo [expr {$ty - 18}] $xhi [expr {$ty + 18}]
    paint metal1

    box values [expr {$vx - 36}] [expr {$ty - 36}] \
               [expr {$vx + 36}] [expr {$ty + 36}]
    paint metal1
    paint metal2
    box values [expr {$vx - 26}] [expr {$ty - 26}] \
               [expr {$vx + 26}] [expr {$ty + 26}]
    contact m2contact

    set ylo [expr {min($ty, $track) - 42}]
    set yhi [expr {max($ty, $track) + 42}]
    box values [expr {$vx - 42}] $ylo [expr {$vx + 42}] $yhi
    paint metal2

    box values [expr {min($vx, $via3_x) - 42}] [expr {$track - 42}] \
               [expr {max($vx, $via3_x) + 42}] [expr {$track + 42}]
    paint metal2
    box values [expr {$via3_x - 42}] [expr {$track - 42}] \
               [expr {$via3_x + 42}] [expr {$track + 42}]
    paint metal3
    box values [expr {$via3_x - 30}] [expr {$track - 30}] \
               [expr {$via3_x + 30}] [expr {$track + 30}]
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
terminal_to_m3 256 -1000 168 $WEB_Y 84
terminal_to_m3 300  -852 300 $WE_Y
terminal_to_m3 344 -1000 432 $VDD_Y 84
# XMNWEB at (600,-5000): D=WE_B, G=WE, S=VSS.
terminal_to_m3 556 -5000 468 $WEB_Y 84
terminal_to_m3 600 -4861 800 $WE_Y
terminal_to_m3 644 -5000 732 $VSS_Y 84

# BL PMOS stack.
# XMPENBL at (1100,-1000): D=net1, G=WE_B, S=VDD.
terminal_to_m3 1056 -1000  968 $NET1_Y 504
terminal_to_m3 1100  -432 1100 $WEB_Y
terminal_to_m3 1144 -1000 1232 $VDD_Y 504
# XMPDBL at (1900,-1000): D=BL, G=DATA_B, S=net1.
terminal_to_m3 1856 -1000 1768 $BL_Y 504
terminal_to_m3 1900  -432 1900 $DATAB_Y
terminal_to_m3 1944 -1000 2032 $NET1_Y 504

# BL NMOS stack.
# XMNDBL at (1400,-5000): D=BL, G=DATA_B, S=net2.
terminal_to_m3 1356 -5000 1268 $BL_Y 504
terminal_to_m3 1400 -4441 1100 $DATAB_Y
terminal_to_m3 1444 -5000 1532 $NET2_Y 504
# XMNENBL at (2200,-5000): D=net2, G=WE, S=VSS.
terminal_to_m3 2156 -5000 2068 $NET2_Y 504
terminal_to_m3 2200 -4441 1650 $WE_Y
terminal_to_m3 2244 -5000 2332 $VSS_Y 504

# BLB PMOS stack.
# XMPENBLB at (2700,-1000): D=net3, G=WE_B, S=VDD.
terminal_to_m3 2656 -1000 2568 $NET3_Y 504
terminal_to_m3 2700  -432 2700 $WEB_Y
terminal_to_m3 2744 -1000 2832 $VDD_Y 504
# XMPDBLB at (3500,-1000): D=BLB, G=DATA, S=net3.
terminal_to_m3 3456 -1000 3368 $BLB_Y 504
terminal_to_m3 3500  -432 3500 $DATA_Y
terminal_to_m3 3544 -1000 3632 $NET3_Y 504

# BLB NMOS stack.
# XMNDBLB at (3000,-5000): D=BLB, G=DATA, S=net4.
terminal_to_m3 2956 -5000 2868 $BLB_Y 504
terminal_to_m3 3000 -4441 2350 $DATA_Y
terminal_to_m3 3044 -5000 3132 $NET4_Y 504
# XMNENBLB at (3800,-5000): D=net4, G=WE, S=VSS.
terminal_to_m3 3756 -5000 3668 $NET4_Y 504
terminal_to_m3 3800 -4441 4050 $WE_Y
terminal_to_m3 3844 -5000 3932 $VSS_Y 504

# PMOS nwell body ties -> VDD.
terminal_to_m3 300  -750  560 $VDD_Y
terminal_to_m3 1100 -330 1360 $VDD_Y 0 1460
terminal_to_m3 1900 -330 2160 $VDD_Y 0 2260
terminal_to_m3 2700 -330 2960 $VDD_Y 0 3060
terminal_to_m3 3500 -330 3760 $VDD_Y 0 3860

# NMOS substrate body ties -> VSS.
terminal_to_m3 600  -4759 1050 $VSS_Y
terminal_to_m3 1400 -4339 1800 $VSS_Y
terminal_to_m3 2200 -4339 2500 $VSS_Y
terminal_to_m3 3000 -4339 3260 $VSS_Y
terminal_to_m3 3800 -4339 4200 $VSS_Y

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

drc euclidean on
drc style drc(full)
drc on
select top cell
expand
box select
drc check
drc catchup
puts "WRITE_W5P04_ROUTE_DRC_BEGIN"
drc count total
set route_drc_rules [drc listall why]
puts "WRITE_W5P04_ROUTE_DRC_RULE_GROUPS=[llength $route_drc_rules]"
puts "WRITE_W5P04_ROUTE_DRC_END"
if {[llength $route_drc_rules] > 0} {
    error "write_driver_w5p04 routing fails drc(full): $route_drc_rules"
}
save write_driver_w5p04
quit -noprompt
