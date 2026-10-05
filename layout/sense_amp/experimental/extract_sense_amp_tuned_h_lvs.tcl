load sense_amp_tuned_h_flat
select top cell
extract do local
extract all
ext2spice lvs
ext2spice -o sense_amp_tuned_h_flat_extracted.spice
quit -noprompt
