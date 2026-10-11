# Captured control to PCLK/PRECH interface screen — 2026-10-09

## Result

The initial paired screen combined the captured qualifier and transistor-level
phase source into one electrical path for two representative SKY130 conditions
at TT, 1.80 V and 27 °C: valid read vector `001` with address transition
`0→3`, and invalid
vector `000`. Each was compared with a Liberty-timed `dfxtp_1` Q waveform
feeding the same transistor-level phase source and downstream PEX. The valid
read pair passed **342/342 checks**; the invalid pair passed **66/66 checks**.
There were no ngspice errors or screen rejections in either run.

The valid-read measurement shows close agreement with the Liberty reference at
this one TT operating point. The invalid-vector measurement shows that the
captured Q remains low at its post-capture sample points, `PCLK` stays below
5.0 mV, and active-low `PRECH` stays below 0.385 mV, so the phase source
continues to hold precharge active. These are representative screens, not a
completed PVT qualification.

| Measurement | Captured transistor-level path | Liberty-timed Q reference | Difference |
|---|---:|---:|---:|
| CLK capture edge to PCLK 50% rise | 1,828.682 ps | 1,827.562 ps | +1.120 ps |
| PRECH 75% rise to PCLK 50% rise | 391.913 ps | 391.968 ps | −0.054 ps |
| PCLK 50% fall to PRECH 75% falling crossing | 2,253.998 ps | 2,253.994 ps | +0.004 ps |
| Valid-read Q 50% clock-to-Q rise | 184.009 ps | 307.041 ps | −123.032 ps |

The comparison reference uses the nominal `dfxtp_1` Liberty lookup load of
3.434554 fF and 53.1329 ps clock slew to shape Q. That Liberty TT table is
characterized at 25 °C, while the native-PM3 circuit deck runs at 27 °C. It is
a timing-table reference, not a transistor-level DFF instance or an exact
extracted-load match to the qualifier's phase-logic input.

![Captured qualifier and phase-source waveforms against the Liberty reference](../sims/row_decoder/results/captured_phase_interface_tt_read_20261009/captured_phase_vs_liberty_tt_read_a0_to_3.png)

## Follow-up: registered row address connected to PEX

The earlier paired runs above used transistor-level capture of the qualified
access bit but supplied the row address from a Liberty-timed PWL source. A
follow-up run now uses `captured_row_decoder_control.sch`, which composes the
two-bit rising-edge row-address register with the captured access qualifier
and the existing PCLK/PRECH source. Its `A0_Q/A1_Q` outputs directly drive the
current dynamic decoder PEX. The same decoder/WL/precharge network is used in
the Liberty-timed reference mode.

For the TT valid-read `001`, address `0→3` case, the input address is presented
500 ps before the 15 ns rising edge and inverted at 15.8 ns while CLK remains
high. The captured A0/A1 values remain high at the post-capture and live-input
change samples. Both paired modes pass all **350 checks** in the run; the
actual-mode register-to-decoder path passes its four sampled address checks.

| Measurement | Captured address/control/phase path | Liberty-timed reference | Difference |
|---|---:|---:|---:|
| CLK capture edge to PCLK 50% rise | 1,828.679 ps | 1,827.562 ps | +1.117 ps |
| PRECH 75% release to PCLK 50% rise | 391.916 ps | 391.968 ps | −0.052 ps |
| PCLK 50% fall to PRECH 75% assertion | 2,254.000 ps | 2,253.994 ps | +0.006 ps |
| Valid-access Q 50% clock-to-Q rise | 184.009 ps | 307.041 ps | −123.032 ps |

This advances the address path from a structural/functional wrapper check to
one loaded transistor-level PEX case. It is not an address setup/hold sweep or
a PVT/control/address qualification. The wrapper still has no reset, no
captured write-data path, and no attached physical bitcell row. The
[dedicated address report](row_decoder_address_capture_20261009.md) and
[integrated manifest](../sims/row_decoder/results/captured_row_address_interface_tt_20261009/manifest.json)
contain the detailed evidence. No extraction was performed for this run.

## Follow-up: valid-write control with captured address — 2026-10-10

