# Consolidated evidence and expected-failure corrections — 2026-10-30

Historical record of the lifecycle corrections and their 71-test campaign.
The [subsequent reconciliation correction](phase2_digital_log_reconciliation_20261030.md)
adds independent comparison of stored summaries with raw result records;
current evidence is selected in `phase2_log_reconciliation`.

The second review confirmed that the first three runner corrections worked,
then reproduced two additional evidence-flow issues. Neither issue required
changing the functional RTL, public protocol or delivered cells.

## Consolidated verification lifecycle

Previously, reusing an output directory changed `results.json` but left a
consolidated `verification_checks.json` with PASS and the former core hash.
An injected compilation failure likewise left the old consolidated PASS.

The runner now takes the output lock and atomically invalidates consolidated
verification as `NOT_CURRENT` before starting any accepted core run. Successful
and failed reruns both require new consolidated evidence. A competing writer
that cannot acquire the lock changes neither receipt.

Consolidation is now automated rather than written by an ad-hoc command:

```bash
./scripts/run_rtl.sh --output reports/digital/phase2_final_review
./scripts/run_rtl.sh --output reports/digital/phase2_final_review --verify-evidence
```

The second command requires a current schema-3 core PASS, verifies source and
snapshot identities and the manifest/transcript/waveform bindings, runs the
full Python tools and reconciliation suites, and audits stored Phase 1 evidence.
Each unittest method must appear exactly once as successful; skips, missing
tests, duplicate records, failing exit codes or incomplete summaries fail.
Core/source identities are rechecked before publishing consolidated PASS.
Consolidation failures publish FAIL while preserving the core simulation result.
The command holds the output lock throughout, including external test processes.

## Expected negative failures

Previously, any nonzero simulation with `FATAL:` counted as a detected mutant.
A probe replaced the six negative test programs with a watchdog-only bench;
none reached the scoreboard, yet all six were counted as detected.

Expected negatives now require exit code 1 and a unique matching diagnostic.
Mutants must fail the formatted DATA comparison in
`tb_sram_4x8.expect_bus`. Unsupported depths must fail with the exact requested
depth and `tb_sram_depth_guard.dut.invalid_depth` scope. Generic fatals,
watchdogs, wrong scopes, ambiguous messages, crashes and other exit codes
fail the campaign. Core `negative_results` retains the accepted cause, message
and scope for each of the six depth guards and six mutants.

## Regression evidence

The guard suite now has **32 tests**: 27 unit/entry-point cases and five
real-Icarus integration tests. The new real-tool tests reproduce both the
consolidated-receipt reuse problem and the watchdog-only negative campaign.
All destructive fault injection stays inside disposable project copies.

The full Python tools suite contains 29 earlier tests plus those 32 guard
tests; ten reconciliation tests run separately. The functional campaign keeps
the five memory runs, 96 controller checks and **154,303 comparisons**, without
changing RTL/TB logic or the data/clock protocol.

Selected evidence:

- [Functional summary](../reports/digital/phase2_final_review/summary.md).
- [Core receipt and accepted negative causes](../reports/digital/phase2_final_review/results.json).
- [Consolidated verification receipt](../reports/digital/phase2_final_review/verification_checks.json).
- [Tools tests](../reports/digital/phase2_final_review/verification_tests.txt).
- [Reconciliation tests](../reports/digital/phase2_final_review/reconciliation_tests.txt).
- [Stored-evidence preservation audit](../reports/digital/phase2_final_review/phase1_preservation.json).

Executed result: core PASS with **154,303 checks** and all 12 accepted
negative causes recorded. Automatic consolidated verification passed **71
Python tests with no skips** (61 tools tests, including all 32 guard tests,
plus ten reconciliation tests). The fresh stored-evidence audit passed for
**3,020 indexed frozen artifacts**. Core and consolidated receipt hashes,
source identities and retained test transcripts were rechecked after publication.

Earlier baseline and first-review evidence remain unchanged historical records.
No synthesis, GLS, new DRC/LVS, PEX or transistor simulation is performed here.
This closes verification-flow issues in the architecture/RTL and digital-test
fronts; the later synthesis/GLS front remains assigned separately.
