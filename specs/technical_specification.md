# SRAM Memory Compiler — Technical Specification

## 1. Scope

This document defines the technical specification for the first version of the open-source SRAM memory compiler.

The project targets the SkyWater SKY130 technology and generates synchronous single-port SRAM macros based on 6T bitcells.

The supported configurations are:

| Configuration | Words | Word width | Total bits |
|---|---:|---:|---:|
| 4×8 | 4 | 8 bits | 32 |
| 8×8 | 8 | 8 bits | 64 |
| 16×8 | 16 | 8 bits | 128 |
| 32×8 | 32 | 8 bits | 256 |

The 4×8 SRAM is the first implementation and integration target.

The compiler must subsequently generate all four supported configurations.

The word width is fixed at 8 bits.

---

## 2. Technology

- **PDK:** SkyWater SKY130
- **Process node:** 130 nm
- **Nominal supply voltage:** 1.8 V
- **Power pins:** `VDD`, `VSS`

---

## 3. Memory Architecture

The SRAM architecture is:

- synchronous;
- single-port;
- based on a conventional 6T SRAM bitcell;
- fixed at 8 bits per word;
- organized with one word per physical row.

The first implementation is a 4×8 SRAM containing 32 bitcells.

The supported memory depths require address widths from 2 to 5 bits.

---

## 4. External Interface

The SRAM interface consists of:

- `CLK`
- `ADDR`
- `DATA[7:0]`
- `CSb`
- `OEb`
- `WEb`
- `VDD`
- `VSS`

`DATA[7:0]` is bidirectional.

`CSb`, `OEb`, and `WEb` are active-low signals.

| CSb | OEb | WEb | Operation |
|---:|---:|---:|---|
| 1 | X | X | Disabled |
| 0 | 0 | 1 | Read |
| 0 | 1 | 0 | Write |
| 0 | 1 | 1 | Idle |
| 0 | 0 | 0 | Invalid |

During a read, the SRAM drives the data bus.

During write, idle, disabled, and invalid conditions, the SRAM output remains in high impedance.

The invalid control combination does not perform a memory access.

---

## 5. Power-Up Behavior

The SRAM has no external reset.

Memory contents after power-up are undefined until explicitly written.

The behavioral model must preserve this behavior.

---

## 6. Clocking and Data Timing

The SRAM uses an edge-triggered synchronous interface.

Address and control inputs are captured on the rising edge of `CLK`.

Write data is also captured on the rising edge during a write operation.

Read data is captured by an 8-bit output register on the falling edge of `CLK`.

Bitline precharge and equalization occur during the low phase of the clock.
Memory access occurs during the high phase. The row-decoder controller must
deassert precharge, wait for the registered address and its complements to
settle, then assert `EVAL`; `EVAL` is deasserted before the next precharge
phase. Read data is sampled on the falling edge before precharge can disturb
the bitlines.

The maximum supported operating frequency will be determined through electrical characterization.

---

## 7. 6T Bitcell

The storage element is a conventional CMOS 6T SRAM bitcell composed of:

- two cross-coupled CMOS inverters;
- two NMOS access transistors;
- differential bitlines;
- one wordline.

Bitcell sizing will be determined through SPICE simulation rather than fixed empirically.

The initial sizing process prioritizes robustness, considering:

- retention;
- read stability;
- write ability;
- Hold SNM;
- Read SNM;
- process variation.

The final design trade-off between robustness, performance, power, and area is:

**(confirm with advisors)**

---

## 8. Precharge and Equalization

Each differential bitline pair uses a three-PMOS precharge and equalization circuit.

The circuit precharges both bitlines to `VDD` and equalizes their voltage before memory access.

Precharge is active during the low phase of `CLK`, including idle and disabled cycles.

---

## 9. Row Decoder

The first 4×8 implementation uses a footed dynamic 2-to-4 row decoder. Its
transistor-level candidate is `cells/row_decoder_2to4.spice`; its device sizes
are provisional and have not been electrically or physically qualified.

