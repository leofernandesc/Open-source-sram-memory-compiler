# Open-Source SRAM Memory Compiler — Phase 2

Fonte editável: `slides.json`; diagramas nativos no PPTX.


---

## 01 — Open-Source SRAM Memory Compiler

PHASE 2 · TECHNICAL REVIEW


- Digital Control, Physical Integration and Experimental Validation of a 4×8 SRAM in SKY130
- Equipe: Danilo · André · Leonardo


**Mensagem:** Implementação e auditoria concluídas no escopo experimental; revisão formal pendente.


**Fontes:** [README.md](../../README.md), [GITFLOW.md](../../GITFLOW.md)


---

## 02 — Uma ponte entre lógica e silício

CONTEXTO


- SRAM customizada: armazenamento e periféricos projetados no nível de transistor.
- Compilador: composição repetível das células e geração de vistas físicas.
- 4×8: primeiro alvo físico; RTL já exercita 4, 8, 16 e 32 palavras.


**Mensagem:** O protótipo pequeno permite inspecionar a integração completa.


**Fontes:** [specs/technical_specification.md](../../specs/technical_specification.md), [docs/phase2_execution.md](../../docs/phase2_execution.md)


---

## 03 — Dois marcos, duas evidências

OBJETIVO DA FASE 2


- F2-DIG: mapear controle e registradores em SKY130HD e verificar a netlist por GLS.
- F2-FIS: conectar células reais, gerar o GDS e demonstrar acesso elétrico com DRC/LVS.


**Mensagem:** Uma SRAM funcional em Verilog não comprova uma SRAM física.


**Fontes:** [docs/phase2_review_20261104_acceptance.md](../../docs/phase2_review_20261104_acceptance.md)


---

## 04 — Seis famílias, 401 MOS customizados

HERANÇA DA FASE 1


- 32 bitcells 6T · 1 decoder dinâmico de 33 MOS · 4 WL drivers
- 8 precharge · 8 write drivers · 8 sense amplifiers
- Seleção congelada: release/phase1_current.json


**Mensagem:** As folhas foram preservadas; adaptações de integração ficam fora delas.


**Fontes:** [release/phase1_current.json](../../release/phase1_current.json), [release/phase1_keeper/manifest.json](../../release/phase1_keeper/manifest.json), [docs/phase2_review_20261104.md](../../docs/phase2_review_20261104.md)


---

## 05 — Arquitetura integrada

SRAM SÍNCRONA 1RW


- Azul: células padrão SKY130HD
- Verde: seis famílias customizadas
- 12 FF de requisição + 8 FF de leitura; DATA bidirecional.


**Mensagem:** Uma palavra de oito bits por linha física, sem column mux.


**Fontes:** [rtl/sram_4x8_wrapper.v](../../rtl/sram_4x8_wrapper.v), [physical/phase2/macro_binding.v](../../physical/phase2/macro_binding.v)


---

## 06 — O pedido é capturado; a saída é mascarada

PROTOCOLO


- 001 → leitura · 010 → escrita · demais combinações → nenhum novo acesso.
- Subida: captura de ADDR, operação e DATA de escrita.
- Descida: captura de leitura; o registro retém o último resultado.
- DATA habilitado somente com READ_Q e controles vivos de leitura.


**Mensagem:** Mudar controles vivos pode liberar DATA sem cancelar o acesso capturado.


**Fontes:** [specs/sram_4x8_digital.md](../../specs/sram_4x8_digital.md), [rtl/sram_controller.v](../../rtl/sram_controller.v), [rtl/sram_4x8_wrapper.v](../../rtl/sram_4x8_wrapper.v)


---

## 07 — RTL e fronteira da macro

IMPLEMENTAÇÃO DIGITAL


- sram_model: referência pública parametrizada.
- sram_controller + wrapper: captura e interface 4×8.
- macro_model: substituto funcional para simulação.
- macro_bb: núcleo preservado como black box na síntese.


**Mensagem:** A definição comportamental de armazenamento não entra na fabricação.


**Fontes:** [rtl/model.f](../../rtl/model.f), [rtl/wrapper_sim.f](../../rtl/wrapper_sim.f), [rtl/wrapper_synth.f](../../rtl/wrapper_synth.f)


---

## 08 — Verificação orientada ao protocolo

DESIGN VERIFICATION


- Scoreboard independente; sem reutilizar helpers do DUT.
- Todos os endereços, 8 controles, 64 transições e padrões dirigidos.
- 2.048 operações pseudoaleatórias por regressão de memória.
- 154.303 checks RTL na campanha completa.


**Mensagem:** Conteúdo não escrito é desconhecido; mutantes verificam os observadores.


**Fontes:** [tb/sram_ref_model.sv](../../tb/sram_ref_model.sv), [reports/digital/phase2_review_20261104/results.json](../../reports/digital/phase2_review_20261104/results.json)


---

