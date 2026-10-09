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
glitch-free `VALID_ACCESS_Q` from upstream control capture. The simulation
runner currently models `CLK` and `VALID_ACCESS_Q` as ideal sources, so this
cell alone is not a complete SRAM control path.

## Captured access qualifier

`valid_access_capture.sch` implements the control condition with SKY130 FD SC
HD standard cells:

```text
VALID_ACCESS_D = !CSb AND (OEb XOR WEb)
VALID_ACCESS_Q = capture(VALID_ACCESS_D, rising edge of CLK)
```

This enables exactly one of read or write when `CSb` is active low, and rejects
idle, simultaneous read/write, and chip-disabled controls. It captures only the
qualified access bit; address and write-data capture are outside this cell. The
cell has no reset, so `VALID_ACCESS_Q` is unspecified until the first rising
clock edge.

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
cell has no layout, DRC, LVS, phase-source PEX, captured qualifier, or complete
6T bitcell read/write path. Do not interpret the numbers as a specification
limit, maximum frequency, reliability result, or signoff.
