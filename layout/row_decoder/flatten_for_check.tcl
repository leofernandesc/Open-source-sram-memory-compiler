load row_decoder_layout
save row_decoder_routed_hier
flatten row_decoder_flat
load row_decoder_flat
select top cell
drc style drc(full)
drc check
drc catchup
drc count total
save row_decoder_flat
quit -noprompt
