load row_decoder_import
save row_decoder_placed
snap internal

proc move_inst_to {name dx dy} {
    select clear
    select cell $name
    if {$dx > 0} { move e $dx }
    if {$dx < 0} { move w [expr {-$dx}] }
    if {$dy > 0} { move n $dy }
    if {$dy < 0} { move s [expr {-$dy}] }
    select clear
}

move_inst_to XM1 1607 13035
move_inst_to XM2 1238 8297
move_inst_to XM3 4269 13141
move_inst_to XM4 3900 8403
move_inst_to XM5 6931 13206
move_inst_to XM6 6562 8393
move_inst_to XM7 7893 8446
move_inst_to XM8 16024 8549
move_inst_to XM9 8855 13243
move_inst_to XM10 8486 8605
move_inst_to XM11 9817 13524
move_inst_to XM12 9448 8711
move_inst_to XM13 10779 8764
move_inst_to XM14 12110 13508
move_inst_to XM15 11741 8870
move_inst_to XM16 14772 13789
move_inst_to XM17 14403 8976
move_inst_to XM18 15734 9029
move_inst_to XM19 17065 13773
move_inst_to XM20 16696 9135
move_inst_to XM21 18027 14054
move_inst_to XM22 17658 9241
move_inst_to XM23 18989 9294
move_inst_to XM24 20320 14038
move_inst_to XM25 19951 9400
move_inst_to XM26 -5918 14244
move_inst_to XM27 -6287 9506
move_inst_to XM28 -3256 14350
move_inst_to XM29 -3625 9612

# Remove the M1 placeholders that Magic creates for top-level pins.
box values -10 -3300 210 210
select do labels
select area metal1
delete
select clear
select no labels

proc m3_track {xlo xhi y} {
    box values $xlo [expr {$y - 30}] $xhi [expr {$y + 30}]
    paint metal3
}

proc terminal_to_m3 {tx ty vx track {create_m3_via 1}} {
    set xlo [expr {min($tx, $vx) - 20}]
    set xhi [expr {max($tx, $vx) + 20}]
    box values $xlo [expr {$ty - 20}] $xhi [expr {$ty + 20}]
    paint metal1
    set vxlo [expr {$vx - 30}]
    set vxhi [expr {$vx + 30}]
    set tylo [expr {$ty - 30}]
    set tyhi [expr {$ty + 30}]
    box values [expr {$vx - 40}] [expr {$ty - 40}] [expr {$vx + 40}] [expr {$ty + 40}]
    paint metal1
    paint metal2
    box values $vxlo $tylo $vxhi $tyhi
    contact m2contact
    set ylo [expr {min($ty, $track) - 30}]
    set yhi [expr {max($ty, $track) + 30}]
    box values $vxlo $ylo $vxhi $yhi
    paint metal2
    if {$create_m3_via} {
        box values $vxlo [expr {$track - 30}] $vxhi [expr {$track + 30}]
        contact m3contact
        box values [expr {$vx - 42}] [expr {$track - 42}] [expr {$vx + 42}] [expr {$track + 42}]
        paint metal2
        box values [expr {$vx - 36}] [expr {$track - 36}] [expr {$vx + 36}] [expr {$track + 36}]
        paint metal3
    }
}

proc body_to_m3 {gx gy mx vx track} {
    set xlo [expr {min($gx, $mx) - 20}]
    set xhi [expr {max($gx, $mx) + 20}]
    box values $xlo [expr {$gy - 20}] $xhi [expr {$gy + 20}]
    paint locali
    set mxlo [expr {$mx - 30}]
    set mxhi [expr {$mx + 30}]
    box values $mxlo [expr {$gy - 30}] $mxhi [expr {$gy + 30}]
    paint locali
    box values [expr {$mx - 50}] [expr {$gy - 50}] [expr {$mx + 50}] [expr {$gy + 50}]
    paint metal1
    box values $mxlo [expr {$gy - 30}] $mxhi [expr {$gy + 30}]
    contact mcon
    terminal_to_m3 $mx $gy $vx $track
}

