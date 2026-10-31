# Synchronous SRAM digital contract

Approved planning decisions implemented on 2026-10-30. The authoritative
architecture remains [technical_specification.md](technical_specification.md).
This document makes its digital behavior executable; it does not approve a
frequency, an analog phase generator or the complete physical macro.

## Interface and organization

| Signal | Direction | Meaning |
|---|---|---|
| `CLK` | input | Rising-edge request capture; falling-edge read capture |
| `ADDR` | input | 2/3/4/5 bits for depth 4/8/16/32 |
| `DATA[7:0]` | bidirectional | Write input / registered read output |
| `CSb`, `OEb`, `WEb` | input | Active-low access controls |
| `VDD`, `VSS` | bidirectional supply pins | Explicit; analog power is not simulated here |

Word width is always eight bits. The public `sram_model` has one parameter,
`DEPTH`, restricted to 4, 8, 16 or 32, defaulting to 4. Other values terminate
simulation with an explicit unsupported-depth error. The structural
`sram_4x8_wrapper` is fixed at four words. Larger physical decoder designs
remain open; their functional models do not establish physical implementation.

## Edge and bus semantics

| Requirement | Required behavior |
|---|---|
| DIG-01 | Capture `ADDR` and the requested operation on rising `CLK` |
| DIG-02 | Capture write `DATA` on that same rising edge |
| DIG-03 | Read only for `CSb/OEb/WEb=001`; write only for `010` |
| DIG-04 | All six remaining control values perform no access |
| DIG-05 | Complete the high-phase write by falling `CLK`; capture read output on falling `CLK` |
| DIG-06 | Drive the bus only if the captured operation and current controls both select read |
| DIG-07 | Changing live controls does not cancel or replace a captured request |
| DIG-08 | Retain the previous read register value until another read completes |
| DIG-09 | No reset or initialized memory; an unwritten read is unknown in the functional model |
| DIG-10 | No column mux, variable word width, unsupported depth or new public port |
| DIG-11 | Logical row mapping is `DEC[0]=00`, `[1]=01`, `[2]=10`, `[3]=11`; only valid high-phase access may select a row |

The write-at-falling-edge update is a **functional completion convention**:
the physical write acts during the high phase. The write data itself is
captured at the rising edge. The model must not resample external write data
at the falling edge. Read/write modes are exclusive, so same-port simultaneous
read/write collision semantics are not required.

The output-enable expression is:

```text
captured_read AND (NOT CSb) AND (NOT OEb) AND WEb
```

External output masking is combinational. It changes bus ownership, not the
captured transaction. Holding the previous result does not make the next read
valid early. If no read has completed, the register can be unknown. Before
the first request capture, unreset internal control state is also unknown;
known inactive live controls still force the bus to high impedance.

### Consecutive reads

| Time | Rising n | Falling n | Rising n+1 | Falling n+1 |
|---|---|---|---|---|
| Captured address | A | A | B | B |
| Read register | Previous | result(A) | result(A) | result(B) |
| DATA, while both read enables hold | Previous | result(A) | result(A) | result(B) |

```mermaid
sequenceDiagram
    participant Master
    participant Capture
    participant Array
    participant Output
    Master->>Capture: Address A and read controls before rising n
    Capture->>Array: Rising n captures A; access during high phase
    Array->>Output: Falling n captures result(A)
    Master->>Capture: Address B before rising n+1
    Note over Output: result(A) is retained during the next high phase
    Capture->>Array: Rising n+1 captures B
    Array->>Output: Falling n+1 captures result(B)
```

Input setup/hold and clock-to-output delays have no numeric value in this model.

### Read-to-write handoff

1. After receiving a read result, the external master changes controls away
   from read and keeps its data driver off.
2. The SRAM releases `DATA`; the master then drives write data with sufficient
   setup before the next rising edge and sufficient hold afterward.
3. The next rising edge captures the write. Later input changes cannot replace it.

No dead cycle is required in the logical model when these ownership rules
are satisfied. This is not a qualified Zero Bus Turn-around interface or an
instantaneous electrical release guarantee. Illegal overlapping external/SRAM
drivers are outside the legal stimulus contract.

