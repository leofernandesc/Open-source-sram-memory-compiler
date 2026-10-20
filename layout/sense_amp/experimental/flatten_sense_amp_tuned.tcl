load sense_amp_tuned
save sense_amp_tuned_routed_hier
flatten sense_amp_tuned_flat
load sense_amp_tuned_flat
drc check
drc count total
save sense_amp_tuned_flat
quit -noprompt
