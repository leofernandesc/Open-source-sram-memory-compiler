snap internal
path search +.
load array_2x2_abut
proc rect {layer x1 y1 x2 y2} {
    box values $x1 $y1 $x2 $y2
    paint $layer
}
proc promote34 {x y} {
    rect metal3 [expr {$x-48}] [expr {$y-48}] [expr {$x+48}] [expr {$y+48}]
    rect metal4 [expr {$x-60}] [expr {$y-48}] [expr {$x+60}] [expr {$y+48}]
    box values [expr {$x-32}] [expr {$y-32}] [expr {$x+32}] [expr {$y+32}]
    contact via3
}
proc via12 {x y} {
    rect metal1 [expr {$x-34}] [expr {$y-34}] [expr {$x+34}] [expr {$y+34}]
    rect metal2 [expr {$x-34}] [expr {$y-34}] [expr {$x+34}] [expr {$y+34}]
    box values [expr {$x-26}] [expr {$y-26}] [expr {$x+26}] [expr {$y+26}]
    contact via1
}
proc via23 {x y} {
    rect metal2 [expr {$x-48}] [expr {$y-48}] [expr {$x+48}] [expr {$y+48}]
    rect metal3 [expr {$x-60}] [expr {$y-48}] [expr {$x+60}] [expr {$y+48}]
    box values [expr {$x-30}] [expr {$y-30}] [expr {$x+30}] [expr {$y+30}]
    contact via2
}
proc pin {name index x y} {
    box values [expr {$x-20}] [expr {$y-20}] [expr {$x+20}] [expr {$y+20}]
    label $name center metal4
    port make $index n
}
getcell bitcell_6t_abut child 0 0 parent 0 0
getcell bitcell_6t_abut child 0 0 parent 3450 0
getcell bitcell_6t_abut child 0 0 parent 0 2800
getcell bitcell_6t_abut child 0 0 parent 3450 2800
rect metal4 2940 90 2960 110
box values 2940 90 2960 110
label VDD center metal4
port make 0 n
rect metal4 3140 90 3160 110
box values 3140 90 3160 110
label VSS center metal4
port make 1 n
rect metal3 90 440 110 460
box values 90 440 110 460
label WL0 center metal3
port make 2 n
rect metal3 90 3240 110 3260
box values 90 3240 110 3260
label WL1 center metal3
port make 3 n
rect metal4 1840 90 1860 110
box values 1840 90 1860 110
label BL0 center metal4
port make 4 n
rect metal4 2520 90 2540 110
box values 2520 90 2540 110
label BLB0 center metal4
port make 5 n
rect metal4 5290 90 5310 110
box values 5290 90 5310 110
label BL1 center metal4
port make 6 n
rect metal4 5970 90 5990 110
box values 5970 90 5990 110
label BLB1 center metal4
port make 7 n
save array_2x2_abut

save array_2x2_abut
select top cell
expand
flatten array_2x2_abut_flat
load array_2x2_abut_flat
select top cell
expand
drc euclidean on
drc style drc(full)
drc on
drc check
drc catchup
puts "ABUT_DRC=[llength [drc listall why]]"
puts "ABUT_DETAILS=[drc listall why]"
save array_2x2_abut_flat
load array_2x2_abut
gds write array_2x2_abut.gds
load array_2x2_abut_flat
extract all
ext2spice lvs
ext2spice scale off
ext2spice -o extracted.spice
quit -noprompt
