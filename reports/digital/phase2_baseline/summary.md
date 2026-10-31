# Phase 2 digital regression

Status: **PASS**. 154,303 checks across five memory runs and the controller test.

| View | Depth | Transactions | Bus checks | Random operations |
|---|---:|---:|---:|---:|
| model | 4 | 2504 | 15619 | 2048 |
| model | 8 | 3088 | 19187 | 2048 |
| model | 16 | 5024 | 30931 | 2048 |
| model | 32 | 11968 | 72851 | 2048 |
| wrapper | 4 | 2504 | 15619 | 2048 |

Controller: 96 checks. Unsupported depths rejected: [0, 1, 2, 3, 5, 64].
Six deliberately faulty models were detected: wrong_capture_edge, address_alias, missing_bus_mask, corrupt_write_data, invalid_control_write, live_address.

Each memory run covers all eight controls, all 64 ordered control transitions, all read/write addresses, and 20 directed data patterns.

Source identities, commands and tool versions are in `results.json`; transcripts are in `logs/`. Real 0..180 ns VCD excerpts are retained under `waveforms/`; full VCD files are regenerated under ignored `build/digital/`. Testbench time is scheduling only, not a characterized operating period.

The clocked-process source audit found only edge-triggered processes in the controller and wrapper. Synthesis, GLS, physical timing and analog integration are **NOT EVALUATED**. The black-box compilation checks interface elaboration only.
