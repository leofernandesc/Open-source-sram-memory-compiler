load bitcell_6t
select top cell
expand
drc euclidean on
drc style drc(full)
drc on
drc check
drc catchup
set findings [drc listall why]
puts "PHASE1_DRC_GROUPS=[llength $findings]"
puts "PHASE1_DRC_DETAILS=$findings"
extract do local
extract all
ext2spice lvs
ext2spice scale off
ext2spice -o /work/sims/integration/results/reconciliation_20261030/physical/verification/bitcell_6t/layout_extracted.spice
quit -noprompt
