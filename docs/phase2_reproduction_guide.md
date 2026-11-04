# Phase 2 reproduction and review guide

The delivered physical prototype is **4×8 only**. RTL also covers 8/16/32
words. Implementation and audit are complete within the declared experiment;
formal team/advisor acceptance remains pending. The [timing contract](../specs/sram_4x8_timing_contract.md)
and [acceptance table](phase2_review_20261104_acceptance.md) define the boundaries.

## Environment and inputs

Run from the repository root. Linux with Docker and the existing
`sram-xschem` environment is the tested environment; Windows portability has
not been demonstrated. See [environment setup](../tools/ENVIRONMENT.md).
The observed image is `isaiassh/unic-cass-tools:1.0.7`, image identity
`sha256:921d95e8cd03b8fbe5cec683ea14add4c1b6e0db1d5d05187fac7deb16b5e0f8`.
PDK: `/opt/pdks/sky130A`, HD library: `libs.ref/sky130_fd_sc_hd`.

| Tool/view | Recorded version or condition |
|---|---|
| Yosys | 0.44 |
| OpenROAD | ee9759486 |
| Magic / Netgen | 8.3.684 / 1.5.293 |
| ngspice | 44.2; `-n -b`, one thread |
| Icarus | 13 development build; zero-delay HD GLS |
| gdstk / NumPy | 0.9.62 / 1.26.4 |
| Mapping Liberty | SKY130HD TT/25 °C/1.8 V |
| Electrical models | Native `libs.tech/ngspice/sky130.lib.spice`, TT/27 °C/1.8 V |

The 25 °C Liberty reference and the 27 °C transistor experiment are distinct.
The default SPICE initialization file must not inject unrelated IHP OSDI models;
the runners use `ngspice -n`. Frozen Phase 1 selection is
`release/phase1_current.json`. Do not edit those inputs to reproduce results.

```sh
./tools/sram-eda --check
```

## Repository map

`rtl/`, `tb/`: public model, capture/controller/wrapper and independent scoreboard.
`synth/`, `verification/phase2/`: mapping and tri-state pilot.
`physical/phase2/`: phase binding, experimental SDC, selectors and old delivery index.
`tools/phase2*.py`, `tools/run_phase2*.py`: generator, runners and validators.
`reports/phase2/`: selected evidence and explicitly historical checkpoints.
`build/phase2/`: ignored, regenerable route databases and full local transients.
`presentations/phase2/`: editable academic presentation, notes, Q&A and figures.

## First review: no physical reconstruction

Choose a new output path for every command. The first command needs only
Python's standard library. It checks delivery hashes, the 171-file prior seal,
the supplemental 80-file seal, selected Git visibility, credentials patterns
and current document links. It **does not rerun DRC/LVS or SPICE**.

```sh
python3 tools/review_phase2_delivery.py --output reports/phase2/local/handoff_check_new --require-versioned
python3 tools/verify_phase1_handoff.py
./tools/sram-eda python3 -m unittest discover -s tools/tests -p 'test_phase2*.py' -v
```

`--require-versioned` checks the Git index; it is intended after the delivery
has been committed/staged, and rejects missing or ignored mandatory evidence.
For an unversioned working tree, omit that flag while preparing the selection.
The Python suites include synthetic checker fixtures, file/metadata checks,
real Icarus tests and CLI checks; their count is not a count of physical runs.

## RTL, synthesis and GLS

```sh
./scripts/run_rtl.sh --output reports/digital/phase2_reproduce_new
./scripts/run_rtl.sh --output reports/digital/phase2_reproduce_new --verify-evidence
./scripts/run_synth.sh --output reports/phase2/local/digital_new
```

The expected coverage is 154,303 functional RTL checks over all supported
models, and 15,619 checks for the mapped 4×8 wrapper. Counts include many
assertions per transaction. Synthesis preserves a custom storage black box,
20 HD FF and eight `ebufn` cells. Its GLS uses a functional macro substitute;
it is not transistor-level storage or qualified timing.

## Full physical reconstruction — costly, explicit

The following reconstructs the custom fabric, HD binding, place/route,
finishing, GDS reimport, DRC/LVS and routed GLS from sources. It does not need
a pre-existing ignored ODB and does not select the new candidate automatically.

```sh
./scripts/reproduce_phase2_4x8.sh reports/phase2/local/physical_new
```

For individual stages, use `./scripts/run_phase2.sh` actions `fabric`, `binding`,
`route`, `layout`, `gds` and `gls`. Their exact invocations and dependencies
are encoded in [the reproduction script](../scripts/reproduce_phase2_4x8.sh).
For example, recheck an already generated candidate without rerouting:

```sh
./scripts/run_phase2.sh gds --layout-report reports/phase2/local/physical_new/layout --output reports/phase2/local/gds_check_new
./scripts/run_phase2.sh gls --layout-report reports/phase2/local/physical_new/layout --output reports/phase2/local/gls_check_new
```

