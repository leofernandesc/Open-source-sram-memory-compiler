if {![info exists ::env(PEX_CELL)]} {
    error "PEX_CELL is required"
}
if {![info exists ::env(PEX_OUT)]} {
    error "PEX_OUT is required"
}

set cell $::env(PEX_CELL)
set flat_cell "${cell}_flat"
set out_file $::env(PEX_OUT)

load $flat_cell
select top cell

extract do local
extract all

ext2sim labels on
ext2sim

# Extract distributed wire resistance before exporting SPICE.
extresist tolerance 1
extresist simplify on
extresist all

ext2spice hierarchy off
ext2spice format ngspice
ext2spice subcircuits top on
ext2spice cthresh 0
ext2spice rthresh 0
ext2spice extresist on
ext2spice -o $out_file

quit -noprompt
