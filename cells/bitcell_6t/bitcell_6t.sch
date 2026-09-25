v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {Standalone smoke: TT, W=0.42 um, precharge 0-10 ns, read 20-30 ns} 820 -720 0 0 0.22 0.22 {}
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
W='WPU'
ad="'W * 0.29'" pd="'W + 2 * 0.29'"
as="'W * 0.29'" ps="'W + 2 * 0.29'"
nrd=0 nrs=0 sa=0 sb=0 sd=0 nf=1 mult=1
model=pfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/nfet_01v8.sym} 460 -260 0 0 {name=MNL
L=0.15
W='WPD'
ad="'W * 0.29'" pd="'W + 2 * 0.29'"
as="'W * 0.29'" ps="'W + 2 * 0.29'"
nrd=0 nrs=0 sa=0 sb=0 sd=0 nf=1 mult=1
model=nfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/pfet_01v8.sym} 720 -420 0 0 {name=MPR
L=0.15
W='WPU'
ad="'W * 0.29'" pd="'W + 2 * 0.29'"
as="'W * 0.29'" ps="'W + 2 * 0.29'"
nrd=0 nrs=0 sa=0 sb=0 sd=0 nf=1 mult=1
model=pfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/nfet_01v8.sym} 720 -260 0 0 {name=MNR
L=0.15
W='WPD'
ad="'W * 0.29'" pd="'W + 2 * 0.29'"
as="'W * 0.29'" ps="'W + 2 * 0.29'"
nrd=0 nrs=0 sa=0 sb=0 sd=0 nf=1 mult=1
model=nfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/nfet_01v8.sym} 370 -340 1 0 {name=MAL
L=0.15
W='WACC'
ad="'W * 0.29'" pd="'W + 2 * 0.29'"
as="'W * 0.29'" ps="'W + 2 * 0.29'"
nrd=0 nrs=0 sa=0 sb=0 sd=0 nf=1 mult=1
model=nfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/nfet_01v8.sym} 850 -340 1 0 {name=MAR
L=0.15
W='WACC'
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
C {devices/netlist.sym} 1030 -650 0 0 {name=STANDALONE_TEST only_toplevel=true value=".lib /opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice tt
.param WPU=0.42 WPD=0.42 WACC=0.42
VVSS_LEAF VSS 0 0
VDD_LEAF VDD VSS 1.8
VWL_LEAF WL VSS PULSE(0 1.8 20n 50p 50p 10n 40n)
VPRE_LEAF PRE_LEAF VSS PULSE(1.8 0 10n 50p 50p 90n 200n)
SBL_LEAF BL VDD PRE_LEAF VSS SWPRE_LEAF
SBLB_LEAF BLB VDD PRE_LEAF VSS SWPRE_LEAF
.model SWPRE_LEAF SW(RON=10 ROFF=1e12 VT=0.9 VH=0.1)
CBL_LEAF BL VSS 5f
CBLB_LEAF BLB VSS 5f
.ic V(Q)=1.8 V(QB)=0 V(BL)=1.8 V(BLB)=1.8
.options ngbehavior=ps method=gear reltol=1e-4 vabstol=1e-9 iabstol=1e-12
.control
save all
tran 10p 40n 0 10p uic
meas tran blb_read_min MIN v(BLB) FROM=20n TO=30n
meas tran bl_read_min MIN v(BL) FROM=20n TO=30n
meas tran bl_21n FIND v(BL) AT=21n
meas tran blb_21n FIND v(BLB) AT=21n
let delta_21n = bl_21n - blb_21n
print delta_21n
meas tran q_read_min MIN v(Q) FROM=20n TO=30n
meas tran qb_read_min MIN v(QB) FROM=20n TO=30n
write bitcell_6t.raw all
.endc"}
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
