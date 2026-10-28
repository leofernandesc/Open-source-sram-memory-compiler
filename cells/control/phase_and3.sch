v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {Three-input static CMOS AND; NAND3 followed by output inverter} 100 -700 0 0 0.25 0.25 {}
N 320 -430 320 -400 {lab=VDD}
N 320 -370 620 -370 {lab=NAND3}
N 80 -400 280 -400 {lab=A}
C {sky130_fd_pr/pfet_01v8.sym} 300 -400 0 0 {name=MPA L=0.15 W=0.84 nf=1 model=pfet_01v8 spiceprefix=X}
C {devices/lab_pin.sym} 320 -430 0 0 {name=l17 lab=VDD}
N 320 -350 320 -320 {lab=VDD}
N 320 -290 620 -290 {lab=NAND3}
N 80 -320 280 -320 {lab=B}
C {sky130_fd_pr/pfet_01v8.sym} 300 -320 0 0 {name=MPB L=0.15 W=0.84 nf=1 model=pfet_01v8 spiceprefix=X}
C {devices/lab_pin.sym} 320 -350 0 0 {name=l22 lab=VDD}
N 320 -270 320 -240 {lab=VDD}
N 320 -210 620 -210 {lab=NAND3}
N 80 -240 280 -240 {lab=C}
C {sky130_fd_pr/pfet_01v8.sym} 300 -240 0 0 {name=MPC L=0.15 W=0.84 nf=1 model=pfet_01v8 spiceprefix=X}
C {devices/lab_pin.sym} 320 -270 0 0 {name=l27 lab=VDD}
N 620 -370 620 -150 {lab=NAND3}
C {sky130_fd_pr/nfet_01v8.sym} 600 -120 0 0 {name=MNA L=0.15 W=0.42 nf=1 model=nfet_01v8 spiceprefix=X}
C {devices/lab_pin.sym} 620 -120 0 0 {name=l43 lab=VSS}
C {devices/lab_pin.sym} 580 -120 0 0 {name=l44 lab=A}
C {sky130_fd_pr/nfet_01v8.sym} 600 -40 0 0 {name=MNB L=0.15 W=0.42 nf=1 model=nfet_01v8 spiceprefix=X}
C {devices/lab_pin.sym} 620 -40 0 0 {name=l46 lab=VSS}
C {devices/lab_pin.sym} 580 -40 0 0 {name=l47 lab=B}
C {sky130_fd_pr/nfet_01v8.sym} 600 40 0 0 {name=MNC L=0.15 W=0.42 nf=1 model=nfet_01v8 spiceprefix=X}
C {devices/lab_pin.sym} 620 40 0 0 {name=l49 lab=VSS}
C {devices/lab_pin.sym} 580 40 0 0 {name=l50 lab=C}
N 620 -90 620 -70 {lab=STACK1}
N 620 -10 620 10 {lab=STACK2}
N 620 70 620 160 {lab=VSS}
N 920 -90 920 -60 {lab=VDD}
N 920 -30 920 70 {lab=Y}
N 920 100 920 130 {lab=VSS}
C {sky130_fd_pr/pfet_01v8.sym} 900 -60 0 0 {name=MPINV L=0.15 W=3.0 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 900 100 0 0 {name=MNINV L=0.15 W=1.5 nf=1 model=nfet_01v8 spiceprefix=X}
C {devices/lab_pin.sym} 620 -150 0 0 {name=l200 lab=NAND3}
C {devices/lab_pin.sym} 880 -60 0 0 {name=l201 lab=NAND3}
C {devices/lab_pin.sym} 880 100 0 0 {name=l202 lab=NAND3}
C {devices/lab_pin.sym} 620 70 0 0 {name=l203 lab=VSS}
C {devices/lab_pin.sym} 920 -90 0 0 {name=l204 lab=VDD}
C {devices/iopin.sym} 320 -430 1 0 {name=p1 lab=VDD}
C {devices/ipin.sym} 80 -400 0 0 {name=p2 lab=A}
C {devices/ipin.sym} 80 -320 0 0 {name=p3 lab=B}
C {devices/ipin.sym} 80 -240 0 0 {name=p4 lab=C}
C {devices/opin.sym} 920 20 2 0 {name=p5 lab=Y}
C {devices/iopin.sym} 920 130 1 0 {name=p6 lab=VSS}
