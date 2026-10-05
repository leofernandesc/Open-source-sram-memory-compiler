# Re-place the imported devices into separate PMOS/NMOS rows so wells and
# guard rings do not overlap across opposite device types.
load sense_amp_import
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

# PMOS row: y=-1000.
move_inst XMP1       142  1108
move_inst XMP2       204  1214
move_inst XMSAMPBL   266  1246
move_inst XMSAMPBLB  697  1299

# NMOS row: y=-3000.
move_inst XMN1        73  -769
move_inst XMN2       235  -663
move_inst XMTAIL      28  -504

drc check
drc count total
save sense_amp_placed
quit -noprompt
