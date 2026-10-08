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

move_inst_to XM1 1607 11635
move_inst_to XM2 1238 9697
move_inst_to XM3 3069 11741
move_inst_to XM4 2700 9803
move_inst_to XM5 4531 11806
move_inst_to XM6 4162 9793
move_inst_to XM7 4893 9846
move_inst_to XM8 10024 9949
move_inst_to XM9 5255 11843
move_inst_to XM10 4886 10005
move_inst_to XM11 5617 12124
move_inst_to XM12 5248 10111
move_inst_to XM13 5979 10164
move_inst_to XM14 6710 12108
move_inst_to XM15 6341 10270
move_inst_to XM16 8172 12389
move_inst_to XM17 7803 10376
move_inst_to XM18 8534 10429
move_inst_to XM19 9265 12373
move_inst_to XM20 8896 10535
move_inst_to XM21 9627 12654
move_inst_to XM22 9258 10641
move_inst_to XM23 9989 10694
move_inst_to XM24 10720 12638
move_inst_to XM25 10351 10800
move_inst_to XM26 -6518 12844
move_inst_to XM27 -6887 10906
move_inst_to XM28 -5056 12950
move_inst_to XM29 -5425 11012

# Remove the M1 placeholders that Magic creates for top-level pins.
box values -10 -3300 210 210
select do labels
select area metal1
delete
select clear
select no labels

