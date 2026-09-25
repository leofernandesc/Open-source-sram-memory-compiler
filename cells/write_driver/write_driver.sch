v {xschem version=3.4.4 file_version=1.2}

* Complementary write driver draft. WE gating and sizing require characterization.
C {sky130_fd_pr/pfet_01v8.sym} 340 -300 0 0 {name=MPBL L=0.15 W=0.84 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 340 -140 0 0 {name=MNBL L=0.15 W=0.84 nf=1 model=nfet_01v8 spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 680 -300 0 0 {name=MPBLB L=0.15 W=0.84 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 680 -140 0 0 {name=MNBLB L=0.15 W=0.84 nf=1 model=nfet_01v8 spiceprefix=X}
N 340 -380 340 -340 {lab=VDD}
N 340 -220 340 -180 {lab=BL}
N 340 -100 340 -60 {lab=VSS}
N 680 -380 680 -340 {lab=VDD}
N 680 -220 680 -180 {lab=BLB}
N 680 -100 680 -60 {lab=VSS}
N 240 -220 340 -220 {lab=DATA}
N 580 -220 680 -220 {lab=DATA_B}
N 240 -140 340 -140 {lab=WE}
N 580 -140 680 -140 {lab=WE}
C {devices/lab_pin.sym} 240 -220 0 0 {name=p1 lab=DATA}
C {devices/lab_pin.sym} 240 -140 0 0 {name=p2 lab=WE}
C {devices/lab_pin.sym} 580 -220 0 0 {name=p3 lab=DATA_B}
C {devices/lab_pin.sym} 680 -220 2 0 {name=p4 lab=BLB}
C {devices/lab_pin.sym} 340 -380 1 0 {name=p5 lab=VDD}
C {devices/lab_pin.sym} 340 -60 3 0 {name=p6 lab=VSS}
