load precharge_w2p52_flat
select top cell
extract do local
extract all
ext2spice lvs
ext2spice -o precharge_w2p52_flat_extracted.spice
quit -noprompt
