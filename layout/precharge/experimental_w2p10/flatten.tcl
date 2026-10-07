load precharge_w2p10
save precharge_w2p10_routed_hier
flatten precharge_w2p10_flat
load precharge_w2p10_flat
drc check
puts "PRECH_W2P10_FLAT_DRC_BEGIN"
drc count total
puts "PRECH_W2P10_FLAT_DRC_END"
save precharge_w2p10_flat
quit -noprompt
