# Frozen Phase 1 six-cell delivery

Selection date: 2026-10-28. This directory is the canonical delivery snapshot;
development files elsewhere remain available for history and future work.
The [manifest](manifest.json) records immutable source revisions, sizing
overrides, SHA256 hashes and the exact file selected for each view.

| Cell / owner | Schematic | Symbol | Electrical leaf | Final flat mask | Existing R-C PEX | Physical evidence |
|---|---|---|---|---|---|---|
| Bitcell 6T / Danilo | [SCH](cells/bitcell_6t/bitcell_6t.sch) | [SYM](cells/bitcell_6t/bitcell_6t.sym) | [SPICE](cells/bitcell_6t/bitcell_6t.spice) | [MAG](cells/bitcell_6t/bitcell_6t.mag) | [PEX](cells/bitcell_6t/bitcell_6t_pex.spice) | [Result](verification/bitcell_6t/result.json) |
| Sense amplifier / André | [SCH](cells/sense_amp/sense_amp.sch) | [SYM](cells/sense_amp/sense_amp.sym) | [SPICE](cells/sense_amp/sense_amp.spice) | [MAG](cells/sense_amp/sense_amp.mag) | [PEX](cells/sense_amp/sense_amp_pex.spice) | [Result](verification/sense_amp/result.json) |
| Precharge / André | [SCH](cells/precharge/precharge.sch) | [SYM](cells/precharge/precharge.sym) | [SPICE](cells/precharge/precharge.spice) | [MAG](cells/precharge/precharge.mag) | [PEX](cells/precharge/precharge_pex.spice) | [Result](verification/precharge/result.json) |
| WL driver / Leonardo | [SCH](cells/wl_driver/wl_driver.sch) | [SYM](cells/wl_driver/wl_driver.sym) | [SPICE](cells/wl_driver/wl_driver.spice) | [MAG](cells/wl_driver/wl_driver.mag) | [PEX](cells/wl_driver/wl_driver_pex.spice) | [Result](verification/wl_driver/result.json) |
| Write driver / Leonardo | [SCH](cells/write_driver/write_driver.sch) | [SYM](cells/write_driver/write_driver.sym) | [SPICE](cells/write_driver/write_driver.spice) | [MAG](cells/write_driver/write_driver.mag) | [PEX](cells/write_driver/write_driver_pex.spice) | [Result](verification/write_driver/result.json) |
| Dynamic decoder / Leonardo | [SCH](cells/row_decoder/row_decoder.sch) | [SYM](cells/row_decoder/row_decoder.sym) | [SPICE](cells/row_decoder/row_decoder.spice) | [MAG](cells/row_decoder/row_decoder.mag) | [PEX](cells/row_decoder/row_decoder_pex.spice) | [Result](verification/row_decoder/result.json) |

## Selected physical sizing

All devices use `L=0.15 µm` and unit finger/multiplicity.

| Cell | Selected widths (µm) | MOS count |
|---|---|---:|
| Bitcell | Pull-up 0.42; pull-down 1.26; access 0.60 | 6 |
| Sense amplifier | Latch PMOS 1.89; latch/tail NMOS 0.975; sampling PMOS 2.0 | 7 |
| Precharge | All three PMOS 2.52 | 3 |
| WL driver | Both devices in stage 1: 1.68; both in stage 2: 5.04 | 4 |
| Write driver | WE inverter 0.84; eight output-stack devices 5.04 | 10 |
| Dynamic decoder | Exact original per-instance sizes in SCH/SPICE; shared footer M8 1.5 | 29 |

The sense NMOS mask quantizes 0.975 µm to an extracted 0.98 µm. This difference
passes the official SKY130A Netgen geometry tolerance (1%); no values were
rounded by the LVS normalizer. The decoder SCH and SYM are exact copies of
Leonardo's existing files, including the nine-pin interface.

## SPICE pin order

| Cell | Ordered pins |
|---|---|
| bitcell_6t | `VDD BL BLB VSS WL` |
| sense_amp | `VDD VSS BL BLB SCLK SA_OUT SA_OUTB` |
| precharge | `VDD BL BLB PRECH VSS` |
| wl_driver | `VDD VSS WL_IN WL` |
| write_driver | `DATA DATA_B WE BL BLB VDD VSS` |
| row_decoder | `VDD PCLK A0 A1 DEC0 DEC1 DEC3 DEC2 VSS` |

