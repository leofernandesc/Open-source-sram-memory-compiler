# Phase 1 six-cell delivery decision and physical closure

Decision date: 2026-10-28. Owner approval: Leonardo explicitly requested the
six-cell delivery, retention of his decoder, a fixed artifact table, and
closure of DRC/LVS evidence.

## Binding scope decision

Phase 1 delivers the bitcell 6T, sense amplifier, three-PMOS precharge/equalizer,
wordline driver, write driver and Leonardo's existing 29-MOS dynamic decoder.
The latter remains a Phase 1 deliverable on `feature/peripherals`. The separate
`cells/row_decoder_2to4.spice` proposal and its PCH_N/EVAL interface are not the
selected decoder. No replacement, keeper insertion or decoder resizing was
performed for this delivery.

The statements merged into `develop` at `eb9217e` proposing another decoder
and its reassignment to Phase 2 are superseded by this explicit user decision.
`specs/technical_specification.md` and `GITFLOW.md` on this branch now express
that decision. Publication/integration into `develop` still follows a reviewed
PR; this work does not merge branches or edit another owner's source files.

Complete SRAM macros, compiler/views, and the physical qualification of the
experimental capture/PCLK/PRECH controller are Phase 2 deliverables.

## Fixed artifact selection

Use the [six-cell artifact table](../release/phase1/README.md) and
[machine-readable manifest](../release/phase1/manifest.json). Each row fixes
SCH, SYM, electrical SPICE, final flat MAG, existing R-C PEX and physical report.
The manifest records exact source revisions, upstream paths, original hashes,
width bindings and released-file hashes.

The selected five upstream variants are those used in the corrected G7
qualification: bitcell 0.42/1.26/0.60, sense scale1p5 with 2.0 µm sampling,
precharge W2.52, WL stages 1.68/5.04, and write output W5.04. New schematic
snapshots expose these physical widths rather than the earlier draft sizes.
The original Danilo/André material remains unchanged. Leonardo's decoder
schematic, symbol, flat mask and PEX are frozen without design changes.

## Fresh physical evidence

| Delivered cell | MOS count | Magic DRC(full) | Netgen LVS: type, terminals, W/L | Existing PEX binding |
|---|---:|---|---|---|
| bitcell_6t | 6 | 0 errors | Unique match | PASS |
| sense_amp | 7 | 0 errors | Unique match | PASS |
| precharge | 3 | 0 errors | Unique match | PASS |
| wl_driver | 4 | 0 errors | Unique match | PASS |
| write_driver | 10 | 0 errors | Unique match | PASS |
| row_decoder | 29 | 0 errors | Unique match | PASS |

See the [summary](../release/phase1/verification/summary.json) and per-cell
reports linked from the artifact table. Checks run with Magic 8.3.589, Netgen
1.5.293 and SKY130A technology 1.0.493 using the installed official
`sky130A_setup.tcl`. Exact executable, setup, input and extracted-file hashes
are retained. Source symbols/netlists are generated and checked with Xschem.

All 30 intentionally faulty comparisons were rejected: 20% width change,
20% length change, wrong gate, wrong bulk and wrong MOS type for each cell.
W/L comparison uses the official 1% tolerance; the sense NMOS 0.975-to-0.98 µm
mask quantization is documented. No black-box MOS or unchecked W/L comparison
is accepted as a passing report.

Existing PEX files were copied unchanged and checked for device/connectivity
binding by collapsing parasitic R networks for LVS only. This does not rerun
or qualify the R/C extraction algorithm or electrical performance.

The [supporting G7 column](../release/phase1/support/g7_column/result.json)
also passed fresh DRC and parameter-aware LVS for 212 MOS. Its reference was
rebuilt from the frozen schematic leaves and original structural top wiring,
instead of extracted leaf references. Both input netlists and new logs are
retained; the older missing/structural-only manual logs are superseded for this
mask by the new check. This supporting column remains distinct from a complete
SRAM macro and is not a seventh leaf. Console warnings concerning the Tcl
namespaces `format`/`global` are retained; no MOS placeholders or property
errors occur in the accepted comparisons.

## Closed items and electrical work still open

The six-cell scope, official decoder selection, artifact inventory and physical
DRC/LVS evidence are closed for these hashes. The
[release audit](../release/phase1/verification/release_audit.json) also confirms
129 archived electrical rows and their selected leaf PEX hashes.

Full electrical Phase 1 acceptance still requires a documented local timing
contract and resolution/acceptance of the decoder's model-domain findings.
The [frozen decoder/WL local-interface campaign](row_decoder_canonical_pair_requalification_20261028.md)
uses the selected 1.68/5.04 µm WL stages. Earlier captured-path results used
the smaller 0.42/0.84 µm driver and do not transfer automatically to this pair.
The 0.9·VDD screen, 2.10 ns phase, 3.8 ns measurement allowance and sampled
250 ps guard remain experimental. No new nominal temperature, clock frequency,
rail-excursion allowance or reliability limit is approved by this physical
closure. The older broad integration task list is superseded as a Phase 1
scope definition, while its recorded experiments remain valid for their inputs.

The scope and physical gates can now be reviewed as a concrete package. The
remaining electrical items must be resolved or explicitly accepted with their
bounded operating conditions before calling all of Phase 1 electrically closed.
