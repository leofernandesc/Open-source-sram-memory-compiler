load sense_amp_balanced_flat
select top cell
extract do local
extract all
ext2spice lvs
ext2spice -o sense_amp_balanced_flat_extracted.spice
quit -noprompt