m3_track 400 29360 1680
m3_track 400 29650 -1680
m3_track 400 25550 1520
m3_track 400 1750 1200
m3_track 400 5150 1360
m3_track 750 21550 -400
m3_track 4150 13050 -240
m3_track 2450 26650 -720
m3_track 5850 24950 -560
m3_track 7550 11950 -80
m3_track 12650 17050 80
m3_track 19450 23850 240
m3_track 24550 28950 400
m3_track 9050 9450 -1360
m3_track 14150 14550 -1200
m3_track 20950 21350 -1040
m3_track 26050 26450 -880
m3_track 10750 27950 -1520
m3_track 400 11500 560
m3_track 400 16600 720
m3_track 400 23400 880
m3_track 400 28500 1040

# XM1: D=A0B, G=A0, S=VDD, B=VDD
terminal_to_m3 1456 2400 1200 -400
terminal_to_m3 1500 2548 1650 1200 1
terminal_to_m3 1500 2252 1650 1200 0
terminal_to_m3 1544 2400 1800 1680
body_to_m3 1500 2650 2000 2060 1680

# XM2: D=A0B, G=A0, S=VSS, B=VSS
terminal_to_m3 1456 -2400 850 -400
terminal_to_m3 1500 -2261 1050 1200 1
terminal_to_m3 1500 -2539 1050 1200 0
terminal_to_m3 1544 -2400 2350 -1680
body_to_m3 1500 -2159 2000 2200 -1680

# XM3: D=A1B, G=A1, S=VDD, B=VDD
terminal_to_m3 4856 2400 4600 -240
terminal_to_m3 4900 2548 5050 1360 1
terminal_to_m3 4900 2252 5050 1360 0
terminal_to_m3 4944 2400 5200 1680
body_to_m3 4900 2650 5400 5460 1680

# XM4: D=A1B, G=A1, S=VSS, B=VSS
terminal_to_m3 4856 -2400 4250 -240
terminal_to_m3 4900 -2261 4450 1360 1
terminal_to_m3 4900 -2539 4450 1360 0
terminal_to_m3 4944 -2400 5750 -1680
body_to_m3 4900 -2159 5400 5600 -1680

# XM5: D=N0, G=PCLK, S=VDD, B=VDD
terminal_to_m3 8256 2400 8000 -80
terminal_to_m3 8300 2589 8450 1520 1
terminal_to_m3 8300 2211 8450 1520 0
terminal_to_m3 8344 2400 8600 1680
body_to_m3 8300 2691 8800 8860 1680

# XM6: D=N0, G=A1B, S=net1, B=VSS
terminal_to_m3 8256 -2400 7650 -80
terminal_to_m3 8300 -2145 7850 -240 1
terminal_to_m3 8300 -2655 7850 -240 0
terminal_to_m3 8344 -2400 9150 -1360
body_to_m3 8300 -2043 8800 9000 -1680

# XM7: D=net1, G=A0B, S=EVAL_GND, B=VSS
terminal_to_m3 9956 -2400 9350 -1360
terminal_to_m3 10000 -2145 9550 -400 1
terminal_to_m3 10000 -2655 9550 -400 0
terminal_to_m3 10044 -2400 10850 -1520
body_to_m3 10000 -2043 10500 10700 -1680

# XM8: D=EVAL_GND, G=PCLK, S=VSS, B=VSS
terminal_to_m3 18456 -2400 17850 -1520
terminal_to_m3 18500 -2195 18050 1520 1
terminal_to_m3 18500 -2605 18050 1520 0
terminal_to_m3 18544 -2400 19350 -1680
body_to_m3 18500 -2093 19000 19200 -1680

# XM9: D=DEC0, G=N0, S=VDD, B=VDD
terminal_to_m3 11656 2400 11400 560
terminal_to_m3 11700 2764 11850 -80 1
terminal_to_m3 11700 2036 11850 -80 0
terminal_to_m3 11744 2400 12000 1680
body_to_m3 11700 2866 12200 12260 1680

# XM10: D=DEC0, G=N0, S=VSS, B=VSS
terminal_to_m3 11656 -2400 11050 560
terminal_to_m3 11700 -2145 11250 -80 1
terminal_to_m3 11700 -2655 11250 -80 0
terminal_to_m3 11744 -2400 12550 -1680
body_to_m3 11700 -2043 12200 12400 -1680

# XM11: D=N1, G=PCLK, S=VDD, B=VDD
terminal_to_m3 13356 2400 13100 80
terminal_to_m3 13400 2589 13550 1520 1
terminal_to_m3 13400 2211 13550 1520 0
terminal_to_m3 13444 2400 13700 1680
body_to_m3 13400 2691 13900 13960 1680

