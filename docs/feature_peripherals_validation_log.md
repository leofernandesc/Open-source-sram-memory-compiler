# Person 3 peripheral validation log

- Date: 2026-10-08
- Branch: `feature/peripherals`

Current decoder status on compact commit `d20f509`: routed/flat DRC is 0/0,
LVS is unique, and the current PEX has 762 R / 389 C across all 22 resistance
networks. The matched 13-case schematic/PEX matrix passes at both 5 ps and
1 ps. See the [compact-layout extraction entry](#2026-10-08-compact-decoder-r-c-extraction-and-electrical-checks)
for measured results and remaining limits. The 7ad0348 PEX and its matrix are
historical for the previous geometry.

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

The transient smoke runner netlists the current Xschem schematic, checks its
pin/device contract, and applies these output-level criteria:

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
