run_id:      memory-ip_20261007_042159
design_name: sram_6t_column_32_g7_precharge_iteration
tool:        Magic/Netgen/ngspice
start_time:  2026-10-07T00:21:59-04:00
last_stage:  g7_engineering_scope_closure
status:      PHASE1_ENGINEERING_COMPLETE
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
freeze_blockers: none for the defined Phase 1 engineering scope: schematic freeze, G6, candidate full-column DRC/LVS/PEX, 120/120 C_BL PVT, precharge Ceff PVT, integrated read 60/60, and integrated write 60/60 are complete; production yield, full statistical-noise, DC-SNM-PVT, and macro-power ceiling are explicitly outside this closure
cbl_pre_layout_assessment_historical: budget was recalculated and reopened by the sense-amp topology change before freeze; the final physical G7 column PEX and requalification have since closed the gate; see docs/cbl_pre_layout_estimate.md
cbl_device_cap_pvt: 270/270 PASS at 1 MHz across 5 corners x 1.62/1.80 V x -40/27/125 C; Ccell_access_max=0.452619 fF, Cprecharge_max=0.908533 fF from existing precharge topology
cwrite_pvt: 120/120 PASS with extracted write_driver and WE=0; Cwrite_max=4.033129497 fF at ss/1.62 V/125 C DATA=0 BLB; tracked in sims/write_driver_capacitance_pvt.csv
cbl_routing_constraint: metal2 width=0.14 um, segment<=5.0 um/row, two-neighbor sidewall coupling, one minimum M2/M1 crossing per row, +20% wire margin
cbl_wire_budget_ff_per_cell: 1.061862
cbl_upper_bound_ff: rows4=20.004191 rows8=26.062115 rows16=38.177963 rows32=62.409659
cbl_screening_values: 5 fF and 50 fF historical; 60 fF superseded after Cwrite discovery; 65 fF current conservative pre-layout screen
sense_amp_topology: seven-device regenerative latch with PMOS sampling devices W=2.0 um; supersedes former NMOS isolation candidate
sense_amp_deterministic_pvt: 330/330 PASS from Xschem-extracted cells/sense_amp.sch; ideal fixed BL/BLB, no offset/noise/yield claim
sense_input_cap_pvt: historical standalone AC characterization 60/60 PASS at 1 MHz with precharged BL/BLB and SCLK=0; Csense_range=7.853676..9.004605 fF; integrated excursion/timing was subsequently qualified in G7 using physical 1.5x sense PEX, 60/60 read matrix; this does not claim explicit transient-noise qualification
sense_input_cap_excursion_tt: 12/12 PASS at tt/1.80V/27C for 0/100/200mV discharge in either direction; Ceff=7.802682..8.380972 fF; not a PVT bound
bitcell_read_60ff_tt: WPD=1.26, tt/1.80V/27C, both data states PASS at 60fF; 10ns ideal WL discharges selected BL almost fully; t100=0.0638ns from WL rise, not final read pulse
bitcell_write_driver_60ff_tt: WPD=1.26, tt/1.62V/27C, 2/2 switched at 60fF; full_flip=0.288ns; +30% screening lower bound=0.374ns at this point only
leaf_peripheral_selected: historical 60fF/50fF leaf screening at tt/1.8V/27C and ss/1.62V/-40C; superseded by final Wpre=2.52 precharge Ceff PVT 60/60 and integrated physical read/write PVT 60/60 each; WL 50% propagation=0.415/0.665ns is screening-only evidence
phase1_leaf_status: PHASE1_ENGINEERING_COMPLETE; schematic freeze and G6 leaf closure complete; final Wpre=2.52 full column DRC/LVS/PEX and integrated G7 read/write gates pass; see docs/phase1_leaf_cell_closure.md (product docs are maintained separately)
g6_status: CLOSED_PHYSICAL_LEAF_DRC_LVS
g6_toolchain: Magic 8.3.613 + Netgen 1.5.293, SKY130A PDK 1.0.493-0-g0fe599b in isaiassh/unic-cass-tools:1.1.0
g6_lvs: bitcell_6t=unique_match; sense_amp=unique_match; precharge=unique_match; wl_driver=unique_match; write_driver=unique_match
g6_drc: all five flattened routed leaves report 0 Magic DRC errors
g6_bitcell_abutment: zero-gap same-orientation and horizontally mirrored pair both report Magic DRC=0 via layout/bitcell_6t/check_abutment.tcl
g7_status: CLOSED_ENGINEERING_SCOPE; candidate column 120/120 C_BL PVT PASS with C_BL,PEX,max=453.588404713 fF and exact 1.15x ceiling=521.626665420 fF; integrated write=60/60 PASS (max recovery=3.49470 ns <4 ns, minimum WL-fall margin=0.34274 ns); integrated read=60/60 PASS at SCLK=4.2 ns and conservative effective CBL=521.626665420..523.083378783 fF; no production-yield, complete statistical-noise, DC-SNM-PVT, or macro-power-ceiling claim
g7_leaf_pex_capacitance: bitcell_max=8.592457068 fF/cell; precharge_max=6.525893794 fF; write_driver_off_max=26.721160015 fF; sense_input_max=28.101192527 fF; see sims/leaf_pex_capacitance_pvt.csv sims/write_driver_capacitance_pex_pvt.csv sims/sense_input_capacitance_pex_pvt.csv
g7_cbl_surrogate: superseded historical screening point; C_BL_surrogate_32=370.286455 fF and +15%=425.829423 fF were used before the physical 32-row column existed
g7_column_32_physical_historical: original layout/column_32_full had hierarchical and flat Magic DRC=0 and structural Netgen LVS unique; superseded by the strengthened G7 column below
g7_cbl_pex_historical: original column PVT AC extraction PASS=120/120; C_BL_PEX,max=422.651866875 fF and ceiling=486.049646906 fF; superseded after physical peripheral changes; see sims/column_32_full_pex_capacitance_pvt.csv
g7_precharge_layout_fix: physical p-substrate tap tied to VSS added in layout/precharge/route_precharge.tcl after PEX exposed floating VSUBS; regenerated precharge PEX has no VSUBS node and layout remains Magic DRC=0
g7_read_425ff_probe_historical: at the superseded 425.829423 fF surrogate, ss/1.62V/-40C at SCLK=4.0 ns reached delta=0.318198 V, setup=375.29 ps and t_res=0.22747 ns for stored Q=1; 90/10 rail sample is diagnostic, not a second t_res gate
g7_write_425ff_probe_historical: at superseded 425.829423 fF surrogate and earlier topology, ss/1.62V/-40C required delaying WL_IN to 7.5 ns; recovery passed only with 30 ns observation; superseded by strengthened physical candidate qualification
g7_read_486ff_historical: at the superseded 486.049647 fF ceiling, canonical sense gives t_res=0.30633/0.32127 ns and tuned_k gives 0.30800/0.32303 ns at ss/1.62V/125C; these old candidates were superseded by the physical 1.5x sense
g7_sense_scale1p5_physical_historical: experimental 1.5x regenerative latch/tail sense variant (PMOS latch 1.89 um, NMOS latch/tail 0.975 um, samplers 2.0 um) has Magic routed/flat DRC=0 and Netgen LVS unique match; the earlier strengthened-column point 520.468097 fF and critical corner t_res=0.22060/0.23257 ns are superseded by the final Wpre=2.52 column and full 60/60 integrated read matrix recorded in g7_status
g7_write_output_sizing_screen_historical: static-leaf screening at 486.049647 fF, ss/1.62V/125C showed Wout=4.20 um with full flip about 0.30432 ns; superseded by physical Wout=5.04 um integrated PEX qualification
g7_precharge_write_physical_historical: precharge Wpre=2.10 um and write output Wout=5.04 um candidates have Magic DRC=0, unique LVS and RC PEX; the 520.468097 fF critical-corner result is superseded by final Wpre=2.52 full-column PEX and integrated read/write matrices recorded in g7_status
g7_wl_physical: row_8_wl artifact has DRC=0, unique LVS and RC PEX; C_WL_ROW8_PEX,max=98.914001 fF, selected bitcell WL input max=8.988801 fF, therefore integrated post-layout extra WL load=89.925201 fF; full-column WLOFF=361.100284 fF remains a 32-WL stress diagnostic only
g7_column_strengthened_pex_historical: layout/column_32_full_g7 integrates precharge Wpre=2.10 um, write Wout=5.04 um and sense scale1p5; hierarchical and flat Magic DRC=0, Netgen LVS unique; 120/120 capacitance PVT PASS with C_BL_PEX,max=452.580954 fF and ceiling=520.468097 fF; superseded by final Wpre=2.52 column recorded in g7_status
g7_integrated_pvt_result_2026_10_06: HISTORICAL_SUPERSEDED: old precharge Wpre=2.10 candidate read=60/60 and write=56/60 with 4 recovery failures; final Wpre=2.52 candidate results are recorded in g7_write_wpre2p52_full_pvt and g7_read_wpre2p52_full_pvt
g7_write_recovery_failures_historical_superseded: sf/ss at 1.62V/-40C had four recovery failures on the Wpre=2.10 candidate; crossings were 4.03137..4.18573ns. The final Wpre=2.52 PEX candidate supersedes these results and passes integrated write 60/60 with max recovery 3.49470ns; see g7_status
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
g2_sclk_eval_window_rule_historical: worst observed mismatch resolution at 150 mV is 0.17277 ns; provisional pre-layout evaluation-high minimum=0.225 ns using +30% engineering margin, rounded to >=0.25 ns; integrated physical read control/timing subsequently passed G7 60/60
g2_direct_zero_failure_reference: p_fail<=0.1% at 95% confidence would require 2995 zero-failure decisions per independently claimed condition; current campaigns do not claim that production-level bound
g2_schematic_freeze_statistical_gate: historical pre-layout engineering screening accepted zero observed failures at the 150 mV mismatch floor (160/160 per corner, 800/800 pooled) plus full real 65 fF integrated PVT at delta>=200 mV, setup>=25 ps and t_res<=0.25 ns; one-sided 95% upper bounds are 0.3738% pooled and 1.8549% per corner; no production-yield claim; the 50 mV guard is not measured noise and may be revisited if a future explicit transient-noise study consumes it
g2_evidence: sims/sense_amp_mismatch_100mv_pvt.csv; sims/sense_amp_mismatch_150_200mv_pvt.csv; sims/sense_amp_mismatch_110_150mv_transition.csv; sims/sense_amp_sclk_setup_pvt.csv
g2_65ff_critical: adding the pre-layout WL load moved the limiting point; SCLK=2.74 ns passed 56/60 and failed ss/1.62 V/-40 C on setup/delta, while SCLK=2.79 ns passed the full 60/60 matrix; minimum setup=31.0 ps, minimum delta_at_sclk=0.26358 V, maximum t_res=0.10140 ns, maximum read_disturb=0.1450104 V
g2_65ff_critical_10ps: ss/1.62 V/-40 C and 27 C at SCLK=2.79 ns passed 4/4; limiting -40 C pair kept setup=28.46 ps, delta_at_sclk>=0.259856 V and t_res<=0.07963 ns
g2_blocker: CLOSED for schematic screening and subsequent G7 physical qualification; integrated read passed 60/60 with extracted sense/precharge/WL PEX; explicit transient-noise/yield study remains outside Phase 1
g2_runner_state: sims/run_integrated_column_read.py defaults to 65 fF, WL extra=17 fF, active SCLK=2.84 ns, workers=1 and writes resumable per-case parts before final consolidation; G2 2.79 ns result remains historical deterministic closure evidence
g3_integrated_write_status: CLOSED_65ff_WL17; 60/60 PASS across 5 corners x 2 VDD x 3 temperatures x 2 write directions with WE=2.20 ns, WL_IN=3.20 ns and WL_IN width=1.0 ns
g3_integrated_write_result: worst full_flip_from_wl50=0.37283 ns and WL_min_30pct=0.484679 ns at ss/1.62 V/-40 C; minimum full-flip margin to WL fall=0.59366 ns; output tracked in sims/integrated_column_write_65ff_wl17_wl3p2_pvt.csv
g3_integrated_write_runner: sims/run_integrated_column_write.py defaults to CBL=65 fF, WL extra=17 fF, WE=2.20 ns, WL_IN=3.20 ns, WL_IN width=1.0 ns, workers=1 and resumable per-case parts
wl_access_gate_capacitance_pvt: 120/120 PASS across 5 corners x 1.62/1.80 V x -40/27/125 C x two stored states x two source/drain orientations; Cgate_max=0.541868469 fF at ff/1.80 V/-40 C/Q0
wl_row_gate_capacitance_max: 16*Cgate_max=8.669895504 fF for an 8-bit row
wl_wire_pre_layout_bound: metal1 width=0.14 um, <=5.0 um/bit, 40 um total, two sidewall neighbors, 16 M1-M2 crossings, +20% engineering margin; CWL_wire=8.727932160 fF
wl_row_pre_layout_bound: CWL_row_max=17.397827664 fF including all 16 access gates plus wire bound
wl_integrated_bench_extra_bound: selected bitcell already contributes two access gates; remaining 14 gates plus wire give CWL_extra_max=16.314090726 fF; use 17 fF additional lumped load in integrated read/write benches
wl_load_status: pre-layout bound is historical; representative 8-bit physical WL PEX measured C_WL,max=98.914001 fF and integrated benches used 89.925201 fF extra after subtracting selected-cell contribution; read/write G7 matrices passed 60/60; full-column WLOFF remains stress-only
g7_precharge_w2p52_screen_historical_unverified: historical CSV sims/g7_write_wpre2p52_screen_4case_codex_20261007.csv reports 4/4 PASS and recovery=3.36652..3.48697ns at CBL=520.468097fF and WL extra=89.925201fF, but its wpre_um/wwrite_out_um fields are defaults 0.42/0.84 and it contains no PEX source paths or hashes; do not attribute this result to the Wpre=2.52/Wout=5.04 candidate or use it for gate closure
g7_precharge_w2p52_column_cbl: 120/120 PASS; C_BL,PEX=418.852838383..453.588404713 fF, max at ss/1.62V/125C/Q1/BL; exact +15% ceiling=521.626665420 fF; output sims/column_32_full_g7_wpre2p52_final_pex_capacitance_codex_20261007.csv
g7_precharge_w2p52_ceff_pvt: 60/60 PASS; candidate Ceff min=10.552943572 fF at fs/1.62V/-40C/BL and max=12.009656935 fF at sf/1.62V/125C/BLB; PEX SHA256=ea43e45a561d306b06e0bc100f6ecc2f600d52e03753812d3b571c29cbfbb339; sims/precharge_w2p52_pex_capacitance_precharge_only_codex_20261007.csv
g7_write_wpre2p52_full_pvt: 60/60 PASS; PEX provenance in CSV; Wpre=2.52um/Wout=5.04um, CBL CLI=521.626665 fF, WL extra=89.925201 fF, 4ns recovery; actual effective load=525.653714778..527.110428141 fF (4.027049358..5.483762721 fF above exact ceiling); max recovery=3.49470ns at sf/1.62V/-40C/Q1; max full flip=0.67063ns; min WL-fall margin=0.34274ns; sims/g7_write_wpre2p52_cbl521p626_final_codex_20261007.csv
g7_read_wpre2p52_full_pvt: 60/60 PASS; CBL exact ceiling=521.626665420 fF, subtract measured minimum candidate precharge Ceff=10.552943572 fF, WL extra=89.925201 fF, SCLK=4.2ns; effective CBL=521.626665420..523.083378783 fF; min setup=566.03ps, min delta=0.276681V, max t_res=0.23209ns at ss/1.62V/125C/Q1, max read-disturb=0.1796454V at ff/1.80V/125C/Q0, max precharge recovery=1.3821ns, WL rise slew=255.85..427.69ps/fall=102.11..159.72ps; sims/g7_read_wpre2p52_cbl521p626665_min_ceff_codex_20261007.csv; PEX source hashes and command in paired command log
g7_load_accounting: candidate precharge Ceff PVT=10.552943572..12.009656935 fF; old write subtraction=6.525893794 fF yields conservative write load above exact ceiling at every measured PVT point; final read subtracts candidate minimum, guaranteeing modeled total at or above exact ceiling with max overage=1.456713363 fF
g7_scope_limits: engineering G7 closure only; no production yield, full statistical-noise, DC-SNM-PVT, or macro-power-ceiling claim
