v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {Two-stage noninverting CMOS WL buffer; sizing frozen for pre-layout closure} 240 -620 0 0 0.22 0.22 {}
N 480 -500 480 -450 {lab=VDD}
N 740 -500 740 -450 {lab=VDD}
N 480 -500 740 -500 {lab=VDD}
N 480 -390 480 -290 {lab=WL_N}
N 740 -390 740 -290 {lab=WL}
N 480 -230 480 -200 {lab=VSS}
N 740 -230 740 -200 {lab=VSS}
N 480 -200 740 -200 {lab=VSS}
N 310 -420 440 -420 {lab=WL_IN}
N 380 -420 380 -260 {lab=WL_IN}
N 380 -260 440 -260 {lab=WL_IN}
N 620 -420 700 -420 {lab=WL_N}
N 620 -420 620 -260 {lab=WL_N}
N 620 -260 700 -260 {lab=WL_N}
C {sky130_fd_pr/pfet_01v8.sym} 460 -420 0 0 {name=MP1 L=0.15 W=0.42 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 460 -260 0 0 {name=MN1 L=0.15 W=0.42 nf=1 model=nfet_01v8 spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 720 -420 0 0 {name=MP2 L=0.15 W=0.84 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 720 -260 0 0 {name=MN2 L=0.15 W=0.84 nf=1 model=nfet_01v8 spiceprefix=X}
C {devices/iopin.sym} 610 -500 1 0 {name=p1 lab=VDD}
C {devices/iopin.sym} 610 -200 1 0 {name=p2 lab=VSS}
C {devices/iopin.sym} 310 -420 0 0 {name=p3 lab=WL_IN}
C {devices/iopin.sym} 740 -340 2 0 {name=p4 lab=WL}
C {devices/lab_pin.sym} 480 -420 1 0 {name=b1 lab=VDD}
C {devices/lab_pin.sym} 740 -420 1 0 {name=b2 lab=VDD}
C {devices/lab_pin.sym} 480 -260 1 0 {name=b3 lab=VSS}
C {devices/lab_pin.sym} 740 -260 1 0 {name=b4 lab=VSS}
C {devices/lab_pin.sym} 480 -340 0 0 {name=g1 lab=WL_N}
C {devices/lab_pin.sym} 620 -420 0 0 {name=g2 lab=WL_N}
C {devices/title.sym} 100 -700 0 0 {name=l0 author="Open-source SRAM Memory Compiler"}
