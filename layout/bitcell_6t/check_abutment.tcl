# Abutment smoke for the routed 6T bitcell.
# Checks same-orientation and horizontally mirrored neighbors at zero gap.

load bitcell_6t_routed_hier

# Routed bitcell bbox: (-450,-2470) .. (2600,-730), width=3050 internal units.
set llx -450
set lly -2470
set pitch 3050

load bitcell_6t_abutment_same
getcell bitcell_6t_routed_hier child $llx $lly parent 0 0
getcell bitcell_6t_routed_hier child $llx $lly parent $pitch 0
drc check
puts "ABUTMENT_SAME_DRC_BEGIN"
drc count total
puts "ABUTMENT_SAME_DRC_END"
save bitcell_6t_abutment_same

load bitcell_6t_abutment_mirror
getcell bitcell_6t_routed_hier child $llx $lly parent 0 0
getcell bitcell_6t_routed_hier child $llx $lly parent $pitch 0
select clear
select cell bitcell_6t_routed_hier_1
box select
sideways
select clear
drc check
puts "ABUTMENT_MIRROR_DRC_BEGIN"
drc count total
puts "ABUTMENT_MIRROR_DRC_END"
save bitcell_6t_abutment_mirror

quit -noprompt
