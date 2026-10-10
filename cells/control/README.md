# Phase-control cells

`pclk_phase_source.sch` is an experimental transistor-level source for the
dynamic row decoder's `PCLK` and the bitline precharge leaf's active-low
`PRECH` input. It belongs to the Person 3 peripheral integration work; it does
not modify the decoder, Danilo's bitcell, or the shared precharge source.

## Interface

| Pin | Direction | Meaning |
|---|---|---|
| `CLK` | input | SRAM clock |
| `VALID_ACCESS_Q` | input | Already captured and qualified read/write enable |
| `VDD`, `VSS` | supply | SKY130A 1.8 V core rails |
| `PCLK` | output | Dynamic decoder precharge/evaluate phase; low precharges |
| `PRECH` | output | Active-low bitline precharge/equalization enable |

The cell does **not** capture `CSb`, `OEb`, or `WEb`; it requires a stable,
glitch-free `VALID_ACCESS_Q` from upstream control capture. The older phase
interface runner models `CLK` and `VALID_ACCESS_Q` as ideal sources. A newer
paired screen composes the actual qualifier and phase cells under PEX loading;
neither runner is a complete SRAM control path.

## Captured access qualifier

`valid_access_capture.sch` implements the control condition with SKY130 FD SC
HD standard cells:

```text
VALID_ACCESS_D = !CSb AND (OEb XOR WEb)
VALID_ACCESS_Q = capture(VALID_ACCESS_D, rising edge of CLK)
```

This enables exactly one of read or write when `CSb` is active low, and rejects
idle, simultaneous read/write, and chip-disabled controls. It captures only the
qualified access bit; row-address capture is implemented separately, and
write-data capture remains outside these cells. The cell has no reset, so
`VALID_ACCESS_Q` is unspecified until the first rising clock edge.

`captured_pclk_phase_source.sch` hierarchically connects this qualifier to the
existing `pclk_phase_source.sch`; it leaves the phase-source implementation
unchanged. Reproduce the logic-only functional check with:

```bash
./tools/sram-eda python3 sims/row_decoder/run_valid_access_capture.py
```

The eight input vectors and edge/hold behavior pass using the PDK's functional
Verilog models. This is not an analog timing simulation of the standard-cell
path or a simulation of the assembled qualifier plus transistor-level phase
source. See the [captured qualifier report](../../docs/row_decoder_valid_access_capture_20261009.md)
for the evidence and remaining limits.

## Captured row-address interface

`row_address_capture.sch` uses two positive-edge `dfxtp_1` registers to
capture `A0` and `A1` and expose `A0_Q`/`A1_Q` to the dynamic decoder.
`captured_row_decoder_control.sch` groups these outputs with the existing
`VALID_ACCESS_Q`, `PCLK`, and active-low `PRECH` phase interface. It preserves
the decoder and phase-source leaf cells as separate hierarchy; the decoder and
physical row are not included in this wrapper.

The Xschem/functional screen checks all four address values, output hold after
live input changes, and the wrapper hierarchy: 4/4 captures, 8/8 hold checks,
and the expected subcircuit connections pass. A follow-up transistor-level TT
screen connects `A0_Q/A1_Q` through the current decoder and WL PEX with the
pinned precharge PEX. For valid read `001`, address `0→3`, all four sampled
address checks pass after capture and after the live inputs change; the paired
actual/reference run passes 350/350 checks. This is one setup point and one
nominal address transition, not a setup/hold or PVT qualification. Reproduce
the functional screen with:

```bash
./tools/sram-eda python3 sims/row_decoder/run_row_address_capture.py \
  --output-dir sims/row_decoder/results/row_address_capture_repro
```

The address inputs now have a separate isolated transistor-level setup/hold
screen: 168 points for A0/A1 rising/falling transitions across TT/SS/FF, with
114/114 Q checks passing where the measured margin is nonnegative against the
matching Liberty reference. These are sampled cell-level results, not timing
limits or signoff. Reproduce with:

```bash
./tools/sram-eda python3 sims/row_decoder/run_row_address_setup_hold.py \
  --output-dir sims/row_decoder/results/row_address_setup_hold_repro
```

The transistor-level PEX integration remains a single loaded nominal case.
Broader address/control transitions and corners, metastability, startup, and a
physical bitcell row remain open; see the [address-capture report](../../docs/row_decoder_address_capture_20261009.md)
and the [setup/hold report](../../docs/row_decoder_address_setup_hold_20261010.md).
The valid-access control input has a separate transistor-level setup/hold
screen; see the [report](../../docs/row_decoder_valid_access_setup_hold_20261009.md).