# XM12: D=N1, G=A1B, S=net2, B=VSS
terminal_to_m3 13356 -2400 12750 80
terminal_to_m3 13400 -2145 12950 -240 1
terminal_to_m3 13400 -2655 12950 -240 0
terminal_to_m3 13444 -2400 14250 -1200
body_to_m3 13400 -2043 13900 14100 -1680

# XM13: D=net2, G=A0T, S=EVAL_GND, B=VSS
terminal_to_m3 15056 -2400 14450 -1200
terminal_to_m3 15100 -2145 14650 -720 1
terminal_to_m3 15100 -2655 14650 -720 0
terminal_to_m3 15144 -2400 15950 -1520
body_to_m3 15100 -2043 15600 15800 -1680

# XM14: D=DEC1, G=N1, S=VDD, B=VDD
terminal_to_m3 16756 2400 16500 720
terminal_to_m3 16800 2764 16950 80 1
terminal_to_m3 16800 2036 16950 80 0
terminal_to_m3 16844 2400 17100 1680
body_to_m3 16800 2866 17300 17360 1680

# XM15: D=DEC1, G=N1, S=VSS, B=VSS
terminal_to_m3 16756 -2400 16150 720
terminal_to_m3 16800 -2145 16350 80 1
terminal_to_m3 16800 -2655 16350 80 0
terminal_to_m3 16844 -2400 17650 -1680
body_to_m3 16800 -2043 17300 17500 -1680

# XM16: D=N2, G=PCLK, S=VDD, B=VDD
terminal_to_m3 20156 2400 19900 240
terminal_to_m3 20200 2589 20350 1520 1
terminal_to_m3 20200 2211 20350 1520 0
terminal_to_m3 20244 2400 20500 1680
body_to_m3 20200 2691 20700 20760 1680

# XM17: D=N2, G=A1T, S=net3, B=VSS
terminal_to_m3 20156 -2400 19550 240
terminal_to_m3 20200 -2145 19750 -560 1
terminal_to_m3 20200 -2655 19750 -560 0
terminal_to_m3 20244 -2400 21050 -1040
body_to_m3 20200 -2043 20700 20900 -1680

# XM18: D=net3, G=A0B, S=EVAL_GND, B=VSS
terminal_to_m3 21856 -2400 21250 -1040
terminal_to_m3 21900 -2145 21450 -400 1
terminal_to_m3 21900 -2655 21450 -400 0
terminal_to_m3 21944 -2400 22750 -1520
body_to_m3 21900 -2043 22400 22600 -1680

# XM19: D=DEC2, G=N2, S=VDD, B=VDD
terminal_to_m3 23556 2400 23300 880
terminal_to_m3 23600 2764 23750 240 1
terminal_to_m3 23600 2036 23750 240 0
terminal_to_m3 23644 2400 23900 1680
body_to_m3 23600 2866 24100 24160 1680

# XM20: D=DEC2, G=N2, S=VSS, B=VSS
terminal_to_m3 23556 -2400 22950 880
terminal_to_m3 23600 -2145 23150 240 1
terminal_to_m3 23600 -2655 23150 240 0
terminal_to_m3 23644 -2400 24450 -1680
body_to_m3 23600 -2043 24100 24300 -1680

# XM21: D=N3, G=PCLK, S=VDD, B=VDD
terminal_to_m3 25256 2400 25000 400
terminal_to_m3 25300 2589 25450 1520 1
terminal_to_m3 25300 2211 25450 1520 0
terminal_to_m3 25344 2400 25600 1680
body_to_m3 25300 2691 25800 25860 1680

# XM22: D=N3, G=A1T, S=net4, B=VSS
terminal_to_m3 25256 -2400 24650 400
terminal_to_m3 25300 -2145 24850 -560 1
terminal_to_m3 25300 -2655 24850 -560 0
terminal_to_m3 25344 -2400 26150 -880
body_to_m3 25300 -2043 25800 26000 -1680

# XM23: D=net4, G=A0T, S=EVAL_GND, B=VSS
terminal_to_m3 26956 -2400 26350 -880
terminal_to_m3 27000 -2145 26550 -720 1
terminal_to_m3 27000 -2655 26550 -720 0
terminal_to_m3 27044 -2400 27850 -1520
body_to_m3 27000 -2043 27500 27700 -1680

