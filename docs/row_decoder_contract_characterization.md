# Dynamic decoder: address contract, phase limits and robustness study

Status: pre-layout characterization in progress. The architecture and nine-pin
interface remain the specified dynamic 2-to-4 NAND decoder. Experimental screens
below are not a macro operating specification, external setup time, Fmax,
foundry reliability clearance, or decoder DRC/LVS result.

On 2026-10-07 Leonardo explicitly selected **electrical margin and robustness**
as the priority for choosing this decoder's sizing. Delay, supply energy and
area remain reported costs. This scoped choice does not silently finalize the
global macro tradeoff or the nominal characterization temperature still open
in the technical specification.

## What the new executor checks

`sims/row_decoder/run_row_decoder_contract.py` freshly netlists the current
Xschem sizing bench and audits its hierarchy. Simulation-only PWL and dimension
overrides are applied to disposable decks. Every case primes the old address
through an evaluation, precharges, then tests the new address. Four unchanged
WL buffers drive independent estimated 17.4 fF loads, or the declared 50 fF
stress load. No bitcell, WL-driver, write-driver or other owner's source is edited.

Both evaluations, intervening precharge and final recovery are checked.
Unselected DEC/WL outputs must remain below 10% VDD throughout evaluation,
including the first nanosecond; selected outputs must reach 90% VDD and remain
there. A separate experimental 1 ns settling allowance is retained. Full
waveform checks distinguish a late selected transition from a spurious row,
residual precharge pulse or loss of a previously established high level.

The original 41 MOS instances (25 decoder, 16 in four WL buffers) have signed external
VGS/VGD/VDS/VBS extrema recorded. The 1.95 V upper/magnitude diagnostics do not
establish the full signed model domain. A logical PASS can still be rejected
by these voltage checks. Missing/truncated/nonfinite waveforms are errors.

Each completed case is atomically checkpointed before its temporary raw file
can be removed. `--resume` requires the same declared cases and input netlist.
Existing complete raw files are reused only when their deck matches exactly.
An incomplete campaign has `complete=false`, an error list and exit code 2;
the summarizer refuses to treat it as a complete matrix.

## B6 address history and load experiment

The archived [history campaign](../sims/row_decoder/results/b6_contract_history/summary.csv)
contains all 16 ordered old/new pairs, including four repeats, and both signs
of 100 ps A0/A1 skew for the four two-bit transitions. The latest changing
input reaches its final value 2 ns before PCLK's 50% rising crossing.
Each of three profiles is tested at 17.4 and 50 fF, giving 144 cases.

| Profile | Experimental condition | Largest WL 90% delay, 17.4 fF | At 50 fF |
|---|---|---:|---:|
| TT | 1.8 V, 27 C | 491.37 ps | 1048.19 ps |
| Slow | SS, 1.62 V, -40 C | 730.75 ps | 1577.16 ps |
| Fast | FF, 1.8 V, 125 C | 423.94 ps | 895.15 ps |

All cases reach the correct final row without a spurious selected row. All
72 cases at the estimated 17.4 fF load pass the declared screens. At 50 fF,
24 FF cases pass; 24 TT and 24 SS cases fail the experimental 1 ns selected-WL
settling allowance. Those 48 failures are retained, not reclassified as passes
because the final output eventually becomes correct. These measurements used
5 ps maximum steps and the original charge truncation default; the finer
voltage review below supersedes any inference of final B6 robustness.

## B6 address arrival and phase experiment

The [810-case suite](../sims/row_decoder/results/b6_contract_suite/summary.csv)
and its [manifest](../sims/row_decoder/results/b6_contract_suite/manifest.json)
are complete. They contain 252 arrival cases, 36 deliberately invalid
evaluation-time address changes, 168 low-phase and 168 high-phase points,
36 retention points, 48 asymmetric-clock points, 60 address-slew points and
42 calibrated charge-withdrawal points. Rejected boundary and perturbation
points are characterization results, not tool failures.

Address lead is the time from the latest changed input reaching its final
value to PCLK crossing 50% on the next rising edge. It is **not** setup to the
external CLK capture register. With 50 ps edges and 17.4 fF, all 12 nonrepeat
transitions pass the combined logic and voltage diagnostics at 100, 250 and
1000 ps lead in the tested TT/slow/fast profiles. A 50 ps lead does not pass
every TT/FF voltage diagnostic despite all sampled logic states passing.
This agrees with the specification's requirement to allow captured address
and complements to settle before decoder assertion.

