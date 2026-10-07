# SKY130A dynamic row decoder layout

The source circuit is [`cells/row_decoder/row_decoder.sch`](../../cells/row_decoder/row_decoder.sch).
This directory contains the generated Magic layout and the scripts used to
import, route, check, and extract it. The layout builder reads the Xschem
netlist, checks its nine external pins and 29 MOS devices, and creates the
Magic views without editing the schematic.

## Current evidence

- The latest routed and flattened views pass Magic `drc(full)` with zero
  errors. Magic 8.3.684 was used for routing and DRC; Magic 8.3.589 was used
  for Xschem-to-layout device import. The flow used SKY130A technology 1.0.493.
- Netgen 1.5.293 reports a unique LVS match: 29 MOS devices (17 NFET,
  12 PFET), 22 nets, and matching external/bulk connections.
- The latest detailed R-C PEX contains 393 resistors and 226 capacitors, has
  no negative capacitor values, and preserves the Xschem pin order. Its
  SHA-256 is `c3e39efae880fd46fddd0d610f9dd789a3beeee847c62ba2fbdaa1bf88419128`;
  see [`pex/row_decoder_pex.spice`](pex/row_decoder_pex.spice),
  `reports/extract.log`, and `reports/lvs.out`.
- The matched 13-case PEX campaign completed: nine cases pass and four
  SS/−40 °C cases fail the selected-wordline 1 ns level check. These are
  electrical closure failures; do not report the decoder as fully validated.
- The earlier Magic 8.3.589 PEX had four negative shunt capacitors and is
  superseded by the 8.3.684 extraction. The negative-capacitance guard remains
  in the builder and simulation runner. Do not remove negative entries by hand.
- The extracted PEX includes the decoder only. The four WL buffers remain
  schematic devices, the row load is the 17.4 fF estimate, and physical-row
  loading and complete macro behavior remain unqualified. Full measurements and
  limitations are recorded in the
  [`validation log`](../../docs/feature_peripherals_validation_log.md).

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

The latest run used Magic 8.3.589 for Xschem-to-layout device import and Magic
8.3.684 for routing, DRC and extraction. The 8.3.589 import sequence calls
`ext2sim` on the loaded cell before `extresist`. Install the newer source release
in the existing project container with the repository installer:

```bash
docker start sram-xschem
docker exec -u 0 -w /work sram-xschem \
  bash /work/tools/install_magic_8_3_684.sh
```

The installer builds Magic 8.3.684 under `/opt/magic/8.3.684`, leaves the PDK
files and existing Magic 8.3.589 installation in place, and records the source
and executable SHA-256 values in `/opt/magic/8.3.684/BUILD-INFO.txt`. The
container's writable layer keeps this installation until the container is
removed; rerun the installer if it is recreated. Confirm the selected binary:

```bash
docker exec -w /work sram-xschem bash -lc \
  'export PATH="/opt/magic/8.3.684/bin:$PATH"; command -v magic; magic --version; cat /opt/magic/8.3.684/BUILD-INFO.txt'
```

On Linux, `tools/sram-eda` adds `/opt/magic/*/bin` to `PATH`. Verify the
selected version and regenerate the retained layout's extraction:

```bash
./tools/sram-eda magic --version
./tools/sram-eda sh -c \
  'test "$(magic --version)" = "8.3.684" && exec python3 layout/row_decoder/build_layout.py --skip-import --extract'
sha256sum layout/row_decoder/pex/row_decoder_pex.spice
```

For Windows Docker Desktop, explicitly select 8.3.684 so the command cannot
silently use the older image binary:

```powershell
docker exec -w /work sram-xschem bash -lc 'for tool_dir in /opt/ngspice/*/bin /opt/netgen/*/bin /opt/iverilog/*/bin /opt/xschem/*/bin; do if [ -d "$tool_dir" ]; then PATH="$tool_dir:$PATH"; fi; done; export PATH="/opt/magic/8.3.684/bin:$PATH" PDK_ROOT=/opt/pdks PDK=sky130A; test "$(magic --version)" = "8.3.684"; magic --version; sha256sum "$(command -v magic)"; python3 layout/row_decoder/build_layout.py --skip-import --extract'
```

The builder runs Netgen LVS and returns nonzero if the extracted PEX contains
any negative capacitor values. Continue to simulation only when it prints
`PEX capacitance audit: PASS`. Record the Magic version, executable hash,
extraction logs, PEX SHA-256, and audit result. The matched simulation runner
also blocks a PEX with negative capacitors before launching Xschem or ngspice.
The earlier cap-only file remains unqualified and must not be used as PEX.

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

## 2026-10-08 UTC: current R-C extraction and simulation status

The later extraction with Magic 8.3.684 supersedes the negative-capacitance
artifact described above. Current routed and flattened DRC are both zero;
Netgen LVS is a unique match. The current PEX contains 29 MOS, 393 resistors and
226 capacitors, preserves the external pins, and contains no negative
capacitance. Its SHA-256 is
`c3e39efae880fd46fddd0d610f9dd789a3beeee847c62ba2fbdaa1bf88419128`.

The full matched simulation is in
[`row_decoder_pex_output_pfets_3um_20261008`](../../sims/row_decoder/results/row_decoder_pex_output_pfets_3um_20261008/).
All 13 pre-layout cases pass their functional/settling checks. The extracted
PEX completed all 13 cases: nine pass and four SS/-40 C diagonal cases fail the
selected-wordline 1 ns level check (1.201–1.328 V versus a 1.458 V minimum).
The PEX's signed model upper screen passes, while five cases exceed the
experimental 1.95 V magnitude screen. Thus R-C extraction, DRC and LVS are
closed; full post-layout electrical closure remains open. The decoder-only PEX
still uses schematic WL buffers and the estimated 17.4 fF row load. See the
dated entry in the validation log for tool versions, commands, measurements
and limitations.
