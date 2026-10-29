# Phase 1 technical handoff — six selected leaf cells

Date: 2026-10-29. Branch: `feature/peripherals`.
Status: **technical leaf package ready for team review**. Advisor approval,
integration into `develop` and a team milestone are not recorded as complete.

## Closure decision

Leonardo instructed us to proceed with closure after reviewing the model-bias
findings. The opposite-sign off-state gate-bias coverage gap is a **documented,
non-blocking limitation for this academic six-leaf handoff**. A response from
the PDK/model provider is not required to proceed. Independent accuracy in
those unmeasured conditions remains unknown; no warning or numerical result
has been changed into a model-validity or reliability PASS.

The [owner disposition](../release/phase1_handoff_20261029/decision.json)
records the scope and the measured local operating reference. It does not
approve a macro frequency, nominal characterization temperature or other
items still marked `(confirm with advisors)` in the specification.

## Fixed deliverables and checked evidence

Use the [current six-cell table](../release/phase1_keeper/README.md), selected
by [the active pointer](../release/phase1_current.json). Each entry fixes its
schematic, symbol, electrical netlist, flat mask, PEX and physical proof.

| Selected leaf | MOS | Stored DRC | Stored W/L and terminal LVS | Selected PEX binding |
|---|---:|---|---|---|
| bitcell_6t | 6 | 0 groups | Unique match | PASS |
| sense_amp | 7 | 0 groups | Unique match | PASS |
| precharge | 3 | 0 groups | Unique match | PASS |
| wl_driver | 4 | 0 groups | Unique match | PASS |
| write_driver | 10 | 0 groups | Unique match | PASS |
| Leonardo dynamic row_decoder with keepers | 33 | 0 groups | Unique match | PASS |

The [final handoff audit](../release/phase1_handoff_20261029/audit.json)
passes. It rechecks the 3,020 indexed artifacts, six current physical results,
all source/symbol/mask/PEX bindings, symbol pin order and the 30 selected
negative-control rejections. It reruns the original package's evidence audit
in a temporary copy, including upstream Git provenance and 129 archived
electrical rows. Neither frozen delivery is rewritten.

This is an audit of existing tool results. **No new SPICE simulation, DRC,
LVS or R-C extraction was performed for this closure step.** The original
per-cell reports identify the actual tools, dates and checked artifacts.

For the selected 33-MOS decoder and frozen WL drivers, the
[post-layout review](row_decoder_robustness_20261029.md) retains 105 passing
experimental runs and 3,045 passing checks, including all 16 ordered address
pairs in TT/SS/FF and 30 crossed PVT points. The five deliberate 32 fC boundary
failures are preserved. These counts are not full SRAM read/write tests.

The earlier G7-column, captured-address/control and PCLK-source campaigns
remain valid only for their original inputs. Their results are not transferred
to integration with the new keeper decoder. The other five leaf selections
and Danilo's original sources, reports and masks are unchanged.

## Local reference retained for the handoff

The evidence uses PCLK low/high = 3/2.5 ns, 2.1 ns external-address lead,
50 ps ramps and 102.873935496 fF per WL, with the existing distributed decoder
and WL PEX. The sampled screens are 0.1/0.9 VDD logic levels, a 250 ps selected
DEC/WL high dwell, 100 ps reset dwell and 250 ps internal-literal stability.
The separate 1.95 V magnitude screen is an experiment criterion, not a
foundry reliability rating. The tested startup/precharge conditions apply.

These settings identify a reproducible passing local experiment. They do not
define the external synchronous SRAM period, input setup/hold contract, sense
delay, power-up sequencing or indefinite clock-stop guarantee.

## Remaining workflow and Phase 2

The remaining Phase 1 workflow is review of the concrete package by the team
and advisors, followed by the authorized Git Flow integration into `develop`.
No PR, merge, rebase, tag or change to `main` is part of this closure step.

The next implementation stage is Phase 2:

1. Instantiate the selected leaves in the first 4×8 SRAM and rerun the relevant
   integration checks with the 33-MOS decoder; demonstrate data write/readback.
2. Implement and physically qualify capture and PCLK/PRECH control, then derive
   the macro timing and sense-enable budget from electrical measurements.
3. Develop the compiler and required GDSII, LEF, behavioral Verilog and Liberty
   macro views; qualify generated macro configurations against the specification.

A new physical edit may require another extraction; notify Leonardo before
starting it so the other machine can be used. Reading this handoff or checking
its integrity does not require an extraction.

## Reproduction and reversibility

Run the portable, read-only audit from the repository root:

```bash
python3 tools/verify_phase1_handoff.py
```

The original [29-MOS baseline](../release/phase1/manifest.json) and the selected
[33-MOS keeper revision](../release/phase1_keeper/manifest.json) both remain
content-addressed and unchanged. Reconsidering the architecture or sizing
requires a deliberate new selection with matching source, mask, PEX and
checksums; historical evidence must not be mixed across revisions.
