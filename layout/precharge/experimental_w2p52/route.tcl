# Parent-level route for the three-PMOS precharge/equalization leaf.
load precharge_w2p52_placed
save precharge_w2p52
snap internal

# Remove the five placeholder import pins.
box values -10 -1700 210 210
select do labels
select area metal1
delete
select clear
select no labels

proc m3_rail {y} {
    box values -450 [expr {$y - 42}] 2600 [expr {$y + 42}]
    paint metal3
}

proc terminal_to_m3 {tx ty vx track {sd_half_y 0}} {
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

    box values [expr {$vx - 42}] [expr {$track - 42}] \
               [expr {$vx + 42}] [expr {$track + 42}]
    paint metal3
    box values [expr {$vx - 30}] [expr {$track - 30}] \
               [expr {$vx + 30}] [expr {$track + 30}]
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

proc body_tap_to_m3 {well diff contact_type cx cy mx vx track} {
    set cxlo [expr {$cx - 100}]
    set cxhi [expr {$cx + 100}]
    set cylo [expr {$cy - 100}]
    set cyhi [expr {$cy + 100}]
    box values $cxlo $cylo $cxhi $cyhi
    paint $well
    paint $diff
    paint locali
    box values [expr {$cx - 40}] [expr {$cy - 40}] \
               [expr {$cx + 40}] [expr {$cy + 40}]
    contact $contact_type

    set lxlo [expr {min($cx, $mx) - 20}]
    set lxhi [expr {max($cx, $mx) + 20}]
    box values $lxlo [expr {$cy - 42}] $lxhi [expr {$cy + 42}]
    paint locali

    set mxlo [expr {$mx - 42}]
    set mxhi [expr {$mx + 42}]
    set mylo [expr {$cy - 42}]
    set myhi [expr {$cy + 42}]
    box values $mxlo $mylo $mxhi $myhi
    paint locali
    paint metal1
    box values [expr {$mx - 26}] [expr {$cy - 26}] \
               [expr {$mx + 26}] [expr {$cy + 26}]
    contact mcon

    terminal_to_m3 $mx $cy $vx $track
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
terminal_to_m3 256 -1000  168 $BL_Y 252
terminal_to_m3 300  -684  300 $PRECH_Y
terminal_to_m3 344 -1000  432 $VDD_Y 252

# XMPBLB at (1100,-1000): D=BLB, G=PRECH, S=VDD.
terminal_to_m3 1056 -1000  968 $BLB_Y 252
terminal_to_m3 1100  -684 1100 $PRECH_Y
terminal_to_m3 1144 -1000 1232 $VDD_Y 252

# XMEQ at (1900,-1000): D=BL, G=PRECH, S=BLB.
terminal_to_m3 1856 -1000 1768 $BL_Y 252
terminal_to_m3 1900  -684 1900 $PRECH_Y
terminal_to_m3 1944 -1000 2032 $BLB_Y 252

# PMOS nwell guard-ring top contacts -> VDD.
terminal_to_m3 300  -583  620 $VDD_Y
terminal_to_m3 1100 -583 1420 $VDD_Y
terminal_to_m3 1900 -583 2220 $VDD_Y

# Tie the physical p-substrate to the exported VSS rail.  Without this tap,
# Magic extracts a floating VSUBS node in the RC netlist.
body_tap_to_m3 pwell psubdiff psc 2450 -2050 2280 2220 $VSS_Y

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

drc euclidean on
drc style drc(full)
drc on
select top cell
expand
box select
drc check
drc catchup
puts "PRECH_W2P52_ROUTE_DRC_BEGIN"
drc count total
set route_drc_rules [drc listall why]
puts "PRECH_W2P52_ROUTE_DRC_RULE_GROUPS=[llength $route_drc_rules]"
puts "PRECH_W2P52_ROUTE_DRC_END"
if {[llength $route_drc_rules] > 0} {
    error "precharge_w2p52 routing fails drc(full): $route_drc_rules"
}
save precharge_w2p52
quit -noprompt
