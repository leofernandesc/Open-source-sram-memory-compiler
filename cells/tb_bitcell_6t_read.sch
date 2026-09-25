v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {Hierarchical SKY130A SRAM 6T read testbench} 340 30 0 0 0.5 0.5 {}
T {Precharge: 0-10 ns | Read WL: 20-30 ns | CBL=CBLB=5 fF} 340 70 0 0 0.25 0.25 {}
N 250 120 250 150 {lab=VDD}
N 250 120 470 120 {lab=VDD}
N 470 120 590 120 {lab=VDD}
N 590 120 930 120 {lab=VDD}
N 470 120 470 260 {lab=VDD}
N 590 120 590 340 {lab=VDD}
N 930 120 930 260 {lab=VDD}
N 470 320 470 380 {lab=BL}
N 470 380 550 380 {lab=BL}
N 550 380 590 380 {lab=BL}
N 550 380 550 500 {lab=BL}
N 810 340 850 340 {lab=BLB}
N 850 340 930 340 {lab=BLB}
N 930 320 930 340 {lab=BLB}
N 850 340 850 500 {lab=BLB}
N 250 320 350 320 {lab=WL}
N 350 320 350 640 {lab=WL}
N 350 640 700 640 {lab=WL}
N 700 510 700 640 {lab=WL}
N 250 550 250 590 {lab=GND}
C {cells/bitcell_6t.sym} 700 400 0 0 {name=XBITCELL WPU=0.42 WPD=0.42 WACC=0.42}
C {cells/vsource_drive.sym} 250 180 0 0 {name=VDD_SRC value=1.8 savecurrent=false}
C {cells/vsource_drive.sym} 250 350 0 0 {name=VWL_SRC value="PULSE(0 1.8 20n 50p 50p 10n 40n)" savecurrent=false}
C {cells/vsource_drive.sym} 250 520 0 0 {name=VPRE_SRC value="PULSE(1.8 0 10n 50p 50p 90n 200n)" savecurrent=false}
C {devices/switch_ngspice.sym} 470 290 0 0 {name=SBL model=SWPRE device_model=".model SWPRE SW(RON=10 ROFF=1e12 VT=0.9 VH=0.1)"}
C {devices/switch_ngspice.sym} 930 290 0 0 {name=SBLB model=SWPRE device_model=".model SWPRE SW(RON=10 ROFF=1e12 VT=0.9 VH=0.1)"}
C {devices/capa.sym} 550 530 0 0 {name=CBL value=5f m=1}
C {devices/capa.sym} 850 530 0 0 {name=CBLB value=5f m=1}
C {devices/gnd.sym} 250 590 0 0 {name=lGND lab=GND}
C {devices/lab_pin.sym} 250 150 0 0 {name=pVDD_SRC lab=VDD}
C {devices/lab_pin.sym} 250 210 0 0 {name=pVSS_SRC1 lab=GND}
C {devices/lab_pin.sym} 250 320 0 0 {name=pWL_SRC lab=WL}
C {devices/lab_pin.sym} 250 380 0 0 {name=pVSS_SRC2 lab=GND}
C {devices/lab_pin.sym} 250 490 0 0 {name=pPRE_SRC lab=PRE}
C {devices/lab_pin.sym} 250 550 0 0 {name=pVSS_SRC3 lab=GND}
C {devices/lab_pin.sym} 430 290 0 0 {name=pSBL_PRE lab=PRE}
C {devices/lab_pin.sym} 430 310 0 0 {name=pSBL_GND lab=GND}
C {devices/lab_pin.sym} 890 290 0 0 {name=pSBLB_PRE lab=PRE}
C {devices/lab_pin.sym} 890 310 0 0 {name=pSBLB_GND lab=GND}
C {devices/lab_pin.sym} 550 560 0 0 {name=pCBL_GND lab=GND}
C {devices/lab_pin.sym} 850 560 0 0 {name=pCBLB_GND lab=GND}
C {devices/lab_pin.sym} 590 380 0 0 {name=pBIT_BL lab=BL}
C {devices/lab_pin.sym} 810 340 0 1 {name=pBIT_BLB lab=BLB}
C {devices/lab_pin.sym} 810 380 0 1 {name=pBIT_GND lab=GND}
C {devices/lab_pin.sym} 700 510 1 0 {name=pBIT_WL lab=WL}
C {devices/netlist.sym} 1080 360 0 0 {name=CONTROL only_toplevel=true value=".lib /opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice tt
.ic V(xbitcell.Q)=1.8 V(xbitcell.QB)=0 V(BL)=1.8 V(BLB)=1.8
.options ngbehavior=ps method=gear reltol=1e-4 vabstol=1e-9 iabstol=1e-12
.control
save all
tran 10p 40n 0 10p uic
meas tran blb_read_min MIN v(BLB) FROM=20n TO=30n
meas tran bl_read_min MIN v(BL) FROM=20n TO=30n
meas tran bl_21n FIND v(BL) AT=21n
meas tran blb_21n FIND v(BLB) AT=21n
let delta_21n = bl_21n - blb_21n
print delta_21n
meas tran q_read_min MIN v(xbitcell.Q) FROM=20n TO=30n
meas tran qb_read_min MIN v(xbitcell.QB) FROM=20n TO=30n
write tb_bitcell_6t_read.raw all
.endc"}
C {devices/title.sym} 140 710 0 0 {name=l0 author="Open-source SRAM Memory Compiler"}
