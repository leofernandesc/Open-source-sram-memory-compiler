# Git workflow

Phase 1 uses `main`, `develop` and `feature/*`, with temporary `integration/*`
branches when feature deliveries need reconciliation.

| Branch | Purpose | Integration |
|---|---|---|
| `main` | Reviewed project milestones | Pull request from `develop` |
| `develop` | Integration of completed work | Pull requests from feature branches |
| `feature/*` | Work owned by one Phase 1 block owner | Starts from and returns to `develop` |
| `integration/*` | Temporary reconciliation of reviewed feature deliveries | Starts from `develop`, merges the relevant features, and returns through a PR to `develop` |

Do not commit directly to `main` or `develop`. Keep commits focused, review the
diff, and use a pull request for integration. Merge the latest `develop` into a
feature branch before its pull request; do not rewrite a shared branch's history.
Keep generated temporary files out of commits unless they are deliberately
selected as reproducible verification evidence.

For the six-cell closure, `integration/phase1-six-cells` reconciles
`feature/peripherals` with the existing `develop` work. Conflict resolutions
and necessary requalification are recorded on that integration branch; the
feature branch and frozen evidence are preserved. Its PR targets `develop`.
This temporary branch integrates repository deliveries, not a complete SRAM
macro. Update it from the latest `develop` again if the base advances before
merging the PR.

## Phase 1 branches and owners

| Branch | Owner | Blocks |
|---|---|---|
| `feature/bitcell` | Danilo (Person 1) | 6T bitcell through schematic, simulation, layout, DRC, and LVS |
| `feature/sense-precharge` | André (Person 2) | Sense amplifier and precharge/equalization through schematic, simulation, layout, DRC, and LVS |
| `feature/peripherals` | Leonardo (Person 3) | Dynamic 2-to-4 row decoder, wordline driver and write driver through schematic, simulation, layout, DRC and LVS |

The dynamic 2-to-4 decoder implementation maintained on `feature/peripherals`
is Leonardo's Person 3 Phase 1 deliverable through schematic, simulation,
sizing, layout, DRC, and LVS. A candidate or phase proposal on another branch
does not replace or reassign this implementation.

The six-cell Phase 1 scope was explicitly reconfirmed by Leonardo on
2026-10-28. On 2026-10-29 he authorized robustness analysis and circuit changes.
His dynamic decoder remains official, now with four feedback PMOS keepers
(33 MOS). `release/phase1_current.json` selects the current six-cell manifest
in `release/phase1_keeper/`; its table is `release/phase1_keeper/README.md`.
The original `release/phase1/` snapshot and the other five selections remain
unchanged. Complete macro,
compiler and physical control/PCLK-generator qualification are Phase 2 work.
Statements in another branch that defer this decoder are superseded by this
explicit scope decision when the development lines are reconciled.

Each owner is responsible for carrying the assigned leaf blocks through the
complete Phase 1 flow. The dynamic decoder is included in that delivery;
complete decoder-driven macro access and physical capture/PCLK/PRECH control
remain Phase 2 integration tasks. Collaboration is allowed, but changes in
another owner's block should be reviewed with that owner first.

The previous `feat/sram-6t-cell-schematic` work has already been integrated into
`develop`. New bitcell work belongs in `feature/bitcell`.

Before starting new work on an existing feature branch, synchronize it with the
latest `develop`. Feature branches must not be force-updated or have their shared
history rewritten.

Do not merge a leaf cell as validated without the evidence required for the
stage being reviewed. A schematic, functional simulation, DRC result, and LVS
result each answer a different question. The project architecture and required
verification are defined in `specs/technical_specification.md`.

After the Phase 1 leaf cells have passed their required checks and the team has
reviewed the integrated work, merge `develop` into `main` through a pull request.
Create a milestone tag on `main` only after that merge. Release and hotfix
branches are outside the current workflow.

PR #6 merged the earlier `develop` revision into `main` on 2026-10-30.
PR #7 still targets `develop` and proposes the reconciled six-cell delivery.
After PR #7 is reviewed and merged, use a new `develop` -> `main` PR for that
delivery; the already closed PR #6 cannot publish subsequent changes.
