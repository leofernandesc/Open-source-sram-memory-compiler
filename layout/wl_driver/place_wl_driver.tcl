load wl_driver_import
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

# PMOS row.
move_inst XMP1 142   -8
move_inst XMP2 604   56

# NMOS row.
move_inst XMN1  73 -1946
move_inst XMN2 535 -1882

drc check
drc count total
save wl_driver_placed
quit -noprompt
