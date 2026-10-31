# Digital verification review corrections — 2026-10-30

Historical record of the first three corrections. The
[subsequent review](phase2_digital_evidence_lifecycle_20261030.md) supersedes
this runner revision and adds consolidated-receipt invalidation and strict
negative-failure classification. Its evidence is in `phase2_final_review`.

## Findings and corrections

The deep review reproduced three failures in the verification flow without
changing delivered RTL. This revision corrects the runner, adds regression
tests and retains new evidence separately from the original baseline.

| Finding | Correction | Required negative/positive control |
|---|---|---|
| Source hashes computed after simulation could describe untested edits | Capture and hash a read-only source snapshot before compilation; compile/audit/mutate only that snapshot; verify live and captured inputs before PASS | Edit live RTL after the first compile: positive cases still use the safe snapshot, but final receipt must be FAIL |
| A bench fixed at four words could PASS requests for larger memories | Compare returned depth, seed and random count with each request; validate coverage dimensions/types/totals | A fixed-four-word bench must fail on the first eight-word request |
| Simultaneous runs overwrote shared executables and aborted VVP | Give each run an exclusive build directory; protect each output with an OS file lock | Two real regressions with seeds 101 and 202 must both PASS with separate paths and waveform seeds |

`source_manifest.json` is written before any compile. The final receipt stores
that manifest's hash and the captured input hashes, not late hashes of mutable
working-tree files. Source additions, modifications, missing files or changes
to the snapshot itself prevent PASS. Full waveforms and captured files remain
in the unique ignored build directory for local inspection.

Each output has a persistent, Git-ignored `.run.lock`; a competing writer
cannot change the owner's results. Caught failures publish FAIL, including
tool preflight failure, and hard interruptions may leave RUNNING. Neither is
a passing receipt. `results.json` is the authoritative completion marker.

## Tests and reproduction

```bash
./scripts/run_rtl.sh --output reports/digital/phase2_review_fixes
./tools/sram-eda python3 -m unittest discover -s tools/tests -v
python3 -m unittest discover -s sims/integration -p 'test*.py' -v
python3 tools/verify_phase1_handoff.py
```

The digital runner guard suite has **21 tests**: 18 unit/entry-point checks
and three integration tests using real Icarus. All fault injection is confined
to disposable project copies. Integration tests check the expected failure
reason, final receipt status, original/captured byte identities and waveform
seeds; a generic subprocess failure is not accepted as proof of correction.

The real-tool tests must run through `tools/sram-eda`; they are explicitly
skipped when Icarus/VVP are unavailable on the invoking environment. The full
tools suite includes 29 pre-existing tests plus these 21 tests. The ten
integration-reconciliation tests remain separate.

The [current simulation summary](../reports/digital/phase2_review_fixes/summary.md)
records the five memory runs and the 96-check controller test. The expected
functional counts remain 154,303 checks, with 2,048 random operations per
memory run, six unsupported-depth rejections and six detected faulty models.
[Verification test log](../reports/digital/phase2_review_fixes/verification_tests.txt),
[reconciliation test log](../reports/digital/phase2_review_fixes/reconciliation_tests.txt)
and [preservation receipt](../reports/digital/phase2_review_fixes/phase1_preservation.json)
are retained alongside the numerical and waveform evidence.

Executed results: **50 tools tests and ten reconciliation tests passed, with
no skips**, including all three real-Icarus hardening tests. The functional
regression again passed **154,303 checks**. The preservation audit passed for
all **3,020 indexed frozen artifacts**; delivered RTL/TB and the original
baseline logs/waveforms remain byte-identical to their recorded hashes.
The [verification receipt](../reports/digital/phase2_review_fixes/verification_checks.json)
binds the test logs, core result and preservation receipt by SHA-256.

No RTL, testbench protocol, supply/reset interface, physical cell, layout,
frozen release or original baseline was modified by these corrections. No
synthesis, GLS, PEX or physical timing qualification is claimed. These fixes
close verification-flow findings in the architecture/RTL and digital-testing
fronts; the subsequent synthesis/GLS front remains assigned separately.
