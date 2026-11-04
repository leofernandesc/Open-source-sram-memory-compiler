# Phase 2 digital/physical binding contract

The technical specification and `sram_4x8_digital.md` remain authoritative.
This contract fixes connectivity and sequencing, not a qualified frequency.
The selected six leaves are read-only inputs from `release/phase1_current.json`.

## Hierarchy and pin binding

`sram_4x8_wrapper` is the public SRAM. Its custom instance `sram_4x8_macro`
contains 32 bitcells, one 33-MOS dynamic decoder, four WL drivers, eight
precharge cells, eight write drivers, eight sense amplifiers and new phase
glue. This is 401 leaf MOS before glue. Input/output capture registers and
external DATA tri-states are outside the core, inside the public SRAM.

| Boundary pin | Direction | Electrical/functional responsibility |
|---|---|---|
| CLK | input | Transaction clock; rising request, falling output capture |
| ADDR_Q[1:0] | input | Registered A1:A0; stable until evaluation has reset |
| DIN_Q[7:0] | input | Registered write word; supply complements locally |
| READ_Q, WRITE_Q | input | Active-high, mutually exclusive captured requests |
| DOUT_RAW[7:0] | output | Full-level resolved data meeting output FF setup/hold |
| VDD, VSS | supply | Explicit 1.8-V core supply and ground |

The public pins remain CLK, ADDR[1:0], DATA[7:0], CSb, OEb, WEb, VDD, VSS.
No reset, FSM, replica bitline, column mux or data-valid pin is introduced.
READ_Q/WRITE_Q can remain high in the low phase: they never directly enable
wordlines or write paths without phase qualification.

| Local signal | Polarity | Producer and consumer |
|---|---|---|
| PCLK | Low precharges decoder, high evaluates | Phase glue -> dynamic decoder |
| PRECH | Low precharges/equalizes BL/BLB | Phase glue -> eight precharge leaves |
| SCLK | Low samples, high regenerates | Delayed read phase -> eight sense leaves |
| WE | High drives bitlines | Qualified WRITE_Q -> eight write leaves |
| WL[0:3] | High selects exactly one row | Qualified DEC -> frozen WL drivers |
| DIN_B[7:0] | Complement of DIN_Q | Local inverters -> write DATA_B pins |
| SA_OUT | Same-polarity read result | Sense output -> DOUT_RAW |

Leaf positional orders are read from frozen `.subckt` declarations and bound
by formal pin name. In particular DEC3 precedes DEC2 in the decoder formal
list, but DEC0/1/2/3 select addresses 00/01/10/11. VPWR/VPB bind to VDD and
VGND/VNB to VSS on standard cells. Body connections are part of LVS.

## Required sequence and measurable acceptance

1. Supply ramps with CLK low and external controls inactive; complete initial
   decoder and bitline precharge. Clock inactive controls to establish known
   captured requests before the first active transaction.
2. On rising CLK capture address, operation and write data. Release bitline
   precharge; wait for registered address/complements to settle before PCLK.
3. Enable only the selected WL for valid high-phase access. For writes, drive
   the captured data without precharge contention. For reads, develop BL/BLB
   differential before SCLK regeneration; do not directly use READ_Q as SCLK.
4. DOUT_RAW must settle before the local falling output-capture edge and remain
   valid through its hold interval. Include actual FF input loading and local
   clock arrival. Terminate WL/write access before bitline precharge resumes.
   Do not resample/reset the sense result early enough to violate output hold.
5. Complete precharge and dynamic-node reset before the next evaluation.

The implemented benchmark uses a **20-ns experimental clock**, 10-ns high/low
phases, a 1-ns supply ramp, 50-ps source transitions and two initial inactive
conditioning cycles. These are recorded simulation conditions, not approved
Fmax, minimum startup duration or external setup/hold specifications. The
selected HD output register is `dfxtp_1` with a physically inverted clock.
Record measured delays with actual loading, local clocks, corner and supply
in the electrical receipt. Historical decoder delays are seeds, not whole-macro timing.
Use an actual mapped output-FF transistor model for core tests where possible;
any reduced load/capture model must state its approximation. Repeat with the
physically integrated registers and clock routing before top-level acceptance.

For the routed benchmark, WL must be below 20% of VDD before PRECH falls
below 80% (precharge conduction screen); the same 20%/80% exclusion applies
to WE versus PRECH. Complete low-level precharge, inactive PCLK/SCLK/WE and
low wordlines are required in the late-low-phase window 18..19 ns after
each public rising edge. This reserves the final nanosecond before the next
capture in this experiment. An inherited 0.5-ns WL release deadline after the
external falling edge is not a specification: actual local clock arrival is
measured, and release must instead satisfy the explicit phase ordering.

## Startup, bus and unknown state

There is no reset and no known initial stored word. Do not `.ic` or force
bitcell/FF/sense internal nodes to obtain a passing startup or cyclic read.
Check first-write/readback, first-unwritten-read without a known-data
expectation, idle conditioning and recovery after inactive cycles. Report
the tested ramp and clock conditions; nominal startup is not a statistical
power-up guarantee. Known inactive live controls must release the public bus.

Public DATA drive = captured READ_Q AND live (CSb,OEb,WEb = 001). Changing
live controls masks the bus without cancelling the internal captured access.
The previous read register is retained until another falling-edge read capture.
External masters must release/settle ownership before driving write data.

## Independent acceptance gates

- F2-DIG: mapped HD capture/control/tri-state; exactly one storage black box;
  no unexpected latches/unmapped primitives; power-aware zero-delay GLS using
  the existing independent scoreboard. No complete SRAM timing closure claim.
- CORE: generated 4x8 custom layout, DRC, expanded parameter-aware LVS and
  real transistor write/read, including startup and capture-load checks.
- F2-FIS: connected/routed core plus digital cells, final GDS reimport DRC/LVS,
  and repeated electrical access/capture on delivered connectivity.

The graph-to-layout/reference consistency check is supplemented by a separate
four-row/eight-column topology audit and deliberate connection/W/L defects.
LVS connectivity extraction is required now; detailed RC PEX, full PVT/Monte
Carlo characterization and characterized Liberty remain later work. Open
advisor decisions and Phase 1 model-coverage limitations remain documented.
