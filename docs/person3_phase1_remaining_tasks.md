# Person 3: remaining Phase 1 tasks

**Scope and physical closure update, 2026-10-28:** the user reconfirmed a
six-leaf Phase 1 delivery including Leonardo's existing 29-MOS decoder.
The [delivery record](phase1_six_cell_delivery.md) and
[frozen manifest](../release/phase1/manifest.json) now govern artifact selection.
Fresh DRC, primitive-MOS W/L/terminal LVS and existing-PEX connectivity binding
pass for all six delivered flat masks, including the reinforced WL/write
variants. The older task table below remains a record of the broader
integration campaign. Full 4×8 read/write/readback, complete capture/phase-source
layout/PEX and compiler work are assigned to Phase 2 by the current scope
decision. Local decoder timing-contract and model-domain acceptance remain
open electrical items; the new physical PASS does not close them.

**Current selected-pair characterization:** the
[canonical decoder/WL campaign](row_decoder_canonical_pair_requalification_20261028.md)
uses the frozen release PEX and the reinforced 1.68/5.04 µm WL driver. The
older captured-interface campaign below used the 0.42/0.84 µm driver; its
passing counts apply to those original inputs. The new local campaign excludes
capture/phase-generation circuitry and does not approve system timing.

**Local timing proposal measured, 2026-10-28:** the
[frozen-pair timing-boundary report](row_decoder_canonical_timing_limits_20261028.md)
retains 120 cases, including 20 intentional timing rejections. The selected
robustness-oriented reference point (PCLK low 3 ns, high 2.5 ns, external
address lead 2.1 ns, 50 ps ramps, 102.873935496 fF/WL) passes all 16 ordered
address pairs in TT/SS/FF: 48/48 cases and 1,392/1,392 local checks, including
the experimental 250 ps internal-literal guard. Its worst measured guard lead
is 895.224 ps in SS. The shorter 1.5 ns lead passed its 12 critical cases but
left only 41.773 ps beyond that guard, so the larger-margin point is selected
for the proposal. No sizing/layout change or new PEX was needed. Next, obtain
explicit timing/margin and signed intrinsic-model-domain disposition for this
bounded reference point; do not infer macro frequency or full bitcell access
from the local screen. Complete macro/control physical work remains Phase 2.

**Intrinsic-state follow-up measured, 2026-10-28:** the
[canonical model-state review](row_decoder_canonical_intrinsic_review_20261028.md)
now probes all 45 decoder/WL MOS in two transitions × three profiles × three
initializations: 18 main cases and 522/522 functional checks. Two passive-island
reference-resistance sensitivity cases add 58/58 passing checks. VDS/VBS remain
inside the published signed-range screen after 2 ns in the focused matrix;
NFET VGS down to -1.710505 V and PFET VGS up to +0.074380 V persist, including
with OP initialization. One passive capacitive island prevents unregularized
DC convergence; the testbench supplies a documented weak reference on that
island only, with matched UIC and 1000× resistance-sensitivity controls.
The PEX and all 211 frozen-package files remain unchanged. The recommendation
is to retain the circuit and consider a bounded experimental Phase 1 handoff
with an explicit model-domain caveat. Acceptance of that scope remains open;
these measurements do not grant full model or reliability qualification.

Owner: Leonardo. Branch: `feature/peripherals`. Updated: 2026-10-14.
Target: 2026-10-13. This is a dependency-based work plan, not evidence that a
pending check has passed. The compiler and generated macro views belong to
later phases. Danilo's bitcell and Andre's sense/precharge sources remain
read-only for this work.

See the [HTML status presentation](person3_phase1_status.html) for a concise
visual handoff of completed work and remaining tasks.

## Confirmed decoder ownership and Phase 1 scope

The decoder is Leonardo's Person 3 block for Phase 1. The dynamic 2-to-4
implementation already maintained on `feature/peripherals` remains the
implementation to finish through schematic, electrical characterization,
layout, DRC and LVS. Its current schematic is the 29-MOS design bound to the
layout and PEX documented below. The separate SPICE candidate introduced on
Danilo's branch is not a replacement for this block and does not move its
ownership or Phase 1 deliverable.

