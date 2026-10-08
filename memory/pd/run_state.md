run_id:      pd_20261007_042130
design_name: sram_6t_column_32_g7_precharge_iteration
pdk:         sky130A
tool:        Magic, Netgen, ngspice
start_time:  2026-10-07T04:21:30Z
last_stage:  g7_physical_requalified_electrical_pending
status:      OPEN_POST_LAYOUT_ELECTRICAL_REQUALIFICATION
status_note: Cycle 0 checkpoint 2026-10-08: G1-G4 schematic screening and canonical sizing remain closed. Five repaired physical leafs and zero-gap bitcell abutment (normal/mirrored), 32-row core, 8-bit WL row, integrated G7 column passed fresh full-cell hierarchical/flat Magic DRC=0, unique Netgen LVS and new RC PEX. Initial 2026-10-08 bitcell Ceff, C_BL and C_WL PVT capacitance runs initialized stored state at access-side resistor taps and are INVALID FOR SIGNOFF; 519.179340 fF C_BL,max, 597.056241 fF ceiling, 102.873935 fF C_WL,max, 94 fF extra WL are DIAGNOSTIC ONLY. Repeat all three PVT classes using latch outputs .t0, recalculate 1.15x C_BL ceiling and extra WL, then run complete integrated read/write matrices. Corrected .t0 nominal TT/1.80V/27C provisional smoke read Q0 passes disturb=0.1659978V, delta=0.427048V, setup=977.22ps, t_res=0.14156ns; write Q0->Q1 passes full_flip=0.47072ns and recovery=2.83645ns. Acceptance pending read t_res<=0.25ns, disturb<=0.20V, delta>=200mV, setup>=25ps; write recovery<=4ns and WL margin. 2026-10-07 60/60 read/write and 521.626665 fF ceiling are historical and superseded. No production yield, full statistical noise, DC-SNM-PVT or macro power ceiling claim. Phase 1 OPEN.