Each row has a dynamic node precharged high by a PMOS controlled by active-low
`PCH_N`. A weak feedback PMOS keeper holds an unselected node high. During
evaluation, the matching pair of address literals and the `EVAL` footer form an
NMOS discharge path to `VSS`. An inverter converts the selected node's low
level into an active-high `DECx` output. Internal stack nodes are clamped to
`VSS` during precharge to reduce charge sharing. Static CMOS inverters generate
the address complements and the clamp phase; the row decode itself is dynamic.

The output mapping is `DEC0=00`, `DEC1=01`, `DEC2=10`, `DEC3=11` for
`A1:A0`. Each `DECx` drives the existing static CMOS wordline driver; the
dynamic decoder does not directly drive the row's bitcell gates.

The control contract is two-phase and break-before-make:

1. Precharge/idle: `PCH_N=0`, `EVAL=0`; all `DECx` outputs are low.
2. Prepare: keep `EVAL=0`, deassert precharge (`PCH_N=1`), and keep the
   address stable.
3. Evaluate: assert `EVAL=1`; only the matching `DECx` may rise.
4. End access: deassert `EVAL` before asserting `PCH_N=0` to reset the dynamic
   nodes and lower the selected output.

`PCH_N` and `EVAL` must never enable precharge and evaluation together. The
address must be captured on the rising edge and held stable from before
evaluation until precharge has reset the dynamic nodes. `EVAL` must wait for
the address register's clock-to-Q and complement-generation delay; changing
the address during evaluation can leave the old row selected because a
discharged dynamic node is not restored until the next precharge. The macro
controller must provide this sequencing and non-overlap; sharing the bitline
precharge signal is allowed only after its polarity and timing are shown to
satisfy this contract. A complete precharge is required before the first
access after power-up or an idle state with unknown decoder-node charge.

The existing G7 read/write matrices use ideal `WL_IN` pulses and therefore do
not characterize decoder delay, one-hot selection, startup, keeper retention,
or phase overlap. The dynamic decoder requires separate electrical evidence
before the macro can be treated as qualified.

Qualification must exercise all four addresses, first-access startup after a
full precharge, same-row and row-change accesses, idle/disabled cycles, and
invalid commands. Transient PVT must cover the project-qualified SKY130A range
(`1.62–1.80 V`, `−40/27/125 °C`, all five process corners) with the actual
wordline driver and row load. Record selected/unselected WL levels, glitches,
decode delay, minimum safe `EVAL` pulse, keeper retention, phase overlap,
charge sharing, and current. Sweep keeper and pull-down sizing before freeze.
After decoder and row PEX are available, rerun integrated read/write PVT with
the decoder-driven WL; the existing ideal-`WL_IN` G7 matrices do not transfer
as decoder qualification.

This is the candidate architecture currently assigned to Phase 2, pending formal validation by the team/advisors. PVT transient timing, keeper versus
pull-down sizing, charge sharing, leakage retention, address setup/hold,
one-hot behavior, power, layout, DRC/LVS, and integrated 4×8 read/write remain
open qualification items. Larger-depth decoders remain an architecture
decision for advisor review.

---

## 10. Wordline Driver

Each active-high `DECx` output drives its corresponding wordline through a
static CMOS wordline driver.

The driver strength and number of stages will be determined according to the effective wordline load.

---

## 11. Write Driver

The SRAM uses one write driver per data bit.

The write drivers generate complementary bitline values during write operations and remain electrically isolated from the bitlines when inactive.

Their final sizing will be determined through electrical simulation.

---

## 12. Sense Amplifier

The SRAM uses one sense amplifier per output bit.

The selected architecture is a differential regenerative latch-based sense amplifier controlled by `sense_en`.

During read operations, the sense amplifier resolves the differential voltage developed on the bitlines into a full logic level.

The current transistor-level topology is a seven-device differential
regenerative latch. It uses two PMOS sampling devices connected to `BL` and
`BLB`, each with `W=2.0 µm`, as implemented in `cells/sense_amp.sch`. This
topology is the selected schematic basis for closure. Mismatch and SCLK setup
have engineering-screening evidence. The full deterministic 65 fF integrated
PVT with the 17 fF pre-layout WL load passed at SCLK=2.79 ns. Dynamic mismatch
then exposed insufficient setup for one real seed at 2.79 ns, so the active
pre-layout freeze timing is `SCLK=2.84 ns`. This remains engineering screening
and is not a production-yield claim.

