# Open-Source SRAM Memory Compiler

Open-source SRAM memory compiler targeting the SkyWater SKY130 PDK.

The project generates synchronous single-port SRAM macros based on conventional 6T bitcells, using an 8-bit fixed word width and supported depths of 4, 8, 16, and 32 words.

The current architecture uses one word per physical row.

## Supported Configurations

| Configuration | Capacity |
|---|---:|
| 4×8 | 32 bits |
| 8×8 | 64 bits |
| 16×8 | 128 bits |
| 32×8 | 256 bits |

The 4×8 SRAM is the first implementation and integration target.

## Generated Views

Each supported configuration is expected to generate:

- GDSII
- LEF
- behavioral Verilog
- simplified Liberty `.lib`

## Verification and Characterization

Generated SRAM macros are intended to undergo:

- DRC
- LVS
- timing characterization
- dynamic and static power characterization
- Static Noise Margin analysis
- TT, SS, and FF process-corner evaluation

## Toolchain

- SkyWater SKY130 / open_pdks
- Xschem
- ngspice
- Magic
- Netgen
- Python
- gdstk
- Icarus Verilog
- GTKWave
- Git

## Project Status

**Phase 1 — Leaf-cell development**

Current work focuses on the schematic design, electrical simulation, layout, DRC, and LVS verification of the SRAM leaf cells.

## Technical Specification

The current architecture and project requirements are documented in:

[`specs/technical_specification.md`](specs/technical_specification.md)
