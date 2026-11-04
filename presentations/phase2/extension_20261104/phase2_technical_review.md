# Apresentação técnica da Fase 2 — rodada complementar

## Slide 1 — Open-Source SRAM Memory Compiler

- Digital Control, Physical Integration and Experimental Validation of a 4×8 SRAM in SKY130
- Equipe: Danilo · André · Leonardo

Fontes: [README.md](../../../README.md); [GITFLOW.md](../../../GITFLOW.md).

## Slide 2 — Contexto e escopo do projeto

- SRAM customizada: armazenamento e periféricos projetados no nível de transistor.
- Compilador: composição repetível das células e geração de vistas físicas.
- 4×8: primeiro alvo físico; RTL já exercita 4, 8, 16 e 32 palavras.

Fontes: [technical_specification.md](../../../specs/technical_specification.md); [phase2_execution.md](../../../docs/phase2_execution.md).

## Slide 3 — Critérios de entrega da Fase 2

- F2-DIG: mapear controle e registradores em SKY130HD e verificar a netlist por GLS.
- F2-FIS: conectar células reais, gerar o GDS e demonstrar acesso elétrico com DRC/LVS.

Fontes: [phase2_review_20261104_acceptance.md](../../../docs/phase2_review_20261104_acceptance.md).

## Slide 4 — Células selecionadas na Fase 1

- 32 bitcells 6T · 1 decoder dinâmico de 33 MOS · 4 WL drivers
- 8 precharge · 8 write drivers · 8 sense amplifiers
- Seleção congelada: release/phase1_current.json

Fontes: [phase1_current.json](../../../release/phase1_current.json); [manifest.json](../../../release/phase1_keeper/manifest.json); [phase2_review_20261104.md](../../../docs/phase2_review_20261104.md).

## Slide 5 — Arquitetura da SRAM 4×8

- Azul: células padrão SKY130HD
- Verde: seis famílias customizadas
- 12 FF de requisição + 8 FF de leitura; DATA bidirecional.

Fontes: [sram_4x8_wrapper.v](../../../rtl/sram_4x8_wrapper.v); [macro_binding.v](../../../physical/phase2/macro_binding.v).

## Slide 6 — Protocolo de leitura e escrita

- 001 → leitura · 010 → escrita · demais combinações → nenhum novo acesso.
- Subida: captura de ADDR, operação e DATA de escrita.
- Descida: captura de leitura; o registro retém o último resultado.
- DATA habilitado somente com READ_Q e controles vivos de leitura.

Fontes: [sram_4x8_digital.md](../../../specs/sram_4x8_digital.md); [sram_controller.v](../../../rtl/sram_controller.v); [sram_4x8_wrapper.v](../../../rtl/sram_4x8_wrapper.v).

## Slide 7 — Hierarquia RTL

- sram_model: referência pública parametrizada.
- sram_controller + wrapper: captura e interface 4×8.
- macro_model: substituto funcional para simulação.
- macro_bb: núcleo preservado como black box na síntese.

Fontes: [model.f](../../../rtl/model.f); [wrapper_sim.f](../../../rtl/wrapper_sim.f); [wrapper_synth.f](../../../rtl/wrapper_synth.f).

## Slide 8 — Cobertura da verificação digital

- Scoreboard independente; sem reutilizar helpers do DUT.
- Todos os endereços, 8 controles, 64 transições e padrões dirigidos.
- 2.048 operações pseudoaleatórias por regressão de memória.
- 154.303 checks RTL na campanha completa.

Fontes: [sram_ref_model.sv](../../../tb/sram_ref_model.sv); [results.json](../../../reports/digital/phase2_review_20261104/results.json).

## Slide 9 — Síntese e GLS em SKY130HD

- 20 flip-flops · 8 ebufn físicos · 1 macro customizada.
- Sem latches inesperados ou armazenamento convertido em FF.
- Piloto tri-state validou 0, 1 e Z.
- 15.619 checks GLS aprovados.

Fontes: [results.json](../../../reports/phase2/review_20261104/digital/results.json); [results.json](../../../reports/phase2/routed_gls/results.json).

## Slide 10 — Interface entre controle e núcleo

- ADDR_Q e DIN_Q estabilizam endereço e escrita.
- READ_Q / WRITE_Q são pedidos, não pulsos diretos.
- PCLK, PRECH, WE e SCLK coordenam acesso e recuperação.
- DOUT_RAW alimenta o mux e o FF de saída.

Fontes: [phase2_physical_interface.md](../../../specs/phase2_physical_interface.md); [macro_binding.v](../../../physical/phase2/macro_binding.v).

## Slide 11 — Decoder dinâmico e seleção de linha

- PCLK baixo: PMOS carregam os quatro nós internos.
- PCLK alto: o endereço capturado descarrega apenas o caminho selecionado.
- Quatro keepers restauram os nós não selecionados.
- DEC qualificado → WL driver → linha física.

Fontes: [technical_specification.md](../../../specs/technical_specification.md); [manifest.json](../../../release/phase1_keeper/manifest.json); [phase2_review_20261104.md](../../../docs/phase2_review_20261104.md).

## Slide 12 — Geração da matriz e integração física

- 4 linhas × 8 colunas; 32 bitcells e 8 pares BL/BLB.
- Instâncias periféricas e pinos lidos dos artefatos congelados.
- Magic: custom fabric; OpenROAD: integração com SKY130HD.
- Auditor separado confere terminais, coordenadas e ordem dos bits.

