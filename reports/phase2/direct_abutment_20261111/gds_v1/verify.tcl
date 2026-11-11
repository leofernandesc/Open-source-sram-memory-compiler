gds read /work/build/phase2/gds-check-45g222z3/sram_4x8.gds
load sram_4x8_wrapper
select top cell
expand
flatten final_flat
load final_flat
select top cell
expand
drc euclidean on
drc style drc(full)
drc on
drc check
drc catchup
puts "FINAL_GDS_DRC=[llength [drc listall why]]"
puts "FINAL_GDS_DETAILS=[drc listall why]"
save final_flat
extract all
ext2spice lvs
ext2spice scale off
ext2spice -o /work/build/phase2/gds-check-45g222z3/final_extracted.spice
quit -noprompt