## Current task and retained evidence

**Current decoder closure, 2026-10-08:** commit `d20f509` preserves the
approved decoder schematic/sizing while compacting its layout. The current
geometry passes routed/flat DRC (0/0) and unique LVS (29 MOS, 22 nets, nine
pins). Its fresh PEX has 762 R / 389 C across all 22 resistance networks,
zero negative capacitors and current source/layout/PEX provenance. Matched
baseline/PEX matrices now cover all 16 ordered address pairs in TT, SS and FF
at 5 ps and 1 ps; all cases pass with zero contract findings. The targeted
PCLK energy refinement also passed its selected high-sensitivity pairs at
0.5 ps. A source-level review confirmed that ngspice clamps `A2`/`A1` in one
FF warning and only warns on negative `Eta0`/`Pdibl` values. The full
three-corner 1 ps operating-point matrix is now complete, along with a targeted
0.5 ps FF refinement. Every functional check passed; 10 of 16
FF baseline cases show a repeatable terminal-magnitude screen excess of at
most 1.954674 V, while all FF PEX cases pass. External-terminal `VGS`
screening remains outside the published ranges under the effective-source convention, so model-domain
qualification is still open. This is not physical-row or full-macro
qualification. See the [compaction handoff](row_decoder_layout_compaction_20261008.md),
[validation log](feature_peripherals_validation_log.md), [operating-point matrix report](row_decoder_opinit_matrix_20261008.md),
[PCLK convergence audit](../sims/row_decoder/results/compact_decoder_pclk_energy_convergence_audit.json),
and [signed-bias audit](row_decoder_signed_bias_domain_audit_20261008.md).

**Review correction, 2026-10-08:** all 116 archived OP/refinement waveforms
reproduce their signed extrema and provenance. The signed audit measures
external MOS subcircuit terminals, not exact intrinsic BSIM4 states. A new
two-device FF probe measures that difference and passes 104 functional checks.
Current-sizing characterization can proceed while final model/margin acceptance
is reviewed. Danilo's remote `d7a6ebb` contains physical bitcell/row artifacts,
but marks its first 08/10 WL-load PVT invalid for acceptance and pending corrected
latch-node initialization. The integration dependency is a corrected approved
row load. See the [analysis review](row_decoder_analysis_review_20261008.md).

**Corrected row-load input and capture/PCLK result, 2026-10-08:** Danilo's
`95c23c0` checkpoint provides a 60/60 PASS `.t0` row-capacitance matrix. Its
maximum full-row Ceff is 102.873935496 fF; source CSV and PEX hashes are in the
[requalification report](row_decoder_capture_load_requalification_20261008.md).
The value is used as a lumped output load in matched 17.4/102.874 fF
current-schematic capture tests. At 1.25 ns and 1.50 ns, the 3 ns settling
waveform checks and 250 ps literal guard pass 72/72 cases; the custom 1.95 V
screen passes 28/72. The physical row and current decoder/WL-driver PEX are
not combined in this capture bench, and owner/model acceptance remains open.

**Combined decoder/WL PEX capture study, 2026-10-09:** the current decoder
R-C PEX and four WL-driver R-C PEX instances were audited and combined with the
same 102.873935496 fF full-row load. At 1.50 ns, TT and FF pass 24/24 each;
in the original run with a 20.00 ns falling edge and 3 ns settling allowance,
all 24 SS cases miss the WL settling screen, and only 2/24 meet the 250 ps
literal guard. All 72 pass the separate 1.95 V screen, which is not reliability
signoff. A two-transition SS pilot at a 2.10 ns phase and
20.70 ns falling edge passes with a 3.3 ns screen, but does not qualify the full
matrix or approve a longer clock cycle. The later full SS phase sweep held the
20.70 ns falling edge and 3.3 ns settling allowance fixed: all 24 cases pass
functional and voltage screens at 1.50, 1.80, 1.95 and 2.10 ns, while the
250 ps literal guard passes 2/24, 13/24, 24/24 and 24/24, respectively. The
1.95 ns point is the earliest passing phase among these samples only; it is not
an approved interface limit or supported frequency. With the falling edge
fixed, the derived time from latest WL90 to PCLK fall decreases from 937 ps to
370 ps across 1.50–2.10 ns, so input lead and available WL evaluation time trade
against each other. See the [combined PEX
report](row_decoder_capture_combined_pex_20261009.md).

