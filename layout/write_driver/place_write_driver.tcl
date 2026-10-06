load write_driver_import
snap internal

proc move_inst {name dx dy} {
    select clear
    select cell $name
    if {$dx > 0} { move e $dx }
    if {$dx < 0} { move w [expr {-$dx}] }
    if {$dy > 0} { move n $dy }
    if {$dy < 0} { move s [expr {-$dy}] }
    select clear
}

# PMOS row, y=-1000.
move_inst XMPWEB    142 1150
move_inst XMPENBL   204 1256
move_inst XMPDBL    635 1309
move_inst XMPENBLB  328 1468
move_inst XMPDBLB   759 1521

# NMOS row, y=-5000.
move_inst XMNWEB     73 -2788
move_inst XMNDBL   -234 -2629
move_inst XMNENBL   197 -2576
move_inst XMNDBLB  -110 -2417
move_inst XMNENBLB  321 -2364

drc check
drc count total
save write_driver_placed
quit -noprompt
