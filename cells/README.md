# SRAM leaf cells

The [active manifest](../release/phase1_current.json) and
[selected artifact table](../release/phase1_keeper/README.md) define the six
Phase 1 deliverables. Use those files for integration and verification.

| Leaf | Selected SCH/SYM directory | Formal SPICE pin order |
|---|---|---|
| bitcell_6t | `release/phase1/cells/bitcell_6t/` | `VDD BL BLB VSS WL` |
| sense_amp | `release/phase1/cells/sense_amp/` | `VDD VSS BL BLB SCLK SA_OUT SA_OUTB` |
| precharge | `release/phase1/cells/precharge/` | `VDD BL BLB PRECH VSS` |
| wl_driver | `release/phase1/cells/wl_driver/` | `VDD VSS WL_IN WL` |
| write_driver | `release/phase1/cells/write_driver/` | `DATA DATA_B WE BL BLB VDD VSS` |
| row_decoder | `release/phase1_keeper/cells/row_decoder/` | `VDD PCLK A0 A1 DEC0 DEC1 DEC3 DEC2 VSS` |

Paths in the table are relative to the repository root. Formal pin order must
be read from the selected symbol/netlist; DEC3 precedes DEC2 in the decoder
interface. The manifest also binds masks, PEX and dimension/terminal LVS proof.

## Selected dynamic decoder

The editable source is `row_decoder/variants/keeper_0p84/row_decoder.sch`.
It contains 33 MOS: 17 NFET and 16 PFET, including four W0.84/L0.15 feedback
PMOS keepers. Each keeper has D=Nrow, G=DECrow and S=B=VDD. DEC outputs feed
separate WL drivers. The 29-MOS source and freeze remain historical.

```bash
./tools/sram-eda xschem cells/row_decoder/variants/keeper_0p84/row_decoder.sch
```

The separate `row_decoder_2to4.spice` PCH_N/EVAL candidate is an unqualified
reference, not the selected implementation. See the
[decoder notes](row_decoder/README.md) for the selected revision and evidence.

## Development captures and historical paths

Root-level bitcell, precharge, sense, WL and write sources from the upstream
work are retained so existing reports and commands can be reproduced.
Structured compatibility copies under `bitcell_6t/`, `precharge/`,
`sense_amp/`, `wordline_driver/` and `write_driver/` support the earlier manual
workflow. These captures do not necessarily have the sizes selected in the
frozen physical variants. Choose the manifest rather than a filename alone.

The write interface uses DATA/DATA_B and active-high WE; WE_B is generated
internally. Its inactive state leaves BL/BLB undriven. PRECH is active low,
and SCLK is the leaf sense-enable interface. Macro control sequencing remains
an integration task under the public specification.

## Historical bitcell testbench

```bash
./tools/sram-eda xschem cells/tb_bitcell_6t_read.sch
```

This preserved bench uses the canonical pre-layout bitcell sizing
WPU/WPD/WACC=0.42/1.26/0.60 um, two ideal precharge switches and 5 fF on each
bitline. It is a small historical functional bench, not the selected PEX load
or complete SRAM integration. Its data and limitations are in the
[bitcell report](../docs/relatorio_validacao_bitcell_6t_sky130.md).

The [integration review](../docs/phase1_integration_20261030.md) records which
upstream advances were retained and which experiments were repeated. The
physical qualification of all six leaves, including the official decoder,
belongs to Phase 1; full macro access and physical control belong to Phase 2.