---

## 13. Sense Timing

The first implementation generates `sense_en` using a fixed internal delay after the beginning of a read access.

The delay value will be determined through electrical simulation according to the time required for sufficient bitline differential development.

---

## 14. Control Logic

The control logic is synchronous and does not use a dedicated finite-state machine.

It coordinates:

- precharge;
- row access;
- write operation;
- sense amplifier activation;
- output enable.

Conflicting read and write operations must not be enabled simultaneously.

---

## 15. Read Operation

A read operation is selected with:

| CSb | OEb | WEb |
|---:|---:|---:|
| 0 | 0 | 1 |

Address and control signals are captured on the rising edge.

The selected row is accessed during the high phase of the clock.

The sense amplifiers resolve the stored word after the required bitline differential has developed.

The result is captured by the output register on the falling edge and presented on `DATA[7:0]`.

---

## 16. Write Operation

A write operation is selected with:

| CSb | OEb | WEb |
|---:|---:|---:|
| 0 | 1 | 0 |

Address, control signals, and write data are captured on the rising edge.

The selected row is accessed during the high phase and the write drivers apply the corresponding values to the bitlines.

The SRAM does not drive the external data bus during the write operation.

---

## 17. First 4×8 Implementation

The first integrated SRAM contains:

- 32 6T bitcells;
- 4 wordlines;
- 8 differential bitline pairs;
- one footed dynamic 2-to-4 row decoder with `PCH_N` and `EVAL` controls;
- 4 wordline drivers;
- 8 precharge/equalization circuits;
- 8 write drivers;
- 8 differential regenerative sense amplifiers;
- an 8-bit output register;
- input registers;
- control logic.

This is currently planned as a Phase 2 macro-level deliverable. The decoder has a
provisional transistor-level SPICE candidate; its qualification and complete
4×8 assembly are outside the current Phase 1 leaf-cell/G7 boundary. Because the
original project planning assigns a validated decoder to the peripherals work,
this phase reassignment must be formally validated by the team/advisors.

---

## 18. Generated Views

For each supported configuration, the compiler must generate:

- GDSII;
- LEF;
- behavioral Verilog;
- simplified Liberty `.lib`.

The behavioral Verilog model must reproduce the externally visible synchronous behavior of the SRAM.

---

## 19. Physical Verification

All generated target configurations must pass:

- DRC;
- LVS.

Leaf cells must be individually verified before full SRAM integration.

**Manual cross-check, 08 Oct 2026 (Phase 1 physical leaves and G7 column):**
Magic GUI reported zero DRC errors for the 6T bitcell; full hierarchical and
flat G7 checks also reported zero. The operator reran Netgen LVS using
`/opt/pdks/sky130A/libs.tech/netgen/sky130A_setup.tcl` inside the SKY130A
tool container; Netgen loaded the setup and reported `Circuits match uniquely`
with 212 MOS devices (136 NMOS, 76 PMOS) and 82 nets on each side. An earlier
`/dev/null` setup run is retained as historical evidence. Undefined MOS
subcircuit placeholders/black boxes and missing-property warnings persisted
even with the SKY130A setup, so this is a confirmed structural match, not a
complete verification of PDK device parameters. The manual setup-based log
was saved as `layout/column_32_full_g7_wpre2p52_final/lvs_sky130_manual.log`
(local, Git-ignored). See the [manual DRC/LVS procedure](../docs/validacao_manual_drc_lvs_sky130a.md).
This check supports the existing Phase 1 engineering qualification for the
bitcell/physical leaves; the dynamic 2-to-4 decoder and 4×8 SRAM macro
remain Phase 2 work.

---

## 20. Electrical Characterization

Electrical characterization is performed using ngspice.

The required process corners are:

- TT;
- SS;
- FF.

The characterization includes:

- access time;
- setup time;
- hold time;
- dynamic power;
- static power;
- Static Noise Margin.

