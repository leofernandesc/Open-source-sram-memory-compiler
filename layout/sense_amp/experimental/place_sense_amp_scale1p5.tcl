load sense_amp_scale1p5_import
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

move_inst XMP1       195  1416
move_inst XMP2       257  1522
move_inst XMSAMPBL   319  1617
move_inst XMSAMPBLB  750  1670
move_inst XMN1       126  -431
move_inst XMN2       288  -325
move_inst XMTAIL      81  -166

drc check
puts "SCALE1P5_PLACE_DRC_BEGIN"
drc count total
puts "SCALE1P5_PLACE_DRC_END"
save sense_amp_scale1p5_placed
quit -noprompt
