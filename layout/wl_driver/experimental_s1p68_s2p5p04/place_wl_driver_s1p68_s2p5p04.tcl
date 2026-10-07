load wl_driver_s1p68_s2p5p04_import
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

# Keep the same logical centers as the canonical WL driver so the external
# rail/port geometry remains stable while the device widths change.
move_inst XMP1 142  -134
move_inst XMP2 604  -364
move_inst XMN1  73 -2072
move_inst XMN2 535 -2302

drc check
drc count total
save wl_driver_s1p68_s2p5p04_placed
quit -noprompt
