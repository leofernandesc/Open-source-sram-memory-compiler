snap internal
path search +.
load bitcell_6t_abut
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
rect metal3 0 2608 3450 2692
rect metal3 0 558 3450 642
rect metal3 0 408 3450 492
rect metal3 870 2458 2110 2542
rect metal3 230 2308 2750 2392
rect metal3 1630 252 1910 348
rect metal3 2250 102 2590 198
promote34 2950 2650
rect metal4 2890 0 3010 2800
promote34 3150 600
rect metal4 3090 0 3210 2800
promote34 1850 300
rect metal4 1790 0 1910 2800
promote34 2530 150
rect metal4 2470 0 2590 2800
box values 2938 88 2962 112
label VDD center metal4
port make 0 n
box values 1838 88 1862 112
label BL center metal4
port make 1 n
box values 2518 88 2542 112
label BLB center metal4
port make 2 n
box values 3138 88 3162 112
label VSS center metal4
port make 3 n
box values 88 438 112 462
label WL center metal3
port make 4 n
property FIXED_BBOX "0 0 3450 2800"

select top cell
expand
flatten bitcell_6t_abut_flat
load bitcell_6t_abut_flat
select top cell
expand
drc euclidean on
drc style drc(full)
drc on
drc check
drc catchup
puts "ABUT_DRC=[llength [drc listall why]]"
puts "ABUT_DETAILS=[drc listall why]"
save bitcell_6t_abut_flat
load bitcell_6t_abut
gds write bitcell_6t_abut.gds
load bitcell_6t_abut_flat
extract all
ext2spice lvs
ext2spice scale off
ext2spice -o extracted.spice
quit -noprompt
