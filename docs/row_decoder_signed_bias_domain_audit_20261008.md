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
standalone signoff criterion. See the [SKY130 device documentation](https://github.com/google/skywater-pdk/blob/main/docs/rules/device-details.rst#L196-L248).

## Measurement method

The audit reads the archived ngspice transient waveforms for all 16 ordered
address pairs at 1 ps in FF (1.8 V, 125 °C) and SS (1.62 V, −40 °C), for both
the schematic baseline and current extracted PEX. It covers 45 MOS devices per
case: 29 decoder devices plus 16 devices in four unchanged WL drivers.

For each sample, it orients the MOS source to the lower-potential diffusion for
an NFET and the higher-potential diffusion for a PFET, then derives `VGS`,
`VDS` and `VBS`. This is an engineering interpretation of reverse-mode
operation. The ngspice 44.2 BSIM4 implementation switches to `VGD` and `VBD`
when its polarity-normalized `VDS` is negative; see the [ngspice source](https://github.com/imr/ngspice/blob/ngspice-44.2/src/spicelib/devices/bsim4v5/b4v5ld.c#L3923-L3948).
It is still a screening convention, not a PDK model-owner approval.

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

The TT full-matrix raw waveforms are not present in the archived results. A
full three-corner operating-point matrix would run 96 ngspice cases and should
be done on the stronger machine before making a cross-corner signed-domain
claim. For each profile, use a separate output root, then run the audit with
`--matrix-root <root> --expected-cases 16`. Current PEX hash remains
`8ee6b99aabf94bde9a1de2a13f0c040cda41dd55bb9568672e38a7f6bb54a6dc`; this
audit did not perform a new extraction.

## Remaining work before electrical closure

1. On the stronger machine, generate the full 1 ps operating-point matrices
   for TT, SS and FF. Each profile runs 16 ordered address pairs for both
   baseline and PEX (32 ngspice runs); all three profiles total 96 runs. Keep
   the current PEX hash and 17.4 fF WL testbench load, and use new output roots
   so the original UIC evidence is preserved. This sequential loop runs each
   profile and audits it before moving on:

   ```bash
   for profile in tt slow fast; do
     root="sims/row_decoder/results/compact_decoder_full_${profile}_opinit_matrix_1ps"
     ./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py \
       --profiles "$profile" --all-address-pairs --max-step-ps 1 --workers 1 \
       --timeout-s 900 --initial-operating-point --output-root "$root"
     ./tools/sram-eda python3 sims/row_decoder/audit_signed_device_domain.py \
       --profiles "$profile" --matrix-root "$root" --expected-cases 16 \
       --output-json "$root/signed_domain_audit.json" \
       --output-csv "$root/signed_domain_audit.csv"
   done
   ```

   `tools/sram-eda` uses the `sram-xschem` container by default. If that
   container is named differently on the stronger machine, set
   `SRAM_EDA_CONTAINER` to the project container that mounts this checkout at
   `/work`; the tool's environment requirements are in `tools/ENVIRONMENT.md`.

2. Review the effective-source convention, the PDK's published bias ranges,
   and the FF BSIM4 parameter warnings with the SKY130 model maintainer or
   project advisors. Record an agreed interpretation and acceptance margin.
   The present screen is a conservative engineering interpretation, not a
   signoff rule. Do not change transistor sizes solely to make this report
   green before that review; if the review confirms a real operating-range
   issue, investigate the devices and transitions identified in the CSV/JSON,
   then rerun the affected functional and PEX matrices.

3. Keep the 4×8 physical-row check separate from decoder-leaf closure. The
   current PEX replaces only the decoder; four WL drivers and 17.4 fF per-row
   loads remain in the testbench. Replace that estimated load with the
   bitcell-row extracted load when Danilo's approved physical bitcell is
   available. No new extraction is needed unless the decoder layout changes
   or the physical row is added to the extraction scope.

Until these items are addressed, the supported conclusion is: **the retained
decoder passes its recorded functional 16-pair matrices and current DRC/LVS,
but full signed model-domain and physical-row electrical closure remain open.**
