# SKY130A dynamic row decoder layout

The canonical circuit is [row_decoder.sch](../../cells/row_decoder/row_decoder.sch).
This directory contains the generated Magic views, routing/extraction scripts,
DRC/LVS reports and the retained historical decoder R-C netlist. Only the decoder was
changed; the WL buffers used by the electrical bench remain schematic devices.

## Current compact layout - 2026-10-08

The compact layout preserves the sizing and extraction safeguards from
`7ad0348`. Its bounding box is 98.80 × 36.92 µm, 12.93% smaller than
`7ad0348`; horizontal M3 trunk length falls 22.68%, including the added VSS
shields.

On 2026-10-08, Magic 8.3.684 with SKY130A tech 1.0.493 reported zero routed
and flattened DRC errors. Netgen 1.5.293 reported a unique LVS match for 29 MOS,
22 nets and nine external pins. The new PEX contains **762 resistors, 389
capacitors and 29 MOS**; resistance covers all 22 labeled networks, every
resistance is positive, and no capacitor is negative. The pin order remains
`VDD PCLK A0 A1 DEC0 DEC1 DEC3 DEC2 VSS`. PEX SHA-256:
`8ee6b99aabf94bde9a1de2a13f0c040cda41dd55bb9568672e38a7f6bb54a6dc`.
`pex/provenance.json` is current.

The matched 13-case schematic/PEX campaigns pass **13/13 at 5 ps and 13/13 at
1 ps**, with zero contract findings in either run. At 1 ps, PEX selected-WL
90% delay is 551.858–815.389 ps, precharge-to-10% is 524.334–789.564 ps and
rise slew is 294.811–445.935 ps. The largest PEX terminal-magnitude result is
1.878 V against the runner's absolute 1.95 V terminal screen. Between 5 ps and
1 ps, the largest per-case changes are 0.091 ps in WL 90% delay, 0.127 ps in
precharge delay, 0.052 ps in rise slew and 4.2 mV in terminal magnitude.

The additional complete TT address-pair matrix covers all 16 ordered old/new
pairs, including same-address pairs. At both 5 ps and 1 ps, schematic baseline
and PEX each passed 16/16 cases with zero contract findings; all absolute
terminal screens passed. Maximum PEX terminal magnitude was 1.875056 V at 5 ps
and 1.877770 V at 1 ps. The largest 5 ps-to-1 ps changes were 0.081 ps in WL
90% delay, 0.126 ps in precharge delay, 0.051 ps in rise slew and 4.19 mV in
terminal magnitude. Results: [5 ps](../../sims/row_decoder/results/compact_decoder_full_tt_matrix_5ps/)
and [1 ps](../../sims/row_decoder/results/compact_decoder_full_tt_matrix_1ps/).

The recorded electrical campaigns include complete 16-pair TT, SS and
FF matrices at 5 ps and 1 ps, using 50 ps input edges, Gear integration and
the estimated 17.4 fF row load. All baseline and PEX cases pass the recorded
contract checks. Selected high-sensitivity PCLK energy cases were refined at
0.5 ps; they differ from 1 ps by less than 0.89% in baseline and 0.51% in PEX.
FF model-parameter warnings were traced to ngspice's BSIM4 checks and remain a
model-qualification caveat. The decoder alone is extracted; four WL buffers
remain schematic devices. This does not establish broad PVT, physical-row
loading, full-macro timing, signed model-domain clearance or reliability
qualification. Full logs and result directories are listed in the
[validation log](../../docs/feature_peripherals_validation_log.md), the
[SS matrix audit](../../sims/row_decoder/results/compact_decoder_full_slow_matrix_audit.json),
the [PCLK convergence audit](../../sims/row_decoder/results/compact_decoder_pclk_energy_convergence_audit.json),
and the [compaction handoff](../../docs/row_decoder_layout_compaction_20261008.md).
Previous layouts and PEX remain archived under `archive/` with hashes.

The full FF/1.8 V/125 °C extension now covers all 16 ordered address pairs.
At 5 ps and 1 ps, baseline and PEX each pass 16/16 cases and all recorded
contract and voltage-screen checks. At 1 ps, maximum PEX WL delay to 90% is
492.795 ps, precharge-to-10% is 461.940 ps, and terminal magnitude is
1.878690 V. The largest matched 5 ps-to-1 ps PEX differences are 0.130 ps in
WL delay, 0.191 ps in precharge, 0.058 ps in WL rise slew, and 0.373 mV in
terminal magnitude. PCLK source cycle energy differs by up to 0.502 fJ
(12.85% relative to the 1 ps value), so that metric is more timestep-sensitive.

The baseline peak is 1.949037 V of absolute `VGD` in `01→10`, 0.963 mV below
the runner's 1.95 V numerical screen. This is not signed PDK model-domain
headroom: `VGD` is not one of the documented signed model-range variables.
The FF logs also report `A2 > 1` (clamped by ngspice) and negative `Eta0`,
`Pdibl1`, and `Pdibl2`. These results pass the project checks under ngspice's
reported model handling; they do not establish full model-domain or
reliability qualification. See the [FF-hot report](../../docs/row_decoder_fast_hot_qualification_20261008.md)
and [full matrix audit](../../sims/row_decoder/results/compact_decoder_full_fast_matrix_audit.json)
for warning records, hashes, per-case data and scope limits.

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
Magic 8.3.684 build inside the container. From the repository root:

```bash
./tools/sram-eda --check
./tools/sram-eda bash tools/extract_row_decoder.sh
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py --output-root sims/row_decoder/results/compact_decoder_5ps --max-step-ps 5 --workers 2 --timeout-s 900
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py --output-root sims/row_decoder/results/compact_decoder_1ps --max-step-ps 1 --workers 2 --timeout-s 900
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py --output-root sims/row_decoder/results/compact_decoder_full_tt_matrix_5ps --profiles tt --all-address-pairs --max-step-ps 5 --workers 2 --timeout-s 900
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py --output-root sims/row_decoder/results/compact_decoder_full_tt_matrix_1ps --profiles tt --all-address-pairs --max-step-ps 1 --workers 2 --timeout-s 900
```

The extraction helper selects Magic 8.3.684 and runs
`python3 layout/row_decoder/build_layout.py --skip-import --extract`. Use fresh
output directories when repeating simulations; the runner rejects a nonempty
output directory.

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
