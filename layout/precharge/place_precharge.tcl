# Re-place the three imported PMOS devices on one well-separated row.
load precharge_import
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

# Imported centers are XMPBL=(158,-1392), XMPBLB=(527,-1445),
# XMEQ=(896,-1498).  Place all three at y=-1000.
move_inst XMPBL   142 392
move_inst XMPBLB  573 445
move_inst XMEQ   1004 498

drc check
drc count total
save precharge_placed
quit -noprompt
