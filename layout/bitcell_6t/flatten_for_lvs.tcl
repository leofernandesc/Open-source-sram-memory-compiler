# Flatten the routed PCells so parent metal can connect directly to device
# terminal geometry during extraction.  Keep the hierarchical routed copy for
# debugging and use bitcell_6t_flat as the LVS candidate.

load bitcell_6t
save bitcell_6t_routed_hier
flatten bitcell_6t_flat
load bitcell_6t_flat
snap internal

# Magic's SKY130 PCell generator centers L=0.15um around x=0 while the
# generated child cell is stored on a 10nm grid.  That rounds the two gate
# edges inward and the flattened geometry extracts as L=0.14um.  After
# flattening, Magic has a 5nm internal grid, so restore the intended 150nm
# physical gate length symmetrically (5nm per side) before DRC/LVS/PEX.
proc restore_l015 {type xlo ylo xhi yhi} {
    box values [expr {$xlo - 1}] $ylo [expr {$xhi + 1}] $yhi
    paint $type
}

# Pull-down NMOS pair.
restore_l015 nmos 186 -2026 214 -1774
restore_l015 nmos 786 -2026 814 -1774

# Access NMOS pair.
restore_l015 nmos 1386 -1960 1414 -1840
restore_l015 nmos 1986 -1960 2014 -1840

# Pull-up PMOS pair.
restore_l015 pmos 186 -1042 214 -958
restore_l015 pmos 886 -1042 914 -958

drc euclidean on
drc style drc(full)
drc on
select top cell
drc catchup
set bitcell_flat_errors [drc listall why]
puts "BITCELL_FLAT_DRC_ERRORS=[llength $bitcell_flat_errors]"
if {[llength $bitcell_flat_errors] > 0} {
    puts "BITCELL_FLAT_DRC_DETAIL=$bitcell_flat_errors"
}
save bitcell_6t_flat
quit -noprompt
