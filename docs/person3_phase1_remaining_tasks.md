# Person 3: remaining Phase 1 tasks

Owner: Leonardo. Branch: `feature/peripherals`. Updated: 2026-10-07.
Target: 2026-10-13. This is a dependency-based work plan, not evidence that a
pending check has passed. The compiler and generated macro views belong to
later phases. Danilo's bitcell and Andre's sense/precharge sources remain
read-only for this work.

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

## Ordered work and acceptance evidence

| ID | Task | Dependency | Completion evidence |
|---|---|---|---|
| P3-1 | Review the retained decoder source, buffer delay and internal timing contract | Current electrical correction | Approved topology/interface, source hashes and recorded scope of electrical qualification; address must settle before evaluation |
| P3-2 | Establish a credible captured-address/PCLK driver and integration timing budget | P3-1; control interface coordination | Measured register/driver edges, decoder address lead and low/high phases; no claim of external setup or Fmax from ideal-source leaf tests |
| P3-3 | Create the decoder layout under `layout/row_decoder/` | P3-1 | Magic source with VDD/VSS body ties, nine named ports, buffered literals, four distinct stack nodes and isolated EVAL_GND |
| P3-4 | Close decoder DRC | P3-3 | Saved Magic/rule-deck versions and an actual zero-error report for the retained layout, including hierarchy checks |
| P3-5 | Extract and close decoder LVS | P3-4 | Netgen unique match to the retained schematic, including all 29 devices if the buffered candidate is adopted, dimensions and explicit supply/body connections |
| P3-6 | Extract parasitics and repeat critical electrical tests | P3-5 | PEX hashes, logic/false-row/precharge/terminal checks, delay and energy comparisons; repeat DRC/LVS after any source/layout change |
| P3-7 | Review row loads and WL behavior with the retained decoder and physical row | P3-6; Danilo's bitcell interface | Decoder -> four existing WL buffers -> row load: all addresses, output levels, slew, delay and coupling. Re-estimate 17.4 fF after physical data; 50 fF remains a stress point |
| P3-8 | Complete write-driver integration checks | Valid bitcell/precharge and control sequencing | Write 0/1, write enable release/Hi-Z, both BL/BLB loads, precharge isolation and bitcell readback, with schematic/PEX evidence |
| P3-9 | Close the 4x8 transistor-level interface review | Qualified leaves from all three owners | No simultaneous conflicting drivers; correct row mapping, address stability, phase sequencing and explicit rails; no automatic edits to other owners' cells |
| P3-10 | Package the Person 3 Phase 1 delivery | P3-4 through P3-9, or explicit documented integration blocker | Retained schematics/symbols, benches, layouts, extraction/DRC/LVS evidence, selected CSVs, reports, dimensions, reproducible environment and remaining limitations |

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
| 07/10 | Complete the current decoder comparison and record the retained candidate and test limits |
| 08/10 | P3-1/P3-2 review and P3-3 layout |
| 09/10 | P3-4/P3-5 DRC, extraction and LVS |
| 10/10 | P3-6 PEX electrical comparisons and any corrective iteration |
| 11/10 | P3-7/P3-8 row/write integration, subject to other leaves being ready |
| 12/10 | P3-9 review, reproduce critical results and assemble delivery |
| 13/10 | P3-10 Phase 1 handoff with explicit completed/pending status |

The dates depend on physical closure and the other owners' leaves. Preserve
failed evidence and record a blocker if a required integration input is missing;
do not declare Phase 1 complete from leaf simulations alone.

Continue on `feature/peripherals` with focused commits. A later reviewed PR
targets `develop`; publishing or merging is a separate authorized action.
`main` receives a stable team milestone after all required blocks are reviewed.
