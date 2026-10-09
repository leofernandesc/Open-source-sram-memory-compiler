# Person 3: remaining Phase 1 tasks

Owner: Leonardo. Branch: `feature/peripherals`. Updated: 2026-10-09.
Target: 2026-10-13. This is a dependency-based work plan, not evidence that a
pending check has passed. The compiler and generated macro views belong to
later phases. Danilo's bitcell and Andre's sense/precharge sources remain
read-only for this work.

See the [HTML status presentation](person3_phase1_status.html) for a concise
visual handoff of completed work and remaining tasks.

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

**Historical evidence:** B7 pre-layout qualification (264 cases), the 204-case
contract campaign, 15 numerical comparisons and the captured-address budget
remain archived for their original source revisions. The current inverter,
precharge and stack sizing differs; those broad results do not qualify it.
Repeat the relevant PVT, noise/retention and captured-address/fanout campaigns
before extending the selected decoder closure to those operating conditions.
The [characterization record](row_decoder_contract_characterization.md)
separates archived B6 schedule-specific results from new simultaneous-address,
numeric-accuracy and buffered-address experiments. Leonardo chose electrical
margin and robustness as the sizing priority. This choice is already recorded;
it does not need to be requested again.

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

## Ordered work and acceptance evidence

| ID | Task | Dependency | Status and next action | Completion evidence |
|---|---|---|---|---|
| P3-1 | Review retained decoder source, buffer delay and internal contract | Electrical correction | **Functional and operating-point matrices complete; source-level model review complete; project/model acceptance pending.** | All 16 ordered pairs pass baseline/PEX functional checks at 5 ps and 1 ps in TT/SS/FF, and all 96 1 ps operating-point cases pass functional checks. At FF, 10 baseline cases exceed the custom 1.95 V magnitude screen by at most 4.674 mV; the 0.5 ps refinement is timestep-stable, while all matching PEX cases pass. External-terminal `VGS` screening remains outside the published model-validity ranges. The source audit documents the ngspice BSIM4 `A2`/`A1` clamp and warn-only negative `Eta0`/`Pdibl` checks; model-owner/advisor acceptance remains open. See [matrix report](row_decoder_opinit_matrix_20261008.md) and [signed-bias audit](row_decoder_signed_bias_domain_audit_20261008.md). No physical-row or reliability qualification is claimed.
| P3-2 | Establish captured-address/PCLK timing budget | Current source/PEX; control interface coordination | **Current schematic measured; PEX and broader edge/phase sweep pending.** Matched 17.4/102.874 fF matrices pass waveform logic and the 250 ps literal guard at 1.25 ns; the corrected-load run also passes at 1.50 ns. Use 1.50 ns as a provisional next-study point, then repeat with decoder and WL-driver PEX if their extracted interfaces can be combined. Review the physical PCLK source. | Current-source netlist hash `2c8e802f...`; 72/72 logic and guard cases at both selected phases, but only 28/72 pass the custom voltage screen. Q uses Liberty-derived PWL, PCLK is ideal, row load is lumped Ceff and DFF load is not extracted. No external setup/hold or Fmax claim. See [requalification report](row_decoder_capture_load_requalification_20261008.md). |
| P3-3 | Create decoder layout under `layout/row_decoder/` | P3-1; record PCLK pin assumptions | **Complete; current routed revision.** Nine external pins, four separate evaluation stacks, internal address literals, VDD/VSS body ties and isolated EVAL_GND are present. | `row_decoder_layout.mag`, flattened view and generation scripts; see the layout README and validation log. |
| P3-4 | Close decoder DRC | P3-3 | **Complete for the current routed revision.** Magic `drc(full)` reports zero errors after `drc catchup` on both the routed top cell and flattened view. | `reports/route.log`, `reports/drc_flat.log`; Magic 8.3.684 routing and SKY130A tech 1.0.493. |
| P3-5 | Extract devices and close decoder LVS | P3-4 | **Complete for the current routed revision.** Connectivity-only extraction matches the retained schematic uniquely; the separate P3-6 artifact contains distributed R-C parasitics. | `row_decoder_flat_extracted.spice`, `reports/lvs.log`, `reports/lvs.out`: 29 devices (17 NFET, 12 PFET), 22 nets, matching external pins and bulk nets. |
| P3-6 | Extract parasitics and repeat critical electrical tests | P3-5 | **Decoder PEX extraction and functional matrices complete; capture bench remains schematic; acceptance pending.** | Current decoder PEX is 29 MOS / 762 R / 389 C. Matched baseline/PEX matrices pass at 5 ps and 1 ps in TT/SS/FF. The full 96-case 1 ps operating-point matrix is complete; a targeted 10-pair FF refinement at 0.5 ps confirms the baseline custom screen excess is timestep-stable and all matching PEX pairs pass. External-terminal `VGS` excursions and baseline PFET `VBS` findings remain outside at least one published signed model-validity interval under the audited convention; ngspice's FF parameter-warning behavior is documented. Project/model-owner acceptance remains open. New capture/PCLK runs use schematic WL buffers and lumped row Ceff, not the decoder PEX. |
| P3-7 | Review row loads and WL behavior with physical row | Current decoder PEX; approved bitcell/row electrical input | **Corrected row-capacitance evidence received and used as a lumped bench load; physical integration and owner acceptance pending.** Danilo's `95c23c0` provides 60/60 PASS `.t0` data, with maximum full-row Ceff 102.873935496 fF and maximum paired additional load 93.351918068 fF. | Join decoder → four WL drivers → physical row or reviewed distributed model for each address and coupling condition. Check all four WL paths and deassertion against actual CLK/PCLK, access enable and BL/BLB precharge. Preserve the captured CSV/hash; its lumped-cap use is not completed physical integration. |
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

