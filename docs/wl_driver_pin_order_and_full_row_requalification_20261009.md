# WL-driver pin-order audit and full-row requalification

Date: 2026-10-09 · Branch: `feature/peripherals`

## Scope

Audit the schematic-versus-PEX pin mapping in
[`run_leaf_peripheral_smoke.py`](../sims/run_leaf_peripheral_smoke.py), correct
the testbench construction, and remeasure the current two-stage WL driver with
its existing schematic and PEX. No schematic, layout, device sizing, or PEX
file was changed. No new extraction was run.

## Pin-order finding

Xschem currently emits the WL-driver formal pins in this order:

```text
VDD WL_IN WL VSS
```

The Magic PEX subcircuit declares:

```text
VDD VSS WL_IN WL
```

The previous smoke deck always instantiated the schematic using the PEX order
(`XWL vdd 0 wl_in wl wl_driver`). That connected schematic terminals by the
wrong positional order. The old schematic smoke results therefore cannot be
used as evidence, despite their PASS status. The retained PEX smoke did use the
correct PEX order and is not invalidated by this finding.

The runner now reads the formal pin order from each generated subcircuit and
builds its instance from a named terminal map. It also records the delay from
the input 50% crossing to WL's 90% crossing, and allows the input pulse width
and high/low sample times to be selected. The existing default samples and
pulse width are unchanged.

## Corrected reference-load matrix

The corrected schematic and existing PEX were each run at TT/SS/FF, 1.62/1.80
V, −40/27/125 °C, and 17.4/50 fF. All 36 cases passed for each netlist with
ngspice return code 0.

| Netlist | Load | Worst input-50% to WL-50% | Worst input-50% to WL-90% | Minimum sampled high | Maximum sampled low |
|---|---:|---:|---:|---:|---:|
| Schematic | 17.4 fF | 0.29133 ns | 0.56313 ns | 1.619995 V | 0.000144687 V |
| Schematic | 50 fF | 0.66536 ns | 1.40949 ns | 1.573060 V | 0.00898481 V |
| Existing PEX | 17.4 fF | 0.38625 ns | 0.72054 ns | 1.619899 V | 0.000151427 V |
| Existing PEX | 50 fF | 0.75951 ns | 1.56602 ns | 1.541609 V | 0.05077535 V |

The worst delay and minimum-high points occur at SS/1.62 V/−40 °C. These are
smoke measurements at the selected operating points, not a sizing optimum or a
complete statistical/reliability qualification.

## Corrected full-row lumped-load screen

The current row-load evidence gives a maximum eight-bit row Ceff of
102.873935496 fF. It was applied as one capacitor from WL to VSS; this is a
lumped leaf-driver screen, not a distributed physical-row simulation. The
maximum Ceff was measured at FF/1.62 V/−40 °C; applying it to the slower
SS/1.62 V/−40 °C driver is a cross-corner stress combination, not a paired
physical operating point. The driver was tested with a 5 ns input-high pulse,
WL high sampled at 4.5 ns, and WL low sampled at 8.0 ns. The longer pulse is
required to observe the high level after the measured settling interval. Both
runs returned ngspice code 0 and passed the existing 90% high / 10% low screen.

| Netlist | Input-50% to WL-50% | Input-50% to WL-90% | WL at 4.5 ns | WL at 8.0 ns |
|---|---:|---:|---:|---:|
| Schematic | 1.27085 ns | 2.78102 ns | 1.555500 V | 0.000059424 V |
| Existing PEX | 1.36447 ns | 2.93698 ns | 1.537326 V | 0.000463388 V |

The 1.95 V terminal-domain/model review and actual access-transistor gate
acceptance remain separate open checks. The full row remains represented by
lumped Ceff, and actual decoder-to-driver timing and distributed coupling are
covered by the combined PEX work and still need interface/owner review.

## Reproduction

Run inside the configured project container:

```bash
./tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 python3 sims/run_leaf_peripheral_smoke.py \
  --blocks wl_driver --corners tt ss ff \
  --vdd-values 1.62 1.8 --temps-c -40 27 125 \
  --wl-cap-ff 17.4 50 \
  --output sims/wl_driver_smoke_3corner_pvt_pinorderfix_20261009.csv

./tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 python3 sims/run_leaf_peripheral_smoke.py \
  --blocks wl_driver --corners tt ss ff \
  --vdd-values 1.62 1.8 --temps-c -40 27 125 \
  --wl-cap-ff 17.4 50 --pex \
  --output sims/wl_driver_pex_smoke_3corner_pvt_pinorderfix_20261009.csv

./tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 python3 sims/run_leaf_peripheral_smoke.py \
  --blocks wl_driver --corners ss --vdd-values 1.62 --temps-c -40 \
  --wl-cap-ff 102.873935496 --wl-pulse-width-ns 5 \
  --wl-high-sample-ns 4.5 --wl-low-sample-ns 8 \
  --output sims/wl_driver_smoke_full_row_ss_20261009.csv

./tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 python3 sims/run_leaf_peripheral_smoke.py \
  --blocks wl_driver --corners ss --vdd-values 1.62 --temps-c -40 \
  --wl-cap-ff 102.873935496 --wl-pulse-width-ns 5 \
  --wl-high-sample-ns 4.5 --wl-low-sample-ns 8 --pex \
  --output sims/wl_driver_pex_smoke_full_row_ss_20261009.csv
```

The `PYTHONDONTWRITEBYTECODE=1` setting avoids writing container-owned Python
cache files into the shared checkout.

## Reproducibility hashes

| File | SHA-256 |
|---|---|
| Runner | `fce80268df0d97f33579d3238f75643ad08cc56c6e83bdb4cdf67555cb8c6df7` |
| WL schematic | `fcbd66081215bbbc32ff3ddb2655bf74f5ad55c6ac952b31159b64d3fb0b86d4` |
| Existing WL PEX | `68a3d7234d6d002d38655c10eace999729222b4a9078568feb71c0867eecfdc0` |
| Corrected schematic matrix CSV | `7ee129657eab6c7bf9c166578461565c3bbe75c4583cbc3cce6399204184822d` |
| Corrected PEX matrix CSV | `1084433e5a1dd42cbc1d55700107ed422e517a00c5010ad223357673d4b17adb` |
| Full-row schematic CSV | `b03915b4254f058d4932f1eaef760d83d5cb0e59bc2a5285555f4299f7c181ef` |
| Full-row PEX CSV | `106f754967c7093194f7f85e411b34a218a8a5bf0d209642a7d57dc544d9064e` |
