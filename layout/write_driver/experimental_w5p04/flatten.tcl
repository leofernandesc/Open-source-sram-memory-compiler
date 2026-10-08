load write_driver_w5p04
save write_driver_w5p04_routed_hier
flatten write_driver_w5p04_flat
load write_driver_w5p04_flat
drc euclidean on
drc style drc(full)
drc on
select top cell
expand
box select
drc check
drc catchup
puts "WRITE_W5P04_FLAT_DRC_BEGIN"
drc count total
set flat_drc_rules [drc listall why]
puts "WRITE_W5P04_FLAT_DRC_RULE_GROUPS=[llength $flat_drc_rules]"
puts "WRITE_W5P04_FLAT_DRC_END"
if {[llength $flat_drc_rules] > 0} {
    error "write_driver_w5p04_flat fails drc(full): $flat_drc_rules"
}
save write_driver_w5p04_flat
quit -noprompt
