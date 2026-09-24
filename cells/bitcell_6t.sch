v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
N 480 -500 480 -460 {lab=VDD}
N 700 -420 720 -420 {lab=Q}
N 480 -460 480 -450 {lab=VDD}
N 480 -390 480 -290 {lab=Q}
N 420 -420 440 -420 {lab=QB}
N 420 -420 380 -420 {lab=QB}
N 740 -390 740 -290 {lab=QB}
N 380 -420 380 -260 {lab=QB}
N 380 -260 440 -260 {lab=QB}
N 420 -260 440 -260 {lab=QB}
N 480 -230 480 -210 {lab=VSS}
N 480 -210 740 -210 {lab=VSS}
N 740 -230 740 -210 {lab=VSS}
N 740 -500 740 -450 {lab=VDD}
N 480 -500 740 -500 {lab=VDD}
N 400 -320 480 -320 {lab=Q}
N 360 -360 850 -360 {lab=WL}
N 310 -320 340 -320 {lab=BL}
N 620 -420 720 -420 {lab=Q}
N 620 -420 620 -260 {lab=Q}
N 620 -260 720 -260 {lab=Q}
N 880 -320 890 -320 {lab=BLB}
N 890 -420 890 -320 {lab=BLB}
N 340 -360 360 -360 {lab=WL}
N 740 -320 820 -320 {lab=QB}
C {sky130_fd_pr/pfet_01v8.sym} 460 -420 0 0 {name=MPL
L=0.15
W=0.21
ad="'W * 0.29'" pd="'W + 2 * 0.29'"
as="'W * 0.29'" ps="'W + 2 * 0.29'"
nrd=0 nrs=0 sa=0 sb=0 sd=0 nf=1 mult=1
model=pfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/nfet_01v8.sym} 460 -260 0 0 {name=MNL
L=0.15
W=0.42
ad="'W * 0.29'" pd="'W + 2 * 0.29'"
as="'W * 0.29'" ps="'W + 2 * 0.29'"
nrd=0 nrs=0 sa=0 sb=0 sd=0 nf=1 mult=1
model=nfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/pfet_01v8.sym} 720 -420 0 0 {name=MPR
L=0.15
W=0.21
ad="'W * 0.29'" pd="'W + 2 * 0.29'"
as="'W * 0.29'" ps="'W + 2 * 0.29'"
nrd=0 nrs=0 sa=0 sb=0 sd=0 nf=1 mult=1
model=pfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/nfet_01v8.sym} 720 -260 0 0 {name=MNR
L=0.15
W=0.42
ad="'W * 0.29'" pd="'W + 2 * 0.29'"
as="'W * 0.29'" ps="'W + 2 * 0.29'"
nrd=0 nrs=0 sa=0 sb=0 sd=0 nf=1 mult=1
model=nfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/nfet_01v8.sym} 370 -340 1 0 {name=MAL
L=0.15
W=0.30
ad="'W * 0.29'" pd="'W + 2 * 0.29'"
as="'W * 0.29'" ps="'W + 2 * 0.29'"
nrd=0 nrs=0 sa=0 sb=0 sd=0 nf=1 mult=1
model=nfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/nfet_01v8.sym} 850 -340 1 0 {name=MAR
L=0.15
W=0.30
ad="'W * 0.29'" pd="'W + 2 * 0.29'"
as="'W * 0.29'" ps="'W + 2 * 0.29'"
nrd=0 nrs=0 sa=0 sb=0 sd=0 nf=1 mult=1
model=nfet_01v8
spiceprefix=X
}
C {devices/iopin.sym} 580 -500 1 0 {name=p1 lab=VDD}
C {devices/iopin.sym} 310 -320 1 0 {name=p3 lab=BL}
C {devices/iopin.sym} 890 -420 1 0 {name=p4 lab=BLB}
C {devices/iopin.sym} 610 -210 1 0 {name=p8 lab=VSS}
C {devices/lab_pin.sym} 480 -420 1 0 {name=b1 lab=VDD}
C {devices/lab_pin.sym} 740 -420 1 0 {name=b2 lab=VDD}
C {devices/lab_pin.sym} 480 -260 1 0 {name=b3 lab=VSS}
C {devices/lab_pin.sym} 740 -260 1 0 {name=b4 lab=VSS}
C {devices/lab_pin.sym} 370 -320 1 0 {name=b5 lab=VSS}
C {devices/lab_pin.sym} 850 -320 1 0 {name=b6 lab=VSS}
C {devices/lab_pin.sym} 380 -420 0 0 {name=g1 lab=QB}
C {devices/lab_pin.sym} 620 -420 0 0 {name=g2 lab=Q}
C {devices/lab_pin.sym} 740 -320 0 0 {name=p5 sig_type=std_logic lab=QB}
C {devices/lab_pin.sym} 480 -320 2 0 {name=p6 sig_type=std_logic lab=Q}
C {devices/iopin.sym} 340 -360 0 0 {name=p7 lab=WL}
C {devices/title.sym} 100 -700 0 0 {name=l0 author="Open-source SRAM Memory Compiler"}
