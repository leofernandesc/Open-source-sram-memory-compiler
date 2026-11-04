snap internal
path search +.
path search +/opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd/mag
load pilot
getcell wl_driver child 0 0 parent 600 4000
getcell sky130_fd_sc_hd__inv_1 child 0 0 parent 5000 2500
getcell sky130_fd_sc_hd__tapvpwrvgnd_1 child 0 0 parent 4908 2500
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
# Custom labels are at x=-230 before placement, on five distinct M3 bars.
foreach {y name idx} {3700 VDD 1 400 VSS 2 3500 IN 3 1800 LINK 0} {
    promote34 370 $y
}
# Stagger contact layers: overlapping different Magic contact types would
# cut holes in the contacts. Escape LI -> M1 -> M2 -> M3 -> M4 separately.
rect locali 4883 2721 5106 2755
rect locali 5164 2789 5417 2823
foreach {x y} {4900 2738 5400 2806} {
    rect metal1 [expr {$x-32}] [expr {$y-32}] [expr {$x+32}] [expr {$y+32}]
    box values [expr {$x-17}] [expr {$y-17}] [expr {$x+17}] [expr {$y+17}]
    contact mcon
}
rect metal1 4766 2712 4926 2764
rect metal1 5374 2780 5534 2832
via12 4800 2738
via12 5500 2806
rect metal2 4466 2704 4834 2772
rect metal2 5466 2772 5834 2840
via23 4500 2738
via23 5800 2806
rect metal3 4240 2690 4560 2786
rect metal3 5740 2758 6060 2854
promote34 4300 2738
promote34 6000 2806
# Tap and inverter share abutting M1 power rails and well ties.
foreach {y escapeY customY} {3044 3300 3700 2500 2200 400} {
    rect metal1 5200 [expr {$y-34}] 6534 [expr {$y+34}]
    via12 6500 $y
    rect metal2 6466 [expr {min($y,$escapeY)-34}] 6534 [expr {max($y,$escapeY)+34}]
    via23 6500 $escapeY
    rect metal3 6440 [expr {$escapeY-48}] 6860 [expr {$escapeY+48}]
    promote34 6800 $escapeY
    rect metal4 6752 [expr {min($escapeY,$customY)-48}] 6848 [expr {max($escapeY,$customY)+48}]
    rect metal4 322 [expr {$customY-48}] 6848 [expr {$customY+48}]
}
rect metal4 322 1752 4348 1848
rect metal4 4252 1752 4348 2786
pin VDD 1 370 3700
pin VSS 2 370 400
pin IN 3 370 3500
pin OUT 4 6000 2806
select top cell
expand
flatten pilot_flat
load pilot_flat
select top cell
expand
drc euclidean on
drc style drc(full)
drc on
drc check
drc catchup
puts "PILOT_DRC=[llength [drc listall why]]"
puts "PILOT_DETAILS=[drc listall why]"
save pilot_flat
# Keep original HD GDS references when streaming the hierarchical pilot.
load pilot
gds write pilot.gds
load pilot_flat
extract all
ext2spice lvs
ext2spice scale off
ext2spice -o pilot_extracted.spice
quit -noprompt
