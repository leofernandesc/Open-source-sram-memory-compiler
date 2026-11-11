# Open-Source SRAM Memory Compiler — Relatório de fechamento técnico da Fase 2

**Tecnologia:** SKY130 · **Protótipo selecionado:** SRAM síncrona 4 × 8, single-port, bitcell 6T  
**Data do registro:** 11 de novembro de 2026 · **Marco:** 2 — Gerador e primeiro array físico  
**Situação:** execução técnica encerrada, aceite pelo responsável com ressalvas; ratificação dos demais integrantes/orientador não registrada.

## 1. Decisão executiva

O protótipo 4 × 8 com **abutment direto das bitcells** foi aprovado pelo responsável pelo projeto como **baseline técnica da Fase 2**. O novo registro de seleção é `release/phase2_current.json`, na branch `release/phase2-acceptance-20261111`. A implementação espaçada anterior permanece como referência histórica e não foi apagada. A biblioteca de seis folhas da Fase 1 permanece congelada; a versão com abutment utiliza a variante física de bitcell explicitamente declarada em `physical/phase2_direct_abutment/bitcell_6t_abut.mag`, sem alterar sua topologia 6T ou seu sizing.

A F1-04 recebe **aceite com ressalva operacional** quanto ao sense amplifier PEX em pequenos diferenciais. A cadeia de identidade e as simulações isoladas da variante final foram obtidas; os quatro FAIL a 5 mV permanecem integralmente válidos. O WL driver foi aprovado nos ensaios isolados nominais. A aceitação não equivale à comprovação de que todos os testes do sense passaram, nem a uma validação PVT ou de fabricação.

## 2. Escopo original e marcos

De acordo com a proposta adaptada de 09/09/2026, a Fase 2 compreende: (i) algoritmo de tiling por abutment; (ii) implementação Python da lógica de posicionamento; (iii) geração do netlist estrutural; (iv) integração com células reais e produção de um primeiro array pequeno em GDSII, com DRC/LVS completo. O Marco 2 estava programado para **02/11/2026**; esta formalização ocorre em 11/11/2026, sem declarar retroativamente o cumprimento do prazo original.

A Fase 3 está prevista para **03–23/11/2026** e o Marco 3 vence em **23/11/2026** (relatório de caracterização e `.lib` gerada automaticamente). As Fases 4 e 5 seguem até **19/12/2026**.

## 3. Baseline física escolhida

- **Célula 6T revisada:** 17,25 × 14 µm, orientação R0, mesma topologia e larguras de transistores da variante congelada.
- **Matriz 4 × 8:** 32 bitcells, envelope de **138 × 56 µm = 7.728 µm²**, com contato de fronteira real entre linhas/colunas.
- **Matriz anterior:** envelope de **227,25 × 87,92 µm = 19.979,82 µm²**. **Redução de 61,3% no envelope da matriz**, não na área da macro completa.
- **Macro completa:** 540 × 380 µm = 205.200 µm²; dimensão do floorplan ainda não otimizada.
- **Composição:** oito pares BL/BLB, quatro WL, decoder dinâmico 2→4 de 33 MOS, quatro WL drivers, oito precharge, oito write drivers, oito sense amplifiers e interfaces/controle HD.
- **Rede temporal:** uma entrada externa `CLK`; 80 inversores SKY130 HD para fases internas, taps 24/40/60/80 preservados. Frequência de 50 MHz usada apenas na campanha nominal (20 ns por ciclo), não Fmax.

**Identificador de GDSII selecionado:** `reports/phase2/direct_abutment_20261111/gds_v1/sram_4x8.gds`  
**SHA-256:** `83e72aee8d45a9826751cdefd46dd062acc2a17ec0acfd33c07f218d20d8e64e`.

## 4. Resultados físicos e elétricos

| Frente | Evidência publicada | Resultado observado |
|---|---|---|
| Bitcell revisada e matriz-piloto 2 × 2 | `reports/direct_abutment/20261111/` | DRC = 0; LVS aprovado; escrita/leitura elétrica piloto aprovadas (104 checks) |
| Fabric 4 × 8 | `reports/phase2/direct_abutment_20261111/fabric_v3/` | DRC = 0; LVS dos 401 MOS custom aprovado |
| Macro roteada e GDS reimportado | `.../layout_v1/`, `.../gds_v1/` | DRC = 0; LVS transistor a transistor aprovado, 1.493 MOS no top |
| Qualificação elétrica integrada | `.../qualification_v1/results.json` | 1.740 verificações; zero falhas; 72 bits lidos; 18 ciclos em 370 ns |
| GLS da netlist roteada | `.../gls_v1/results.json` | 15.619 verificações funcionais aprovadas; fabric representado por modelo de verificação |
| Auditoria do novo candidato | `.../audit_v1/results.json` | PASS_NEW_CANDIDATE_AUDIT |
| Integridade do modelo | `physical/phase2_direct_abutment/candidate.json` | Identidades e hashes do candidato preservados |

A campanha integrada inclui escritas, reescritas, leituras das quatro linhas, leitura consecutiva, pré-carga, recuperação, mascaramento do barramento e trocas de direção. Os resultados refletem **TT, 1,8 V e 27 °C**, com extração dos dispositivos e junções, **sem RC distribuído completo das folhas/interconexões**.

### 4.1 Temporalidade nominal observada

