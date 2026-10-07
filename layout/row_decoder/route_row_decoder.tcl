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

move_inst_to XM1 1395 6529
move_inst_to XM2 2526 2591
move_inst_to XM3 3657 6635
move_inst_to XM4 4788 2697
move_inst_to XM5 5919 6733
move_inst_to XM6 7050 2745
move_inst_to XM7 8181 2798
move_inst_to XM8 9312 2801
move_inst_to XM9 10443 6795
move_inst_to XM10 11574 2857
move_inst_to XM11 12705 7051
move_inst_to XM12 13836 3063
move_inst_to XM13 14967 3116
move_inst_to XM14 16098 7060
move_inst_to XM15 17229 3122
move_inst_to XM16 18360 7316
move_inst_to XM17 19491 3328
move_inst_to XM18 20622 3381
move_inst_to XM19 21753 7325
move_inst_to XM20 22884 3387
move_inst_to XM21 24015 7581
move_inst_to XM22 25146 3593
move_inst_to XM23 26277 3646
move_inst_to XM24 27408 7590
move_inst_to XM25 28539 3652
move_inst_to XM26 29670 7696
move_inst_to XM27 30801 3758
move_inst_to XM28 31932 7802
move_inst_to XM29 33063 3864

# Remove the M1 placeholders that Magic creates for top-level pins.
box values -10 -3300 210 210
select do labels
select area metal1
delete
select clear
select no labels