Added a second paired TT case with valid-write control `010` and address
transition `3→0`. It uses the current transistor-level PCLK/PRECH source,
captured row-address and access-control registers, decoder/WL PEX, four
wordline-driver PEX instances, the pinned read-only Danilo precharge PEX, and
the existing lumped bitline residual. The test applies the input address
500 ps before capture and changes the live address during the high phase.
This is a write-control/row-selection screen; no physical bitcell data is
written or read back.

The actual and Liberty-reference modes each passed **175/175 checks**, for
350/350 checks total, with no simulation errors or screen rejections. The
actual captured `VALID_ACCESS_Q` remained asserted for write vector `010`, and
`A0_Q/A1_Q` captured row 0 and held it after the live inputs changed. No WL was
asserted while PRECH was active. The measured phase comparisons are:

| Measurement | Captured transistor-level path | Liberty-timed reference | Difference |
|---|---:|---:|---:|
| CLK capture edge to PCLK 50% rise | 1,828.672 ps | 1,827.548 ps | +1.124 ps |
| PRECH 75% release to PCLK 50% rise | 391.907 ps | 391.954 ps | −0.048 ps |
| PCLK 50% fall to PRECH 75% assertion | 2,253.999 ps | 2,254.000 ps | −0.001 ps |
| Valid-access Q 50% clock-to-Q rise | 184.010 ps | 307.041 ps | −123.031 ps |

The captured qualifier reaches −72.195 mV and 1.947143 V in the actual run.
The bench has no accepted rail-excursion criterion; this remains an electrical
and model review item even though the sampled logic checks pass. Both ngspice
logs report `No compatibility mode selected!`, with no missing OSDI library
or fatal model error. No extraction was performed.

The [run manifest](../sims/row_decoder/results/captured_address_write_tt_20261010/manifest.json),
[350 paired checks](../sims/row_decoder/results/captured_address_write_tt_20261010/checks.csv),
[summary metrics](../sims/row_decoder/results/captured_address_write_tt_20261010/summary.csv),
and [matched timing comparison](../sims/row_decoder/results/captured_address_write_tt_20261010/matched_comparison.csv)
preserve the evidence and provenance.

## Follow-up: valid-read selection of all four rows at TT — 2026-10-10

Two additional runs select read targets 1 and 2 from old address 0, and a
third selects target 0 from old address 0. Together with the earlier read
case targeting row 3, valid-read control `001` now selects each of the four
decoder outputs in a representative TT case at 1.80 V/27 °C. The three new
paired cases pass **1,050/1,050 checks** (175 actual plus 175 reference
checks per case), with no simulation errors or screen rejections. Across all
four read targets, the paired count is **1,400/1,400**. The earlier valid-write
control `010`, address `3→0`, adds one more representative case, for
**1,750/1,750 checks** across the five valid cases now recorded here.

For the three new cases, the actual PCLK rising edge occurs 1,828.677–1,828.678
ps after capture, 1.111–1.117 ps later than the Liberty-timed reference. The
actual `VALID_ACCESS_Q` spans −72.202 mV to 1.947177 V. There is no accepted
rail-excursion criterion, so the voltage/model review remains open despite
the sampled logic checks passing. Logs report `No compatibility mode
selected!`; none reports a missing OSDI library or fatal model error.

This covers target selection from old address 0, including the `0→0` hold
case; it is **not** the full set of 16 ordered old/new row-address pairs. The
write control still has only the `3→0` case, and none of these tests writes
data into or reads back a physical bitcell. The [row 1/2 manifest](../sims/row_decoder/results/captured_address_read_rows1_2_tt_20261010/manifest.json),
[row 1/2 checks](../sims/row_decoder/results/captured_address_read_rows1_2_tt_20261010/checks.csv),
[row 0 manifest](../sims/row_decoder/results/captured_address_read_row0_tt_20261010/manifest.json),
and [row 0 checks](../sims/row_decoder/results/captured_address_read_row0_tt_20261010/checks.csv)
preserve both runs.

## Simulated path and setup

