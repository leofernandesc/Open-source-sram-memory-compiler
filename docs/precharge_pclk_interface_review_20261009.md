# Precharge schematic review and PCLK interface proposal — 2026-10-09

## Status and scope

This began as a read-only review of the older precharge snapshot on
`feature/peripherals`, a follow-up check of Danilo's newer candidate on
`origin/feat/sram-6t-cell`, and an integration proposal for the dynamic
decoder's `PCLK`. Danilo's W2.52 candidate is selected for Person 3's
integration, along with an initial phase timing point from the
measured sweep. The resulting decision and new verification are recorded in
the [phase decision report](row_decoder_precharge_pclk_decision_20261009.md).
That decision does not amend `specs/technical_specification.md` or modify
either owner's source; implementation with a real phase generator remains
open.

## Precharge schematic review

The checked-in source is `cells/precharge/precharge.sch` (SHA-256
`2331e0e438d037c62cc6e47498c7c89bec0fdecf06c4da8c39869e40da031f04`). A
read-only Xschem SPICE netlist was generated with:

```bash
./tools/sram-eda xschem -n -q -s --netlist_path /tmp \
  -N precharge_review.spice /work/cells/precharge/precharge.sch
```

The resulting file has `**.subckt precharge` with no ports. It lists the three
PMOS instances, but each instance has four distinct anonymous terminal nets
(`net2` through `net13`); none of the MOS terminals is connected to the labeled
schematic wires. This is not a usable or electrically testable precharge cell.

The source also contains a direct wire-graph short: the `BL` segment from
`(300,-160)` to `(450,-160)` continues into the `BLB` segment from
`(450,-160)` to `(600,-160)`, and the `PRECH` segment ends at the same
`(450,-160)` junction. Thus the intended BL, BLB, and PRECH nets meet in the
drawn wiring. The file uses `lab_pin.sym` labels but has no `ipin.sym` or
`iopin.sym` port symbols, which is consistent with the empty subcircuit
interface in the netlist.

**Conclusion for this checkout:** this older schematic cannot be used for
integrated simulation. The earlier integrated-read attempt stopped at its
netlisting. That conclusion applies only to the old copy on `feature/peripherals`;
it does not mean that no corrected precharge implementation exists.

## Danilo's newer precharge candidate

The follow-up cross-branch review found Danilo's updated source on
`origin/feat/sram-6t-cell`, tip `5dc00fe`. The corrected Xschem schematic was
introduced in `9611618`; the SPICE leaf and physical leaf work followed in
`8285968`, with the W2.52 physical candidate repaired/recheckpointed in
`962ebbf` and its G7 results recorded in `ad5c3dc`. This branch tip is not an
ancestor of `origin/develop`; the corrected source and physical evidence are not
yet part of `develop` or `feature/peripherals`. Both branches therefore have
different precharge files: the old path here is `cells/precharge/precharge.sch`,
while Danilo's updated source is `cells/precharge.sch` on his branch.

A temporary copy of Danilo's schematic was netlisted with Xschem. Its generated
subcircuit has formal ports `VDD BL BLB PRECH VSS` and the transistor
connections are:

```spice
XMPBL  BL  PRECH VDD VDD sky130_fd_pr__pfet_01v8 ...
XMPBLB BLB PRECH VDD VDD sky130_fd_pr__pfet_01v8 ...
XMEQ   BL  PRECH BLB VDD sky130_fd_pr__pfet_01v8 ...
```

The copy was generated from
`origin/feat/sram-6t-cell:cells/precharge.sch` and netlisted in `/tmp`:

```bash
git show origin/feat/sram-6t-cell:cells/precharge.sch |
  docker exec -i sram-xschem sh -c 'cat > /tmp/precharge_danilo.sch'
./tools/sram-eda xschem -n -q -s --netlist_path /tmp \
  -N precharge_danilo_review.spice /tmp/precharge_danilo.sch
```

