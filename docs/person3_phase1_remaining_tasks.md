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
| P3-3 | Create decoder layout under `layout/row_decoder/` | P3-1; record PCLK pin assumptions | **Pending; next.** Route nine named ports, regenerated literals, four distinct stack nodes, body ties and isolated EVAL_GND. | Saved Magic source and reviewed interface/rail connectivity. |
| P3-4 | Close decoder DRC | P3-3 | **Pending.** | Saved Magic/rule-deck versions and zero-error report, including hierarchy checks. |
| P3-5 | Extract and close decoder LVS | P3-4 | **Pending.** | Unique Netgen match to retained schematic, all 29 devices, dimensions, supplies and body pins. |
| P3-6 | Extract parasitics and repeat critical electrical tests | P3-5 | **Pending.** | PEX hashes plus logic, false-row, precharge, terminal, delay and energy comparisons; rerun DRC/LVS after changes. |
| P3-7 | Review row loads and WL behavior with physical row | P3-6; Danilo's bitcell interface | **Pending.** Test decoder → four WL buffers → row for every address; include coupling and 50 fF stress. Replace 17.4 fF estimate with extracted data. | Output levels, slew, delay and coupling from physical row extraction. |
| P3-8 | Complete write-driver integration checks | Valid bitcell/precharge and control sequence | **Pending.** Preserve other owners' source; integrate when leaves are ready. | Write 0/1, WE release/Hi-Z, both BL/BLB loads, precharge isolation and bitcell readback with schematic/PEX evidence. |
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
precharge leaf, before ngspice. Recheck the owner's latest source when it is
ready. This historical blocker is not proof that the current remote version
still fails. Andre owns that correction; Leonardo's decoder work must not
silently repair or change it. Preserve Danilo's bitcell sizes, testbenches,
reports and layouts while consuming their approved interfaces and capacitance
data.

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
