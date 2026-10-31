# Open-Source SRAM Memory Compiler

An open-source synchronous single-port SRAM compiler project targeting
SkyWater SKY130A at a nominal core supply of 1.8 V. The architecture uses a
conventional 6T bitcell, eight bits per word, one word per physical row and
explicit VDD/VSS. The first macro target is 4×8; supported compiler depths
are 4, 8, 16 and 32 words.

The [technical specification](specs/technical_specification.md) defines the
architecture and open advisor decisions. The compiler, complete physical macros
and compiler-generated GDSII/LEF/Verilog/Liberty views remain planned work.

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

## Next phase and review workflow

The first two Phase 2 digital fronts now have a public Verilog functional
model, a separately structured 4x8 controller/wrapper and an independent
self-checking regression. See the [digital contract](specs/sram_4x8_digital.md),
[interfaces and commands](docs/sram_4x8_interfaces.md) and
[selected regression evidence](reports/digital/phase2_log_reconciliation/summary.md).
Run `./scripts/run_rtl.sh` to reproduce the digital checks. These models do
not replace the selected dynamic decoder or establish physical macro access.
After a core PASS, use the same output with `--verify-evidence` to run the
Python suites and preservation audit and publish the consolidated receipt.

Phase 2 integrates the selected leaves into a 4×8 SRAM with data write/readback,
physically implements capture/PCLK/PRECH control, derives macro timing and
sense-enable margins, and develops the compiler and generated views.

See [GITFLOW.md](GITFLOW.md) for branch ownership and review. PR #6 published
the earlier develop state to main. PR #7 proposes the reconciled six-cell
package to develop; after its acceptance, a new develop-to-main PR is needed
to publish that delivery as a reviewed milestone.
