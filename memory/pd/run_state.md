run_id:      pd_20261007_042130
design_name: sram_6t_column_32_g7_precharge_iteration
pdk:         sky130A
tool:        Magic, Netgen, ngspice
start_time:  2026-10-07T04:21:30Z
last_stage: g7_integrated_read_write_60of60_engineering_qualification
status: CLOSED_ENGINEERING_QUALIFICATION
active_stage: cycle4_final_audit_complete
status_note: Cycle 4 audit 2026-10-08: Phase 1 CLOSED_ENGINEERING_QUALIFICATION for the bitcell and physical-leaf scope. Selected leafs, 8-bit WL row and 32-row column retain fresh hierarchical/flat Magic DRC=0, unique Netgen LVS and RC PEX. Access-tap initialization capacitance results remain INIT_INVALID historical diagnostics; corrected latch-output .t0 PVTs and current hashes are verified. C_BL,PEX,max=519.179340 fF; test limit=597.056240839 fF; WL extra=93.351918068 fF. Integrated read and write pass 60/60 each; 1 ps critical refinements pass. A provisional dynamic 2-to-4 decoder SPICE candidate now exists at cells/row_decoder_2to4.spice; its electrical/physical qualification and the 4x8 macro remain Phase 2 work. No production-yield, full-noise, DC-SNM-PVT or macro-power-ceiling claim.
manual_drc_lvs_2026_10_08: Magic GUI bitcell Total DRC errors found=0 (operator screenshot); G7 hierarchical and flat full-cell DRC=0/0 (audit_full_drc_requal.log). Initial Netgen manual LVS with /dev/null is historical; rerun with /opt/pdks/sky130A/libs.tech/netgen/sky130A_setup.tcl inside tool container read setup and returned Circuits match uniquely, 212 MOS (136 NMOS, 76 PMOS) and 82 nets per side. Undefined MOS subcircuit/placeholder and missing-property warnings persisted, limiting confirmation to structural equivalence. Operator copied local log to layout/column_32_full_g7_wpre2p52_final/lvs_sky130_manual.log (Git-ignored). See docs/validacao_manual_drc_lvs_sky130a.md.
