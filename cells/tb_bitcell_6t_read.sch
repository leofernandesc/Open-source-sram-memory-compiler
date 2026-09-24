v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {Hierarchical SKY130A SRAM 6T read testbench} 350 80 0 0 0.5 0.5 {}
T {Precharge: 0-10 ns | Read WL: 20-30 ns | CBL=CBLB=5 fF} 350 110 0 0 0.25 0.25 {}
C {cells/bitcell_6t.sym} 700 400 0 0 {name=XBITCELL}
C {cells/vsource_drive.sym} 250 180 0 0 {name=VDD_SRC value=1.8 savecurrent=false}
C {cells/vsource_drive.sym} 250 350 0 0 {name=VWL_SRC value="PULSE(0 1.8 20n 100p 100p 10n 100n)" savecurrent=false}
C {cells/vsource_drive.sym} 250 520 0 0 {name=VPRE_SRC value="PULSE(1.8 0 10n 100p 100p 90n 200n)" savecurrent=false}
C {devices/switch_ngspice.sym} 470 290 0 0 {name=SBL model=SWPRE device_model=".model SWPRE SW(RON=1 ROFF=1G VT=0.9 VH=0.1)"}
C {devices/switch_ngspice.sym} 930 290 0 0 {name=SBLB model=SWPRE device_model=".model SWPRE SW(RON=1 ROFF=1G VT=0.9 VH=0.1)"}
C {devices/capa.sym} 550 530 0 0 {name=CBL value=5f m=1}
C {devices/capa.sym} 850 530 0 0 {name=CBLB value=5f m=1}
C {devices/gnd.sym} 250 590 0 0 {name=lGND lab=GND}
C {devices/gnd.sym} 700 620 0 0 {name=lVSS lab=GND}
C {devices/lab_pin.sym} 250 150 0 0 {name=pVDD_SRC lab=VDD}
C {devices/lab_pin.sym} 250 210 0 0 {name=pVSS_SRC1 lab=GND}
C {devices/lab_pin.sym} 250 320 0 0 {name=pWL_SRC lab=WL}
C {devices/lab_pin.sym} 250 380 0 0 {name=pVSS_SRC2 lab=GND}
C {devices/lab_pin.sym} 250 490 0 0 {name=pPRE_SRC lab=PRE}
C {devices/lab_pin.sym} 250 550 0 0 {name=pVSS_SRC3 lab=GND}
C {devices/lab_pin.sym} 470 260 0 0 {name=pSBL_VDD lab=VDD}
C {devices/lab_pin.sym} 470 320 0 0 {name=pSBL_BL lab=BL}
C {devices/lab_pin.sym} 430 290 0 0 {name=pSBL_PRE lab=PRE}
C {devices/lab_pin.sym} 430 310 0 0 {name=pSBL_GND lab=GND}
C {devices/lab_pin.sym} 930 260 0 0 {name=pSBLB_VDD lab=VDD}
C {devices/lab_pin.sym} 930 320 0 0 {name=pSBLB_BLB lab=BLB}
C {devices/lab_pin.sym} 890 290 0 0 {name=pSBLB_PRE lab=PRE}
C {devices/lab_pin.sym} 890 310 0 0 {name=pSBLB_GND lab=GND}
C {devices/lab_pin.sym} 550 500 0 0 {name=pCBL lab=BL}
C {devices/lab_pin.sym} 550 560 0 0 {name=pCBL_GND lab=GND}
C {devices/lab_pin.sym} 850 500 0 0 {name=pCBLB lab=BLB}
C {devices/lab_pin.sym} 850 560 0 0 {name=pCBLB_GND lab=GND}
C {devices/lab_pin.sym} 590 340 0 0 {name=pBIT_VDD lab=VDD}
C {devices/lab_pin.sym} 590 380 0 0 {name=pBIT_BL lab=BL}
C {devices/lab_pin.sym} 810 340 0 1 {name=pBIT_BLB lab=BLB}
C {devices/lab_pin.sym} 810 380 0 1 {name=pBIT_GND lab=GND}
C {devices/lab_pin.sym} 700 510 1 0 {name=pBIT_WL lab=WL}
C {devices/netlist.sym} 1080 360 0 0 {name=CONTROL only_toplevel=true value=".param corner_factor=1 process_mc_factor=1 mismatch_factor=1 MC_MM_SWITCH=0 MC_PR_SWITCH=0
.include /opt/pdks/sky130A/libs.tech/combined/continuous/parameters_fet_tt.spice
.include /opt/pdks/sky130A/libs.tech/combined/continuous/parameters_res_nom.spice
.include /opt/pdks/sky130A/libs.tech/combined/continuous/parameters_cap_nom.spice
.include /opt/pdks/sky130A/libs.tech/combined/continuous/models_global.spice
.include /opt/pdks/sky130A/libs.tech/combined/continuous/models_fet.spice
.control
tran 10p 50n uic
save all
meas tran blb_read_min MIN v(BLB) FROM=20n TO=30n
meas tran bl_read_min MIN v(BL) FROM=20n TO=30n
meas tran q_read_min MIN v(Q) FROM=20n TO=30n
.endc"}
C {devices/title.sym} 140 710 0 0 {name=l0 author="Open-source SRAM Memory Compiler"}
