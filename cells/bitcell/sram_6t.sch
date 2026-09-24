v {xschem version=3.4.4 file_version=1.2}

C {sky130_fd_pr/pfet_01v8.sym} 420 -420 0 0 {name=M1
L=0.15
W=0.42
ad="'W * 0.29'" pd="'W + 2 * 0.29'"
as="'W * 0.29'" ps="'W + 2 * 0.29'"
nrd=0 nrs=0 sa=0 sb=0 sd=0 nf=1 mult=1
model=pfet_01v8
spiceprefix=X
}

C {sky130_fd_pr/nfet_01v8.sym} 420 -260 0 0 {name=M2
L=0.15
W=0.42
ad="'W * 0.29'" pd="'W + 2 * 0.29'"
as="'W * 0.29'" ps="'W + 2 * 0.29'"
nrd=0 nrs=0 sa=0 sb=0 sd=0 nf=1 mult=1
model=nfet_01v8
spiceprefix=X
}

C {sky130_fd_pr/pfet_01v8.sym} 720 -420 0 0 {name=M3
L=0.15
W=0.42
ad="'W * 0.29'" pd="'W + 2 * 0.29'"
as="'W * 0.29'" ps="'W + 2 * 0.29'"
nrd=0 nrs=0 sa=0 sb=0 sd=0 nf=1 mult=1
model=pfet_01v8
spiceprefix=X
}

C {sky130_fd_pr/nfet_01v8.sym} 720 -260 0 0 {name=M4
L=0.15
W=0.42
ad="'W * 0.29'" pd="'W + 2 * 0.29'"
as="'W * 0.29'" ps="'W + 2 * 0.29'"
nrd=0 nrs=0 sa=0 sb=0 sd=0 nf=1 mult=1
model=nfet_01v8
spiceprefix=X
}

C {sky130_fd_pr/nfet_01v8.sym} 260 -120 1 0 {name=M5
L=0.15
W=0.42
ad="'W * 0.29'" pd="'W + 2 * 0.29'"
as="'W * 0.29'" ps="'W + 2 * 0.29'"
nrd=0 nrs=0 sa=0 sb=0 sd=0 nf=1 mult=1
model=nfet_01v8
spiceprefix=X
}

C {sky130_fd_pr/nfet_01v8.sym} 880 -120 1 0 {name=M6
L=0.15
W=0.42
ad="'W * 0.29'" pd="'W + 2 * 0.29'"
as="'W * 0.29'" ps="'W + 2 * 0.29'"
nrd=0 nrs=0 sa=0 sb=0 sd=0 nf=1 mult=1
model=nfet_01v8
spiceprefix=X
}

N 420 -500 420 -460 {lab=VDD}
N 720 -500 720 -460 {lab=VDD}
N 420 -380 420 -340 {lab=Q}
N 720 -380 720 -340 {lab=QB}
N 420 -300 420 -220 {lab=VSS}
N 720 -300 720 -220 {lab=VSS}
N 420 -180 420 -120 {lab=Q}
N 720 -180 720 -120 {lab=QB}
N 260 -80 260 -40 {lab=BL}
N 880 -80 880 -40 {lab=BLB}
N 260 -200 260 -160 {lab=WL}
N 880 -200 880 -160 {lab=WL}
N 420 -420 520 -420 {lab=QB}
N 520 -420 520 -260 {lab=QB}
N 520 -260 460 -260 {lab=QB}
N 720 -420 620 -420 {lab=Q}
N 620 -420 620 -260 {lab=Q}
N 620 -260 680 -260 {lab=Q}
N 260 -120 420 -120 {lab=Q}
N 720 -120 880 -120 {lab=QB}
N 260 -200 720 -200 {lab=WL}
N 420 -500 720 -500 {lab=VDD}
N 420 -180 420 -160 {lab=Q}
N 720 -180 720 -160 {lab=QB}
N 420 -220 420 -200 {lab=VSS}
N 720 -220 720 -200 {lab=VSS}
N 420 -200 720 -200 {lab=VSS}

C {devices/lab_pin.sym} 420 -500 1 0 {name=p1 sig_type=std_logic lab=VDD}
C {devices/lab_pin.sym} 420 -200 3 0 {name=p2 sig_type=std_logic lab=VSS}
C {devices/lab_pin.sym} 260 -40 1 0 {name=p3 sig_type=std_logic lab=BL}
C {devices/lab_pin.sym} 880 -40 1 0 {name=p4 sig_type=std_logic lab=BLB}
C {devices/lab_pin.sym} 520 -260 0 0 {name=p5 sig_type=std_logic lab=QB}
C {devices/lab_pin.sym} 620 -260 2 0 {name=p6 sig_type=std_logic lab=Q}
C {devices/lab_pin.sym} 520 -200 0 0 {name=p7 sig_type=std_logic lab=WL}
C {devices/title.sym} 100 -700 0 0 {name=l0 author="Open-source SRAM Memory Compiler"}
