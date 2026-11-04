# Phase 2 TT experiment, not a qualified public timing contract or Fmax.
# Same clock as the original routed prototype: period 20 ns, high phase 10 ns.
create_clock -name CLK -period 20 -waveform {0 10} [get_ports CLK]
# Request capture is rising; output FFs see the physically inverted clock.
# The rising-to-falling budget is about half a cycle before actual margins.
# IO delays, uncertainty, macro arcs/caps and numeric operating limits remain
# uncharacterized. They are intentionally unspecified, not silently zeroed.
