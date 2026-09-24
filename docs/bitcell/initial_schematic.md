# 6T bitcell: initial schematic notes

Status: draft schematic capture. This note records the intended initial topology;
`specs/technical_specification.md` remains the architectural source of truth.

The cell uses two cross-coupled CMOS inverters and two NMOS access devices.
`WL` controls both access devices; `BL` and `BLB` connect to the internal
storage nodes `Q` and `QB`. The nominal supply is 1.8 V.

| Device | Type | Drain | Gate | Source | Bulk | Role |
|---|---|---|---|---|---|---|
| M1 | `pfet_01v8` | Q | QB | VDD | VDD | Q pull-up |
| M2 | `nfet_01v8` | Q | QB | VSS | VSS | Q pull-down |
| M3 | `pfet_01v8` | QB | Q | VDD | VDD | QB pull-up |
| M4 | `nfet_01v8` | QB | Q | VSS | VSS | QB pull-down |
| M5 | `nfet_01v8` | Q | WL | BL | VSS | BL access |
| M6 | `nfet_01v8` | QB | WL | BLB | VSS | BLB access |

The captured schematic currently assigns `L=0.15 um`, `W=0.42 um`, and `nf=1`
to all six devices. These are provisional starting values, not validated cell
sizes. Xschem netlisting and SKY130/ngspice hold, read, write, and stability
checks are still required before the schematic can be considered functional.
Layout, DRC, extraction, and LVS have not been completed.