**Captured access qualifier, 2026-10-09:** `valid_access_capture.sch` now
implements `VALID_ACCESS_D = !CSb AND (OEb XOR WEb)` with SKY130 FD SC HD
standard cells and captures it on the rising edge of `CLK`. The Xschem
structural Verilog passed all eight control vectors, eight high-phase input
change holds, and eight falling-edge holds against the PDK functional models.
The `captured_pclk_phase_source.sch` wrapper also netlists with the qualifier
connected to the existing phase source. This is Boolean/edge-functional
evidence only: it does not measure the gate/DFF path electrically, integrate
that path in the phase PVT matrices, capture the address or write data, or
resolve startup before the first clock edge. See the [qualifier report](row_decoder_valid_access_capture_20261009.md)
and [captured-control schematic](../cells/control/valid_access_capture.sch).

**Captured qualifier to phase-source loaded screen, 2026-10-09:** the actual
SKY130 standard-cell qualifier output now drives the transistor-level phase
source, current decoder/WL PEX, and pinned Danilo precharge PEX in a paired TT
simulation. The valid-read `001`, address `0→3` case passed 342/342 checks;
capture-edge-to-PCLK differed from the Liberty-timed reference by 1.120 ps. The
invalid `000` case passed 66/66 checks and kept PCLK below 5 mV with PRECH
active. This is one valid and one invalid TT case, not a corner or interface
qualification. Setup/hold, startup, wider control/address coverage, phase
source PEX, and physical row read/write remain open. See the [loaded
interface report](row_decoder_captured_phase_interface_20261009.md) and its
[waveform comparison](../sims/row_decoder/results/captured_phase_interface_tt_read_20261009/captured_phase_vs_liberty_tt_read_a0_to_3.png).

**Historical evidence:** B7 pre-layout qualification (264 cases), the 204-case
contract campaign, 15 numerical comparisons and the captured-address budget
remain archived for their original source revisions. The current inverter,
precharge and stack sizing differs; those broad results do not qualify it.
On 2026-10-09, the current 29-MOS source was freshly netlisted and used for
414 finite-hold, charge-injection and low/high-phase-duration cases across TT,
SS and FF. The measured results and per-case evidence are in the
[current-sizing contract report](row_decoder_current_sizing_contract_20261009.md).
Those schematic screens do not replace broader crossed-PVT, captured-address/
fanout with actual PCLK, or combined physical-row work. The
[characterization record](row_decoder_contract_characterization.md)
separates archived B6/B7 evidence from these current-source experiments. Leonardo
chose electrical margin and robustness as the sizing priority. This choice is
already recorded; it does not need to be requested again.

Wordline and write drivers already have schematic/PEX experiments and local
DRC/LVS results recorded in the [validation log](feature_peripherals_validation_log.md).
Those measurements are for the documented source/layout versions and loads.
They were not rerun as independent leaf physical checks during the decoder
study. Integration with a changed decoder or physical row is a separate task.

