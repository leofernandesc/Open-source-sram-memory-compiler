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
move_inst XMPWEB 195 1680
move_inst XMPENBL 257 1366
move_inst XMPDBL 688 1419
move_inst XMPENBLB 381 1578
move_inst XMPDBLB 812 1631
move_inst XMNWEB 126 -2258
move_inst XMNDBL -181 -2519
move_inst XMNENBL 250 -2466
move_inst XMNDBLB -57 -2307
move_inst XMNENBLB 374 -2254
drc check
puts "WRITE_W5P04_PLACE_DRC_BEGIN"
drc count total
puts "WRITE_W5P04_PLACE_DRC_END"
save write_driver_w5p04_placed
quit -noprompt