## 09 — Mapeamento real em SKY130HD

SÍNTESE E GLS


- 20 flip-flops · 8 ebufn físicos · 1 macro customizada.
- Sem latches inesperados ou armazenamento convertido em FF.
- Piloto tri-state validou 0, 1 e Z.
- 15.619 checks GLS aprovados.


**Mensagem:** GLS sem atraso confirma comportamento, não fechamento de timing.


**Fontes:** [reports/phase2/review_20261104/digital/results.json](../../reports/phase2/review_20261104/digital/results.json), [reports/phase2/routed_gls/results.json](../../reports/phase2/routed_gls/results.json)


---

## 10 — Pedidos digitais, fases elétricas

INTERFACE DIGITAL–FÍSICA


- ADDR_Q e DIN_Q estabilizam endereço e escrita.
- READ_Q / WRITE_Q são pedidos, não pulsos diretos.
- PCLK, PRECH, WE e SCLK coordenam acesso e recuperação.
- DOUT_RAW alimenta o mux e o FF de saída.


**Mensagem:** Taps 24 / 40 / 60 / 80 são posições em uma cadeia de inversores.


**Fontes:** [specs/phase2_physical_interface.md](../../specs/phase2_physical_interface.md), [physical/phase2/macro_binding.v](../../physical/phase2/macro_binding.v)


---

## 11 — Pré-carga, avaliação e retenção

DECODER DINÂMICO


- PCLK baixo: PMOS carregam os quatro nós internos.
- PCLK alto: o endereço capturado descarrega apenas o caminho selecionado.
- Quatro keepers restauram os nós não selecionados.
- DEC qualificado → WL driver → linha física.


**Mensagem:** 33 MOS oficiais; o decoder RTL permanece somente referência funcional.


**Fontes:** [specs/technical_specification.md](../../specs/technical_specification.md), [release/phase1_keeper/manifest.json](../../release/phase1_keeper/manifest.json), [docs/phase2_review_20261104.md](../../docs/phase2_review_20261104.md)


---

## 12 — Composição e verificação independente

GERADOR PYTHON


- 4 linhas × 8 colunas; 32 bitcells e 8 pares BL/BLB.
- Instâncias periféricas e pinos lidos dos artefatos congelados.
- Magic: custom fabric; OpenROAD: integração com SKY130HD.
- Auditor separado confere terminais, coordenadas e ordem dos bits.


**Mensagem:** A mesma configuração reproduziu GDS e SPICE equivalentes.


**Fontes:** [tools/phase2_core.py](../../tools/phase2_core.py), [tools/run_phase2_fabric.py](../../tools/run_phase2_fabric.py), [tools/review_phase2_structure.py](../../tools/review_phase2_structure.py), [reports/phase2/review_20261104/reproduction/results.json](../../reports/phase2/review_20261104/reproduction/results.json)


---

## 13 — O top-level físico entregue

LAYOUT INTEGRADO


- 1.493 MOS: 401 customizados + 1.092 SKY130HD.
- 20 FF e lógica de fases, captura, interface e CTS.
- Floorplan experimental: 540 × 380 µm.


**Mensagem:** Imagem do GDS real: M4/M5 e footprints das células padrão.


**Fontes:** [reports/phase2/layout_overview/results.json](../../reports/phase2/layout_overview/results.json), [physical/phase2/delivery.json](../../physical/phase2/delivery.json), [reports/phase2/review_20261104/structure/results.json](../../reports/phase2/review_20261104/structure/results.json)


---

## 14 — Da pré-carga à captura

FORMAS DE ONDA REAIS


- PRECH libera antes de WE/WL.
- WL seleciona a linha; BL/BLB desenvolvem diferencial.
- SCLK regenera e o FF captura após a descida pública.


**Mensagem:** TT · 1,8 V · 27 °C · conectividade e junções extraídas, sem wire RC.


**Fontes:** [reports/phase2/final_polish_20261104/startup_extended/r1_idle2/results.json](../../reports/phase2/final_polish_20261104/startup_extended/r1_idle2/results.json), [reports/phase2/final_polish_20261104/events/results.json](../../reports/phase2/final_polish_20261104/events/results.json)


---

## 15 — Problemas reais, correções rastreáveis

ENGENHARIA


- WE antecipado: guarda −232,897 ps → tap 40 → +167,388 ps no piloto.
- Roteamento: anel de obstrução de 5 nm isolava acessos M4.
- Importação: vias tecnológicas e vistas físicas reais precisaram ser preservadas.


**Mensagem:** Readback correto, sozinho, não revelava todos os problemas.


**Fontes:** [docs/phase2_execution.md](../../docs/phase2_execution.md), [reports/phase2/phase_guard_review/results.json](../../reports/phase2/phase_guard_review/results.json)


---

## 16 — Geometria e conectividade verificadas

DRC · LVS · GDSII


