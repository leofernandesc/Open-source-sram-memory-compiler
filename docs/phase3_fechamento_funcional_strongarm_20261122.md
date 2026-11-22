# Fase 3 · Fechamento funcional pós-layout com três StrongARM

**INCONCLUSIVE** · Macro 4×8 experimental, bits 3, 6 e 7 StrongARM.

## A. Identidade física

ECO físico v6, 540 × 380 µm, 1.785 MOS. O GDS reimportado tem DRC zero e LVS com correspondência única. A visão DC do PEX também teve correspondência única. Os 16 pinos do binding foram conferidos, e o PEX distribuído e o binding são os mesmos em todos os corners e fixtures da campanha. Os recibos físicos vieram do checkpoint anterior.

| Artefato | SHA-256 |
|---|---|
| [GDS](../build/phase3/strongarm_triple_20261122/physical/macro_v6/sram_4x8.gds) | `315c2ebceb2bc4cf258fa63be2279843805db3010637d0c273aea9db12813e37` |
| [LEF](../build/phase3/strongarm_triple_20261122/physical/macro_v6/sram_4x8.lef) | `39f09e853f89e7693523588c5c2d28fb217c8c9710fd18cd09b2bd813be0d5c7` |
| [PEX](../build/phase3/strongarm_triple_20261122/physical/pex_verified/extracted_rc.spice) | `a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f` |

[Cadeia de identidade](../build/phase3/strongarm_functional_closure_20261122/identity.json) · [Critérios congelados](../build/phase3/strongarm_functional_closure_20261122/CRITERIOS.md)

## B. Validação C250

SKY130A, 1,8 V, 27 °C, Gear/KLU, passo máximo de 25 ps. A C250 escreve nas quatro linhas, lê três delas e observa os pares das quatro linhas após escrita. A cobertura de leitura das quatro linhas pertence à regressão de 18 ciclos. A inspeção de correntes de barramento na C250 testa oposição nas escritas e abertura do host na leitura normal.

| Corner | Escritas | Leituras | Retenção | D/Q | DATA c14–c17 | Veredito |
|---|---|---|---|---|---|---|
| [TT](../build/phase3/strongarm_functional_closure_20261122/c250/TT/qualification.json) | 6/6 | 4/4 | 48/48 pares escritos | 4 leituras com D/Q correto e estável | `AA` · `0F` · `F0` · `F0` | PASS |
| [SS](../build/phase3/strongarm_functional_closure_20261122/c250/SS/qualification.json) | 6/6 | 4/4 | 48/48 pares escritos | 4 leituras com D/Q correto e estável | `AA` · `0F` · `F0` · `F0` | PASS |
| [FF arquivado e reanalisado](../build/phase3/strongarm_functional_closure_20261122/c250/FF/qualification.json) | 6/6 | 4/4 | 48/48 pares escritos | 4 leituras com D/Q correto e estável | `AA` · `0F` · `F0` · `F0` | PASS |

## C. Regressão integrada

Fixture histórica de 18 ciclos e 370 ns, 10 fF por DATA, período 20 ns, slew 50 ps e guarda de 1,5 ns. O observador revisado de SS avalia condução, liberação e transferência de propriedade. As classificações do observador anterior e da janela de ±100 ps ficam registradas separadamente.

| Corner | Leituras | Escritas/readback | Propriedade do barramento | Veredito |
|---|---|---|---|---|
| TT | — | — | — | NOT_RUN |
| SS | — | — | — | NOT_RUN |
| FF | — | — | — | NOT_RUN |

## D. Análise elétrica

| C250 | Menor margem conjunta regeneração/D | Pico do tail | Tail/reset na subida | Tail/pré-carga na queda |
|---|---:|---:|---:|---:|
| TT | 4,609 ns | 109,0–119,9 µA | 186–234 ps | 0–0 ps |
| SS | 1,827 ns | 70,4–82,5 µA | 109–186 ps | 0–0 ps |
| FF | 6,116 ns | 148,8–158,7 µA | 453–468 ps | 0–0 ps |

| Configuração | Margem mínima SA/SAB dos senses nativos | Tap 80→tronco em c15 |
|---|---:|---:|
| C250 TT | 5,218 ns | 541,3 ps |
| C250 SS | 2,892 ns | 797,0 ps |
| C250 FF | 6,511 ns | 408,9 ps |

[Medições por bit](../build/phase3/strongarm_functional_closure_20261122/electrical_by_lane.csv)

Na última leitura, os três StrongARM recuperaram BL/BLB, SA/SAB e os nós intermediários até 244,786 ns em TT, 247,137 ns em SS e 243,482 ns em FF. Não foi observada oposição sustentada nas janelas C250 de escrita, e o host permaneceu aberto nas leituras normais. Liberação em cada handoff, alta impedância e recuperação de propriedade no protocolo completo dependem da fixture integrada.

As janelas de corrente usam o marcador diagnóstico de 1 µA e a resolução do waveform. A simultaneidade durante a subida é um indicador elétrico a caracterizar. A análise mantém a decisão e recuperação dos cinco senses nativos e dos três StrongARM por lane.

## E. Veredito final

O fechamento funcional ainda depende dos corners ou verificações em aberto da tabela. Os PASS observados têm validade no escopo de cada execução.

O gate C250 passou nos três corners. A regressão integrada em TT foi adiada por orçamento. A previsão foi de 101,8 min com 87,1 min ativos disponíveis, extrapolando o maior tempo C250 observado nesta rodada e tratando a partida separadamente. O próximo passo é retomar nessa regressão com o mesmo PEX e a mesma guarda, sob uma nova janela de execução.

A qualificação elétrica continua `NOT_CHARACTERIZED`. Permanecem pendentes setup/hold, acesso e desabilitação, potência estática, potência dinâmica e energia, tabelas por slew/carga, homologação SNM Monte Carlo e geração e validação da Liberty. As 200 amostras Hold e 206 Read e os checkpoints anteriores foram preservados. As configurações adicionais da especificação seguem pendentes.

A primeira tentativa TT foi interrompida pelo desligamento do host em 67,1 ns, sem exportar waveform. O mesmo contêiner EDA voltou pelo launcher `sram-eda`, que restaurou o arquivo da montagem de Xauthority. As duas tentativas de TT usam deck e binding com bytes idênticos. O intervalo até a retomada foi excluído do relógio ativo da campanha. O manifesto inicial integrado TT herdava o rótulo SS apenas nos metadados de condições. Esse rótulo foi corrigido antes de qualquer transiente integrado.

[Registro de progressão](../build/phase3/strongarm_functional_closure_20261122/campaign.jsonl) · [Procedimento de reprodução](../build/phase3/strongarm_functional_closure_20261122/REPRODUCAO.md)
