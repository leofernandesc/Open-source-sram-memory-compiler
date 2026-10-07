# Person 3: remaining Phase 1 tasks

Owner: Leonardo. Branch: `feature/peripherals`. Updated: 2026-10-07.
Target: 2026-10-13. This is a dependency-based work plan, not evidence that a
pending check has passed. The compiler and generated macro views belong to
later phases. Danilo's bitcell and Andre's sense/precharge sources remain
read-only for this work.

See the [HTML status presentation](person3_phase1_status.html) for a concise
visual handoff of completed work and remaining tasks.

## Current task and retained evidence

**Completed:** decoder pre-layout correction and comparison, retained B7
source, 264-case broad qualification, 204-case internal contract campaign,
15 finer numerical comparisons, fresh source reruns and 30 checker regressions.
The complete evidence remains scoped to the documented stimuli and diagnostics.
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
is not extracted. This gives a provisional pre-layout interface target; it
does not validate a physical clock-generation path or external setup/hold.
Details and reproductions are in the [validation log](feature_peripherals_validation_log.md#2026-10-07-captured-address-to-pclk-timing-budget)
and [decoder characterization](row_decoder_contract_characterization.md#captured-address-to-pclk-timing-budget).

## Ordered work and acceptance evidence

| ID | Task | Dependency | Status and next action | Completion evidence |
|---|---|---|---|---|
| P3-1 | Review retained decoder source, buffer delay and internal contract | Electrical correction | **Complete.** B7 source and declared pre-layout qualification retained. | Source hashes and bounded electrical evidence in the characterization report. |
| P3-2 | Establish captured-address/PCLK timing budget | P3-1; control interface coordination | **Provisional budget measured; integration open.** Use 1.50 ns as the tested pre-layout target, then agree and characterize the actual PCLK source and captured-address fanout. | 72/72 selected-point cases pass; 431.2 ps worst literal lead with 250 ps experimental guard. No external setup/hold or Fmax claim. |
| P3-3 | Create decoder layout under `layout/row_decoder/` | P3-1; record PCLK pin assumptions | **Complete; first routed layout.** Nine external pins, four separate evaluation stacks, internal address literals, VDD/VSS body ties and isolated EVAL_GND are present. | `row_decoder_layout.mag`, flattened view and generation scripts; see the layout README and validation log. |
| P3-4 | Close decoder DRC | P3-3 | **Complete for this layout revision.** Magic reports zero errors on the routed hierarchy and flattened layout. | `reports/route.txt`, `reports/drc_flat.txt`; Magic 8.3.589 and SKY130A tech 1.0.493. |
| P3-5 | Extract devices and close decoder LVS | P3-4 | **Complete for this layout revision.** Extracted topology matches the retained schematic uniquely. | `reports/lvs_recheck.txt`: 29 devices (17 NFET, 12 PFET), 22 nets, matching external pins and bulk nets. |
| P3-6 | Extract parasitics and repeat critical electrical tests | P3-5 | **Paused before detailed resistive extraction.** Capacitive extraction exists, but no distributed resistors or post-layout electrical comparison is accepted yet. The legacy Magic command was corrected in the script, but that correction has not been exercised; detailed extraction awaits a faster machine. | Full R-C netlist with resistance and capacitance elements, provenance/hashes, then functional, precharge, terminal, delay and energy comparisons; rerun DRC/LVS after any layout changes. |
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
