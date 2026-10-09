# Captured `VALID_ACCESS_Q` Liberty timing screen — 2026-10-09

## Result

The phase-chain integration was rerun with `VALID_ACCESS_Q` shaped from the
SKY130 `dfxtp_1` Liberty clock-to-Q rise delay and output transition. The
decoder, wordline and Danilo precharge inputs remained at their current PEX
revisions; the 80-stage Xschem phase source remained transistor-level.

All six sampled cases passed: address transition 0→3, both read (`001`) and
write (`010`) control vectors, and the TT, SS and FF library profiles. The
combined checks file records **1,008/1,008 PASS**. The smallest PRECH release
lead was **334.158 ps in FF**, 84.158 ps above the experimental 250 ps guard.
That guard is not a technical-specification limit.

| Profile | Liberty CLK-to-Q rise | Q rise transition | Measured Q arrival | PRECH lead | Read/write |
|---|---:|---:|---:|---:|---|
| TT, 1.80 V, 25 °C | 307.041 ps | 47.479 ps | 307.041 ps | 436.665 ps | 2/2 PASS |
| SS, 1.60 V, −40 °C | 677.087 ps | 94.679 ps | 677.087 ps | 692.543 ps | 2/2 PASS |
| FF, 1.65 V, 100 °C | 248.733 ps | 41.789 ps | 248.733 ps | 334.158 ps | 2/2 PASS |

A separate idle/invalid vector (`000`) passed **30/30 checks** in TT. PCLK
peaked at 6.35 mV, all four DEC outputs remained below 1.56 mV, all wordlines
remained below 1.78 µV, the four internal decoder nodes stayed above 1.755 V,
and all sixteen bitlines ended at approximately 1.8 V. This is a single
representative vector, not a complete invalid-control matrix; the remaining
invalid vectors and corners are open.

The Liberty table interpolation used a 53.1329 ps clock slew and a nominal
3.434554 fF output load. The simulated PCLK rise was about 1.837 ns after the
capture edge in FF and 2.119 ns in TT. These are bounded results for the
selected 0→3 address change and the existing phase/PEX setup, not an SRAM
frequency or full timing signoff.

## Why the direct `dfxtp_1` SPICE attempt failed

The archived direct-cell attempt stopped at `XCAP0.X12` with ngspice reporting
`could not find a valid modelname`; see the [failed case log](../sims/row_decoder/results/capture_to_pclk_smoke2/cases/tt_a0_to_3_p500ps/ngspice.log).
The direct SKY130 standard-cell SPICE subcircuit uses four special NFETs with
`W=0.36 µm`, `L=0.15 µm`. The simulation deck loads the project's continuous
`sky130.lib.spice` model family. In that family, the narrowest `nshort_model`
bin at `L=0.15–0.18 µm` starts at `W=0.42 µm`, so the 0.36 µm devices have no
matching bin. The separate SKY130 TT PM3 device file has a 0.36–0.39 µm bin,
which confirms these are different model-file families and should not be
silently mixed.

A temporary diagnostic copy with those four widths changed to 0.42 µm ran to
completion. That changes the official cell geometry, so it is diagnostic
evidence only and is not used as a design or validation result. The test
runner instead keeps the current continuous model for the custom decoder and
uses the standard-cell Liberty arc for the DFF output transition.

## Model boundary

`--valid-access-q-model dfxtp_1-liberty` replaces the ideal step at
`VALID_ACCESS_Q` with a PWL rise timed by the profile's `dfxtp_1` Liberty
clock-to-Q and rise-transition tables. It represents the output timing of one
captured valid bit for the sampled read/write vectors. It does **not** add a
transistor-level DFF or control-qualification circuit.

The following remain open: the actual captured control logic and D-input
setup, capture-cell output loading from the implemented phase gates,
metastability, glitches, the remaining invalid vectors/corners, the next
cycle/qualifier deassertion, legal clock windows, phase-source layout/DRC/LVS/
PEX, bitcell access, and stored-data read/write/readback. No extraction was
run.

## Reproduction

Run from the repository root with a new output directory:

```bash
./tools/sram-eda python3 sims/row_decoder/run_precharge_phase_interface.py \
  --phase-source xschem-tapped-delay-chain \
  --valid-access-q-model dfxtp_1-liberty \
  --profiles tt slow fast \
  --transitions 0:3 \
  --control-vectors 001 010 \
  --phase-ps 2100 \
  --clk-fall-ps 22000 \
  --settling-allowance-ns 3.4 \
  --wl-cap-ff 102.873935496 \
  --release-lead-ps 250 \
  --turnoff-guard-ps 1800 \
  --step-ps 5 \
  --output-dir sims/row_decoder/results/phase_source_valid_access_q_liberty_dfxtp1_rerun
```

The representative invalid-vector case used the same phase/load settings with
`--profiles tt --control-vectors 000` and a fresh output directory:

```bash
./tools/sram-eda python3 sims/row_decoder/run_precharge_phase_interface.py \
  --phase-source xschem-tapped-delay-chain \
  --valid-access-q-model dfxtp_1-liberty \
  --profiles tt \
  --transitions 0:3 \
  --control-vectors 000 \
  --phase-ps 2100 \
  --clk-fall-ps 22000 \
  --settling-allowance-ns 3.4 \
  --wl-cap-ff 102.873935496 \
  --release-lead-ps 250 \
  --turnoff-guard-ps 1800 \
  --step-ps 5 \
  --output-dir sims/row_decoder/results/phase_source_valid_access_q_liberty_dfxtp1_invalid_tt_rerun
```

Archived evidence:

- [Summary CSV](../sims/row_decoder/results/phase_source_valid_access_q_liberty_dfxtp1_20261009/summary.csv)
- [All checks](../sims/row_decoder/results/phase_source_valid_access_q_liberty_dfxtp1_20261009/checks.csv)
- [Run manifest and Liberty arc values](../sims/row_decoder/results/phase_source_valid_access_q_liberty_dfxtp1_20261009/manifest.json)
- [Runner used for the run](../sims/row_decoder/results/phase_source_valid_access_q_liberty_dfxtp1_20261009/executed_script.py)
- [TT invalid vector 000 checks](../sims/row_decoder/results/phase_source_valid_access_q_liberty_dfxtp1_invalid_tt_20261009/checks.csv)
