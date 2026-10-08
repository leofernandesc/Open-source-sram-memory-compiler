# SKY130A dynamic row decoder layout

The canonical circuit is [row_decoder.sch](../../cells/row_decoder/row_decoder.sch).
This directory contains the generated Magic views, routing/extraction scripts,
DRC/LVS reports and the retained historical decoder R-C netlist. Only the decoder was
changed; the WL buffers used by the electrical bench remain schematic devices.

## Current compact layout - 2026-10-08

The latest remote sizing and extraction safeguards from `7ad0348` are preserved.
The new compact layout passes routed/flat DRC (0/0) and unique LVS (29 MOS,
22 nets). Its bbox is 98.80 × 36.92 µm: 12.93% smaller than `7ad0348`.
Horizontal M3 trunk length falls 22.68%, including added VSS shields.
New R-C extraction and electrical qualification are **pending on the other machine**.
The canonical PEX and extraction manifest are still historical; the runner blocks
their use for the new geometry via `pex/provenance.json` (stale).

Run on the other machine, with the updated checkout mounted at `/work`:

```powershell
docker exec -w /work sram-xschem bash tools/extract_row_decoder.sh
```

The helper selects Magic 8.3.684, repeats physical checks, performs all-net
R-C extraction and binds the resulting PEX to the checked layout. See the
[compaction report and handoff](../../docs/row_decoder_layout_compaction_20261008.md)
for geometry images, local evidence, installation and subsequent tests.
Previous revisions and PEX are archived under `archive/` with hashes.

## Historical evidence for 7ad0348 - 2026-10-07 UTC

- Magic 8.3.684, SKY130A tech 1.0.493, `drc(full)`: **0 routed / 0 flattened
  errors**, measured after `drc catchup`. See `reports/route.log` and
  `reports/drc_flat.log`.
- Netgen 1.5.293: **Circuits match uniquely**, 29 MOS (17 NFET / 12 PFET),
  22 connectivity nets, matching external pins and bulk connections.
  See `reports/lvs.log` and `reports/lvs.out`.
- [Historical PEX](archive/remote_7ad0348/pex/row_decoder_pex.spice): **744 R / 392 C / 29 MOS**;
  resistance networks cover **all 22 nets**. No negative capacitors.
  The pin order is `VDD PCLK A0 A1 DEC0 DEC1 DEC3 DEC2 VSS`.
  [Historical extraction manifest](archive/remote_7ad0348/pex/extraction_manifest.json) records hashes,
  tool version, extraction cutoffs and counts by network.
- Matched schematic/PEX campaigns pass **13/13 cases each at both 5 ps and
  1 ps**, with zero functional, precharge or experimental voltage-screen
  findings. See [5 ps results](../../sims/row_decoder/results/row_decoder_pex_verified_5ps/)
  and [1 ps results](../../sims/row_decoder/results/row_decoder_pex_verified_1ps/).
  Slow-corner PEX WL delay to 90% is 891.858-943.617 ps; WL precharge to
  10% is 877.315-899.474 ps. The existing 1 ns checks were retained.

This closes the selected decoder electrical matrix with a distributed R-C
model. The scope is nine TT/1.8 V/27 C transitions and four SS/1.62 V/-40 C
diagonal transitions, ideal 50 ps input edges and a 17.4 fF estimated row load.
Physical row loading, broader PVT/noise/retention qualification, captured-address
fanout and full-macro operation remain to be requalified for the changed source.
The experimental 1.95 V screens do not establish signed model-domain or
reliability clearance. Source-energy measurements require their own numerical
convergence review; see the validation log.

## What changed

Placement groups the address inverters/buffers and each row's devices around
a central routing channel. Each M3 track ends at its actual connections,
removing the old full-width stubs. All contacts and vias retain DRC-valid
landing dimensions. Address inverters M1-M4 use W=0.84 um, precharge PFETs
M5/M11/M16/M21 use W=1.25 um, evaluation stacks use W=2 um and output PFETs
use W=3 um. All decoder devices retain L=0.15 um, nf=1 and mult=1.

Detailed extraction explicitly sets `extresist threshold 0`, `mindelay 0` and
`minres 100` (milliohms). Magic's default threshold had emitted only the VSS
resistance network in the previous 393-R artifact; merely finding both R and C
was insufficient. The builder now requires all 22 networks, positive
resistances, preserved pins, nonnegative capacitances and clean connectivity
LVS. The simulator checks the extraction/source hashes and compares MOS
connectivity and geometry before accepting a PEX. Every distributed dynamic
segment must have a saved waveform; baseline coverage is reported separately.

## Reproduce

Use the configured `sram-xschem` container (see [environment setup](../../tools/ENVIRONMENT.md)).
The [versioned installer](../../tools/install_magic_8_3_684.sh) reproduces the
Magic 8.3.684 build inside the container.
Import with Magic 8.3.589 and route/extract with 8.3.684. The detailed-extraction
cutoff controls require Magic 8.3.653 or newer; use the recorded 8.3.684 build
for reproduction. From PowerShell in the repository root:

```powershell
docker exec -w /work sram-xschem bash -lc 'PATH=/opt/magic/8.3.589/bin:$PATH; for tool_dir in /opt/netgen/*/bin /opt/xschem/*/bin; do PATH=$tool_dir:$PATH; done; export PATH PDK_ROOT=/opt/pdks PDK=sky130A; python3 layout/row_decoder/build_layout.py --skip-route'
docker exec -w /work sram-xschem bash -lc 'PATH=/opt/magic/8.3.684/bin:$PATH; for tool_dir in /opt/ngspice/*/bin /opt/netgen/*/bin /opt/iverilog/*/bin /opt/xschem/*/bin; do PATH=$tool_dir:$PATH; done; export PATH PDK_ROOT=/opt/pdks PDK=sky130A; python3 layout/row_decoder/build_layout.py --skip-import --extract'
docker exec -w /work sram-xschem bash -lc 'for tool_dir in /opt/ngspice/*/bin /opt/netgen/*/bin /opt/iverilog/*/bin /opt/xschem/*/bin; do PATH=$tool_dir:$PATH; done; export PATH PDK_ROOT=/opt/pdks PDK=sky130A; python3 sims/row_decoder/run_row_decoder_pex_contract.py --output-root sims/row_decoder/results/decoder_reproduction_5ps --max-step-ps 5 --workers 2 --timeout-s 300'
```

Repeat the last command with a new empty output directory and
`--max-step-ps 1` for the numerical comparison. The runner deliberately rejects
an existing nonempty output directory. In the configured Linux launcher, the
corresponding extraction command remains:

```bash
./tools/sram-eda python3 layout/row_decoder/build_layout.py --skip-import --extract
```

`--lvs-only` repeats routing, DRC and connectivity LVS without `extresist` or
R-C generation. `row_decoder_flat_extracted.spice` is **connectivity only**;
use `pex/row_decoder_pex.spice` for decoder post-layout simulations.
`--skip-route` cannot be combined with `--extract` or `--lvs-only`.

## Historical artifacts

Earlier negative-capacitance, cap-only and timed-out experiments remain
historical evidence in the [validation log](../../docs/feature_peripherals_validation_log.md).
The cap-only artifact `reports/row_decoder_cap_only_unqualified.spice` has
231 C / 0 R and remains unqualified. The earlier 393-R PEX and its four slow
failures are superseded by the all-network extraction and passing matrix above.
