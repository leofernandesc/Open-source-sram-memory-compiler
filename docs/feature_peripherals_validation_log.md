# Person 3 peripheral validation log

- Date: 2026-10-08
- Branch: `feature/peripherals`

Current decoder status: the compact layout from `d20f509` has routed/flat DRC
0/0, unique LVS, and current PEX with 762 R / 389 C across all 22 resistance
networks. The matched 13-case schematic/PEX matrix passes at both 5 ps and
1 ps. The complete 16-pair TT matrix also passes 16/16 schematic and PEX cases
at both steps; see the full address-pair entry below.
A full FF/1.8 V/125 °C matrix now passes all 16 ordered address pairs in both
baseline and PEX at 5 ps and 1 ps. The baseline terminal screen remains close
to its 1.95 V numerical threshold, and ngspice reports FF model-parameter
warnings. See the
[compact-layout extraction entry](#2026-10-08-compact-decoder-r-c-extraction-and-electrical-checks)
and [full FF address-pair entry](#2026-10-08-full-16-pair-ff-hot-decoder-matrix)
for measurements and limits. The 7ad0348 PEX and its matrix are historical for
the previous geometry.

The [HTML status presentation](person3_phase1_status.html) summarizes the
Person 3 work, current evidence, and remaining Phase 1 tasks.

This log records local tests run on the current wordline-driver and write-driver
schematics and layouts. Imported results in
[`peripheral_driver_validation.md`](peripheral_driver_validation.md) remain
historical unless a local rerun is explicitly recorded here.

## Environment

The project launcher in [`tools/sram-eda`](../tools/sram-eda) runs commands in
the existing `sram-xschem` container, sets `PDK=sky130A` and `PDK_ROOT=/opt/pdks`,
and adds the versioned `/opt` tool directories to `PATH`. The environment check
passed for Xschem 3.4.6, ngspice 44.2, Magic 8.3.589, Netgen 1.5.293, Icarus
Verilog, GTKWave, Python, gdstk, and the SKY130A model/technology files.
Reproduction instructions are in [`tools/ENVIRONMENT.md`](../tools/ENVIRONMENT.md).

The earlier leaf-driver checks above recorded
`isaiassh/unic-cass-tools:1.0.7`. The compact-decoder run below used the
verified `1.1.0` image and the same SKY130A PDK revision.

## Wordline driver

The tested schematic is the two-stage non-inverting CMOS buffer in
[`wl_driver.sch`](../cells/wordline_driver/wl_driver.sch), with stage widths
0.42 µm and 0.84 µm, and channel length 0.15 µm. The 17.4 fF load is the
pre-layout full-row estimate from [`cwl_pre_layout_estimate.md`](cwl_pre_layout_estimate.md).
The 50 fF point is a stress load, not the estimated physical row capacitance.

The original transient smoke runner netlisted the current Xschem schematic and
checked its pin set and device list, but did not check that the testbench's
positional instance order matched the schematic's declared terminal order. A
2026-10-09 audit found that mismatch; the original schematic rows in the table
below are retained for history but are superseded as evidence. The PEX rows
used the correct PEX pin order and remain valid. See the corrected
requalification entry below.

The runner applies these output-level criteria:

- `WL` before the input transition is at or below 10% of VDD;
- `WL` at the high sample is at or above 90% of VDD;
- `WL` at the low sample is at or below 10% of VDD.

The delay is measured between the input and output 50% crossings. The schematic
screen covered TT/SS/FF, 1.62/1.80 V, −40/27/125 °C, and both loads: 36/36
cases passed. The PEX screen covered the same matrix using the existing
`layout/wl_driver/pex/wl_driver_pex.spice`: 36/36 cases passed.

| Netlist | Load | Cases | Worst 50% delay | Minimum high | Maximum low |
|---|---:|---:|---|---|---|
| Schematic | 17.4 fF | 18/18 PASS | 0.29133 ns, SS/1.62 V/−40 °C | 1.619995 V, SS/1.62 V/−40 °C | 0.000144687 V, FF/1.80 V/125 °C |
| Schematic | 50 fF | 18/18 PASS | 0.66536 ns, SS/1.62 V/−40 °C | 1.57306 V, SS/1.62 V/−40 °C | 0.00898481 V, SS/1.62 V/125 °C |
| Existing leaf PEX | 17.4 fF | 18/18 PASS | 0.38625 ns, SS/1.62 V/−40 °C | 1.619899 V, SS/1.62 V/−40 °C | 0.000151427 V, FF/1.80 V/125 °C |
| Existing leaf PEX | 50 fF | 18/18 PASS | 0.75951 ns, SS/1.62 V/−40 °C | 1.541609 V, SS/1.62 V/−40 °C | 0.05077535 V, SS/1.62 V/125 °C |

At TT/1.80 V/27 °C, schematic-to-PEX delay was 0.18622 to 0.24933 ns at
17.4 fF, and 0.41541 to 0.47787 ns at 50 fF. These are leaf-level results;
the PEX does not include the complete physical row/interconnect.

### 2026-10-09 pin-order audit and corrected WL-driver requalification

An audit found that the prior smoke runner used the PEX terminal order for the
Xschem schematic. The actual schematic formal order is `VDD WL_IN WL VSS`,
while the PEX order is `VDD VSS WL_IN WL`. Therefore, the previously recorded
schematic smoke matrix is superseded as evidence; the PEX matrix is unaffected.
The runner now constructs the instance according to its subcircuit header and
records both 50%- and 90%-crossing delay. Corrected schematic and existing PEX
matrices each pass 36/36 cases at TT/SS/FF, 1.62/1.80 V, −40/27/125 °C and
17.4/50 fF. The maximum measured eight-bit row load was also screened at
SS/1.62 V/−40 °C with a longer input pulse: schematic and PEX both pass 1/1 at
102.873935496 fF. This is a lumped leaf-load result, not a distributed array
simulation. See the detailed [pin-order and full-row report](wl_driver_pin_order_and_full_row_requalification_20261009.md)
and its reproduction CSVs.

Reproduction commands:

```bash
./tools/sram-eda python3 sims/run_leaf_peripheral_smoke.py \
  --blocks wl_driver --corners tt ss ff \
  --vdd-values 1.62 1.8 --temps-c -40 27 125 \
  --wl-cap-ff 17.4 50 \
  --output sims/wl_driver_smoke_3corner_pvt.csv

./tools/sram-eda python3 sims/run_leaf_peripheral_smoke.py \
  --blocks wl_driver --corners tt ss ff \
  --vdd-values 1.62 1.8 --temps-c -40 27 125 \
  --wl-cap-ff 17.4 50 --pex \
  --output sims/wl_driver_pex_smoke_3corner_pvt.csv
```

## Write driver

The write-driver schematic was netlisted by Xschem and its embedded TT
transient deck was run with ngspice at 1.80 V, 27 °C, and 50 fF per bitline.
Measured outputs were:

| Operation/sample | BL | BLB |
|---|---:|---:|
| Write 0, 3 ns | 0.000000589 V | 1.800297 V |
| Write 1, 12 ns | 1.777446 V | 0.000000583 V |

During the disabled interval, the measured 5-to-8 ns drift was 3.39078 mV on
BL and 1.45900 mV on BLB. The embedded deck has no explicit drift acceptance
limit, so these values are recorded as measurements rather than a separate
automated PASS criterion.

The standalone deck can be rerun from the current schematic with:

```bash
tmpdir="$(./tools/sram-eda mktemp -d /tmp/write-driver-xschem.XXXXXX)"
./tools/sram-eda xschem -x -q -n -o "$tmpdir" \
  /work/cells/write_driver/write_driver.sch
./tools/sram-eda sh -lc "cd '$tmpdir' && ngspice -n -b write_driver.spice"
```

The canonical Xschem schematic was also used for the off-state AC capacitance
sweep, with DATA=0/1, BL/BLB probes, TT/SS/FF, 1.62/1.80 V, and −40/27/125 °C.
All 72 schematic cases and all 72 cases using the existing
`layout/write_driver/pex/write_driver_pex.spice` completed and produced parsed
measurements.

| Netlist | Cases | Ceff range | Maximum point |
|---|---:|---:|---|
| Schematic | 72/72 measured | 1.020331–4.033129 fF | SS/1.62 V/125 °C, DATA=0, BLB |
| Existing leaf PEX | 72/72 measured | 14.112635–26.721160 fF | SS/1.62 V/125 °C, DATA=1, BL |

For this AC runner, `PASS` means ngspice completed and the capacitance was
parsed; the specification does not set a maximum off-state Ceff acceptance
limit. The PEX netlist was used as present and was not regenerated during this
AC sweep. The runner's progress text uses a fixed `/120` denominator for
subsets; the final `PASS=72/72` and CSV row count are authoritative.

Reproduction commands:

```bash
./tools/sram-eda python3 sims/run_write_driver_capacitance.py \
  --corners tt ss ff --vdd-values 1.62 1.8 \
  --temps-c -40 27 125 --data 0 1 \
  --output sims/write_driver_capacitance_local_3corner_pvt.csv

./tools/sram-eda python3 sims/run_write_driver_capacitance.py \
  --corners tt ss ff --vdd-values 1.62 1.8 \
  --temps-c -40 27 125 --data 0 1 --pex \
  --output sims/write_driver_capacitance_local_3corner_pex.csv
```

## Dynamic row decoder

The current specification requires a precharged dynamic 2-to-4 NAND decoder.
The nominal functional screen used the saved hierarchical testbench in
[`tb_row_decoder.sch`](../sims/row_decoder/tb_row_decoder.sch), SKY130A TT,
1.80 V, and 27 °C. Address combinations were sampled during evaluation at
15/35/55/75 ns. Outputs were also sampled during precharge at 5/25/45/65/85 ns.
The screen uses 0.1×VDD as the maximum inactive output and 0.9×VDD as the
minimum selected output; these are test criteria, not numeric thresholds from
the specification.

The decoder wiring was corrected to keep the shared `EVAL_GND` rail distinct
from `VSS`, connect it to the four evaluation branches and the footer drain,
and keep NMOS bodies and output-inverter pull-down sources at `VSS`. The saved
schematic netlisted without structural diagnostics (Xschem return code 0), and
ngspice completed successfully.

The rerun passed all 36 sampled voltage checks: 16 evaluation samples and 20
precharge samples. The four selected outputs measured 1.800 V; unselected
outputs were within about 1 µV of 0 V. During precharge, the largest output was
0.434 µV, below the 0.18 V inactive-output limit. The 0.1×VDD and 0.9×VDD
limits are screening criteria used by the runner, not numeric thresholds from
the specification.

This is nominal TT evidence at 1.80 V and 27 °C. It does not establish PVT
robustness, maximum frequency, or post-layout behavior. No row-decoder layout
is present yet; Magic layout, DRC, extraction, and LVS remain to be completed.

The runner overrides Xschem's symbol search path for this headless invocation
to resolve standard `devices/*`, SKY130A, and local decoder symbols. It does not
edit the saved schematic. Reproduce the screen with:

```bash
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_tt.py
```

The measurements are in
[`row_decoder_tt.csv`](../sims/row_decoder/row_decoder_tt.csv). The runner
returns nonzero while structural Xschem errors or voltage-criterion failures
remain.

## Layout checks

Magic 8.3.589 with the SKY130A technology file ran `drc check` and
`drc count total` on `wl_driver_flat` and `write_driver_flat`; both reported
zero DRC errors.

For example, the read-only wordline check was:

```bash
./tools/sram-eda sh -lc \
  'cd /work/layout/wl_driver && printf "load wl_driver_flat\\ndrc check\\ndrc count total\\nquit -noprompt\\n" | magic -dnull -noconsole -rcfile /opt/pdks/sky130A/libs.tech/magic/sky130A.magicrc'
```

The write-driver check uses the same command with `write_driver` in place of
`wl_driver`.

For LVS, Magic re-extracted each flat layout in a temporary copy under `/tmp`.
Netgen 1.5.293 compared those extracted netlists against normalized Xschem
netlists generated from the current schematics. Both comparisons reported
`Circuits match uniquely`:

- `wl_driver`: 4 devices, 5 nets;
- `write_driver`: 10 devices, 12 nets.

The repository layout files were not rewritten. Netgen printed primitive-model
placeholder/property warnings before reading the SKY130A setup file; the final
comparison result was a unique match for each leaf.

Each LVS comparison used a normalized netlist generated from the current
Xschem source by `extract_leaf` in `sims/run_integrated_column_write.py`; Magic
extraction and Netgen outputs were kept in temporary directories.

## Integration attempt and blocker

A nominal TT integrated-column read was attempted with
`sims/run_integrated_column_read.py`. It stopped before ngspice while Xschem
netlisted `cells/precharge/precharge.sch`. Xschem reported undriven/open nets,
shorts between `BL` and `BLB`/`PRECH`, and disconnected MOS devices. No
integrated-read result CSV was produced. The precharge schematic was left
untouched because it belongs to another block owner. Integrated read and write
qualification remain pending until that leaf can be netlisted correctly.

The attempted conditions were TT, 1.80 V, 27 °C, and stored states 0 and 1;
the command used `/tmp/integrated_column_read_wl_checkpoint_parts` for parts and
`sims/integrated_column_read_wl_checkpoint_tt.csv` as the requested output.

```bash
./tools/sram-eda python3 sims/run_integrated_column_read.py \
  --corners tt --vdd-values 1.8 --temps-c 27 --states 0 1 --workers 1 \
  --parts-dir /tmp/integrated_column_read_wl_checkpoint_parts \
  --output sims/integrated_column_read_wl_checkpoint_tt.csv
```

## Evidence files created in this branch

- `sims/wl_driver_smoke_3corner_pvt.csv`
- `sims/wl_driver_pex_smoke_tt.csv`
- `sims/wl_driver_pex_smoke_3corner_pvt.csv`
- `sims/write_driver_capacitance_local_tt.csv`
- `sims/write_driver_capacitance_local_3corner_pvt.csv`
- `sims/write_driver_capacitance_local_3corner_pex.csv`
- `tools/sram-eda`
- `tools/ENVIRONMENT.md`

Temporary netlists, raw waveforms, extracted LVS netlists, and Netgen reports
were kept under `/tmp` and are not repository evidence artifacts.

## 2026-10-07: dynamic row-decoder feedthrough correction

The original B5 output-NMOS upper-VGS finding was reproduced and localized to
the precharge path with independent-clock and footer-off diagnostics. A
precharge-only correction also exposed address-inverter VDS overshoot at
SS/1.8 V/-40 C. The implemented B6 source reduces M1–M5, M11, M16 and M21
widths to 0.42 um, retaining the original dynamic topology and M8 W=0.50 um.
The source-generated netlist matches the qualification netlist byte for byte.

Fresh Xschem/ngspice checks pass for the bare and loaded decoder. The loaded
TT/1.8 V/27 C/17.4 fF/50 ps result has 72/72 output samples, 252/252
non-model checks and zero upper-voltage findings. Peak output-NMOS VGS is
1.90111 V; maximum WL evaluation/precharge times are 302.04/413.64 ps.

The 54-condition TT/SS/FF voltage/temperature/slew experiment passes 3,888
output samples, with no VGS/VGD/VDS magnitude over 1.95 V. Four additional
Gear/trapezoidal 1 ps runs pass; their smallest measured magnitude margin is
3.12 mV. Sixteen script regressions pass. The full signed model domain,
noise/mismatch, timing contract and decoder physical closure remain open.

Selected CSV/JSON/netlist evidence, cause isolation, energy/timing comparisons
and a waveform figure are in [the feedthrough report](row_decoder_feedthrough_fix.md).
The standard runner now checks address-inverter VDS during precharge as well as
dynamic-node upper VGS during the entire transient. Existing bitcell, WL driver,
write driver and other owners' schematics/layouts were preserved.


## 2026-10-07: address-history and robustness characterization

Leonardo chose electrical margin and robustness as the decoder sizing priority.
The new contract executor preserves the canonical B6 schematic while testing
disposable input waveforms and dimensions. Completed matrices include 144
address/load histories, an 810-point arrival/phase/retention/edge/noise suite,
152 nominal family runs, 80 shortlisted corner cases, 132 refined interactions,
80 stack runs and 96 capacitance interactions. Twenty-four DC inverter curves
provide measured trip references. Their CSVs, manifests and executed script
snapshots are archived under `sims/row_decoder/results/`.

Expanded simultaneous address changes and CHGTOL=1e-18 C expose B6 M2 VDS
up to 1.974458 V. Thus the earlier schedule-specific B6 PASS is insufficient
for final sizing. All first shortlisted candidates fail at least one screen;
several larger-capacitance alternatives pass limited matrices with less than
0.23 mV voltage headroom and remain unfrozen. Exploratory rejected points and
invalid-address negative controls are retained, not counted as legal passes.

The executor rejects ngspice error logs, incomplete and nonfinite waveforms
even when `.control quit 0` returns zero. Checkpoints are written atomically
before raw cleanup; reuse requires matching input/script, recursive model
includes, helpers and tool versions. Numerical retries record MINBREAK and
CHGTOL without adding artificial circuit shunts. Current regressions include
narrow wrong-row pulses, incomplete precharge, bulk/rail/connectivity faults,
voltage-only exit failures, model fingerprint changes and buffered-address
diagnostic structure. Twenty-eight checker regressions pass.

Candidate interaction and buffered-address comparisons are continuing.
[The characterization report](row_decoder_contract_characterization.md) and
its exported PNG/PDF chart document the measurements and their limits.
Canonical decoder, WL/write driver, bitcell, root Xschem configuration and
other-owner source/layout work remain untouched by this campaign. No decoder
DRC, LVS, mismatch or full signed-model/reliability closure is claimed.


## 2026-10-07: retained buffered decoder B7 and Phase 1 handoff plan

B7 preserves the dynamic NAND architecture and all nine external pins. Four
additional static MOS regenerate A0T/A1T after the existing complement
inverters. M26--M29 use W=2 um; precharge uses 0.5 um, footer 1.5 um, output
inverters 2 um and evaluation stacks 1 um; original address inverters remain
0.42 um. All L=0.15 um, nf=1. The canonical schematic and SVG are updated.

The complete 264-case PVT/edge study passes all declared logical, settling
and terminal diagnostics. The worst magnitude is 1.924359 V in an unchanged
WL-buffer NMOS. Fifteen finer numerical comparisons pass; their largest
value is 1.925134 V with 0.25 ps Gear. The freshly netlisted canonical source
reproduces the qualified limiting-corner result exactly. Its original TT
loaded bench passes 72 output samples, 252 non-model checks and all upper
voltage diagnostics. Thirty checker/generator regressions pass.

The 204-case B7 contract campaign is also complete: 168 PASS, 24 detected
invalid-address controls, eight rejected 0.5 ns slow-phase samples, and four
rejected 8 fC perturbations. All ordered histories and sampled arrival leads
250/500/1000 ps pass at both declared profiles. All finite 10/1000 ns holds
pass. Invalid-address voltage findings are retained. These sampled phase,
arrival, retention and charge limits are not external setup, macro Fmax,
a noise budget or statistical/reliability qualification.

The comparison records actual costs: in four matched SS-cold/FF-hot 50 ps
cases, VDD cycle energy rises from 136.35 to 200.13 fJ and decoder channel-area
proxy from 2.979 to 5.577 um2. W=3 true buffers slightly worsen the observed
peak and add costs versus W=2. No global mathematical optimum is claimed.

All source/evidence hashes, source-to-derived netlist equivalence, selected
waveform samples and PNG/PDF views are in
[the characterization record](row_decoder_contract_characterization.md).
[The remaining Person 3 tasks](person3_phase1_remaining_tasks.md) now cover
real capture/PCLK timing, decoder layout, DRC/LVS, PEX repetition, row/write
integration and delivery through 13 October. No physical implementation was
started in this task. Existing WL/write layouts and other owners' work remain
unchanged. Local focused commits record the work; no publishing is implied.


## 2026-10-07: captured-address to PCLK timing budget

The new [`run_row_decoder_capture_timing.py`](../sims/row_decoder/run_row_decoder_capture_timing.py)
uses the SKY130 `sky130_fd_sc_hd__dfxtp_1` Liberty clock-to-Q and output
transition tables to create address-Q PWL waveforms. The current B7 decoder
and its four WL buffers are then freshly netlisted and simulated with the
continuous SKY130 MOS models. All 12 non-repeat old/new address transitions
are included. The decoder's wordline capacitors remain at the pre-layout
estimate of 17.4 fF for this timing study.

The DFF timing arcs were evaluated at two Liberty table loads: 3.434554 fF
(`nominal`) and 9.001619 fF (`stress`). These are table lookup points; the
captured-address Q-pin fanout has not yet been extracted. The selected
libraries are TT/1.80 V/25 C, SS/1.60 V/-40 C, and FF/1.65 V/100 C. The
decoder transistor-model profiles are TT/1.80 V/27 C, SS/1.62 V/-40 C, and
FF/1.80 V/125 C. Thus the DFF Liberty points are close-corner timing proxies,
not exact matched DFF/decoder corner pairs. The FF hot library was selected
from the installed PDK because it is closer to the decoder's hot profile than
the previously used FF/-40 C file.

| Campaign | Address transitions | PCLK phase points | Qualification | Timing guard |
|---|---:|---:|---:|---:|
| SS/-40 C, 9.00 fF DFF load | 12 x 8 = 96 | 0 to 2 ns | 60/96; early evaluation points are rejected | 41/96 across the sampled phase grid |
| Selected point, TT and FF; 3.43/9.00 fF DFF loads | 48 | 1.50 ns | 48/48 | 48/48 |
| Selected point, SS/-40 C; 3.43 fF DFF load | 12 | 1.50 ns | 12/12 | 12/12 |

At the recommended **1.50 ns capture-to-PCLK rise**, all 72 selected-point
cases pass the full decoder logic/voltage screen and the experimental
250 ps literal-settling guard. The worst result is SS/-40 C with the 9.00 fF
DFF table load: the raw and regenerated address literals settle 431.2 ps
before PCLK, leaving 181.2 ps beyond the selected guard. The largest measured
selected-WL delay to 90% is 675.44 ps. The largest terminal-magnitude result
at this selected point is 1.910414 V. PCLK falls at the CLK falling edge in
the test deck, leaving a 3.50 ns high evaluation phase after the 1.50 ns delay.

At 1.25 ns, all twelve SS/stress cases pass the logic/voltage screen, but only
5/12 meet the 250 ps internal-literal guard; the worst lead is 181.2 ps. At
1.00 ns all twelve pass the logic/voltage screen, but none meet the guard.
The sampled coarse study therefore supports 1.50 ns as a conservative
pre-layout timing target for the tested B7/17.4 fF row-load case. It does not
claim that 1.50 ns is an exact minimum or a project-wide clock specification.

The capture standard-cell subcircuit did not resolve with this installation's
continuous MOS model set: after adding the missing special-device wrapper,
ngspice still rejected the `nshort_model` bin. Those direct-subcircuit
attempts are excluded; the rejected run is retained in
[`capture_to_pclk_smoke2`](../sims/row_decoder/results/capture_to_pclk_smoke2/manifest.json).
The first two direct-subcircuit pilots each failed all 12 cases before a
complete transient. A later TT/nominal PWL pilot passed its 12 output
logic/voltage screens at a 500 ps phase, but its worst internal-literal lead
was -157.8 ps; that pilot is superseded by the full matrix. The accepted
method uses Liberty table arcs and PWL Q waveforms, while PCLK remains an ideal
delayed waveform. External register setup/hold, metastability, the
actual PCLK-generation path, extracted Q/load capacitance, the 50 fF WL stress
load, and post-layout timing are not covered. The 250 ps guard is an
engineering screening value, not yet an advisor-approved system requirement.
This closes a measured pre-layout timing budget, but the physical PCLK source
and complete macro timing budget remain open.

Reproduce the archived campaigns using new output directories:

```bash
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_capture_timing.py \
  --profiles slow --loads stress \
  --phase-ps 0 500 750 1000 1250 1500 1750 2000 --workers 2 \
  --output-dir /tmp/decoder-capture-slow-grid

./tools/sram-eda python3 sims/row_decoder/run_row_decoder_capture_timing.py \
  --profiles tt fast --loads nominal stress --phase-ps 1500 --workers 2 \
  --output-dir /tmp/decoder-capture-tt-ff-1500ps

./tools/sram-eda python3 sims/row_decoder/run_row_decoder_capture_timing.py \
  --profiles slow --loads nominal --phase-ps 1500 --workers 2 \
  --output-dir /tmp/decoder-capture-slow-nominal-1500ps
```

Summaries, detailed checks, terminal measurements, exact executed scripts,
PDK/library/tool hashes, and per-case decks/logs are archived in
[`sims/row_decoder/results/`](../sims/row_decoder/results/).


## 2026-10-07: dynamic row decoder layout, DRC and LVS

Correction: the initial zero-DRC counts recorded below were premature. The
Magic background checker had not been awaited, so those counts did not establish
DRC closure. A subsequent `drc catchup` found layout errors; the corrected
result is recorded in the next entry.

The B7 dynamic 2-to-4 decoder was imported from the canonical Xschem netlist
and routed in Magic under [`layout/row_decoder/`](../layout/row_decoder/).
The generated layout contains 29 MOS devices, four distinct evaluation stacks,
four precharge PMOS devices, four output inverters, two address-complement
inverters, a shared PCLK-controlled evaluation footer, separate VDD/VSS body
connections and an isolated `EVAL_GND` node. The external interface retains
`VDD`, `PCLK`, `A0`, `A1`, `DEC0`–`DEC3` and `VSS`; the physical port ordering
is checked against the Xschem-generated netlist by the layout builder.

The original DRC log recorded zero errors on the routed hierarchy and flattened
view, but the check had not finished. After waiting for it, Magic reported
1,745 error tiles on the flattened layout. The old zero counts therefore do not
prove DRC closure. The original Netgen comparison reported a unique match with
29 devices (17 NFET, 12 PFET) and 22 nets; a fresh comparison after the routing
correction is recorded below.

The first extraction attempt produced 231 coupling/substrate capacitance
elements, but **zero distributed route resistors**. Therefore the file from
that attempt is not a completed R-C PEX result and has not been used for
post-layout simulation. The cap-only SPICE file is retained under the explicit
name [`row_decoder_cap_only_unqualified.spice`](../layout/row_decoder/reports/row_decoder_cap_only_unqualified.spice).
Inspection of the failed Magic transcript
[`extract_attempt.txt`](../layout/row_decoder/reports/extract_attempt.txt) showed that the
legacy command had created `run.sim`/`run.nodes` instead of the required
cell-named files, so the builder now runs `ext2sim` on the loaded flattened
cell before `extresist`. The script has been corrected to call `ext2sim` with
no root argument, which targets the loaded cell; this correction has not yet
been exercised. Magic 8.3.589 predates the integrated full-resistance option
added in 8.3.597; the legacy flow depends on the `.sim` and `.nodes` files.
The detailed resistance extraction was paused until it can be run on a faster
machine. The RC extraction flow described in this initial entry has not been
run or qualified. The next command, once that machine is ready, is:

```bash
./tools/sram-eda python3 layout/row_decoder/build_layout.py \
  --skip-import --extract
```

The runner checks for both R and C elements and stops if either is missing.
Do not treat a capacitance-only netlist as PEX. The Magic command sequence is
described in the [official Magic extraction reference](https://github.com/RTimothyEdwards/magic/blob/master/doc/html/extract.html)
and [extresist reference](https://github.com/RTimothyEdwards/magic/blob/master/doc/html/extresist.html).

## 2026-10-07: row decoder DRC/LVS correction before parasitic extraction

The 1,745-error result came from the first routed geometry. The causes were
undersized via landing enclosures and only one of the two Magic MOS gate
contacts being routed. The layout generator now routes both gate contacts to
their schematic net and sizes the M1/M2/M3 landing regions to satisfy the
SKY130A contact rules. It also runs `drc catchup` before reading either DRC
count; Magic documents this command as waiting for the background checker to
finish ([DRC command reference](https://opencircuitdesign.com/magic/commandref/drc.html)).

After rebuilding from the retained B7 Xschem schematic, Magic 8.3.589 with
SKY130A technology 1.0.493 (`drc(full)`) reports **0 errors** on both the
routed top cell and the flattened layout. Updated reports are
[`route.txt`](../layout/row_decoder/reports/route.txt) and
[`drc_flat.txt`](../layout/row_decoder/reports/drc_flat.txt).

The new `--lvs-only` mode runs Magic connectivity extraction and Netgen without
calling `extresist` or generating an R-C PEX file. Netgen 1.5.293 reports a
unique match: 29 MOS devices (17 NFET, 12 PFET), 22 nets, and matching external
pins. The current LVS report is
[`lvs_recheck.txt`](../layout/row_decoder/reports/lvs_recheck.txt); the
connectivity netlist is [`row_decoder_flat_extracted.spice`](../layout/row_decoder/row_decoder_flat_extracted.spice).
That SPICE file contains no resistor or capacitor elements. This confirms
layout connectivity only; no parasitic timing simulation has been run.

Reproduce the pre-PEX checks from the repository root:

```bash
./tools/sram-eda python3 layout/row_decoder/build_layout.py --skip-import
./tools/sram-eda python3 layout/row_decoder/build_layout.py \
  --skip-import --lvs-only
```

Detailed distributed R-C extraction and post-layout simulation remain pending
for the faster machine. The earlier cap-only artifact remains explicitly
unqualified.

## 2026-10-07: distributed decoder R-C extraction completed; electrical simulation pending

The previous entry records the state before the current extraction run and is
superseded for extraction status by this entry. The WSL 2 / Docker Desktop setup
was completed on the Windows host: WSL 2.7.13.0 with kernel 6.1.33.2,
Docker Desktop 4.94, and Docker CLI/server 29.8.2. The project container is
`isaiassh/unic-cass-tools:1.0.7`, mounted at `/work`; tools used were Xschem
3.4.6, Magic 8.3.589, SKY130A technology 1.0.493
(`open_pdks` commit `0fe599b2afb6708d281543108caf8310912f54af`), Netgen
1.5.293, and ngspice 44.2. The container image and PDK versions were checked
from the installed tools and files rather than inferred from the image tag.

The standard `tools/sram-eda --check` launcher could not validate its bind mount
from this Windows checkout because Docker reports the mount source as a Windows
drive path while the launcher resolves the checkout through the shell's POSIX
path. The EDA command was therefore run directly in the already configured
container with `PDK_ROOT=/opt/pdks`, `PDK=sky130A`, and the installed `/opt`
tool directories added to `PATH`:

```powershell
docker exec -w /work sram-xschem bash -lc 'for tool_dir in /opt/ngspice/*/bin /opt/magic/*/bin /opt/netgen/*/bin /opt/iverilog/*/bin /opt/xschem/*/bin; do if [ -d "$tool_dir" ]; then PATH="$tool_dir:$PATH"; fi; done; export PATH PDK_ROOT=/opt/pdks PDK=sky130A; python3 layout/row_decoder/build_layout.py --skip-import --extract'
```

This command rebuilt routing, waited for Magic DRC on the routed and flattened
views, performed detailed extraction, and ran Netgen LVS. Both DRC reports
contain zero errors. The extracted netlist
[`row_decoder_pex.spice`](../layout/row_decoder/pex/row_decoder_pex.spice)
contains 29 MOS devices, 769 resistors, and 494 capacitors, and preserves the
external pin order `VDD PCLK A0 A1 DEC0 DEC1 DEC3 DEC2 VSS`. Its SHA-256 is
`cb22575eba88efbd7f40412cb18870cb3854fa4873c24db76f07f4f25df9b737`.
Netgen reports “Circuits match uniquely,” with 29 devices (17 NFET, 12 PFET)
and 22 nets. The extraction, DRC, and LVS logs are retained in
[`layout/row_decoder/reports/`](../layout/row_decoder/reports/); the earlier
231-capacitor, zero-resistor artifact remains explicitly unqualified.

The schematic-to-PEX electrical comparison has not completed. Two one-case
TT/00-to-00 pilots used 17.4 fF WL loads, 50 ps clock/address edges, Gear
integration, and maximum steps of 1 ps and 5 ps. The schematic baseline passed
with zero failed checks in both runs. At 1 ps its measured DEC/WL 90% delays
were 115.59/459.74 ps, DEC/WL precharge-to-10% delays were 245.66/418.65 ps,
and the terminal-magnitude maximum was 1.9033 V. At 5 ps the corresponding
values were 115.97/459.94 ps, 245.98/418.73 ps, and 1.8998 V. These are
pre-layout pilot results only. In both runs, ngspice 44.2 exceeded its
180-second per-case limit on the R-C PEX case; no PEX waveform, PEX measurements,
or paired comparison was produced. The manifests and baseline outputs are
retained in
[`row_decoder_pex_smoke_20261007`](../sims/row_decoder/results/row_decoder_pex_smoke_20261007/pex/manifest.json)
and
[`row_decoder_pex_smoke_5ps_20261007`](../sims/row_decoder/results/row_decoder_pex_smoke_5ps_20261007/pex/manifest.json).
The timeout does not establish either a functional failure or a successful PEX
simulation.

The new PEX runner
[`run_row_decoder_pex_contract.py`](../sims/row_decoder/run_row_decoder_pex_contract.py)
prepares a matched 13-case matrix: nine TT transitions and four SS/-40 C
diagonal transitions. It checks functional outputs, precharge, all distributed
dynamic-node segments, terminal magnitudes, delay, slew, and energy. Its
per-case ngspice timeout is configurable. A static audit performed after this
entry found a capacitance issue in the current PEX, so do not run this matrix
against the retained netlist yet. The audit and next action are recorded below.

## 2026-10-07: decoder PEX capacitance audit

The extracted file has 494 capacitor elements, of which four are negative
capacitors to `VSS` on distributed nodes:

| Element | Node | Extracted value |
| --- | --- | ---: |
| `C236` | `DEC0.n0` | −3.02859 fF |
| `C275` | `N3.n0` | −9.29966 fF |
| `C302` | `net4.n0` | −16.2877 fF |
| `C489` | `N2.n0` | −1.3128 fF |

The extracted capacitor matrix has four negative eigenvalues, equal to those
four isolated shunt values. This is a static audit of the SPICE capacitor
network, not a transient simulation result. The extracted netlist is therefore
not accepted for electrical characterization in its current form. The Magic
maintainer has documented negative parasitic capacitances as an extraction
bookkeeping problem and noted that they can remain in some R-C extractions
([Magic discussion #229](https://github.com/RTimothyEdwards/magic/discussions/229)).

The current artifact was generated with Magic 8.3.589. The builder now reports
negative capacitor entries and returns a nonzero status after completing LVS;
the matched PEX simulation runner rejects them before invoking Xschem or
ngspice. The [Magic download page](https://opencircuitdesign.com/magic/download.html)
lists version 8.3.684 dated 2026-09-18. The earlier PowerShell extraction
command reused the existing `sram-xschem` container, so it continued to select
Magic 8.3.589; rerunning that command alone would not change the tool version.
The repository now includes
[`install_magic_8_3_684.sh`](../tools/install_magic_8_3_684.sh) and explicit
version-selection commands in the
[`row decoder layout guide`](../layout/row_decoder/README.md). Magic 8.3.684 is
a candidate to evaluate, not a confirmed fix. Regenerate this same flattened
layout's PEX with that exact executable, record its version and hash, audit the
resulting capacitor values, and only then resume the one-case smoke and 13-case
comparison. Do not delete the four entries from the published PEX by hand:
that would alter the extracted model without a justified capacitance
redistribution.

The two earlier 180-second pilot timeouts remain inconclusive. The negative
capacitors may contribute to slow convergence, but the available runs do not
prove that they caused the timeout.

After the PEX passes the capacitance audit, start with a one-case smoke using a
900-second limit, then run the full matrix:

```bash
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py \
  --limit 1 --workers 1 --timeout-s 900
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py \
  --workers 2 --timeout-s 900
```

Do not report post-layout electrical validation until the PEX cases complete
and the matched checks pass. The decoder PEX includes the extracted decoder
only; the four WL buffers remain schematic devices and the row load remains the
17.4 fF estimate. Physical-row loading and complete macro behavior are still
outside this evidence.

## 2026-10-08 UTC: nonnegative decoder R-C PEX and matched electrical matrix

This entry supersedes the 2026-10-07 negative-capacitance status above. The
layout is the row decoder only. The bitcell and sense-amplifier/precharge source
trees were not changed. The retained decoder sizing for this run is: four
PCLK precharge PFETs M5/M11/M16/M21 at 2 um, eight evaluation-stack NFETs
M6/M7/M12/M13/M17/M18/M22/M23 at 2 um, and four output PFETs
M9/M14/M19/M24 at 3 um. The four wordline buffers remain schematic devices.

The Windows host used the `sram-xschem` container and SKY130A tech 1.0.493
(`open_pdks` commit `0fe599b2afb6708d281543108caf8310912f54af`). Magic 8.3.589
was used for Xschem-to-layout device import; Magic 8.3.684, built from commit
`4f53bb3091d1e4a9b2009a58f157a8a4331d4c84`, was used for routing, DRC and
extraction. Xschem was 3.4.6, Netgen 1.5.293 and ngspice 44.2. The generated
netlist/import and PEX flow was:

```bash
docker exec -w /work sram-xschem bash -lc 'for tool_dir in /opt/xschem/*/bin; do PATH="$tool_dir:$PATH"; done; export PATH PDK_ROOT=/opt/pdks PDK=sky130A; python3 layout/row_decoder/build_layout.py --skip-route'
docker exec -w /work/layout/row_decoder sram-xschem bash -lc 'PATH=/opt/magic/8.3.589/bin:$PATH; export PATH PDK_ROOT=/opt/pdks PDK=sky130A; magic -dnull -noconsole -rcfile /opt/pdks/sky130A/libs.tech/magic/sky130A.magicrc < generate_import.tcl'
docker exec -w /work sram-xschem bash -lc 'PATH=/opt/magic/8.3.684/bin:$PATH; for tool_dir in /opt/ngspice/*/bin /opt/netgen/*/bin /opt/iverilog/*/bin /opt/xschem/*/bin; do PATH="$tool_dir:$PATH"; done; export PATH PDK_ROOT=/opt/pdks PDK=sky130A; python3 layout/row_decoder/build_layout.py --skip-import --extract'
docker exec -w /work sram-xschem bash -lc 'for tool_dir in /opt/ngspice/*/bin /opt/netgen/*/bin /opt/iverilog/*/bin /opt/xschem/*/bin; do PATH="$tool_dir:$PATH"; done; export PATH PDK_ROOT=/opt/pdks PDK=sky130A; python3 sims/row_decoder/run_row_decoder_pex_contract.py --output-root sims/row_decoder/results/row_decoder_pex_output_pfets_3um_20261008 --workers 2 --timeout-s 300'
```

Both hierarchical and flattened Magic `drc(full)` reports have zero errors.
Netgen reports a unique match: 29 MOS (17 NFET, 12 PFET), 22 nets and matching
external/bulk connections. The R-C PEX preserves the pin order
`VDD PCLK A0 A1 DEC0 DEC1 DEC3 DEC2 VSS`, contains 393 resistors and 226
capacitors, and has no negative capacitor values. Its SHA-256 is
`c3e39efae880fd46fddd0d610f9dd789a3beeee847c62ba2fbdaa1bf88419128`.
The connectivity-only `row_decoder_flat_extracted.spice` remains separate from
this R-C PEX. Logs are in `layout/row_decoder/reports/`.

The complete paired matrix is retained at
[`row_decoder_pex_output_pfets_3um_20261008`](../sims/row_decoder/results/row_decoder_pex_output_pfets_3um_20261008/),
including its manifests, input netlists, CSV checks/measurements and comparison.
It completed all nine TT transitions and four SS/1.62 V/-40 C diagonal
transitions at a 5 ps maximum timestep with Gear integration, 50 ps clock and
address edges, and 17.4 fF loads. The pre-layout functional/settling results
are PASS in all 13 cases, while its separate terminal screen reports nine
upper-range findings. The PEX has nine PASS cases and four
`SETTLING_SCREEN_FAIL` cases. In each slow-corner case, the two selected-WL
checks at 1 ns measure 1.201–1.328 V against the 1.458 V minimum. No logic or
precharge check fails in those cases. The output PFET increase from 2 um to
3 um improved the slow-corner 90% WL delay from 1166–1235 ps in the prior
2 um-output iteration to 1089–1142 ps here, but did not close the 1 ns level
check. Current slow-corner WL precharge-to-10% delay is 943–1000 ps, compared
with 419–427 ps pre-layout. The PEX terminal screen reports five magnitude
findings; its experimental dynamic-node upper-voltage screen passes in all 13 cases. The baseline
and PEX campaign command exits nonzero because these experimental screens and
the four PEX settling checks are not all closed.

The sizing trail is retained as compact run evidence: the 0.5 um precharge
pilot fails the TT 00-to-00 PEX recovery check
([result](../sims/row_decoder/results/row_decoder_pex_20261007_234742/)); the
1 um precharge/1 um stack full matrix has 9 PEX passes and 4 slow-corner cases
with six failed checks each
([result](../sims/row_decoder/results/row_decoder_pex_20261007_235827/)); and
the 2 um precharge/2 um stack, 2 um output-PFET matrix reduces those slow cases
to two selected-WL failures each
([result](../sims/row_decoder/results/row_decoder_pex_20261008_000419/)). The
current 3 um output-PFET iteration improves the slow-corner WL delay further,
but the four 1 ns level failures remain. The runner's `.raw` waveforms are
excluded by the repository's `*.raw` ignore rule; manifests, input netlists,
logs and CSV measurements are retained for review.

These results establish a nonnegative distributed R-C extraction with DRC/LVS
closure and a completed matched simulation campaign; they do not establish
post-layout electrical closure. The 1.95 V terminal-magnitude screen remains
experimental, not a full reliability qualification. The PEX replaces only the
decoder; WL buffers are schematic devices and 17.4 fF remains an estimated row
load. Physical-row loading, full-macro behavior and external setup/hold remain
unqualified. Keep the four slow-corner selected-WL failures open; do not relax
the contract threshold or report full electrical sign-off.


## 2026-10-07 UTC: decoder all-network RC and selected electrical closure

The decoder now closes routed/flattened DRC, connectivity LVS and the selected
13-case schematic/PEX matrix at both 5 ps and 1 ps. This entry supersedes the
open four-case settling status above. Scope remains Person 3 / Leonardo's
2:4 dynamic decoder. Bitcell, sense-amplifier, precharge and WL-driver sources
were preserved. The remote Magic installer update was incorporated from
`origin/feature/peripherals` (`39f5ebc`); it is not an electrical decoder change.
Earlier date labels and results are retained as history; the manifests provide
actual UTC start times and the exact source/model/script hashes.

### Root causes and implementation

The previous router painted each of the 22 M3 tracks over the entire layout
width, including internal dynamic nets connected to distant labels. These
stubs unnecessarily loaded the decoder. Placement now groups each address
inverter/buffer and each row's precharge, stack and output stages; a central
routing channel and per-net endpoint bounds shorten local connections.
Separate PFET/NFET M2 lanes avoid shorts when cells share a column. Contact/via
landing dimensions and `drc catchup` are retained.

A second extraction audit found that all 393 resistors in the previously
reported PEX belonged to VSS. Signal nets had capacitance but no distributed
resistance because of the extraction cutoff. Magic documents `threshold` and
`minres` in milliohms, with a default threshold of 10000 milliohms
([official extresist reference](https://opencircuitdesign.com/magic/commandref/extresist.html)).
Detailed extraction now explicitly uses `threshold 0`, `mindelay 0` and
`minres 100` (0.1 ohm). The builder verifies the applied options, all 22 labeled
resistance networks, positive R values, R and C presence, MOS count/pins,
nonnegative capacitance and the exact clean Netgen final result. The earlier
393-R extraction did not meet this stronger coverage requirement.

Retained decoder sizing (all L=0.15 um, nf=1, mult=1):

| Devices | Width | Purpose of revision |
|---|---:|---|
| M1-M4 address inverters | 0.84 um | Reduce literal excursions that exceeded the experimental 1.95 V magnitude screen with 0.42 um inverters. |
| M5/M11/M16/M21 precharge PFETs | 1.25 um | Close recovery/precharge with less dynamic-node overshoot than the previous 2 um devices. |
| M6/M7/M12/M13/M17/M18/M22/M23 stacks | 2 um | Retain evaluation drive needed at SS/1.62 V/-40 C. |
| M9/M14/M19/M24 output PFETs | 3 um | Retain the output rise improvement. |
| Output NFETs / true-literal buffers | 2 um | Retained. |
| M8 footer | 1.5 um | Retained. |

[Intermediate trial summary](../layout/row_decoder/reports/closure_trials.json)
records the compact, original-sizing and central-channel candidates. Restoring
the original 0.5 um precharge/1 um stack sizing failed all 13 PEX cases;
1 um precharge/1 um stacks left four slow-corner failures; 1 um precharge with
2 um stacks closed the rise check but left four slow precharge failures and
baseline address-inverter excursions. The retained 1.25/2/3 um sizes and
0.84 um address inverters close both. A compact pilot lacking distributed
input source-voltage probes was an analysis failure, not a timing result.
Complete intermediate artifacts remain local; their summarized failures are
preserved separately from the final evidence.

The PEX runner now rejects stale MOS geometry/connectivity even when the pin
order matches, verifies source/PEX extraction hashes, saves input voltages
needed by the energy calculation, and requires every distributed dynamic-node
probe. It distinguishes baseline coverage from the 28 PEX dynamic segments.
The source text digest normalizes line endings so an equivalent Windows/Linux
schematic does not appear as a geometry revision. Byte digests are retained
for artifact provenance. `--cases` and `--max-step-ps` support numerical checks;
the manifest reports the actual timestep and acceptance screen definitions.

Energy integration now interpolates both endpoints of the unchanged
first-fall to second-fall window (10-25 ns, falling-edge midpoints). The old
sample mask could omit an endpoint and truncate part of a 50 ps edge. This
was tested against an analytical linear-power integral and a truncated trace.
The CSV reports net energy delivered by ideal VDD/PCLK/address sources,
including returned energy; it is not the dissipation of a physical upstream
clock/address driver. Old masked-energy values must not be compared directly
with the corrected measurement.

### Extraction and matched results

Versions: Magic 8.3.589 for PCell import and 8.3.684 for routing/DRC/extraction
(upstream `4f53bb3091d1e4a9b2009a58f157a8a4331d4c84`); SKY130A tech 1.0.493;
open_pdks `0fe599b2afb6708d281543108caf8310912f54af`; Xschem 3.4.6;
Netgen 1.5.293; ngspice 44.2. The host is Windows/Docker Desktop and the
container is `sram-xschem`, mounted at `/work`, with explicit
`PDK_ROOT=/opt/pdks PDK=sky130A`.

Current extraction: **744 R, 392 C, 29 MOS, 22 resistance networks**, zero
negative capacitors, nine external pins in order
`VDD PCLK A0 A1 DEC0 DEC1 DEC3 DEC2 VSS`. Routed and flattened `drc(full)`
each report **0**, and Netgen reports **Circuits match uniquely**. LVS checks
the separate connectivity netlist; MOS signature and extraction coverage
audits bind the simulation R-C network to that source. It is not a separate
resistor-by-resistor Netgen comparison.

PEX SHA-256:
`58fdf8632941897bc2e243a1141b047b4bd872eee6239fae18f872e21faba0a0`.
Normalized source-text SHA-256:
`90f6aa170d7f9b7019b55d3cd43ee4482d9c5d2927f0b0b011a6f5b492c8ec50`.
[Extraction manifest](../layout/row_decoder/pex/extraction_manifest.json)
records the byte hashes, per-net R counts, cutoffs and UTC time.

The nine TT/1.8 V/27 C and four SS/1.62 V/-40 C cases use Gear integration,
50 ps clock/address edges, a 2 ns address lead, 5 ns high / 10 ns low phases,
unchanged schematic WL buffers and 17.4 fF loads. Both baseline and PEX pass
**13/13 at 5 ps and 13/13 at 1 ps**; all four campaign exits are zero.
There are zero functional, precharge and experimental voltage-screen findings.
The 1 ns level thresholds and 1.95 V experimental bounds were not relaxed.

| 1 ps measurement | Baseline TT | PEX TT | Baseline SS cold | PEX SS cold |
|---|---:|---:|---:|---:|
| Selected WL delay to 90%, ps | 451.815-454.832 | 603.653-641.364 | 668.286-671.837 | 891.858-943.617 |
| Selected WL precharge to 10%, ps | 345.683-348.895 | 586.284-610.075 | 505.858-510.733 | 877.315-899.474 |
| WL rise slew 10-90%, ps | 294.752-294.754 | 294.931-295.110 | 445.904-445.905 | 446.020-446.185 |
| WL fall slew 90-10%, ps | 105.168-105.174 | 105.365-105.641 | 127.226-127.229 | 127.315-127.352 |
| Worst absolute VGS/VGD/VDS, V | 1.938876 | 1.887313 | 1.766355 | 1.755402 |
| Net ideal VDD energy, fJ | 160.071-221.766 | 303.933-596.692 | 162.756-173.638 | 437.156-471.432 |

Worst PEX slow-corner WL rise margin against 1 ns is **56.383 ps**;
precharge margin is **100.526 ps**. Between 5 ps and 1 ps, maximum PEX
WL rise-delay change is 0.148 ps and precharge-delay change is 0.125 ps.
Baseline changes are 0.243 ps and 0.137 ps respectively. Worst terminal
magnitude remains below 1.95 V at both steps; the tightest baseline margin is
about 11 mV. This is measured margin for the selected conditions, not a
mismatch/noise or lifetime guarantee.

`model_upper_result` retains its historical field name but measures the
experimental upper bound on gate-side dynamic-node voltage. It does **not**
provide signed model-domain clearance. `magnitude_result` checks absolute
VGS/VGD/VDS against 1.95 V; VBS extrema are separately reported. Earlier
references to a "signed model upper screen" were inaccurate.

### Area and energy cost

Paint bounding boxes at 0.005 um per Magic internal unit:

| Revision | Width x height, um | Bounding-box area, um2 |
|---|---:|---:|
| `627769a` | 220.5 x 73.76 | 16264.08 |
| Current | 146.25 x 28.645 | 4189.33125 |

The bounding box shrank by 74.24%; it is a decoder paint extent, not a full
macro area. The 29-MOS channel-area proxy sum(W*L) changed from 8.277 to
8.079 um2 (-2.39%). PCLK-driven gate channel area (four precharge PFETs plus
footer) changed from 1.425 to 0.975 um2 (-31.58%). These are geometry proxies,
not a measured capacitance or power reduction. Doubling the address inverters
also changes external A0/A1 loading; their capture/fanout budget must be repeated.

Corrected ideal-PCLK net energy is sensitive to timestep and returned energy.
Across the full matrix, its maximum 5 ps-to-1 ps difference is 0.596 fJ in
PEX (0.126 fJ baseline). The 1 ps-to-0.25 ps check covers two selected cases:

| Case / stage | VDD energy at 1 ps / 0.25 ps, fJ | PCLK net energy at 1 ps / 0.25 ps, fJ |
|---|---:|---:|
| TT 00-to-00 baseline | 160.070731 / 160.073095 | 1.457808 / 1.444598 |
| TT 00-to-00 PEX | 303.932963 / 303.948619 | 3.707040 / 3.723609 |
| SS cold 01-to-10 baseline | 169.236304 / 169.243539 | 0.990389 / 0.979237 |
| SS cold 01-to-10 PEX | 471.431559 / 471.447998 | 2.521789 / 2.535004 |

All four refined baseline/PEX simulations pass. PEX PCLK differences are
0.45% and 0.52% relative to 0.25 ps; baseline differences reach 1.14%.
VDD differences in these pilots are below 0.006%. Full-matrix PCLK energy
convergence and consumption with a physical clock/address driver remain open;
negative net ideal-source energies in some transitions indicate returned
energy over this window, not negative physical dissipation. No upstream
clock-driver power or frequency claim is made.

### Commands and retained evidence

The import and extraction commands are the explicit version-pinned commands in
[the decoder layout README](../layout/row_decoder/README.md#reproduce).
After extraction, the final electrical runs were:

```powershell
docker exec -w /work sram-xschem bash -lc 'for tool_dir in /opt/ngspice/*/bin /opt/netgen/*/bin /opt/iverilog/*/bin /opt/xschem/*/bin; do PATH=$tool_dir:$PATH; done; export PATH PDK_ROOT=/opt/pdks PDK=sky130A; python3 sims/row_decoder/run_row_decoder_pex_contract.py --output-root sims/row_decoder/results/row_decoder_pex_verified_5ps --max-step-ps 5 --workers 2 --timeout-s 300'
docker exec -w /work sram-xschem bash -lc 'for tool_dir in /opt/ngspice/*/bin /opt/netgen/*/bin /opt/iverilog/*/bin /opt/xschem/*/bin; do PATH=$tool_dir:$PATH; done; export PATH PDK_ROOT=/opt/pdks PDK=sky130A; python3 sims/row_decoder/run_row_decoder_pex_contract.py --output-root sims/row_decoder/results/row_decoder_pex_verified_1ps --max-step-ps 1 --workers 2 --timeout-s 300'
docker exec -w /work sram-xschem bash -lc 'for tool_dir in /opt/ngspice/*/bin /opt/netgen/*/bin /opt/iverilog/*/bin /opt/xschem/*/bin; do PATH=$tool_dir:$PATH; done; export PATH PDK_ROOT=/opt/pdks PDK=sky130A; python3 sims/row_decoder/run_row_decoder_pex_contract.py --output-root sims/row_decoder/results/row_decoder_pex_energy_025ps --max-step-ps 0.25 --cases tt_00_to_00 slow_01_to_10 --workers 2 --timeout-s 300'
docker exec -w /work sram-xschem bash -lc 'python3 -m unittest discover -s sims/row_decoder -p "test_*.py"'
docker exec -w /work sram-xschem bash -lc 'python3 -m py_compile layout/row_decoder/build_layout.py sims/row_decoder/run_row_decoder_contract.py sims/row_decoder/run_row_decoder_pex_contract.py'
git diff --check
```

Use new empty output directories when repeating these runs. All **37** tests
pass: they include stale sizing rejection, distributed input source-voltage
saves, missing-segment rejection, baseline coverage separation, energy-window
interpolation/truncation and the existing waveform checker regressions.

Final evidence roots:

- [5 ps matrix](../sims/row_decoder/results/row_decoder_pex_verified_5ps/)
- [1 ps matrix](../sims/row_decoder/results/row_decoder_pex_verified_1ps/)
- [0.25 ps energy pilots](../sims/row_decoder/results/row_decoder_pex_energy_025ps/)
- [Closure metrics and hashes](../layout/row_decoder/reports/closure_metrics.json)
- [Intermediate candidate summary](../layout/row_decoder/reports/closure_trials.json)

These roots retain input netlists, cases/decks, runner/helper snapshots,
completed manifests, checks/terminal CSVs, comparison CSVs and ngspice/Xschem
logs (explicitly added despite the generic log ignore rule). `.raw` waveforms
remain local under the repository ignore rule. The previous claim that all
historical campaign logs were published was too broad; these final campaign
logs are explicitly retained. ngspice emits the installed model's negative
Eta0 parameter warnings in the slow corner; the logs preserve them. Neither
those warnings nor passing experimental voltage screens establish model-domain
or reliability sign-off.

Selected decoder R-C timing/voltage closure is complete. The archived 264-case
B7 broad campaign and 72-case captured-address budget apply to their original
source, not the new sizing. Requalify broad PVT, perturbation/retention and
capture/fanout before using those historical guarantees. Physical-row loading,
full-macro operation and owner-interface integration remain separate work;
no other owner's block was modified to obtain this result.

> As duas entradas seguintes investigam a revisão histórica 39f5ebc, antes das correções de 7ad0348; não descrevem o sizing/PEX atual.

## 2026-10-08: analysis of the retained decoder PEX campaign

The artifact-only analysis is recorded in
[`row_decoder_pex_analysis_20261008.md`](row_decoder_pex_analysis_20261008.md).
It was reproduced with `python3 sims/row_decoder/analyze_row_decoder_pex.py`;
input hashes and derived CSVs are retained under
`sims/row_decoder/results/row_decoder_pex_analysis_20261008/`. No new extraction,
simulation, circuit/layout edit, or acceptance-threshold change was performed.

The eight failed checks are selected-WL window minima after the experimental
1 ns settling allowance, not wrong-row or final-level failures. About 84% of
the additional slow-corner 50% delay is already present at DEC. The route
generator creates full-width M3 tracks even for internal local nets. Static
PEX analysis finds 18.5–19.7 fF of incident capacitance on each dynamic node
and 61.4 fF on EVAL_GND, including coupling rather than constant effective loads.
This supports investigating routing/capacitive loading, without proving its
causal contribution before a controlled transient comparison.

All 393 explicit resistors belong to VSS; the dynamic/output signal nets are
not resistively segmented in this PEX. The isolated DC resistor-network
reduction gives 2.4–33.7 ohm to grounded diffusion contacts and 234–322 ohm
to NFET bulk contacts. A 127 kOhm individual resistor does not represent the
complete grounded path. Five magnitude-screen warnings peak on address-inverter
M1/M2 at 18 ns during address switching, before PCLK evaluation at 20 ns.
Worst WL precharge-to-10% is 999.896 ps, leaving only 0.104 ps versus the
experimental 1 ns check at a 5 ps maximum timestep. Numerical margin and
full signed model qualification remain open. The 1 ns allowance is not a
specified macro timing target. Proposed next work starts with focused
convergence and R/C-isolation simulations using the existing PEX; another
extraction is needed after an actual physical change.

## 2026-10-08: completed existing-PEX diagnostic simulations

The detailed report is
[`row_decoder_pex_diagnostics_20261008.md`](row_decoder_pex_diagnostics_20261008.md).
Ten convergence/R-C isolation simulations of `slow_00_to_11` and `tt_11_to_00`,
then two additional slow-case refinements, completed with ngspice 44.2.
All 12 ngspice subprocesses returned zero; both campaigns have `complete=true`
and no execution errors. The experiment executors return 1 because the full
PEX settling/voltage screens remain open. No acceptance threshold, circuit,
layout, or PEX was changed. The same recursive model hashes were required.
A fresh Xschem electrical netlist exactly matches the archived baseline,
despite differences in historical/current source-file byte hashes.

At SS/1.62 V/-40 C, full PEX WL 90% delay is 1141.66 ps at 5 ps maximum step;
collapsing the VSS resistor network changes it to 1139.63 ps; removing only
the 226 explicit extracted capacitors changes it to 662.89 ps. Intrinsic MOS
capacitances and external WL loads remain. These artificial variants identify
the extracted-capacitance set as the dominant additional delay in the tested
cases, without qualifying a modified physical circuit or isolating individual
capacitors. The full slow-case settling failure persists at 1, 0.5 and 0.25 ps.
At 0.25 ps with explicit tight tolerances, WL 90% delay is 1141.8598 ps and
precharge-to-10% delay is 999.9769 ps. The latter still passes, but leaves only
0.0231 ps versus the experimental 1 ns screen. Convergence does not supply
physical robustness margin.

The TT A0B undershoot is directly observed at -0.38606 V in the refined full
PEX waveform. Collapsing VSS resistors barely changes it; removing extracted
C reduces it to -0.03095 V. Full TT terminal magnitude remains 2.18606 V;
even the no-C TT diagnostic has a 2.05783 V magnitude finding. Model-domain
and reliability qualification remain open. Source/PEX hashes were checked
again after execution. The host's stale GUI Xauthority mount was bypassed
with a resource-limited headless container using the already installed image.

Retained results are in `sims/row_decoder/results/row_decoder_pex_diagnostics_20261008/`
and `row_decoder_pex_precharge_refinement_20261008/`: manifests, decks, CSVs,
PNG/PDF waveforms, 10 ps visualization samples and versionable simulator text
logs. Full raw waveforms are retained locally and remain ignored by Git.
These focused tests support a routing/capacitance revision next, followed by
DRC/LVS and another extraction after the physical change. They are not a
completed full post-layout PVT/macro qualification.

## 2026-10-08: compact decoder layout and remote extraction handoff

- Fetched and fast-forwarded `feature/peripherals` to `7ad0348`. Preserved its
  source sizing, all-network R-C extraction controls and runner fixes; archived
  its physical/PEX evidence before changing geometry. The earlier local PEX
  diagnostics above describe 39f5ebc only.
- Paired placement, branch-local M3 spans and grounded address shields produce
  a 98.80 × 36.92 um bbox (3647.70 um2). Compared to the newly fetched remote
  layout: 12.93% less bbox area and 22.68% less horizontal M3, including shields.
  Compared to 39f5ebc: 77.57% / 77.90%. No electrical improvement claimed.
- Magic 8.3.684, SKY130A tech 1.0.493: routed and flattened DRC both zero.
  Netgen 1.5.293 reports unique LVS, 29 MOS / 22 nets / nine unchanged pins.
  The retained schematic is byte-identical to 7ad0348.
- Connectivity extraction only for LVS; **no extresist or new R-C extraction
  executed locally**. New PEX and electrical tests are for the other machine.
- Ten routing/provenance regressions pass. The simulation runner rejects stale
  PEX before starting tools; successful new extraction alone can bind current
  source/layout/PEX hashes after physical and parasitic audits.
- The old canonical PEX remains byte-identical to 7ad0348 (SHA-256
  `58fdf8632941897bc2e243a1141b047b4bd872eee6239fae18f872e21faba0a0`).
  It is marked stale for the new layout. `.res.ext`, `.sim`, `.nodes` and old
  RC logs are archived so they cannot be mistaken for current extraction.
- Commands, actual-geometry PNG/PDF, reports and next checks:
  [compaction handoff](row_decoder_layout_compaction_20261008.md).

## 2026-10-08: compact decoder R-C extraction and electrical checks

This entry closes the new compact geometry from `d20f509`; it supersedes the
pending-extraction handoff above. Only `layout/row_decoder/` and its decoder
simulation evidence were regenerated. The canonical decoder schematic and
the bitcell, sense-amplifier, precharge, WL-driver and write-driver sources
were not changed.

The checkout was on `feature/peripherals` at `d20f509`, fast-forwarded from
`7ad0348` with a clean worktree before execution. Docker image
`isaiassh/unic-cass-tools:1.1.0` mounted that checkout at `/work`.
`./tools/sram-eda --check` confirmed the container, SKY130A model/technology
files, Xschem 3.4.6, ngspice 44.2, Netgen 1.5.293 and support tools. The
image's Magic 8.3.613 was too old for this run; the repository's
`tools/install_magic_8_3_684.sh` installed Magic 8.3.684, after which the
launcher check selected that version. SKY130A technology was 1.0.493, from
open_pdks commit `0fe599b2afb6708d281543108caf8310912f54af`; the PDK was
already present and was not rebuilt.

One extraction command was run:

```bash
./tools/sram-eda bash tools/extract_row_decoder.sh
```

The helper selected Magic 8.3.684 and ran
`python3 layout/row_decoder/build_layout.py --skip-import --extract`. It
regenerated routing, waited for hierarchical and flat `drc(full)`, extracted
R-C, ran Netgen LVS and checked current provenance. Exit status was 0.
Both DRC counts were zero. Netgen reported “Circuits match uniquely” for
29 MOS (17 NFET, 12 PFET), 22 nets and the matching nine pins. The PEX contains
**762 positive resistors and 389 nonnegative capacitors**; resistance covers
all 22 labeled networks. The external pin order is
`VDD PCLK A0 A1 DEC0 DEC1 DEC3 DEC2 VSS`. There are no negative capacitors.
The current PEX SHA-256 is
`8ee6b99aabf94bde9a1de2a13f0c040cda41dd55bb9568672e38a7f6bb54a6dc`.

The full extraction stdout is retained in
[the extraction log](../layout/row_decoder/reports/extract_run_d20f509_20261008.log).
Machine-readable counts, the 22-network breakdown and source/layout/PEX hashes
are in [the extraction manifest](../layout/row_decoder/pex/extraction_manifest.json)
and [current provenance](../layout/row_decoder/pex/provenance.json).
The builder logs are `reports/route.log`, `reports/drc_flat.log`,
`reports/extract.log` and `reports/lvs.log`.

The critical paired simulations were run as:

```bash
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py --output-root sims/row_decoder/results/compact_decoder_5ps --max-step-ps 5 --workers 2 --timeout-s 900
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py --output-root sims/row_decoder/results/compact_decoder_1ps --max-step-ps 1 --workers 2 --timeout-s 900
```

Each matrix contains nine TT/1.8 V/27 °C transitions and four SS/1.62 V/-40 °C
diagonal transitions. Both used Gear integration, 50 ps clock/address edges,
the unchanged schematic WL buffers and an estimated 17.4 fF row load. At both
steps, schematic and PEX each pass 13/13 cases with zero contract, precharge,
dynamic-node or experimental terminal-screen findings. The runner checked 28
distributed dynamic segments on the PEX.

At 1 ps, PEX selected-WL 90% delay is 551.858–815.389 ps; precharge-to-10%
is 524.334–789.564 ps; selected-WL 10–90% rise slew is 294.811–445.935 ps.
The largest PEX terminal-magnitude result is 1.878 V, below the unchanged
experimental 1.95 V screen. Across matched cases, the largest 5 ps-to-1 ps
differences are 0.091 ps for WL 90% delay, 0.127 ps for precharge delay,
0.052 ps for rise slew, 4.2 mV for terminal magnitude and 0.139 fJ for the
reported ideal-VDD-source energy. Source energy is net energy in the selected
window and includes returned energy; it is not upstream-driver dissipation.

Detailed checks and measurements are in each result root's
`baseline/`, `pex/` and `comparison.csv`; each root also records the
PEX hash and extraction manifest. These results close the selected decoder
matrix for this layout, not broad PVT, noise/retention, captured-address
fanout, physical-row loading or full-macro operation. The WL buffers remain
schematic and 17.4 fF remains an estimate. The 1.95 V screen is experimental
and does not establish signed model-domain or reliability clearance.

## 2026-10-08: compact decoder FF-hot electrical extension

After the fresh compact-layout extraction, the selected decoder matrix was
extended to the existing fast-hot model profile: FF, 1.8 V and 125 °C. The
runner now accepts `--profiles fast`; the default TT/SS matrix is unchanged.
Nine selected address transitions matching the TT set were evaluated against
both the current Xschem baseline and the current distributed R-C PEX. This is
a selected extension, not the full set of 16 possible previous/new address
pairs or broad PVT qualification.

| Maximum transient step | Baseline | PEX | Baseline checks | PEX checks |
|---:|---:|---:|---:|---:|
| 5 ps | 9/9 pass | 9/9 pass | 936/936 | 1,440/1,440 |
| 1 ps | 9/9 pass | 9/9 pass | 936/936 | 1,440/1,440 |
| 0.5 ps, directed peak case | 1/1 pass | 1/1 pass | 104/104 | 160/160 |

At 1 ps, maximum baseline WL delay to 90% was 394.006 ps and maximum
precharge-to-10% was 306.280 ps. The corresponding PEX maxima were 492.795 ps
and 461.940 ps. In the directed `01→10` baseline case, maximum absolute `VGD`
was 1.949037 V at 1 ps and 1.949031 V at 0.5 ps, or 0.963 mV below the
runner's 1.95 V absolute terminal-difference screen. This is not a signed
model-domain margin: the PDK documents signed operating ranges for `VGS`,
`VDS` and `VBS`, but not `VGD`. The runner's historical `model_upper_result`
checks an internal dynamic-node voltage against the same number, while
`magnitude_result` checks absolute `VGS`/`VGD`/`VDS`; neither is a full signed
PDK-domain check. The maximum PEX terminal magnitude was 1.878690 V at 1 ps
and 1.878005 V in the directed 0.5 ps case. These project screens do not
establish reliability or signed device-model validity. The PDK ranges are
documented in [device-details.rst](https://github.com/google/skywater-pdk/blob/main/docs/rules/device-details.rst#L4-L100).

The 38 retained ngspice text logs contain no `Error:` lines, but they report
FF model warnings: several `A2` values exceed 1, causing ngspice to clamp `A2`
and reset `A1`, and negative `Eta0`, `Pdibl1` and `Pdibl2` values are also
reported. The versioned [ngspice 44.2 BSIM4 check for `A2`](https://github.com/imr/ngspice/blob/ngspice-44.2/src/spicelib/devices/bsim4v5/b4v5check.c#L485-L498)
sets `A2` to 1 and `A1` to 0 when `A2 > 1`. Its [checks for negative `Eta0`,
`Pdibl1` and `Pdibl2`](https://github.com/imr/ngspice/blob/ngspice-44.2/src/spicelib/devices/bsim4v5/b4v5check.c#L471-L575)
print warnings without changing those parameters in that validation routine.
There are no fatal `Error:` lines. The warnings come from FF model parameter
validation; they are not evidence of a schematic connectivity error. The
logic and project screens therefore describe this simulator's handling of the
loaded FF model, while model-domain and reliability qualification still need
review by the PDK/model owner.

The largest 5 ps-to-1 ps PEX timing and terminal changes are 0.130 ps in WL
90% delay, 0.191 ps in WL precharge, 0.058 ps in selected WL rise slew, and
0.373 mV in terminal magnitude. The PCLK ideal-source energy had a maximum
0.502 fJ difference in this full matrix. Selected 0.5 ps refinements of the
highest-sensitivity pairs across TT/SS/FF passed; the 1 ps-to-0.5 ps change
was at most 0.576% in the FF baseline and 0.253% in FF PEX. The full
corner-by-corner results are in the [PCLK convergence audit](../sims/row_decoder/results/compact_decoder_pclk_energy_convergence_audit.json).
The four WL buffers remain schematic and each row load is an estimated
17.4 fF; extracted physical row loading, address capture/fanout, noise,
retention, mismatch and macro-level behavior remain open.

The runner unit suite passes six tests, including the new nine-transition
profile regression. Result decks, manifests, CSVs and text logs are under
[`compact_decoder_fast_5ps`](../sims/row_decoder/results/compact_decoder_fast_5ps/),
[`compact_decoder_fast_1ps`](../sims/row_decoder/results/compact_decoder_fast_1ps/)
and [`compact_decoder_fast_peak_0p5ps`](../sims/row_decoder/results/compact_decoder_fast_peak_0p5ps/).
The audit summary with hashes and warning counts is
[`compact_decoder_fast_hot_audit.json`](../sims/row_decoder/results/compact_decoder_fast_hot_audit.json);
the interpretation and reproduction commands are in the
[qualification report](row_decoder_fast_hot_qualification_20261008.md).

## 2026-10-08: full 16-pair TT decoder matrix

The current runner's --all-address-pairs option was used with --profiles tt
to exercise all 16 ordered pairs among 00, 01, 10 and 11, including same-address
pairs. The run used the current 29-MOS, 762-R, 389-C PEX. At 5 ps and 1 ps,
both the schematic baseline and PEX passed 16/16 cases; contract findings were
zero and all dynamic-node, model-upper and absolute-terminal screens passed.
The 5 ps PEX peak terminal magnitude was 1.875056 V (tt_11_to_11); the 1 ps
peak was 1.877770 V (tt_11_to_00).

The largest per-case PEX differences between 5 ps and 1 ps were 0.080561 ps
in WL delay to 90%, 0.126165 ps in precharge-to-10%, 0.051190 ps in selected
WL rise slew and 4.190 mV in terminal magnitude. The complete result roots,
including cases, summaries, checks, manifests, input decks and per-case ngspice
logs, are [5 ps](../sims/row_decoder/results/compact_decoder_full_tt_matrix_5ps/)
and [1 ps](../sims/row_decoder/results/compact_decoder_full_tt_matrix_1ps/).
Each root includes a raw-waveform manifest with size and SHA-256 for its 32
waveforms. The 845,475,648 bytes of waveform dumps remain under
/tmp/row_decoder_ced83c4_tt_all_pairs_{5ps,1ps} in sram-xschem and are not
committed.

Reproduce from the repository root with:
- ./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py --output-root sims/row_decoder/results/compact_decoder_full_tt_matrix_5ps --profiles tt --all-address-pairs --max-step-ps 5 --workers 2 --timeout-s 900
- ./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py --output-root sims/row_decoder/results/compact_decoder_full_tt_matrix_1ps --profiles tt --all-address-pairs --max-step-ps 1 --workers 2 --timeout-s 900

This section closes the TT address-pair matrix for the recorded setup. The
later SS-cold and FF-hot sections also record their complete 16-pair matrices.
None of these leaf tests qualifies broad PVT, physical row loading, noise,
retention, capture/fanout, signed model-domain limits or reliability.

## 2026-10-08: full 16-pair FF-hot decoder matrix

The complete ordered address-transition matrix was run at the `fast` profile
(FF, 1.8 V, 125 °C), at both 5 ps and 1 ps maximum transient steps. Each
matrix includes all 16 old/new address pairs among 00, 01, 10 and 11,
including the four same-address transitions. The baseline and current compact
29-MOS/762-R/389-C PEX each passed 16/16 cases at both steps, with zero
contract-check failures. That is 1,664/1,664 baseline checks and 2,560/2,560
PEX checks per timestep; the dynamic-node, model-upper and absolute-terminal
screens passed in every case.

| Maximum step | Baseline | PEX | Baseline checks | PEX checks | Peak baseline terminal magnitude | Peak PEX terminal magnitude |
|---:|---:|---:|---:|---:|---:|---:|
| 5 ps | 16/16 PASS | 16/16 PASS | 1,664/1,664 | 2,560/2,560 | 1.948349 V | 1.879030 V |
| 1 ps | 16/16 PASS | 16/16 PASS | 1,664/1,664 | 2,560/2,560 | 1.949037 V | 1.878690 V |

At 1 ps, the baseline maximum WL delay to 90% is 394.006 ps and the maximum
precharge-to-10% is 306.280 ps. The corresponding PEX maxima are 492.795 ps
and 461.940 ps. The baseline peak is the absolute `VGD` magnitude in
`fast_01_to_10`; it is 0.963 mV below the runner's historical 1.95 V
absolute-terminal screen. That is a numerical screen result, not a signed PDK
model-domain margin. The PEX peak terminal magnitude is 1.878690 V in
`fast_10_to_01`.

For matched cases, the largest 5 ps-to-1 ps PEX changes are 0.130 ps in WL
90% delay, 0.191 ps in WL precharge-to-10%, 0.058 ps in selected WL rise slew,
and 0.373 mV in terminal magnitude. The maximum difference in measured PCLK
source cycle energy is 0.502 fJ (12.85% relative to the 1 ps value), so the
energy result is more timestep-sensitive than the timing and terminal screens.
The targeted 0.5 ps refinements documented below support 1 ps as the reference
for the recorded cases.

All 64 retained ngspice logs (16 baseline and 16 PEX cases at each of two
timesteps) have no `Error:` lines. They do contain the FF BSIM4 parameter
warnings already seen in the selected campaign: `A2 > 1` (ngspice clamps `A2`
and resets `A1`), and negative `Eta0`, `Pdibl1` and `Pdibl2`. Therefore, passing
logic and project voltage screens under the simulator's reported parameter
handling does not establish full signed model-domain or reliability
qualification. The terminal-magnitude screen includes `VGD` and is not itself
a signed model-domain check.

The PEX file hash is
`8ee6b99aabf94bde9a1de2a13f0c040cda41dd55bb9568672e38a7f6bb54a6dc` (29 MOS,
762 resistors, 389 capacitors). The full audit, including warning counts,
matched timestep deltas and hashes, is
[`compact_decoder_full_fast_matrix_audit.json`](../sims/row_decoder/results/compact_decoder_full_fast_matrix_audit.json).
Per-case summaries, checks, manifests, input decks and text logs are in the
[5 ps result root](../sims/row_decoder/results/compact_decoder_full_fast_matrix_5ps/)
and [1 ps result root](../sims/row_decoder/results/compact_decoder_full_fast_matrix_1ps/).
The 64 raw waveforms total 845,475,232 bytes and remain local/ignored by Git.

Reproduce from the repository root with one worker:
- `./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py --output-root sims/row_decoder/results/compact_decoder_full_fast_matrix_5ps --profiles fast --all-address-pairs --max-step-ps 5 --workers 1 --timeout-s 900`
- `./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py --output-root sims/row_decoder/results/compact_decoder_full_fast_matrix_1ps --profiles fast --all-address-pairs --max-step-ps 1 --workers 1 --timeout-s 900`

This completes the FF all-address-pair matrix for the recorded setup. It
does not remove the model warnings or qualify broad PVT, physical row loading,
noise, retention, mismatch, captured-address/fanout or macro-level behavior.


## 2026-10-08: full 16-pair SS-cold decoder matrix

The complete 16-pair address-transition matrix was run at the `slow` profile
(SS, 1.62 V, -40 °C), including all old/new pairs among `00`, `01`, `10` and
`11`. At both 5 ps and 1 ps, the schematic baseline and the current compact
29-MOS/762-R/389-C PEX passed all 16 cases, with no contract failures or
voltage-screen findings. The baseline recorded 1,664 passing checks and PEX
recorded 2,560 passing checks per timestep.

| Maximum step | Baseline | PEX | Baseline checks | PEX checks | Peak baseline terminal magnitude | Peak PEX terminal magnitude |
|---:|---:|---:|---:|---:|---:|---:|
| 5 ps | 16/16 PASS | 16/16 PASS | 1,664/1,664 | 2,560/2,560 | 1.757977 V | 1.714500 V |
| 1 ps | 16/16 PASS | 16/16 PASS | 1,664/1,664 | 2,560/2,560 | 1.766599 V | 1.716479 V |

At 1 ps, the maximum WL delay to 90% is 672.226 ps in the baseline and
815.389 ps in PEX; the maximum precharge-to-10% time is 510.733 ps and
789.564 ps, respectively. All cases remain below the testbench's 1 ns timing
screen. Between 5 ps and 1 ps, the largest PEX changes were 0.092 ps in WL
90% delay, 0.097 ps in precharge-to-10%, and 2.363 mV in terminal magnitude.

All 64 retained ngspice logs have no `Error:` lines. They report the same
negative `Eta0` parameter warning in all 32 logs at each step (16 baseline and
16 PEX). The selected 5 ps-to-1 ps PCLK energy differences and the 0.5 ps
refinements for sensitive TT/SS/FF cases are summarized in the dedicated PCLK
audit. The 1 ps full-matrix results are the numerical reference for the
recorded setup.

The PEX hash is
`8ee6b99aabf94bde9a1de2a13f0c040cda41dd55bb9568672e38a7f6bb54a6dc`.
The audit records hashes, model and tool versions, check counts, per-case
metrics, warnings, and waveform sizes: [SS full-matrix audit](../sims/row_decoder/results/compact_decoder_full_slow_matrix_audit.json).
Per-case outputs are in the [5 ps](../sims/row_decoder/results/compact_decoder_full_slow_matrix_5ps/)
and [1 ps](../sims/row_decoder/results/compact_decoder_full_slow_matrix_1ps/) result roots. Raw waveforms total 845,503,008 bytes and remain local/ignored by Git.

Reproduce with one worker in the headless project container:

```bash
SRAM_EDA_CONTAINER=sram-pex-diag-20261008 ./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py \
  --profiles slow --all-address-pairs --max-step-ps 5 --workers 1 \
  --timeout-s 900 --output-root sims/row_decoder/results/compact_decoder_full_slow_matrix_5ps
SRAM_EDA_CONTAINER=sram-pex-diag-20261008 ./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py \
  --profiles slow --all-address-pairs --max-step-ps 1 --workers 1 \
  --timeout-s 900 --output-root sims/row_decoder/results/compact_decoder_full_slow_matrix_1ps
```

## PCLK ideal-source energy convergence review — TT, SS and FF

The complete 16-pair matrices at 5 ps and 1 ps show that PCLK source energy is
more timestep-sensitive than the timing and terminal metrics. The selected
0.5 ps runs target the pairs with the largest baseline or PEX energy changes
in those full matrices. All seven selected pairs passed in both baseline and
PEX, with 0 failed checks and no `Error:` lines.

| Profile | Largest 5 ps→1 ps baseline delta | Largest 5 ps→1 ps PEX delta | Largest selected 1 ps→0.5 ps baseline delta | Largest selected 1 ps→0.5 ps PEX delta |
|---|---:|---:|---:|---:|
| TT, 1.8 V, 27 °C | 0.126 fJ (`11→01`) | 0.501 fJ (`11→10`) | 0.721% | 0.431% |
| SS, 1.62 V, -40 °C | 0.090 fJ (`01→00`) | 0.395 fJ (`10→10`) | 0.889% | 0.503% |
| FF, 1.8 V, 125 °C | 0.144 fJ (`01→11`) | 0.502 fJ (`01→00`) | 0.576% | 0.253% |

Across all full matrices, the largest relative 5 ps-to-1 ps PEX change was
15.83% in SS (`01→00`), using the 1 ps value as the denominator. The 0.5 ps refinements are targeted, not a complete
0.5 ps matrix. Their maximum 1 ps-to-0.5 ps changes were below 0.89% in the
baseline and below 0.51% in PEX. This supports retaining 1 ps as the reported
reference for the specified cases; no energy tolerance was defined by the
technical specification.

The metric is signed net energy delivered by the ideal `VPCLK` source between
the first and second PCLK falling-edge midpoints. It includes energy returned
to the ideal source and is not the dissipation of a physical clock source or
driver. The [machine-readable audit](../sims/row_decoder/results/compact_decoder_pclk_energy_convergence_audit.json)
contains the per-case 5 ps, 1 ps and 0.5 ps values, screens, hashes and
reproduction commands. Detailed 0.5 ps outputs are in the [FF](../sims/row_decoder/results/compact_decoder_fast_pclk_energy_0p5ps/)
and [TT/SS](../sims/row_decoder/results/compact_decoder_ttslow_pclk_energy_0p5ps/) result roots.

## 2026-10-08: signed device-bias and transient-initialization audit

The new signed-bias postprocessor reviewed the archived 1 ps FF and SS
baseline/PEX waveforms across all 16 ordered address pairs. It compares
polarity-oriented `VGS`, `VDS` and `VBS` with the published SKY130 1.8 V
device ranges. All existing functional checks remain passing; this audit
found no new logic or wiring failure. It did find that the previous absolute
terminal-magnitude screen does not answer whether signed device biases are
inside the published ranges.

In the post-startup PEX window (samples at or after 1 ns), FF/SS `VDS` and
`VBS` stayed within the published ranges. The SS PFET `VBS` minimum was
−0.096479 V, only 3.521 mV above the documented −0.10 V boundary. Signed
`VGS` fell outside the published ranges in both corners: NFET `VGS` reached
−1.532192 V (FF) and −1.084485 V (SS), while PFET `VGS` reached +0.079892 V
(FF) and +0.096479 V (SS). These are measured screening results under the
documented source/drain orientation convention; their applicability to
model qualification needs review. They do not, by themselves, indicate a
logic failure or a schematic connection error.

The original decks use `uic`. During the first sub-ns PEX startup, local VDD
taps are not yet at 1.8 V and PFET `VBS` reaches −0.611637 V in FF. One FF
`00→00` case was rerun with operating-point initialization: its full-waveform
PEX PFET `VBS` was −0.077979 to +0.057088 V, and functional checks passed.
However, NFET `VGS` still reached −1.479475 V and PFET `VGS` +0.078286 V.
This single case supports the UIC-startup-artifact interpretation for the
large PFET `VBS` excursion, but it does not establish that result for every
address pair or corner.

The audit script, full FF/SS CSV/JSON, the one-case operating-point artifacts,
source/model hashes and reproduction instructions are documented in the
[signed-bias audit report](row_decoder_signed_bias_domain_audit_20261008.md).
No extraction was run; the audited PEX hash is unchanged. The complete
three-corner operating-point matrix has since been run on the available
machine, and the focused FF 0.5 ps refinement confirms the small baseline
screen excess is repeatable. The signed model-domain qualification remains
open pending authoritative interpretation of the signed `VGS` excursions
and the FF model warnings. See the [matrix and refinement report](row_decoder_opinit_matrix_20261008.md).

## 2026-10-08: complete operating-point decoder matrix

The complete 1 ps baseline/PEX matrix ran all 16 ordered address pairs at TT,
SS and FF (96 ngspice runs). Every logic/contract check passed, and no
ngspice log contains an Error line. TT and SS passed the 1.95 V terminal
screen in baseline and PEX. At FF, all 16 PEX cases passed; 10 of 16
schematic-baseline cases exceeded the magnitude screen, peaking at 1.954645 V
on VGD. The FF runner's nonzero exit reflects those screen findings; the
simulations themselves completed and had zero contract failures.

A 0.5 ps refinement reran the 10 affected FF transitions in both stages. The
same 10 baseline transitions remained above the screen (maximum 1.954674 V),
while all 10 PEX transitions passed (maximum 1.879681 V). The largest 1 ps to
0.5 ps change was 0.037 mV in baseline and 0.014 mV in PEX. For the worst
baseline sample, FF 11→00 on x1.m12 at 5.03325 ns, measured VGD was −1.954674 V;
A1B was −34.741 mV, N1 was 1.919933 V and EVAL_GND was 0.436868 V. The case
deck finishes the PCLK rise at 5.025 ns while A0/A1 remain high until 17.95 ns,
so this sample is near the start of evaluation rather than an address change.
It is a repeatable transient, not a functional decoder failure. Whether the
screen indicates an accepted model-domain or reliability issue requires
review with the model maintainer/advisors.

The post-startup signed-bias audit is now available for all three corners.
PEX VDS/VBS remained within the published ranges; signed VGS still falls
outside the published table under the audit's effective-source convention.
The schematic baseline PFET VBS also crosses its −0.10 V lower published
boundary at all three corners. These are conservative engineering screens,
not signoff findings.

The result roots retain the comparison CSVs, manifests, scripts, signed-bias
audits and waveform hashes. Raw waveforms and simulator logs remain local and
ignored by Git. No new PEX extraction was performed. See the [full report](row_decoder_opinit_matrix_20261008.md)
for per-corner numbers, device ranges, evidence links, commands and remaining
closure tasks.

## 2026-10-08: source review of signed bias ranges and FF model warnings

The source review distinguished model-validity ranges from reliability limits.
The public SKY130 reference labels its signed 1.8 V terminal ranges as the
voltages where the SPICE models are valid; it does not list a `VGD` range. The
ngspice 44.2 BSIM4 code confirms that it changes from `VGS`/`VBS` to
`VGD`/`VBD` when the polarity-normalized `VDS` reverses, which supports the
source-orientation reconstruction in the audit script.

The FF model logs say that `A2 > 1` is clamped to `A2=1` and `A1=0`. The
negative `Eta0`, `Pdibl1` and `Pdibl2` entries produce warnings without
parameter reassignment in those ngspice checks. Thus the FF simulations
completed without fatal errors, but they use the clamped `A2`/`A1` model values
and retain the other warned values. At the refined worst baseline `VGD` sample,
`x1.m12` has `VDS=+1.284323 V`, `VGS=−0.670351 V` and `VGD=−1.954674 V`;
the custom `|VGS|/|VGD|/|VDS| <= 1.95 V` screen finding is not itself a
published `VGD` limit. Signed off-state `VGS` and baseline PFET `VBS` findings
remain outside the documented signed model-validity intervals under the
audited convention, so model-owner/project acceptance and margin remain open.
The source references, exact distinctions and provenance are in the
[signed-bias audit](row_decoder_signed_bias_domain_audit_20261008.md). No
schematic or layout change and no new extraction resulted from this review.

## 2026-10-08: review correction and intrinsic-state probe

The [latest-analysis review](row_decoder_analysis_review_20261008.md) reproduced
all signed audit records and waveform/netlist/manifest provenance for 116
archived OP/refinement waveforms. All 15,312 archived functional checks are
PASS. Links to PDK/ngspice source were corrected to actual source-file lines;
historical result metadata and hashes were preserved.

The signed audit derives biases from external MOS subcircuit terminals; the
BSIM4 states use intrinsic nodes behind series/body resistance. A new FF
11-to-00 baseline probe at 0.5 ps saved intrinsic VGS/VDS/VBS for M12 and M1.
Its 104 functional checks pass and all original external traces are bitwise
identical. At the critical M12 sample, external/intrinsic VGS is
−0.670351/−0.674755 V. M1 minimum external/intrinsic VBS is
−0.141914/−0.120427 V. This preserves the model-domain concern while correcting
the claim that terminal-derived biases are exact intrinsic model biases.
Evidence is retained under
`sims/row_decoder/results/decoder_analysis_review_20261008/`.

Current-sizing capture/PCLK, noise/retention, load and additional PVT
characterization can proceed with model limitations recorded. Project model
acceptance gates final qualification, rather than all further simulations.
The three measured PVT points do not establish an exhaustive PVT grid, and
1-to-0.5 ps stability with Gear does not establish independence of other
methods/tolerances. The 1 ns output settling allowance also remains a bench
criterion, not an agreed CLK/PCLK/precharge integration deadline.

The fetched Danilo checkpoint `d7a6ebb` contains bitcell and eight-bit WL row
physical views, but explicitly invalidates the first 08/10 WL-load PVT due to
access-tap initialization. Its corrected latch-output (`.t0`) PVT and approved
row load remain the integration dependency. These remote owner files were
reviewed read-only; no merge or owner-source changes occurred. Decoder
schematic, layout and PEX remain unchanged, with no new extraction.

## 2026-10-08: corrected row Ceff and current capture-to-PCLK requalification

Danilo's remote `feat/sram-6t-cell` commit `95c23c0` adds a corrected
latch-output-initialized (`.t0`) eight-bit row capacitance table. It covers five
process corners, two supplies, three temperatures and both stored states; all
60 rows are marked PASS. The table was copied byte-for-byte to
[`sims/row_decoder/inputs/row_8_wl_pex_capacitance_latch_t0_requal_20261008.csv`](../sims/row_decoder/inputs/row_8_wl_pex_capacitance_latch_t0_requal_20261008.csv).
Its [provenance sidecar](../sims/row_decoder/inputs/row_8_wl_pex_capacitance_latch_t0_requal_20261008.provenance.json)
records the source commit, input SHA-256
`b1f7da873879c30228c183d99eae5aa5c6f19214d09cc03153ce817eb07e36ca`, row PEX
SHA-256 `160b65544e12481aa99b287329ef2798e80c184c8f91566a23177ed8f0fb2dd6`,
and the associated cell PEX/table hashes. The maximum **full-row** Ceff is
102.873935496 fF (FF, 1.62 V, −40 °C, stored state 0); the maximum paired
additional load with the selected cell already represented is 93.351918068 fF.

The capture runner now accepts an explicit WL capacitance, can check a full
60-case source table and hash, and records load/source provenance in each
manifest. It also parameterizes the output settling allowance and captured
clock falling edge. Defaults preserve the historical 17.4 fF and 1 ns
criterion. No schematic or layout changed.

The current decoder was freshly netlisted (SHA-256
`2c8e802f8a5392eb2680e67cd6381627f9a680f8972325296ead1c387955202d`). It
contains 29 decoder MOS devices plus four schematic WL buffers. The bench
models each WL's **full-row** value as a capacitor to VSS because bitcells are
not explicitly instantiated. It does not use the current decoder R-C PEX or a
distributed row net.

### Matched WL-load sensitivity at 1.25 ns

Two full 72-case runs used the same current netlist, 12 address transitions,
two Liberty DFF Q-load points, PWL address-Q arcs, ideal PCLK, 3 ns output
settling allowance, 250 ps internal-literal guard and TT/SS/FF device profiles.
Only the WL capacitance changed from 17.4 fF to the measured 102.873935496 fF.
Each row below reports the largest WL90 delay among 24 cases per profile.

| Profile | Functional checks | Custom voltage screen | Maximum WL90 at 17.4 fF | Maximum WL90 at 102.874 fF |
|---|---:|---:|---:|---:|
| TT, 1.80 V, 27 °C | 24/24 | 4/24 | 0.449299 ns | 1.908236 ns |
| SS, 1.62 V, −40 °C | 24/24 | 24/24 | 0.665397 ns | 2.883215 ns |
| FF, 1.80 V, 125 °C | 24/24 | 0/24 | 0.389122 ns | 1.623869 ns |
| **Total** | **72/72 each** | **28/72 each** | | |

Across 72 exact pairs, increasing the load adds 1.235–2.218 ns to WL90 delay
(mean 1.637 ns), or 4.17–4.37× (mean 4.27×). A reproducible graphic is at
[`docs/assets/row_decoder_wl_load_capture_delay_20261008.svg`](assets/row_decoder_wl_load_capture_delay_20261008.svg),
generated by [`plot_capture_wl_load_sensitivity.py`](../sims/row_decoder/plot_capture_wl_load_sensitivity.py).

### Capture phase at the measured row load

At both 1.25 and 1.50 ns capture-to-PCLK, all 72 cases pass waveform logic and
the experimental 250 ps latest-literal guard. The custom 1.95 V terminal
magnitude/model-envelope screen passes only 28/72 (TT 4/24, SS 24/24, FF
0/24); the largest magnitude is 1.966736 V in FF. This screen is diagnostic,
not a formal reliability limit, and the model-domain review remains open.

| Capture-to-PCLK | PCLK high phase | Logic checks | Minimum literal lead | Margin beyond guard | Voltage screen | Maximum WL90 |
|---:|---:|---:|---:|---:|---:|---:|
| 1.25 ns | 3.75 ns | 72/72 | 286.518 ps | 36.518 ps | 28/72 | 2.883215 ns |
| 1.50 ns | 3.50 ns | 72/72 | 536.518 ps | 286.518 ps | 28/72 | 2.883069 ns |

At 1.50 ns, the slowest selected WL reaches 90% VDD about 617 ps before the
ideal PCLK falling edge. This supports 1.50 ns as a provisional next-study
point, not as macro cycle time or Fmax. An initial run at the same load and
phase with the old 1 ns settling allowance passed 0/72 logic/settling checks;
the 3 ns exploratory allowance passed 72/72 while leaving the voltage-screen
count unchanged. Neither settling value is a project specification.

The older 2026-10-07 17.4 fF selected campaign has a different netlist hash, so
it remains historical and was not used to attribute the load delay change.
Detailed commands, manifests and limitations are in the
[current requalification report](row_decoder_capture_load_requalification_20261008.md).
All selected result manifests are complete with no simulator execution errors.
They retain per-case decks, check and terminal CSVs, summary CSVs, manifests
and executed runner sources. No new PEX extraction, DRC, LVS or layout change
was part of this work.

## 2026-10-09 UTC: combined decoder/WL-driver PEX capture-to-PCLK

The capture runner now has an opt-in `--post-layout-pex` mode. Before
simulation, it checks that the decoder PEX is current, verifies the WL-driver
PEX pin contract and MOS topology/sizing against both the current Xschem
netlist and the flat extracted netlist, checks for nonnegative capacitors, and
records all source hashes. It preserves the WL driver's differing Xschem and
Magic pin orders without changing top-level instances or source schematics.

The complete 72-case selected matrix uses current decoder PEX (29 MOS, 762 R,
389 C), four WL-driver PEX instances (4 MOS, 99 R, 43 C each), the 102.873935496
fF full-row Ceff as a separate lumped load per WL, 12 address transitions, two
Liberty DFF Q-load points, TT/SS/FF profiles, 1.50 ns capture-to-PCLK, 3 ns
settling screen and 250 ps literal guard. All 72 ngspice runs completed with
return code zero. TT and FF each pass 24/24 functional and timing screens. SS
passes its separate 1.95 V magnitude screen in 24/24 cases, but has 0/24
functional/timing passes and only 2/24 literal leads at or above 250 ps. The
48 failed waveform checks are the selected WLs missing the 3 ns settling
criterion, two checks in each SS case. The worst SS WL90 is 3.262722 ns,
0.379652 ns slower than the matched schematic-only case; the worst literal
lead is −279.707 ps. The voltage screen is diagnostic, not model/reliability
signoff.

A follow-up two-transition SS/stress pilot at 2.10 ns capture-to-PCLK, a 20.70
ns falling edge and 3.3 ns settling screen passed 160/160 checks in each case,
with approximately 448 ps literal lead and 3.23 ns WL90. This extends the
clock high window and changes an experimental settling parameter; it is not a
full matrix, approved clock setting, or frequency result.

The full 24-case SS matrix was then run at 1.50, 1.80, 1.95 and 2.10 ns,
holding the ideal falling edge at 20.70 ns, the settling allowance at 3.3 ns,
the maximum row Ceff, all 12 address transitions and both Q-load points fixed.
Every phase completed 24/24 cases with zero ngspice errors and all 3,840
waveform checks passing per phase (15,360 checks across the four matrices). All
four points also pass the separate terminal-
magnitude diagnostic in 24/24 cases. The 250 ps literal guard passes 2/24,
13/24, 24/24 and 24/24 cases, respectively; the minimum lead is −279.707,
141.738, 291.738 and 441.738 ps. The maximum WL90 is 3.262722, 3.234038,
3.231437 and 3.230220 ns, respectively. Thus 1.95 ns is the earliest passing
sampled point for that experimental guard, not an approved PCLK interface or
frequency limit. The PCLK high phase varies from 4.20 to 3.60 ns across these
points because its falling edge remains fixed. Subtracting the maximum measured
WL90 from that phase gives 937.278, 665.962, 518.563 and 369.780 ps before
the ideal fall, respectively. This derived interval shows the tradeoff: moving
PCLK later improves literal lead but reduces the time left for the selected WL.

The [combined-PEX report](row_decoder_capture_combined_pex_20261009.md) records
the inputs, hashes, results, limitations and commands. Complete artifacts are
under:

- [`capture_combined_pex_wlcap102p874_p1500_s3ns_20261009`](../sims/row_decoder/results/capture_combined_pex_wlcap102p874_p1500_s3ns_20261009/)
- [`capture_combined_pex_phase2100_clk20700_s3p3ns_20261009`](../sims/row_decoder/results/capture_combined_pex_phase2100_clk20700_s3p3ns_20261009/)
- [`capture_combined_pex_slow_phase1500_clk20700_s3p3ns_20261009`](../sims/row_decoder/results/capture_combined_pex_slow_phase1500_clk20700_s3p3ns_20261009/)
- [`capture_combined_pex_slow_phase1800_clk20700_s3p3ns_20261009`](../sims/row_decoder/results/capture_combined_pex_slow_phase1800_clk20700_s3p3ns_20261009/)
- [`capture_combined_pex_slow_phase1950_clk20700_s3p3ns_20261009`](../sims/row_decoder/results/capture_combined_pex_slow_phase1950_clk20700_s3p3ns_20261009/)
- [`capture_combined_pex_slow_phase2100_clk20700_s3p3ns_20261009`](../sims/row_decoder/results/capture_combined_pex_slow_phase2100_clk20700_s3p3ns_20261009/)

The phase plot is generated by
[`plot_combined_pex_phase_sweep.py`](../sims/row_decoder/plot_combined_pex_phase_sweep.py)
and saved as
[`row_decoder_combined_pex_phase_sweep_20261009.svg`](assets/row_decoder_combined_pex_phase_sweep_20261009.svg).

No new extraction, DRC, LVS, schematic edit or layout edit was performed. The
physical row is still represented by lumped Ceff, and actual PCLK generation,
external setup/hold and accepted timing limits remain open.

## 2026-10-09: current-sizing dynamic-decoder hold and phase screens

The current 29-MOS decoder netlist was freshly generated and used for four
schematic-level campaigns: 36 finite-hold, 42 charge-injection, 168 low-phase,
and 168 high-phase cases, each across TT, SS and FF. All manifests completed
with the same current netlist hash. All 36 finite holds passed at 10, 100 and
1000 ns; charge up to 4 fC passed all sampled cases, while 4 of 6 cases at 8 fC
were tagged `REJECTED_PERTURBATION`. The minimum sampled phase durations passing
all rows were 0.4/0.6/0.4 ns low and 0.5/0.75/0.5 ns high for TT/SS/FF. These are
exploratory bounds for the 17.4 fF bench load and 50 ps PCLK/address edges;
they do not establish a noise budget, clock-stop limit, safe period or Fmax.
See the [current-sizing report](row_decoder_current_sizing_contract_20261009.md)
and its per-case summaries/manifests. Broader crossed-PVT and actual-PCLK
integration remain open.

## 2026-10-09 UTC: decoder, WL-driver and distributed physical-row PEX screen

The selected-row screen now instantiates the current decoder R-C PEX, four
current WL-driver R-C PEX instances, and four copies of the extracted physical
eight-bit row from Danilo's `feat/sram-6t-cell` commit
`95c23c03ddc29f0d4bf40adf5fe7adb1b4af0a6a`. The row PEX was copied byte-for-byte
to the Person 3 test inputs; its SHA-256 is
`160b65544e12481aa99b287329ef2798e80c184c8f91566a23177ed8f0fb2dd6` (48 MOS,
786 resistors, 349 capacitors per row). Source branch files were not changed,
and no extraction was run.

The 12-case matrix selects each of the four rows once in TT/1.80 V/27 °C,
SS/1.62 V/−40 °C and FF/1.80 V/125 °C. With a 5 ps maximum transient step,
all 4,992 decoder-output and distributed row-tap checks pass. The selected-row
WL90 range across the 16 physical taps is 2.142–2.149 ns (TT), 3.221–3.224 ns
(SS), and 1.834–1.840 ns (FF). A targeted 1 ps rerun of SS, row 3, passes 416
checks and measures 3.224141–3.224215 ns; it is 0.131 ps below the 5 ps
maximum and leaves 75.785 ps before the exploratory 3.3 ns settling screen.
The latter is not an approved SRAM timing requirement or margin.

The test shares all eight BL/BLB pairs among the rows and clamps each line to
ideal VDD for the complete transient. It therefore screens selected WL assertion,
unselected-row isolation and recovery through the distributed row model; it
does not model release of bitline precharge for evaluation, precharge/equalizer
devices, sense amplification, write drive, or stored-data readback. The PCLK
and the address capture phase are idealized bench inputs. Bitcell-row device
terminal model-domain limits are not qualified. These results are physical
row-load path evidence, not full 4×8 read/write or timing closure.

The copied PEX and source commit/hash are recorded in
[`row_8_wl_pex_95c23c0.provenance.json`](../sims/row_decoder/inputs/row_8_wl_pex_95c23c0.provenance.json).
There is also an unresolved row-Ceff discrepancy: the `.t0` table records
102.873935496 fF full-row Ceff, while the detailed bitcell report gives
98.914001 fF; both associate their data with the same row PEX hash. The
distributed simulation uses the PEX directly and does not adjudicate those
measurements. Reconcile with the bitcell owner before treating either as the
official lumped integration load. See the
[distributed-row report](row_decoder_distributed_row_pex_20261009.md).

Reproduction commands:

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
```

The manifests, per-case decks, checks, sampled WL taps and terminal traces are
under the two output directories above. No schematic, owner source, layout,
DRC/LVS result or PEX extraction was changed or regenerated for this campaign.

## 2026-10-09 UTC: full physical-row address and access-control matrices

The dynamic 2-to-4 decoder on `feature/peripherals` remains Leonardo's Person
3 Phase 1 deliverable. It will be completed through characterization, layout,
DRC and LVS. A separate SPICE candidate on Danilo's branch does not replace or
reassign this decoder. Danilo's physical-row PEX was consumed as a read-only
input; his source branch was not modified.

The distributed-row runner was extended to accept same-address pairs and to
exercise all **16 ordered old/new address combinations**. The full physical
matrix used decoder and four WL-driver PEX instances, four extracted eight-bit
row PEX instances, TT/SS/FF, nominal Liberty Q load, 1.950 ns capture-to-PCLK,
20.700 ns CLK falling edge, a 3.3 ns exploratory settling screen and a 5 ps
maximum transient step. It completed **48/48 cases** and **19,968/19,968
checks**, with no rejected cases. The observed WL90 ranges across all physical
row taps and old-address values were 2.142469–2.150495 ns in TT,
3.220558–3.228800 ns in SS, and 1.833842–1.841717 ns in FF. The slowest point
was SS, address `1→2`, at 3.228800 ns, 71.2 ps below the experimental 3.3 ns
screen. This is not an approved system timing limit.

A separate physical-row access-policy matrix covered all eight static
`CSb/OEb/WEb` vectors at address `2→2` in all three profiles. It completed
**24/24 cases and 3,882/3,882 checks**. `001` (read) and `010` (write) both
evaluate row 2. `000` (invalid), `011` (idle), and all four `1XX` disabled
vectors keep PCLK low and pass checks for precharged internal nodes, inactive
DEC/WL outputs, and all 64 physical-row taps. Each denied vector/corner case
contributes 77 checks. The valid-control SS WL90 maximum is 3.223037 ns.

This access-policy screen maps a static truth-table vector to an ideal PCLK
source in the testbench. It does not instantiate the control block, capture
the control inputs, or model a physical PCLK generator. BL/BLB are clamped to
ideal VDD throughout both matrices, so neither matrix verifies bitcell read,
write, precharge release, sense amplification, or data readback. The row-Ceff
discrepancy between the `.t0` input table and the detailed bitcell report is
still open for owner reconciliation.

The access run completed every ngspice case, but its initial final-summary
writer rejected the mixed result columns from selected and denied accesses.
The per-case passing results were preserved; summary/check artifacts and the
manifest were reconstructed from those outputs without rerunning simulations.
The runner now writes union columns, and the fix passed a mixed two-case TT
smoke (`000` denied, `001` read): 2/2 cases and 493/493 checks passed. The
recoverable manifest records this summary repair. The generated all-transition
plot is `docs/assets/row_decoder_distributed_row_full_transition_pex_20261009.svg`.

Reproduction commands and the complete limitations are in the
[distributed-row report](row_decoder_distributed_row_pex_20261009.md). The
full simulation artifacts are under
[`distributed_row_pex_full_transition_matrix_20261009`](../sims/row_decoder/results/distributed_row_pex_full_transition_matrix_20261009/manifest.json)
and
[`distributed_row_pex_access_control_matrix_20261009`](../sims/row_decoder/results/distributed_row_pex_access_control_matrix_20261009/manifest.json).

## 2026-10-09 UTC: row-Ceff source alignment with the current owner closure

The earlier distributed-row entry recorded the Ceff interpretation as open at
the time of that simulation. Reviewing Danilo's latest owner closure available
on `origin/feat/sram-6t-cell` at commit `5dc00fe` resolves how the values apply:
the current `.t0` row table reports a full-row range of
`102.328671–102.873935496 fF` and a maximum paired `CWL_EXTRA` of
`93.351918068 fF`. The `98.914001 fF` full-row and `89.925201 fF` extra values
are retained in his material as superseded 07/10 history.

The Person 3 lumped capture and WL-leaf benches do not instantiate the row's
bitcells, so their full-row load of `102.873935496 fF` is the applicable value.
If the selected bitcell is explicitly included, use the paired extra load of
`93.351918068 fF`. The distributed-row matrix instantiates the extracted row
PEX and adds no lumped row capacitance. Therefore, no electrical result needed
to be rerun for this source clarification. Existing result manifests remain
unchanged as snapshots of what was known when those runs were recorded. No
Danilo-owned source files were modified.

## 2026-10-09 UTC: precharge and PCLK integration readiness

A read-only check of `origin/feature/sense-precharge` found only `.gitkeep`
placeholders under `cells/precharge/` and `sims/precharge/`; the branch has no
review-ready precharge/equalization schematic, netlist, or physical view to
integrate. The precharge draft currently present on `feature/peripherals` is
owned by André and remains unchanged. Its prior Xschem netlisting attempt,
recorded above, stopped before ngspice with open nets, BL/BLB/PRECH shorts and
disconnected MOS devices.

No transistor-level PCLK qualifier/generator is present under `cells/`; the
decoder matrices continue to use ideal PCLK sources. Therefore the next
decoder-to-bitline electrical test requires the owner-reviewed precharge
interface and an agreed PCLK/access-enable source. No new electrical
simulation was run in this readiness audit, and no other owner's files were
changed.

## 2026-10-09 UTC: read-only precharge netlist review and proposed PCLK phases

The current `cells/precharge/precharge.sch` was netlisted read-only in the
SKY130A Xschem container using `xschem -n -q -s`. The generated
`precharge_review.spice` has an empty `.subckt precharge` port list and three
PMOS instances whose twelve terminals map to separate anonymous nets. Source
inspection also confirms the drawn `BL`, `BLB`, and `PRECH` wires share the
`(450,-160)` junction. The source hash remains
`2331e0e438d037c62cc6e47498c7c89bec0fdecf06c4da8c39869e40da031f04`; André's
schematic was not changed and is not ready for integrated simulation.

The proposed interface keeps decoder `PCLK` (low=dynamic-node precharge,
high=evaluation) separate from active-low bitline `PRECH` (low=precharge on).
For valid accesses, release bitline precharge after capture, raise decoder PCLK
only after a characterized address/data settling guard, and reassert bitline
precharge only after decoder evaluation has stopped and wordlines have fallen.
For idle, disabled, and invalid accesses, keep both controls low. The timing
proposal and its PVT/PEX limits are recorded in the
[precharge/PCLK review](precharge_pclk_interface_review_20261009.md). No
electrical simulation was run because the current precharge netlist is
disconnected.

## 2026-10-09 UTC: cross-branch correction — Danilo's precharge candidate

The readiness review above checked `origin/feature/sense-precharge` and the
older precharge source on `feature/peripherals`, but did not check Danilo's
`origin/feat/sram-6t-cell` branch. That branch contains a corrected
`cells/precharge.sch` and `cells/precharge.spice`; a read-only Xschem netlist of
a temporary copy produced a connected three-PMOS subcircuit with formal
`VDD`, `BL`, `BLB`, `PRECH`, and `VSS` ports. The branch also contains the
physical `Wpre=2.52 µm` candidate, PEX, and the G6/G7 results summarized in
`docs/phase1_leaf_cell_closure.md`: DRC zero, unique LVS, precharge Ceff PVT
`60/60`, and integrated PEX read/write `60/60` each. These are Danilo's
recorded branch results, not checks rerun here.

The corrected candidate is not in `origin/develop` or `feature/peripherals`;
the branch tip `5dc00fe` is not an ancestor of `origin/develop`. The previous
netlist finding applies to the older copy in this checkout and remains true,
but the statement that the cell must be corrected from scratch is withdrawn.
Coordinate with André to review and select Danilo's candidate for the shared
precharge interface. The candidate still has no actual PCLK phase generator
for the dynamic decoder on `feature/peripherals`. See the updated
[precharge/PCLK review](precharge_pclk_interface_review_20261009.md).

## 2026-10-09 UTC: decoder/WL/precharge phase-interface PEX screen

To continue Person 3's dynamic-decoder integration without changing either
owner's source, Danilo's `precharge_w2p52_flat` PEX was copied byte-for-byte
from `origin/feat/sram-6t-cell` commit `5dc00fe02e43492267516c3e448e935456406a1d`
into `sims/row_decoder/inputs/`. SHA-256 is
`cf0fa457b4ab84a1d19e6202541b6a43149b575e492a108e36d0de62489cc423`.
Its interface is `VDD BL BLB PRECH VSS`, with three PFETs, 20 resistors and
30 capacitors; `PRECH` is active low. Its source revision and Danilo-reported
DRC/LVS/Ceff evidence are kept in the
[provenance sidecar](../sims/row_decoder/inputs/precharge_w2p52_pex_5dc00fe.provenance.json).
His physical validation is cited, not rerun here.

The new runner freshly netlists the current decoder and combines its PEX with
four wordline-driver PEXs and eight instances of Danilo's precharge PEX. It
uses the current `102.873935496 fF` full-row WL load. Each bitline combines the
precharge leaf with a `583.992055 fF` lumped external residual to represent the
`597.056241 fF` target after subtracting the owner-reported maximum leaf Ceff
of `13.064186 fF`. This equivalent load is approximate and is not a distributed
physical bitline model.

The stimuli are ideal PWL waveforms: decoder PCLK is released for evaluation,
and active-low bitline PRECH is released before evaluation then reasserted
after the PCLK falling edge. With a 250 ps nominal PRECH release lead, a 1.8 ns
nominal post-fall guard, 50 ps ramps and a 5 ps maximum transient step, the
final campaigns passed **26/26 ngspice cases**, **4,660/4,660 detailed
checks**, and **1,460/1,460 phase checks**:

- TT valid read/write transitions: 8/8 cases;
- TT invalid/idle/disabled controls: 6/6 cases;
- SS, 1.62 V/−40 °C, selected transitions: 4/4 cases;
- FF, 1.80 V/125 °C, all four target rows: 8/8 cases.

At the 10% VDD wordline-off and 75% VDD precharge-threshold definitions, the
smallest selected-WL-off margin was `254.477 ps` in the SS cases. The minimum
sampled bitline voltage before valid evaluation was `1.619687 V` at 1.62 V,
above the test's 90% VDD screen. These are bounded simulation results, not
silicon guarantees or approved timing limits.

Exploratory failures are retained as evidence for the guard choice. A TT
500 ps pilot reasserted PRECH while the selected WL was still active by
`637.466 ps`; an SS 1.5 ns pilot missed the WL-off screen by `52.963 ps` and
its initial precharge ended below the 90% VDD bitline threshold. The final
campaign uses 1.8 ns and a longer startup-conditioning interval. That setting
is not asserted to be optimal or sufficient for untested conditions.

The result is limited to phase sequencing, decoder/WL response and bitline
restoration. There is no transistor-level PCLK/PRECH generator, captured
control circuit, 6T access path, sense amplifier, write operation or data
readback. TT/FF cover four 0→row transitions, SS covers two selected
transitions, and no fully crossed PVT/mismatch campaign was run. No new layout,
DRC, LVS or extraction was run. The older `cells/precharge/precharge.sch`,
Danilo's source and André's source remain unchanged; the test copy does not
establish the team's shared precharge revision.

The reproducible runner and plotting script are
[`run_precharge_phase_interface.py`](../sims/row_decoder/run_precharge_phase_interface.py)
and
[`plot_precharge_phase_interface.py`](../sims/row_decoder/plot_precharge_phase_interface.py).
The [phase-interface report](row_decoder_precharge_phase_integration_20261009.md)
contains exact commands, matrix links, waveform evidence and limitations. The
figure is
[`row_decoder_precharge_phase_sequence_20261009.svg`](assets/row_decoder_precharge_phase_sequence_20261009.svg).

## 2026-10-09 UTC: initial 2.10 ns precharge/PCLK phase candidate

Person 3's decoder integration uses Danilo's W2.52 precharge PEX. The 2.10 ns
point was selected by comparing measured timing slacks across the sampled
phase points. Its smaller slack is 191.738 ps after the experimental 250 ps
literal guard, versus 41.738 ps at 1.95 ns. This is an experimental maximin
choice, not a timing requirement or operating-frequency claim.

The full decoder/WL/precharge PEX interface matrix was rerun at 2.10 ns, with
Danilo's pinned W2.52 PEX, an ideal 20.70 ns PCLK falling edge, 3.3 ns settling
allowance, 250 ps nominal PRECH release lead, 1.80 ns nominal post-fall guard,
and 5 ps maximum transient step. It completed 26/26 cases, 4,660/4,660
detailed checks and 1,460/1,460 phase checks. The slow-profile minimum
selected-WL-off interval before PRECH conduction remained 254.477 ps. The
observed release lead and post-fall intervals were 237.5 ps and 1,787.5 ps,
respectively. Minimum bitline voltage before valid evaluation was 1.545430 V
at 1.62 V, above the bench's 90%-VDD threshold of 1.458 V.

Campaign manifests:

- [`precharge_phase_interface_tt_valid_phase2100_20261009`](../sims/row_decoder/results/precharge_phase_interface_tt_valid_phase2100_20261009/manifest.json)
- [`precharge_phase_interface_invalid_tt_phase2100_20261009`](../sims/row_decoder/results/precharge_phase_interface_invalid_tt_phase2100_20261009/manifest.json)
- [`precharge_phase_interface_slow_phase2100_20261009`](../sims/row_decoder/results/precharge_phase_interface_slow_phase2100_20261009/manifest.json)
- [`precharge_phase_interface_ff_phase2100_20261009`](../sims/row_decoder/results/precharge_phase_interface_ff_phase2100_20261009/manifest.json)

The exact selection, phase interface, provenance and limitations are in the
[phase decision report](row_decoder_precharge_pclk_decision_20261009.md).
PCLK and PRECH are still ideal bench stimuli: this run does not qualify a real
phase generator or include captured-control devices, a 6T access path, read or
write behavior, or data readback. No new extraction, layout, DRC or LVS was
performed.

## 2026-10-09 UTC: correction to PRECH access-release timing

Review of `run_precharge_phase_interface.py` found that the first interface
campaign set the access-cycle PRECH release to the 15 ns capture edge. At a
17.1 ns PCLK evaluation edge, that provided about 2.09 ns lead; the 237.5 ps
measured release lead applied only to the initial conditioning pulse. The
earlier 26-case result did pass for the waveform it simulated, but it does not
verify the intended 250 ps access lead. The same scheduling issue affected the
earlier 1.95 ns phase-interface report. Those result directories remain
unchanged as historical records and are superseded for phase-ordering claims.

The runner now releases PRECH 250 ps nominally before each PCLK rising edge.
The corrected 2.10 ns matrix was rerun against the same pinned Danilo W2.52
precharge PEX and current decoder/WL PEX:

- TT valid read/write: 8/8 cases, 1,792/1,792 checks;
- TT invalid/idle/disabled: 6/6 cases, 180/180 checks;
- slow profile: 4/4 cases, 896/896 checks;
- fast profile: 8/8 cases, 1,792/1,792 checks;
- total: 26/26 cases, 4,660/4,660 checks and 1,460/1,460 phase checks.

The corrected access release lead measures 237.5 ps after accounting for the
50 ps PRECH ramp. The minimum selected-WL-off interval before the conservative
75%-VDD precharge threshold is 262.786 ps in the slow-profile cases. Minimum
sampled bitline voltage before evaluation is 1.624086 V at 1.62 V, above the
1.458 V screen. These remain bounded ideal-source interface results; they do
not validate a physical phase generator or bitcell access path.

Corrected results and reproduction commands:

- [phase decision and waveform](row_decoder_precharge_pclk_decision_20261009.md)
- [corrected TT valid matrix](../sims/row_decoder/results/precharge_phase_interface_tt_valid_phase2100_release250_20261009/manifest.json)
- [corrected TT invalid matrix](../sims/row_decoder/results/precharge_phase_interface_invalid_tt_phase2100_release250_20261009/manifest.json)
- [corrected slow matrix](../sims/row_decoder/results/precharge_phase_interface_slow_phase2100_release250_20261009/manifest.json)
- [corrected fast matrix](../sims/row_decoder/results/precharge_phase_interface_ff_phase2100_release250_20261009/manifest.json)

## 2026-10-09 UTC: transistor-level PCLK/PRECH phase-chain candidate

The phase-interface runner now has an experimental `tapped-delay-chain`
source. It builds a shared 80-stage SKY130A inverter chain in the SPICE deck,
with taps at 24, 60, and 80 stages. The generated logic follows
`PCLK = VALID_ACCESS_Q AND CLK AND DLY60` and
`PRECH = VALID_ACCESS_Q AND ((CLK AND DLY24) OR DLY80)`. This delays evaluation
after the captured access edge and holds bitline precharge released until the
decoder evaluation and selected wordline have turned off. The proposed
implementation path remains captured, glitch-free access qualification from
`CLK` and registered controls, followed by separate non-overlapping `PCLK`
and active-low `PRECH` outputs. The tapped chain is a simulation candidate for
that path, not a finalized circuit choice.

The valid qualifier and external `CLK` are still ideal PWL sources in this
bench. The qualifier rises at the nominal capture edge; its actual capture
and glitch suppression are not transistor-level. The runner's phase generator
is not yet an Xschem cell and has no layout, DRC/LVS, or PEX. This candidate
therefore provides measured phase behavior for the decoder/WL/precharge
interface, not physical phase-source signoff or a supported frequency.

Four fresh PVT campaigns completed **26/26 cases and 3,540/3,540 checks**:
TT valid read/write (8 cases), TT invalid/idle (6), SS at 1.62 V/−40 °C
(4 selected transitions), and FF at 1.80 V/125 °C (8). The 980 phase checks
and 2,560 decoder checks all passed. The minimum measured interval from the
selected WL falling below 10% VDD to PRECH reaching the conservative 75% VDD
conduction threshold is 637.024 ps in FF. The minimum bitline sample before
evaluation is 1.624971 V in SS, above the test's 90% VDD screen. These sampled
checks do not establish an approved timing guard or clock period.

The nominal ideal-source targets of 250 ps PRECH release lead and 1.80 ns
PCLK-fall-to-precharge delay are not enforced by the transistor chain. Measured
release lead ranges from 168.051 ps (FF) to 444.348 ps (SS); measured
PCLK-fall-to-precharge intervals range from 1.694 ns (FF) to 2.979 ns (SS).
The measured selected-WL-off clearance is positive in every valid case, with
the 637.024 ps minimum above. The maximum absolute decoder terminal voltage is
1.867033 V, below the project's 1.95 V numerical screen only; this is not a
reliability or model-domain signoff.

The detailed method, exact commands, pinned Danilo W2.52 PEX provenance,
waveform and limitations are in the
[phase-chain candidate report](row_decoder_tapped_phase_generator_screen_20261009.md).
The four manifests are linked there. The representative waveform is
[`row_decoder_precharge_phase_chain_20261009.png`](assets/row_decoder_precharge_phase_chain_20261009.png).
No extraction was run for this phase-source candidate.

## 2026-10-09 UTC: phase-delay sizing and qualifier-arrival sensitivity

The 80 phase-chain inverters in the checked-in hierarchical Xschem phase-source
cell were screened at six PFET/NFET sizing pairs.
`Wp=1.26 µm`, `Wn=0.42 µm`, `L=0.15 µm`, `nf=1` gave the largest minimum
PRECH-release and WL-off timing margins in that sample and passed the selected
26-case decoder/precharge matrix. This is a provisional schematic-level size,
not a physical phase-cell signoff. See the [sizing comparison](phase_delay_inverter_sizing_screen_20261009.md).

A follow-up arrival-skew campaign used the same current PEX and Xschem phase
source, with an ideal PWL `VALID_ACCESS_Q` edge delayed by 0, 900, 1,000 or
1,250 ps after the CLK capture edge. For the sampled 0→3 read transition, 0
and 900 ps pass across TT, SS and FF; the 1,000 ps FF case measures a 230.525
ps release lead and fails the configured 250 ps experimental guard. At
1,250 ps, TT and FF fail that guard, while SS passes. All decoder logic and
voltage screens pass in these cases.

This campaign exposed a checker gap: transistor-level phase-source cases had
been required only to release PRECH before PCLK, even though the selected
interface target was 250 ps. The runner now enforces the measured 250 ps lead
between PRECH rising through 75% VDD and PCLK rising through 50% VDD for
transistor-level phase-source modes. The previous unguarded arrival-skew
directories are retained as exploratory history and superseded by the
`phase_source_valid_access_q_guard250_*` directories.

The qualifier edge is still an ideal PWL input; this does not verify captured
control logic, address/control setup and hold, write data, metastability,
glitch suppression or a legal SRAM frequency. The 900 ps point is a
provisional implementation target only. Phase-source layout, DRC/LVS and PEX
remain pending; no extraction was run. Full results, per-case manifests,
reproduction commands and a margin plot are in the
[arrival-skew report](row_decoder_valid_access_arrival_skew_20261009.md).

## 2026-10-09 UTC: Liberty-timed captured VALID_ACCESS_Q screen

The direct `dfxtp_1` SPICE attempt archived under
`capture_to_pclk_smoke2` failed model resolution at an internal `special_nfet`
with `could not find a valid modelname`. The cell uses four 0.36 µm NFETs at
`L=0.15 µm`, but the continuous `sky130.lib.spice` `nshort_model` bins used by
this deck start at 0.42 µm for that channel-length range. The PDK's separate
TT PM3 device model includes a 0.36–0.39 µm bin; these model-file families are
not interchangeable. A temporary 0.42 µm width substitution let ngspice
complete, confirming the bin boundary as the failure cause, but changes the
standard-cell geometry and is not accepted as a cell simulation.

To preserve the current continuous model on the custom decoder and phase
source, `run_precharge_phase_interface.py` now supports
`--valid-access-q-model dfxtp_1-liberty`. This builds the `VALID_ACCESS_Q` PWL
rise from the selected profile's `dfxtp_1` Liberty clock-to-Q and rise
transition tables. Its nominal table point uses a 53.1329 ps clock slew and a
3.434554 fF output load. It represents the captured valid bit's output timing;
the DFF transistor circuit, control-qualification logic, input setup/hold,
metastability and glitches are not simulated.

The selected 0→3 address transition passed for read (`001`) and write (`010`)
in TT, SS and FF: **6/6 cases, 1,008/1,008 checks**. Liberty clock-to-Q rise
delays were 307.041 ps (TT), 677.087 ps (SS) and 248.733 ps (FF). The minimum
measured PRECH release lead was 334.158 ps in FF, above the 250 ps experimental
guard. This is one address transition with the existing 102.873935496 fF WL
load, 2.10 ns phase candidate, 22 ns CLK falling edge and 3.4 ns settling
window. It does not close full control capture, invalid-vector suppression in
this mode across the full control/PVT matrix, next-cycle qualifier
deassertion, physical bitcell access, setup/hold, or a legal clock window or
frequency. No extraction was run.

A separate `000` invalid-control test in TT passed **30/30 checks**. PCLK,
decoder outputs and wordlines remained inactive; internal dynamic nodes and all
bitlines remained precharged. This is representative evidence only; the other
invalid vectors and corners have not yet been rerun in Liberty mode.

Evidence, exact reproduction command and limitations are in the
[captured-Q Liberty report](row_decoder_valid_access_q_liberty_screen_20261009.md).
Machine-readable results are in
[`summary.csv`](../sims/row_decoder/results/phase_source_valid_access_q_liberty_dfxtp1_20261009/summary.csv),
[`checks.csv`](../sims/row_decoder/results/phase_source_valid_access_q_liberty_dfxtp1_20261009/checks.csv),
and the [manifest](../sims/row_decoder/results/phase_source_valid_access_q_liberty_dfxtp1_20261009/manifest.json). The
representative [invalid-vector checks](../sims/row_decoder/results/phase_source_valid_access_q_liberty_dfxtp1_invalid_tt_20261009/checks.csv)
are archived separately.

## 2026-10-09 UTC: captured valid-access qualifier functional check

Added `cells/control/valid_access_capture.sch`, a SKY130 FD SC HD standard-cell
implementation of `VALID_ACCESS_D = !CSb AND (OEb XOR WEb)`, captured by a
positive-edge `dfxtp_1`. The equation enables a selected read or write, while
rejecting idle, simultaneous read/write, and all chip-disabled vectors. No
reset is present; Q is undefined before the first rising edge. Address and
write-data capture are not part of this cell.

The Xschem structural Verilog was checked with the PDK functional models in
Icarus. All eight control vectors were captured correctly at the rising edge;
eight checks retained Q after live controls changed during the high phase, and
eight checks retained Q across the falling edge. Result: **8/8 captures and
16/16 hold checks passed**. Xschem also generated the structural netlist without
missing symbols. The new `captured_pclk_phase_source.sch` wrapper netlists the
qualifier to the existing `pclk_phase_source.sch` hierarchy without modifying
the phase source.

Reproduce with `./tools/sram-eda python3 sims/row_decoder/run_valid_access_capture.py`.
The testbench, runner, manifest, vectors, VCD, netlists and tool logs are under
[`sims/row_decoder/results/valid_access_capture_integrated_20261009T213300994820Z/`](../sims/row_decoder/results/valid_access_capture_integrated_20261009T213300994820Z/);
the [report](row_decoder_valid_access_capture_20261009.md) records the control
truth table, schematic image, commands and limits.

This is a zero-delay Boolean/edge-functional check, not an analog standard-cell
timing simulation. The wrapper was netlisted but not simulated as a complete
qualifier-to-PCLK/PRECH electrical path. Existing phase timing matrices still
use ideal or Liberty-derived `VALID_ACCESS_Q`; their delay results do not
measure this new gate/DFF path. Setup/hold, metastability, startup before the
first clock, PVT timing, address/data capture, layout, DRC/LVS, and integrated
bitcell read/write/readback remain open. No extraction was run.
