# Rejected import cache

The intended 0.84 um keeper schematic was initially paired with stale 0.42 um PCells.
Primitive-MOS LVS rejected all four keeper widths. This PEX is invalid for the 0.84 um schematic.
It was never used as a qualified 0.84 um electrical input.
The builder now uses a distinct import top and requires dimension-aware LVS before R-C extraction.
