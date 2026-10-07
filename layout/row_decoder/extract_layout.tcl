load row_decoder_flat
select top cell
extract do local
extract all
ext2sim labels on
ext2sim
extresist
ext2spice lvs
ext2spice -o row_decoder_flat_extracted.spice
ext2spice default
ext2spice extresist on
ext2spice cthresh 0
ext2spice rthresh 0
ext2spice -o pex/row_decoder_pex.spice
quit -noprompt
