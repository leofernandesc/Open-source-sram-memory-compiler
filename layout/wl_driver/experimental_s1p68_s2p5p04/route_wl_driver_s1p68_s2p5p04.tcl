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
terminal_to_m3 256 -1000 176 $WL_N_Y
terminal_to_m3 300  -768 300 $WL_IN_Y
terminal_to_m3 344 -1000 424 $VDD_Y

terminal_to_m3 556 -3000 476 $WL_N_Y
terminal_to_m3 600 -2780 600 $WL_IN_Y
terminal_to_m3 644 -3000 724 $VSS_Y

# Stage 2, W=5.04um. Device centers: XMP2=(1500,-1000), XMN2=(1800,-3000).
terminal_to_m3 1456 -1000 1376 $WL_Y
terminal_to_m3 1500  -432 1500 $WL_N_Y
terminal_to_m3 1544 -1000 1624 $VDD_Y

terminal_to_m3 1756 -3000 1676 $WL_Y
terminal_to_m3 1800 -2441 1800 $WL_N_Y
terminal_to_m3 1844 -3000 1924 $VSS_Y

# Body ties: use the upper locali guard-ring segments of each generated device.
guard_li_to_m3 300  -666  820  880 $VDD_Y
guard_li_to_m3 1500 -330 2200 2260 $VDD_Y
guard_li_to_m3 600  -2675 980 1040 $VSS_Y
guard_li_to_m3 1800 -2339 2200 2260 $VSS_Y

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

drc check
drc count total
save wl_driver_s1p68_s2p5p04_layout
quit -noprompt
