# Dynamic row decoder sizing record

Status: sizing in progress. The measurements below define the loaded reference
candidate; they do not establish final transistor sizes or PVT robustness.

## Baseline setup

| Item | Value |
|---|---|
| Candidate | `B0` — uniform baseline |
| Schematic | `cells/row_decoder/row_decoder.sch` |
| Testbench | `sims/row_decoder/tb_row_decoder_sizing.sch` |
| Process/model | SKY130A, TT |
| Supply/temperature | 1.80 V, 27 °C |
| Tools | Xschem 3.4.6, ngspice 44.2 |
| Wordline load | One 17.4 fF capacitor from each `WL` output to GND |
| Load implementation | Four hierarchical instances of `cells/wordline_driver/wl_driver.sch` |
| Decoder sizing | All 25 MOS: W=1.00 µm, L=0.15 µm, nf=1, mult=1 |
| Wordline driver sizing | Stage 1 W=0.42 µm; stage 2 W=0.84 µm; L=0.15 µm |

The 17.4 fF capacitor is the current pre-layout estimate for one complete
wordline. It is attached to each wordline-driver output; the decoder output
drives the input devices of that driver. The separate 50 fF stress load has not
been run in this decoder sizing series.

The copied testbench preserves the original functional bench. Its current
generated node mapping is `net5`=WL0, `net6`=WL1, `net7`=WL2, and `net8`=WL3.
The sizing bench was netlisted after correcting the WL1 output connection; all
four decoder outputs now feed distinct drivers and all four WL outputs have
separate loads.

## Measurement definitions

- Evaluation level checks: sample DEC and WL outputs at 15, 35, 55, and 75 ns
  for addresses 00, 01, 10, and 11.
- Precharge level checks: sample DEC and WL outputs at 5, 25, 45, 65, and 85 ns.
- Screening limits: selected output >= 0.9 VDD (1.62 V); inactive output <=
  0.1 VDD (0.18 V). These limits are used by this screen and are not numeric
  limits stated in the technical specification.
- Evaluation delay: PCLK rising through 0.5 VDD to the selected DEC or WL output
  rising through 0.5 VDD.
- Precharge delay: PCLK falling through 0.5 VDD to the selected DEC or WL output
  falling below 0.1 VDD.

Each run contains 36 DEC voltage samples and 36 WL voltage samples. Rise and
precharge delays are measured for each selected row. Keep these definitions and
the same input stimulus for every candidate.

## Candidate comparison

| Candidate | W address inverter | W precharge PFET | W evaluation NMOS | W footer NMOS | W output inverter P/N | Load | DEC eval max | WL eval max | DEC precharge max | WL precharge max | Voltage checks |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| B0 | 1.00 µm | 1.00 µm | 1.00 µm | 1.00 µm | 1.00 / 1.00 µm | 17.4 fF | 93.30 ps | 272.65 ps | 119.55 ps | 295.94 ps | 72/72 PASS |

All channels are L=0.15 µm for B0. Group membership is:

- Address inverters: M1–M4.
- Precharge PFETs: M5, M11, M16, M21.
- Evaluation NMOS network: M6, M7, M12, M13, M17, M18, M22, M23.
- Shared footer: M8.
- DEC output inverters: M9/M10, M14/M15, M19/M20, M24/M25 (PMOS/NMOS).

## B0 measured results

| Metric | Result |
|---|---:|
| Evaluation samples passing | 32/32 (16 DEC + 16 WL) |
| Precharge samples passing | 40/40 (20 DEC + 20 WL) |
| Selected DEC and WL levels | 1.800 V at all sample points |
| Largest absolute deselected DEC sample | 0.994 µV |
| Largest absolute deselected WL sample | 0.292 µV |
| Largest absolute DEC precharge sample | 0.434 µV |
| Largest absolute WL precharge sample | 0.292 µV |
| DEC evaluation delay range | 88.74–93.30 ps |
| WL evaluation delay range | 268.01–272.65 ps |
| DEC precharge delay range | 117.90–119.55 ps |
| WL precharge delay range | 293.70–295.94 ps |

## Interpretation and next work

B0 is a measured nominal-TT reference with the wordline drivers and estimated
wordline loads attached. It is not an optimized sizing. No PVT sweep, layout,
parasitic extraction, or post-layout simulation is included here.

The next candidates will change one transistor family at a time while holding
the rest at B0. Record the exact W values and rerun the same loaded testbench.
After individual sweeps, combine the best passing choices and repeat the
comparison before freezing the schematic for Magic layout.
