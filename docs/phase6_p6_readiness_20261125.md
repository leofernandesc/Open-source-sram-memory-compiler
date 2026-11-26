# P6/D1 — prontidão dimensional e baseline de área

**Data:** 25/11/2026  
**Checkout:** `integration/phase3-danilo-ss`, HEAD `0ede0345`, 10 commits à frente do ref local `origin/integration/phase3-danilo-ss`; worktree limpo antes deste registro.  
**Status:** inventário concluído; P6/D1 ainda não fechado. Nenhum GDS, LEF, PEX ou circuito físico 8×8/32×8 foi criado nesta etapa.

## Escopo e nomenclatura

A revisão atual do plano usa P0–P5 para a entrega 4×8 e P6/D1 para disponibilizar e caracterizar 8×8 e 32×8. A tabela histórica P0–P10 do mesmo arquivo chama a qualificação física de P6; esse gate corresponde ao P4 atual e já tem fechamento técnico na identidade v6. O plano foi anotado para explicitar essa colisão. A otimização de área é uma frente exploratória opcional e não substitui P6/D1.

## Inventário por dimensão

| Dimensão | O que existe neste checkout | O que falta para P6/D1 |
|---|---|---|
| 4×8 | Modelo funcional genérico, wrapper, macro física v6, GDS/LEF, DRC/LVS/PEX e replays C250/integrados TT/SS/FF. P4 fechado tecnicamente. | Aceite formal da arquitetura, fechamento P5 e revisão independente. |
| 8×8 | Execuções digitais arquivadas em `reports/digital/phase2_final_review/logs/model_8x8.txt`; `rtl/sram_model.v` aceita `DEPTH=8`. | Decoder e periferia para 3 bits de endereço; netlist/circuito físico; GDS, LEF, DRC, LVS, PEX e caracterização próprios. |
| 32×8 | Execuções digitais arquivadas em `reports/digital/phase2_final_review/logs/model_32x8.txt`; `rtl/sram_model.v` aceita `DEPTH=32`. | Decoder e periferia para 5 bits de endereço; netlist/circuito físico; GDS, LEF, DRC, LVS, PEX e caracterização próprios. |

Os logs digitais 8×8/32×8 demonstram somente o modelo comportamental: registram PASS com profundidade 8 e 32. Não são evidência de macro transistor-level, layout ou desempenho elétrico. O contrato `characterization/phase3` aceita os nomes das configurações, mas declara que isso não implica circuitos físicos correspondentes. A especificação requer dados caracterizados próprios para pelo menos 8×8 e 32×8; resultados da v6 4×8 não podem ser extrapolados.

## Baseline física preservada para estudo de área

A cópia de preservação `phase3_evidence_20261124` contém as fontes editáveis e as vistas seladas da v6. Uma cópia de trabalho isolada foi criada em `build/phase6_area_p6_20261125/baseline/manifest.json`; os 11 artefatos copiados conferem com os hashes do snapshot e com a identidade P3/P4.

| Vista | SHA-256 | Estado de referência |
|---|---|---|
| GDS v6 | `315c2ebceb2bc4cf258fa63be2279843805db3010637d0c273aea9db12813e37` | 540 × 380 µm; DRC=0; LVS único |
| LEF v6 | `39f09e853f89e7693523588c5c2d28fb217c8c9710fd18cd09b2bd813be0d5c7` | Interface física da mesma geometria |
| PEX v6 | `a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f` | 1.785 MOS, 16.442 resistores, 12.612 capacitores; vinculado ao GDS |
| Binding de replay | `3b6f7205476b79d02754ba081a7d2eb2ef9d372670daf26067d3d0cb5745e76d` | Usado no fechamento técnico P4 |

O contorno GDS da baseline é 205.200 µm². O handoff mede a matriz de 32 bitcells em aproximadamente 138 × 56 µm, ou 7.728 µm² de envelope geométrico, antes de contabilizar periferia, roteamento, alimentação e folgas. Nenhuma candidata compactada ou medição de redução antes/depois foi encontrada. A especificação ainda não fixa meta numérica de redução nem prioridade entre área, desempenho, potência e robustez.

## Gates para concluir P6/D1

1. Registrar a decisão de escopo e o aceite da arquitetura física v6 como baseline 4×8.
2. Escolher e registrar a arquitetura de decoder/periferia para 8 e 32 linhas; a célula atual é um decoder 2→4.
3. Implementar cada dimensão como variante independente, preservando a v6 e os seletores das Fases 1/2.
4. Gerar views coerentes de netlist, GDS, LEF e Liberty de interface; executar DRC, LVS e PEX identificados por hash para cada dimensão.
5. Validar funcionalidade, ownership e controles por corner na PEX própria de cada macro.
6. Executar a caracterização elétrica aplicável por dimensão, inclusive a exigência de SNM/pós-layout definida para o escopo aprovado. Não reutilizar valores medidos na 4×8 como resultado de 8×8/32×8.
7. Se houver otimização de área, mantê-la em variante separada: iniciar por reposicionamento de periféricos, medir contorno/área, acesso a pinos e nets críticas, e repetir DRC/LVS/PEX e gates elétricos afetados. Sem meta aprovada, publicar apenas o delta medido, sem declarar que atingiu uma meta de produto.

## Próxima tarefa técnica

O primeiro caminho é desenvolver e validar um decoder maior, pois o inventário não contém fonte física 3→8/5→32. Antes de expandir o layout, comparar uma arquitetura de pré-decodificação com a duplicação em estágios do decoder 2→4, incluindo fanout, carga, dispositivos, pinos e requisitos de clock/fase. A alternativa escolhida precisa de uma prova isolada de função/DRC/LVS/PEX antes da integração na matriz.

## Limites deste checkpoint

- P6/D1 não está concluído.
- A qualificação elétrica global continua `NOT_CHARACTERIZED`; `signoff_achieved=false`.
- P5 4×8 permanece parcial/provisório; P6/D1 não substitui esse gate.
- Este registro não representa aceite da equipe nem alteração formal do requisito.
- Nenhum arquivo congelado da v6 ou das Fases 1/2 foi alterado.
