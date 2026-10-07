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
- Detailed Magic 8.3.589 extraction now produces 769 distributed resistors
  and 494 capacitors for the 29-MOS decoder. The extracted subcircuit preserves
  the Xschem pin order. Netgen reports a unique match on the separate
  connectivity-only extraction. The PEX SHA-256 is
  `cb22575eba88efbd7f40412cb18870cb3854fa4873c24db76f07f4f25df9b737`;
  see [`pex/row_decoder_pex.spice`](pex/row_decoder_pex.spice),
  `reports/extract.log`, and `reports/lvs.log`.
- Electrical post-layout validation remains pending. On the current host,
  ngspice 44.2 exceeded the 180-second timeout for one matched TT case at both
  1 ps and 5 ps maximum steps. The corresponding schematic baselines passed;
  no PEX waveform or baseline-to-PEX comparison was produced. Do not treat the
  PEX as electrically qualified until the matched campaign completes.
- Bulk terminals are tied to the appropriate supply rails; `EVAL_GND` remains
  a separate internal node connected to VSS through the decoder footer.
- An earlier cap-only extraction remains unqualified. Do not use it for
  post-layout timing claims. It is explicitly labeled
  `reports/row_decoder_cap_only_unqualified.spice` (231 capacitors, 0
  resistors). See the dated entry in
  [`docs/feature_peripherals_validation_log.md`](../../docs/feature_peripherals_validation_log.md).

These checks qualify the current generated layout revision for DRC, LVS, and
the presence of distributed R-C extraction. They do not qualify post-layout
electrical behavior, physical-row loading, area optimization, or the complete
SRAM macro.

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

## Reproduce detailed R-C extraction

The builder's legacy Magic 8.3.589 sequence calls `ext2sim` on the loaded cell
before `extresist`. Extraction, DRC and LVS have completed on the current
routed revision. From the configured project container, reproduce them with:

```bash
./tools/sram-eda python3 layout/row_decoder/build_layout.py \
  --skip-import --extract
```

On the Windows Docker Desktop setup used for the recorded run, the equivalent
PowerShell command was:

```powershell
docker exec -w /work sram-xschem bash -lc 'for tool_dir in /opt/ngspice/*/bin /opt/magic/*/bin /opt/netgen/*/bin /opt/iverilog/*/bin /opt/xschem/*/bin; do if [ -d "$tool_dir" ]; then PATH="$tool_dir:$PATH"; fi; done; export PATH PDK_ROOT=/opt/pdks PDK=sky130A; python3 layout/row_decoder/build_layout.py --skip-import --extract'
```

The PEX builder rejects a result without both R and C elements and then runs
Netgen LVS. The earlier cap-only file remains unqualified and must not be used
as PEX.

## Repeat matched electrical tests

The PEX-specific runner replaces only the decoder subcircuit with the extracted
network; it retains the four existing pre-layout WL buffers and their 17.4 fF
loads. It compares the schematic and PEX for nine TT address transitions and
four SS/-40 C diagonal transitions, checking logic, precharge, dynamic-node
segments, terminal magnitudes, delay, slew, and energy. On a faster machine,
run the full matrix with a longer per-case timeout:

```bash
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py \
  --workers 2 --timeout-s 900
```

The 1 ps and 5 ps single-case pilots and their failed PEX manifests are retained
under `sims/row_decoder/results/row_decoder_pex_smoke*`. They show the timeout,
not a functional PEX failure or a successful post-layout simulation. Record
the matched comparison before making electrical post-layout claims.
