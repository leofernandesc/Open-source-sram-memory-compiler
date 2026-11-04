path search +/opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd/mag
gds read /work/build/phase2/finish-u97mmwui/leaf_fabric.gds
load leaf_fabric
lef read /work/build/phase2/finish-u97mmwui/leaf_fabric.lef -annotate
lef read /work/build/phase2/finish-u97mmwui/used_cells.lef -import
def read /work/build/phase2/finish-u97mmwui/final.def
load sram_4x8_wrapper
select top cell
expand
gds write /work/build/phase2/finish-u97mmwui/sram_4x8.gds
save sram_4x8_wrapper
flatten integrated_flat
load integrated_flat
select top cell
expand
drc euclidean on
drc style drc(full)
drc on
drc check
drc catchup
puts "INTEGRATED_DRC=[llength [drc listall why]]"
puts "INTEGRATED_DETAILS=[drc listall why]"
save integrated_flat
extract all
ext2spice lvs
ext2spice scale off
ext2spice -o /work/build/phase2/finish-u97mmwui/integrated_extracted.spice
quit -noprompt
