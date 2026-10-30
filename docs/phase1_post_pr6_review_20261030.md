# Phase 1 review after PR #6 — 2026-10-30

PR #6 merged into main as `edeeb0b608c8c21c05517de49dd49d8cb34d4476`.
Its tree is identical to develop `eb9217ee80c585cf952e14f6a13f6fc7230ba639`,
the first parent of the existing integration commit `083a080`. Consequently,
that merge adds no new electrical source, model or layout changes to reconcile.
PR #7 remains an integration-to-develop PR and is updated in place.

## Findings and changes

| Finding | Resolution |
|---|---|
| An automatic GitFlow merge retained both the six-leaf decision and an older statement deferring decoder qualification to Phase 2 | Remove the obsolete reassignment from the active ownership table and workflow. The selected 33-MOS dynamic decoder is a Phase 1 leaf; complete macro access and physical control remain Phase 2. |
| Current README and cell index contained long historical sections that still described another decoder as current | Replace these indexes with the actual selected six-cell delivery, formal interfaces, reproduction commands and scoped next work. Historical scientific reports remain linked and intact. |
| Matching a campaign hash did not prove that a cached row belonged to the requested corner/state | Require successful simulator status and matching corner, VDD, temperature and stored state before reuse, for both read and write. |

Preservation follows evidence and the current specification, not authorship:

- Retain the canonical 6T cell, seven-MOS sense topology, selected strengthened
  peripheral variants and their measured/physical evidence. Their chosen files
  are fixed by the current release manifest and remain unchanged.
- Retain the upstream `.t0` initialization, per-PVT/per-side Ceff accounting,
  PEX overrides, source hashes and recovery measurements in the G7 runners.
  Regression checks confirm that circuit generation, numerical measurement
  functions and electrical acceptance criteria were not downgraded.
- Preserve Danilo's bitcell report, bitcell specification and WL-load report
  as dated scientific records. The root README no longer republishes their
  obsolete planning statements as the current project state.
- Keep the separate PCH_N/EVAL decoder candidate as historical source material;
  it is not selected, qualified or substituted for the official PCLK decoder.
- Keep failed exploratory cases and missing historical diagnostics in their
  original scope. A prior partial/structural LVS result or an ideal-WL G7 run
  does not acquire stronger qualification by being merged.

## Verification

The cache defect was reproduced before the correction: a PASS row from another
corner and stored state could be accepted solely because its campaign hash
matched. The gate now rejects mismatched or missing identity, nonzero simulator
return code, unknown contract and failed result. CSV numeric formatting remains
compatible with the correct case.

The [real cache review](../sims/integration/results/post_pr6_cache_20261030/manifest.json)
exercises a TT/1.8 V/27 C/state-0 read and write with the selected G7 PEX and
the previously recorded explicit load/timing options. Each runner performs:

1. One fresh passing simulation.
2. One successful reuse of the correct checkpoint, with zero pending cases.
3. One deliberately injected wrong-corner checkpoint, rejected and replaced by
   a fresh simulation of the requested case.

All six command executions pass: four actual SPICE simulations, two correct
cache hits and two rejected wrong-case controls. Reused and resimulated rows
match the original correct row exactly. These are regression checks, not a
new all-corner characterization campaign.

The current checks pass:

- 29 tool tests, 90 decoder tests and 10 reconciliation tests: **129 tests**.
- Current six-cell handoff audit: **3,020 frozen artifacts** unchanged.
- Original reconciliation evidence integrity: **1,134 artifacts** unchanged.
- Independent replay of the earlier reconciliation review: **PASS**. Its
  48 decoder/WL cases, 1,392 checks, six native physical results, 30 physical
  negative controls, 60 read cases and 60 write cases retain their original scope.
- **337 installed model dependencies** match the hashes recorded by those
  electrical campaigns.
- Links in the revised indexes resolve; source whitespace checks pass.

The [review receipt](../sims/integration/results/post_pr6_review_20261030/summary.json)
records hashes, commands and outputs. No selected schematic, dimension, mask,
PEX or model changed. No new DRC/LVS, distributed R-C extraction or full
48/60-case rerun was necessary solely because PR #6 merged. Earlier native
physical runs and electrical campaigns were rechecked as stored evidence.

## Remaining scope and workflow

Tight G7 margins and the accepted model-data limitation are unchanged. The
fresh read experiment and historical read CSV use different documented scopes;
missing historical recovery durations remain unknown. No macro frequency,
statistical yield, foundry reliability or complete decoder-driven SRAM access
is approved by this review.

Review and merge PR #7 into develop. Since PR #6 is already closed, publishing
the reconciled delivery to main requires a new develop-to-main PR, followed by
the reviewed milestone tag. Neither main nor develop is modified by this work.

Read-only evidence and regression commands:

```bash
python3 tools/verify_phase1_handoff.py
python3 sims/integration/check_evidence.py
python3 -m unittest discover -s tools/tests -v
python3 -m unittest discover -s sims/integration -p 'test*.py' -v
./tools/sram-eda python3 -m unittest discover \
  -s sims/row_decoder -p 'test*.py' -v
```

Reproduce the real cache controls in a new directory:

```bash
./tools/sram-eda python3 sims/integration/run_cache_case_review.py \
  --output-dir sims/integration/results/cache_case_repro
```