- PRECH liberado até habilitação de WE: ~211–212 ps.
- WL a 80% até SCLK a 20%: **238,5–244,5 ps**.
- DOUT_RAW válido antes da captura local: janela mínima observada **7,4368 ns**.
- Novos dados em `DATA` após descida pública: **0,4888–0,5509 ns** nos bits que comutaram.
- Na reanálise do raw completo, o diferencial assinado de **200 mV** surgiu em **40,1–45,9 ps após a WL cruzar 20%**, nos 72 pares leitura/bit analisados. Parte do diferencial 5–20 mV já estava presente antes da ativação da WL.

Esses resultados **não** definem setup/hold públicos, Fmax, atraso garantido nem margem de todo corner. O possível adiantamento de SCLK fica para a Fase 3.

## 5. F1-04 — decisão com ressalva

Na campanha isolada final (TT, 1,8 V, 27 °C): o WL driver passou em **6/6** casos; o sense esquemático em **12/12**; e o sense PEX em **8/12**. Os quatro casos completos de sense PEX em 5 mV falharam porque uma avaliação de cada caso decidiu pela polaridade incorreta. Repetições com passo de 1 ps não eliminaram a falha.

O diagnóstico causal mostrou que a assimetria capacitiva do PEX favorece uma polaridade; retirar capacitores eliminou a falha e espelhá-los inverteu a preferência. Na varredura nominal da PEX completa, **20, 30 e 50 mV** passaram em ambas as polaridades e cargas testadas; isso não é sensibilidade garantida. O 4×8 apresentou mínimo nominal de **1,571 V** de diferencial 50 ps antes de SCLK20, em uma campanha sem RC distribuído completo.

**Deliberação registrada:** manter a célula atual e aceitar a comprovação da F1-04 com ressalva explícita para o regime de pequenos diferenciais. Os FAIL permanecem como evidência. Reabrir o projeto físico do sense apenas se a caracterização integrada da Fase 3 demonstrar comprometimento do domínio de operação necessário. Aprovação colegiada/orientador permanece pendente de registro, sem falsificar aceite histórico.

## 6. Exclusões: o que não foi declarado concluído

A Fase 2 não estabelece extração RC detalhada completa do bloco com abutment, corners TT/SS/FF qualificados, Monte Carlo SNM e yield, potência, Fmax, setup/hold de interface nem arquivo Liberty caracterizado. Tampouco demonstra os arrays físicos 8 × 8 e 32 × 8 — escalabilidade e views de quatro configurações integram a Fase 4 da proposta. Estas não são falhas implícitas do Marco 2, mas atividades seguintes.

## 7. Registro de seleção e integridade

Aprovada a versão com abutment como baseline técnica do Marco 2 em **11/11/2026**, com documentação sob branch dedicada, sem merge nas branches principais. O arquivo `release/phase2_current.json` aponta o candidato e o GDS selecionados; `docs/phase2_f1_04_acceptance_20261111.md` registra a exceção. Não foram alterados arquivos congelados, o histórico das tentativas reprovadas ou o manifesto F1. A passagem para uma branch de integração/principal exige atualização controlada de referências e verificação de conflitos antes do merge.

## 8. Parecer de encerramento e passagem à Fase 3

**Parecer:** a execução técnica da Fase 2 do protótipo 4 × 8 está **apta ao encerramento com ressalvas**, com abutment direto, GDSII válido, DRC/LVS e verificação funcional nominal documentados. A decisão de referência foi registrada pelo responsável; a ratificação coletiva/institucional não está documentada.

**Handoff para 23/11:** base 4 × 8 selecionada; definir extração RC, automatizar ensaios de timing/potência TT/SS/FF, medir SNM com Monte Carlo (N≥200 quando aplicável), gerar `.lib` simplificada a partir de métricas rastreáveis e produzir relatório consolidado. A disponibilidade de 8 × 8 e 32 × 8, exigida pela caracterização final da proposta mas agendada para a Fase 4, é uma dependência a ser tratada explicitamente no Marco 3.

## 9. Referências e rastreabilidade

1. Proposta adaptada *Open-Source SRAM Memory Compiler*, 09/09/2026, seções 4–7.
2. [`docs/phase2_direct_abutment_20261111.md`](https://github.com/leofernandesc/Open-source-sram-memory-compiler/blob/feature/phase2-direct-abutment/docs/phase2_direct_abutment_20261111.md).
3. [`physical/phase2_direct_abutment/candidate.json`](https://github.com/leofernandesc/Open-source-sram-memory-compiler/blob/feature/phase2-direct-abutment/physical/phase2_direct_abutment/candidate.json).
4. [`docs/phase1_final_isolated_20261111.md`](https://github.com/leofernandesc/Open-source-sram-memory-compiler/blob/verification/phase1-final-isolated/docs/phase1_final_isolated_20261111.md).
5. [`docs/sense_pex_small_signal_investigation.md`](https://github.com/leofernandesc/Open-source-sram-memory-compiler/blob/investigation/sense-pex-small-signal/docs/sense_pex_small_signal_investigation.md).
6. Registro de aceite: `release/phase2_current.json` e `docs/phase2_f1_04_acceptance_20261111.md`, branch `release/phase2-acceptance-20261111`.
7. Transiente completo da campanha 4×8: SHA-256 `f5c19a6db9293edd792d73c4fe306c7782f9ad718fd66dfd0fa56872b75feb95`.