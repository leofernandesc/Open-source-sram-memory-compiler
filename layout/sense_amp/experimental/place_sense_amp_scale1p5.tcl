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

move_inst XMP1       142  1045
move_inst XMP2       204  1151
move_inst XMSAMPBL   266  1246
move_inst XMSAMPBLB  697  1299
move_inst XMN1        73  -802
move_inst XMN2       235  -696
move_inst XMTAIL      28  -537

drc check
puts "SCALE1P5_PLACE_DRC_BEGIN"
drc count total
puts "SCALE1P5_PLACE_DRC_END"
save sense_amp_scale1p5_placed
quit -noprompt
