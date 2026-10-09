# Git workflow

Phase 1 uses a small Git Flow with `main`, `develop`, and `feature/*` branches.

| Branch | Purpose | Integration |
|---|---|---|
| `main` | Reviewed project milestones | Pull request from `develop` |
| `develop` | Integration of completed work | Pull requests from feature branches |
| `feature/*` | Work owned by one Phase 1 block owner | Starts from and returns to `develop` |

Do not commit directly to `main` or `develop`. Keep commits focused, review the
diff, and use a pull request for integration. Merge the latest `develop` into a
feature branch before its pull request; do not rewrite a shared branch's history.
Keep generated temporary files out of commits unless they are deliberately
selected as reproducible verification evidence.

## Phase 1 branches and owners

| Branch | Owner | Blocks |
|---|---|---|
| `feature/bitcell` | Danilo (Person 1) | 6T bitcell through schematic, simulation, layout, DRC, and LVS |
| `feature/sense-precharge` | André (Person 2) | Sense amplifier and precharge/equalization through schematic, simulation, layout, DRC, and LVS |
| `feature/peripherals` | Leonardo (Person 3) | Wordline driver and write driver through schematic, simulation, layout, DRC, and LVS; dynamic 2-to-4 decoder candidate and qualification are planned for Phase 2 macro integration, pending formal validation by the team/advisors |

Each owner is responsible for carrying the assigned blocks through the complete
Phase 1 flow. The dynamic 2-to-4 decoder candidate and its electrical/physical
qualification, together with the complete 4×8 macro, are currently planned as
Phase 2 macro-integration deliverables. This reassignment changes the original
planning for the decoder deliverable and remains subject to formal validation
by the team/advisors.
Collaboration is allowed, but architecture or implementation changes in
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