# XM24: D=DEC3, G=N3, S=VDD, B=VDD
terminal_to_m3 28656 2400 28400 1040
terminal_to_m3 28700 2764 28850 400 1
terminal_to_m3 28700 2036 28850 400 0
terminal_to_m3 28744 2400 29000 1680
body_to_m3 28700 2866 29200 29260 1680

# XM25: D=DEC3, G=N3, S=VSS, B=VSS
terminal_to_m3 28656 -2400 28050 1040
terminal_to_m3 28700 -2145 28250 400 1
terminal_to_m3 28700 -2655 28250 400 0
terminal_to_m3 28744 -2400 29550 -1680
body_to_m3 28700 -2043 29200 29400 -1680

# XM26: D=A0T, G=A0B, S=VDD, B=VDD
terminal_to_m3 3156 2400 2900 -720
terminal_to_m3 3200 2664 3350 -400 1
terminal_to_m3 3200 2136 3350 -400 0
terminal_to_m3 3244 2400 3500 1680
body_to_m3 3200 2766 3700 3760 1680

# XM27: D=A0T, G=A0B, S=VSS, B=VSS
terminal_to_m3 3156 -2400 2550 -720
terminal_to_m3 3200 -2145 2750 -400 1
terminal_to_m3 3200 -2655 2750 -400 0
terminal_to_m3 3244 -2400 4050 -1680
body_to_m3 3200 -2043 3700 3900 -1680

# XM28: D=A1T, G=A1B, S=VDD, B=VDD
terminal_to_m3 6556 2400 6300 -560
terminal_to_m3 6600 2664 6750 -240 1
terminal_to_m3 6600 2136 6750 -240 0
terminal_to_m3 6644 2400 6900 1680
body_to_m3 6600 2766 7100 7160 1680

# XM29: D=A1T, G=A1B, S=VSS, B=VSS
terminal_to_m3 6556 -2400 5950 -560
terminal_to_m3 6600 -2145 6150 -240 1
terminal_to_m3 6600 -2655 6150 -240 0
terminal_to_m3 6644 -2400 7450 -1680
body_to_m3 6600 -2043 7100 7300 -1680

box values 475 1655 525 1705
label VDD center metal3
select clear
select do labels
select area metal3
port make 0 n
select clear
select no labels
box values 475 -1705 525 -1655
label VSS center metal3
select clear
select do labels
select area metal3
port make 8 n
select clear
select no labels
box values 475 1495 525 1545
label PCLK center metal3
select clear
select do labels
select area metal3
port make 1 n
select clear
select no labels
box values 475 1175 525 1225
label A0 center metal3
select clear
select do labels
select area metal3
port make 2 n
select clear
select no labels
box values 475 1335 525 1385
label A1 center metal3
select clear
select do labels
select area metal3
port make 3 n
select clear
select no labels
box values 21475 -425 21525 -375
label A0B center metal3
select clear
select no labels
box values 12975 -265 13025 -215
label A1B center metal3
select clear
select no labels
box values 26575 -745 26625 -695
label A0T center metal3
select clear
select no labels
box values 24875 -585 24925 -535
label A1T center metal3
select clear
select no labels
box values 11875 -105 11925 -55
label N0 center metal3
select clear
select no labels
box values 16975 55 17025 105
label N1 center metal3
select clear
select no labels
box values 23775 215 23825 265
label N2 center metal3
select clear
select no labels
box values 28875 375 28925 425
label N3 center metal3
select clear
select no labels
box values 9375 -1385 9425 -1335
label net1 center metal3
select clear
select no labels
box values 14475 -1225 14525 -1175
label net2 center metal3
select clear
select no labels
box values 21275 -1065 21325 -1015
label net3 center metal3
select clear
select no labels
box values 26375 -905 26425 -855
label net4 center metal3
select clear
select no labels
box values 27875 -1545 27925 -1495
label EVAL_GND center metal3
select clear
select no labels
box values 475 535 525 585
label DEC0 center metal3
select clear
select do labels
select area metal3
port make 4 n
select clear
select no labels
box values 475 695 525 745
label DEC1 center metal3
select clear
select do labels
select area metal3
port make 5 n
select clear
select no labels
box values 475 855 525 905
label DEC2 center metal3
select clear
select do labels
select area metal3
port make 7 n
select clear
select no labels
box values 475 1015 525 1065
label DEC3 center metal3
select clear
select do labels
select area metal3
port make 6 n
select clear
select no labels

select top cell
drc style drc(full)
drc check
drc catchup
drc count total
save row_decoder_layout
quit -noprompt
