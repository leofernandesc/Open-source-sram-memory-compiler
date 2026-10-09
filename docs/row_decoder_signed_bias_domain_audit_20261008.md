# Row decoder: signed device-bias and initialization audit

Date: 2026-10-08 · Branch: `feature/peripherals`
Scope: compact row-decoder PEX and its existing 4-WL-driver testbench

## Why this audit was added

The earlier decoder runner checked absolute terminal-difference magnitudes and
stored per-device signed extrema, but did not compare those signed values with
the documented ranges for each device polarity. Those two results answer
different questions. A magnitude below 1.95 V is not, by itself, proof that a
sample is inside the documented signed range for an NFET or PFET.

The SKY130 device documentation publishes the following operating ranges for
the 1.8 V devices:

| Device | `VGS` | `VDS` | `VBS` |
|---|---:|---:|---:|
| `nfet_01v8` | 0 to +1.95 V | 0 to +1.95 V | −1.95 to +0.30 V |
| `pfet_01v8` | 0 to −1.95 V | 0 to −1.95 V | −0.10 to +1.95 V |

These are published model operating ranges, not reliability limits or a
standalone signoff criterion. See the [SKY130 device documentation](https://github.com/google/skywater-pdk/blob/main/docs/rules/device-details.rst#L4-L100).

## Measurement method

The audit reads the archived ngspice transient waveforms for all 16 ordered
address pairs at 1 ps in FF (1.8 V, 125 °C) and SS (1.62 V, −40 °C), for both
the schematic baseline and current extracted PEX. It covers 45 MOS devices per
case: 29 decoder devices plus 16 devices in four unchanged WL drivers.

For each sample, it orients the external MOS subcircuit source to the
lower-potential diffusion terminal for an NFET and the higher-potential
diffusion terminal for a PFET, then derives terminal `VGS`, `VDS` and `VBS`.
The script does not save intrinsic BSIM4 states behind series/body resistances.
This is an engineering interpretation of reverse-mode
operation. The ngspice 44.2 BSIM4 implementation switches to `VGD` and `VBD`
when its polarity-normalized `VDS` is negative; see the [ngspice source](https://github.com/imr/ngspice/blob/ngspice-44.2/src/spicelib/devices/bsim4v5/b4v5ld.c#L983-L997).
It is still an external-terminal screening convention. The [subsequent review](row_decoder_analysis_review_20261008.md)
measured external/intrinsic differences in a targeted FF probe; the archived
audit is not an exact intrinsic channel-bias measurement or a PDK approval.

The script records full-transient extrema and a second window starting at 1 ns.
The 1 ns cutoff is diagnostic: it separates the UIC initialization interval
from the first PCLK event at 4.975 ns. It does not establish a general power-up
specification.

## Existing UIC matrix results

Across the FF and SS PEX matrices after 1 ns:

| Corner | NFET `VDS` range | PFET `VDS` range | NFET `VBS` range | PFET `VBS` range | PFET `VBS` margin to −0.10 V |
|---|---:|---:|---:|---:|---:|
| FF | 0 to +1.866488 V | −1.835330 to 0 V | −1.675746 to +0.040690 V | −0.079674 to +0.061886 V | 20.326 mV |
| SS | 0 to +1.716479 V | −1.707240 to 0 V | −1.198299 to +0.094323 V | −0.096479 to +0.029535 V | 3.521 mV |

Those `VDS` and `VBS` values stay within the listed ranges in this window. The
SS PFET `VBS` margin is only 3.521 mV in this deterministic run; noise,
mismatch, loading changes and a model guardband have not been included.

Signed `VGS` does not pass the published ranges in either corner. NFET samples
go negative while devices are off, reaching −1.532192 V in FF PEX and
−1.084485 V in SS PEX. PFET samples go positive, peaking at +0.079892 V in FF
and +0.096479 V in SS. The PFET peak occurs on a decoder/WL-driver gate during
dynamic-node movement; for example, FF PEX `x1.27` reaches +79.892 mV at
20.0265 ns. The absolute magnitudes are small and the logic screens pass, but
these signs lie outside the table's published operating ranges. They need
review with the PDK/model owner before claiming full model-domain qualification.
An out-of-range signed screen is not, by itself, evidence of a schematic wiring
error or a logic failure.

The complete post-startup `VGS` extrema for both stages are:

| Corner | Stage | NFET `VGS` min..max | PFET `VGS` min..max |
|---|---|---:|---:|
| FF | Schematic baseline | −1.403577..+1.941933 V | −1.941933..+0.141933 V |
| FF | Extracted PEX | −1.532192..+1.875388 V | −1.861607..+0.079892 V |
| SS | Schematic baseline | −0.963759..+1.740349 V | −1.766599..+0.120349 V |
| SS | Extracted PEX | −1.084485..+1.716479 V | −1.713823..+0.096479 V |

The schematic baseline also shows transient PFET `VBS` below −0.10 V: the
minimum is −0.141933 V in FF and −0.120349 V in SS. The extracted layout reduces
the corresponding post-initialization PEX minima to the ranges above.

In the operating-point FF `00→00` probe, baseline device `x1.m1` reaches
`VBS` = −0.141931 V at 10.1075 ns. At that sample its `A0B` diffusion is
1.941931 V while the tied bulk/supply is 1.8 V; the gate is near 0 V. The
same probe's PEX PFET `VBS` minimum is −0.077979 V. This is consistent with an
overshoot on the schematic `A0B` node that is damped by the extracted network;
it does not identify a rail short.

## UIC initialization artifact and one operating-point probe

The archived PEX deck starts with `.tran ... uic`. In the first FF `00→00`
waveform sample (0.00005 ns), the local PEX VDD taps range from 0.149716 to
0.857186 V, the four dynamic nodes are about 0.323–0.345 V, and the four DEC
outputs are about 0.345–0.352 V. The full-transient PFET `VBS` minimum is
−0.611637 V, outside the −0.10 V published lower bound. The UIC deck forces
the capacitive PEX network to start from its zero initial state while the
ideal supply is already at 1.8 V.

To check whether that first transient is an initialization artifact, the PEX
runner gained an opt-in `--initial-operating-point` mode. Its default remains
UIC, so previous matrices retain their original setup. One FF `00→00` case was
rerun with the DC operating point:

- baseline and PEX both completed with exit code 0; the case passed its
  functional checks and reported no terminal-magnitude or dynamic-node upper
  screen findings. The ngspice logs had no `Error:` lines and contained 52
  baseline / 61 PEX model warnings, including the previously documented FF
  `A2` clamp and negative `Eta0`/`Pdibl` warnings;
- at time zero, local PEX VDD taps are 1.799946–1.799998 V, internal `N0`–`N3`
  are about 1.8 V and `DEC0`–`DEC3` are about 0.23 mV;
- PFET `VBS` over the full PEX waveform is −0.077979 to +0.057088 V, with no
  samples outside its published range;
- during the settled first evaluation, selected `DEC0` is at least 1.799989 V
  and `WL0` at least 1.799616 V; unselected DEC/WL outputs remain below
  0.15 mV. During precharge, the maximum DEC output is 0.300 mV and the
  minimum dynamic-node voltage is 1.789642 V.

This single-case result supports the interpretation that the large sub-ns
PFET `VBS` excursion in the UIC PEX waveform is a forced initial-condition
transient. It does not establish the no-UIC result for every address pair or
corner. The no-UIC case still has negative NFET and positive PFET `VGS`
samples, so the published signed `VGS` range question remains open.

The remaining FF PEX `VGS` extrema in this probe are traceable to specific
nodes:

| Device and time | Measured terminal values | Interpretation |
|---|---|---|
| NFET `x1.22`, 4.9975 ns, `VGS` = −1.479475 V | Gate `A0T.t3` = 0.0104 V; diffusion nodes `EVAL_GND.t3` = 1.4899 V and `net2.t1` = 1.5876 V; local `PCLK.t3` = 0.7929 V. | The input gate is low while both stack nodes retain charge during the PCLK edge. This is consistent with an off evaluation branch; it does not resemble an accidental gate-to-rail short. |
| PFET `x1.27`, 20.0265 ns, `VGS` = +0.078286 V | Gate `N2.t3` = 1.8783 V; source-side VDD diffusion = 1.8000 V; `DEC2.t0` = 0.0055 V; local `PCLK.t3` = 1.8002 V. | The dynamic node is about 78 mV above local VDD while the unselected DEC output remains low, consistent with clock/feedthrough overshoot. |

These node readings are measured from the archived raw waveform; the circuit
explanations are inferences. They make a wiring mistake less likely for these
two extrema, while leaving PDK signed-range acceptance unresolved.

## Reproduction and evidence

The complete FF/SS postprocessing is reproducible from retained raw waveforms:

```bash
python3 sims/row_decoder/audit_signed_device_domain.py --profiles fast slow
```

The one-case operating-point probe was generated with:

```bash
SRAM_EDA_CONTAINER=sram-pex-diag-20261008 ./tools/sram-eda python3 \
  sims/row_decoder/run_row_decoder_pex_contract.py \
  --profiles fast --cases fast_00_to_00 --max-step-ps 1 --workers 1 \
  --timeout-s 900 --initial-operating-point \
  --output-root sims/row_decoder/results/row_decoder_op_init_probe_fast_00_to_00

python3 sims/row_decoder/audit_signed_device_domain.py \
  --profiles fast \
  --matrix-root sims/row_decoder/results/row_decoder_op_init_probe_fast_00_to_00 \
  --expected-cases 1 \
  --output-json sims/row_decoder/results/row_decoder_op_init_probe_fast_00_to_00/signed_domain_audit.json \
  --output-csv sims/row_decoder/results/row_decoder_op_init_probe_fast_00_to_00/signed_domain_audit.csv
```

The [FF/SS signed-bias CSV](../sims/row_decoder/results/signed_device_domain_audit.csv)
and [JSON with hashes and per-case provenance](../sims/row_decoder/results/signed_device_domain_audit.json)
contain the full matrix screen. The one-case operating-point result is in its
[comparison](../sims/row_decoder/results/row_decoder_op_init_probe_fast_00_to_00/comparison.csv),
[PEX manifest](../sims/row_decoder/results/row_decoder_op_init_probe_fast_00_to_00/pex/manifest.json),
and [signed-bias audit](../sims/row_decoder/results/row_decoder_op_init_probe_fast_00_to_00/signed_domain_audit.json).
Raw `.raw` files remain ignored by Git; their SHA-256 values are recorded in
the JSON audit.

At the time this audit was first drafted, the TT raw waveforms and full
operating-point matrix were still missing. The complete 96-simulation,
three-corner baseline/PEX matrix has since been run at 1 ps, with a targeted
0.5 ps refinement of the FF screen cases. Results and reproduction details
are in the [completed operating-point matrix report](row_decoder_opinit_matrix_20261008.md).
The PEX hash remains
`8ee6b99aabf94bde9a1de2a13f0c040cda41dd55bb9568672e38a7f6bb54a6dc`; no
new extraction was performed.

## Source-level review of model ranges and FF warnings (2026-10-08)

The public SKY130 device reference calls the listed values the operating
voltages “where SPICE models are valid.” For the 1.8 V NFET it lists `VGS` and
`VDS` from 0 to +1.95 V and `VBS` from −1.95 to +0.30 V; for the PFET it lists
`VGS` and `VDS` from 0 to −1.95 V and `VBS` from −0.10 to +1.95 V. These are
model-validity ranges in that reference, not a standalone silicon reliability
or lifetime limit. The PDK reference does not publish a separate `VGD` range.
See the [SKY130 device reference](https://github.com/google/skywater-pdk/blob/main/docs/rules/device-details.rst#L4-L100).

The ngspice 44.2 BSIM4 source uses the named intrinsic source node when its
polarity-normalized `VDS` is nonnegative. When it is negative, the code
reverses channel orientation and evaluates with `VGD` and `VBD`. This supports
the audit's use of the lower-potential diffusion as the NFET effective source
and the higher-potential diffusion as the PFET effective source when
reconstructing source-oriented external terminal biases. The simulator's
voltage differences use its internal `dNodePrime`, `sNodePrime`, `gNodePrime`
and `bNodePrime`; see the [node differences in the load code](https://github.com/imr/ngspice/blob/ngspice-44.2/src/spicelib/devices/bsim4v5/b4v5ld.c#L364-L372).
The external-terminal reconstruction is not an exact measurement of those
intrinsic states. Source/drain reversal support does not establish that every
transient bias is covered by the published model range.
See [ngspice's BSIM4 load code](https://github.com/imr/ngspice/blob/ngspice-44.2/src/spicelib/devices/bsim4v5/b4v5ld.c#L983-L997).

This clarifies the two decoder findings:

- Negative NFET `VGS` and positive PFET `VGS` in the audit are outside the
  signed `VGS` intervals published for the device models. The sampled states
  are consistent with temporarily charged internal stack nodes and small
  dynamic-node feedthrough while those devices are off. That is an inference
  from the measured node waveforms, not proof of model accuracy or inaccuracy
  in those conditions, and not evidence by itself of a schematic wiring
  fault.
- The repeatable FF baseline maximum `|VGD| = 1.954674 V` is 4.674 mV above
  the runner's custom 1.95 V terminal-magnitude screen. Because the published
  table does not specify `VGD`, this is a diagnostic requiring review, not a
  direct violation of a published `VGD` limit or a reliability signoff result.
  At the refined FF `11→00` sample for `x1.m12`, the named-terminal values are
  `VDS=+1.284323 V`, `VGS=−0.670351 V`, and `VGD=−1.954674 V`. Since `VDS` is
  positive for this NFET's external terminals, the external effective source
  is its named source. The subsequent probe reads the model state and finds
  intrinsic `VGS=−0.674755 V` at this same sample, compared with the external
  `−0.670351 V`. The drain-referenced `VGD` screen is separate from both
  `VGS` measurements. All corresponding PEX samples remain below the custom
  screen. The absence of a separate `VGD` row in this public table does not
  establish acceptable gate/drain stress or an exemption from electrical
  qualification.

The FF logs identify these as BSIM 4.5 parameter checks. The tagged ngspice
44.2 source shows that `A2 > 1` is actively clamped to 1 and `A1` is set to 0
by the check routine. The same routine warns when `Eta0`, `Pdibl1` or
`Pdibl2` is negative but does not modify those values in those checks. The
FF simulations therefore completed without fatal errors, but their results
include the ngspice `A2`/`A1` adjustment and the negative parameters that the
model checker merely warns about. See the [BSIM4 parameter checks for `Eta0`
and `A2`](https://github.com/imr/ngspice/blob/ngspice-44.2/src/spicelib/devices/bsim4v5/b4v5check.c#L471-L498)
and [`Pdibl1`/`Pdibl2`](https://github.com/imr/ngspice/blob/ngspice-44.2/src/spicelib/devices/bsim4v5/b4v5check.c#L566-L575).

The retained matrix manifest records ngspice 44.2 and hashes the recursive
SKY130 model include closure. Installed PDK metadata identifies open_pdks
1.0.493 at commit `0fe599b2afb6708d281543108caf8310912f54af` and the
`sky130_fd_pr` source at commit `afc63d29f811b65b9888b2133fd3348eefc92046`.
The source review narrows the concern to model
domain and model-card handling: the archived waveforms and unique LVS match do
not indicate a decoder logic or connectivity failure. The model maintainer or
advisors still need to accept the use of these signed off-state biases and the
FF model adjustments for this project before sizing can be called fully
qualified.

## Review correction and remaining work before electrical closure

The [review of the latest analyses](row_decoder_analysis_review_20261008.md)
reproduces the archived numerical results and records a new two-device FF
intrinsic-state probe. Signed external-terminal findings remain useful, but
must not be described as exact intrinsic BSIM4 biases. Project acceptance is a
condition for final qualification, rather than a blanket prerequisite for
collecting further current-sizing characterization data.

1. Obtain model-maintainer/advisor acceptance of the effective-source
   convention, signed off-state `VGS` excursions, FF BSIM4 parameter handling,
   and the diagnostic `VGD` screen. The source-level review above is complete;
   the project's interpretation and acceptance margin remain unresolved.
   Capture/PCLK, noise, retention and broader PVT characterization can proceed
   in parallel with that review. Do not change transistor sizes solely to
   make the custom `VGD` screen green.
2. If review confirms a real operating-range issue or sets a stricter
   acceptance criterion, investigate the identified devices and transitions,
   then rerun the affected functional/electrical matrices. Update layout,
   DRC/LVS and PEX only if the physical design changes.
3. Keep the 4×8 physical-row check separate from decoder-leaf closure. The
   current PEX replaces only the decoder; four WL drivers and 17.4 fF per-row
   loads remain in the testbench. Replace that estimate with the extracted
   bitcell-row load when the approved physical bitcell is available.

The supported conclusion is: **all three corners pass the recorded
functional operating-point matrices, and the current DRC/LVS/PEX artifacts
are unchanged; signed model-domain acceptance and physical-row electrical
closure remain open.**
