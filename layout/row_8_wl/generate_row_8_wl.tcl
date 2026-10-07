path search +../bitcell_6t
load row_8_wl
snap internal
set llx -450
set lly -2470
set pitch_x 3110
set cols 8
set x_port_offset 220
set y_bl 150
set y_blb 30
set y_vss 390
set y_vdd 1710
set y_wl 270
for {set col 0} {$col < $cols} {incr col} {
  set x [expr {$col * $pitch_x}]
  getcell bitcell_6t_flat child $llx $lly parent $x 0
}
set row_right [expr {$cols * $pitch_x}]
proc m4_hrail {y xlo xhi} {
  box values $xlo [expr {$y - 40}] $xhi [expr {$y + 40}]
  paint metal4
}
proc m3_to_m4 {x y} {
  box values [expr {$x - 40}] [expr {$y - 40}] [expr {$x + 40}] [expr {$y + 40}]
  paint metal3
  paint metal4
  contact via3
}
proc make_m4_port {name index x y} {
  box values [expr {$x - 30}] [expr {$y - 30}] [expr {$x + 30}] [expr {$y + 30}]
  label $name center metal4
  select clear
  select do labels
  select area metal4
  port make $index n
  select clear
  select no labels
}
m4_hrail $y_vdd -80 [expr {$row_right + 80}]
m4_hrail $y_vss -80 [expr {$row_right + 80}]
m4_hrail $y_wl  -80 [expr {$row_right + 80}]
for {set col 0} {$col < $cols} {incr col} {
  set x [expr {$col * $pitch_x + $x_port_offset}]
  m3_to_m4 $x $y_vdd
  m3_to_m4 $x $y_vss
  m3_to_m4 $x $y_wl
  m3_to_m4 $x $y_bl
  m3_to_m4 $x $y_blb
}
make_m4_port VDD 0 -40 $y_vdd
make_m4_port VSS 1 -40 $y_vss
make_m4_port WL  2 -40 $y_wl
make_m4_port BL0 3 220 $y_bl
make_m4_port BLB0 4 220 $y_blb
make_m4_port BL1 5 3330 $y_bl
make_m4_port BLB1 6 3330 $y_blb
make_m4_port BL2 7 6440 $y_bl
make_m4_port BLB2 8 6440 $y_blb
make_m4_port BL3 9 9550 $y_bl
make_m4_port BLB3 10 9550 $y_blb
make_m4_port BL4 11 12660 $y_bl
make_m4_port BLB4 12 12660 $y_blb
make_m4_port BL5 13 15770 $y_bl
make_m4_port BLB5 14 15770 $y_blb
make_m4_port BL6 15 18880 $y_bl
make_m4_port BLB6 16 18880 $y_blb
make_m4_port BL7 17 21990 $y_bl
make_m4_port BLB7 18 21990 $y_blb
drc check
puts "ROW8_WL_HIER_DRC_BEGIN"
drc count total
puts "ROW8_WL_HIER_DRC_END"
save row_8_wl
flatten row_8_wl_flat
load row_8_wl_flat
drc check
puts "ROW8_WL_FLAT_DRC_BEGIN"
drc count total
puts "ROW8_WL_FLAT_DRC_END"
save row_8_wl_flat
quit -noprompt