save row_decoder_placed
proc m3_track {y xmin xmax} {
    box values $xmin [expr {$y - 30}] $xmax [expr {$y + 30}]
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

m3_track 1700 100 19800
m3_track -1700 100 19800
m3_track 3200 440 17110
m3_track 200 440 1710
m3_track 500 440 3910
m3_track 3800 1140 14610
m3_track 4400 3340 9110
m3_track 5000 2240 17910
m3_track 5600 4440 16810
m3_track 2000 5540 8310
m3_track 2000 8840 11610
m3_track 2000 13240 16010
m3_track 2000 16540 19310
m3_track 2300 6600 6800
m3_track 2300 9900 10100
m3_track 2300 14300 14500
m3_track 2300 17600 17800
m3_track 0 7240 18360
m3_track 2600 7740 8860
m3_track 2600 11040 12160
m3_track 2600 15440 16560
m3_track 2600 18740 19860
terminal_to_m3 200 -1700 200 -1700
m3_track 3500 100 19800
terminal_to_m3 200 -1700 200 3500
m3_track 4100 100 19800
terminal_to_m3 200 -1700 200 4100
m3_track 4700 100 19800
terminal_to_m3 200 -1700 200 4700
m3_track 5300 100 19800
terminal_to_m3 200 -1700 200 5300

# XM1: D=A0B, G=A0, S=VDD, B=VDD
terminal_to_m3 1456 1000 1200 3800
terminal_to_m3 1500 1148 1650 200 1
terminal_to_m3 1500 852 1650 200 0
terminal_to_m3 1544 1000 1800 1700
body_to_m3 1500 1250 2000 2060 1700

# XM2: D=A0B, G=A0, S=VSS, B=VSS
terminal_to_m3 1456 -1000 1200 3800
terminal_to_m3 1500 -861 1350 200 1
terminal_to_m3 1500 -1139 1350 200 0
terminal_to_m3 1544 -1000 1800 -1700
body_to_m3 1500 -759 2000 2060 -1700

# XM3: D=A1B, G=A1, S=VDD, B=VDD
terminal_to_m3 3656 1000 3400 4400
terminal_to_m3 3700 1148 3850 500 1
terminal_to_m3 3700 852 3850 500 0
terminal_to_m3 3744 1000 4000 1700
body_to_m3 3700 1250 4200 4260 1700

# XM4: D=A1B, G=A1, S=VSS, B=VSS
terminal_to_m3 3656 -1000 3400 4400
terminal_to_m3 3700 -861 3550 500 1
terminal_to_m3 3700 -1139 3550 500 0
terminal_to_m3 3744 -1000 4000 -1700
body_to_m3 3700 -759 4200 4260 -1700

# XM5: D=N0, G=PCLK, S=VDD, B=VDD
terminal_to_m3 5856 1000 5600 2000
terminal_to_m3 5900 1189 6050 3200 1
terminal_to_m3 5900 811 6050 3200 0
terminal_to_m3 5944 1000 6200 1700
body_to_m3 5900 1291 6400 6460 1700

# XM6: D=N0, G=A1B, S=net1, B=VSS
terminal_to_m3 5856 -1000 5600 2000
terminal_to_m3 5900 -745 5750 4400 1
terminal_to_m3 5900 -1255 5750 4400 0
terminal_to_m3 5944 -1000 6700 2300
body_to_m3 5900 -643 6400 6460 -1700

# XM7: D=net1, G=A0B, S=EVAL_GND, B=VSS
terminal_to_m3 6956 -1000 6700 2300
terminal_to_m3 7000 -745 6850 3800 1
terminal_to_m3 7000 -1255 6850 3800 0
terminal_to_m3 7044 -1000 7300 0
body_to_m3 7000 -643 7500 7560 -1700

# XM8: D=EVAL_GND, G=PCLK, S=VSS, B=VSS
terminal_to_m3 12456 -1000 12200 0
terminal_to_m3 12500 -795 12350 3200 1
terminal_to_m3 12500 -1205 12350 3200 0
terminal_to_m3 12544 -1000 12800 -1700
body_to_m3 12500 -693 13000 13060 -1700

# XM9: D=DEC0, G=N0, S=VDD, B=VDD
terminal_to_m3 8056 1000 7800 2600
terminal_to_m3 8100 1364 8250 2000 1
terminal_to_m3 8100 636 8250 2000 0
terminal_to_m3 8144 1000 8400 1700
body_to_m3 8100 1466 8600 8660 1700

# XM10: D=DEC0, G=N0, S=VSS, B=VSS
terminal_to_m3 8056 -1000 7800 2600
terminal_to_m3 8100 -745 7950 2000 1
terminal_to_m3 8100 -1255 7950 2000 0
terminal_to_m3 8144 -1000 8400 -1700
body_to_m3 8100 -643 8600 8660 -1700

# XM11: D=N1, G=PCLK, S=VDD, B=VDD
terminal_to_m3 9156 1000 8900 2000
terminal_to_m3 9200 1189 9350 3200 1
terminal_to_m3 9200 811 9350 3200 0
terminal_to_m3 9244 1000 9500 1700
body_to_m3 9200 1291 9700 9760 1700

# XM12: D=N1, G=A1B, S=net2, B=VSS
terminal_to_m3 9156 -1000 8900 2000
terminal_to_m3 9200 -745 9050 4400 1
terminal_to_m3 9200 -1255 9050 4400 0
terminal_to_m3 9244 -1000 10000 2300
body_to_m3 9200 -643 9700 9760 -1700

# XM13: D=net2, G=A0T, S=EVAL_GND, B=VSS
terminal_to_m3 10256 -1000 10000 2300
terminal_to_m3 10300 -745 10150 5000 1
terminal_to_m3 10300 -1255 10150 5000 0
terminal_to_m3 10344 -1000 10600 0
body_to_m3 10300 -643 10800 10860 -1700

# XM14: D=DEC1, G=N1, S=VDD, B=VDD
terminal_to_m3 11356 1000 11100 2600
terminal_to_m3 11400 1364 11550 2000 1
terminal_to_m3 11400 636 11550 2000 0
terminal_to_m3 11444 1000 11700 1700
body_to_m3 11400 1466 11900 11960 1700

# XM15: D=DEC1, G=N1, S=VSS, B=VSS
terminal_to_m3 11356 -1000 11100 2600
terminal_to_m3 11400 -745 11250 2000 1
terminal_to_m3 11400 -1255 11250 2000 0
terminal_to_m3 11444 -1000 11700 -1700
body_to_m3 11400 -643 11900 11960 -1700

# XM16: D=N2, G=PCLK, S=VDD, B=VDD
terminal_to_m3 13556 1000 13300 2000
terminal_to_m3 13600 1189 13750 3200 1
terminal_to_m3 13600 811 13750 3200 0
terminal_to_m3 13644 1000 13900 1700
body_to_m3 13600 1291 14100 14160 1700

# XM17: D=N2, G=A1T, S=net3, B=VSS
terminal_to_m3 13556 -1000 13300 2000
terminal_to_m3 13600 -745 13450 5600 1
terminal_to_m3 13600 -1255 13450 5600 0
terminal_to_m3 13644 -1000 14400 2300
body_to_m3 13600 -643 14100 14160 -1700

# XM18: D=net3, G=A0B, S=EVAL_GND, B=VSS
terminal_to_m3 14656 -1000 14400 2300
terminal_to_m3 14700 -745 14550 3800 1
terminal_to_m3 14700 -1255 14550 3800 0
terminal_to_m3 14744 -1000 15000 0
body_to_m3 14700 -643 15200 15260 -1700

# XM19: D=DEC2, G=N2, S=VDD, B=VDD
terminal_to_m3 15756 1000 15500 2600
terminal_to_m3 15800 1364 15950 2000 1
terminal_to_m3 15800 636 15950 2000 0
terminal_to_m3 15844 1000 16100 1700
body_to_m3 15800 1466 16300 16360 1700

# XM20: D=DEC2, G=N2, S=VSS, B=VSS
terminal_to_m3 15756 -1000 15500 2600
terminal_to_m3 15800 -745 15650 2000 1
terminal_to_m3 15800 -1255 15650 2000 0
terminal_to_m3 15844 -1000 16100 -1700
body_to_m3 15800 -643 16300 16360 -1700

# XM21: D=N3, G=PCLK, S=VDD, B=VDD
terminal_to_m3 16856 1000 16600 2000
terminal_to_m3 16900 1189 17050 3200 1
terminal_to_m3 16900 811 17050 3200 0
terminal_to_m3 16944 1000 17200 1700
body_to_m3 16900 1291 17400 17460 1700

# XM22: D=N3, G=A1T, S=net4, B=VSS
terminal_to_m3 16856 -1000 16600 2000
terminal_to_m3 16900 -745 16750 5600 1
terminal_to_m3 16900 -1255 16750 5600 0
terminal_to_m3 16944 -1000 17700 2300
body_to_m3 16900 -643 17400 17460 -1700

# XM23: D=net4, G=A0T, S=EVAL_GND, B=VSS
terminal_to_m3 17956 -1000 17700 2300
terminal_to_m3 18000 -745 17850 5000 1
terminal_to_m3 18000 -1255 17850 5000 0
terminal_to_m3 18044 -1000 18300 0
body_to_m3 18000 -643 18500 18560 -1700

# XM24: D=DEC3, G=N3, S=VDD, B=VDD
terminal_to_m3 19056 1000 18800 2600
terminal_to_m3 19100 1364 19250 2000 1
terminal_to_m3 19100 636 19250 2000 0
terminal_to_m3 19144 1000 19400 1700
body_to_m3 19100 1466 19600 19660 1700

# XM25: D=DEC3, G=N3, S=VSS, B=VSS
terminal_to_m3 19056 -1000 18800 2600
terminal_to_m3 19100 -745 18950 2000 1
terminal_to_m3 19100 -1255 18950 2000 0
terminal_to_m3 19144 -1000 19400 -1700
body_to_m3 19100 -643 19600 19660 -1700

# XM26: D=A0T, G=A0B, S=VDD, B=VDD
terminal_to_m3 2556 1000 2300 5000
terminal_to_m3 2600 1264 2750 3800 1
terminal_to_m3 2600 736 2750 3800 0
terminal_to_m3 2644 1000 2900 1700
body_to_m3 2600 1366 3100 3160 1700

# XM27: D=A0T, G=A0B, S=VSS, B=VSS
terminal_to_m3 2556 -1000 2300 5000
terminal_to_m3 2600 -745 2450 3800 1
terminal_to_m3 2600 -1255 2450 3800 0
terminal_to_m3 2644 -1000 2900 -1700
body_to_m3 2600 -643 3100 3160 -1700

# XM28: D=A1T, G=A1B, S=VDD, B=VDD
terminal_to_m3 4756 1000 4500 5600
terminal_to_m3 4800 1264 4950 4400 1
terminal_to_m3 4800 736 4950 4400 0
terminal_to_m3 4844 1000 5100 1700
body_to_m3 4800 1366 5300 5360 1700

# XM29: D=A1T, G=A1B, S=VSS, B=VSS
terminal_to_m3 4756 -1000 4500 5600
terminal_to_m3 4800 -745 4650 4400 1
terminal_to_m3 4800 -1255 4650 4400 0
terminal_to_m3 4844 -1000 5100 -1700
body_to_m3 4800 -643 5300 5360 -1700

box values 475 1675 525 1725
label VDD center metal3
select clear
select do labels
select area metal3
port make 0 n
select clear
select no labels
box values 475 -1725 525 -1675
label VSS center metal3
select clear
select do labels
select area metal3
port make 8 n
select clear
select no labels
box values 475 3175 525 3225
label PCLK center metal3
select clear
select do labels
select area metal3
port make 1 n
select clear
select no labels
box values 475 175 525 225
label A0 center metal3
select clear
select do labels
select area metal3
port make 2 n
select clear
select no labels
box values 475 475 525 525
label A1 center metal3
select clear
select do labels
select area metal3
port make 3 n
select clear
select no labels
box values 1175 3775 1225 3825
label A0B center metal3
select clear
select no labels
box values 3375 4375 3425 4425
label A1B center metal3
select clear
select no labels
box values 2275 4975 2325 5025
label A0T center metal3
select clear
select no labels
box values 4475 5575 4525 5625
label A1T center metal3
select clear
select no labels
box values 5575 1975 5625 2025
label N0 center metal3
select clear
select no labels
box values 8875 1975 8925 2025
label N1 center metal3
select clear
select no labels
box values 13275 1975 13325 2025
label N2 center metal3
select clear
select no labels
box values 16575 1975 16625 2025
label N3 center metal3
select clear
select no labels
box values 6635 2275 6685 2325
label net1 center metal3
select clear
select no labels
box values 9935 2275 9985 2325
label net2 center metal3
select clear
select no labels
box values 14335 2275 14385 2325
label net3 center metal3
select clear
select no labels
box values 17635 2275 17685 2325
label net4 center metal3
select clear
select no labels
box values 7275 -25 7325 25
label EVAL_GND center metal3
select clear
select no labels
box values 8775 2575 8825 2625
label DEC0 center metal3
select clear
select do labels
select area metal3
port make 4 n
select clear
select no labels
box values 12075 2575 12125 2625
label DEC1 center metal3
select clear
select do labels
select area metal3
port make 5 n
select clear
select no labels
box values 16475 2575 16525 2625
label DEC2 center metal3
select clear
select do labels
select area metal3
port make 7 n
select clear
select no labels
box values 19775 2575 19825 2625
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