The actual case freshly netlists `captured_pclk_phase_source.sch`, which
connects the SKY130 FD SC HD standard-cell qualifier to the existing
transistor-level `pclk_phase_source.sch`. The phase equations and selected
24/60/80-stage inverter taps are unchanged. The simulations use the native
SKY130 PM3 models for the phase logic, qualifier standard cells, decoder,
wordline drivers, and precharge devices.

Downstream loading consists of the current row-decoder R-C PEX, four
wordline-driver R-C PEX instances at 102.873935496 fF per row, eight pinned
read-only copies of Danilo's `precharge_w2p52_flat` PEX, and 583.992055 fF of
lumped bitline residual per side. The effective bitline target is 597.056241
fF. This is not a distributed bitline or a physical 6T read/write path.

Controls start disabled at `111`; a priming clock edge captures an invalid
value before the test applies the selected control vector and captures it on
the next rising edge at 15 ns. The controls then change to the opposite
validity class during the high phase to check that the captured Q holds.
The transient maximum step is 5 ps. Experimental 250 ps PRECH-release and
1,800 ps WL-turnoff guards are used by the testbench; neither is a requirement
from the project specification.

## 2026-10-11 UTC: initial three-profile matrix with a short evaluation window

Ran both valid operations (`001` read and `010` write) from old row 0 to all
four row targets in TT, SS, and FF. Each logical case has an actual
transistor-level path and a matched Liberty-timed reference, for 24 paired
cases and 48 completed ngspice runs. The current decoder and four WL-driver
PEX instances, the pinned read-only Danilo precharge PEX, and the same lumped
bitline residual were used throughout. No new extraction was performed.

The final manifest is `complete=true`, with 48/48 simulations completed and
zero simulation errors. Its overall `status` is **REVIEW_REQUIRED**: 16 of the
48 actual/reference results are rejected by the defined experimental screens.
The combined check file has 8,400 rows: 8,352 PASS and 48 FAIL.

| Profile | Actual path | Liberty reference | Notes |
|---|---:|---:|---|
| TT | 8/8 PASS | 8/8 PASS | 16 paired results passed |
| SS | 0/8 PASS | 0/8 PASS | All 16 results are `REJECTED_SCREEN` |
| FF | 8/8 PASS | 8/8 PASS | 16 paired results passed |

The 48 SS check failures split into two findings:

1. **Loaded WL response: 32 failures.** The selected WL does not meet the
   bench's 0.9·VDD end-level and settled-minimum screens in either path. Across
   the SS cases, the failing end-level measurements are 1.43783–1.44059 V and
   the settled minima are 1.37357–1.37642 V; the experimental floor is 1.458 V
   at the 1.62 V supply. This is an observed loaded-path/timing-screen failure,
   not by itself proof of a project-specification violation: the specification
   does not define this waveform's PCLK high time or a WL settling deadline.
2. **Liberty-reference sample timing: 16 failures.** The reference Q is sampled
   700 ps after capture. At SS, its Liberty clock-to-Q 50% crossing is about
   677.1 ps, leaving only about 23 ps before the sample. The output is then
   1.045 V, below the bench's 1.458 V high threshold. Eight failures are
   `VALID_ACCESS_Q_capture` samples and eight are high-valued A0_Q/A1_Q
   samples. This is a sampling-point limitation in the reference monitor; the
   current measurement does not establish that the reference register has
   settled to a valid high level at the chosen sample.

The actual SS `VALID_ACCESS_Q` also reaches −0.11279 V and 1.81175 V at the
1.62 V supply. The bench defines no accepted rail-excursion limit, so these
measured excursions remain an electrical/model review item; they are not
accepted as reliable operation based on the logic samples alone.