proc m3_track {y} {
    box values 400 [expr {$y - 30}] 44500 [expr {$y + 30}]
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

m3_track 6000
m3_track 6300
m3_track 6600
m3_track 6900
m3_track 7200
m3_track 7500
m3_track 7800
m3_track 8100
m3_track 8400
m3_track 8700
m3_track 9000
m3_track 9300
m3_track 9600
m3_track 9900
m3_track 10200
m3_track 10500
m3_track 10800
m3_track 11100
m3_track 11400
m3_track 11700
m3_track 12000
m3_track 12300

# XM1: D=A0B, G=A0, S=VDD, B=VDD
terminal_to_m3 1456 2000 1200 7500
terminal_to_m3 1500 2106 1650 6900 1
terminal_to_m3 1500 1894 1650 6900 0
terminal_to_m3 1544 2000 1800 6000
body_to_m3 1500 2208 2000 2060 6000

# XM2: D=A0B, G=A0, S=VSS, B=VSS
terminal_to_m3 2956 -2000 2700 7500
terminal_to_m3 3000 -1903 3150 6900 1
terminal_to_m3 3000 -2097 3150 6900 0
terminal_to_m3 3044 -2000 3300 6300
body_to_m3 3000 -1801 3500 3560 6300

# XM3: D=A1B, G=A1, S=VDD, B=VDD
terminal_to_m3 4456 2000 4200 7800
terminal_to_m3 4500 2106 4650 7200 1
terminal_to_m3 4500 1894 4650 7200 0
terminal_to_m3 4544 2000 4800 6000
body_to_m3 4500 2208 5000 5060 6000

# XM4: D=A1B, G=A1, S=VSS, B=VSS
terminal_to_m3 5956 -2000 5700 7800
terminal_to_m3 6000 -1903 6150 7200 1
terminal_to_m3 6000 -2097 6150 7200 0
terminal_to_m3 6044 -2000 6300 6300
body_to_m3 6000 -1801 6500 6560 6300

# XM5: D=N0, G=PCLK, S=VDD, B=VDD
terminal_to_m3 7456 2000 7200 8700
terminal_to_m3 7500 2114 7650 6600 1
terminal_to_m3 7500 1886 7650 6600 0
terminal_to_m3 7544 2000 7800 6000
body_to_m3 7500 2216 8000 8060 6000

# XM6: D=N0, G=A1B, S=net1, B=VSS
terminal_to_m3 8956 -2000 8700 8700
terminal_to_m3 9000 -1845 9150 7800 1
terminal_to_m3 9000 -2155 9150 7800 0
terminal_to_m3 9044 -2000 9300 9900
body_to_m3 9000 -1743 9500 9560 6300

# XM7: D=net1, G=A0B, S=EVAL_GND, B=VSS
terminal_to_m3 10456 -2000 10200 9900
terminal_to_m3 10500 -1845 10650 7500 1
terminal_to_m3 10500 -2155 10650 7500 0
terminal_to_m3 10544 -2000 10800 11100
body_to_m3 10500 -1743 11000 11060 6300

# XM8: D=EVAL_GND, G=PCLK, S=VSS, B=VSS
terminal_to_m3 11956 -2000 11700 11100
terminal_to_m3 12000 -1795 12150 6600 1
terminal_to_m3 12000 -2205 12150 6600 0
terminal_to_m3 12044 -2000 12300 6300
body_to_m3 12000 -1693 12500 12560 6300

# XM9: D=DEC0, G=N0, S=VDD, B=VDD
terminal_to_m3 13456 2000 13200 11400
terminal_to_m3 13500 2264 13650 8700 1
terminal_to_m3 13500 1736 13650 8700 0
terminal_to_m3 13544 2000 13800 6000
body_to_m3 13500 2366 14000 14060 6000

# XM10: D=DEC0, G=N0, S=VSS, B=VSS
terminal_to_m3 14956 -2000 14700 11400
terminal_to_m3 15000 -1745 15150 8700 1
terminal_to_m3 15000 -2255 15150 8700 0
terminal_to_m3 15044 -2000 15300 6300
body_to_m3 15000 -1643 15500 15560 6300

# XM11: D=N1, G=PCLK, S=VDD, B=VDD
terminal_to_m3 16456 2000 16200 9000
terminal_to_m3 16500 2114 16650 6600 1
terminal_to_m3 16500 1886 16650 6600 0
terminal_to_m3 16544 2000 16800 6000
body_to_m3 16500 2216 17000 17060 6000

# XM12: D=N1, G=A1B, S=net2, B=VSS
terminal_to_m3 17956 -2000 17700 9000
terminal_to_m3 18000 -1845 18150 7800 1
terminal_to_m3 18000 -2155 18150 7800 0
terminal_to_m3 18044 -2000 18300 10200
body_to_m3 18000 -1743 18500 18560 6300

# XM13: D=net2, G=A0T, S=EVAL_GND, B=VSS
terminal_to_m3 19456 -2000 19200 10200
terminal_to_m3 19500 -1845 19650 8100 1
terminal_to_m3 19500 -2155 19650 8100 0
terminal_to_m3 19544 -2000 19800 11100
body_to_m3 19500 -1743 20000 20060 6300

# XM14: D=DEC1, G=N1, S=VDD, B=VDD
terminal_to_m3 20956 2000 20700 11700
terminal_to_m3 21000 2264 21150 9000 1
terminal_to_m3 21000 1736 21150 9000 0
terminal_to_m3 21044 2000 21300 6000
body_to_m3 21000 2366 21500 21560 6000

# XM15: D=DEC1, G=N1, S=VSS, B=VSS
terminal_to_m3 22456 -2000 22200 11700
terminal_to_m3 22500 -1745 22650 9000 1
terminal_to_m3 22500 -2255 22650 9000 0
terminal_to_m3 22544 -2000 22800 6300
body_to_m3 22500 -1643 23000 23060 6300

# XM16: D=N2, G=PCLK, S=VDD, B=VDD
terminal_to_m3 23956 2000 23700 9300
terminal_to_m3 24000 2114 24150 6600 1
terminal_to_m3 24000 1886 24150 6600 0
terminal_to_m3 24044 2000 24300 6000
body_to_m3 24000 2216 24500 24560 6000

# XM17: D=N2, G=A1T, S=net3, B=VSS
terminal_to_m3 25456 -2000 25200 9300
terminal_to_m3 25500 -1845 25650 8400 1
terminal_to_m3 25500 -2155 25650 8400 0
terminal_to_m3 25544 -2000 25800 10500
body_to_m3 25500 -1743 26000 26060 6300

# XM18: D=net3, G=A0B, S=EVAL_GND, B=VSS
terminal_to_m3 26956 -2000 26700 10500
terminal_to_m3 27000 -1845 27150 7500 1
terminal_to_m3 27000 -2155 27150 7500 0
terminal_to_m3 27044 -2000 27300 11100
body_to_m3 27000 -1743 27500 27560 6300

# XM19: D=DEC2, G=N2, S=VDD, B=VDD
terminal_to_m3 28456 2000 28200 12000
terminal_to_m3 28500 2264 28650 9300 1
terminal_to_m3 28500 1736 28650 9300 0
terminal_to_m3 28544 2000 28800 6000
body_to_m3 28500 2366 29000 29060 6000

# XM20: D=DEC2, G=N2, S=VSS, B=VSS
terminal_to_m3 29956 -2000 29700 12000
terminal_to_m3 30000 -1745 30150 9300 1
terminal_to_m3 30000 -2255 30150 9300 0
terminal_to_m3 30044 -2000 30300 6300
body_to_m3 30000 -1643 30500 30560 6300

# XM21: D=N3, G=PCLK, S=VDD, B=VDD
terminal_to_m3 31456 2000 31200 9600
terminal_to_m3 31500 2114 31650 6600 1
terminal_to_m3 31500 1886 31650 6600 0
terminal_to_m3 31544 2000 31800 6000
body_to_m3 31500 2216 32000 32060 6000

# XM22: D=N3, G=A1T, S=net4, B=VSS
terminal_to_m3 32956 -2000 32700 9600
terminal_to_m3 33000 -1845 33150 8400 1
terminal_to_m3 33000 -2155 33150 8400 0
terminal_to_m3 33044 -2000 33300 10800
body_to_m3 33000 -1743 33500 33560 6300

# XM23: D=net4, G=A0T, S=EVAL_GND, B=VSS
terminal_to_m3 34456 -2000 34200 10800
terminal_to_m3 34500 -1845 34650 8100 1
terminal_to_m3 34500 -2155 34650 8100 0
terminal_to_m3 34544 -2000 34800 11100
body_to_m3 34500 -1743 35000 35060 6300

# XM24: D=DEC3, G=N3, S=VDD, B=VDD
terminal_to_m3 35956 2000 35700 12300
terminal_to_m3 36000 2264 36150 9600 1
terminal_to_m3 36000 1736 36150 9600 0
terminal_to_m3 36044 2000 36300 6000
body_to_m3 36000 2366 36500 36560 6000

# XM25: D=DEC3, G=N3, S=VSS, B=VSS
terminal_to_m3 37456 -2000 37200 12300
terminal_to_m3 37500 -1745 37650 9600 1
terminal_to_m3 37500 -2255 37650 9600 0
terminal_to_m3 37544 -2000 37800 6300
body_to_m3 37500 -1643 38000 38060 6300

# XM26: D=A0T, G=A0B, S=VDD, B=VDD
terminal_to_m3 38956 2000 38700 8100
terminal_to_m3 39000 2264 39150 7500 1
terminal_to_m3 39000 1736 39150 7500 0
terminal_to_m3 39044 2000 39300 6000
body_to_m3 39000 2366 39500 39560 6000

# XM27: D=A0T, G=A0B, S=VSS, B=VSS
terminal_to_m3 40456 -2000 40200 8100
terminal_to_m3 40500 -1745 40650 7500 1
terminal_to_m3 40500 -2255 40650 7500 0
terminal_to_m3 40544 -2000 40800 6300
body_to_m3 40500 -1643 41000 41060 6300

# XM28: D=A1T, G=A1B, S=VDD, B=VDD
terminal_to_m3 41956 2000 41700 8400
terminal_to_m3 42000 2264 42150 7800 1
terminal_to_m3 42000 1736 42150 7800 0
terminal_to_m3 42044 2000 42300 6000
body_to_m3 42000 2366 42500 42560 6000

# XM29: D=A1T, G=A1B, S=VSS, B=VSS
terminal_to_m3 43456 -2000 43200 8400
terminal_to_m3 43500 -1745 43650 7800 1
terminal_to_m3 43500 -2255 43650 7800 0
terminal_to_m3 43544 -2000 43800 6300
body_to_m3 43500 -1643 44000 44060 6300

box values 475 5975 525 6025
label VDD center metal3
select clear
select do labels
select area metal3
port make 0 n
select clear
select no labels
box values 475 6275 525 6325
label VSS center metal3
select clear
select do labels
select area metal3
port make 8 n
select clear
select no labels
box values 475 6575 525 6625
label PCLK center metal3
select clear
select do labels
select area metal3
port make 1 n
select clear
select no labels
box values 475 6875 525 6925
label A0 center metal3
select clear
select do labels
select area metal3
port make 2 n
select clear
select no labels
box values 475 7175 525 7225
label A1 center metal3
select clear
select do labels
select area metal3
port make 3 n
select clear
select no labels
box values 44350 7475 44400 7525
label A0B center metal3
select clear
select no labels
box values 44350 7775 44400 7825
label A1B center metal3
select clear
select no labels
box values 44350 8075 44400 8125
label A0T center metal3
select clear
select no labels
box values 44350 8375 44400 8425
label A1T center metal3
select clear
select no labels
box values 44350 8675 44400 8725
label N0 center metal3
select clear
select no labels
box values 44350 8975 44400 9025
label N1 center metal3
select clear
select no labels
box values 44350 9275 44400 9325
label N2 center metal3
select clear
select no labels
box values 44350 9575 44400 9625
label N3 center metal3
select clear
select no labels
box values 44350 9875 44400 9925
label net1 center metal3
select clear
select no labels
box values 44350 10175 44400 10225
label net2 center metal3
select clear
select no labels
box values 44350 10475 44400 10525
label net3 center metal3
select clear
select no labels
box values 44350 10775 44400 10825
label net4 center metal3
select clear
select no labels
box values 44350 11075 44400 11125
label EVAL_GND center metal3
select clear
select no labels
box values 475 11375 525 11425
label DEC0 center metal3
select clear
select do labels
select area metal3
port make 4 n
select clear
select no labels
box values 475 11675 525 11725
label DEC1 center metal3
select clear
select do labels
select area metal3
port make 5 n
select clear
select no labels
box values 475 11975 525 12025
label DEC2 center metal3
select clear
select do labels
select area metal3
port make 7 n
select clear
select no labels
box values 475 12275 525 12325
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
