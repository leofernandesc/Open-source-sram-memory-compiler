v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {Differential regenerative latch with SCLK-controlled isolation NMOS} 240 -620 0 0 0.22 0.22 {}
N 480 -500 480 -450 {lab=VDD}
N 740 -500 740 -450 {lab=VDD}
N 480 -500 740 -500 {lab=VDD}
N 480 -390 480 -290 {lab=SA_OUT}
N 740 -390 740 -290 {lab=SA_OUTB}
N 480 -230 480 -210 {lab=VSS}
N 480 -210 740 -210 {lab=VSS}
N 740 -230 740 -210 {lab=VSS}
N 420 -420 440 -420 {lab=SA_OUTB}
N 420 -420 380 -420 {lab=SA_OUTB}
N 380 -420 380 -260 {lab=SA_OUTB}
N 380 -260 440 -260 {lab=SA_OUTB}
N 620 -420 720 -420 {lab=SA_OUT}
N 620 -420 620 -260 {lab=SA_OUT}
N 620 -260 720 -260 {lab=SA_OUT}
N 400 -320 480 -320 {lab=SA_OUT}
N 740 -320 820 -320 {lab=SA_OUTB}
N 310 -320 340 -320 {lab=BL}
N 880 -320 890 -320 {lab=BLB}
N 340 -360 360 -360 {lab=SCLK}
N 360 -360 850 -360 {lab=SCLK}
C {sky130_fd_pr/pfet_01v8.sym} 460 -420 0 0 {name=MP1 L=0.15 W=0.84 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 460 -260 0 0 {name=MN1 L=0.15 W=0.42 nf=1 model=nfet_01v8 spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 720 -420 0 0 {name=MP2 L=0.15 W=0.84 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 720 -260 0 0 {name=MN2 L=0.15 W=0.42 nf=1 model=nfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 370 -340 1 0 {name=MI1 L=0.15 W=0.42 nf=1 model=nfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 850 -340 1 0 {name=MI2 L=0.15 W=0.42 nf=1 model=nfet_01v8 spiceprefix=X}
C {devices/iopin.sym} 610 -500 1 0 {name=p1 lab=VDD}
C {devices/iopin.sym} 610 -210 1 0 {name=p2 lab=VSS}
C {devices/iopin.sym} 310 -320 0 0 {name=p3 lab=BL}
C {devices/iopin.sym} 890 -320 2 0 {name=p4 lab=BLB}
C {devices/iopin.sym} 340 -360 0 0 {name=p5 lab=SCLK}
C {devices/iopin.sym} 480 -320 1 0 {name=p6 lab=SA_OUT}
C {devices/iopin.sym} 740 -320 1 0 {name=p7 lab=SA_OUTB}
C {devices/lab_pin.sym} 480 -420 1 0 {name=b1 lab=VDD}
C {devices/lab_pin.sym} 740 -420 1 0 {name=b2 lab=VDD}
C {devices/lab_pin.sym} 480 -260 1 0 {name=b3 lab=VSS}
C {devices/lab_pin.sym} 740 -260 1 0 {name=b4 lab=VSS}
C {devices/lab_pin.sym} 370 -320 1 0 {name=b5 lab=VSS}
C {devices/lab_pin.sym} 850 -320 1 0 {name=b6 lab=VSS}
C {devices/lab_pin.sym} 380 -420 0 0 {name=g1 lab=SA_OUTB}
C {devices/lab_pin.sym} 620 -420 0 0 {name=g2 lab=SA_OUT}
C {devices/title.sym} 100 -700 0 0 {name=l0 author="Open-source SRAM Memory Compiler"}
