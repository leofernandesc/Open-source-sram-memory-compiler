# SKY130A dynamic row decoder layout

The source circuit is [`cells/row_decoder/row_decoder.sch`](../../cells/row_decoder/row_decoder.sch).
This directory contains the generated Magic layout and the scripts used to
import, route, check, and extract it. The layout builder reads the Xschem
netlist, checks its nine external pins and 29 MOS devices, and creates the
Magic views without editing the schematic.

## Current evidence

- Magic 8.3.589 / SKY130A technology 1.0.493, `drc(full)`: 0 DRC errors on
  the routed top cell and the flattened view after `drc catchup`
  (`reports/route.txt`, `reports/drc_flat.txt`).
- Netgen 1.5.293: unique LVS match against the retained Xschem topology;
  29 MOS devices (17 NFET, 12 PFET) and 22 nets
  (`reports/lvs_recheck.txt`).
- The Magic LVS netlist is connectivity-only. It contains no extracted R or C
  elements; detailed parasitic extraction and post-layout simulation remain
  pending.
- Bulk terminals are tied to the appropriate supply rails; `EVAL_GND` remains
  a separate internal node connected to VSS through the decoder footer.
- A preliminary capacitance extraction exists, but no qualified distributed
  R-C PEX has been produced. Do not use the cap-only attempt for post-layout
  timing claims. It is explicitly labeled
  `reports/row_decoder_cap_only_unqualified.spice` (231 capacitors, 0
  resistors). See the dated entry in
  [`docs/feature_peripherals_validation_log.md`](../../docs/feature_peripherals_validation_log.md).

These checks qualify the current generated layout revision for DRC/LVS only.
They do not qualify physical-row loading, PEX behavior, area optimization, or
the complete SRAM macro.

## Reproduce layout, DRC, and LVS

From the repository root, in the configured project container, rerun layout
generation and DRC with:

```bash
./tools/sram-eda python3 layout/row_decoder/build_layout.py --skip-import
```

The DRC scripts wait for Magic's background checker before reading the count.
To repeat DRC and then regenerate the connectivity netlist and run LVS without
starting RC PEX, run:

```bash
./tools/sram-eda python3 layout/row_decoder/build_layout.py \
  --skip-import --lvs-only
```

`--lvs-only` runs Magic connectivity extraction and Netgen LVS. It does not run
`extresist` or create an R-C PEX netlist.

## Deferred detailed R-C extraction

The builder's legacy Magic 8.3.589 sequence calls `ext2sim` on the loaded cell
before `extresist`. The detailed R-C path has not been exercised on the current
layout revision. Run it on the faster machine before post-layout electrical
tests:

```bash
./tools/sram-eda python3 layout/row_decoder/build_layout.py \
  --skip-import --extract
```

The command is expected to be noticeably heavier than DRC/LVS. The script
rejects the result unless it contains both extracted resistors and capacitors.
Only after that check should the decoder's critical electrical tests be
repeated with the extracted netlist.
