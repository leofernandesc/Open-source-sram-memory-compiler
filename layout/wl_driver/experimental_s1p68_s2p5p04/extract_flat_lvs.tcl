load wl_driver_s1p68_s2p5p04_flat
select top cell
extract do local
extract all
ext2spice lvs
ext2spice -o wl_driver_s1p68_s2p5p04_flat_extracted.spice
quit -noprompt
