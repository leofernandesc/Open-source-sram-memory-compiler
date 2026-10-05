load bitcell_6t_flat
select top cell

extract do local
extract all

ext2spice lvs
ext2spice -o bitcell_6t_flat_extracted.spice

quit -noprompt
