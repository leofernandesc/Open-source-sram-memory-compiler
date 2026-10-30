load column_32_full_g7_wpre2p52_flat
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
ext2spice -o pex/column_32_full_g7_wpre2p52_pex.spice
quit -noprompt
