# Phase 2 experimental handoff

Implementation and technical audit are complete in the declared experimental
scope. Formal team/advisor acceptance remains pending. This is not a foundry
release or full SRAM characterization.

The new [handoff manifest](manifest.json) points to the exact views and
historical evidence. `physical/phase2/delivery.json` remains the immutable
pre-publication local delivery receipt: its LOCAL_ONLY/uncommitted statements
describe that earlier snapshot, not today's Git publication state.

## Review order and dependency

PR #7 (`integration/phase1-six-cells` → `develop`) is still open at handoff
preparation. The Phase 2 draft targets `integration/phase1-six-cells`, whose
tip is `a27dd1e5373d70c546bdfae44decefde64393794`. Integrate/review Phase 1 first,
then retarget the Phase 2 PR to develop and inspect its updated comparison.
No direct main/develop merge, rebase or force push is part of this handoff.

The digital commit `3b0675b` already exists on `feature/phase2-digital`; it is
included by ancestry, not duplicated. Its appearance in the stacked diff is
intentional because that commit follows the selected Phase 1 base.

## Artifacts and evidence

- [Reproduction guide](../../docs/phase2_reproduction_guide.md).
- [Full file inventory](inventory.json): A source, B deliverable, C selected
  evidence, E preserved history. D regenerable build/cache groups are described
  separately; they are kept locally and omitted from Git.
- [Phase 2 acceptance](../../docs/phase2_review_20261104_acceptance.md).
- [Timing/startup supplement](../../docs/phase2_final_polish.md).
- [22-slide presentation](../../presentations/phase2/README.md).
- [Optional raw bundle index](raw_bundle.json): seven complete transients,
  lossless roundtrip verified. The ~81-MiB bundle stays outside Git and is not
  hosted automatically. Obtain it from the holder or regenerate simulations.

The inventory excludes itself and `validation.json`: validation seals the
inventory in one direction, avoiding recursive hashes. The versioned gate
also compares worktree content against Git's staged blobs; a path being
tracked is insufficient if its current bytes were not staged.

## Publication selection

Mandatory views, metadata, logs and sealed evidence are retained, including
the 21-MiB Magic flat view named in the original manifest. Earlier checkpoints
are explicit histories rather than current acceptance. The large ignored
OpenROAD ODBs, transient raw caches, local Python packages, PDF-render previews
and optional raw bundle are regenerable/transfer data, not Git payload.
The baseline raw gzip is a deliberate selected evidence exception. Three
checker logs have a precise `.gitignore` exception because the supplemental
seal requires them. No frozen Phase 1 file is changed.

Git publication does not change the experimental boundaries: physical 4×8,
TT/1.8 V/27 °C, 20-ns experimental clock, extracted connectivity/junctions,
no detailed wire RC, Fmax, all-corner/statistical qualification or fabrication
reliability. Historical raw-source snapshots preserve their original paths
and links as captured source text; they are not independently navigable guides.
