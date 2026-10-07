load row_decoder_layout
save row_decoder_routed_hier
flatten row_decoder_flat
load row_decoder_flat
select top cell
drc check
drc count total
save row_decoder_flat
quit -noprompt
