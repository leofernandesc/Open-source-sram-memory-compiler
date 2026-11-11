# Directed sense PEX investigation — 2026-11-11

Report: [sense_pex_small_signal_investigation.md](../../../docs/sense_pex_small_signal_investigation.md).
These nominal diagnostic experiments are not replacement library selections.
Original PEX, library and previous results remain unchanged.

| Directory | Scope | Cases / result |
|---|---|---|
| `sweep_v1` | Original PEX, 5/10/20/30/50 mV, both orders, 2/10 fF | 20 complete; 12 PASS, eight FAIL |
| `refine_v1` | Original PEX, 15 mV | Four complete; two PASS, two FAIL |
| `ablation_v2` | No C / R contracted / no RC copies | 12 complete; eight PASS, four FAIL |
| `focused_v1` | Remove clock-output C / equalize output-ground C / mirror C with R contracted | 12 complete; two PASS, ten FAIL |
| `operating_v1` | Original PEX, 5 mV, lower input common-mode or slower SCLK | Eight complete; eight FAIL |
| `top_context_v1` | Existing abutted 4×8 raw and actual sense pins | Nine reads; 288 bit/time observations |
| `analysis_v1` | Tables, limits and real-data plots | 56 cases / 112 evaluations |
| `ablation_v1` | Global-port probe incorrectly named as internal node | **FAIL_EXECUTION**, excluded from the 56 complete cases |

`investigator_v1.py` matches the script hash recorded by `sweep_v1` and the
failed `ablation_v1`. Subsequent runs store `runner_snapshot.py` before
simulation. The correction affects only probe naming after R contraction.
Full-PEX devices, stimuli, criteria and results did not change.

Every case keeps the actual deck/DUT, exact removed/changed element list,
native log, complete losslessly compressed transient, functional decisions,
internal probes and hashes. Execution/integrity success is separate from
functional PASS. Failures of modified diagnostic models are not a statistical
failure rate of the library.

The top context preserves all native samples in nine edge windows, without
decimation, in `top_edge_windows.npz` (numeric `data`, no pickle), plus pin maps
and source raw hash. The analyzer replays the specific clock/pin measurements
from these windows. This is not the complete ~100 MB top transient. Recreating
the excerpt requires the original local raw or reproduction of that campaign;
no complete top resimulation was performed here.

Simulation commands are in the report. Audit without a new simulation:

```sh
./tools/sram-eda python3 tools/investigate_sense_pex.py \
  --output reports/phase1/sense_pex_small_signal_20261111/sweep_v1 --verify
./tools/sram-eda python3 tools/test_sense_pex_diagnostics.py
```

Regenerate tables/figures in a **new** directory:

```sh
./tools/sram-eda python3 tools/analyze_sense_pex_investigation.py \
  --sources reports/phase1/sense_pex_small_signal_20261111/sweep_v1 \
            reports/phase1/sense_pex_small_signal_20261111/ablation_v2 \
            reports/phase1/sense_pex_small_signal_20261111/focused_v1 \
            reports/phase1/sense_pex_small_signal_20261111/operating_v1 \
            reports/phase1/sense_pex_small_signal_20261111/refine_v1 \
  --top-context reports/phase1/sense_pex_small_signal_20261111/top_context_v1 \
  --output reports/phase1/sense_diagnostic_analysis_fresh
```

Model hash verification requires the matching PDK. Package hashes are in
`package_checksums.sha256`; original manifests are not rewritten. Native log
carriage returns are preserved despite Git whitespace diagnostics.
