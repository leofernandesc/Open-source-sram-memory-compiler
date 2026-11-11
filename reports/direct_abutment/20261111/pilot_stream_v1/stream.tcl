gds read /work/reports/direct_abutment/20261111/pilot_v2/array_2x2_abut.gds
load array_2x2_abut
select top cell
expand
flatten stream_flat
load stream_flat
drc euclidean on
drc style drc(full)
drc on
drc check
drc catchup
puts "STREAM_DRC=[llength [drc listall why]]"
puts "STREAM_DETAILS=[drc listall why]"
save stream_flat
extract all
ext2spice lvs
ext2spice scale off
ext2spice -o /work/reports/direct_abutment/20261111/pilot_stream_v1/stream_extracted.spice
quit -noprompt
