# Phase 3 team transfer quickstart

**Status at the 2026-11-22 checkpoint:** experimental 4×8 v6 with three
StrongARM senses passes the 250 ns post-layout fixture in TT, SS and FF.
The 18-cycle integrated regression on v6 is `NOT_RUN`; full electrical
characterization and Liberty are `NOT_CHARACTERIZED` / pending. These are
separate validation boundaries. This branch is not a production sign-off.

## Repository and checkpoints

- Work from `integration/phase3-danilo-ss`, whose local historical base was
  `8e1d961d65054b59f9032ed5f9338d9ee4353c33`. Verify the actual remote
  HEAD before making changes.
- Read [the detailed Portuguese handoff](phase3_handoff_equipe_20261122.md),
  [the three-StrongARM implementation report](phase3_triple_strongarm_20261122.md)
  and [the functional C250 report](phase3_fechamento_funcional_strongarm_20261122.md).
- The four separately verified ZIPs needed to reproduce the local handoff are
  `phase3_handoff_equipe_20261122.zip`,
  `phase3_fechamento_funcional_strongarm_20261122.zip`,
  `phase3_triple_strongarm_20261122.zip` and
  `phase3_revisao_sense_sky130_checkpoint_C_20261121.zip`.
  They must be transferred through an approved shared storage location;
  their binary contents are **not** part of this source branch.
- Check SHA-256 before extraction. Restore into a **separate clean checkout**
  according to the handoff package's `CRITICAL_README.md`; run its `restore.py`
  with `--dry-run` before allowing any writes. The package also contains the
  exact artifact manifest and checksums.
- Other intermediate `NOTEBOOK_ONLY` files, including earlier failed fabric
  revisions, are not all recovered by that minimum four-ZIP plan. Preserve the
  original notebook or a supplementary backup if the full experimental history
  is required.

## Architecture and next decision

The original macro C produced `0xF8` instead of `0xF0` in TT for cycles 16
and 17 because sense 3 regenerated the wrong value, despite correct stored
data. In FF, the original senses 6 and 7 also produced an incorrect `0xCF`
instead of `0x0F` in cycle 15. Replacing senses 3, 6 and 7 with StrongARM
fixed the known C250 failures, but does **not** yet prove all bus handoffs or
complete operating limits.

The team has two mutually exclusive next investigation paths:

1. **Study eight StrongARM senses:** preserve v6 as control, audit the
   additional shared SCLK/bitline/power load, build a virtual eight-sense ECO
   and compare TT/SS/FF before any physical change. This is currently the
   recommended experiment, **not yet a ratified design change**.
2. **Complete validation of v6:** use the archived `continue_campaign.py`
   and the frozen 1.5 ns host guard to execute the 370 ns integrated fixture
   in TT, followed conditionally by SS and FF. This can take hours.

Do not characterize Liberty or reorganize bitcells until the team has selected
and verified a final physical candidate. The first area-optimization pass is
planned for **peripheral block placement**, preserving the internal 6T bitcell
geometry. Any new layout invalidates old PEX-dependent timing and power data.

## Reproduction and result integrity

- Preserve the existing C, v6, SNM and bus-ownership checkpoints separately.
- Do not substitute a virtual ECO netlist for the GDS-derived physical PEX.
- Keep the 300 ps collision stress test and the historical ±100 ps DATA
  window separate from the functional 1.5 ns handoff protocol.
- The bitcell mismatch-SNM pilot contains 200 valid Hold and 206 valid Read
  samples in experimental `tt_mm` at 1.8 V / 27 °C; model-domain approval
  remains open. Do not rerun 406 seeds without a clear reason.
- A completed C250 check is not equivalent to access/setup/hold, static power,
  dynamic energy or a characterized Liberty model.
- Record actual PVT, netlist and GDS/LEF/PEX SHA-256 with every new result.

## Repository hygiene

Version reviewed source code, tests, architecture documentation and compact
provenance manifests in Git. Keep waveforms, generated decks, PDK copies and
other large reproducible outputs in the separately hashed artifacts.
Do not use `git add .` on an EDA working tree. Avoid force-push, reset or
history rewriting. Changes to the public specification require an explicit
approved architectural decision.
