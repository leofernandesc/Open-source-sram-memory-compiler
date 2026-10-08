load wl_driver_s1p68_s2p5p04_placed
save wl_driver_s1p68_s2p5p04_layout
snap internal

# Remove the placeholder import pins.
box values -10 -1300 210 210
select do labels
select area metal1
delete
select clear
select no labels

proc m3_rail {y} {
    box values -450 [expr {$y - 42}] 2600 [expr {$y + 42}]
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

set VDD_Y   -300
set WL_IN_Y -500
set WL_N_Y  -2000
set WL_Y    -2200
set VSS_Y   -3600

foreach y [list $VDD_Y $WL_IN_Y $WL_N_Y $WL_Y $VSS_Y] {
    m3_rail $y
}

# Stage 1, W=1.68um. Device centers: XMP1=(300,-1000), XMN1=(600,-3000).
# Metal1 diffusion centers stay at x=center +/-44. Gate/guard Y offsets come
# from the generated 1.68um SKY130 devices.
terminal_to_m3 256 -1000 168 $WL_N_Y 168
terminal_to_m3 300  -768 300 $WL_IN_Y
terminal_to_m3 344 -1000 432 $VDD_Y 168

terminal_to_m3 556 -3000 468 $WL_N_Y 168
terminal_to_m3 600 -2780 300 $WL_IN_Y
terminal_to_m3 644 -3000 732 $VSS_Y 168

# Stage 2, W=5.04um. Device centers: XMP2=(1500,-1000), XMN2=(1800,-3000).
terminal_to_m3 1456 -1000 1368 $WL_Y 504
terminal_to_m3 1500  -432 1500 $WL_N_Y
terminal_to_m3 1544 -1000 1632 $VDD_Y 504

terminal_to_m3 1756 -3000 1668 $WL_Y 504
terminal_to_m3 1800 -2441 1500 $WL_N_Y
terminal_to_m3 1844 -3000 1932 $VSS_Y 504

# Body ties: use the upper locali guard-ring segments of each generated device.
terminal_to_m3 300  -666  880 $VDD_Y
terminal_to_m3 1500 -330 2260 $VDD_Y 0 2360
terminal_to_m3 600  -2675 1040 $VSS_Y
terminal_to_m3 1800 -2339 2260 $VSS_Y

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
make_port VSS   1 -230 $VSS_Y
make_port WL_IN 2 -230 $WL_IN_Y
make_port WL    3 -230 $WL_Y

drc euclidean on
drc style drc(full)
drc on
select top cell
expand
box select
drc check
drc catchup
puts "WL_DRIVER_ROUTE_DRC_BEGIN"
drc count total
set route_drc_rules [drc listall why]
puts "WL_DRIVER_ROUTE_DRC_RULE_GROUPS=[llength $route_drc_rules]"
puts "WL_DRIVER_ROUTE_DRC_END"
if {[llength $route_drc_rules] > 0} {
    error "wl_driver_s1p68_s2p5p04 routing fails drc(full): $route_drc_rules"
}
save wl_driver_s1p68_s2p5p04_layout
quit -noprompt
