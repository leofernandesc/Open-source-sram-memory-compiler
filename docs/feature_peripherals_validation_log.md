# Person 3 peripheral validation log

- Date: 2026-10-06
- Branch: `feature/peripherals`

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

The active container image is `isaiassh/unic-cass-tools:1.0.7`; the bitcell
status note mentions `1.1.0`. The local executable and PDK checks passed, so the
container was not replaced.

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
