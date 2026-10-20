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
move_inst XMP1 195    78
move_inst XMP2 657  -152
move_inst XMN1 126 -1860
move_inst XMN2 588 -2090

drc check
drc count total
save wl_driver_s1p68_s2p5p04_placed
quit -noprompt