This matches the intended three-PMOS topology and keeps `BL` and `BLB`
separate. The branch's canonical `cells/precharge.spice` schematic-equivalent
leaf uses `W=0.42 µm`. The physically qualified candidate is a separate
`layout/precharge/experimental_w2p52` implementation with `Wpre=2.52 µm` and
extracted PEX. Danilo's `docs/phase1_leaf_cell_closure.md` reports the physical
leaf with Magic DRC zero, unique Netgen LVS, PEX, and precharge Ceff PVT
`60/60` (`11.469724–13.064186 fF`). The G7 report also records integrated PEX
read and write matrices at `60/60` each. These are documented results from his
branch, not reruns in this review.

His candidate exposes `VSS` as an unused interface port; all three PMOS bulk
terminals are tied to `VDD`. Keep that port only if the shared leaf interface
requires it, and preserve the body ties to `VDD`.

Thus there is no need to redraw this cell from scratch. This candidate is
selected for Person 3's decoder integration. That choice uses the pinned PEX
input in this branch; it does not change André's source or declare a shared
team-wide source merge. The corrected candidate still does not supply a PCLK
phase generator for this branch's dynamic decoder.

For the intended three-PMOS topology, the corrected connectivity should be:

- `MPBL`: source and bulk to `VDD`, drain to `BL`, gate to active-low `PRECH`;
- `MPBLB`: source and bulk to `VDD`, drain to `BLB`, gate to the same `PRECH`;
- `MEQ`: source/drain between `BL` and `BLB`, bulk to `VDD`, gate to `PRECH`.

`BL` and `BLB` must remain separate nets and only connect through the channel
of `MEQ`. Formal Xschem ports are needed for `BL`, `BLB`, `PRECH`, and `VDD`.
If the project keeps a `VSS` port on this PMOS-only leaf for interface
consistency, it must remain separate from every PMOS body; whether that unused
port is required should be agreed with the cell owner. Danilo's corrected
schematic already meets this connectivity checklist in the read-only Xschem
netlist above; rerun the netlist and preserve the selected PEX evidence when a
chosen revision is integrated into the shared branch.

## PCLK polarity and proposed path

**Specified:** the decoder uses dynamic precharge. Its `PCLK` is low while the
internal decode nodes precharge and high while the selected branch evaluates.
The precharge cell's current `PRECH` interface is active low: low enables the
three PMOS devices. These two interfaces therefore have different roles and
should not be joined as one wire with an assumed common edge timing.

Proposed signal path:

```text
CLK, CSb/OEb/WEb, captured address and write data
                    │
          rising-edge capture and
       glitch-free access qualification
                    │
       non-overlap phase generation
             ┌──────┴──────┐
             │             │
       PCLK_DEC         PRECH_N
       decoder.PCLK     bitline precharge/equalizers
```

`PCLK_DEC` and `PRECH_N` are descriptive phase-source nets in this proposal;
they connect to the leaf pins `PCLK` and active-low `PRECH`, respectively.

The access qualifier is:

```text
VALID_ACCESS = !CSb && (OEb XOR WEb)
```

This is true for the specified read (`001`) and write (`010`) control vectors;
it is false for idle, disabled, and invalid vectors. Capture or latch this
qualification without glitches. Do not form PCLK by directly ANDing `CLK`
with live `CSb/OEb/WEb`, because a control transition around or after the
clock edge could create a runt evaluation pulse.

| Phase | `PCLK_DEC` | `PRECH_N` | Required behavior |
|---|---:|---:|---|
| Low clock phase; idle/disabled/invalid access | 0 | 0 | Decoder and bitlines precharge; no row is selected. |
| Valid rising edge, address/data settling interval | 0 | 1 | Release bitline precharge; keep decoder evaluation disabled. |
| Valid access evaluation | 1 | 1 | Evaluate the captured address; only its row may assert. |
| Falling edge and wordline turn-off interval | 0 | 1 | Stop decoder evaluation and allow the selected wordline to fall. |
| Remaining low phase | 0 | 0 | Re-enable bitline precharge/equalization after wordlines are inactive. |