A retained SS row-3 waveform diagnostic resolves the loaded WL timing. With
1.62 V, −40 °C and 102.873935496 fF per row, actual PCLK crosses falling 90% at
22.184933 ns and WL3 reaches rising 90% at 22.283966 ns, a 99.033 ps delay.
The Liberty-reference path measures 22.184824 ns and 22.278566 ns,
respectively (93.742 ps). At the actual PCLK falling 50% crossing, WL3 is only
1.45059 V, slightly below the 1.458 V screen. The close actual/reference
waveforms indicate that the slow loaded evaluation path is present in both
models; they do not make the screen pass or define an accepted timing limit.
See the [waveform plot](../sims/row_decoder/results/captured_phase_interface_ss_waveform_diag_20261010/ss_row3_pclk_wl3_timing.png),
[selected waveform samples](../sims/row_decoder/results/captured_phase_interface_ss_waveform_diag_20261010/ss_row3_selected_waveforms.csv),
and [crossing summary](../sims/row_decoder/results/captured_phase_interface_ss_waveform_diag_20261010/ss_row3_wl_timing_summary.json).
The PNG/SVG can be regenerated from the retained CSV without the removed RAW
files using
`./tools/sram-eda python3 sims/row_decoder/plot_captured_phase_ss_diagnostic.py --case-dir sims/row_decoder/results/captured_phase_interface_ss_waveform_diag_20261010/cases/slow_ctl001_a0_to_3_p2100 --waveform-csv sims/row_decoder/results/captured_phase_interface_ss_waveform_diag_20261010/ss_row3_selected_waveforms.csv --output-dir sims/row_decoder/results/captured_phase_interface_ss_waveform_diag_20261010`.

The initial full-matrix attempt exposed a runner bug: measured phase edges
were written into a shared schedule and then reused for the Liberty-reference
simulation. The runner now creates a mode-local schedule copy, preserving the
external `PHASE_CLK` reference in both modes. The aborted attempt is not used
as evidence; all counts above come from the complete run with the corrected
runner.

The PCLK capture-to-rise difference between actual and reference was
1.109–1.117 ps in TT, 2.588–2.595 ps in SS, and 0.731–0.743 ps in FF. The
experimental 250 ps PRECH-release screen passed in all profiles; it is not a
specification limit. All 48 logs completed without missing OSDI-library or
fatal model-resolution errors, though they print `No compatibility mode
selected!`.

This run is retained as the initial diagnostic. It is superseded for the
selected-row valid matrix by the retest below, which uses a longer experimental
window and later settled-Q sampling. The initial results remain useful evidence
of why the earlier SS screens rejected the candidate settings.

The [manifest](../sims/row_decoder/results/captured_phase_interface_valid_3profile/manifest.json),
[summary](../sims/row_decoder/results/captured_phase_interface_valid_3profile/summary.csv),
[matched timing comparison](../sims/row_decoder/results/captured_phase_interface_valid_3profile/matched_comparison.csv),
and [per-check CSV](../sims/row_decoder/results/captured_phase_interface_valid_3profile/checks.csv)
contain the matrix evidence. Reproduce it with:

```bash
./tools/sram-eda python3 sims/row_decoder/run_captured_phase_interface.py \
  --profiles tt slow fast --control-vectors 001 010 \
  --transitions 0:0 0:1 0:2 0:3 --transitions-per-vector \
  --phase-ps 2100 --clk-fall-ps 22000 \
  --settling-allowance-ns 3.4 --q-sample-ps 700 \
  --hold-challenge-ps 800 --wl-cap-ff 102.873935496 --step-ps 5 \
  --output-dir sims/row_decoder/results/captured_phase_interface_valid_3profile
```

## 2026-10-11 UTC: retest with later Q sampling and a longer candidate window

Reran the same 24 logical cases after changing the experimental schedule and
reference monitor: `phase_ps=2100`, external `CLK` falling edge at 22.50 ns,
3.8 ns settling allowance, captured-Q sample at +900 ps, and live-input hold
challenge at +1100 ps. The selected row load remains 102.873935496 fF and the
transient step remains 5 ps. These are test settings only; the specification
does not approve this clock period, PCLK phase, or settling deadline.

All 48 actual/reference ngspice runs completed with zero simulation errors.
The manifest reports `complete=true`, `status=PASS`, and no screen rejections.
All **8,400/8,400 checks pass**:

| Profile | Actual path | Liberty reference | Selected-WL result |
|---|---:|---:|---|
| TT | 8/8 PASS | 8/8 PASS | All selected WL checks pass |
| SS | 8/8 PASS | 8/8 PASS | Minimum end level 1.52050 V; minimum settled level 1.46393 V |
| FF | 8/8 PASS | 8/8 PASS | All selected WL checks pass |

