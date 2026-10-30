# Phase 1 repository integration — 2026-10-30

This is the original reconciliation record for commit `083a080`. The
[post-PR6 review](phase1_post_pr6_review_20261030.md) records the subsequent
active-documentation cleanup and checkpoint-identity fix, with 129 current tests.
Statements below about retaining the previous README body describe the original
reconciliation, not the later current-status indexes.

Branch: `integration/phase1-six-cells`.
Base: `develop` at `eb9217ee80c585cf952e14f6a13f6fc7230ba639`.
Feature delivery: `feature/peripherals` at
`e73757f2498729075531bc5725d4c469fa4b01cf`.

This branch reconciles the six-leaf delivery for review through a PR to
`develop`. It does not deliver a complete synchronous 4×8 SRAM macro.
The source feature branch and both frozen deliveries remain unchanged.

## Conflict resolutions

All 14 conflicting paths were reviewed. The resolution preserves the newer
upstream work rather than replacing it with older imported copies:

| Area | Resolution and reason |
|---|---|
| Bitcell report, bitcell specification and WL-load report | Preserve Danilo's `develop` files byte for byte. Their newer sizing, latch-output `.t0` initialization, Ceff and physical results are supported by the selected artifacts and CSV provenance. |
| Original cell paths | Preserve the upstream root-level files and their original references. Structured copies remain available for the peripheral workflow. These development captures are not a substitute for the selected release manifest. |
| Hierarchical bitcell testbench | Preserve the newer sizing and stimulus when reconciling the moved testbench. Keep the original testbench path available. |
| Integrated read/write and capacitance runners | Retain the upstream PEX overrides, geometry/source hashes, recovery measurements and per-side capacitance accounting. Add safe reuse of results without removing the measurements. |
| Peripheral smoke | Combine upstream PEX support with the peripheral formal-pin mapping and configurable WL pulse/sampling options. Preserve `--blocks` compatibility. |
| Public specification | Retain the authorized six-leaf scope and Leonardo's 33-MOS PCLK decoder. Preserve the useful captured-address, startup/precharge and read-sampling sequencing requirements, expressed for this implementation. |
| README and cell index | Keep the newer upstream body and add the current selected-delivery reference. |

The original report and candidate `cells/row_decoder_2to4.spice` are retained
as source material. Their proposal to defer a different decoder to Phase 2
does not replace the explicit current project decision. The authority is
[`technical_specification.md`](../specs/technical_specification.md), and the
selected artifacts come from [`phase1_current.json`](../release/phase1_current.json).

## Evidence reuse and requalification

The five non-decoder leaf selections are identical in both frozen manifests.
The keeper decoder keeps its own matched source, symbol, mask and PEX. No mask
or transistor size was changed during reconciliation. A new distributed R-C
extraction would repeat the existing geometry, so none was required.

The new native physical checks run on copies, leaving the delivered bytes
intact. They repeat full Magic DRC, primitive-MOS dimension/terminal LVS,
existing-PEX connectivity binding and five rejected controls per leaf.
Thirty control rejections apply to the six selected cells. This remains the
documented project physical contract, not foundry fabrication signoff.

Electrical checks are deliberately separated:

| Campaign | What it establishes | What does not transfer |
|---|---|---|
| Decoder/WL: 48 ordered address transitions in TT/SS/FF | Reproduction of the selected 33-MOS decoder and four WL drivers using identical decks, PEX and model hashes | Full SRAM data access or physically implemented capture/PCLK control |
| G7 write: 60 cases | Requalification of the restored representative-column write runner, selected bitcell/precharge/WL/write PEX and per-PVT/per-side residual Ceff | A decoder-driven or complete-macro write operation |
| G7 read: 60 cases | A fresh, explicitly recorded representative-column experiment with selected bitcell/precharge/WL/sense PEX | An exact timing reproduction of the historical CSV or a decoder-driven read |
| Source-path smoke: 12 cases | Root-level Xschem source compatibility, formal pin order and both selected smoke blocks | Electrical qualification of the stronger frozen physical variants |
| Boundary CLI: two actual 32 fC runs | Mandatory failure returns 2; explicit `--allow-boundary` records the same physical rejection and returns 0 | Noise immunity at 32 fC |

The G7 benches instantiate one represented bitcell and peripheral PEX, with
the remaining column/row capacitance represented by the documented residuals.
They use ideal WL input timing and do not contain the new decoder. Their
measurements must not be presented as integration of all six leaves.

Read stimulus: WL input at 2.25 ns with 3 ns high time, sense at 4.6 ns;
CBL target 597.056240839 fF, WL extra 93.351918068 fF. Historical CSVs do not
retain every pulse option. Exploratory 1.5/2/3 ns pilot results are preserved;
differences between them are stimulus differences, not a keeper improvement.
The fresh 3 ns experiment has a complete recorded command. Write uses the
recorded historical WE=2.2 ns, WL input=3.4 ns/1 ns and the same load contract.
The runners use one ngspice worker thread; all electrical screens are retained.

