# Decoder-to-distributed-row PEX screen — 2026-10-09

## Result

A new transient screen connects the current dynamic decoder PEX, four current
wordline-driver PEX instances, and four extracted eight-bit row instances. The
four physical rows cover the 4×8 array's 32 bitcells and share the eight
BL/BLB column pairs.

The selected-row matrix completed **12/12 cases**: one address transition for
each selected row in TT, SS, and FF. All 4,992 decoder-output and row-tap checks
passed. A targeted 1 ps refinement of the slowest 5 ps case, SS/WL3, also
passed its 416 checks. This is a measured electrical screen under the bench
assumptions below; it does not close read/write operation, model acceptance,
or macro timing.

| Profile | Selected-row WL90 across 16 taps | Highest unselected tap | Highest recovery tap |
|---|---:|---:|---:|
| TT, 1.80 V, 27 °C | 2.142–2.149 ns | 16.2 µV | 0.330 µV |
| SS, 1.62 V, −40 °C | 3.221–3.224 ns | 12.8 µV | 0.577 µV |
| FF, 1.80 V, 125 °C | 1.834–1.840 ns | 170.4 µV | 151.3 µV |

The 1 ps refinement measured 3.224141–3.224215 ns across the SS/WL3 taps,
about 0.131 ps below the 5 ps result. This leaves 75.8 ps before the bench's
3.3 ns settling screen. That screen is an exploratory allowance, not a
specified SRAM requirement or approved timing margin.

The plot shows the measured range across all 16 WL taps in each selected
physical row:

![Selected-row WL90 delay from PCLK across distributed row taps](assets/row_decoder_distributed_row_pex_20261009.svg)

## PEX input and provenance

The physical-row source is a byte-for-byte copy of Danilo's existing
`layout/row_8_wl/pex/row_8_wl_pex.spice` from branch `feat/sram-6t-cell`, commit
`95c23c03ddc29f0d4bf40adf5fe7adb1b4af0a6a`. The SHA-256 is
`160b65544e12481aa99b287329ef2798e80c184c8f91566a23177ed8f0fb2dd6`. It has
48 MOS, 786 resistors, and 349 capacitors per eight-bit row; the four instances
therefore add 192 MOS, 3,144 resistors, and 1,396 capacitors to the transient
network. The copy and its provenance are under
[`sims/row_decoder/inputs/`](../sims/row_decoder/inputs/row_8_wl_pex_95c23c0.provenance.json).
Danilo's source files and branch were not modified, and no extraction was run.

The physical row has pins `VDD VSS WL BL0 BLB0 ... BL7 BLB7`. Each instance
connects its `WL` pin to the corresponding WL-driver PEX output. Each column
BL/BLB pair is shared by the four row instances.

## Bench assumptions

- Current decoder: 29-MOS schematic replaced with its current Magic R-C PEX.
- Wordline drivers: four instances of current Magic R-C PEX.
- Physical row: four instances of the extracted eight-bit row above.
- Address launch: `dfxtp_1` Liberty clock-to-Q PWL, nominal Q load 3.434554 fF.
- Capture-to-PCLK delay: 1.950 ns; ideal CLK falling edge: 20.700 ns.
- Settling screen: 3.3 ns after PCLK evaluation begins.
- Maximum transient step: 5 ps for the 12-case matrix; 1 ps for SS/WL3.
- Transitions select rows 0–3 once: `1→0`, `0→1`, `0→2`, `0→3`.
- Every BL and BLB is clamped to VDD for the entire transient. This holds the
  line pair at a stiff high level to keep the simulation numerically defined.

The bench does **not** reproduce the specified bitline timing: its ideal
precharge clamps remain active after PCLK enters evaluation. It has no
precharge/equalizer transistor, sense amplifier, write driver, access-enable
gate, or readback check. Cell state and bitcell terminal model-domain limits
are not qualified. The results establish that the decoder/driver chain can
charge and deassert the distributed WL taps under this explicit loading setup;
they do not establish SRAM read/write correctness.

PCLK remains an ideal source. Its actual generation, capture timing, external
setup/hold, and accepted operating frequency are unresolved. The 1.950 ns phase
and 3.3 ns settling screen are inherited experimental points, not project
specifications. Decoder/WL terminal screens passed in the matrix; model-owner
acceptance and reliability signoff remain open.

## Row-capacitance value to reconcile

The `.t0` input table copied into this branch records a maximum full-row Ceff
of 102.873935496 fF and a paired additional load of 93.351918068 fF. Its
provenance cites the same row PEX SHA as the direct simulation. Danilo's report
summary also mentions 93.351918 fF extra, while a detailed paragraph lists
98.914001 fF for the full row and 89.925201 fF extra. The older and `.t0`
capacitance CSVs both cite this PEX but report different values. This screen
instantiates the PEX directly, so it does not choose between those Ceff
measurements. Reconcile the table/report interpretation with the bitcell owner
before using one value as the official integration load.

## Reproduction and artifacts

Run from the repository root in the configured EDA environment:

```bash
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_distributed_row.py \
  --profiles tt slow fast --loads nominal \
  --phase-ps 1950 --clk-fall-ps 20700 \
  --settling-allowance-ns 3.3 --step-ps 5 \
  --output-dir sims/row_decoder/results/distributed_row_pex_selection_matrix_20261009

./tools/sram-eda python3 sims/row_decoder/run_row_decoder_distributed_row.py \
  --profiles slow --transitions 0:3 --loads nominal \
  --phase-ps 1950 --clk-fall-ps 20700 \
  --settling-allowance-ns 3.3 --step-ps 1 --timeout-s 300 \
  --output-dir sims/row_decoder/results/distributed_row_pex_slow_row3_refine_1ps_20261009

./tools/sram-eda python3 sims/row_decoder/plot_distributed_row_pex.py
```

The matrices, per-case decks/logs, checks, tap samples, terminal samples,
manifests, and executed runner snapshots are archived under
`sims/row_decoder/results/distributed_row_pex_*_20261009/`. The runner and plot
generator are `sims/row_decoder/run_row_decoder_distributed_row.py` and
`sims/row_decoder/plot_distributed_row_pex.py`.

## Next required work

1. Reconcile the two row-Ceff results with Danilo while leaving his source
   files unchanged.
2. Replace the continuous ideal BL/BLB clamps with the reviewed precharge and
   equalization interface; hold the bitlines during precharge and release them
   for evaluation.
3. Agree the actual PCLK source/phase and access-enable behavior with the
   control/interface owners, then repeat the selected-row and deassertion
   tests at that timing.
4. Add bitcell state, read/write stimulus, and data readback only after the
   bitline and precharge interfaces are agreed.

P3-7 is therefore **advanced, not fully closed**: distributed WL PEX behavior
has been exercised for all four selected rows, while the SRAM electrical
interface and owner acceptance remain open.