At SS the experimental 0.9·VDD floor is 1.458 V. The minimum selected-WL
settled level is 5.93 mV above that screen, so the measured margin is narrow.
This passes the present testbench criterion at the tested load and schedule;
it does not establish an approved SRAM timing limit or adequate design margin.
The later +900 ps Q sample avoids the earlier premature Liberty-reference
sample, and the +1100 ps live-input change still exercises capture/hold.

The reference is a PWL shaped from `dfxtp_1` Liberty timing arcs, not a
transistor-level flip-flop in the same supply condition: the slow Liberty
table is characterized at 1.60 V while the native-PM3 slow test deck uses
1.62 V; the fast Liberty table uses 1.65 V while its native-PM3 deck uses
1.80 V. TT uses 1.80 V in both. Interpret the comparison as a timing reference
for the captured-Q interface, not a same-voltage validation of the standard
cell.

The actual captured control/address path continues to show rail excursions:
`VALID_ACCESS_Q` ranges from −72.20 mV to 1.94718 V in TT, −112.79 mV to
1.81175 V in SS, and −36.93 mV to 1.90417 V in FF. The bench has no accepted
excursion criterion. Passing sampled logic checks does not close electrical,
model-domain, or reliability review. The run used the native SKY130 PM3 models;
all 48 ngspice logs completed without missing OSDI libraries or fatal model
errors and include the informational `No compatibility mode selected!`
message.

The simulation used the current decoder and four WL-driver R-C PEX instances,
the pinned read-only Danilo precharge PEX, and the existing lumped bitline
residual. No new extraction was performed. It covers valid read `001` and
valid write `010`, each from old address 0 to targets 0–3. The write cases
select rows; no physical bitcell data is written or read back. The matrix is
not the complete set of 16 ordered address pairs and does not cover invalid or
idle controls, startup, or integrated setup/hold.

Evidence: [passing manifest](../sims/row_decoder/results/captured_phase_interface_valid_3profile_fall22500_settle3800_q900_20261011/manifest.json),
[summary](../sims/row_decoder/results/captured_phase_interface_valid_3profile_fall22500_settle3800_q900_20261011/summary.csv),
[matched comparison](../sims/row_decoder/results/captured_phase_interface_valid_3profile_fall22500_settle3800_q900_20261011/matched_comparison.csv),
[8,400 per-check results](../sims/row_decoder/results/captured_phase_interface_valid_3profile_fall22500_settle3800_q900_20261011/checks.csv),
and [representative TT waveforms](../sims/row_decoder/results/captured_phase_interface_valid_3profile_fall22500_settle3800_q900_20261011/captured_phase_vs_liberty_tt_read_a0_to_3.png).
Reproduce with:

```bash
./tools/sram-eda python3 sims/row_decoder/run_captured_phase_interface.py \
  --profiles tt slow fast --control-vectors 001 010 \
  --transitions 0:0 0:1 0:2 0:3 --transitions-per-vector \
  --phase-ps 2100 --clk-fall-ps 22500 \
  --settling-allowance-ns 3.8 --q-sample-ps 900 \
  --hold-challenge-ps 1100 --wl-cap-ff 102.873935496 \
  --step-ps 5 \
  --output-dir sims/row_decoder/results/captured_phase_interface_valid_3profile_fall22500_settle3800_q900_20261011
```

## Limits and review items

- The passing matrix covers valid-read `001` and valid-write `010` from old
  address 0 to each of four rows in TT/SS/FF, under the experimental schedule
  recorded above. Agree timing and margin criteria before treating it as a
  qualified operating point or using it to claim frequency closure.
- The captured Q reaches −72.2 mV and 1.9471 V in the valid run, and −7.2 mV
  and 1.9471 V in the invalid run. This bench has no rail-excursion acceptance
  criterion; the overshoot remains for electrical/model review. Passing the
  sampled logic and timing checks does not close that review.
- In the passing matrix, actual `VALID_ACCESS_Q` ranges from −112.79 mV to
  1.81175 V at the SS supply. This bench has no accepted rail-excursion limit.
- The phase-source chain has no layout, DRC, LVS, or PEX. The test does not
  establish metastability behavior, startup before a valid clock edge, clock
  frequency, a complete row read/write/readback, or reliability/signoff.
