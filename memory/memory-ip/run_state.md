run_id:      memory-ip_20260921_165204
design_name: sram_6t_cell
tool:        xschem
start_time:  2026-09-21T16:52:04-04:00
last_stage:  write_driver_functional_smoke
freeze_status: blocked
schematic_sizing_um: WPU=0.42 WPD=0.84 WACC=0.60 L=0.15
candidate_sizing_um: WPU=0.42 WPD=1.26 WACC=0.60 L=0.15
closure_sizing_status: selected_not_frozen_not_applied_to_schematic
exploratory_wpd_um: 1.05
g0_status: closed; voltage contract, post-freeze PEX, sense topology and pre-layout C_BL bound aligned
pvt_screen: 5 corners x 1.62/1.80 V x -40/27/125 C, pre-layout; 1.95 V retained as static-limit audit point only
continuous_qualification_vdd: 1.62..1.80 V
static_model_audit_limit_vdd: 1.95 V
pvt_read_50ff_wpd1p05: 72/90 PASS, worst_low_peak=0.230218 V
pvt_read_50ff_wpd1p26: 90/90 PASS, worst_low_peak=0.194778 V
pvt_write_full_swing_wpd1p26: 90/90 PASS, ideal drivers only
requested_1p98_v: outside documented 01v8 model operating range
hold_leakage_pvt_wpd1p26: 90/90 stable, worst_total=21.759 nA at fs/1.95 V/125 C
read_terminal_audit_1p95_v: 30/30 conditions exceed 1.95 V, worst=2.056858 V at sf/125 C
read_terminal_audit_1p62_v: 0/30 conditions exceed 1.95 V in current pre-layout bench
read_terminal_audit_1p80_v: 0/30 conditions exceed 1.95 V in current pre-layout bench
write_driver_netlist: PASS, headless Xschem netlist without shorts/open control nets
write_driver_standalone_tt: PASS, WE=1 drives complementary BL/BLB; WE=0 drift=3.391/1.459 mV over 3 ns with 50 fF
write_driver_integrated_screen: 12/12 switched at tt/ss/ff, 1.80 V, 27 C, both directions, WPD=0.84/1.26; Q crossing delay=0.148..0.212 ns
write_driver_screen_assumptions: Wdriver=0.84 um, CBL=50 fF, WL window=10 ns, edge=200 ps; exploratory only
engineering_vdd_target: nominal=1.80 V, continuous qualification=1.62..1.80 V; 1.95 V static audit only; 1.98 V not qualified with current 01v8 model set
engineering_read_snm_nominal_min: 0.400 V
read_snm_nominal_tt: WPD0.84=0.348804 V FAIL, WPD1.05=0.388060 V FAIL, WPD1.26=0.414349 V PASS
engineering_cbl_rule: Nrows*(Ccell_access+Cwire_per_cell)+Cprecharge+Cmux+Csense
freeze_cbl_basis: recalculated pre-layout budget with new sense input; 32-row C_BL,max=58.376530 fF under same routing constraint; electrical requalification and sense input excursion pending
pex_stage: post-schematic-freeze; requalification_ceiling=1.15*C_BL_PEX
column_organization: one word per physical row; Nrows=4/8/16/32 for 4x8/8x8/16x8/32x8
column_mux: none in current architecture, Cmux=0
cell_drain_only_cbl: rows4=0.8 fF, rows8=1.6 fF, rows16=3.2 fF, rows32=6.4 fF
engineering_wl_lower_rule: 1.30*worst 90/10 full-flip time
write_driver_timing_1p62_wpd1p26: 30/30 switched, worst_full_flip=0.3216 ns at ss/-40 C/0to1, provisional_WL_min=0.4181 ns with 50 fF
engineering_wl_upper_rule: pending sense-amp deltaV target/offset; bound by target differential plus read-disturb and bitline-excursion limits at fast condition; no dynamic-SNM gate defined
snm_mismatch_sf_mm: N=200 read at 1.62 V/125 C, N=200 hold at 1.62 V/-40 C
freeze_blockers: complete full 60 fF PVT read/write revalidation and sense input excursion; confirm sense-amp deltaV/offset/setup; close WL upper bound; define leakage/mismatch/power acceptance; integrate controls and review architecture
cbl_pre_layout_assessment: budget recalculated, gate reopened by sense-amp topology change; see docs/cbl_pre_layout_estimate.md
cbl_device_cap_pvt: 270/270 PASS at 1 MHz across 5 corners x 1.62/1.80 V x -40/27/125 C; Ccell_access_max=0.452619 fF, Cprecharge_max=0.908533 fF from existing precharge topology
cbl_routing_constraint: metal2 width=0.14 um, segment<=5.0 um/row, two-neighbor sidewall coupling, one minimum M2/M1 crossing per row, +20% wire margin
cbl_wire_budget_ff_per_cell: 1.061862
cbl_upper_bound_ff: rows4=15.971062 rows8=22.028986 rows16=34.144834 rows32=58.376530
cbl_screening_values: 5 fF small-load historical test; 50 fF historical screen does not cover 32 rows; 60 fF new exploratory screen
sense_amp_topology: seven-device regenerative latch with PMOS sampling devices W=2.0 um; supersedes former NMOS isolation candidate
sense_amp_deterministic_pvt: 330/330 PASS from Xschem-extracted cells/sense_amp.sch; ideal fixed BL/BLB, no offset/noise/yield claim
sense_input_cap_pvt: 60/60 PASS at 1 MHz with precharged BL/BLB and SCLK=0; Csense_range=7.853676..9.004605 fF; excursion/phase check pending
sense_input_cap_excursion_tt: 12/12 PASS at tt/1.80V/27C for 0/100/200mV discharge in either direction; Ceff=7.802682..8.380972 fF; not a PVT bound
bitcell_read_60ff_tt: WPD=1.26, tt/1.80V/27C, both data states PASS at 60fF; 10ns ideal WL discharges selected BL almost fully; t100=0.0638ns from WL rise, not final read pulse
bitcell_write_driver_60ff_tt: WPD=1.26, tt/1.62V/27C, 2/2 switched at 60fF; full_flip=0.288ns; +30% screening lower bound=0.374ns at this point only
leaf_peripheral_selected: precharge and WL driver passed 60fF/50fF screening at tt/1.8V/27C and ss/1.62V/-40C; WL 50% propagation=0.415/0.665ns; full PVT matrix remains open
phase1_leaf_status: open; no project leaf .mag layout or DRC/LVS evidence; see docs/phase1_leaf_cell_closure.md
g1_revalidation_scope: WPU/WPD/WACC=0.42/1.26/0.60 um, CBL=60 fF, continuous PVT 1.62..1.80 V, read-disturb plus transistor-level write driver
g1_revalidation_status: open_partial_pvt_pass_runtime_mitigated
g1_runtime_guard: read sweep supports --timeout-s (45 s default), --tran-step-ps (10 ps default), per-state selection and explicit returncode=124 on TimeoutExpired; write sweep supports per-state selection and timeout
g1_read_screening_step: 50 ps screening compared with 10 ps at tt/1.80 V/27 C/60 fF; delta21 diff=1.238109 mV, read-disturb peak diff=0.1115 mV, t100 diff=1.8 ps; use 50/100 ps only for screening, not final timing qualification
g1_read_60ff_representative: tt/1.80 V/27 C Q0/Q1 2/2 PASS; ss/1.62 V/-40 C Q0/Q1 2/2 PASS at 50 ps, low_peak=0.1071132 V, t100=0.0746 ns; ff/1.80 V/125 C Q0/Q1 2/2 PASS at 50 ps, low_peak=0.1775878 V, t100=0.0596 ns
g1_write_driver_60ff_representative: tt/1.62 V/27 C 2/2 PASS full_flip=0.288 ns; ss/1.62 V/-40 C 2/2 PASS full_flip=0.321 ns and +30%=0.417 ns; ff/1.80 V/125 C 2/2 PASS full_flip=0.246 ns and +30%=0.319 ns
g1_runner_smoke: run_g1_revalidation.py with jobs=1 at tt/1.62 V/27 C completed read/write Q0/Q1 4/4 tasks PASS using 100 ps read screening; high parallelism is not qualified on this host
g1_parallel_attempt: five concurrent corner jobs caused 60/60 read timeouts at 60 s/case from CPU contention; those timeout CSVs were discarded and are not electrical FAIL evidence
g1_revalidation_blocker: full 5-corner x 2-VDD x 3-temperature x 2-state read/write 60 fF qualification remains incomplete; screening accelerations do not replace 10 ps final timing evidence; G1 remains open
g2_status: not_started
