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
restore_l015 nmos 882  -1549 910  -1297
restore_l015 nmos 1251 -1602 1279 -1350

# Access NMOS pair.
restore_l015 nmos 1620 -1655 1648 -1535
restore_l015 nmos 1989 -1708 2017 -1588

# Pull-up PMOS pair.
restore_l015 pmos 144 -1434 172 -1350
restore_l015 pmos 513 -1487 541 -1403

drc check
drc count total
save bitcell_6t_flat
quit -noprompt