- Magic: zero violações no GDS reimportado.
- Netgen: correspondência expandida de modelos, terminais e dimensões.
- Gate, bulk, W e L adulterados foram rejeitados.
- 1.493 MOS brutos → 1.459 equivalentes após redução legal de paralelos.


**Mensagem:** DRC verifica regras geométricas; LVS compara o circuito extraído.


**Fontes:** [reports/phase2/final_gds/magic.txt](../../reports/phase2/final_gds/magic.txt), [reports/phase2/final_gds/lvs.txt](../../reports/phase2/final_gds/lvs.txt), [reports/phase2/review_20261104/lvs_negative/results.json](../../reports/phase2/review_20261104/lvs_negative/results.json)


---

## 17 — Escrever, manter e recuperar

VALIDAÇÃO ELÉTRICA


- Campanha original: 128 bits lidos + 392 checks adicionais.
- Campanha dirigida: 1.332 checks totais, incluindo 160 bits lidos.
- Walking-one/zero, perturbações pós-captura, idle e máscara viva.


**Mensagem:** Bitcells e sense amplifiers transistor-level; sem armazenamento comportamental.


**Fontes:** [reports/phase2/extracted_access_singlethread/results.json](../../reports/phase2/extracted_access_singlethread/results.json), [reports/phase2/review_20261104/directed/results.json](../../reports/phase2/review_20261104/directed/results.json), [docs/phase2_final_polish.md](../../docs/phase2_final_polish.md)


---

## 18 — Contrato temporal sem números inventados

INTERFACE PÚBLICA


- Subida: captura da requisição. Descida: captura da leitura.
- RAW válido ~7,44 ns antes do clock local; FF_D ~7,25 ns.
- Estabilidade posterior observada ≥2 ns: janela limitada.
- 20 ns = 50 MHz no experimento; Fmax e turnaround pendentes.


**Mensagem:** Janelas internas disponíveis não são setup/hold públicos da SRAM.


**Fontes:** [specs/sram_4x8_timing_contract.md](../../specs/sram_4x8_timing_contract.md), [reports/phase2/final_polish_20261104/capture_directed/results.json](../../reports/phase2/final_polish_20261104/capture_directed/results.json)


---

## 19 — Cinco partidas independentes

SEM RESET EXTERNO


- Rampas 1 / 5 / 10 ns; condicionamento de 0 / 2 / 3 ciclos nas combinações ensaiadas.
- 5 cenários PASS · 3.383 checks totais, incluindo 240 bits lidos.
- Sem IC, nodeset ou conteúdo artificialmente imposto.


**Mensagem:** Zero ciclos inativos ainda incluiu 9 ns de espera após o plateau.


**Fontes:** [reports/phase2/final_polish_20261104/startup_verification/results.json](../../reports/phase2/final_polish_20261104/startup_verification/results.json), [docs/phase2_final_polish.md](../../docs/phase2_final_polish.md)


---

## 20 — Resultados consolidados

ACEITES SEPARADOS


- F2-DIG: síntese/GLS funcional aprovada.
- F2-FIS: SRAM 4×8 integrada e aprovada no experimento nominal.
- DRC/LVS e acessos reais, com artefatos e hashes rastreáveis.
- Contrato temporal documentado e partida ampliada.


**Mensagem:** Desenvolvimento concluído no escopo experimental; revisão formal pendente.


**Fontes:** [docs/phase2_review_20261104_acceptance.md](../../docs/phase2_review_20261104_acceptance.md), [docs/phase2_final_polish.md](../../docs/phase2_final_polish.md), [physical/phase2/delivery.json](../../physical/phase2/delivery.json)


---

## 21 — Limites reconhecidos

ESCOPO EXPERIMENTAL


- Fmax e temporização externa completa ainda não caracterizados.
- Sem RC detalhado, robustez PVT ou partida estatística.
- Sem potência/yield caracterizados ou qualificação de fabricação.
- Geração física 8×8 / 16×8 / 32×8 continua fora desta entrega.


**Mensagem:** Conhecer o limite da evidência faz parte da conclusão técnica.


**Fontes:** [specs/sram_4x8_timing_contract.md](../../specs/sram_4x8_timing_contract.md), [docs/phase2_review_20261104_acceptance.md](../../docs/phase2_review_20261104_acceptance.md)


---

## 22 — Da célula ao sistema SRAM

CONCLUSÕES E DISCUSSÃO


- Controle digital sintetizado e células customizadas integrados.
- SRAM 4×8 física com leitura, escrita e captura demonstradas.
- Fontes, vistas, evidências e procedimentos disponíveis para revisão.


**Mensagem:** Fase 2 tecnicamente concluída no escopo experimental. Fechamento acadêmico depende da equipe e dos orientadores.


**Fontes:** [docs/phase2_reproduction_guide.md](../../docs/phase2_reproduction_guide.md), [docs/phase2_final_polish.md](../../docs/phase2_final_polish.md)

