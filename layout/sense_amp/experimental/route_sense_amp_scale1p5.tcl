load sense_amp_scale1p5_placed
save sense_amp_scale1p5
snap internal

box values -10 -2500 210 210
select do labels
select area metal1
delete
select clear
select no labels

proc m3_rail {y} {
    box values -450 [expr {$y - 42}] 3000 [expr {$y + 42}]
    paint metal3
}

proc terminal_to_m3 {tx ty vx track {sd_half_y 0} {via_y ""}} {
    if {$via_y eq ""} { set via_y $ty }
    if {$sd_half_y > 0} {
        box values [expr {$tx - 23}] [expr {$ty - $sd_half_y}] \
                   [expr {$tx + 23}] [expr {$ty + $sd_half_y}]
        paint metal1
    }

    set xlo [expr {min($tx, $vx) - 20}]
    set xhi [expr {max($tx, $vx) + 20}]
    box values $xlo [expr {$ty - 18}] $xhi [expr {$ty + 18}]
    paint metal1
    if {$via_y != $ty} {
        box values [expr {$tx - 20}] [expr {min($ty, $via_y) - 18}] \
                   [expr {$tx + 20}] [expr {max($ty, $via_y) + 18}]
        paint metal1
    }

    box values [expr {$vx - 36}] [expr {$via_y - 36}] \
               [expr {$vx + 36}] [expr {$via_y + 36}]
    paint metal1
    paint metal2
    box values [expr {$vx - 26}] [expr {$via_y - 26}] \
               [expr {$vx + 26}] [expr {$via_y + 26}]
    contact m2contact

    set ylo [expr {min($via_y, $track) - 42}]
    set yhi [expr {max($via_y, $track) + 42}]
    box values [expr {$vx - 42}] $ylo [expr {$vx + 42}] $yhi
    paint metal2

    box values [expr {$vx - 42}] [expr {$track - 42}] \
               [expr {$vx + 42}] [expr {$track + 42}]
    paint metal2
    paint metal3
    box values [expr {$vx - 30}] [expr {$track - 30}] \
               [expr {$vx + 30}] [expr {$track + 30}]
    contact m3contact
}

set VDD_Y    -300
set BL_Y     -500
set BLB_Y    -650
set SAOUT_Y  -2005
set SCLK_Y   -2350
set SAOUTB_Y -2900
set NTAIL_Y  -3400
set VSS_Y    -3600

foreach y [list $VDD_Y $NTAIL_Y $VSS_Y $SCLK_Y $BL_Y $BLB_Y] { m3_rail $y }
box values 145 [expr {$SAOUT_Y - 42}] 2055 [expr {$SAOUT_Y + 42}]
paint metal3
box values 270 [expr {$SAOUTB_Y - 42}] 2607 [expr {$SAOUTB_Y + 42}]
paint metal3

terminal_to_m3 256 -1000 168 $SAOUT_Y 189
terminal_to_m3 300 -747 300 $SAOUTB_Y
terminal_to_m3 344 -1000 432 $VDD_Y 189
terminal_to_m3 556 -3000 468 $SAOUT_Y 98
terminal_to_m3 600 -3153 600 $SAOUTB_Y 0 -3280
terminal_to_m3 644 -3000 732 $NTAIL_Y 98
terminal_to_m3 1056 -1000 968 $SAOUTB_Y 189
terminal_to_m3 1100 -747 1100 $SAOUT_Y
terminal_to_m3 1144 -1000 1232 $VDD_Y 189
terminal_to_m3 1456 -3000 1368 $SAOUTB_Y 98
terminal_to_m3 1500 -2847 1250 $SAOUT_Y
terminal_to_m3 1544 -3000 1632 $NTAIL_Y 98
terminal_to_m3 1856 -1000 1768 $BL_Y 200
terminal_to_m3 1900 -736 1900 $SCLK_Y
terminal_to_m3 1944 -1000 2032 $SAOUT_Y 200
terminal_to_m3 2656 -1000 2568 $SAOUTB_Y 200
terminal_to_m3 2700 -736 2700 $SCLK_Y
terminal_to_m3 2744 -1000 2832 $BLB_Y 200
terminal_to_m3 2356 -3000 2268 $NTAIL_Y 98
terminal_to_m3 2400 -2847 2150 $SCLK_Y
terminal_to_m3 2444 -3000 2456 $VSS_Y 98

terminal_to_m3 300 -645 600 $VDD_Y
terminal_to_m3 1100 -645 1400 $VDD_Y
terminal_to_m3 1900 -634 2200 $VDD_Y
terminal_to_m3 2700 -634 2950 $VDD_Y
terminal_to_m3 600 -2745 850 $VSS_Y
terminal_to_m3 1500 -2745 1750 $VSS_Y
terminal_to_m3 2400 -2745 2800 $VSS_Y

proc make_port {name index x y} {
    box values [expr {$x - 25}] [expr {$y - 25}] [expr {$x + 25}] [expr {$y + 25}]
    label $name center metal3
    select clear
    select do labels
    select area metal3
    port make $index n
    select clear
    select no labels
}

make_port VDD 0 -230 $VDD_Y
make_port VSS 1 -230 $VSS_Y
make_port BL 2 -230 $BL_Y
make_port BLB 3 -230 $BLB_Y
make_port SCLK 4 -230 $SCLK_Y
make_port SA_OUT 5 170 $SAOUT_Y
make_port SA_OUTB 6 295 $SAOUTB_Y

drc euclidean on
drc style drc(full)
drc on
select top cell
expand
box select
drc check
drc catchup
puts "SCALE1P5_ROUTE_DRC_BEGIN"
drc count total
set route_drc_rules [drc listall why]
puts "SCALE1P5_ROUTE_DRC_RULE_GROUPS=[llength $route_drc_rules]"
puts "SCALE1P5_ROUTE_DRC_END"
if {[llength $route_drc_rules] > 0} {
    error "sense_amp_scale1p5 routing fails drc(full): $route_drc_rules"
}
save sense_amp_scale1p5
quit -noprompt