The original-to-rebuilt comparison already established identical extracted
SPICE including junction geometry, and GDS equality after timestamps alone
were normalized. See `reports/phase2/review_20261104/reproduction/results.json`.
Do not reconstruct merely to replace valid existing logs with newer dates.

## Electrical access — costly, explicit

```sh
./scripts/reproduce_phase2_4x8.sh reports/phase2/local/physical_with_access_new --with-electrical
./tools/sram-eda python3 tools/run_phase2_directed_review.py --output reports/phase2/local/directed_new
./tools/sram-eda python3 tools/run_phase2_startup_review.py --output reports/phase2/local/startup_new
./tools/sram-eda python3 tools/verify_phase2_startup_review.py --sources reports/phase2/local/startup_new --output reports/phase2/local/startup_verify_new
```

The directed and startup runners reuse the **selected original sealed extracted
SPICE**, not a new candidate merely because its path exists. They validate
model/input identities and must run in the matching PDK. The whole baseline
campaign is 710 ns; the directed campaign is 830 ns; startup has five separate
processes. These runs can take minutes to tens of minutes on a notebook.
Full extracted connectivity and junction geometry are included; detailed
interconnect RC is not. No internal `.ic`/`.nodeset` or behavioral bitcells
are used. A failed/incomplete run never replaces acceptance with PASS.

The startup runner refuses an existing output directory. The directed runner
can overwrite its output: **always choose a new directory**. The selected old
baseline, checks and receipts remain historical evidence and are not edited.

## Raw data, recovery and audit modes

The original full raw is versioned losslessly as
`reports/phase2/portable_raw/waveform.dat.gz`, with decompressed identity in
`results.json`. The five startup raws and the directed raw are local ignored
files named by their receipts. Their excerpts support figures, not independent
full-waveform reanalysis. A clean clone therefore has two distinct review routes:

1. **Identity/evidence review:** run the standard-library handoff audit above;
   inspect logs, declared criteria, hashes, selected checks and final geometry.
2. **Independent electrical reanalysis:** obtain the optional lossless raw
   bundle produced by `tools/bundle_phase2_raw.py` from its holder, or rerun
   the documented simulations. The bundle is a local optional transfer file,
   **not a promised GitHub download**. Its manifest records exact member hashes.

```sh
python3 tools/bundle_phase2_raw.py --output build/phase2/transfer/raw_review.tar.gz
# After transferring that exact bundle into the same /work repository mount:
python3 tools/bundle_phase2_raw.py --restore build/phase2/transfer/raw_review.tar.gz
```

Restore verifies every member before installing only missing raw files at
their original receipt paths. It refuses a conflicting existing file and
does not overwrite results or restore arbitrary archive paths. This recreates
an observation-data cache, not a simulator execution. The tested portability
scope is verified archive roundtrip in the existing Linux/container environment;
no Windows or different-PDK execution is claimed.

With matching local raw data available, the existing raw-dependent audits are:

```sh
./scripts/run_phase2.sh audit --output reports/phase2/local/raw_audit_new
./tools/sram-eda python3 tools/verify_phase2_startup_review.py --sources reports/phase2/final_polish_20261104/startup_reduced reports/phase2/final_polish_20261104/startup_extended --output reports/phase2/local/startup_raw_audit_new
```

Without the optional bundle, rerun new campaigns rather than copying a PASS
or changing a hash. Newly generated candidates are not selected automatically;
the checkpoint/acceptance selection must be reviewed before changing it.

## Evidence map and limitations

| Question | Source |
|---|---|
| Exact delivered views | `physical/phase2/delivery.json` |
| Current handoff index | `release/phase2_experimental/manifest.json` |
| Digital mapping/GLS | `reports/phase2/review_20261104/digital/` |
| Final DRC/LVS/GDS | `reports/phase2/final_gds/` |
| 401 + 1,092 = 1,493 MOS | `reports/phase2/review_20261104/structure/` |
| Baseline 128 read + 392 protocol | `reports/phase2/extracted_access_singlethread/` |
| Directed 1,332 total including 160 reads | `reports/phase2/review_20261104/directed/` |
| Startup 3,383 total including 240 reads | `reports/phase2/final_polish_20261104/startup_verification/` |
| Timing and final caveats | `specs/sram_4x8_timing_contract.md`, `docs/phase2_final_polish.md` |

Check free RAM, swap and disk before costly work. Native runners use resource
preflights and one-thread ngspice/OMP/BLAS. Keep several GB free for route
databases and transients; never delete unrelated data/caches to make a run fit.
No Fmax, complete external timing, RC/PVT/statistical startup, power/yield or
fabrication reliability is established. The Phase 1 model-coverage limitation
remains documented. This handoff does not start Phase 3 or grant advisor signoff.
