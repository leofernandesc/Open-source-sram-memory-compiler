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
- Detailed Magic 8.3.589 extraction produced 769 distributed resistors and
  494 capacitors for the 29-MOS decoder. The extracted subcircuit preserves
  the Xschem pin order. Netgen reports a unique match on the separate
  connectivity-only extraction. The PEX SHA-256 is
  `cb22575eba88efbd7f40412cb18870cb3854fa4873c24db76f07f4f25df9b737`;
  see [`pex/row_decoder_pex.spice`](pex/row_decoder_pex.spice),
  `reports/extract.log`, and `reports/lvs.log`.
- A static audit found four negative capacitors to VSS in that PEX:
  `DEC0.n0` (−3.02859 fF), `N3.n0` (−9.29966 fF), `net4.n0` (−16.2877 fF),
  and `N2.n0` (−1.3128 fF). The resulting capacitor matrix has four negative
  eigenvalues, so this extracted file is not accepted for electrical
  characterization. The layout's DRC/LVS status remains valid; the PEX needs
  regeneration and another static audit. Magic's official download page lists
  version 8.3.684 dated 2026-09-18. This is the next candidate to evaluate, not
  a confirmed fix for the negative capacitors; use the versioned install and
  extraction steps below before deciding whether the PEX is usable.
- Two earlier one-case TT pilots at 1 ps and 5 ps exceeded the 180-second
  timeout on the R-C PEX case. Their schematic baselines passed, but they
  produced no PEX waveform or paired comparison. The negative capacitors may
  contribute to slow convergence; the timeouts do not prove causation.
- The builder now reports negative capacitors and returns nonzero after LVS;
  the matched PEX runner refuses a netlist containing them before simulation.
  Do not remove those entries manually. Magic's maintainer has documented
  negative parasitic capacitances as an extraction bookkeeping issue
  ([discussion #229](https://github.com/RTimothyEdwards/magic/discussions/229)).
- Bulk terminals are tied to the appropriate supply rails; `EVAL_GND` remains
  a separate internal node connected to VSS through the decoder footer.
- An earlier cap-only extraction remains unqualified. Do not use it for
  post-layout timing claims. It is explicitly labeled
  `reports/row_decoder_cap_only_unqualified.spice` (231 capacitors, 0
  resistors). See the dated entry in
  [`docs/feature_peripherals_validation_log.md`](../../docs/feature_peripherals_validation_log.md).

The current layout revision has DRC and LVS evidence, and a distributed R-C
file was generated. The current R-C file has not passed the capacitance audit,
so it is not ready for post-layout simulation. Physical-row loading, area
optimization, and complete SRAM macro behavior also remain unqualified.

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

The previously recorded extraction used Magic 8.3.589 and called `ext2sim` on
the loaded cell before `extresist`. The existing extraction command does not
upgrade Magic: it runs whichever `magic` executable is selected by `PATH`. Use
the versioned install procedure below before regenerating the PEX.

### Install Magic 8.3.684 in the project container

From PowerShell or a Linux host with the project container available, install
the source build in the existing `sram-xschem` container. The script installs
to `/opt/magic/8.3.684`, leaves the PDK files unchanged, and writes the source
and executable hashes to `/opt/magic/8.3.684/BUILD-INFO.txt`.

```bash
docker start sram-xschem
docker exec -u 0 -w /work sram-xschem \
  bash /work/tools/install_magic_8_3_684.sh
```

The install is in the container's writable layer. If `sram-xschem` is removed
and recreated, run the installer again. Confirm the executable and source-build
record before extraction:

```bash
docker exec -w /work sram-xschem bash -lc \
  'export PATH="/opt/magic/8.3.684/bin:$PATH"; command -v magic; magic --version; cat /opt/magic/8.3.684/BUILD-INFO.txt'
```

### Regenerate and audit the PEX

On Linux, `tools/sram-eda` adds the versioned `/opt/magic/*/bin` directories to
`PATH`. Check the selected version, then run extraction:

```bash
./tools/sram-eda magic --version
./tools/sram-eda sh -c \
  'test "$(magic --version)" = "8.3.684" && exec python3 layout/row_decoder/build_layout.py --skip-import --extract'
sha256sum layout/row_decoder/pex/row_decoder_pex.spice
```

For the Windows Docker Desktop setup, explicitly select the versioned executable
so the extraction cannot silently fall back to the image's older Magic:

```powershell
docker exec -w /work sram-xschem bash -lc 'for tool_dir in /opt/ngspice/*/bin /opt/netgen/*/bin /opt/iverilog/*/bin /opt/xschem/*/bin; do if [ -d "$tool_dir" ]; then PATH="$tool_dir:$PATH"; fi; done; export PATH="/opt/magic/8.3.684/bin:$PATH" PDK_ROOT=/opt/pdks PDK=sky130A; test "$(magic --version)" = "8.3.684"; magic --version; sha256sum "$(command -v magic)"; python3 layout/row_decoder/build_layout.py --skip-import --extract'
```

The builder reports the extracted R/C counts and runs Netgen LVS. It returns
nonzero if any extracted capacitor is negative; only continue to electrical
simulation when it prints `PEX capacitance audit: PASS`. Record the Magic version,
the extraction logs, the PEX SHA-256, and the audit result. Magic 8.3.684 is a
candidate for investigation, not a guaranteed correction. Do not edit negative
capacitors out of the generated netlist by hand. The matched simulation runner
also refuses a PEX file containing negative capacitors before launching Xschem
or ngspice. The earlier cap-only file remains unqualified and must not be used
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
