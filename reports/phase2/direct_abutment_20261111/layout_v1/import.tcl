path search +/opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd/mag
lef read /opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef
gds read /work/build/phase2/finish-yqqyjrug/leaf_fabric.gds
load leaf_fabric
lef read /work/build/phase2/finish-yqqyjrug/leaf_fabric.lef -annotate
load sky130_fd_sc_hd__and2_1
load sky130_fd_sc_hd__and2_4
load sky130_fd_sc_hd__and3_2
load sky130_fd_sc_hd__and3_4
load sky130_fd_sc_hd__clkbuf_2
load sky130_fd_sc_hd__clkinv_1
load sky130_fd_sc_hd__dfxtp_1
load sky130_fd_sc_hd__ebufn_1
load sky130_fd_sc_hd__fill_1
load sky130_fd_sc_hd__fill_2
load sky130_fd_sc_hd__fill_4
load sky130_fd_sc_hd__fill_8
load sky130_fd_sc_hd__inv_1
load sky130_fd_sc_hd__mux2_1
load sky130_fd_sc_hd__nand2_1
load sky130_fd_sc_hd__nor3b_1
load sky130_fd_sc_hd__or2_1
load sky130_fd_sc_hd__tapvpwrvgnd_1
lef read /work/build/phase2/finish-yqqyjrug/used_cells.lef -annotate
def read /work/build/phase2/finish-yqqyjrug/final.def
load sram_4x8_wrapper
select top cell
expand
gds write /work/build/phase2/finish-yqqyjrug/sram_4x8.gds
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
ext2spice -o /work/build/phase2/finish-yqqyjrug/integrated_extracted.spice
quit -noprompt
