load precharge_w2p10_import
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
move_inst XMPBL 142 224
move_inst XMPBLB 573 277
move_inst XMEQ 1004 330
drc check
puts "PRECH_W2P10_PLACE_DRC_BEGIN"
drc count total
puts "PRECH_W2P10_PLACE_DRC_END"
save precharge_w2p10_placed
quit -noprompt
