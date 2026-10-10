v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {Registered row address and access-phase interface for the dynamic decoder} 60 -280 0 0 0.32 0.32 {}
T {A0/A1 and access controls are sampled on the rising edge of CLK.} 60 -240 0 0 0.22 0.22 {}
T {Captured A0_Q/A1_Q feed the row decoder; PCLK and PRECH drive its phase interfaces.} 60 -210 0 0 0.22 0.22 {}

C {cells/control/row_address_capture.sym} 400 220 0 0 {name=XADDR}
C {cells/control/captured_pclk_phase_source.sym} 900 500 0 0 {name=XPHASE}

C {devices/ipin.sym} 60 40 0 0 {name=p1 lab=CLK}
C {devices/ipin.sym} 60 80 0 0 {name=p2 lab=A0}
C {devices/ipin.sym} 60 120 0 0 {name=p3 lab=A1}
C {devices/ipin.sym} 60 300 0 0 {name=p4 lab=CSb}
C {devices/ipin.sym} 60 340 0 0 {name=p5 lab=OEb}
C {devices/ipin.sym} 60 380 0 0 {name=p6 lab=WEb}
C {devices/iopin.sym} 400 0 1 0 {name=p7 lab=VDD}
C {devices/iopin.sym} 500 0 1 0 {name=p8 lab=VSS}
C {devices/opin.sym} 1300 180 2 0 {name=p9 lab=A0_Q}
C {devices/opin.sym} 1300 220 2 0 {name=p10 lab=A1_Q}
C {devices/opin.sym} 1300 260 2 0 {name=p11 lab=VALID_ACCESS_Q}
C {devices/opin.sym} 1300 300 2 0 {name=p12 lab=PCLK}
C {devices/opin.sym} 1300 340 2 0 {name=p13 lab=PRECH}

C {devices/lab_pin.sym} 250 150 0 0 {name=l1 lab=CLK}
C {devices/lab_pin.sym} 250 190 0 0 {name=l2 lab=A0}
C {devices/lab_pin.sym} 250 230 0 0 {name=l3 lab=A1}
C {devices/lab_pin.sym} 400 100 0 0 {name=l4 lab=VDD}
C {devices/lab_pin.sym} 400 340 0 0 {name=l5 lab=VSS}
C {devices/lab_pin.sym} 550 180 0 0 {name=l6 lab=A0_Q}
C {devices/lab_pin.sym} 550 260 0 0 {name=l7 lab=A1_Q}

C {devices/lab_pin.sym} 750 410 0 0 {name=l8 lab=CLK}
C {devices/lab_pin.sym} 750 450 0 0 {name=l9 lab=CSb}
C {devices/lab_pin.sym} 750 490 0 0 {name=l10 lab=OEb}
C {devices/lab_pin.sym} 750 530 0 0 {name=l11 lab=WEb}
C {devices/lab_pin.sym} 900 365 0 0 {name=l12 lab=VDD}
C {devices/lab_pin.sym} 900 635 0 0 {name=l13 lab=VSS}
C {devices/lab_pin.sym} 1050 460 0 0 {name=l14 lab=VALID_ACCESS_Q}
C {devices/lab_pin.sym} 1050 500 0 0 {name=l15 lab=PCLK}
C {devices/lab_pin.sym} 1050 540 0 0 {name=l16 lab=PRECH}
