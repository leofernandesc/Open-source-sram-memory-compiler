v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {Captured-access control path plus the transistor-level PCLK/PRECH phase source} 60 -300 0 0 0.32 0.32 {}
T {External CSb/OEb/WEb are qualified before the rising CLK edge and held in VALID_ACCESS_Q.} 60 -260 0 0 0.21 0.21 {}
T {The phase-source subcircuit itself remains unchanged. The assembled path has no reset.} 60 -230 0 0 0.21 0.21 {}

C {cells/control/valid_access_capture.sym} 300 150 0 0 {name=XACCESS}
C {cells/control/pclk_phase_source.sym} 700 150 0 0 {name=XPHASE}

C {devices/ipin.sym} 60 90 0 0 {name=p1 lab=CLK}
C {devices/ipin.sym} 60 130 0 0 {name=p2 lab=CSb}
C {devices/ipin.sym} 60 170 0 0 {name=p3 lab=OEb}
C {devices/ipin.sym} 60 210 0 0 {name=p4 lab=WEb}
C {devices/iopin.sym} 300 10 1 0 {name=p5 lab=VDD}
C {devices/iopin.sym} 300 280 1 0 {name=p6 lab=VSS}
C {devices/opin.sym} 1000 140 2 0 {name=p7 lab=VALID_ACCESS_Q}
C {devices/opin.sym} 1000 180 2 0 {name=p8 lab=PCLK}
C {devices/opin.sym} 1000 200 2 0 {name=p9 lab=PRECH}

C {devices/lab_pin.sym} 160 80 0 0 {name=l1 lab=CLK}
C {devices/lab_pin.sym} 160 120 0 0 {name=l2 lab=CSb}
C {devices/lab_pin.sym} 160 160 0 0 {name=l3 lab=OEb}
C {devices/lab_pin.sym} 160 200 0 0 {name=l4 lab=WEb}
C {devices/lab_pin.sym} 300 40 0 0 {name=l5 lab=VDD}
C {devices/lab_pin.sym} 300 260 0 0 {name=l6 lab=VSS}
C {devices/lab_pin.sym} 440 140 0 0 {name=l7 lab=VALID_ACCESS_Q}

C {devices/lab_pin.sym} 580 110 0 0 {name=l8 lab=CLK}
C {devices/lab_pin.sym} 700 90 0 0 {name=l9 lab=VDD}
C {devices/lab_pin.sym} 700 130 0 0 {name=l10 lab=VSS}
C {devices/lab_pin.sym} 580 150 0 0 {name=l11 lab=VALID_ACCESS_Q}
C {devices/lab_pin.sym} 820 170 0 0 {name=l12 lab=PCLK}
C {devices/lab_pin.sym} 820 190 0 0 {name=l13 lab=PRECH}

T {PCLK and PRECH only respond to the registered valid-access bit; idle, disabled and invalid vectors inhibit evaluation.} 60 360 0 0 0.21 0.21 {}