1. The current-schematic captured-address/PCLK study is measured at 17.4 and
   102.874 fF, at 1.25 and 1.50 ns. Next, combine current decoder and WL-driver
   PEX if the extracted interfaces permit, then measure address/clock edge and
   phase sensitivity while keeping the model screens visible.
2. Repeat current-sizing noise, retention and phase-duration experiments.
   Cover crossed voltage/temperature conditions as diagnostics; the three
   existing PVT points are not a complete characterization grid.
3. In parallel, extend targeted intrinsic-bias probes and agree acceptance
   criteria for model-domain and margin findings. This decision gates final
   qualification, not further exploratory simulation. The existing source
   review and one-case probe are in the [review report](row_decoder_analysis_review_20261008.md).
4. Integrate the corrected extracted bitcell/row load and evaluate all four
   decoder-to-WL paths. The maximum full-row Ceff is available and has been
   modeled as a lumped load; check distributed coupling and WL deassertion
   against actual CLK/PCLK, access enable and BL/BLB precharge. The 1 ns and
   exploratory 3 ns settling allowances are not project specifications.
   Coordinate the integrated read/write interface with the owners.
5. If a defined condition fails or agreed margin is insufficient, review the
   responsible sizing/topology, then update affected physical checks and PEX
   when geometry changes. Otherwise retain the current decoder PEX. Package
   completed evidence and explicit open dependencies for Phase 1.

## Coordination and known integration dependency

The last recorded integrated-read attempt failed while netlisting the
precharge leaf, before ngspice. Recheck the owner's latest source during the
interface review; this historical blocker is not proof that the current remote
version still fails. André owns that block. No physical bitcell layout is
integrated on this branch. Danilo's `95c23c0` checkpoint now supplies the
corrected latch-initialized (`.t0`) eight-bit row Ceff matrix; its source and
hash are recorded in the [load report](row_decoder_capture_load_requalification_20261008.md).
Owner acceptance and connection to the physical row remain pending. The
provisional 08/10 and superseded 07/10 values are not final decoder limits.
Do not silently modify either owner's source. Preserve Danilo's
bitcell sizes, testbenches, reports and layouts while consuming approved
interfaces and capacitance data.

## Proposed dates

| Date | Work |
|---|---|
| 07/10 | Capture/PCLK pre-layout timing budget measured; retain B7 and limits |
| 08/10 | Current decoder DRC/LVS/PEX and selected OP matrices complete; corrected row Ceff received; current-schematic capture/PCLK measured at both loads |
| 09/10 | Combine decoder/WL-driver PEX for capture/PCLK if feasible; extend edge/phase sensitivity and begin noise/retention tests |
| 10/10 | Current-sizing noise/retention/phase-duration and additional PVT diagnostics; model criteria review in parallel |
| 11/10 | P3-7 physical row/WL and P3-8 write integration after review of corrected owner inputs |
| 12/10 | P3-9 team interface review, reproduce critical results, assemble handoff |
| 13/10 | P3-10 Phase 1 handoff with explicit completed/pending status |

The dates depend on physical closure and the other owners' leaves. Preserve
failed evidence and record a blocker if a required integration input is missing;
do not declare Phase 1 complete from leaf simulations alone.

Continue on `feature/peripherals` with focused commits. A later reviewed PR
targets `develop`; publishing or merging is a separate authorized action.
`main` receives a stable team milestone after all required blocks are reviewed.
