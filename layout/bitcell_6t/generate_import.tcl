# Initial SKY130A physical scaffold for the frozen 6T bitcell.
#
# This intentionally stops before routing.  It imports the canonical SPICE
# netlist through Magic's SKY130 PCell generator so transistor geometry stays
# tied to WPU/WPD/WACC = 0.42/1.26/0.60 um.  DRC/LVS closure is a separate gate.

set project_root "/work"
set netlist "$project_root/cells/bitcell_6t.spice"

magic::netlist_to_layout $netlist sky130
save bitcell_6t_import

select top cell
box select
puts "BITCELL_IMPORT_BBOX=[box values]"

drc check
drc count total

writeall force
quit -noprompt