- The representative and matrix ngspice logs print `No compatibility mode
  selected!`. The 48 runs in the passing matrix report no missing OSDI
  libraries or fatal model-resolution errors. This informational notice stays
  part of the model-environment record.
- Danilo's precharge PEX is consumed read-only and pinned to commit `5dc00fe`
  with SHA-256
  `cf0fa457b4ab84a1d19e6202541b6a43149b575e492a108e36d0de62489cc423`.
  This test does not replace or revise the shared precharge source.

## Reproduction

Run the default representative valid-read case:

```bash
./tools/sram-eda python3 sims/row_decoder/run_captured_phase_interface.py \
  --output-dir sims/row_decoder/results/captured_phase_interface_tt_read_repro
```

Run the representative invalid-vector case:

```bash
./tools/sram-eda python3 sims/row_decoder/run_captured_phase_interface.py \
  --output-dir sims/row_decoder/results/captured_phase_interface_invalid_repro \
  --profiles tt --control-vectors 000 --transitions 0:3
```

Both result directories contain manifests, exact simulation input netlists,
case JSON, checks, and ngspice logs. The valid-read directory also contains
representative waveform CSVs and the comparison plot. Large transient RAW
files are not retained by default; use `--keep-raw` only when detailed
waveform inspection is needed.

## Remaining matrix and next steps

The initial review items that rejected SS in the short-window run were
resolved for this testbench run: the selected-WL screens pass at the longer
candidate window, and the Q monitor samples after settling. The broader
qualification is still open. Next, agree an acceptable PCLK/system timing and
margin with the project team, then sweep around the passing candidate to
measure margin rather than adopting this point as a timing limit. After that,
run the invalid/idle control vectors and the 12 remaining ordered address
pairs using the agreed schedule. These screens still do not replace physical
bitcell row read/write/readback, startup, or integrated setup/hold tests.

The initial short-window matrix command is retained for historical reproduction
(24 paired cases, 48 actual/reference runs; superseded by the passing retest):

```bash
./tools/sram-eda python3 sims/row_decoder/run_captured_phase_interface.py \
  --profiles tt slow fast --control-vectors 001 010 \
  --transitions 0:0 0:1 0:2 0:3 --transitions-per-vector \
  --output-dir sims/row_decoder/results/captured_phase_interface_valid_3profile
```

Next matrix: cover all six invalid/idle control vectors with the `0→3`
challenge in TT/SS/FF (18 paired cases, 36 actual/reference ngspice runs),
after the project accepts the timing condition to use:

```bash
./tools/sram-eda python3 sims/row_decoder/run_captured_phase_interface.py \
  --profiles tt slow fast --control-vectors 000 011 100 101 110 111 \
  --transitions 0:3 --phase-ps 2100 --clk-fall-ps 22500 \
  --settling-allowance-ns 3.8 --q-sample-ps 900 \
  --hold-challenge-ps 1100 --wl-cap-ff 102.873935496 --step-ps 5 \
  --output-dir sims/row_decoder/results/captured_phase_interface_invalid_3profile
```

Then cover the 12 ordered address pairs whose old address is 1, 2 or 3. The
passing valid screen already covers the four pairs from old address 0.
Together, these stages cover all 16 ordered old/new pairs for both valid
operations and all three profiles. These row-selection tests do not substitute
for a physical bitcell read/write/readback path.

```bash
./tools/sram-eda python3 sims/row_decoder/run_captured_phase_interface.py \
  --profiles tt slow fast --control-vectors 001 010 \
  --transitions 1:0 1:1 1:2 1:3 2:0 2:1 2:2 2:3 3:0 3:1 3:2 3:3 \
  --transitions-per-vector \
  --output-dir sims/row_decoder/results/captured_phase_interface_valid_remaining_ordered_3profile
```

This remaining valid-operation matrix contains 72 paired cases (144 actual/
reference ngspice runs); it is intentionally a separate high-compute step.

The invalid and remaining ordered-address commands are suspended until the
review above closes. The simulations do not sweep setup/hold skew, phase
placement, clock period, or supply/temperature within a model profile; those
need separate scoped runs after the acceptance conditions are agreed.
