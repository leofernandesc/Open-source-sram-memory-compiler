v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {Captured valid-access qualifier for the dynamic decoder phase source} 80 -120 0 0 0.32 0.32 {}
T {VALID_ACCESS_D = !CSb AND (OEb XOR WEb)} 80 -80 0 0 0.24 0.24 {}

C {sky130_stdcells/inv_1.sym} 320 200 0 0 {name=XCSB_INV VGND=VSS VNB=VSS VPB=VDD VPWR=VDD}
C {sky130_stdcells/xor2_1.sym} 320 420 0 0 {name=XOE_WE_XOR VGND=VSS VNB=VSS VPB=VDD VPWR=VDD}
C {sky130_stdcells/and2_1.sym} 680 300 0 0 {name=XVALID_AND VGND=VSS VNB=VSS VPB=VDD VPWR=VDD}
C {sky130_stdcells/dfxtp_1.sym} 1000 300 0 0 {name=XVALID_FF VGND=VSS VNB=VSS VPB=VDD VPWR=VDD}

C {devices/iopin.sym} 80 40 1 0 {name=p1 lab=VDD}
C {devices/iopin.sym} 180 40 1 0 {name=p2 lab=VSS}
C {devices/ipin.sym} 80 200 0 0 {name=p3 lab=CSb}
C {devices/ipin.sym} 80 400 0 0 {name=p4 lab=OEb}
C {devices/ipin.sym} 80 440 0 0 {name=p5 lab=WEb}
C {devices/ipin.sym} 910 60 0 0 {name=p6 lab=CLK}
C {devices/opin.sym} 1450 290 2 0 {name=p7 lab=VALID_ACCESS_Q}

N 80 200 280 200 {lab=CSb}
N 80 400 260 400 {lab=OEb}
N 80 440 260 440 {lab=WEb}
N 360 200 480 200 {lab=CSB_N}
N 480 200 480 280 {lab=CSB_N}
N 480 280 620 280 {lab=CSB_N}
N 380 420 480 420 {lab=OE_WE_XOR}
N 480 320 480 420 {lab=OE_WE_XOR}
N 480 320 620 320 {lab=OE_WE_XOR}
N 740 300 820 300 {lab=VALID_ACCESS_D}
N 820 300 820 310 {lab=VALID_ACCESS_D}
N 820 310 910 310 {lab=VALID_ACCESS_D}
N 910 60 910 290 {lab=CLK}
N 1090 290 1450 290 {lab=VALID_ACCESS_Q}

T {The rising-edge DFF registers the qualified condition; live control changes cannot change Q mid-cycle.} 80 540 0 0 0.21 0.21 {}
T {No reset is present: Q is undefined until the first rising CLK edge. VPWR/VPB=VDD; VGND/VNB=VSS.} 80 570 0 0 0.19 0.19 {}
