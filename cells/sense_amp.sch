v {xschem version=3.4.8RC file_version=1.2}
G {}
K {}
V {}
S {}
E {}
N 440 -410 440 -390 {lab=VDD}
N 440 -410 570 -410 {lab=VDD}
N 570 -410 740 -410 {lab=VDD}
N 740 -410 740 -390 {lab=VDD}
N 440 -170 440 -150 {lab=VSS}
N 440 -150 740 -150 {lab=VSS}
N 740 -170 740 -150 {lab=VSS}
N 440 -330 440 -230 {lab=SA_OUT}
N 740 -330 740 -230 {lab=SA_OUTB}
N 380 -60 410 -60 {lab=BL}
N 690 -60 710 -60 {lab=BLB}
N 440 -60 440 0 {lab=VSS}
N 740 -60 740 0 {lab=VSS}
N 440 -110 440 -100 {lab=SCLK}
N 740 -110 740 -100 {lab=SCLK}
N 590 -170 590 -150 {lab=VSS}
N 590 -110 590 -90 {lab=SCLK}
N 440 -110 740 -110 {lab=SCLK}
N 470 -60 490 -60 {lab=SA_OUT}
N 770 -60 790 -60 {lab=SA_OUTB}
N 740 -200 830 -200 {lab=VSS}
N 830 -200 830 -150 {lab=VSS}
N 740 -150 830 -150 {lab=VSS}
N 440 -200 540 -200 {lab=VSS}
N 540 -200 540 -150 {lab=VSS}
N 440 -360 510 -360 {lab=VDD}
N 510 -360 530 -360 {lab=VDD}
N 530 -410 530 -360 {lab=VDD}
N 740 -360 830 -360 {lab=VDD}
N 830 -410 830 -360 {lab=VDD}
N 740 -410 830 -410 {lab=VDD}
N 590 -430 590 -410 {lab=VDD}
N 380 -360 400 -360 {lab=SA_OUTB}
N 680 -360 700 -360 {lab=SA_OUT}
N 680 -200 700 -200 {lab=SA_OUT}
N 380 -200 400 -200 {lab=SA_OUTB}
N 420 -280 440 -280 {lab=SA_OUT}
N 720 -280 740 -280 {lab=SA_OUTB}
C {sky130_fd_pr/pfet_01v8.sym} 420 -360 0 0 {name=MP1 L=0.15 W=0.84 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 720 -360 0 0 {name=MP2 L=0.15 W=0.84 nf=1 model=pfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 420 -200 0 0 {name=MN1 L=0.15 W=0.42 nf=1 model=nfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 720 -200 0 0 {name=MN2 L=0.15 W=0.42 nf=1 model=nfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 440 -80 1 0 {name=MI1 L=0.15 W=0.30 nf=1 model=nfet_01v8 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 740 -80 1 0 {name=MI2 L=0.15 W=0.30 nf=1 model=nfet_01v8 spiceprefix=X}
C {devices/lab_pin.sym} 590 -430 1 0 {name=p4 lab=VDD}
C {devices/lab_pin.sym} 590 -170 1 0 {name=p5 lab=VSS}
C {devices/lab_pin.sym} 490 -60 2 0 {name=p6 lab=SA_OUT}
C {devices/lab_pin.sym} 790 -60 2 0 {name=p7 lab=SA_OUTB}
C {devices/lab_pin.sym} 740 0 3 0 {name=p8 lab=VSS}
C {devices/lab_pin.sym} 440 0 3 0 {name=p10 lab=VSS}
C {devices/lab_pin.sym} 680 -360 0 0 {name=p9 lab=SA_OUT}
C {devices/lab_pin.sym} 380 -360 0 0 {name=p11 lab=SA_OUTB}
C {devices/lab_pin.sym} 680 -200 0 0 {name=p12 lab=SA_OUT}
C {devices/lab_pin.sym} 380 -200 0 0 {name=p13 lab=SA_OUTB}
C {devices/lab_pin.sym} 420 -280 0 0 {name=p14 lab=SA_OUT}
C {devices/lab_pin.sym} 720 -280 0 0 {name=p15 lab=SA_OUTB}
C {C:/ProjetosSRAM/Open-source-sram-memory-compiler/devices/ipin.sym} 590 -90 3 0 {name=p16 lab=SCLK}
C {C:/ProjetosSRAM/Open-source-sram-memory-compiler/devices/iopin.sym} 380 -60 2 0 {name=p1 lab=BL}
C {C:/ProjetosSRAM/Open-source-sram-memory-compiler/devices/iopin.sym} 690 -60 2 0 {name=p2 lab=BLB}