# Row decoder: complete operating-point matrix and FF screen refinement

Date: 2026-10-08 · Branch: `feature/peripherals`

## Scope and result

The full 16-pair address-transition matrix was run with DC operating-point
initialization at TT (1.8 V, 27 °C), SS (1.62 V, −40 °C), and FF (1.8 V,
125 °C). Each pair ran once against the schematic baseline and once against
the existing compact decoder PEX, for 96 ngspice simulations total. The
testbench still uses four schematic WL drivers and an estimated 17.4 fF per
wordline. The PEX hash remained
`8ee6b99aabf94bde9a1de2a13f0c040cda41dd55bb9568672e38a7f6bb54a6dc`; this
work did not run a new extraction.

All 96 simulations completed. Every baseline and PEX case passed the decoder
functional contract checks, and none of the ngspice logs contains an `Error:`
line. The runner returned code 1 for the FF campaign because 10 schematic
baseline cases exceeded its separate 1.95 V terminal-magnitude screen. This
is a screen finding, not an ngspice failure or a functional contract failure.
All FF PEX cases passed that screen.

| Corner | Baseline checks | PEX checks | Baseline magnitude screen | PEX magnitude screen | Peak baseline / PEX terminal magnitude | Max WL-to-90% baseline / PEX |
|---|---:|---:|---:|---:|---:|---:|
| TT | 1,664/1,664 | 2,560/2,560 | 16/16 pass | 16/16 pass | 1.945748 / 1.877775 V | 455.562 / 561.777 ps |
| SS | 1,664/1,664 | 2,560/2,560 | 16/16 pass | 16/16 pass | 1.766599 / 1.716479 V | 673.002 / 817.504 ps |
| FF | 1,664/1,664 | 2,560/2,560 | 6/16 pass; 10 outside | 16/16 pass | 1.954645 / 1.879693 V | 394.662 / 494.785 ps |

All measured WL-to-90% delays remain below the bench's 1 ns timing screen.
Textual warning counts across the 16 logs per stage were 0/144 at TT, 64/208
at SS, and 832/976 at FF (baseline/PEX); these counts include repeated
per-device model warnings. The runner's terminal-magnitude screen is distinct
from the polarity-oriented signed-bias audit below and is not, by itself, a
PDK or reliability signoff.

## Signed device-bias audit

The post-startup audit window begins at 1 ns. It treats the lower-potential
diffusion as the effective source for NFETs and the higher-potential diffusion
as the effective source for PFETs. This is an engineering screen for reverse
operation, not an approved model-owner convention.

Across the three corners, the PEX `VDS` and `VBS` values stayed within the
published ranges in this window. The schematic baseline PFET `VBS` crossed
the −0.10 V lower boundary at every corner; PEX did not. Both stages show
negative NFET `VGS` samples and positive PFET `VGS` samples under this
orientation convention:

| Corner | Stage | NFET `VGS` min..max | PFET `VGS` min..max | PFET `VBS` minimum |
|---|---|---:|---:|---:|
| TT | Baseline | −1.474141..+1.936551 V | −1.936551..+0.136551 V | −0.136551 V |
| TT | PEX | −1.563153..+1.877775 V | −1.860582..+0.077775 V | −0.077775 V |
| SS | Baseline | −1.141035..+1.740349 V | −1.766599..+0.120349 V | −0.120349 V |
| SS | PEX | −1.221833..+1.716479 V | −1.713869..+0.096479 V | −0.096479 V |
| FF | Baseline | −1.595279..+1.941931 V | −1.941931..+0.141931 V | −0.141931 V |
| FF | PEX | −1.739678..+1.875334 V | −1.861608..+0.079838 V | −0.079619 V |

These signed-range findings need review with the SKY130 model maintainer or
the project advisors. They do not demonstrate a logic error. The FF model
warnings also remain part of that review; the logs contain no fatal ngspice
errors.

## FF 0.5 ps refinement

The 10 FF address pairs that exceeded the baseline magnitude screen at 1 ps
were rerun at a 0.5 ps maximum timestep, with both baseline and PEX. All 20
simulations completed, and all 10 functional cases passed at each stage.
The same 10 baseline cases remained just above the screen, with a maximum of
1.954674 V; all 10 PEX cases remained below it, with a maximum of 1.879681 V.
Across the selected cases, the largest change in the reported maximum
terminal magnitude between 1 ps and 0.5 ps was 0.037 mV for the baseline and
0.014 mV for PEX. The small baseline excess is therefore repeatable under
this timestep refinement rather than a numerical-step artifact.

