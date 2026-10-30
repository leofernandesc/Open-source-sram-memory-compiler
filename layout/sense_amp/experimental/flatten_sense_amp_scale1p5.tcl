load sense_amp_scale1p5
save sense_amp_scale1p5_routed_hier
flatten sense_amp_scale1p5_flat
load sense_amp_scale1p5_flat
drc euclidean on
drc style drc(full)
drc on
select top cell
expand
box select
drc check
drc catchup
puts "SCALE1P5_FLAT_DRC_BEGIN"
drc count total
set flat_drc_rules [drc listall why]
puts "SCALE1P5_FLAT_DRC_RULE_GROUPS=[llength $flat_drc_rules]"
puts "SCALE1P5_FLAT_DRC_END"
if {[llength $flat_drc_rules] > 0} {
    error "sense_amp_scale1p5_flat fails drc(full): $flat_drc_rules"
}
save sense_amp_scale1p5_flat
quit -noprompt
