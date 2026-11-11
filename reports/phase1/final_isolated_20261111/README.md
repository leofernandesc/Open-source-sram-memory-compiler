# Final isolated leaf tests — 2026-11-11

Scope: the two frozen final variants, TT / 1.8 V / 27 °C. No source, PEX,
selection, sizing, layout or physical generator was modified.

- `nominal_v1/`: original executions, including a **WL testbench error** and
  genuine sense PEX polarity failures at 5 mV. Its aggregate is **FAIL**.
- `development_runner_v1.py`: exact source snapshot used by those executions;
  its SHA-256 is bound in the original receipt. It is historical source, not
  the current reproduction entrypoint.
- `nominal_v2/`: corrected WL stimulus (two explicit pulses), unchanged sense
  stimuli and criteria. The 24 exact original sense executions are preserved
  byte for byte with `reused_from`; only the six WL cases are re-executed.
  A functional FAIL remains a FAIL. Receipt integrity is a separate result.
- `sense_reproduction/`: targeted repeat of the PEX 5 mV case, with original
  numerical settings and then a 1 ps maximum step / tighter relative tolerance.
  No circuit, stimulus, output load or functional limit is changed.
- `verification.txt`, `checker_tests.txt`: native command transcripts.
- `package_checksums.sha256`: hashes of the package, excluding this checksum
  file itself. Both successful and failed executions remain available.

Each case keeps the exact `dut.spice`, executed `bench.spice`, native
`ngspice.txt`, losslessly compressed **complete** `waveform.dat.gz`, and
`checks.json`. `results.json` binds inputs, all 319 files in the PDK include
closure, command, tool version, case matrix, metrics and artifact hashes.
`metrics.csv` is a convenience table, not a replacement for the raw transient.

Full fresh reproduction (new directory; a functional failure returns exit 1):

```sh
./tools/sram-eda python3 tools/run_phase1_final_isolated.py \
  --output reports/phase1/final_isolated_reproduction
```

Audit stored results without another simulation (requires the matching PDK):

```sh
./tools/sram-eda python3 tools/run_phase1_final_isolated.py \
  --output reports/phase1/final_isolated_20261111/nominal_v2 --verify
./tools/sram-eda python3 tools/test_phase1_final_isolated.py \
  --evidence reports/phase1/final_isolated_20261111/nominal_v2
```

The verifier's `PASS_EVIDENCE_INTEGRITY` is **not** functional approval: its
separate `functional_status` and `case_failures` must also be read. Native logs
and full data support an independent assessment of the failed cases.

The report is [phase1_final_isolated_20261111.md](../../../docs/phase1_final_isolated_20261111.md).
This evidence was obtained now and is not a claim about historical execution
during the original Phase 1 schedule.