The historical read CSV omits the recovery-delay diagnostic in 30 cases;
those entries remain unknown and are excluded from that numerical comparison,
not converted to zero. The fresh 3 ns read campaign records all 60 recovery
durations. Its final bitline-level checks remain separate from that diagnostic.

Measured comparisons and independently checked pass counts are in
[`review_20261030.json`](../sims/integration/results/review_20261030.json).
The 2 ps write and 1 ps decoder comparison tolerances are numerical
reproduction checks, not newly approved SRAM timing requirements.

| Measured result | Outcome |
|---|---|
| Native physical requalification | Six zero-DRC masks, six dimension/terminal LVS matches, 30 rejected controls; original PEX bindings pass |
| Decoder/WL reproduction | 48/48 cases, 1,392/1,392 checks; identical decks/model hashes and exactly 0 ps difference in the compared WL90 delays |
| Restored G7 write | 60/60; full-flip time, WL30 margin and recovery metrics reproduce with exactly zero numerical difference |
| Explicit G7 read | 60/60; minimum differential 0.341996 V, maximum resolution 0.245100 ns, maximum low-node excursion 0.1964912 V |
| Source-path smoke | 12/12 after restoring CLI compatibility |
| Regression tests | 29 tools + 90 decoder + 8 reconciliation = 127 passing tests |

Some inherited G7 screens have little spare margin. The fresh read's worst
low-node excursion is only 3.5088 mV below its 0.2 V screen, and resolution
has 4.9 ps below the 250 ps screen. The write recovery maximum 3.978840 ns
has 21.16 ps below its 4 ns screen; its minimum WL30 margin is 79.696 ps.
These are measured margins of the representative-column experiments, not
guaranteed macro margins or a regression caused by merging the branches.
Recheck them with the actual decoder/control-driven data path in Phase 2.

## Automation fixes

- `run_keeper_pex.py` returns nonzero for unexpected measured failures.
  Expected boundary failures require `--allow-boundary`; simulator errors,
  missing data and nonfinite magnitudes cannot be approved by that flag.
- The campaign coordinator permits a boundary only in the explicitly named
  charge-boundary job. Other jobs must pass their screens.
- G7 `--resume` requires a matching contract covering electrical parameters,
  rendered leaves, recursive model includes, source CSVs, runner/helper code
  and ngspice. Older unsigned PASS rows are rerun.
- The smoke runner retains configurable WL pulses and `--blocks`, and builds
  instances from the declared formal pin order.
- Git attributes preserve CSV line endings and native evidence padding.
  Frozen data was not reformatted to suppress whitespace diagnostics.

The first reconciliation attempt stopped after successful physical checks
because tool-hash metadata used a string instead of a `Path`. The corrected
second attempt passed the physical and G7 campaigns, then exposed the missing
`--blocks` compatibility in the merged smoke CLI. Its failure record remains
unchanged. The separate smoke retry passes after restoring that interface;
the independent review accepts only this specific recorded CLI retry, never
an electrical failure. Neither failure is relabelled as a circuit PASS.

## Reproduction

Use the configured EDA container and new output directories:

```bash
./tools/sram-eda python3 sims/integration/run_reconciliation.py \
  --output-dir sims/integration/results/reconciliation_repro

./tools/sram-eda python3 sims/row_decoder/run_keeper_pex.py \
  --output-dir sims/integration/results/decoder_repro

python3 tools/verify_phase1_handoff.py
python3 sims/integration/check_evidence.py
python3 -m unittest discover -s tools/tests -v
python3 -m unittest discover -s sims/integration -p 'test*.py' -v
./tools/sram-eda python3 -m unittest discover \
  -s sims/row_decoder -p 'test*.py' -v
```

The boundary CLI commands and expected exit codes are recorded in
[`cli_results.json`](../sims/integration/results/boundary_cli_20261030/cli_results.json).
The active evidence review uses the completed native/G7 campaign and its
separately recorded smoke retry; the command manifest identifies both.
The evidence index covers the recorded attempts, including their retained
failures; its integrity PASS does not approve an individual failed attempt.

## Remaining acceptance boundary

The off-state model-data coverage limitation remains documented and
non-blocking for this academic leaf handoff, as authorized. No model accuracy,
statistical yield, macro frequency or fabrication reliability claim was added.
The open advisor decisions remain open. Complete decoder-driven data access,
physical capture/PCLK/PRECH timing and the compiler/macro views are Phase 2.

Team review and merging the PR into `develop` are separate acceptance actions.
No merge into `develop`, change to `main` or milestone tag is performed here.
