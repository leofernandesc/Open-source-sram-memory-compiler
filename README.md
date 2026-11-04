# Open-Source SRAM Memory Compiler

An open-source synchronous single-port SRAM compiler project targeting
SkyWater SKY130A at a nominal core supply of 1.8 V. The architecture uses a
conventional 6T bitcell, eight bits per word, one word per physical row and
explicit VDD/VSS. The first macro target is 4×8; supported compiler depths
are 4, 8, 16 and 32 words.

The [technical specification](specs/technical_specification.md) defines the
architecture and open advisor decisions. A local experimental physical 4×8
prototype now has an integrated GDSII/LEF, mapped digital control, GLS and
transistor-level checks. Physical generation at depths 8/16/32 and characterized
Liberty remain future work. This is not full PVT, RC timing or fabrication qualification.

## Phase 2 experimental handoff

Implementation and technical audit are complete within the declared nominal
scope; **formal team/advisor acceptance is pending**. The physical prototype
is 4×8. The compiler is still under development: physical 8×8/16×8/32×8
and a characterized Liberty library are not delivered.

| Evidence | Verified scope/result |
|---|---|
| Integrated circuit | 1,493 MOS: 401 selected custom + 1,092 SKY130HD |
| Digital interface | 20 FF, eight physical tri-state cells, custom macro preserved |
| Functional regression | 154,303 RTL checks; 15,619 mapped GLS checks |
| Physical verification | Zero Magic DRC and expanded Netgen LVS, including GDS reimport |
| Directed electrical access | 1,332 total checks, including 160 read bits |
| Additional no-reset startup | Five passing scenarios; 3,383 total checks including 240 read bits |

Mapped and routed GLS repeat the same coverage and are not 31,238 unique tests.
Read-bit counts are subsets of the corresponding total checks. Electrical
conditions are TT, 1.8 V, 27 °C and a **20-ns experimental clock**, with extracted
connectivity/junctions and no detailed interconnect RC. This does not establish
Fmax, complete external timing, statistical startup/PVT, power/yield or
fabrication reliability. The Phase 1 model-coverage limitation remains recorded.

```text
RTL/controller → Yosys/SKY130HD → mapped GLS
Frozen custom cells → Python/Magic fabric → OpenROAD integration
→ final GDS reimport → DRC/LVS → transistor-level access/capture
```

Start with the [reproduction guide](docs/phase2_reproduction_guide.md),
[current handoff index](release/phase2_experimental/README.md),
[public timing contract](specs/sram_4x8_timing_contract.md) and
[22-slide technical presentation](presentations/phase2/README.md).
The [audit](docs/phase2_review_20261104.md),
[requirements matrix](docs/phase2_review_20261104_requirements.md),
[acceptance gates](docs/phase2_review_20261104_acceptance.md) and
[startup supplement](docs/phase2_final_polish.md) distinguish verified results
from uncharacterized limits. Historical receipts retain their original
pre-publication status; Git publication does not change scientific acceptance.

A light identity audit needs no EDA reconstruction:

```sh
python3 tools/review_phase2_delivery.py --output reports/phase2/local/review_new --require-versioned
```

The source-to-GDS script reconstructs an unselected candidate without cached
ODBs. Costly SPICE is optional and explicit; full raw-data recovery and
regeneration routes are documented in the guide.

## Phase 1 delivery

The six-leaf technical package is ready for team review. Its selected files
are fixed by [phase1_current.json](release/phase1_current.json) and the
[current artifact table](release/phase1_keeper/README.md).

| Selected cell | MOS | Role |
|---|---:|---|
| bitcell_6t | 6 | Differential storage cell |
| sense_amp | 7 | Regenerative latch with PMOS sampling |
| precharge | 3 | Bitline precharge and equalization |
| wl_driver | 4 | Two-stage static CMOS wordline buffer |
| write_driver | 10 | Complementary tri-state bitline driver |
| row_decoder | 33 | Leonardo's dynamic 2-to-4 PCLK NAND decoder with four feedback PMOS keepers |

Each entry selects SCH, SYM, SPICE, flat MAG, PEX and physical proof. Stored
and repeated checks report zero DRC, dimension/terminal-aware LVS and PEX
connectivity binding for these masks. The original 29-MOS decoder remains
an unchanged historical baseline, alongside the five unchanged leaf selections.

The [decoder study](docs/row_decoder_robustness_20261029.md) records 105 passing
experimental runs and 3,045 checks, including 48 ordered address cases and
30 crossed PVT points; deliberate noise-boundary failures remain recorded.
The [integration review](docs/phase1_integration_20261030.md) records fresh
six-cell physical checks, a 48-case decoder/WL reproduction and representative
G7 read/write matrices with 60 cases each. G7 uses ideal WL-input timing;
these results do not establish complete SRAM access with the selected decoder.
The [post-PR6 review](docs/phase1_post_pr6_review_20261030.md) checks the merged
baseline and corrects documentation and checkpoint identity, with 129 tests passing.

The off-state model-data gap is a documented, non-blocking limitation for
this academic leaf handoff. Macro frequency, statistical yield and foundry
reliability are not established. Tight G7 screening margins and the open
advisor decisions remain visible in the linked reports.

## Reproduce and inspect

The configured Docker environment contains SKY130A/open_pdks, Xschem,
ngspice, Magic, Netgen, Python/gdstk, Icarus Verilog and GTKWave. Setup and
version details are in [tools/ENVIRONMENT.md](tools/ENVIRONMENT.md).

```bash
./tools/sram-eda --check
python3 tools/verify_phase1_handoff.py
python3 sims/integration/check_evidence.py
./tools/sram-eda xschem cells/row_decoder/variants/keeper_0p84/row_decoder.sch
```

The Python audit commands check recorded evidence without rerunning electrical
simulation or extraction. To reproduce simulations, use the commands in the
[reconciliation report](docs/phase1_integration_20261030.md) and choose fresh
output directories. The [cell index](cells/README.md) distinguishes delivered
views from development captures and compatibility paths.

## Preserved engineering work

Danilo's [bitcell development report](docs/relatorio_validacao_bitcell_6t_sky130.md),
[bitcell specification](specs/sram_6t_cell.md), [capacitance derivation](docs/cbl_pre_layout_estimate.md)
and [dated G7 qualification record](docs/phase1_leaf_cell_closure.md) retain
measured sizing, .t0 initialization, capacitance and electrical evidence.
Their earlier planning statements and experimental candidates are read in
that dated scope; the current six-cell manifest and public specification
control the present delivery. The selected physical proofs supersede an older
wrapper-only LVS claim for the masks actually checked.

## Repository structure and review workflow

- `rtl/`, `tb/`, `synth/`, `verification/`: digital sources and verification.
- `cells/`, `layout/`, `release/phase1*`: selected leaf development/frozen views.
- `physical/phase2/`, `tools/`: phase binding, 4×8 generation and verification.
- `reports/phase2/`, `reports/digital/`: selected evidence and dated histories.
- `presentations/phase2/`: editable deck, PDF, notes and technical Q&A.
- `build/`: ignored regenerable databases, local raw data and rendering scratch.

The digital reference `3b0675b` was already published on `feature/phase2-digital`.
The Phase 2 integration branch preserves it by ancestry. PR #7 still proposes
Phase 1 to `develop`; the Phase 2 draft is stacked on
`integration/phase1-six-cells`. Review/integrate Phase 1 first, then retarget
and recheck the Phase 2 comparison. No direct main/develop merge is implied.
See [GITFLOW.md](GITFLOW.md) and the [handoff review order](release/phase2_experimental/README.md).
