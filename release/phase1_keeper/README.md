# Phase 1 selected keeper revision — 2026-10-29

Exactly six leaves. Leonardo's dynamic decoder is retained and hardened with four feedback PMOS keepers.
The five other selections are identical to the original six-cell freeze.

| Cell | MOS | SCH | SYM | SPICE | MAG | PEX | Physical result |
|---|---:|---|---|---|---|---|---|
| bitcell_6t | 6 | [SCHEMATIC](../../release/phase1/cells/bitcell_6t/bitcell_6t.sch) | [SYMBOL](../../release/phase1/cells/bitcell_6t/bitcell_6t.sym) | [SPICE](../../release/phase1/cells/bitcell_6t/bitcell_6t.spice) | [LAYOUT](../../release/phase1/cells/bitcell_6t/bitcell_6t.mag) | [PEX](../../release/phase1/cells/bitcell_6t/bitcell_6t_pex.spice) | [result](../../release/phase1/verification/bitcell_6t/result.json) |
| sense_amp | 7 | [SCHEMATIC](../../release/phase1/cells/sense_amp/sense_amp.sch) | [SYMBOL](../../release/phase1/cells/sense_amp/sense_amp.sym) | [SPICE](../../release/phase1/cells/sense_amp/sense_amp.spice) | [LAYOUT](../../release/phase1/cells/sense_amp/sense_amp.mag) | [PEX](../../release/phase1/cells/sense_amp/sense_amp_pex.spice) | [result](../../release/phase1/verification/sense_amp/result.json) |
| precharge | 3 | [SCHEMATIC](../../release/phase1/cells/precharge/precharge.sch) | [SYMBOL](../../release/phase1/cells/precharge/precharge.sym) | [SPICE](../../release/phase1/cells/precharge/precharge.spice) | [LAYOUT](../../release/phase1/cells/precharge/precharge.mag) | [PEX](../../release/phase1/cells/precharge/precharge_pex.spice) | [result](../../release/phase1/verification/precharge/result.json) |
| wl_driver | 4 | [SCHEMATIC](../../release/phase1/cells/wl_driver/wl_driver.sch) | [SYMBOL](../../release/phase1/cells/wl_driver/wl_driver.sym) | [SPICE](../../release/phase1/cells/wl_driver/wl_driver.spice) | [LAYOUT](../../release/phase1/cells/wl_driver/wl_driver.mag) | [PEX](../../release/phase1/cells/wl_driver/wl_driver_pex.spice) | [result](../../release/phase1/verification/wl_driver/result.json) |
| write_driver | 10 | [SCHEMATIC](../../release/phase1/cells/write_driver/write_driver.sch) | [SYMBOL](../../release/phase1/cells/write_driver/write_driver.sym) | [SPICE](../../release/phase1/cells/write_driver/write_driver.spice) | [LAYOUT](../../release/phase1/cells/write_driver/write_driver.mag) | [PEX](../../release/phase1/cells/write_driver/write_driver_pex.spice) | [result](../../release/phase1/verification/write_driver/result.json) |
| row_decoder | 33 | [SCHEMATIC](../../release/phase1_keeper/cells/row_decoder/row_decoder.sch) | [SYMBOL](../../release/phase1_keeper/cells/row_decoder/row_decoder.sym) | [SPICE](../../release/phase1_keeper/cells/row_decoder/row_decoder.spice) | [LAYOUT](../../release/phase1_keeper/cells/row_decoder/row_decoder.mag) | [PEX](../../release/phase1_keeper/cells/row_decoder/row_decoder_pex.spice) | [result](../../release/phase1_keeper/verification/row_decoder/result.json) |

The [electrical review](../../sims/row_decoder/results/keeper_review_20261029/summary.json) records 48 address cases and 30 crossed PVT points.
Functional and experimental terminal-magnitude checks do not establish independent off-state model accuracy, statistical yield or foundry reliability.
See [engineering analysis](../../docs/row_decoder_robustness_20261029.md). The [29-MOS freeze](../phase1/README.md) remains byte-for-byte unchanged.

Read-only audit: `python3 tools/freeze_keeper_revision.py --check`.
