v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {Two-bit row address register for the dynamic 2-to-4 decoder} 80 -120 0 0 0.32 0.32 {}
T {Both address bits are captured on the rising edge of CLK and held at A0_Q/A1_Q.} 80 -80 0 0 0.22 0.22 {}

C {sky130_stdcells/dfxtp_1.sym} 440 200 0 0 {name=XA0_FF VGND=VSS VNB=VSS VPB=VDD VPWR=VDD}
C {sky130_stdcells/dfxtp_1.sym} 840 500 0 0 {name=XA1_FF VGND=VSS VNB=VSS VPB=VDD VPWR=VDD}

C {devices/iopin.sym} 80 40 1 0 {name=p1 lab=VDD}
C {devices/iopin.sym} 180 40 1 0 {name=p2 lab=VSS}
C {devices/ipin.sym} 80 120 0 0 {name=p3 lab=CLK}
C {devices/ipin.sym} 80 210 0 0 {name=p4 lab=A0}
C {devices/ipin.sym} 80 510 0 0 {name=p5 lab=A1}
C {devices/opin.sym} 1300 190 2 0 {name=p6 lab=A0_Q}
C {devices/opin.sym} 1300 490 2 0 {name=p7 lab=A1_Q}

C {devices/lab_pin.sym} 160 80 0 0 {name=l1 lab=CLK}
C {devices/lab_pin.sym} 280 190 0 0 {name=l2 lab=CLK}
C {devices/lab_pin.sym} 680 490 0 0 {name=l7 lab=CLK}
C {devices/lab_pin.sym} 300 210 0 0 {name=l3 lab=A0}
C {devices/lab_pin.sym} 680 510 0 0 {name=l4 lab=A1}
C {devices/lab_pin.sym} 1180 190 0 0 {name=l5 lab=A0_Q}
C {devices/lab_pin.sym} 1180 490 0 0 {name=l6 lab=A1_Q}

N 80 120 200 120 {lab=CLK}
N 260 190 350 190 {lab=CLK}
N 660 490 750 490 {lab=CLK}
N 80 210 350 210 {lab=A0}
N 80 510 680 510 {lab=A1}
N 680 510 750 510 {lab=A1}
N 530 190 1180 190 {lab=A0_Q}
N 930 490 1180 490 {lab=A1_Q}
N 1180 190 1300 190 {lab=A0_Q}
N 1180 490 1300 490 {lab=A1_Q}

T {No reset is provided. Outputs are undefined until the first rising CLK edge.} 80 360 0 0 0.20 0.20 {}
