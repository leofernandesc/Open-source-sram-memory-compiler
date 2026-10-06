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
| B1 | 1.00 µm | 1.00 µm | 1.50 µm | 1.00 µm | 1.00 / 1.00 µm | 17.4 fF | 95.04 ps | 274.60 ps | 151.92 ps | 326.98 ps | 72/72 PASS |

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

## B1 measured results

B1 changes only the evaluation-network NMOS widths (M6, M7, M12, M13, M17,
M18, M22, and M23) from 1.00 µm to 1.50 µm. The shared footer M8 and all other
devices remain at B0 widths. Xschem generated the updated hierarchy without
structural errors; the generated SPICE netlist was checked to contain W=1.50 µm
on all eight changed devices. ngspice completed with return code 0.

| Metric | Result |
|---|---:|
| Evaluation samples passing | 32/32 (16 DEC + 16 WL) |
| Precharge samples passing | 40/40 (20 DEC + 20 WL) |
| Selected DEC and WL levels | 1.800 V at all sample points |
| Largest absolute deselected DEC sample | 1.311 µV |
| Largest absolute deselected WL sample | 0.291 µV |
| Largest absolute DEC precharge sample | 0.486 µV |
| Largest absolute WL precharge sample | 0.291 µV |
| DEC evaluation delay range | 90.44–95.04 ps |
| WL evaluation delay range | 270.03–274.60 ps |
| DEC precharge delay range | 147.97–151.92 ps |
| WL precharge delay range | 323.50–326.98 ps |

Relative to B0, B1's maximum measured delays increased by 1.74 ps for DEC
evaluation, 1.95 ps for WL evaluation, 32.37 ps for DEC precharge, and 31.04 ps
for WL precharge. Thus B1 passes the same nominal voltage screen but does not
improve the measured timing for this load. The larger evaluation devices add
capacitance to the dynamic nodes; that is a plausible contributor to the slower
precharge and is an engineering interpretation of the measurements, not a
separately isolated capacitance measurement.

## Interpretation and next work

B0 is a measured nominal-TT reference with the wordline drivers and estimated
wordline loads attached. B1 is functionally passing in the same nominal-TT
screen, but is slower than B0 in all four recorded maximum timing metrics. Neither
candidate is an optimized sizing. No PVT sweep, layout, parasitic extraction, or
post-layout simulation is included here.

The next candidates will change one transistor family at a time while holding
the rest at B0. Record the exact W values and rerun the same loaded testbench.
After individual sweeps, combine the best passing choices and repeat the
comparison before freezing the schematic for Magic layout.
