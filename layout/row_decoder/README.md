# SKY130A dynamic row decoder layout

The source circuit is [`cells/row_decoder/row_decoder.sch`](../../cells/row_decoder/row_decoder.sch).
This directory contains the generated Magic layout and the scripts used to
import, route, check, and extract it. The layout builder reads the Xschem
netlist, checks its nine external pins and 29 MOS devices, and creates the
Magic views without editing the schematic.

## Current evidence

- Magic 8.3.589 / SKY130A technology 1.0.493: 0 DRC errors on the routed
  hierarchy and 0 on the flattened view (`reports/route.txt`,
  `reports/drc_flat.txt`).
- Netgen 1.5.293: unique LVS match between the flattened Magic extraction and
  the retained Xschem topology; 29 MOS devices and 22 nets
  (`reports/lvs_recheck.txt`).
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

From the repository root, in the configured project container:

```bash
./tools/sram-eda python3 layout/row_decoder/build_layout.py
```

This regenerates the Xschem netlist, Magic import, placement, routing, and both
DRC checks. `build_layout.py --skip-import` reuses the existing imported
transistor cells. To repeat LVS against the saved extracted topology without
starting detailed resistance extraction, run:

```bash
./tools/sram-eda netgen -batch lvs \
  'layout/row_decoder/row_decoder_flat_extracted.spice row_decoder_flat' \
  'layout/row_decoder/row_decoder_import.spice row_decoder_sram6t' \
  /opt/pdks/sky130A/libs.tech/netgen/setup.tcl \
  layout/row_decoder/reports/lvs_recheck.out
```

The full extraction script regenerates the extracted netlist and then runs
Netgen LVS, but it also starts the deferred detailed R-C extraction described
below.

## Deferred detailed R-C extraction

The current host was slow during detailed route-resistance extraction. The
builder's legacy Magic 8.3.589 sequence has been corrected to call `ext2sim`
without a root argument on the loaded cell before invoking `extresist`. This
correction has not yet been exercised. Wait until a faster machine is available
before running:

```bash
./tools/sram-eda python3 layout/row_decoder/build_layout.py \
  --skip-import --extract
```

The command is expected to be noticeably heavier than DRC/LVS. The script
rejects the result unless it contains both extracted resistors and capacitors.
Only after that check should the decoder's critical electrical tests be
repeated with the extracted netlist.
