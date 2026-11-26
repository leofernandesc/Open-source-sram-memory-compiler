run_id:      pd_20261125_235019
design_name: sram_4x8_phase6_peripheral_area_candidate
pdk:         sky130A
tool:        Magic, Netgen, ngspice, gdstk
start_time:  2026-11-25T23:50:19-04:00
last_stage:  baseline_capture
status:      IN_PROGRESS
active_stage: dimensional_physical_inventory
baseline:    physical v6 snapshot from phase3_evidence_20261124, GDS SHA-256 315c2ebceb2bc4cf258fa63be2279843805db3010637d0c273aea9db12813e37
scope:       exploratory peripheral placement/area study; preserve v6 and Fase 1/2 selections
qualification: NOT_CHARACTERIZED
signoff_achieved: false
baseline_artifacts: build/phase6_area_p6_20261125/baseline/manifest.json; 11 hashes verified
status_note: P6/D1 physical 8x8 and 32x8 candidates are absent. Existing evidence is digital-model-only for those depths. Area optimization remains exploratory and has no approved reduction target. The v6 baseline is captured read-only; no candidate geometry has been generated.

## Archived previous run

run_id:      pd_20261007_042130
design_name: sram_6t_column_32_g7_precharge_iteration
pdk:         sky130A
tool:        Magic, Netgen, ngspice
start_time:  2026-10-07T04:21:30Z
last_stage:  g7_integrated_read_write_60of60_engineering_qualification
status:      CLOSED_ENGINEERING_QUALIFICATION
active_stage: cycle4_final_audit_complete
status_note: Phase 1 qualification applies only to the bitcell and physical-leaf scope. Selected leaves, 8-bit WL row and 32-row column have fresh hierarchical/flat Magic DRC=0, unique Netgen LVS and RC PEX. C_BL,PEX,max=519.179340 fF; test limit=597.056240839 fF; WL extra=93.351918068 fF. Integrated read and write pass 60/60 each; 1 ps critical refinements pass. This is not macro sign-off and makes no production-yield, full-noise, DC-SNM-PVT or macro-power-ceiling claim.
