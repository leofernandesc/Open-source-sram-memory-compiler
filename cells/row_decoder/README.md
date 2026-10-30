# Selected dynamic decoder revision

The selected Phase 1 source is `variants/keeper_0p84/row_decoder.sch`.
Open it in the configured SKY130 environment:

```bash
./tools/sram-eda xschem cells/row_decoder/variants/keeper_0p84/row_decoder.sch
```

It preserves the dynamic PCLK NAND architecture and adds four W0.84/L0.15
PMOS feedback keepers. Each keeper has D=Nrow, G=DECrow, S=B=VDD. The circuit
contains 33 MOS: 17 NFET and 16 PFET. DEC outputs still feed separate WL drivers.

The original `row_decoder.sch` and `release/phase1/` preserve the 29-MOS
baseline. The current fixed SCH/SYM/SPICE/MAG/PEX files and physical proofs
are listed in [the selected delivery](../../release/phase1_keeper/README.md).
The [engineering analysis](../../docs/row_decoder_robustness_20261029.md)
explains sizing, measured retention/noise margins, delay/energy cost and the
remaining independent-model-coverage limitation.

Stored post-layout evidence can be checked without rerunning extraction:

```bash
python3 tools/freeze_keeper_revision.py --check
```

Reproduce electrical characterization in a new output directory:

```bash
./tools/sram-eda python3 sims/row_decoder/run_keeper_pex.py \
  --output-dir sims/row_decoder/results/keeper_pex_repro
```

Layout generation is `layout/row_decoder_keeper/build_layout.py`. Notify the
owner before a new detailed R-C extraction because it may be moved to the
other machine. Existing G7/captured-control integration evidence belongs to
its original inputs and requires new integration checks when this leaf is used.
