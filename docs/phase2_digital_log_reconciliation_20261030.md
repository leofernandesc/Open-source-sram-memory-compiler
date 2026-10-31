# Raw-log reconciliation correction — 2026-10-30

## Reproduced issue

The consolidation verified transcript hashes but trusted numeric counters in
`results.json`. Changing one case's count from 15,619 to 1,015,619 in a
disposable report copy produced consolidated PASS with 1,154,303 checks,
although the untouched raw logs contained 154,303 checks.

## Implemented correction

Before running verification suites, and again before publishing consolidated
PASS, the runner now:

1. Requires the fixed matrix of four model depths and the 4x8 structural view.
2. Reparses one `RESULT` record from each of their five logs, validates actual
   depth, seed, random operations and coverage, and compares every field with
   the stored case matrix. Missing, duplicate and reordered cases fail.
3. Reparses the controller's `CONTROL_RESULT`, requiring the complete 96-check
   result and an exact match with stored metadata.
4. Reconciles the six depth guards and six mutants against their uniquely
   classified fatal messages/scopes and recorded negative results.
5. Calculates `core_checks` from parsed log records, not summary counters.

Every required log must also have a matching recorded SHA-256 identity.
Canonical JSON comparison distinguishes integer, float and boolean values.
The consolidated `log_reconciliation` section records the primary log hashes,
five memory cases, 96 controller checks, 12 negative cases and derived total.

## Regression coverage and reproduction

The guard suite now contains 43 tests: 37 unit/entry-point tests and six
real-Icarus integration tests. New cases cover modified memory/controller
counts, non-count metadata, missing/duplicate/reordered cases, altered negative
diagnostics, absent hashes, changed raw logs, duplicated result records and
JSON type mismatches. A real simulation followed by a million-count edit must
publish consolidated FAIL before any verification suite is launched.

```bash
./scripts/run_rtl.sh --output reports/digital/phase2_log_reconciliation
./scripts/run_rtl.sh --output reports/digital/phase2_log_reconciliation --verify-evidence
```

The full Python tools suite has 72 tests (29 earlier tests plus 43 guard tests),
with ten reconciliation tests run separately. Functional expectations remain
154,303 checks, six rejected depths and six detected mutants. No RTL, HDL
testbench behavior, external protocol, cell, layout, frozen release or earlier
evidence was changed.

Current artifacts:

- [Functional summary](../reports/digital/phase2_log_reconciliation/summary.md).
- [Raw-log-derived consolidated receipt](../reports/digital/phase2_log_reconciliation/verification_checks.json).
- [Core receipt](../reports/digital/phase2_log_reconciliation/results.json).
- [Tools test transcript](../reports/digital/phase2_log_reconciliation/verification_tests.txt).
- [Reconciliation transcript](../reports/digital/phase2_log_reconciliation/reconciliation_tests.txt).
- [Read-only preservation audit](../reports/digital/phase2_log_reconciliation/phase1_preservation.json).

Executed result: **82 Python tests passed with no skips**, including all 43
guard tests and the real million-count corruption test. The functional run
passed **154,303 checks**; that total was independently recomputed from the
five memory records and the controller record. All 18 primary log bindings
were checked. The fresh stored-evidence audit passed for **3,020 indexed
frozen artifacts**. Current source/receipt identities were checked again after
automatic consolidation.

Synthesis, GLS, new DRC/LVS, PEX and electrical macro timing remain outside
this digital correction. Subsequent synthesis/GLS work remains a separate front.
