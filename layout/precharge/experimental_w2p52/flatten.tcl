load precharge_w2p52
save precharge_w2p52_routed_hier
flatten precharge_w2p52_flat
load precharge_w2p52_flat
drc euclidean on
drc style drc(full)
drc on
select top cell
expand
box select
drc check
drc catchup
puts "PRECH_W2P52_FLAT_DRC_BEGIN"
drc count total
set flat_drc_rules [drc listall why]
puts "PRECH_W2P52_FLAT_DRC_RULE_GROUPS=[llength $flat_drc_rules]"
puts "PRECH_W2P52_FLAT_DRC_END"
if {[llength $flat_drc_rules] > 0} {
    error "precharge_w2p52_flat fails drc(full): $flat_drc_rules"
}
save precharge_w2p52_flat
quit -noprompt
