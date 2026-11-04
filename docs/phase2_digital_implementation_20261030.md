# Phase 2 digital implementation — 2026-10-30

## Delivered behavior

Branch: `feature/phase2-digital`, based on Phase 1 integration commit
`a27dd1e5373d70c546bdfae44decefde64393794`. No commit, push or PR is part of
this local implementation record. PR #7 remains a separate Phase 1 delivery.

The [digital contract](../specs/sram_4x8_digital.md) implements the accepted
shared DATA interface, rising request/write-data capture, falling read capture,
live output-disable mask and retention of the previous read register value.
The public specification now states these bus semantics explicitly and corrects
Butera's institutional affiliation. Reference differences are recorded rather
than presented as interchangeable OpenRAM protocols.

The public Verilog model supports all four depths; the separately structured
wrapper/controller/macro boundary targets 4x8. The decoder RTL is a logical
verification reference. The selected 33-MOS dynamic physical decoder is
unchanged and is not replaced by synthesized logic.

## Reproduced evidence

Run: `./scripts/run_rtl.sh --output reports/digital/phase2_baseline`.

| View | Depth | Transactions | Bus checks |
|---|---:|---:|---:|
| Public model | 4 | 2,504 | 15,619 |
| Public model | 8 | 3,088 | 19,187 |
| Public model | 16 | 5,024 | 30,931 |
| Public model | 32 | 11,968 | 72,851 |
| Structural wrapper | 4 | 2,504 | 15,619 |

Each run passed with seed `0x5A17` and 2,048 random operations, plus directed
tests. Controller/one-hot verification added 96 checks: **154,303 checks passed**.
All eight controls, 64 ordered control transitions, all read/write addresses,
20 directed data patterns, unwritten reads and high-phase disturbances are
covered by the testbench. Six unsupported depths were rejected and six
deliberately faulty model variants failed the checker as required.

Compilation with warnings enabled produced no diagnostics. The public model
was also parsed as Verilog 2005; the future synthesis file list elaborated with
the macro black box. The clocked-process audit confirms only rising/falling
procedural processes in the controller/wrapper. This is not a synthesis report.

The initial testbench incorrectly expected high impedance after selecting
read before the first rising edge. Because there is no reset, the captured
control state is unknown at that point. The scoreboard was corrected to model
that unknown state; no artificial DUT initialization was added. Known inactive
live controls still require high impedance at startup.

Selected [results, logs and real VCD excerpts](../reports/digital/phase2_baseline/summary.md)
include source/tool identity and artifact hashes. Full VCDs and temporary
mutants remain ignored build products. The report explicitly identifies the
tested working-tree hashes rather than claiming the base Git commit already
contains these new files.

## Preservation and entry-point checks

- `python3 tools/verify_phase1_handoff.py --output reports/digital/phase2_baseline/phase1_preservation.json`:
  PASS, with 3,020 indexed frozen artifacts checked. This is a stored-evidence
  audit; no DRC, LVS, electrical simulation or PEX was rerun.
- Existing `tools/tests` regressions: 29 tests passed.
- New `test_digital_regression.py`: three tests passed, covering unsafe output
  rejection, minimum random count and removal of stale PASS status after an
  injected compilation failure.
- `python3 -m unittest discover -s sims/integration -p 'test*.py' -v`:
  ten tests passed, including preservation of original owner sources/reports.

No files under `cells/`, `layout/`, `release/` or `sims/` changed. The shared
integration branch and frozen source snapshots remain intact.

## Next front

The initial verifier was subsequently hardened after a deep review found
late source hashing, unchecked executed depth and shared build paths. The
[correction record](phase2_digital_review_fixes_20261030.md) and
[current evidence](../reports/digital/phase2_review_fixes/summary.md) supersede
the initial runner for current verification. The original baseline above
remains a historical record; the functional RTL and its contract are unchanged.

Proceed to SKY130HD synthesis and reuse the same public-interface testbench
for GLS. Keep the custom storage/peripheral macro as a black box, not a
flip-flop implementation of SRAM. Yosys is not currently available in the
configured container; that tool setup belongs to the next front.

Actual physical binding must qualify captured inputs, output-register sampling,
PCLK/PRECH/sense sequencing, clock/setup/hold/output-disable timing, full-macro
DRC/LVS and electrical write/readback. Frequency, electrical margin and foundry
reliability are not established by this digital delivery. The original physical
Phase 2 milestone is not closed by these two digital fronts.
