load wl_driver_s1p68_s2p5p04_layout
save wl_driver_s1p68_s2p5p04_routed_hier
flatten wl_driver_s1p68_s2p5p04_flat
load wl_driver_s1p68_s2p5p04_flat
drc euclidean on
drc style drc(full)
drc on
select top cell
expand
box select
drc check
drc catchup
puts "WL_DRIVER_FLAT_DRC_BEGIN"
drc count total
set flat_drc_rules [drc listall why]
puts "WL_DRIVER_FLAT_DRC_RULE_GROUPS=[llength $flat_drc_rules]"
puts "WL_DRIVER_FLAT_DRC_END"
if {[llength $flat_drc_rules] > 0} {
    error "wl_driver_s1p68_s2p5p04_flat fails drc(full): $flat_drc_rules"
}
save wl_driver_s1p68_s2p5p04_flat
quit -noprompt
