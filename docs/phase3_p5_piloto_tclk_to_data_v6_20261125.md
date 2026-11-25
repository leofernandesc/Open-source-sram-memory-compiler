# P5 — piloto de tCLK_TO_DATA na v6 física

Data: 25/11/2026. Relatório reprodutível: [`build/phase3/timing_v6_tclk_to_data.json`](../build/phase3/timing_v6_tclk_to_data.json), SHA-256 `8d829a325346dd593857e76cbb744d6e9361ba32df416f7cbcbb907fad3fc68a`. O extrator é [`tools/phase3_timing_v6_transition_pilot.py`](../tools/phase3_timing_v6_transition_pilot.py), SHA-256 `b48581a5953a76908b56c18dd9a00086ffc90afa9f6f0446383cc9bfbc55cb3f`.

O cálculo usa as nove leituras integradas em cada corner, ligadas à PEX v6 `a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f`, a 1,8 V, 27 °C e 10 fF por lane. Para cada lane cuja DATA estava no trilho oposto imediatamente antes da descida pública de CLK, o instante DATA50 foi interpolado linearmente entre amostras nativas. A validade posterior foi confrontada com o observador integrado pinado. Lanes sem transição após essa borda são mantidos como `NOT_CHARACTERIZED`.

| Corner | Transições medidas | Lanes sem transição | tCLK_TO_DATA mínimo | Médio | Máximo |
|---|---:|---:|---:|---:|---:|
| TT | 48/72 | 24 | 534,917 ps | 557,962 ps | 589,701 ps |
| SS | 48/72 | 24 | 789,890 ps | 822,604 ps | 866,222 ps |
| FF | 48/72 | 24 | 396,108 ps | 413,440 ps | 437,783 ps |

É um piloto de um único domínio nominal e de transições que ocorreram no protocolo integrado. Não caracteriza arcos completos, polaridades/cargas/slews alternativos, tDIS por controle, setup/hold, limite máximo público ou tabelas Liberty. O estado elétrico global continua `NOT_CHARACTERIZED`.