## Architecture and physical boundary

The public behavioral view is `rtl/sram_model.v` (Verilog, not SystemVerilog).
The independently structured 4x8 wrapper uses a capture controller, an internal
macro interface and a falling-edge output register. Its macro simulation
substitute has combinational raw read data and falling-edge write completion.
This avoids an accidental extra cycle from recapturing registered inputs.

The logical `row_decoder_2to4` is a verification reference. It is not instantiated
as a replacement for Leonardo's selected 33-MOS dynamic decoder in the macro.
The physical macro boundary includes that decoder, wordline/write drivers,
array, precharge and sensing. PCLK, PRECH and sense timing must be implemented
and electrically qualified when binding the physical macro.

Control RTL uses edge-triggered registers without a dedicated FSM, reset,
simulation delays, or initialized array. The supply pins carry connectivity
only; voltage-dependent behavior is not represented.

## Verification and traceability

| Requirement | Executable evidence |
|---|---|
| DIG-01/02 | High-phase address/data disturbances; controller input-hold checks |
| DIG-03/04 | All eight control values; inactive write attempts and full readback |
| DIG-05 | Checks after rising and falling edges; wrong-edge mutant |
| DIG-06 | Undriven bus checks before host writes; live-control changes; missing-mask mutant |
| DIG-07 | Disable or change controls during high phase; operation still completes |
| DIG-08 | Previous-result checks at rising edge; all ordered address read pairs |
| DIG-09 | Read every unwritten location before the first write; four-state comparisons |
| DIG-10 | Verilog-2005 parse; fixed-width interfaces; rejected-depth tests |
| DIG-11 | Controller/logical-decoder unit test across 8 controls x 4 addresses |

Every memory regression includes all addresses, 20 data patterns (00, FF,
AA, 55, eight walking-one and eight walking-zero patterns), all 64 ordered
control transitions and at least 2,048 deterministic pseudorandom operations.
The scoreboard is transaction-level and does not reuse DUT helpers or hierarchy.
Comparisons use four-state semantics: unknown is expected for unwritten reads,
but fails a comparison against known written data.

The common testbench exercises the public model at all four depths and the
structural wrapper at depth four. Matching coverage is not a formal equivalence
proof; each view independently passes the same reference expectations.

The PRNG is a fixed 32-bit LCG, default seed `0x5A17`. Testbench delays schedule
stimuli and observations outside NBA updates; they are not ASIC timing limits.
All output checks run after sequential updates have settled.

## References and deliberate differences

- Butera, *OpenRAM: An Open-Source Memory Compiler*, UC Santa Cruz, 2013,
  sections 2.1.7 and 2.2: shared DATA, rising-edge write-data capture,
  falling-edge read register, and registered OEb. Our live output mask is an
  explicit adaptation, not a claim that this thesis used that mask.
  [Primary source](https://escholarship.org/content/qt2vv5q88z/qt2vv5q88z.pdf).
- Guthaus et al., ICCAD 2016, section 3, describes negative-edge write-data
  capture for its ZBT timing. That is not this project's write-input contract.
  [Primary source](https://escholarship.org/content/qt8x19c778/qt8x19c778_noSplash_b2b3fbbb57f1269f86d0de77865b0691.pdf).
- OpenRAM `stable/compiler/base/verilog.py`, file blob
  `c834898856ed7f52686c045d1687abb575b78b4c`, inspected 2026-10-30:
  separate DIN/DOUT, rising input capture, falling memory operations,
  arbitrary DELAY/T_HOLD and output invalidation after the rising edge.
  These delay values and invalidation policy are not imported.
  [Official source](https://github.com/VLSIDA/OpenRAM/blob/stable/compiler/base/verilog.py).

The phase-planning deck's DIN/DOUT signals are internal interfaces here, not
a public port rename. Its `.sv` model suggestion is fulfilled with a `.v`
deliverable; SystemVerilog is used only for verification. Completing these
digital fronts does not complete the original physical Phase 2 milestone.