**Historical timing-budget update, 2026-10-07:** a 156-case capture-to-PCLK campaign is
complete. At a 1.50 ns capture-to-PCLK rise delay, all 72 selected-point
cases pass the decoder logic/voltage checks and the experimental 250 ps
internal-literal guard. The worst measured lead is 431.2 ps in SS/-40 C with
the 9.00 fF Liberty DFF load; the tested WL row load is the 17.4 fF estimate.
The DFF Q waveform comes from Liberty tables, PCLK is ideal, and the DFF load
is not extracted. This gave a provisional pre-layout interface target for that historical source;
the current sizing requires the capture/fanout campaign to be repeated. It
does not validate a physical clock-generation path or external setup/hold.
Details and reproductions are in the [validation log](feature_peripherals_validation_log.md#2026-10-07-captured-address-to-pclk-timing-budget)
and [decoder characterization](row_decoder_contract_characterization.md#captured-address-to-pclk-timing-budget).
The 17.4 fF load and source revision in that archived campaign are not the
current physical-row capture result.

**Precharge/PCLK integration decision, 2026-10-09:** a fresh read-only Xschem
netlist of the existing precharge draft has no subcircuit ports and shows all
three PMOS devices disconnected; its drawn BL, BLB, and PRECH wires also meet
at one junction. That older source remains untouched. Person 3's integration
uses Danilo's corrected W2.52 leaf; its PEX is pinned as a read-only input in
this branch. The corrected ideal-source interface matrix passed 26/26 cases
and 4,660/4,660 checks, including 1,460 phase checks. A follow-up
transistor-level 24/60/80-tap phase-chain candidate passed the same 26 cases
with 3,540/3,540 checks across TT, SS, and FF. The phase source is now a
checked-in hierarchical Xschem cell, but its external CLK and VALID_ACCESS_Q
were ideal PWL in that 26-case matrix. A later six-case screen uses the
`dfxtp_1` Liberty clock-to-Q delay and output slew to shape VALID_ACCESS_Q for
one read and one write transition in TT/SS/FF; all 1,008 checks pass and the
minimum measured PRECH lead is 334.158 ps in FF. This is a timing-table model
of the captured bit's output, not a transistor-level captured-control
qualifier. The phase source has no layout or PEX, and the bench has no 6T
access path. The chosen
implementation direction is a captured, glitch-free access qualifier followed
by separate non-overlapping PCLK and PRECH phases; the tap counts and timing
are exploratory, not frozen. This work does not modify either owner's source
or change the technical specification. See the [phase decision](row_decoder_precharge_pclk_decision_20261009.md),
[precharge/PCLK review](precharge_pclk_interface_review_20261009.md),
[ideal-source phase report](row_decoder_precharge_phase_integration_20261009.md),
and [transistor phase-chain report](row_decoder_tapped_phase_generator_screen_20261009.md).

## Ordered work and acceptance evidence

| ID | Task | Dependency | Status and next action | Completion evidence |
|---|---|---|---|---|
| P3-1 | Review retained decoder source, buffer delay and internal contract | Electrical correction | **Functional and operating-point matrices complete; source-level model review complete; project/model acceptance pending.** | All 16 ordered pairs pass baseline/PEX functional checks at 5 ps and 1 ps in TT/SS/FF, and all 96 1 ps operating-point cases pass functional checks. At FF, 10 baseline cases exceed the custom 1.95 V magnitude screen by at most 4.674 mV; the 0.5 ps refinement is timestep-stable, while all matching PEX cases pass. External-terminal `VGS` screening remains outside the published model-validity ranges. The source audit documents the ngspice BSIM4 `A2`/`A1` clamp and warn-only negative `Eta0`/`Pdibl` checks; model-owner/advisor acceptance remains open. See [matrix report](row_decoder_opinit_matrix_20261008.md) and [signed-bias audit](row_decoder_signed_bias_domain_audit_20261008.md). No physical-row or reliability qualification is claimed.
| P3-2 | Establish captured-control/PCLK timing budget | Current source/PEX; control interface coordination | **The representative captured path, isolated setup/hold screen, complete valid address/control matrix, and six invalid-control vectors across TT/SS/FF are measured under a passing experimental schedule; timing qualification remains open.** The qualifier setup/hold screen retained Q for all 24/24 sampled hold cases. The complete valid matrix covers 16 ordered address pairs × two operations × three profiles: 192 actual/reference runs and 33,600/33,600 checks. The invalid matrix adds 36 actual/reference runs and 1,332/1,332 checks for `0→3`. Both matrix campaigns used a 900 ps Q sample, 1,100 ps live-input challenge, 22.5 ns external falling edge, and 3.8 ns settling allowance. | In the complete matrix, the minimum selected-WL settled level is 1.462972 V in SS, 4.972 mV above the bench's 0.9·VDD screen at 102.874 fF. A focused `1→2` SS sweep covered external falls at 22.5/24/25 ns with 3.8 ns settling and at 24/25 ns with 5.5 ns settling. At fixed 3.8 ns, the measured minimum stayed 1.462972 V; at fixed 5.5 ns it was 1.602516 V for both fall times. The three added campaigns passed 12/12 paired runs and 2,100/2,100 checks. This indicates the test's later measurement window sets the higher measured minimum; it does not establish bitcell access time or an approved margin. The captured Q excursions have no accepted limit. Control-only setup/hold brackets remain exploratory. Startup, accepted timing, physical-row data access, and phase-source layout/PEX remain open. See the [loaded interface report](row_decoder_captured_phase_interface_20261009.md), [setup/hold report](row_decoder_valid_access_setup_hold_20261009.md), [complete matrix manifest](../sims/row_decoder/results/captured_phase_interface_valid_remaining_ordered_3profile_fall22500_settle3800_q900_20261013/manifest.json), and [invalid matrix manifest](../sims/row_decoder/results/captured_phase_interface_invalid_3profile_fall22500_settle3800_q900_20261013/manifest.json). | Current PEX, captured control/address manifests and checks, waveform evidence, and dedicated reports. |
| P3-2a | Capture and route the two-bit row address | Technical specification §6/§9; dynamic decoder interface | **The two-bit `row_address_capture.sch` and composed control/phase wrapper select all four rows across all 16 old/new address pairs for valid-read `001` and valid-write `010` in TT/SS/FF; the combined valid matrices pass 33,600/33,600 checks.** The six invalid-control vectors also suppress PCLK, DEC, and WL for the tested `0→3` transition: 1,332/1,332 checks pass. Icarus passes 4/4 address captures and 8/8 hold checks. The isolated transistor-level input timing screen measures 168 A0/A1 transitions in TT/SS/FF, with 114/114 samples at nonnegative Liberty slack matching expected Q. | The full-matrix 22.5 ns falling edge and 3.8 ns settling allowance are experimental settings, not approved system timing. A focused SS study found that the selected-WL minimum is nearly unchanged as CLK fall moves from 22.5 to 25 ns at 3.8 ns settling, while a 5.5 ns settling window reports a higher minimum at both 24 and 25 ns. The latter screens a later portion of the rising pulse; it does not close bitcell access margin. Captured-Q excursions remain under review. Sampled pre-edge capture brackets are exploratory, not guaranteed setup limits. The wrapper has no reset; startup before the first rising edge and write-data capture remain open. The valid `010` cases select rows but do not exercise physical write data. See [control README](../cells/control/README.md), [row-address report](row_decoder_address_capture_20261009.md), [setup/hold report](row_decoder_address_setup_hold_20261010.md), and the [3-profile matrix report](row_decoder_captured_phase_interface_20261009.md). | `cells/control/row_address_capture.sch`, `captured_row_decoder_control.sch`, functional and PEX runners, setup/hold runner, manifests, plot, and per-check CSVs. |
| P3-3 | Create decoder layout under `layout/row_decoder/` | P3-1; record PCLK pin assumptions | **Complete; current routed revision.** Nine external pins, four separate evaluation stacks, internal address literals, VDD/VSS body ties and isolated EVAL_GND are present. | `row_decoder_layout.mag`, flattened view and generation scripts; see the layout README and validation log. |
| P3-4 | Close decoder DRC | P3-3 | **Complete for the current routed revision.** Magic `drc(full)` reports zero errors after `drc catchup` on both the routed top cell and flattened view. | `reports/route.log`, `reports/drc_flat.log`; Magic 8.3.684 routing and SKY130A tech 1.0.493. |
| P3-5 | Extract devices and close decoder LVS | P3-4 | **Complete for the current routed revision.** Connectivity-only extraction matches the retained schematic uniquely; the separate P3-6 artifact contains distributed R-C parasitics. | `row_decoder_flat_extracted.spice`, `reports/lvs.log`, `reports/lvs.out`: 29 devices (17 NFET, 12 PFET), 22 nets, matching external pins and bulk nets. |
| P3-6 | Extract parasitics and repeat critical electrical tests | P3-5 | **Current decoder/WL PEX and the complete captured valid-control/address matrix across TT/SS/FF are measured; broader qualification and model acceptance remain open.** Current decoder PEX is 29 MOS / 762 R / 389 C. Matched baseline/PEX matrices pass at 5 ps and 1 ps in TT/SS/FF; the 96-case 1 ps operating-point matrix and targeted 0.5 ps FF refinement are complete. The full SS ideal-phase sweep has 3,840/3,840 waveform checks at each of four sampled phases, but only 2/24, 13/24, 24/24 and 24/24 cases pass the separate experimental 250 ps guard. The valid captured path now covers all 16 address pairs, two controls, and three profiles: 192 actual/reference runs and 33,600/33,600 checks. The six invalid controls add 1,332/1,332 checks at `0→3`. These runs reused existing PEX; no new extraction was run. The SS `1→2` window study measured +4.972 mV at 22.5/24/25 ns clock fall with 3.8 ns settling, and +144.516 mV at 24/25 ns with 5.5 ns settling. The metric tracks the later window rather than clock-fall placement in these samples. Broader phase/settling coverage and accepted access-time criteria remain open. Captured-Q excursions, phase-source PEX, and model-domain review also remain open. Voltage screens and external-terminal model-domain review are not reliability signoff. See [combined PEX report](row_decoder_capture_combined_pex_20261009.md) and [captured phase interface report](row_decoder_captured_phase_interface_20261009.md). |
| P3-7 | Review row loads, access policy, and WL behavior with physical row | Current decoder PEX; selected Danilo precharge PEX; bitcell row interface | **The captured path uses the 102.873935496 fF WL row target and 597.056241 fF BL target, current decoder/WL PEX, and pinned read-only Danilo precharge PEX.** All 16 ordered address pairs pass for valid read/write across TT/SS/FF; the six invalid controls pass for `0→3` (1,332/1,332 checks), under the experimental candidate schedule. | The complete-matrix minimum in SS is 1.462972 V, 4.972 mV above the screen floor. The focused `1→2` study measured 1.602516 V (+144.516 mV) at 24/25 ns with 5.5 ns settling, compared with 1.462972 V (+4.972 mV) at 22.5/24/25 ns with 3.8 ns settling. This higher value reflects the later measurement window, not a like-for-like access-margin improvement. Timing and margin are not approved project limits. The `010` cases select rows but do not write into a physical bitcell. The lumped BL model remains Danilo's pinned precharge PEX plus residual capacitance. Physical bitcell read/write/readback, startup, integrated setup/hold, and phase-source layout/PEX are pending. See the [loaded interface report](row_decoder_captured_phase_interface_20261009.md), [complete valid matrix manifest](../sims/row_decoder/results/captured_phase_interface_valid_remaining_ordered_3profile_fall22500_settle3800_q900_20261013/manifest.json), [invalid matrix manifest](../sims/row_decoder/results/captured_phase_interface_invalid_3profile_fall22500_settle3800_q900_20261013/manifest.json), [initial SS waveform diagnostic](../sims/row_decoder/results/captured_phase_interface_ss_waveform_diag_20261010/ss_row3_pclk_wl3_timing.png), [address setup/hold report](row_decoder_address_setup_hold_20261010.md), and [phase-chain report](row_decoder_tapped_phase_generator_screen_20261009.md). |
| P3-8 | Complete write-driver integration checks | Valid bitcell/precharge and control sequence | **Pending owner-interface review.** Keep Danilo/André source read-only until their block interfaces are agreed. | Write 0/1, WE release/Hi-Z, both BL/BLB loads, precharge isolation and bitcell readback with schematic/PEX evidence. |
| P3-9 | Close the 4x8 transistor-level interface review | Qualified leaves from all three owners | **Pending; team dependency.** | No conflicting drivers; correct row mapping, address stability, phase sequencing and explicit rails. |
| P3-10 | Package Person 3 Phase 1 delivery | P3-4 through P3-9, or documented blocker | **Pending.** | Schematics/symbols, benches, layouts, extraction/DRC/LVS, selected CSVs, reports, dimensions, reproducible environment and limitations. |

For layout, give particular attention to PCLK coupling into the four dynamic
nodes, EVAL_GND routing resistance, floating intermediate-node capacitance,
and local routing around the address buffers. Channel-area proxies from
schematic studies are not physical layout area.

The terminal magnitude screen is not full signed model-domain or reliability
clearance. The source-level FF warning review found that ngspice clamps
`A2`/`A1` for the reported `A2 > 1` values but only warns on negative
`Eta0`/`Pdibl` values; these different effects are documented in the
[signed-bias audit](row_decoder_signed_bias_domain_audit_20261008.md).
PDK/model-owner acceptance and any required guardband are still needed before
calling the sizing fully qualified. Noise injection and finite retention are
measured experiments; an approved noise budget, clock-stop duration and
mismatch sample policy require project-level decisions. A bitcell Monte Carlo
sample count must not silently become the decoder's statistical acceptance
criterion.

### Decoder closure sequence after the operating-point matrix

1. The current-schematic study and a matched combined decoder/WL-driver PEX
   study are measured at the 102.874 fF full-row load. A four-point SS phase
   sweep at a fixed ideal 20.70 ns falling edge and 3.3 ns settling window is
   complete for all 12 transitions and both Liberty loads. The experimental
   250 ps literal guard passes all cases at 1.95 and 2.10 ns, but this does not
   define an interface limit. The 2.10 ns sample is selected as the initial
   maximin candidate and has passed the bounded interface matrix with Danilo's
   PEX. Next, use the actual PCLK source and approved system cycle to sweep
   phase and falling edge; do not claim frequency closure from ideal PWL clocks.
2. **Current-sizing schematic screens complete:** 36 finite-hold, 42 charge,
   168 low-phase and 168 high-phase cases are archived for TT, SS and FF.
   The phase minima are sampled experimental bounds; the 8 fC injection
   cases are not a system noise budget. If these conditions are retained for
   final qualification, repeat selected points with the combined current PEX,
   approved PCLK and broader crossed voltage/temperature conditions.
3. In parallel, extend targeted intrinsic-bias probes and agree acceptance
   criteria for model-domain and margin findings. This decision gates final
   qualification, not further exploratory simulation. The existing source
   review and one-case probe are in the [review report](row_decoder_analysis_review_20261008.md).
4. **Distributed decoder → WL-driver → captured-control/address path screened; final qualification is open:** four extracted eight-bit row instances pass the 48-case all-transition matrix in TT/SS/FF, and all eight control vectors pass the truth-table screen. Those tests use an ideal PCLK decision and ideal VDD clamps on BL/BLB. A separate 26-case phase-interface screen consumes Danilo’s W2.52 precharge PEX; its ideal-source version passes 4,660 checks and its transistor-level 24/60/80-tap candidate passes 3,540 checks across TT/SS/FF. The captured valid matrix now covers all 16 ordered address pairs × read/write × TT/SS/FF (96 logical cases, 192 actual/reference simulations, 33,600/33,600 checks). Six invalid controls pass `0→3` in all profiles (1,332/1,332 checks). The full valid matrix's minimum selected-WL level is 1.462972 V in SS (+4.972 mV over the screen). In a focused `1→2` study, that result stayed the same for 22.5/24/25 ns falls at 3.8 ns settling; a 5.5 ns window measured +144.516 mV at both 24 and 25 ns falls. This is a later-window screen, not bitcell access margin. The schedule is not approved timing, and captured-Q rail excursions have no accepted criterion. The phase source has no layout/PEX, and the tests do not include physical 6T data access or stored-data readback. Next, broaden the phase/settling study to the other critical transitions and relate WL arrival/hold time to the bitcell's access requirement; agree timing and margin criteria before qualification. Then complete startup/integrated setup-hold and connect the physical row for write/read/readback. The 3.3 ns, 2.10 ns, 250 ps and 1.80 ns timing values remain experimental, not project requirements.
5. If a defined condition fails or agreed margin is insufficient, review the
   responsible sizing/topology, then update affected physical checks and PEX
   when geometry changes. Otherwise retain the current decoder PEX. Package
   completed evidence and explicit open dependencies for Phase 1.

## Coordination and known integration dependency

The last recorded integrated-read attempt failed while netlisting the old
precharge leaf, before ngspice. The current `origin/feature/sense-precharge`
ref contains only `.gitkeep` placeholders under `cells/precharge/` and
`sims/precharge/`; it does not provide the candidate used in the new screen.
The old precharge schematic present on this branch is a draft and the recorded
netlisting attempt reported open nets, BL/BLB/PRECH shorts, and disconnected
MOS devices. It remains untouched. André owns the shared precharge block; the
new test uses a separate, pinned read-only copy of Danilo's extracted W2.52
PEX, selected for Person 3's integration, but does not install a team-wide
source revision. No physical bitcell read/write path is integrated in that
test. Danilo's `95c23c0`
checkpoint supplies an extracted eight-bit row PEX, already connected to
decoder/WL PEX in a bounded ideal-bitline screen. The latest owner closure on
`origin/feat/sram-6t-cell` (`5dc00fe`) aligns the current `.t0` table with the
full-row maximum of 102.873935 fF and paired extra load of 93.351918 fF. The
98.914001/89.925201 fF values remain superseded 07/10 history. Decoder tests
without an explicit row use the full-row value; the distributed-row test
models row PEX directly. The runner contains a simulation-only transistor-level
24/60/80-tap candidate. Earlier phase runs use ideal external CLK and captured
qualifier inputs. The captured qualifier now has an Xschem cell and separate
functional/electrical screens; paired TT screens have measured the composed
qualifier → phase → decoder/WL/precharge PEX path. The two-bit row-address
register now drives decoder PEX in four valid-read TT cases, selecting rows
0–3 from old row 0 (1,400/1,400 paired checks), and one valid-write TT case
(`010`, `3→0`, 350/350 checks) against Liberty references. These five cases
are row-selection screens, not all ordered address transitions or physical
bitcell data operations. A separate
168-point transistor-level address setup/hold screen covers A0/A1 rising and
falling transitions in TT/SS/FF; all 114/114 sampled points with nonnegative
Liberty slack match the expected Q value. This isolated result does not qualify
the loaded path. Wider integrated corner/control coverage, startup, and
read/write interface acceptance remain pending. The phase source has no layout
or PEX.
The 3.3 ns settling screen and selected
2.10 ns/250 ps/1.80 ns timing values remain experimental, not final decoder
timing limits. Do not silently modify either owner's source.
Preserve Danilo's bitcell sizes, testbenches, reports and layouts while
consuming approved interfaces and physical views.

## Proposed dates

| Date | Work |
|---|---|
| 07/10 | Capture/PCLK pre-layout timing budget measured; retain B7 and limits |
| 08/10 | Current decoder DRC/LVS/PEX and selected OP matrices complete; corrected row Ceff received; current-schematic capture/PCLK measured at both loads |
| 09/10 | Combined decoder/WL PEX and distributed-row matrices, ideal-source interface screen, and transistor-level tapped phase-chain candidate |
| 09/10 | Implement and functionally check the captured qualifier in Xschem; netlist the wrapper to the existing phase source |
| 09/10 | Add the two-bit captured row-address cell and compose it with the access qualifier/phase source; screen qualifier setup/hold |
| 09/10 | Connect captured A0_Q/A1_Q to decoder/WL/precharge PEX for a representative TT read and record the paired reference |
| 10/10 | Measure isolated row-address setup/hold; run valid captured-path matrix for two controls, four targets, and TT/SS/FF; 48/48 simulations and 8,400/8,400 checks pass at the experimental candidate schedule. Agree timing/margin before calling it qualified. |
| 11/10 | Replace ideal CLK/qualifier inputs in the integration bench; connect the physical bitcell row and continue write/readback integration if interfaces are available |
| 12/10 | P3-9 team interface review, reproduce critical results, assemble handoff |
| 13/10 | P3-10 Phase 1 handoff with explicit completed/pending status |

The dates depend on physical closure and the other owners' leaves. Preserve
failed evidence and record a blocker if a required integration input is missing;
do not declare Phase 1 complete from leaf simulations alone.

Continue on `feature/peripherals` with focused commits. A later reviewed PR
targets `develop`; publishing or merging is a separate authorized action.
`main` receives a stable team milestone after all required blocks are reviewed.
