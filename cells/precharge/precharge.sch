v {xschem version=3.4.4 file_version=1.2}

* Precharge/equalization: PRECH=0 connects BL and BLB to VDD.
C {sky130_fd_pr/pfet_01v8.sym} 300 -260 0 0 {name=MPBL L=0.15 W=0.42 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 600 -260 0 0 {name=MPBLB L=0.15 W=0.42 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 450 -100 1 0 {name=MEQ L=0.15 W=0.42 nf=1 model=pfet_01v8 spiceprefix=X}
N 300 -340 300 -300 {lab=VDD}
N 600 -340 600 -300 {lab=VDD}
N 300 -220 300 -160 {lab=BL}
N 600 -220 600 -160 {lab=BLB}
N 450 -60 450 -20 {lab=VDD}
N 450 -140 450 -160 {lab=PRECH}
N 300 -160 450 -160 {lab=BL}
N 450 -160 600 -160 {lab=BLB}
C {devices/lab_pin.sym} 300 -340 1 0 {name=p1 lab=VDD}
C {devices/lab_pin.sym} 300 -160 0 0 {name=p2 lab=BL}
C {devices/lab_pin.sym} 600 -160 2 0 {name=p3 lab=BLB}
C {devices/lab_pin.sym} 450 -140 0 0 {name=p4 lab=PRECH}
C {devices/lab_pin.sym} 450 -20 3 0 {name=p5 lab=VSS}
