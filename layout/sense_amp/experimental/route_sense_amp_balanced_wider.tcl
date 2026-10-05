# Route the generated SKY130A sense-amplifier scaffold.
# PCells are kept unchanged; parent-level M1/M2/M3 connects the logical nets.

load sense_amp_placed
save sense_amp_balanced_wider
snap internal

# Remove the seven placeholder M1 pin rectangles/labels from the import.
box values -10 -2500 210 210
select do labels
select area metal1
delete
select clear
select no labels

proc m3_rail {y} {
    box values -450 [expr {$y - 30}] 3000 [expr {$y + 30}]
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
    # Start on an existing guard-ring LI contact and move to a dedicated
    # LI/M1 contact before entering the metal stack.
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

# Rails surround the two device rows.  Outputs and SCLK live between rows so
# upper and lower branches do not share long overlapping M2 corridors.
set VDD_Y    -300
set BL_Y     -500
set BLB_Y    -650
set SAOUT_Y  -1900
set SCLK_Y   -2350
set SAOUTB_Y -2800
set NTAIL_Y  -3400
set VSS_Y    -3600

foreach y [list $VDD_Y $SAOUT_Y $SAOUTB_Y $NTAIL_Y $VSS_Y $SCLK_Y $BL_Y $BLB_Y] {
    m3_rail $y
}

# MP1 at (300,-1000): D=SA_OUT, G=SA_OUTB, S=VDD.
terminal_to_m3 256 -1000  176 $SAOUT_Y
terminal_to_m3 300  -810  300 $SAOUTB_Y
terminal_to_m3 344 -1000  424 $VDD_Y

# MN1 at (600,-3000): D=SA_OUT, G=SA_OUTB, S=NTAIL.
terminal_to_m3 556 -3000  476 $SAOUT_Y
terminal_to_m3 600 -2880  600 $SAOUTB_Y
terminal_to_m3 644 -3000  724 $NTAIL_Y

# MP2 at (1100,-1000): D=SA_OUTB, G=SA_OUT, S=VDD.
terminal_to_m3 1056 -1000  976 $SAOUTB_Y
terminal_to_m3 1100  -810 1100 $SAOUT_Y
terminal_to_m3 1144 -1000 1224 $VDD_Y

# MN2 at (1500,-3000): D=SA_OUTB, G=SA_OUT, S=NTAIL.
terminal_to_m3 1456 -3000 1376 $SAOUTB_Y
terminal_to_m3 1500 -2880 1500 $SAOUT_Y
terminal_to_m3 1544 -3000 1624 $NTAIL_Y

# PMOS bitline samplers at y=-1000.
# XMSAMPBL at x=1900: D=BL, G=SCLK, S=SA_OUT.
terminal_to_m3 1856 -1000 1776 $BL_Y
terminal_to_m3 1900  -736 1900 $SCLK_Y
terminal_to_m3 1944 -1000 2024 $SAOUT_Y

# XMSAMPBLB at x=2700: D=SA_OUTB, G=SCLK, S=BLB.
terminal_to_m3 2656 -1000 2576 $SAOUTB_Y
terminal_to_m3 2700  -736 2700 $SCLK_Y
terminal_to_m3 2744 -1000 2824 $BLB_Y

# Tail NMOS at (2400,-3000): D=NTAIL, G=SCLK, S=VSS.
terminal_to_m3 2356 -3000 2276 $NTAIL_Y
terminal_to_m3 2400 -2880 2400 $SCLK_Y
terminal_to_m3 2444 -3000 2524 $VSS_Y

# Tie each isolated PCell guard ring to its intended body rail.  With the two
# rows separated these LI leads no longer cross opposite-type guard rings.
# PMOS nwell guard-ring top contacts -> VDD.
guard_li_to_m3 300  -708  560  600 $VDD_Y
guard_li_to_m3 1100 -708 1360 1400 $VDD_Y
guard_li_to_m3 1900 -634 2160 2200 $VDD_Y
guard_li_to_m3 2700 -634 2910 2950 $VDD_Y

# NMOS pwell/substrate guard-ring top contacts -> VSS.
guard_li_to_m3 600  -2778  810  850 $VSS_Y
guard_li_to_m3 1500 -2778 1710 1750 $VSS_Y
guard_li_to_m3 2400 -2778 2630 2670 $VSS_Y

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

make_port VDD     0 -230 $VDD_Y
make_port VSS     1 -230 $VSS_Y
make_port BL      2 -230 $BL_Y
make_port BLB     3 -230 $BLB_Y
make_port SCLK    4 -230 $SCLK_Y
make_port SA_OUT  5 -230 $SAOUT_Y
make_port SA_OUTB 6 -230 $SAOUTB_Y

drc check
drc count total
save sense_amp_balanced_wider
quit -noprompt
