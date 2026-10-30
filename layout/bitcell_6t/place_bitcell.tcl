load __bitcell_6t_placed_scratch__
snap internal

# Build a fresh parent so no placeholder pins, stale error paint, or geometry
# from a previous netlist_to_layout run can leak into the sign-off candidate.
getcell bitcell_6t_pu_device  child 0 0 parent  200 -1000
getcell bitcell_6t_pu_device  child 0 0 parent  900 -1000
getcell bitcell_6t_pd_device  child 0 0 parent  200 -1900
getcell bitcell_6t_pd_device  child 0 0 parent  800 -1900
getcell bitcell_6t_acc_device child 0 0 parent 1400 -1900
getcell bitcell_6t_acc_device child 0 0 parent 2000 -1900

drc euclidean on
drc style drc(full)
drc on
select top cell
expand
drc catchup
puts "BITCELL_PLACE_DRC_ERRORS=[llength [drc listall why]]"

save bitcell_6t_placed
quit -noprompt