Fontes: [phase2_core.py](../../../tools/phase2_core.py); [run_phase2_fabric.py](../../../tools/run_phase2_fabric.py); [review_phase2_structure.py](../../../tools/review_phase2_structure.py); [results.json](../../../reports/phase2/review_20261104/reproduction/results.json).

## Slide 13 — Layout integrado da SRAM 4×8

- 1.493 MOS: 401 customizados + 1.092 SKY130HD.
- 20 FF e lógica de fases, captura, interface e CTS.
- Floorplan experimental: 540 × 380 µm.

Fontes: [results.json](../../../reports/phase2/layout_overview/results.json); [delivery.json](../../../physical/phase2/delivery.json); [results.json](../../../reports/phase2/review_20261104/structure/results.json).

## Slide 14 — Sequenciamento elétrico de acesso

- PRECH libera antes de WE/WL.
- WL seleciona a linha; BL/BLB desenvolvem diferencial.
- SCLK regenera e o FF captura após a descida pública.

Fontes: [phase2_timing_extension.md](../../../docs/phase2_timing_extension.md); [results.json](../../../reports/phase2/extension_20261104/c2_bus/results.json).

## Slide 15 — Problemas encontrados e correções

- WE antecipado: guarda −232,897 ps → tap 40 → +167,388 ps no piloto.
- Roteamento: anel de obstrução de 5 nm isolava acessos M4.
- Importação: vias tecnológicas e vistas físicas reais precisaram ser preservadas.

Fontes: [phase2_execution.md](../../../docs/phase2_execution.md); [results.json](../../../reports/phase2/phase_guard_review/results.json); [phase2_timing_extension.md](../../../docs/phase2_timing_extension.md).

## Slide 16 — Verificação física: DRC e LVS

- Magic: zero violações no GDS reimportado.
- Netgen: correspondência expandida de modelos, terminais e dimensões.
- Gate, bulk, W e L adulterados foram rejeitados.
- 1.493 MOS brutos → 1.459 equivalentes após redução legal de paralelos.

Fontes: [magic.txt](../../../reports/phase2/final_gds/magic.txt); [lvs.txt](../../../reports/phase2/final_gds/lvs.txt); [results.json](../../../reports/phase2/review_20261104/lvs_negative/results.json).

## Slide 17 — Simulação elétrica de leitura e escrita

- Dirigida anterior: 1.332 checks, incluindo 160 bits lidos.
- C1: 1.150 checks; leituras e reescritas adjacentes na mesma linha.
- C2: 1.281 checks; máscara viva e corrente do barramento.

Fontes: [phase2_coverage_extension.md](../../../docs/phase2_coverage_extension.md); [results.json](../../../reports/phase2/extension_20261104/c1_sequences/results.json).

## Slide 18 — Contrato temporal e barramento

- FF_Q preservado durante a máscara viva.
- Liberação: corrente e tensão verificadas juntas.
- Sob probe de 1 kΩ: tDIS ≈0,13–0,18 ns; tEN ≈0,63 ns.
- Medidas nominais; turnaround garantido pendente.

Fontes: [phase2_timing_extension.md](../../../docs/phase2_timing_extension.md); [sram_4x8_timing_contract.md](../../../specs/sram_4x8_timing_contract.md).

## Slide 19 — Ensaios de partida sem reset

- Rampas 1 / 5 / 10 ns; condicionamento de 0 / 2 / 3 ciclos nas combinações ensaiadas.
- 5 cenários PASS · 3.383 checks totais, incluindo 240 bits lidos.
- Sem IC, nodeset ou conteúdo artificialmente imposto.

Fontes: [results.json](../../../reports/phase2/final_polish_20261104/startup_verification/results.json); [phase2_final_polish.md](../../../docs/phase2_final_polish.md).

## Slide 20 — Quadro de resultados

- F2-DIG: síntese/GLS funcional aprovada.
- F2-FIS: SRAM 4×8 integrada e aprovada no experimento nominal.
- DRC/LVS e acessos reais, com artefatos e hashes rastreáveis.
- Sequências críticas, máscara viva e partida nominal verificadas.

Fontes: [phase2_review_20261104_acceptance.md](../../../docs/phase2_review_20261104_acceptance.md); [phase2_final_polish.md](../../../docs/phase2_final_polish.md); [delivery.json](../../../physical/phase2/delivery.json); [phase2_extension_state_20261104.md](../../../docs/phase2_extension_state_20261104.md).

## Slide 21 — Limitações da validação

- Fmax e temporização externa completa ainda não caracterizados.
- Sem RC detalhado, robustez PVT ou partida estatística.
- Sem potência/yield caracterizados ou qualificação de fabricação.
- Geração física 8×8 / 16×8 / 32×8 continua fora desta entrega.

Fontes: [sram_4x8_timing_contract.md](../../../specs/sram_4x8_timing_contract.md); [phase2_review_20261104_acceptance.md](../../../docs/phase2_review_20261104_acceptance.md).

## Slide 22 — Conclusão da Fase 2

- Controle digital sintetizado e células customizadas integrados.
- SRAM 4×8 física com leitura, escrita e captura demonstradas.
- Entregáveis: RTL, gerador Python, GDS/LEF/DEF/MAG/SPICE, relatórios e scripts.

Fontes: [phase2_reproduction_guide.md](../../../docs/phase2_reproduction_guide.md); [phase2_final_polish.md](../../../docs/phase2_final_polish.md).
