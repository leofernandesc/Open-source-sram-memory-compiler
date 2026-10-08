# Abutment smoke for the routed 6T bitcell.
# Checks same-orientation and horizontally mirrored neighbors at zero gap.

load bitcell_6t_routed_hier

# Routed bitcell bbox: (-450,-2942) .. (3000,-358), width=3450 internal units.
set llx -450
set lly -2942
set pitch 3450

load bitcell_6t_abutment_same
getcell bitcell_6t_routed_hier child $llx $lly parent 0 0
getcell bitcell_6t_routed_hier child $llx $lly parent $pitch 0
drc euclidean on
drc style drc(full)
drc on
select top cell
expand
box select
drc check
drc catchup
puts "ABUTMENT_SAME_DRC_BEGIN"
set same_errors 0
foreach {rule boxes} [drc listall why] { incr same_errors [llength $boxes] }
puts "ABUTMENT_SAME_DRC_ERRORS=$same_errors"
puts "ABUTMENT_SAME_DRC_END"
if {$same_errors != 0} { error "same-orientation abutment DRC failed" }
save bitcell_6t_abutment_same

load bitcell_6t_abutment_mirror
getcell bitcell_6t_routed_hier child $llx $lly parent 0 0
getcell bitcell_6t_routed_hier child $llx $lly parent $pitch 0
select clear
select cell bitcell_6t_routed_hier_1
box select
sideways
select clear
select top cell
expand
box select
drc check
drc catchup
puts "ABUTMENT_MIRROR_DRC_BEGIN"
set mirror_errors 0
foreach {rule boxes} [drc listall why] { incr mirror_errors [llength $boxes] }
puts "ABUTMENT_MIRROR_DRC_ERRORS=$mirror_errors"
puts "ABUTMENT_MIRROR_DRC_END"
if {$mirror_errors != 0} { error "mirrored abutment DRC failed" }
save bitcell_6t_abutment_mirror

quit -noprompt
