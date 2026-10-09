# Current decoder: finite-hold, charge-injection, and phase-duration screens

Date: 2026-10-09 · Branch: `feature/peripherals`

## Scope and input identity

These campaigns repeat selected robustness experiments on the current,
freshly-netlisted 29-MOS dynamic decoder plus four current WL-driver instances.
The input netlist hash is
`2c8e802f8a5392eb2680e67cd6381627f9a680f8972325296ead1c387955202d`; all four
campaign manifests use this same netlist and record source, model-library,
helper, and tool hashes. The decoder source SHA-256 is
`90f6aa170d7f9b7019b55d3cd43ee4482d9c5d2927f0b0b011a6f5b492c8ec50`.
Xschem 3.4.6 and ngspice 44.2 ran inside the configured SKY130A container.

The current sizing captured in the manifests is: address inverter N/P 0.84 µm,
output inverter N/P 2.0/3.0 µm, precharge PFET 1.25 µm, evaluation stack 2.0 µm,
footer 1.5 µm, and address-buffer N/P 2.0 µm, with 0.15 µm channel length.
The bench used a 17.4 fF lumped WL load and 50 ps address/PCLK ramps. Three
profiles were tested: TT/1.80 V/27 °C, SS/1.62 V/−40 °C, and FF/1.80 V/125 °C.
This is a three-point diagnostic set, not a full PVT grid. The original case
checks and scripts remain in each result folder. Raw waveform files were not
retained; targeted waveforms can be reproduced with `--artifacts-dir`.

## Results

| Campaign | Cases | Result classification | Finding |
|---|---:|---|---|
| Evaluation hold / finite retention | 36 | 36 `PASS` | Four rows × 10, 100, 1000 ns × three profiles; no detected wrong-row assertion. |
| Charge injection | 42 | 38 `PASS`, 4 `REJECTED_PERTURBATION` | All 36 cases through 4 fC pass. At 8 fC, 4 of 6 cases detect a perturbation; 2 still pass. |
| PCLK low-phase duration | 168 | 88 `PASS`, 80 `REJECTED_TIMING` | Shortest sampled low duration passing all four rows: TT 0.4 ns, SS 0.6 ns, FF 0.4 ns. |
| PCLK high/evaluation duration | 168 | 76 `PASS`, 92 `REJECTED_TIMING` | Shortest sampled high duration passing all four rows: TT 0.5 ns, SS 0.75 ns, FF 0.5 ns. |

All retention cases passed the script's custom 1.95 V magnitude and output
upper screens. The lowest recorded unselected dynamic-node minimum over those
cases was 1.63810 V in SS at a 1000 ns evaluation hold; the largest wrong-row
output peak was 2.36 mV. These are model-specific simulated values, not a
retention specification or silicon reliability result.

The 8 fC injection results vary by profile and node. TT/N1 and FF/N1 pass while
their N3 counterparts are tagged `REJECTED_PERTURBATION`; both slow-profile
nodes are tagged. This is a bracket for the script's 120 ps injected-charge
waveform, not an approved noise immunity or system noise budget. No mismatch
Monte Carlo was run.

The minimum phase durations are the first passing points on the declared grid,
not exact limits. Do not add the sampled low/high minima and call the sum a
minimum clock period: captured-address setup, PCLK generation, distributed
row RC, bitcell access, and the rest of the SRAM cycle are not included. The
larger combined decoder/WL PEX capture study remains separately documented in
[`row_decoder_capture_combined_pex_20261009.md`](row_decoder_capture_combined_pex_20261009.md).

These screens are schematic-level requalification at 17.4 fF. They do not
supersede the combined PEX timing results, the 102.873935496 fF WL-leaf stress
screen, model-domain review, or project-owner acceptance of limits.

## Reproduction

```bash
./tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 python3 sims/row_decoder/run_row_decoder_contract.py \
  --campaign retention --profiles tt slow fast --workers 2 \
  --output-dir sims/row_decoder/results/current_decoder_retention_20261009

./tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 python3 sims/row_decoder/run_row_decoder_contract.py \
  --campaign charge --profiles tt slow fast --workers 2 \
  --output-dir sims/row_decoder/results/current_decoder_charge_20261009

./tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 python3 sims/row_decoder/run_row_decoder_contract.py \
  --campaign low_phase --profiles tt slow fast --workers 2 \
  --output-dir sims/row_decoder/results/current_decoder_low_phase_20261009

./tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 python3 sims/row_decoder/run_row_decoder_contract.py \
  --campaign high_phase --profiles tt slow fast --workers 2 \
  --output-dir sims/row_decoder/results/current_decoder_high_phase_20261009
```

Each output directory contains `manifest.json`, `executed_script.py`, the
fresh input netlist, case checkpoints, and `summary.csv`, `checks.csv`, and
`terminals.csv`. The manifests mark all four campaigns complete and record the
full 29-device source/model/tool provenance.

## Result files

- [Finite-hold summary](../sims/row_decoder/results/current_decoder_retention_20261009/summary.csv) · [manifest](../sims/row_decoder/results/current_decoder_retention_20261009/manifest.json)
- [Charge-injection summary](../sims/row_decoder/results/current_decoder_charge_20261009/summary.csv) · [manifest](../sims/row_decoder/results/current_decoder_charge_20261009/manifest.json)
- [Low-phase summary](../sims/row_decoder/results/current_decoder_low_phase_20261009/summary.csv) · [manifest](../sims/row_decoder/results/current_decoder_low_phase_20261009/manifest.json)
- [High-phase summary](../sims/row_decoder/results/current_decoder_high_phase_20261009/summary.csv) · [manifest](../sims/row_decoder/results/current_decoder_high_phase_20261009/manifest.json)