For a valid access, `PRECH_N` rises after capture to release the bitlines.
`PCLK_DEC` rises later, after a characterized guard for address complements,
access qualification, and write-data/driver settling. At the falling edge,
`PCLK_DEC` falls first; `PRECH_N` falls only after the worst-case wordline
turn-off interval. This creates non-overlap on both edges and preserves
precharge during the low phase, including idle and disabled cycles. During an
invalid, idle, or disabled cycle, both signals remain low, so no dynamic row is
evaluated and the bitlines stay precharged.

The phase generator can use a low-phase-transparent access-enable latch (or an
equivalent glitch-free gate) and characterized edge-delay logic. It is phase
control, not a dedicated FSM. Buffering and routing for the decoder PCLK load
and the bitline precharge-gate fanout must be included in timing analysis.

## Timing evidence and limits

The earlier combined decoder/WL PEX study on `feature/peripherals` used an
**ideal** delayed PCLK and did not include Danilo's precharge PEX. Danilo's
separate G7 read/write matrices did include the W2.52 precharge PEX but did not
qualify the actual PCLK generator for this dynamic decoder. A follow-up
interface screen now combines the current decoder PEX, four WL-driver PEX
instances and eight copies of Danilo's W2.52 precharge PEX. It uses ideal PWL
sources for both PCLK and PRECH. The completed TT valid and invalid vectors,
selected slow-corner transitions, and FF address-target cases passed 26/26
cases. The smallest measured selected-WL-off interval before the 75%-VDD
precharge threshold was 254.477 ps with a nominal 1.8 ns turn-off guard. The
full method, data and limits are in the
[phase-interface report](row_decoder_precharge_phase_integration_20261009.md).

The earlier combined study's full SS phase sweep passed functional and
voltage screens at sampled capture-to-PCLK delays of 1.50, 1.80, 1.95, and
2.10 ns; the separate exploratory 250 ps literal guard passed 2/24, 13/24,
24/24, and 24/24 cases, respectively. The 1.95 ns point is only the earliest
passing sampled point for that experiment. It is not an approved delay,
frequency limit, or complete SRAM timing result. That earlier study did not
model the precharge cell, control capture circuit, or actual PCLK distribution.
The new bounded interface screen does not model a transistor-level control
generator or bitcell access path either. See the
[combined PEX report](row_decoder_capture_combined_pex_20261009.md).

The initial experimental timing choice is 2.10 ns from captured rising edge to
PCLK evaluation, a nominal 250 ps PRECH release lead before PCLK rises, and a
nominal 1.80 ns PRECH reassertion guard after PCLK falls. A follow-up screen
with Danilo's PEX passed at that setting; its measurements and limits are in
the [phase decision report](row_decoder_precharge_pclk_decision_20261009.md).
These are not specification limits. Characterize the real generator and its
loads over the required process/voltage/temperature conditions. Verify that:

1. captured address and controls are stable before `PCLK_DEC` rises;
2. bitline precharge is off before any wordline asserts;
3. all wordlines are inactive before `PRECH_N` re-enables precharge;
4. the low phase leaves enough time to restore both bitlines and decoder nodes;
5. invalid/idle/disabled controls never assert a row;
6. a precharge phase occurs before the first valid access after power-up.

The bounded phase-interface bench consumes Danilo's PEX as a pinned,
read-only input selected for Person 3's integration work. It does not merge or
modify the team-wide precharge source. In this branch, PCLK and PRECH are still
ideal testbench inputs because the transistor-level control generator is not
implemented. Neither this screen nor Danilo's separate G7 results establish
integrated SRAM timing or qualify the dynamic decoder with real control capture
and bitcell read/write behavior.
