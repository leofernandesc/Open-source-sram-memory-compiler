v {xschem version=3.4.4 file_version=1.2}

* Differential tri-state write driver.
* WE=1: BL=DATA and BLB=DATA_B, assuming DATA_B is complementary to DATA.
* WE=0: both pull-up and pull-down paths are disabled.

* WE inverter: generates WE_B for the PMOS enable devices.
C {sky130_fd_pr/pfet_01v8.sym} 280 -520 0 0 {name=MPWEB L=0.15 W=0.84 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 280 -400 0 0 {name=MNWEB L=0.15 W=0.84 nf=1 model=nfet_01v8 spiceprefix=X}
N 300 -590 300 -550 {lab=VDD}
N 300 -490 300 -430 {lab=WE_B}
N 300 -370 300 -110 {lab=VSS}
N 220 -520 260 -520 {lab=WE}
N 220 -400 260 -400 {lab=WE}
C {devices/lab_pin.sym} 300 -590 1 0 {name=l1 lab=VDD}
C {devices/lab_pin.sym} 300 -460 0 0 {name=l2 lab=WE_B}
C {devices/lab_pin.sym} 300 -370 1 0 {name=l3 lab=VSS}
C {devices/lab_pin.sym} 220 -520 0 0 {name=l4 lab=WE}
C {devices/lab_pin.sym} 220 -400 0 0 {name=l5 lab=WE}
C {devices/lab_pin.sym} 300 -520 1 0 {name=b1 lab=VDD}
C {devices/lab_pin.sym} 300 -400 1 0 {name=b2 lab=VSS}

* BL branch: enabled tri-state inverter driven by DATA_B, therefore BL=DATA.
C {sky130_fd_pr/pfet_01v8.sym} 540 -560 0 0 {name=MPENBL L=0.15 W=0.84 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 540 -440 0 0 {name=MPDBL L=0.15 W=0.84 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 540 -280 0 0 {name=MNDBL L=0.15 W=0.84 nf=1 model=nfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 540 -160 0 0 {name=MNENBL L=0.15 W=0.84 nf=1 model=nfet_01v8 spiceprefix=X}
N 560 -620 560 -590 {lab=VDD}
N 560 -530 560 -470 {lab=PBL_INT}
N 560 -410 560 -310 {lab=BL}
N 560 -250 560 -190 {lab=NBL_INT}
N 560 -130 560 -100 {lab=VSS}
N 500 -560 520 -560 {lab=WE_B}
N 500 -440 520 -440 {lab=DATA_B}
N 500 -280 520 -280 {lab=DATA_B}
N 500 -160 520 -160 {lab=WE}
C {devices/lab_pin.sym} 560 -620 1 0 {name=l6 lab=VDD}
C {devices/lab_pin.sym} 560 -100 1 0 {name=l7 lab=VSS}
C {devices/lab_pin.sym} 500 -560 0 0 {name=l8 lab=WE_B}
C {devices/lab_pin.sym} 500 -440 0 0 {name=l9 lab=DATA_B}
C {devices/lab_pin.sym} 500 -280 0 0 {name=l10 lab=DATA_B}
C {devices/lab_pin.sym} 500 -160 0 0 {name=l11 lab=WE}
C {devices/lab_pin.sym} 560 -560 1 0 {name=b3 lab=VDD}
C {devices/lab_pin.sym} 560 -440 1 0 {name=b4 lab=VDD}
C {devices/lab_pin.sym} 560 -280 1 0 {name=b5 lab=VSS}
C {devices/lab_pin.sym} 560 -160 1 0 {name=b6 lab=VSS}

* BLB branch: enabled tri-state inverter driven by DATA, therefore BLB=DATA_B.
C {sky130_fd_pr/pfet_01v8.sym} 840 -560 0 0 {name=MPENBLB L=0.15 W=0.84 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 840 -440 0 0 {name=MPDBLB L=0.15 W=0.84 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 840 -280 0 0 {name=MNDBLB L=0.15 W=0.84 nf=1 model=nfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 840 -160 0 0 {name=MNENBLB L=0.15 W=0.84 nf=1 model=nfet_01v8 spiceprefix=X}
N 860 -620 860 -590 {lab=VDD}
N 860 -530 860 -470 {lab=PBLB_INT}
N 860 -410 860 -310 {lab=BLB}
N 860 -250 860 -190 {lab=NBLB_INT}
N 860 -130 860 -100 {lab=VSS}
N 800 -560 820 -560 {lab=WE_B}
N 800 -440 820 -440 {lab=DATA}
N 800 -280 820 -280 {lab=DATA}
N 800 -160 820 -160 {lab=WE}
C {devices/lab_pin.sym} 860 -620 1 0 {name=l12 lab=VDD}
C {devices/lab_pin.sym} 860 -100 1 0 {name=l13 lab=VSS}
C {devices/lab_pin.sym} 800 -560 0 0 {name=l14 lab=WE_B}
C {devices/lab_pin.sym} 800 -440 0 0 {name=l15 lab=DATA}
C {devices/lab_pin.sym} 800 -280 0 0 {name=l16 lab=DATA}
C {devices/lab_pin.sym} 800 -160 0 0 {name=l17 lab=WE}
C {devices/lab_pin.sym} 860 -560 1 0 {name=b7 lab=VDD}
C {devices/lab_pin.sym} 860 -440 1 0 {name=b8 lab=VDD}
C {devices/lab_pin.sym} 860 -280 1 0 {name=b9 lab=VSS}
C {devices/lab_pin.sym} 860 -160 1 0 {name=b10 lab=VSS}

* External interface.
C {devices/iopin.sym} 180 -300 0 0 {name=p1 lab=DATA}
C {devices/iopin.sym} 180 -340 0 0 {name=p2 lab=DATA_B}
C {devices/iopin.sym} 180 -380 0 0 {name=p3 lab=WE}
C {devices/iopin.sym} 560 -360 0 0 {name=p4 lab=BL}
C {devices/iopin.sym} 860 -360 0 0 {name=p5 lab=BLB}
C {devices/iopin.sym} 710 -650 1 0 {name=p6 lab=VDD}
C {devices/iopin.sym} 710 -70 1 0 {name=p7 lab=VSS}

* Standalone nominal smoke test. The 50 fF load and timing are exploratory only.
C {devices/netlist.sym} 1030 -610 0 0 {name=STANDALONE_TEST only_toplevel=true value=".lib /opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice tt
VVSS_WR VSS 0 0
VDD_WR VDD VSS 1.8
VWE_WR WE VSS PWL(0 0 0.95n 0 1n 1.8 4n 1.8 4.05n 0 9n 0 9.05n 1.8 14n 1.8 14.05n 0 18n 0)
VDATA_WR DATA VSS PWL(0 0 6n 0 6.05n 1.8 18n 1.8)
VDATAB_WR DATA_B VSS PWL(0 1.8 6n 1.8 6.05n 0 18n 0)
CBL_WR BL VSS 50f
CBLB_WR BLB VSS 50f
.ic V(BL)=0 V(BLB)=1.8
.options ngbehavior=ps method=gear reltol=1e-4 vabstol=1e-9 iabstol=1e-12
.control
save all
tran 10p 18n 0 10p uic
meas tran bl_write0 FIND v(BL) AT=3n
meas tran blb_write1 FIND v(BLB) AT=3n
meas tran bl_hiz_before FIND v(BL) AT=5n
meas tran bl_hiz_after FIND v(BL) AT=8n
meas tran blb_hiz_before FIND v(BLB) AT=5n
meas tran blb_hiz_after FIND v(BLB) AT=8n
let bl_hiz_drift = abs(bl_hiz_after - bl_hiz_before)
let blb_hiz_drift = abs(blb_hiz_after - blb_hiz_before)
print bl_hiz_drift blb_hiz_drift
meas tran bl_write1 FIND v(BL) AT=12n
meas tran blb_write0 FIND v(BLB) AT=12n
write write_driver.raw all
.endc"}
