load write_driver_w5p04_import
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
move_inst XMPWEB 142 1150
move_inst XMPENBL 204 836
move_inst XMPDBL 635 889
move_inst XMPENBLB 328 1048
move_inst XMPDBLB 759 1101
move_inst XMNWEB 73 -2788
move_inst XMNDBL -234 -3049
move_inst XMNENBL 197 -2996
move_inst XMNDBLB -110 -2837
move_inst XMNENBLB 321 -2784
drc check
puts "WRITE_W5P04_PLACE_DRC_BEGIN"
drc count total
puts "WRITE_W5P04_PLACE_DRC_END"
save write_driver_w5p04_placed
quit -noprompt
