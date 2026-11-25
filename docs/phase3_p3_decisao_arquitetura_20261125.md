# P3 — decisão técnica de arquitetura da SRAM 4×8

Data: 25/11/2026  
Decisão técnica local: selecionar a **v6 híbrida, com três StrongARM**, como geometria física de referência para concluir a Fase 3 da macro 4×8.

## Base da decisão

A v6 é a única das duas variantes comparadas com uma geometria física correspondente e vistas coerentes identificadas. O GDS mede 540 × 380 µm. A verificação persistida apresenta DRC=0 e LVS `UNIQUE_MATCH` para 1.785 MOS. O relatório de verificação tem SHA-256 `6aba22a3c66867bc85f3c546a43a5aa253db44ae782d7629df5c54074274552b`.

| Vista | SHA-256 |
|---|---|
| GDS | `315c2ebceb2bc4cf258fa63be2279843805db3010637d0c273aea9db12813e37` |
| LEF | `39f09e853f89e7693523588c5c2d28fb217c8c9710fd18cd09b2bd813be0d5c7` |
| PEX distribuída | `a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f` |
| Binding físico usado nos replays | `3b6f7205476b79d02754ba081a7d2eb2ef9d372670daf26067d3d0cb5745e76d` |

A candidata de oito StrongARM tem replays funcionais e decisão de P2 favoráveis no envelope RC usado, mas cinco núcleos e seus buffers são virtuais. Não há GDS/LEF/netlist/PEX de oito StrongARM para sustentar um fechamento físico nesta fase. A v6 permite concluir a validação da geometria realmente extraída e preserva o fallback físico conhecido.

## Escopo e condição de fechamento

Esta decisão congela a identidade física de trabalho para P4 e P5. Ela não representa aceite externo da equipe nem qualificação elétrica. O aceite da equipe deve ser anexado ao registro de revisão. Uma alteração de geometria ou binding invalida os recibos P4 e exige repetir os checks físicos afetados.

P4 está fechado tecnicamente: os replays integrados de 370 ns e C250 passam em TT/SS/FF na PEX v6. Os recibos e resultados C250 estão no relatório P4.

## Evidência

- Comparação das variantes: [phase3_comparacao_arquiteturas_20261125.md](phase3_comparacao_arquiteturas_20261125.md).
- Verificação GDS/DRC/LVS: `../phase3_evidence_20261124/build/phase3/strongarm_triple_20261122/physical/macro_v6/gds_check/results.json`.
- P4 e recibos integrados: [phase3_p4_validacao_pex_v6_20261125.md](phase3_p4_validacao_pex_v6_20261125.md) e `../build/phase3/phase3_p4_v6_status_20261125.json`.

