load write_driver_w5p04_flat
select top cell
extract do local
extract all
ext2spice lvs
ext2spice -o write_driver_w5p04_flat_extracted.spice
quit -noprompt
