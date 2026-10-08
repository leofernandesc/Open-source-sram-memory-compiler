# Person 3: remaining Phase 1 tasks

Owner: Leonardo. Branch: `feature/peripherals`. Updated: 2026-10-08.
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
zero negative capacitors and current source/layout/PEX provenance. The matched
13-case schematic/PEX matrix passes at both 5 ps and 1 ps, with zero contract
findings. Full selected measurements and scope limits are in the
[compaction handoff](row_decoder_layout_compaction_20261008.md) and
[validation log](feature_peripherals_validation_log.md).

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

**Timing-budget update, 2026-10-07:** a 156-case capture-to-PCLK campaign is
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

## Ordered work and acceptance evidence

| ID | Task | Dependency | Status and next action | Completion evidence |
|---|---|---|---|---|
| P3-1 | Review retained decoder source, buffer delay and internal contract | Electrical correction | **Selected TT/SS matrix and nine FF-hot transitions complete at 5 ps/1 ps; full address-pair matrix pending.** | Current 13-case TT/SS matrix plus 9/9 FF-hot schematic/PEX cases at both steps. The FF schematic `VGD` peak is 0.963 mV below the runner's absolute terminal-difference screen, but this is not a signed PDK model-domain margin. ngspice emitted FF model-parameter warnings. Run the prepared 16-pair FF matrix on the stronger machine and review warnings before adopting a broader validity claim. See `row_decoder_fast_hot_qualification_20261008.md`. |
| P3-2 | Establish captured-address/PCLK timing budget | P3-1; control interface coordination | **Historical provisional budget; requalification pending.** Repeat capture/fanout tests with the current W=0.84 um address inverters and agree the physical PCLK source. | Archived 72/72 selected-point cases and 431.2 ps worst lead belong to their original schematic. No current setup/hold or Fmax claim. |
| P3-3 | Create decoder layout under `layout/row_decoder/` | P3-1; record PCLK pin assumptions | **Complete; current routed revision.** Nine external pins, four separate evaluation stacks, internal address literals, VDD/VSS body ties and isolated EVAL_GND are present. | `row_decoder_layout.mag`, flattened view and generation scripts; see the layout README and validation log. |
| P3-4 | Close decoder DRC | P3-3 | **Complete for the current routed revision.** Magic `drc(full)` reports zero errors after `drc catchup` on both the routed top cell and flattened view. | `reports/route.log`, `reports/drc_flat.log`; Magic 8.3.684 routing and SKY130A tech 1.0.493. |
| P3-5 | Extract devices and close decoder LVS | P3-4 | **Complete for the current routed revision.** Connectivity-only extraction matches the retained schematic uniquely; the separate P3-6 artifact contains distributed R-C parasitics. | `row_decoder_flat_extracted.spice`, `reports/lvs.log`, `reports/lvs.out`: 29 devices (17 NFET, 12 PFET), 22 nets, matching external pins and bulk nets. |
| P3-6 | Extract parasitics and repeat critical electrical tests | P3-5 | **Selected compact-layout closure complete.** Magic 8.3.684 extracted current R-C and provenance; matched 5 ps and 1 ps matrices both pass 13/13. | `layout/row_decoder/pex/extraction_manifest.json`, `pex/provenance.json`, and `sims/row_decoder/results/compact_decoder_{5ps,1ps}/`. WL buffers remain schematic and the row load is estimated at 17.4 fF; broad PVT, noise/retention and captured-address/fanout requalification remain open. |
| P3-7 | Review row loads and WL behavior with physical row | P3-6; Danilo's bitcell interface | **Blocked by missing physical input.** No `layout/bitcell_6t/` layout is present on this branch. | After Danilo supplies/reviews the physical bitcell: decoder → four WL buffers → row for every address, coupling and 50 fF stress; replace the 17.4 fF estimate with extracted data. |
| P3-8 | Complete write-driver integration checks | Valid bitcell/precharge and control sequence | **Pending owner-interface review.** Keep Danilo/André source read-only until their block interfaces are agreed. | Write 0/1, WE release/Hi-Z, both BL/BLB loads, precharge isolation and bitcell readback with schematic/PEX evidence. |
| P3-9 | Close the 4x8 transistor-level interface review | Qualified leaves from all three owners | **Pending; team dependency.** | No conflicting drivers; correct row mapping, address stability, phase sequencing and explicit rails. |
| P3-10 | Package Person 3 Phase 1 delivery | P3-4 through P3-9, or documented blocker | **Pending.** | Schematics/symbols, benches, layouts, extraction/DRC/LVS, selected CSVs, reports, dimensions, reproducible environment and limitations. |

For layout, give particular attention to PCLK coupling into the four dynamic
nodes, EVAL_GND routing resistance, floating intermediate-node capacitance,
and local routing around the address buffers. Channel-area proxies from
schematic studies are not physical layout area.

The terminal magnitude screen is not full signed model-domain or reliability
clearance. Review model bias handling and any required guardband before calling
the electrical sizing final. Noise injection and finite retention are measured
experiments; an approved noise budget, clock-stop duration and mismatch sample
policy require project-level decisions. A bitcell Monte Carlo sample count must
not silently become the decoder's statistical acceptance criterion.

## Coordination and known integration dependency

The last recorded integrated-read attempt failed while netlisting the
precharge leaf, before ngspice. Recheck the owner's latest source during the
interface review; this historical blocker is not proof that the current remote
version still fails. André owns that block. No physical bitcell layout was
found under `layout/` on this branch, so extracted row loading cannot be
completed yet. Do not silently modify either owner's source. Preserve Danilo's
bitcell sizes, testbenches, reports and layouts while consuming approved
interfaces and capacitance data.

## Proposed dates

| Date | Work |
|---|---|
| 07/10 | Capture/PCLK pre-layout timing budget measured; retain B7 and limits |
| 08/10 | Agree PCLK interface assumptions and start P3-3 decoder layout |
| 09/10 | P3-4/P3-5 decoder DRC, extraction and LVS |
| 10/10 | P3-6 PEX electrical comparisons; fix and recheck if needed |
| 11/10 | P3-7 physical row/WL checks and P3-8 write integration, subject to owner leaves |
| 12/10 | P3-9 team interface review, reproduce critical results, assemble handoff |
| 13/10 | P3-10 Phase 1 handoff with explicit completed/pending status |

The dates depend on physical closure and the other owners' leaves. Preserve
failed evidence and record a blocker if a required integration input is missing;
do not declare Phase 1 complete from leaf simulations alone.

Continue on `feature/peripherals` with focused commits. A later reviewed PR
targets `develop`; publishing or merging is a separate authorized action.
`main` receives a stable team milestone after all required blocks are reviewed.