Monte Carlo analysis must use at least 200 samples for SNM characterization.

### 20.1 Provisional engineering qualification targets

The following values are **project engineering recommendations**, not fixed
limits taken from the cited literature. They are used to make the next
characterization steps reproducible and must remain distinguishable from
foundry/model limits and measured results.

- nominal `VDD`: `1.8 V`;
- continuous qualification range with the current device/model strategy:
  `1.62 V` to `1.80 V`;
- `1.95 V` is retained only as the documented static model limit/audit point,
  not as a continuously qualified operating point;
- the originally requested `+10%` point (`1.98 V`) is outside the current
  `01v8` qualification strategy and requires a valid model/device strategy
  before it can be called PASS;
- Read SNM target at the nominal operating point: `>= 0.4 V`;
- provisional integrated sense-amplifier input differential target: `200 mV`.
  The G2 mismatch screen rejected `100 mV` (`480/500`); a 110–150 mV
  transition campaign still found a failure at `140 mV` but passed
  `150 mV` in `500/500` decisions. Combined with the earlier campaign,
  `150 mV` has `800/800` decisions without failure and is used as the
  effective mismatch floor. The extra `50 mV` is a pre-layout
  input-referred uncertainty/noise guard, not a measured transient-noise or
  production-yield sign-off;
- for **pre-layout schematic freeze**, the sense statistical acceptance is an
  engineering screening criterion rather than a production-yield claim:
  require zero observed decision failures at the `150 mV` mismatch floor in
  the completed campaign (`160/160` per mismatch corner, `800/800` pooled),
  then require the real 65 fF integrated path to deliver `>=200 mV` before
  sampling across the qualified PVT matrix, with setup `>=25 ps` and
  `t_res<=0.25 ns`. The observed zero-failure campaign corresponds to a
  one-sided 95% upper failure-probability bound of about `0.3738%` pooled and
  `1.8549%` per corner; these bounds document the evidence strength and are
  **not** a guaranteed product yield. The 50 mV guard is not a measured
  transient-noise allowance. PEX requalification is complete for Phase 1, but
  the guard remains an engineering assumption and must be revisited if a later
  explicit-noise study consumes that allocation;
- bitline capacitance model for schematic freeze:
  `C_BL = Nrows × (Ccell_access + Cwire_per_cell) + Cprecharge + Cwrite + Cmux + Csense`;
  the SKY130 small-signal PVT characterization closed
  `Ccell_access,max=0.452619 fF`, `Cprecharge,max=0.908533 fF`,
  `Cwrite,max=4.033129 fF` with the tri-state write driver disabled, and
  `Csense,max=9.004605 fF` per bitline at precharged BL/BLB and `SCLK=0`;
  this standalone AC value is distinct from integrated post-layout read
  qualification, which uses extracted sense PEX and passed its full 60-case
  engineering matrix;
- the current architecture uses one word per physical row and one differential
  bitline pair per data bit, so there is no column mux in the supported
  `4×8/8×8/16×8/32×8` macros (`Cmux = 0` unless the architecture is revised);
- therefore `Nrows` is fixed by macro depth: `4/8/16/32`, respectively;
- schematic freeze uses the documented conservative pre-layout `C_BL` budget
  from `docs/cbl_pre_layout_estimate.md`: `metal2`, width `0.14 µm`, maximum
  segment `5.0 µm/row`, two-neighbor sidewall coupling and +20% wire margin,
  giving `Cwire_per_cell <= 1.061862 fF` and a recalculated
  `C_BL,max = 62.409659 fF` for
  the 32-row configuration;
- the previous `58.376530 fF` budget omitted the disabled write-driver output
  capacitance. Electrical revalidation therefore moves from `60 fF` to a
  conservative `65 fF` screen; this is a
  pre-layout estimate rather than a qualified limit;