| B6 sampled phase grid | TT | Slow profile | Fast profile |
|---|---:|---:|---:|
| Shortest tested low phase passing all four repeated addresses | 0.50 ns | 0.75 ns | 0.40 ns |
| Shortest tested high phase passing all four repeated addresses | 0.60 ns | 1.00 ns | 0.50 ns |

Phase lengths are between PCLK 50% crossings; end-of-evaluation checks finish
at the beginning of its falling ramp. These are sampled bounds under repeated
addresses, not exact minima or a safe macro frequency. Both phase constraints,
input-register delay, bitcell access, sense and output-capture timing matter.
All 36 deliberate address changes during evaluation produce the expected
wrong-row evidence: a discharged dynamic node cannot recover until precharge.

Evaluation holds of 10, 100 and 1000 ns pass their defined screens for all
four rows in the three profiles. The 1000 ns cases use a 25 ps maximum step;
the shorter cases use 5 ps. This is a finite tested retention interval, not
unlimited clock-stop tolerance. Asymmetric 25/250, 250/25, 50/1000 and
1000/50 ps clock edges pass the coarse declared screens. A 25 ps address edge
exposes additional voltage failures in three TT/FF cases.

## Numerical failure and finer voltage finding

Some PWL breakpoint cases abort with `Timestep too small` while ngspice's
`.control quit 0` still returns zero. The executor rejects the error log and
truncated raw file. Smaller maximum steps, a different integrator, more Newton
iterations and temporary diagnostic shunts did not resolve the reference
case. The successful adopted retry sets `MINBREAK=1 fs`; this controls transient
breakpoint handling without adding a circuit element or relaxing voltage checks.
The ngspice [transient source](https://raw.githubusercontent.com/ngspice/ngspice/master/src/spicelib/analysis/dctran.c)
shows the breakpoint-spacing handling and its default initialization.

Tightening `CHGTOL` to 1e-18 C independently completes the reference case and
resolves a previously undersampled address-inverter peak. Evidence is archived
in [the numerical comparison](../sims/row_decoder/results/b6_numeric_breakpoints/summary.csv),
including the failing deck/log and both successful settings.

| Same B6 circuit, TT, simultaneous 00 to 11, 250/25 ps clock | M2 maximum VDS |
|---|---:|
| Gear, 5 ps maximum step, MINBREAK=1 fs, default charge tolerance | 1.946750 V |
| Gear, 5 ps maximum step, CHGTOL=1e-18 C | 1.950579 V |

The tighter maximum occurs at 17.97445 ns during the simultaneous 50 ps
address changes, compared with 17.97250 ns in the coarser record. Thus the
previous roughly 3 mV B6 headroom is not sufficient evidence to freeze it.
The earlier 54-condition report remains correct for its archived schedule;
it did not establish every address history under this tighter charge criterion.
New robustness comparisons use Gear, maximum step 1 ps, MINBREAK=1 fs and
CHGTOL=1e-18 C consistently.

## Static transfer and charge sensitivity

[24 DC transfer curves](../sims/row_decoder/results/b6_inverter_dc/summary.csv)
measure the address, decoder-output and both buffer-stage inverters under
TT/slow/fast/SS-cold profiles and additional SF/FS diagnostics. VOUT=VIN is
interpolated on a 1 mV input grid. The decoder-output trip is 0.83601 V at
TT/1.8 V/27 C and 0.73735 V at SS/1.62 V/-40 C. These are actual transfer
references, not bitcell SNM or dynamic noise qualification.

Charge tests withdraw Q from unselected N1 or N3 using a 120 ps trapezoid:
10 ps ramps, 100 ps plateau, amplitude Q/110 ps. In the coarse B6 suite,
0, 0.25, 0.5, 1 and 2 fC pass all six node/profile combinations; 4 and 8 fC
produce false-row predictions. Some 8 fC waveforms also exceed the magnitude
screen. The tested transition between 2 and 4 fC is an experimental bracket
for this injection waveform, not an approved system noise budget or silicon
failure rating. A selected row remains asserted until the next precharge.

## Family comparison and selection status

The [38-size TT sweep](../sims/row_decoder/results/contract_tables/sizing_candidates.csv)
holds other families at B6, not the older B0. Each candidate exercises four
two-bit histories. All 152 runs pass logic; only 21 candidates pass every
coarse voltage diagnostic. The nominal comparisons include decoder + four
buffers' VDD energy and sum(W*L) channel-area proxy, not physical area. Ideal
clock/address source energies are reported separately as delivered energy;
they are not actual upstream-driver losses.

The first shortlist tests footer W=3, precharge W=0.5, output Wn/Wp=0.42/0.84
and output Wn/Wp=0.75/0.75 at 80 corner/clock cases. Every shortlisted candidate
fails at least one voltage or excursion check; none is adopted from its TT
performance alone. Larger footers also worsen negative DEC excursions in
some SS cases. Therefore robustness refinement includes address length/ratio,
footer/output interactions and evaluation-stack capacitance with the tighter
numeric settings. No candidate is labeled final merely because its logic passes.

## Expanded interactions: measured screening results

The refined [132-case study](../sims/row_decoder/results/decoder_robustness_refinement/summary.csv)
uses simultaneous two-bit transitions in TT, FF/1.8 V/125 C and SS/1.8 V/-40 C.
All runs pass logic, but 35 exceed the magnitude screen. B6 reaches **1.974458 V**
at M2 VDS in SS-cold. Increasing address channel length or transistor width
alone does not close the issue. Footer W=6 plus output Wp/Wn=2/2 passes its
12 cases with only **0.184865 mV** headroom, which does not justify a robustness
freeze or qualify untested stimulus conditions.

The [80-case stack study](../sims/row_decoder/results/decoder_stack_robustness/summary.csv)
adds TT, SS/1.62 V/-40 C, FF-hot and SS-cold profiles. It retains six logical
failures and 29 magnitude findings. Enlarging stack gates changes both address
loading and dynamic-node coupling; it is not a universally beneficial correction.

The [96-case capacitance study](../sims/row_decoder/results/decoder_capacitance_robustness/summary.csv)
passes all logical checks but has two magnitude findings. Four footer-W6,
output-W3/W4 combinations pass their 16-case sets, yet their maximum terminal
magnitude is still 1.949779--1.949836 V. The smallest headroom is about 0.16 mV.
Increasing output-node capacitance suppresses dynamic-row feedthrough while
leaving the address-inverter peak nearly unchanged. These points remain
experimental candidates, not finalized schematic dimensions.

Additional address-ratio, joint-stack and balanced-footer studies retain
failed cases in their own directories. A buffered-address diagnostic adds
four MOS to regenerate the true address literals after the existing complement
inverters; it is explicitly a disposable 29-MOS candidate with all 45 MOS
terminals (including the four unchanged WL drivers) measured. It introduces
no clock, state machine or external pin. Its added input delay, coupling,
energy and area must be measured before considering a schematic adoption.

![Measured contract and robustness comparisons](assets/row_decoder_contract.png)

The [standalone PDF](assets/row_decoder_contract.pdf) and figure provenance
accompany the exported chart. Its green bars mean only that a particular
candidate's declared case set passes. Differing case sets are not a common
qualification or a final ranking.

## Reproduction and remaining work

Run from the checkout through `./tools/sram-eda`. Use new output directories
for independent comparisons. For an interrupted run, reuse its arguments and
add `--resume`; preserve the same cases/netlist. Each manifest includes input,
script/helper and source hashes, explicit conditions, tool versions and any
numerical retry settings. Older datasets fingerprint the top-level model library only. The current
executor fingerprints its recursive `.include` closure (18 files in this
installation), helpers and tool versions before reusing a checkpoint. Legal
qualification cases now return nonzero on a voltage-only failure as well as
a logic failure; older tables with zero tool return codes still require
inspection of the voltage columns.
Exact executed script snapshots accompany historical tables.

```bash
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_contract.py \
  --campaign history --output-dir /tmp/decoder-history-review
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_contract.py \
  --campaign suite --output-dir /tmp/decoder-contract-review
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_contract.py \
  --campaign sizing --profiles tt --output-dir /tmp/decoder-family-review
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_trip.py \
  --netlist sims/row_decoder/results/b6_contract_history/input_netlist.spice \
  --output-dir /tmp/decoder-trip-review
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_contract.py \
  --campaign selected --case-file sims/row_decoder/contract_robustness_cases.json \
  --output-dir /tmp/decoder-robustness-review
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_contract.py \
  --campaign selected --case-file sims/row_decoder/contract_stack_robustness_cases.json \
  --output-dir /tmp/decoder-stack-review
```

Remaining closure includes a retained candidate's full experimental PVT/edge
matrix, address histories under refined numerical settings, margins after
parasitic extraction, and real captured-address/PCLK driver timing. The leaf
contains no CSb/OEb/WEb qualification; idle/disabled/invalid row suppression
requires the integration control path. Decoder layout, DRC and LVS have not
been executed by this characterization study.