`WE` is active high; `PRECH` is active low. `DATA_B` is supplied as the
complement of `DATA`. PEX subcircuit names and ordered ports retain their
original physical-view interfaces; when instantiating them, read their
`.subckt` declaration rather than assuming the schematic's pin ordering.

The other five schematic snapshots originate from the pinned upstream
revision; only transistor widths are bound to the selected physical variants.
Their original topology, wiring and upstream development sources are preserved.
Inherited standalone smoke stimuli are historical examples; use the archived
qualification benches/results for electrical claims.

## Physical acceptance evidence

The [summary](verification/summary.json) records six DRC(full) passes and six
unique primitive-MOS LVS matches. Each cell directory contains `magic.txt`,
`xschem.txt`, `layout_extracted.spice`, normalized comparison netlists,
`lvs_report.txt`, five intentionally faulty inputs and their rejection reports.
There are 30 negative controls: W, L, gate, body and MOS type, one of each per
cell. The retained PEX also passes a separate connectivity/W/L binding check
after collapsing its parasitic resistor networks; its R-C bytes are unchanged.

The official masks are the **final flat views**, copied byte for byte from
the recorded source revision. Earlier hierarchical PCell construction views
are not substituted for these masks: some historical flows restored gate
length on the final flat geometry. Fresh DRC and extraction operate on scratch
copies of the delivered masks. No R-C extraction was repeated.

The LVS adapter maps the two supported four-terminal SKY130 `X` MOS wrappers to
primitive `M` devices, preserving D/G/S/B, W/L, type and unit multiplicity. Both
files express dimensions in µm; explicit `u` suffixes make the comparison
units unambiguous. PCell-generation options, AD/AS/PD/PS and compact-model
parameters are outside this LVS contract. The official PDK setup governs
permutation and geometry tolerance. The passing reports have no MOS
placeholders/black boxes. These reports replace structural-only comparisons
for the six selected leaves.

The [supporting G7 column](support/g7_column/result.json) was also rerun:
DRC zero and parameter-aware LVS unique match for 212 MOS. Its reference
expands the frozen electrical schematic leaves using the pinned original
structural column wiring. Fresh logs and both comparison netlists are
retained in that directory, replacing the dependency on missing historical
manual logs. It remains supporting column evidence, not a seventh delivery
cell or a fully decoded SRAM macro. The retained Netgen consoles emit Tcl
namespace warnings for `format` and `global`; the device comparisons report
no MOS placeholders or property errors.

## Electrical evidence and remaining limits

The [electrical archive](electrical/) retains the upstream 60-case read and
60-case write G7 matrices, plus eight read and one write refinement cases.
All 129 rows pass their original checks. The
[release audit](verification/release_audit.json) verifies the leaf PEX hashes
used by those runs against this selection. This is an audit of archived
results, not a new simulation. G7 used ideal `WL_IN` and does not qualify
decoder-driven macro access.

Decoder electrical evidence remains in
[the captured-interface report](../../docs/row_decoder_captured_phase_interface_20261009.md).
The decoder's local phase/timing contract and model-domain acceptance remain
open. Its experimental threshold/window settings are not approved frequency
or reliability limits. Full macro access, physical control/phase generation
and final generated views are Phase 2 work.

## Reproduce

From the repository root, regenerate the frozen snapshots and physical checks:

```bash
python3 tools/prepare_phase1_release.py
./tools/sram-eda python3 tools/verify_phase1_physical.py
./tools/sram-eda python3 tools/verify_phase1_g7_support.py
python3 tools/audit_phase1_release.py
```

The first command restores pinned inputs and must be followed by verification;
it does not confer PASS on a changed selection. To open the canonical decoder:

```bash
./tools/sram-eda xschem release/phase1/cells/row_decoder/row_decoder.sch
```

`checksums.json` covers the released inputs, generated files and retained
reports. New edits require regenerating the affected evidence and audit.

## Audit failure behavior

The audit uses explicit runtime checks that remain active with Python `-O`
and `-OO`. Invalid or missing evidence produces exit code 1 and a `FAIL`
report in `verification/release_audit.json`, replacing any stale `PASS`.
Checksums are updated only after all acceptance checks succeed.

Regression tests use temporary release copies; the valid package is approved
and nine invalid-evidence cases are rejected in all three interpreter modes:

```bash
python3 -m unittest discover -s tools/tests -p 'test_audit_phase1_release.py' -v
```
