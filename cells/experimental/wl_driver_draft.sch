v {xschem version=3.4.4 file_version=1.2}

* Two-stage wordline buffer. Drive strength is intentionally provisional.
C {sky130_fd_pr/pfet_01v8.sym} 360 -280 0 0 {name=MP1 L=0.15 W=0.42 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 360 -120 0 0 {name=MN1 L=0.15 W=0.42 nf=1 model=nfet_01v8 spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 700 -280 0 0 {name=MP2 L=0.15 W=0.84 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 700 -120 0 0 {name=MN2 L=0.15 W=0.84 nf=1 model=nfet_01v8 spiceprefix=X}
N 360 -360 360 -320 {lab=VDD}
N 360 -200 360 -160 {lab=WL_N}
N 360 -80 360 -40 {lab=VSS}
N 700 -360 700 -320 {lab=VDD}
N 700 -200 700 -160 {lab=WL}
N 700 -80 700 -40 {lab=VSS}
N 260 -200 360 -200 {lab=WL_IN}
N 360 -200 620 -200 {lab=WL_N}
N 620 -200 620 -200 {lab=WL_N}
N 620 -200 700 -200 {lab=WL_N}
C {devices/lab_pin.sym} 260 -200 0 0 {name=p1 lab=WL_IN}
C {devices/lab_pin.sym} 700 -200 2 0 {name=p2 lab=WL}
C {devices/lab_pin.sym} 360 -360 1 0 {name=p3 lab=VDD}
C {devices/lab_pin.sym} 360 -40 3 0 {name=p4 lab=VSS}
