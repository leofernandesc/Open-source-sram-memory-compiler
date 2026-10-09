v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {Two-input static CMOS OR; NOR2 followed by output inverter} 100 -700 0 0 0.25 0.25 {}
N 320 -230 320 -200 {lab=VDD}
N 320 -170 320 -130 {lab=PSTACK}
N 320 -70 620 -70 {lab=NOR2}
N 80 -200 280 -200 {lab=A}
N 80 -100 280 -100 {lab=B}
C {sky130_fd_pr/pfet_01v8.sym} 300 -200 0 0 {name=MPA L=0.15 W=1.68 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 300 -100 0 0 {name=MPB L=0.15 W=1.68 nf=1 model=pfet_01v8 spiceprefix=X}
C {devices/lab_pin.sym} 320 -230 0 0 {name=l10 lab=VDD}
C {devices/lab_pin.sym} 320 -100 0 0 {name=l11 lab=VDD}
N 620 -70 620 110 {lab=NOR2}
N 320 30 620 30 {lab=NOR2}
N 320 110 620 110 {lab=NOR2}
C {sky130_fd_pr/nfet_01v8.sym} 300 60 0 0 {name=MNA L=0.15 W=0.42 nf=1 model=nfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 300 140 0 0 {name=MNB L=0.15 W=0.42 nf=1 model=nfet_01v8 spiceprefix=X}
C {devices/lab_pin.sym} 320 60 0 0 {name=l12 lab=VSS}
C {devices/lab_pin.sym} 320 140 0 0 {name=l13 lab=VSS}
C {devices/lab_pin.sym} 280 60 0 0 {name=l14 lab=A}
C {devices/lab_pin.sym} 280 140 0 0 {name=l15 lab=B}
C {devices/lab_pin.sym} 320 90 0 0 {name=l16 lab=VSS}
C {devices/lab_pin.sym} 320 170 0 0 {name=l17 lab=VSS}
N 920 -90 920 -60 {lab=VDD}
N 920 -30 920 70 {lab=Y}
N 920 100 920 130 {lab=VSS}
C {sky130_fd_pr/pfet_01v8.sym} 900 -60 0 0 {name=MPINV L=0.15 W=3.0 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 900 100 0 0 {name=MNINV L=0.15 W=1.5 nf=1 model=nfet_01v8 spiceprefix=X}
C {devices/lab_pin.sym} 620 -70 0 0 {name=l200 lab=NOR2}
C {devices/lab_pin.sym} 880 -60 0 0 {name=l201 lab=NOR2}
C {devices/lab_pin.sym} 880 100 0 0 {name=l202 lab=NOR2}
C {devices/lab_pin.sym} 920 -90 0 0 {name=l203 lab=VDD}
C {devices/iopin.sym} 320 -230 1 0 {name=p1 lab=VDD}
C {devices/ipin.sym} 80 -200 0 0 {name=p2 lab=A}
C {devices/ipin.sym} 80 -100 0 0 {name=p3 lab=B}
C {devices/opin.sym} 920 20 2 0 {name=p4 lab=Y}
C {devices/iopin.sym} 920 130 1 0 {name=p5 lab=VSS}
