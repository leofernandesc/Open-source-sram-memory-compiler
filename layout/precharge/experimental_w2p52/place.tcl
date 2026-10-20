load precharge_w2p52_import
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
move_inst XMPBL 195 341
move_inst XMPBLB 626 394
move_inst XMEQ 1057 447
drc check
puts "PRECH_W2P52_PLACE_DRC_BEGIN"
drc count total
puts "PRECH_W2P52_PLACE_DRC_END"
save precharge_w2p52_placed
quit -noprompt
