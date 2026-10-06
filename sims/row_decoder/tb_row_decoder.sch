v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
N 0 -270 440 -270 {lab=#net1}
N 440 -270 440 -160 {lab=#net1}
N 420 -160 440 -160 {lab=#net1}
N 0 -180 100 -180 {lab=#net2}
N 100 -180 100 -160 {lab=#net2}
N 100 -160 120 -160 {lab=#net2}
N -0 -90 100 -90 {lab=#net3}
N 100 -140 100 -90 {lab=#net3}
N 100 -140 120 -140 {lab=#net3}
N -0 0 120 0 {lab=#net4}
N 120 -120 120 0 {lab=#net4}
N -40 -210 -0 -210 {lab=GND}
N -40 -210 -40 60 {lab=GND}
N -40 60 -0 60 {lab=GND}
N -40 -120 -0 -120 {lab=GND}
N -40 -30 -0 -30 {lab=GND}
N 0 60 380 60 {lab=GND}
N 380 20 380 60 {lab=GND}
N 380 20 420 20 {lab=GND}
N 420 -60 420 20 {lab=GND}
N 420 -120 470 -120 {lab=DEC1}
N 420 -100 520 -100 {lab=DEC3}
N 420 -80 570 -80 {lab=DEC3}
C {row_decoder.sym} 270 -110 0 0 {name=x1}
C {vsource.sym} 0 -240 0 0 {name=VDD_SRC value=1.8 savecurrent=false}
C {vsource.sym} 0 -150 0 0 {name=VPCLK value="PULSE(0 1.8 10n 50p 50p 10n 20n)" savecurrent=false}
C {vsource.sym} 0 -60 0 0 {name=VA0 value= "PULSE(0 1.8 22n 50p 50p 20n 40n)" savecurrent=false}
C {vsource.sym} 0 30 0 0 {name=VA1 value="PULSE(0 1.8 42n 50p 50p 40n 80n)" savecurrent=false}
C {gnd.sym} 420 20 0 0 {name=l1 lab=GND}
C {lab_pin.sym} 420 -140 0 1 {name=p1 sig_type=std_logic lab=DEC0}
C {lab_pin.sym} 470 -120 0 1 {name=p2 sig_type=std_logic lab=DEC1}
C {lab_pin.sym} 520 -100 0 1 {name=p3 sig_type=std_logic lab=DEC3}
C {lab_pin.sym} 570 -80 0 1 {name=p4 sig_type=std_logic lab=DEC2}
