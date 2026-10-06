run_id:      memory-ip_20260921_165204
design_name: sram_6t_cell
tool:        xschem
start_time:  2026-09-21T16:52:04-04:00
last_stage:  leaf_layout_drc_lvs_complete_pex_ready
freeze_status: frozen_pre_layout
schematic_sizing_um: WPU=0.42 WPD=1.26 WACC=0.60 L=0.15
candidate_sizing_um: WPU=0.42 WPD=1.26 WACC=0.60 L=0.15
closure_sizing_status: frozen_applied_to_schematic
exploratory_wpd_um: 1.05
g0_status: closed_revised; voltage contract, post-freeze PEX, sense topology and corrected pre-layout C_BL bound including write-driver output capacitance aligned
pvt_screen: 5 corners x 1.62/1.80 V x -40/27/125 C, pre-layout; 1.95 V retained as static-limit audit point only
continuous_qualification_vdd: 1.62..1.80 V
static_model_audit_limit_vdd: 1.95 V
pvt_read_50ff_wpd1p05: 72/90 PASS, worst_low_peak=0.230218 V
pvt_read_50ff_wpd1p26: 90/90 PASS, worst_low_peak=0.194778 V
pvt_write_full_swing_wpd1p26: 90/90 PASS, ideal drivers only
requested_1p98_v: outside documented 01v8 model operating range
hold_leakage_pvt_wpd1p26: 90/90 stable, worst_total=21.759 nA at fs/1.95 V/125 C
hold_leakage_qualified_range: 60/60 stable over 1.62/1.80 V; worst_total=20.0676 nA and cell_VDD_power=36.1079 nW at fs/1.80 V/125 C; 32x8 bitcell-only VDD-power reference=9.2436 uW, excluding periphery
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
engineering_cbl_rule: Nrows*(Ccell_access+Cwire_per_cell)+Cprecharge+Cwrite+Cmux+Csense
freeze_cbl_basis: corrected pre-layout budget includes disabled write-driver output capacitance; 32-row C_BL,max=62.409659 fF under the same routing constraint; use 65 fF screening
pex_stage: ready_after_g6; requalification_ceiling=1.15*C_BL_PEX
column_organization: one word per physical row; Nrows=4/8/16/32 for 4x8/8x8/16x8/32x8
column_mux: none in current architecture, Cmux=0
cell_drain_only_cbl: rows4=0.8 fF, rows8=1.6 fF, rows16=3.2 fF, rows32=6.4 fF
engineering_wl_lower_rule: 1.30*worst 90/10 full-flip time
write_driver_timing_1p62_wpd1p26: 60/60 switched at 60 fF across 5 corners x 1.62/1.80 V x -40/27/125 C x both states; worst_full_flip=0.3210 ns at ss/1.62 V/-40 C; provisional_WL_min=0.4173 ns (+30%)
engineering_wl_upper_rule: integrated read uses WL_IN width=1.5 ns and active pre-layout SCLK=2.84 ns at 65 fF plus 17 fF WL extra; G2 deterministic closure at 2.79 ns remains historical evidence, but G4 mismatch exposed insufficient setup for seed 7007 at 2.79 ns; integrated write closes with WE=2.20 ns, WL_IN asserted at 3.20 ns and WL_IN width=1.0 ns
snm_mismatch_sf_mm: N=200 read at 1.62 V/125 C, N=200 hold at 1.62 V/-40 C
g4_status: CLOSED_ENGINEERING_SCREENING_PRE_LAYOUT; deterministic seed injection is applied before mismatch model load; read and write dynamic mismatch screens pass the selected critical/remaining corners with no production-yield claim
g4_seed_reproducibility: sims/g4_seed_repro_a.csv and sims/g4_seed_repro_b.csv are byte-identical; sha256=d7dda63c18e054a805a76c2d9ff1ef710e9673190ef23653059f17f0edb28a52
g4_read_timing_decision: seed 7007 at ss_mm/1.62V/-40C failed SCLK=2.79 ns on setup/delta (setup=3.66 ps, delta=0.207463 V) while SCLK=2.84 ns passed (setup=50.02 ps, delta=0.298265 V); active pre-layout read SCLK=2.84 ns
g4_read_screen: ss_mm/1.62V/-40C 10/10 PASS at SCLK=2.84 ns with disturb<=0.09247513 V, delta>=0.277567 V, setup>=41.84 ps, t_res<=0.08602 ns; ff_mm/1.80V/125C 10/10 PASS; all mismatch corners smoke at 1.62V/-40C 10/10 PASS; remaining tt_mm/fs_mm/sf_mm at 1.80V/125C 6/6 PASS
g4_write_screen: ss_mm+sf_mm at 1.62V/-40C 20/20 PASS; worst full_flip=0.39181 ns, WL_min_30pct=0.509353 ns, minimum margin_to_WL_fall=0.56732 ns; remaining tt_mm/ff_mm/fs_mm 6/6 PASS
postfreeze_regression: canonical WPD=1.26 Xschem netlist confirmed; Read SNM tt/1.80V=0.414349 V PASS; ff/1.80V/125C/65fF read-disturb 2/2 PASS worst=0.1781393 V; ss/1.62V/-40C integrated read at SCLK=2.84 ns 2/2 PASS setup>=78.46 ps delta>=0.360848 V; integrated write 2/2 PASS worst_full_flip=0.37283 ns
freeze_blockers: none for pre-layout schematic freeze; G6 physical leaf closure is complete; G7 PEX/requalification remains open because full-column post-layout sense/write timing fails at the +15% ceiling; power remains a measured architecture reference because no macro ceiling is approved
cbl_pre_layout_assessment: budget recalculated, gate reopened by sense-amp topology change; see docs/cbl_pre_layout_estimate.md
cbl_device_cap_pvt: 270/270 PASS at 1 MHz across 5 corners x 1.62/1.80 V x -40/27/125 C; Ccell_access_max=0.452619 fF, Cprecharge_max=0.908533 fF from existing precharge topology
cwrite_pvt: 120/120 PASS with extracted write_driver and WE=0; Cwrite_max=4.033129497 fF at ss/1.62 V/125 C DATA=0 BLB; tracked in sims/write_driver_capacitance_pvt.csv
cbl_routing_constraint: metal2 width=0.14 um, segment<=5.0 um/row, two-neighbor sidewall coupling, one minimum M2/M1 crossing per row, +20% wire margin
cbl_wire_budget_ff_per_cell: 1.061862
cbl_upper_bound_ff: rows4=20.004191 rows8=26.062115 rows16=38.177963 rows32=62.409659
cbl_screening_values: 5 fF and 50 fF historical; 60 fF superseded after Cwrite discovery; 65 fF current conservative pre-layout screen
sense_amp_topology: seven-device regenerative latch with PMOS sampling devices W=2.0 um; supersedes former NMOS isolation candidate
sense_amp_deterministic_pvt: 330/330 PASS from Xschem-extracted cells/sense_amp.sch; ideal fixed BL/BLB, no offset/noise/yield claim
sense_input_cap_pvt: 60/60 PASS at 1 MHz with precharged BL/BLB and SCLK=0; Csense_range=7.853676..9.004605 fF; excursion/phase check pending
sense_input_cap_excursion_tt: 12/12 PASS at tt/1.80V/27C for 0/100/200mV discharge in either direction; Ceff=7.802682..8.380972 fF; not a PVT bound
bitcell_read_60ff_tt: WPD=1.26, tt/1.80V/27C, both data states PASS at 60fF; 10ns ideal WL discharges selected BL almost fully; t100=0.0638ns from WL rise, not final read pulse
bitcell_write_driver_60ff_tt: WPD=1.26, tt/1.62V/27C, 2/2 switched at 60fF; full_flip=0.288ns; +30% screening lower bound=0.374ns at this point only
leaf_peripheral_selected: precharge and WL driver passed 60fF/50fF screening at tt/1.8V/27C and ss/1.62V/-40C; WL 50% propagation=0.415/0.665ns; full PVT matrix remains open
phase1_leaf_status: physical_complete_g6; bitcell_6t, sense_amp, precharge, wl_driver and write_driver have Magic flat DRC=0 and unique Netgen LVS matches; post-layout PEX/requalification remains open; see docs/phase1_leaf_cell_closure.md
g6_status: CLOSED_PHYSICAL_LEAF_DRC_LVS
g6_toolchain: Magic 8.3.613 + Netgen 1.5.293, SKY130A PDK 1.0.493-0-g0fe599b in isaiassh/unic-cass-tools:1.1.0
g6_lvs: bitcell_6t=unique_match; sense_amp=unique_match; precharge=unique_match; wl_driver=unique_match; write_driver=unique_match
g6_drc: all five flattened routed leaves report 0 Magic DRC errors
g6_bitcell_abutment: zero-gap same-orientation and horizontally mirrored pair both report Magic DRC=0 via layout/bitcell_6t/check_abutment.tcl
g7_status: OPEN_PEX_REQUALIFICATION; physical 32-row full column now has DRC=0, unique LVS and RC PEX, with C_BL_PEX measured; post-layout sense/write timing remains open at the +15% ceiling
g7_leaf_pex_capacitance: bitcell_max=8.592457068 fF/cell; precharge_max=6.525893794 fF; write_driver_off_max=26.721160015 fF; sense_input_max=28.101192527 fF; see sims/leaf_pex_capacitance_pvt.csv sims/write_driver_capacitance_pex_pvt.csv sims/sense_input_capacitance_pex_pvt.csv
g7_cbl_surrogate: superseded historical screening point; C_BL_surrogate_32=370.286455 fF and +15%=425.829423 fF were used before the physical 32-row column existed
g7_column_32_physical: layout/column_32_full has hierarchical and flat Magic DRC=0; structural Netgen LVS against 32 bitcells + precharge + sense_amp + write_driver reports Circuits match uniquely; see scripts/run_column_32_full_lvs.sh
g7_cbl_pex: full-column PVT AC extraction PASS=120/120; C_BL_PEX,max=422.651866875 fF at ss/1.62V/125C stored_q=1 BL; final +15% requalification ceiling=486.049646906 fF; see sims/column_32_full_pex_capacitance_pvt.csv
g7_precharge_layout_fix: physical p-substrate tap tied to VSS added in layout/precharge/route_precharge.tcl after PEX exposed floating VSUBS; regenerated precharge PEX has no VSUBS node and layout remains Magic DRC=0
g7_read_425ff_probe: ss/1.62V/-40C at SCLK=4.0 ns reaches delta=0.318198 V, setup=375.29 ps and t_res=0.22747 ns for stored Q=1, satisfying the frozen integrated delta/setup/t_res contract; 90/10 rail sample at 250 ps is retained as diagnostic and is not a second t_res gate
g7_write_425ff_probe: ss/1.62V/-40C requires delaying WL_IN to 7.5 ns for bitlines to be within 90/10 before selection; Q0->Q1 full_flip=0.84478 ns, +30% WL_min=1.098214 ns and margin_to_WL_fall=0.61943 ns, but precharge recovery fails with a 15 ns observation window and passes with 30 ns; this exceeds the <2.5 ns access objective and reopens physical drive/timing
g7_read_486ff_blocker: at the real +15% ceiling 486.049647 fF, ss/1.62V/125C canonical sense gives t_res=0.30633/0.32127 ns for Q0/Q1 at SCLK=4.2 ns, above the <=0.25 ns contract; tuned_k remains 0.30800/0.32303 ns and does not close the gate
g7_write_486ff_blocker: at 486.049647 fF and ss/1.62V/125C, the 1.0 ns WL case has WL_min_30pct up to 1.29844 ns and fails; widening WL to 1.4 ns still does not provide a clean measured full-flip event because BL/BLB are insufficiently prepared before selection; write drive must be redesigned before G7 closure
g1_revalidation_scope: WPU/WPD/WACC=0.42/1.26/0.60 um, CBL=65 fF, continuous PVT 1.62..1.80 V, read-disturb plus transistor-level write driver
g1_revalidation_status: CLOSED_65ff
g1_runtime_guard: read sweep supports --timeout-s (45 s default), --tran-step-ps (10 ps default), per-state selection and explicit returncode=124 on TimeoutExpired; write sweep supports per-state selection and timeout
g1_read_screening_step: 50 ps screening compared with 10 ps at tt/1.80 V/27 C/60 fF; delta21 diff=1.238109 mV, read-disturb peak diff=0.1115 mV, t100 diff=1.8 ps; use 50/100 ps only for screening, not final timing qualification
g1_read_60ff_representative: tt/1.80 V/27 C Q0/Q1 2/2 PASS; ss/1.62 V/-40 C Q0/Q1 2/2 PASS at 50 ps, low_peak=0.1071132 V, t100=0.0746 ns; ff/1.80 V/125 C Q0/Q1 2/2 PASS at 50 ps, low_peak=0.1775878 V, t100=0.0596 ns
g1_write_driver_60ff_representative: tt/1.62 V/27 C 2/2 PASS full_flip=0.288 ns; ss/1.62 V/-40 C 2/2 PASS full_flip=0.321 ns and +30%=0.417 ns; ff/1.80 V/125 C 2/2 PASS full_flip=0.246 ns and +30%=0.319 ns
g1_read_60ff_full_pvt: 60/60 PASS screening; worst read_disturb_peak=0.1775878 V at ff/1.80 V/125 C; slowest t100=0.0846 ns and minimum delta21=1.4803251 V at ss/1.62 V/125 C; tracked in sims/bitcell_read_60ff_pvt_screen.csv
g1_write_driver_60ff_full_pvt: 60/60 initialized and switched; worst full_flip=0.3210 ns, WL_min_30pct=0.4173 ns at ss/1.62 V/-40 C; tracked in sims/bitcell_write_driver_60ff_pvt.csv
g1_read_10ps_envelope: ss/1.62 V/125 C Q0/Q1 2/2 PASS, t100=0.0869 ns, read_disturb_peak=0.137403 V; ff/1.80 V/125 C Q0/Q1 2/2 PASS, t100=0.0610 ns, read_disturb_peak=0.1776892 V; tracked in sims/bitcell_read_60ff_ss_1p62_125_final_10ps.csv and sims/bitcell_read_60ff_ff_1p8_125_final_10ps.csv
g1_runner_smoke: run_g1_revalidation.py with jobs=1 at tt/1.62 V/27 C completed read/write Q0/Q1 4/4 tasks PASS using 100 ps read screening; high parallelism is not qualified on this host
g1_parallel_attempt: five concurrent corner jobs caused 60/60 read timeouts at 60 s/case from CPU contention; those timeout CSVs were discarded and are not electrical FAIL evidence
g1_60ff_historical_result: CLOSED; read screening 60/60 PASS and transistor-level write 60/60 PASS at 60 fF across 5 corners x 2 VDD x 3 temperatures x 2 states; superseded as the active gate after Cwrite increased the pre-layout screen to 65 fF
g1_65ff_result: CLOSED; read screening 60/60 PASS and transistor-level write 60/60 PASS at 65 fF across 5 corners x 2 VDD x 3 temperatures x 2 states; worst 50 ps read-disturb=0.1780729 V at ff/1.80 V/125 C, slowest t100=0.0888 ns at ss/1.62 V/125 C, worst write full_flip=0.3194 ns and WL_min_30pct=0.41522 ns at ss/1.62 V/-40 C
g1_65ff_critical_10ps: read ss/1.62 V/125 C passed both states with t100=0.0910 ns; read ff/1.80 V/125 C passed both states with read-disturb=0.1781393 V; write ss/1.62 V/-40 C passed both directions with full_flip=0.3192 ns and WL_min_30pct=0.41496 ns
g2_status: CLOSED_65ff_WL17; full integrated read PVT passed 60/60 at CBL=65 fF, WL extra=17 fF and SCLK=2.79 ns
g2_mismatch_100mv: 480/500 PASS across tt_mm/ff_mm/ss_mm/fs_mm/sf_mm at 1.62 V/125 C, 50 samples per corner x both polarities; 100 mV is rejected as the G2 target
g2_mismatch_150mv: 300/300 PASS across tt_mm/ff_mm/ss_mm/fs_mm/sf_mm at 1.62 V/125 C, 30 samples per corner x both polarities; worst t_res_from_sclk50=0.17277 ns at ss_mm
g2_mismatch_200mv: 300/300 PASS across the same mismatch matrix; retained as additional margin evidence, not required by current provisional target
g2_mismatch_transition_110_150mv: 2486/2500 PASS; aggregate failures by delta were 110mV=3/500, 120mV=6/500, 130mV=4/500, 140mV=1/500, 150mV=0/500; therefore 150 mV is the smallest tested all-corner zero-failure transition point in this campaign
g2_mismatch_150mv_combined: 800/800 PASS combining the prior 300 decisions with the 500-decision transition campaign; one-sided 95% zero-failure upper bound is 0.3738% pooled and 1.8549% per corner at N=160/corner; engineering screening evidence, not production-yield signoff
g2_delta_v_target: provisional=200 mV at the real bitline pair; reserve 50 mV as a pre-layout input-referred uncertainty/noise guard, leaving an effective 150 mV mismatch floor; this guard is an engineering allocation, not measured transient-noise signoff
g2_sclk_setup_pvt: at deltaV=150 mV and 50 ps input slew, 0/25/50/100/200 ps setup to SCLK50 each passed 60/60 across 5 corners x 1.62/1.80 V x -40/27/125 C x both polarities; -50 ps passed 58/60 and -100 ps 0/60
g2_sclk_setup_rule: require differential established no later than SCLK 50% crossing; use >=25 ps as provisional engineering guard because 0 ps has no timing margin
g2_sclk_eval_window_rule: worst observed mismatch resolution at 150 mV is 0.17277 ns; provisional evaluation-high minimum=0.225 ns using +30% engineering margin, round to >=0.25 ns pending integrated control validation
g2_direct_zero_failure_reference: p_fail<=0.1% at 95% confidence would require 2995 zero-failure decisions per independently claimed condition; current campaigns do not claim that production-level bound
g2_schematic_freeze_statistical_gate: engineering screening accepts zero observed failures at the 150 mV mismatch floor (160/160 per corner, 800/800 pooled) plus full real 65 fF integrated PVT at delta>=200 mV, setup>=25 ps and t_res<=0.25 ns; one-sided 95% upper bounds are 0.3738% pooled and 1.8549% per corner; no production-yield claim and 50 mV guard reopens after PEX or explicit transient-noise consumption
g2_evidence: sims/sense_amp_mismatch_100mv_pvt.csv; sims/sense_amp_mismatch_150_200mv_pvt.csv; sims/sense_amp_mismatch_110_150mv_transition.csv; sims/sense_amp_sclk_setup_pvt.csv
g2_65ff_critical: adding the pre-layout WL load moved the limiting point; SCLK=2.74 ns passed 56/60 and failed ss/1.62 V/-40 C on setup/delta, while SCLK=2.79 ns passed the full 60/60 matrix; minimum setup=31.0 ps, minimum delta_at_sclk=0.26358 V, maximum t_res=0.10140 ns, maximum read_disturb=0.1450104 V
g2_65ff_critical_10ps: ss/1.62 V/-40 C and 27 C at SCLK=2.79 ns passed 4/4; limiting -40 C pair kept setup=28.46 ps, delta_at_sclk>=0.259856 V and t_res<=0.07963 ns
g2_blocker: CLOSED for pre-layout schematic screening at 65 fF plus 17 fF WL extra; reopen after PEX or if explicit transient-noise analysis consumes the 50 mV guard
g2_runner_state: sims/run_integrated_column_read.py defaults to 65 fF, WL extra=17 fF, active SCLK=2.84 ns, workers=1 and writes resumable per-case parts before final consolidation; G2 2.79 ns result remains historical deterministic closure evidence
g3_integrated_write_status: CLOSED_65ff_WL17; 60/60 PASS across 5 corners x 2 VDD x 3 temperatures x 2 write directions with WE=2.20 ns, WL_IN=3.20 ns and WL_IN width=1.0 ns
g3_integrated_write_result: worst full_flip_from_wl50=0.37283 ns and WL_min_30pct=0.484679 ns at ss/1.62 V/-40 C; minimum full-flip margin to WL fall=0.59366 ns; output tracked in sims/integrated_column_write_65ff_wl17_wl3p2_pvt.csv
g3_integrated_write_runner: sims/run_integrated_column_write.py defaults to CBL=65 fF, WL extra=17 fF, WE=2.20 ns, WL_IN=3.20 ns, WL_IN width=1.0 ns, workers=1 and resumable per-case parts
wl_access_gate_capacitance_pvt: 120/120 PASS across 5 corners x 1.62/1.80 V x -40/27/125 C x two stored states x two source/drain orientations; Cgate_max=0.541868469 fF at ff/1.80 V/-40 C/Q0
wl_row_gate_capacitance_max: 16*Cgate_max=8.669895504 fF for an 8-bit row
wl_wire_pre_layout_bound: metal1 width=0.14 um, <=5.0 um/bit, 40 um total, two sidewall neighbors, 16 M1-M2 crossings, +20% engineering margin; CWL_wire=8.727932160 fF
wl_row_pre_layout_bound: CWL_row_max=17.397827664 fF including all 16 access gates plus wire bound
wl_integrated_bench_extra_bound: selected bitcell already contributes two access gates; remaining 14 gates plus wire give CWL_extra_max=16.314090726 fF; use 17 fF additional lumped load in integrated read/write benches
wl_load_status: pre-layout bound closed for schematic screening; former 50 fF WL load retained only as conservative stress evidence; replace this estimate with extracted parasitics after schematic freeze/layout and reopen if geometry exceeds the documented routing bound
