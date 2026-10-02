run_id:      memory-ip_20260921_165204
design_name: sram_6t_cell
tool:        xschem
start_time:  2026-09-21T16:52:04-04:00
last_stage:  write_driver_functional_smoke
freeze_status: blocked
candidate_sizing_um: WPU=0.42 WPD=0.84 WACC=0.60 L=0.15
exploratory_wpd_um: 1.05, 1.26
pvt_screen: 5 corners x 1.62/1.80/1.95 V x -40/27/125 C, pre-layout
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
engineering_vdd_target: nominal=1.80 V, intended_sweep=1.62..1.98 V (+/-10%); 1.98 V not qualified with current 01v8 model set
engineering_read_snm_nominal_min: 0.400 V
read_snm_nominal_tt: WPD0.84=0.348804 V FAIL, WPD1.05=0.388060 V FAIL, WPD1.26=0.414349 V PASS
engineering_cbl_rule: Nrows*(0.2 fF + Cwire_per_cell)+Cprecharge+Cmux+Csense; final_ceiling=1.15*PEX
column_organization: one word per physical row; Nrows=4/8/16/32 for 4x8/8x8/16x8/32x8
column_mux: none in current architecture, Cmux=0
cell_drain_only_cbl: rows4=0.8 fF, rows8=1.6 fF, rows16=3.2 fF, rows32=6.4 fF
engineering_wl_lower_rule: 1.30*worst 90/10 full-flip time
write_driver_timing_1p62_wpd1p26: 30/30 switched, worst_full_flip=0.3216 ns at ss/-40 C/0to1, provisional_WL_min=0.4181 ns with 50 fF
snm_mismatch_sf_mm: N=200 read at 1.62 V/125 C, N=200 hold at 1.62 V/-40 C
