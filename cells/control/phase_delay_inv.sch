v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {SKY130A delay-chain inverter; experimental Wp=0.84 um, Wn=0.42 um} 100 -700 0 0 0.25 0.25 {}
N 420 -190 420 -160 {lab=VDD}
N 420 -130 420 -30 {lab=Y}
N 420 0 420 30 {lab=VSS}
N 280 -160 280 0 {lab=A}
N 280 -160 380 -160 {lab=A}
N 280 0 380 0 {lab=A}
C {sky130_fd_pr/pfet_01v8.sym} 400 -160 0 0 {name=MP L=0.15 W=0.84 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 400 0 0 0 {name=MN L=0.15 W=0.42 nf=1 model=nfet_01v8 spiceprefix=X}
C {devices/ipin.sym} 280 -80 0 0 {name=p1 lab=A}
C {devices/opin.sym} 420 -80 0 0 {name=p2 lab=Y}
C {devices/iopin.sym} 420 -190 1 0 {name=p3 lab=VDD}
C {devices/iopin.sym} 420 30 1 0 {name=p4 lab=VSS}