The largest baseline sample is FF `11→00`, device `x1.m12`, at 5.03325 ns:
`VGD = −1.954674 V`. At that sample, `A1B = −34.741 mV`, `N1 = 1.919933 V`,
and `EVAL_GND = 0.436868 V`. These values come from the archived raw
waveform. The VGD magnitude exceeds the runner's 1.95 V screen by 4.674 mV.
The case deck ramps PCLK from 0 to 1.8 V between 4.975 and 5.025 ns; the
sample is 8.25 ps after the ramp ends, with A0/A1 still at 1.8 V. The node
values make coupling around the start of evaluation the likely explanation,
rather than an address-change glitch. This is an inference; the voltage alone
does not establish that the design violates an approved reliability limit.
The PEX result is below the screen for all 10 refined pairs.

The threshold crossing should not trigger an arbitrary resize before the
team agrees what the 1.95 V VGD screen means for this model and topology.
The larger open item is still the signed `VGS` interpretation and the FF
BSIM4 warnings, not logic functionality.

## Evidence and reproduction

Full operating-point matrices and signed-bias audits:

- [TT comparison](../sims/row_decoder/results/compact_decoder_full_tt_opinit_matrix_1ps/comparison.csv) · [TT signed audit](../sims/row_decoder/results/compact_decoder_full_tt_opinit_matrix_1ps/signed_domain_audit.json)
- [SS comparison](../sims/row_decoder/results/compact_decoder_full_slow_opinit_matrix_1ps/comparison.csv) · [SS signed audit](../sims/row_decoder/results/compact_decoder_full_slow_opinit_matrix_1ps/signed_domain_audit.json)
- [FF comparison](../sims/row_decoder/results/compact_decoder_full_fast_opinit_matrix_1ps/comparison.csv) · [FF signed audit](../sims/row_decoder/results/compact_decoder_full_fast_opinit_matrix_1ps/signed_domain_audit.json)
- [FF 0.5 ps comparison](../sims/row_decoder/results/compact_decoder_fast_opinit_screen_refinement_0p5ps/comparison.csv) · [FF 0.5 ps signed audit](../sims/row_decoder/results/compact_decoder_fast_opinit_screen_refinement_0p5ps/signed_domain_audit.json)
- [FF screen refinement plot](assets/row_decoder_ff_opinit_screen_refinement.svg) · [plot generator](../sims/row_decoder/plot_ff_opinit_screen_refinement.py)

Reproduce one full corner using the running project EDA container:

```bash
SRAM_EDA_CONTAINER=sram-pex-diag-20261008 ./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py \
  --profiles tt --all-address-pairs --max-step-ps 1 --workers 1 \
  --timeout-s 900 --initial-operating-point \
  --output-root sims/row_decoder/results/compact_decoder_full_tt_opinit_matrix_1ps
```

Use the slow and fast profiles with their corresponding output-root names for SS / FF.
The FF runner exits nonzero because of the 10 baseline screen findings even
though all cases ran; run the signed audit independently after the campaign.

Reproduce the targeted FF 0.5 ps refinement and its signed-bias audit:

```bash
SRAM_EDA_CONTAINER=sram-pex-diag-20261008 ./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py --profiles fast --cases fast_00_to_11 fast_01_to_10 fast_10_to_00 fast_10_to_01 fast_10_to_10 fast_10_to_11 fast_11_to_00 fast_11_to_01 fast_11_to_10 fast_11_to_11 --max-step-ps 0.5 --workers 1 --timeout-s 900 --initial-operating-point --output-root sims/row_decoder/results/compact_decoder_fast_opinit_screen_refinement_0p5ps
python3 sims/row_decoder/audit_signed_device_domain.py --profiles fast --matrix-root sims/row_decoder/results/compact_decoder_fast_opinit_screen_refinement_0p5ps --expected-cases 10 --output-json sims/row_decoder/results/compact_decoder_fast_opinit_screen_refinement_0p5ps/signed_domain_audit.json --output-csv sims/row_decoder/results/compact_decoder_fast_opinit_screen_refinement_0p5ps/signed_domain_audit.csv
python3 sims/row_decoder/plot_ff_opinit_screen_refinement.py
```

Raw waveform files and ngspice logs are ignored by Git. The signed audit JSON
retains waveform hashes and provenance. The compact PEX remains unchanged.

## Remaining work

1. Review the effective-source signed-bias convention, `VGD` screen and FF
   BSIM4 warnings with the model maintainer/advisors; record acceptance
   criteria and required margins.
2. If review requires a topology or sizing change, rerun the affected
   functional and electrical matrices, then update layout, DRC/LVS and PEX
   only if the physical layout changes.
3. Repeat the broader current-sizing noise, retention and captured-address/
   PCLK qualification. Existing broad campaigns belong to earlier sizing.
4. Replace the 17.4 fF estimate with the approved extracted bitcell-row load
   when that physical input is available, then check all four decoder-to-WL
   paths.
5. Complete the integrated 4×8 read/write interface with the approved
   bitcell, precharge, decoder, WL-driver and write-driver views.

The high-compute parasitic extraction step has not been repeated here.