- PEX is a post-freeze validation step. The 07/10/2026 column previously
  reported `C_BL,PEX,max=453.588404713 fF` and ceiling
  `521.626665420 fF`; both are superseded historical evidence.
  On 08/10/2026 the repaired 32-row column passed full-cell DRC/LVS/PEX.
  The first capacitance run used invalid access-tap state initialization and
  remains historical. Corrected latch-output (`.t0`) PVT gives
  `C_BL,PEX,max=519.179340 fF`, ceiling `597.056241 fF`, and
  `CWL_EXTRA=93.351918 fF`; integrated G7 read and write each passed 60/60.
  Phase 1 is closed for the bitcell/leaf scope. Decoder and 4×8 macro integration
  are currently assigned to Phase 2, pending formal validation by the team/advisors;
  see `docs/phase1_leaf_cell_closure.md`;
- the lower WL pulse limit is `1.30 ×` the worst measured full write-flip time;
  full flip is defined here as both internal storage nodes reaching the
  `90%/10%` rails;
- integrated control timing uses operation-specific pulses: deterministic G2
  passed 60/60 at 65 fF plus 17 fF WL load with `SCLK=2.79 ns`, while G4
  mismatch promoted `SCLK=2.84 ns` as the active freeze timing. The post-sizing
  critical rerun at `ss/1.62 V/-40 °C` passed 2/2 with minimum
  `ΔV=360.848 mV`, setup `78.46 ps` and `t_res<=0.07144 ns`. The integrated
  write screen passed 60/60 with `WL_IN=3.2 ns`;
  no separate "dynamic SNM" acceptance criterion is defined at this stage.
  Absolute timing is intended to be generated by a replica/control path rather
  than frozen as a universal nanosecond constant;
- the reference access-time objective is `< 2.5 ns` for the combined access
  path, subject to validation on this implementation.

For the supported depths, the corrected pre-layout maxima are
`20.004/26.062/38.178/62.410 fF` per bitline for `4/8/16/32` rows under the
routing constraint above, including `Cwrite`. `Cmux = 0`.

The derivation, PVT evidence and routing constraint are recorded in
[`docs/cbl_pre_layout_estimate.md`](../docs/cbl_pre_layout_estimate.md). The
`50 fF` and `60 fF` no longer cover the corrected 32-row budget; `65 fF` is
the conservative pre-layout screening point. It has been superseded for Phase 1
G7 by the corrected post-layout column extraction and the `597.056241 fF`
requalification ceiling.

Characterization results must be reported for at least the 8×8 and 32×8 configurations.

Post-layout characterization must use parasitic-extracted netlists.

The nominal characterization temperature is:

**(confirm with advisors)**

---

## 21. Memory Compiler

The memory compiler is implemented in Python.

It must generate the four supported memory depths with an 8-bit word width and one word per physical row.

The compiler is responsible for:

- array generation;
- physical hierarchy generation;
- structural connectivity;
- GDSII generation;
- LEF generation;
- behavioral Verilog generation;
- simplified `.lib` generation.

---

## 22. Toolchain

| Function | Tool |
|---|---|
| PDK | SkyWater SKY130 / open_pdks |
| Schematic | Xschem |
| Electrical simulation | ngspice |
| Layout | Magic |
| DRC | Magic |
| LVS | Netgen |
| Parasitic extraction | Magic |
| Compiler | Python |
| GDSII generation/manipulation | Magic / gdstk |
| Behavioral simulation | Icarus Verilog |
| Waveform visualization | GTKWave |
| Version control | Git |

---

## 23. Current Scope

The current project scope is limited to:

- single-port SRAM;
- 6T bitcells;
- 8-bit word width;
- depths of 4, 8, 16, and 32 words;
- one word per physical row.

---

## 24. Open Technical Decisions

The following architectural decisions still require confirmation:

- final optimization priority between robustness, performance, power, and area — **(confirm with advisors)**
- implementation strategy for larger row decoders — **(confirm with advisors)**
- nominal characterization temperature — **(confirm with advisors)**

---

## 25. References

1. *Memory Compiler Open-Source — Adapted Project Specification*.
2. M. R. Guthaus et al., *OpenRAM: An Open-Source Memory Compiler*, ICCAD, 2016.
3. J. T. Butera, *OpenRAM: An Open-Source Memory Compiler*, M.S. Thesis, University of Virginia, 2013.
4. H. Wann et al., *SRAM Cell Design for Stability Methodology*.
