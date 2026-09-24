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

Bitline precharge and equalization occur during the low phase of the clock. Memory access occurs during the high phase.

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

The SRAM uses a static CMOS row decoder.

The first 4×8 implementation uses a 2-to-4 decoder.

The decoder architecture scales with the supported memory depth.

The implementation strategy for the larger decoders is:

**(confirm with advisors)**

---

## 10. Wordline Driver

Each decoder output drives its corresponding wordline through a static CMOS wordline driver.

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

The exact transistor-level topology is:

**(confirm with advisors)**

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
- one static 2-to-4 row decoder;
- 4 wordline drivers;
- 8 precharge/equalization circuits;
- 8 write drivers;
- 8 differential regenerative sense amplifiers;
- an 8-bit output register;
- input registers;
- control logic.

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
- exact regenerative sense-amplifier topology — **(confirm with advisors)**
- nominal characterization temperature — **(confirm with advisors)**

---

## 25. References

1. *Memory Compiler Open-Source — Adapted Project Specification*.
2. M. R. Guthaus et al., *OpenRAM: An Open-Source Memory Compiler*, ICCAD, 2016.
3. J. T. Butera, *OpenRAM: An Open-Source Memory Compiler*, M.S. Thesis, University of Virginia, 2013.
4. H. Wann et al., *SRAM Cell Design for Stability Methodology*.
