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
N 420 -80 570 -80 {lab=DEC2}
N 420 -140 500 -140 {lab=DEC0}
N 500 -240 500 -140 {lab=DEC0}
N 500 -240 700 -240 {lab=DEC0}
N 470 -120 540 -120 {lab=DEC1}
N 540 -140 540 -120 {lab=DEC1}
N 540 -140 700 -140 {lab=DEC1}
N 520 -100 550 -100 {lab=DEC3}
N 550 -100 550 -40 {lab=DEC3}
N 550 -40 700 -40 {lab=DEC3}
N 570 -80 570 60 {lab=DEC2}
N 570 60 700 60 {lab=DEC2}
N 440 -220 700 -220 {lab=#net1}
N 660 -120 700 -120 {lab=#net1}
N 660 -220 660 -120 {lab=#net1}
N 660 -20 700 -20 {lab=#net1}
N 660 -120 660 -20 {lab=#net1}
N 660 80 700 80 {lab=#net1}
N 660 -20 660 80 {lab=#net1}
N 620 20 700 20 {lab=GND}
N 620 20 620 80 {lab=GND}
N 380 80 620 80 {lab=GND}
N 380 60 380 80 {lab=GND}
N 620 -80 700 -80 {lab=GND}
N 620 -80 620 20 {lab=GND}
N 620 -180 700 -180 {lab=GND}
N 620 -180 620 -80 {lab=GND}
N 620 -280 700 -280 {lab=GND}
N 620 -280 620 -180 {lab=GND}
N 400 60 400 120 {lab=#net5}
N 400 60 460 60 {lab=#net5}
N 460 -260 460 60 {lab=#net5}
N 460 -260 700 -260 {lab=#net5}
N 480 40 480 120 {lab=#net6}
N 520 -160 700 -160 {lab=#net6}
N 560 40 560 120 {lab=#net7}
N 560 40 700 40 {lab=#net7}
N 640 -60 640 120 {lab=#net8}
N 640 -60 690 -60 {lab=#net8}
N 690 -60 700 -60 {lab=#net8}
N 560 180 640 180 {lab=GND}
N 400 180 560 180 {lab=GND}
N 380 180 400 180 {lab=GND}
N 380 80 380 180 {lab=GND}
N 510 -160 520 -160 {lab=#net6}
N 510 -160 510 40 {lab=#net6}
N 480 40 510 40 {lab=#net6}
C {/work/sims/row_decoder/results/buffered_b7_candidate/row_decoder.sym} 270 -110 0 0 {name=x1}
C {vsource.sym} 0 -240 0 0 {name=VDD_SRC value=1.8 savecurrent=false}
C {vsource.sym} 0 -150 0 0 {name=VPCLK value="PULSE(0 1.8 10n 50p 50p 10n 20n)" savecurrent=false}
C {vsource.sym} 0 -60 0 0 {name=VA0 value= "PULSE(0 1.8 22n 50p 50p 20n 40n)" savecurrent=false}
C {vsource.sym} 0 30 0 0 {name=VA1 value="PULSE(0 1.8 42n 50p 50p 40n 80n)" savecurrent=false}
C {gnd.sym} 420 20 0 0 {name=l1 lab=GND}
C {lab_pin.sym} 420 -140 0 1 {name=p1 sig_type=std_logic lab=DEC0}
C {lab_pin.sym} 470 -120 0 1 {name=p2 sig_type=std_logic lab=DEC1}
C {lab_pin.sym} 520 -100 0 1 {name=p3 sig_type=std_logic lab=DEC3}
C {lab_pin.sym} 570 -80 0 1 {name=p4 sig_type=std_logic lab=DEC2}
C {/work/cells/wordline_driver/wl_driver.sym} 850 -250 2 0 {name=x2}
C {/work/cells/wordline_driver/wl_driver.sym} 850 -150 2 0 {name=x3}
C {/work/cells/wordline_driver/wl_driver.sym} 850 -50 2 0 {name=x4}
C {/work/cells/wordline_driver/wl_driver.sym} 850 50 2 0 {name=x5}
C {devices/capa.sym} 400 150 0 0 {name=C_WL0
m=1
value=17.4f
footprint=1206
device="ceramic capacitor"}
C {devices/capa.sym} 480 150 0 0 {name=C_WL1
m=1
value=17.4f
footprint=1206
device="ceramic capacitor"}
C {devices/capa.sym} 560 150 0 0 {name=C_WL2
m=1
value=17.4f
footprint=1206
device="ceramic capacitor"}
C {devices/capa.sym} 640 150 0 0 {name=C_WL3
m=1
value=17.4f
footprint=1206
device="ceramic capacitor"}
