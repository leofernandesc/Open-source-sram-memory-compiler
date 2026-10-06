load wl_driver_flat
select top cell
extract do local
extract all
ext2spice lvs
ext2spice -o wl_driver_flat_extracted.spice
quit -noprompt
