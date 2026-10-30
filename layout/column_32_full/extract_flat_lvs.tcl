load column_32_full_v2_flat
select top cell

extract do local
extract all

ext2spice lvs
ext2spice -o column_32_full_v2_flat_extracted.spice

quit -noprompt
