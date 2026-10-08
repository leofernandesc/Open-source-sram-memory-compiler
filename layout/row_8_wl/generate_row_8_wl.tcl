path search +../bitcell_6t
load row_8_wl
box values -100000 -100000 100000 100000
select area
delete
select clear
snap internal
set llx -450
set lly -2942
# Repaired bitcell bbox is 3450 units wide.  Keep a 60-unit horizontal
# channel between adjacent cells instead of overlapping the new geometry.
set pitch_x 3510
set cols 8
set x_port_offset 220
set y_bl 192
set y_blb 42
set y_vss 492
set y_vdd 2542
set y_wl 342
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
  # Five rails are 150 units apart.  Adjacent landings need a 60-unit gap.
  box values [expr {$x - 45}] [expr {$y - 45}] [expr {$x + 45}] [expr {$y + 45}]
  paint metal3
  # Broaden M4 horizontally to satisfy its 9600-unit minimum area.
  box values [expr {$x - 60}] [expr {$y - 45}] [expr {$x + 60}] [expr {$y + 45}]
  paint metal4
  box values [expr {$x - 32}] [expr {$y - 32}] [expr {$x + 32}] [expr {$y + 32}]
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
for {set col 0} {$col < $cols} {incr col} {
  set x [expr {$col * $pitch_x + $x_port_offset}]
  set bl_index [expr {3 + 2 * $col}]
  set blb_index [expr {$bl_index + 1}]
  make_m4_port "BL${col}" $bl_index $x $y_bl
  make_m4_port "BLB${col}" $blb_index $x $y_blb
}

drc euclidean on
drc style drc(full)
drc on
select top cell
expand
box select
drc check
drc catchup
set row8_hier_errors 0
foreach {rule boxes} [drc listall why] {
  puts "ROW8_WL_HIER_DRC_RULE=$rule BOXES=[llength $boxes]"
  if {[llength $boxes] > 0} { puts "ROW8_WL_HIER_DRC_SAMPLES=[lrange $boxes 0 9]" }
  incr row8_hier_errors [llength $boxes]
}
puts "ROW8_WL_HIER_DRC_ERRORS=$row8_hier_errors"
if {$row8_hier_errors != 0} { error "row_8_wl hierarchical DRC failed" }
save row_8_wl
flatten row_8_wl_flat
load row_8_wl_flat
select top cell
expand
box select
drc check
drc catchup
set row8_flat_errors 0
foreach {rule boxes} [drc listall why] {
  puts "ROW8_WL_FLAT_DRC_RULE=$rule BOXES=[llength $boxes]"
  incr row8_flat_errors [llength $boxes]
}
puts "ROW8_WL_FLAT_DRC_ERRORS=$row8_flat_errors"
if {$row8_flat_errors != 0} { error "row_8_wl flat DRC failed" }
save row_8_wl_flat
quit -noprompt
