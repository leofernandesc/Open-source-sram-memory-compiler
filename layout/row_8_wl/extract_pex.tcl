load row_8_wl_flat
select top cell
extract do local
extract all
ext2sim labels on
ext2sim
extresist tolerance 1
extresist simplify on
extresist all
ext2spice hierarchy off
ext2spice format ngspice
ext2spice subcircuits top on
ext2spice cthresh 0
ext2spice rthresh 0
ext2spice extresist on
ext2spice -o pex/row_8_wl_pex.spice
quit -noprompt
