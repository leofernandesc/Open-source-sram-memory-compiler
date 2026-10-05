# Flatten the routed sense-amplifier PCells for physical verification.
load sense_amp_layout
save sense_amp_routed_hier
flatten sense_amp_flat
load sense_amp_flat
drc check
drc count total
save sense_amp_flat
quit -noprompt