The isolated qualifier also has a transistor-level ngspice screen using the
official SKY130 FD SC HD SPICE subcircuits and the PDK native PM3 corner
library. Reproduce it with:

```bash
./tools/sram-eda python3 sims/row_decoder/run_valid_access_capture_spice.py
```

This screen passes the sampled control captures and holds in TT/SS/FF and
measures clock-to-Q threshold crossings. It logs missing OSDI library warnings
and observes Q excursions beyond VSS/VDD, which have no acceptance criterion
in this isolated test. It does not by itself establish setup/hold,
clock-frequency, reliability, or signoff limits. Results and per-run
provenance are in the [captured qualifier report](../../docs/row_decoder_valid_access_capture_20261009.md).

The composed `captured_pclk_phase_source.sch` hierarchy has a separate,
paired transistor-level interface screen:

```bash
./tools/sram-eda python3 sims/row_decoder/run_captured_phase_interface.py \
  --output-dir sims/row_decoder/results/captured_phase_interface_tt_read_repro
```

The earlier evidence covers one TT valid-read case and one TT invalid control
vector with decoder/WL and pinned precharge PEX loading: 342/342 and 66/66
checks. A later paired run uses `captured_row_decoder_control.sch`, so
transistor-level A0/A1 registers now feed the decoder PEX. The valid-read
`001`, address `0→3` pair passes 350/350 checks; the actual PCLK edge differs
by 1.117 ps from the Liberty-timed reference. These are bounded nominal
comparisons. The isolated address setup/hold screen is now complete, but
broader integrated control/address/corner coverage, startup, phase-source PEX,
and physical 6T read/write integration remain open. See the [address
setup/hold report](../../docs/row_decoder_address_setup_hold_20261010.md).
See the [captured phase-interface report](../../docs/row_decoder_captured_phase_interface_20261009.md)
for the historical and follow-up results, exact evidence files, warnings, and
the planned matrix.

## Experimental topology

An 80-stage chain of CMOS inverters provides taps at stages 24, 60, and 80:

```text
CLK_RELEASED = CLK AND DLY24
PRECH_SET    = CLK_RELEASED OR DLY80
PCLK         = VALID_ACCESS_Q AND CLK AND DLY60
PRECH        = VALID_ACCESS_Q AND PRECH_SET
```

The AND and OR functions use static CMOS gates. The current provisional
working sizing for each delay-chain inverter is SKY130A
`pfet_01v8`/`nfet_01v8` at `L=0.15 µm`, `Wp=1.26 µm`, and `Wn=0.42 µm`.
This pair had the largest measured timing margins in the initial six-pair
screen while keeping worst-corner capture-to-PCLK delay close to the reference
pair (`Wp=0.84 µm`, `Wn=0.42 µm`). The phase-logic output inverters use
`Wp=3.0 µm` and `Wn=1.5 µm`; the OR gate's pull-up PMOS devices use
`Wp=1.68 µm`. These are initial experimental values, not final sizing.

The hierarchy contains 160 delay-chain MOSFETs, three 8-MOS AND3 gates, and
one 6-MOS OR2 gate: **190 MOSFETs total**. This count was audited from the
Xschem-generated SPICE hierarchy. An earlier simulation-only report counted
only two AND3 gates and stated 182; that was a counting error, corrected in
the phase-source follow-up report.

## Use and limits

Open the top schematic with:

```bash
./tools/sram-eda xschem cells/control/pclk_phase_source.sch
```

Regenerate the new hierarchy deterministically with:

```bash
python3 tools/generate_pclk_phase_source.py --write
python3 tools/generate_pclk_phase_source.py --check
```

The Xschem netlist can be used in the existing decoder/WL/precharge PEX
interface runner with `--phase-source xschem-tapped-delay-chain`. The initial
sizing comparison and full-matrix evidence are in
[`docs/phase_delay_inverter_sizing_screen_20261009.md`](../../docs/phase_delay_inverter_sizing_screen_20261009.md).
The measured 24/60/80 taps and clock/sample windows remain experimental: the
cell has no layout, DRC, LVS, or phase-source PEX, and the full 6T bitcell
read/write path is not integrated. Do not interpret the numbers as a
specification limit, maximum frequency, reliability result, or signoff.
