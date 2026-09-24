v {xschem version=3.4.4 file_version=1.2}

* Structural voltage-latch sense amplifier draft.
* SCLK enables isolation and regeneration; sizing is not frozen.
C {sky130_fd_pr/pfet_01v8.sym} 420 -360 0 0 {name=MP1 L=0.15 W=0.84 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 720 -360 0 0 {name=MP2 L=0.15 W=0.84 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 420 -200 0 0 {name=MN1 L=0.15 W=0.42 nf=1 model=nfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 720 -200 0 0 {name=MN2 L=0.15 W=0.42 nf=1 model=nfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 260 -80 1 0 {name=MI1 L=0.15 W=0.30 nf=1 model=nfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 880 -80 1 0 {name=MI2 L=0.15 W=0.30 nf=1 model=nfet_01v8 spiceprefix=X}
N 420 -440 420 -400 {lab=VDD}
N 720 -440 720 -400 {lab=VDD}
N 420 -280 420 -240 {lab=SA_L}
N 720 -280 720 -240 {lab=SA_R}
N 420 -160 420 -120 {lab=VSS}
N 720 -160 720 -120 {lab=VSS}
N 260 -40 260 0 {lab=BL}
N 880 -40 880 0 {lab=BLB}
N 260 -120 260 -160 {lab=SCLK}
N 880 -120 880 -160 {lab=SCLK}
N 260 -80 420 -80 {lab=SA_L}
N 720 -80 880 -80 {lab=SA_R}
N 420 -360 560 -360 {lab=SA_R}
N 560 -360 560 -200 {lab=SA_R}
N 560 -200 460 -200 {lab=SA_R}
N 720 -360 580 -360 {lab=SA_L}
N 580 -360 580 -200 {lab=SA_L}
N 580 -200 680 -200 {lab=SA_L}
C {devices/lab_pin.sym} 260 0 1 0 {name=p1 lab=BL}
C {devices/lab_pin.sym} 880 0 1 0 {name=p2 lab=BLB}
C {devices/lab_pin.sym} 260 -120 0 0 {name=p3 lab=SCLK}
C {devices/lab_pin.sym} 420 -440 1 0 {name=p4 lab=VDD}
C {devices/lab_pin.sym} 420 -120 3 0 {name=p5 lab=VSS}
C {devices/lab_pin.sym} 420 -200 0 0 {name=p6 lab=SA_OUT}
C {devices/lab_pin.sym} 720 -200 2 0 {name=p7 lab=SA_OUTB}
