v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {Three-PMOS precharge/equalization; PRECH is active low} 260 -520 0 0 0.22 0.22 {}
N 380 -440 680 -440 {lab=VDD}
N 380 -440 380 -390 {lab=VDD}
N 680 -440 680 -390 {lab=VDD}
N 380 -330 380 -220 {lab=BL}
N 680 -330 680 -220 {lab=BLB}
N 300 -360 340 -360 {lab=PRECH}
N 600 -360 640 -360 {lab=PRECH}
N 380 -220 480 -220 {lab=BL}
N 540 -220 680 -220 {lab=BLB}
N 510 -280 510 -260 {lab=PRECH}
C {sky130_fd_pr/pfet_01v8.sym} 360 -360 0 0 {name=MPBL L=0.15 W=0.42 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 660 -360 0 0 {name=MPBLB L=0.15 W=0.42 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 510 -240 1 0 {name=MEQ L=0.15 W=0.42 nf=1 model=pfet_01v8 spiceprefix=X}
C {devices/iopin.sym} 530 -440 1 0 {name=p1 lab=VDD}
C {devices/iopin.sym} 380 -220 0 0 {name=p2 lab=BL}
C {devices/iopin.sym} 680 -220 2 0 {name=p3 lab=BLB}
C {devices/iopin.sym} 300 -360 0 0 {name=p4 lab=PRECH}
C {devices/iopin.sym} 530 -120 1 0 {name=p5 lab=VSS}
C {devices/lab_pin.sym} 380 -360 1 0 {name=b1 lab=VDD}
C {devices/lab_pin.sym} 680 -360 1 0 {name=b2 lab=VDD}
C {devices/lab_pin.sym} 510 -220 1 0 {name=b3 lab=VDD}
C {devices/lab_pin.sym} 600 -360 0 0 {name=g1 lab=PRECH}
C {devices/lab_pin.sym} 510 -280 0 0 {name=g2 lab=PRECH}
C {devices/title.sym} 100 -620 0 0 {name=l0 author="Open-source SRAM Memory Compiler"}
