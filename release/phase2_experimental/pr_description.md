## Summary

Integrate the selected six Phase 1 leaf families with SKY130HD capture, phase
control and bus interface into a reproducible physical 4×8 SRAM. Implementation
and technical audit are complete **within the declared experimental scope**;
formal team/advisor review remains pending.

## Dependency and integration order

This is a stacked draft on `integration/phase1-six-cells`, not directly on
`develop`. It depends on **PR #7**, which is still open against develop.
Review/integrate #7 first, then retarget this PR to develop and inspect the
updated comparison. The digital commit `3b0675b` is included by ancestry;
it has not been duplicated or rewritten. No main/develop merge is requested.

## Architecture and implementation

- Synchronous single-port 1RW, 4 words × 8 bits, one word per physical row.
- Public bidirectional DATA; rising-edge request/write-data capture,
  falling-edge read capture; no external reset.
- Selected dynamic 33-MOS decoder with four PMOS keepers preserved.
- 401 frozen custom MOS plus 1,092 HD MOS: 1,493 MOS total, including 20 FF
  and eight physical tri-state buffers.
- Python/Magic custom fabric generation, OpenROAD digital/physical integration,
  final GDSII/LEF/DEF/MAG/powered Verilog and flat extracted SPICE.

## Verification and evidence

| Gate | Evidence |
|---|---|
| RTL | 154,303 functional checks over supported models and wrapper |
| SKY130HD synthesis / GLS | 20 FF, 8 ebufn, one storage black box; 15,619 checks |
| Final geometry | Zero Magic DRC; expanded parameter/body/model LVS, including GDS reimport |
| Negative LVS | Wrong gate, bulk, W and L rejected |
| Baseline electrical | 128 read-bit checks plus 392 protocol/capture checks |
| Directed electrical | 1,332 total checks, **including** 160 read bits |
| Additional startup | 5 passing scenarios, 3,383 total checks **including** 240 read bits |
| Publication regression | 47 relevant Python tests; old seals/manifests and raw evidence reaudited |

Mapped and routed GLS repeat the same coverage; they are not 31,238 unique
tests. The read-bit subsets above are not added to the corresponding totals.
The circuit/source-to-GDS reconstruction reproduces the original GDS after
normalizing timestamps only, with byte-identical extracted SPICE. No fresh
heavy EDA campaign was required solely for this publication.

## Timing, startup and limits

Electrical experiments use TT, 1.8 V, 27 °C and a 20-ns clock, with extracted
connectivity/junctions and **no detailed wire RC**. The five startup cases use
1/5/10-ns ramps and 0/2/3 inactive captures in the documented combinations,
without IC/nodeset or behavioral storage. Zero inactive captures still waited
9 ns after the supply plateau. No minimum startup guarantee is inferred.

The public timing contract separates functional rules, observed windows and
uncharacterized parameters. No Fmax, full external setup/hold/turnaround,
all-corner/statistical power-up, characterized power/yield or fabrication
reliability is established. The Phase 1 model-coverage limitation is retained.

## Reviewer entry points

- `docs/phase2_reproduction_guide.md`: environment, light audits and explicit costly runs.
- `release/phase2_experimental/manifest.json`: handoff index and evidence identities.
- `physical/phase2/delivery.json`: immutable historical artifact selection.
- `docs/phase2_review_20261104_acceptance.md`: separate F2-DIG / F2-FIS acceptance.
- `docs/phase2_final_polish.md` and `specs/sram_4x8_timing_contract.md`.
- `presentations/phase2/`: 22-slide editable PPTX/PDF, Portuguese notes,
  24 technical questions and figures with provenance.

```sh
python3 tools/review_phase2_delivery.py --output reports/phase2/local/reviewer_new --require-versioned
./tools/sram-eda python3 -m unittest discover -s tools/tests -p 'test_phase2*.py' -v
```

Full startup/directed raws remain outside Git. Their optional ~81-MiB
lossless transfer bundle is indexed and locally verified; it is not an
unpublished download promise. Obtain it from the holder or regenerate using
the documented runners. The original complete baseline gzip is versioned.

## Reviewer checklist

- [ ] Review/integrate Phase 1 PR #7 before retargeting this draft.
- [ ] Confirm frozen leaves and dynamic decoder selection.
- [ ] Inspect mapped control, bus ownership and capture edges.
- [ ] Inspect delivered GDS/LEF and DRC/LVS evidence.
- [ ] Review electrical sequencing, startup scenarios and raw provenance.
- [ ] Accept the explicitly limited nominal scope and remaining timing/model boundaries.
- [ ] Review presentation and reproduction instructions.
- [ ] Deliberate academic closure; no automatic merge or Phase 3 work is included.
