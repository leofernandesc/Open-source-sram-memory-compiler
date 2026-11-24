# Plano de ação para fechamento da Fase 3

Data: 24/11/2026. Base auditada nesta retomada: `integration/phase3-danilo-ss`, HEAD `486f689b00a63badf4c4b58518711bec225d1eb9`, worktree inicialmente limpo e alinhado ao ref local `origin/integration/phase3-danilo-ss`. O remoto não foi consultado nesta revisão. Plano proposto; não representa aprovação da equipe nem execução das etapas futuras.

### Registro de execução — atualização 24/11

- **P0 concluído:** snapshot integral em `/home/danilo_cunha/projetos/ueletronica/phase3_evidence_20261124`; manifesto revalidado por SHA-256 em 2.717 arquivos / 1.807.007.816 bytes, zero divergências. O `run_state.md` de Phase 1 foi preservado em `metadata/run_state_phase1_20261007.md`; o registro corrente tem run_id `memory-ip_20261124_130441`, `IN_PROGRESS`, sem signoff.
- **P0, delta de fonte:** além do snapshot `build/phase3`, foram preservados os 126 arquivos modificados/não rastreados do checkout histórico; 126/126 foram comparados por SHA-256. O README e os manifestos estão em `phase3_evidence_20261124/README.md` e `phase3_evidence_20261124/metadata/`.
- **P1, classificação (COMPLETO):** replays finais derivados e imutáveis do candidato virtual TT/SS passaram `classification_gate`, `lane_coverage_gate` (9 leituras × 8 bits), `receipt_integrity_gate` e `p1_replay_gate`. Baseline SS v6 também passou: 27 StrongARM PEX + 45 nativos, oito bits únicos por leitura, recibo íntegro. Recibos finais: `derived_integrated/virtual_eight_TT_final/topology_classification.json`, `derived_integrated/virtual_eight_SS_final/topology_classification.json` e `derived_integrated/v6_baseline_SS_final/topology_classification.json`. Os três observers brutos continuam `INCONCLUSIVO` por ownership.
- **P1, suplemento TT:** o auditor preservou o resultado bruto e produziu `PASS_WITH_STATIC_PAYLOAD_WITNESS` somente para c2 bits 4/7 em `derived_integrated/virtual_eight_TT_final/static_payload_witness.json`, com `qualification=NOT_CHARACTERIZED`. É evidência diagnóstica, não fechamento de ownership. O auditor exige `--output` fora do run de entrada, valida recibos/hashes/cobertura e registra hashes dos artefatos de entrada inalterados. 13 regressões locais passaram.
- **P2, SS (INCONCLUSIVO):** candidato e baseline têm a mesma lacuna c12 `read_to_idle`, bit 6, registrada nos recibos finais SS acima. O gate de condução efetivo é 50 ps; os 100 ps são apenas diagnóstico de estresse. Candidate SS mede 57,6 ps no bit0, 80,8 ps nos bits2/4, ≥227 ps nos bits1/3/5/7; baseline mede 64,7 ps no bit0, 87,8 ps nos bits2/4 e ≥234 ps nos bits1/3/5/7. Só o bit6 não tem janela qualificável em ambos. Na onda candidate SS, DATA6 sobe de 0 para 0,951 V em 241,5–242,5 ns com pico weak-host de 1,717 mA; sobe a 1,799 V em 242,5–244 ns enquanto weak-host e DUT conduzem em sentidos opostos até 0,856 mA; em 244–245,5 ns fica em 1,799 V com ambos os ramos abaixo de ~1,5 µA. Isso é drive/corrente antes de restore e possível contention, não prova de ownership correto após restore nem de que a sobreposição seja permitida. O witness iniciado em 244 ns não encontra 50 ps antes da borda de 247 ns. Release é verificada até 247,653 ns em todas as lanes, mas `drive_verified=false`. A causa exige teste controlado.
- **P2, replay de alta resolução — 24/11 (INCONCLUSIVO):** o mesmo fixture candidato SS de 370 ns foi reexecutado com PEX, modelo, estímulos e guard de 1,5 ns preservados; passo máximo nativo de 10 ps e somente vetores de observação necessários. ngspice 44.2 terminou com código 0; 38.241 amostras, passo máximo observado 10,000 ps. Sete lanes atendem ao witness de 50 ps; o bit6 não. A região contínua interpolada do bit6 é 51,677 ps (246,948323–247 ns), mas o primeiro ponto nativo é 246,954950 ns, deixando apenas 45,050 ps conservadores até a borda de controle. Release passa nas oito lanes até 247,655195 ns. Isso mostra uma janela de drive extremamente curta, sem qualificar o gate; P2 permanece aberto e nenhuma regra foi relaxada. O replay, deck, log e onda estão preservados em `phase3_evidence_20261124/build/phase3/diagnostics/c12_highres_candidate_ss_20261124/`.
- **P3, replay integrado FF — 24/11 (PARCIAL):** o fixture candidato virtual de 18 ciclos completou 370 ns em ngspice 44.2 sobre o envelope RC da PEX v6 `a1e812…`; todas as 18 operações funcionais passam. O observer de ownership continua `INCONCLUSIVO` em c2 (`write`) e c10 (`read_to_write`); c12 `read_to_idle` passa em FF. O runner legado recusou a preparação antes de simular porque está preso a outro PEX (`12c41…`); a execução direta e a análise vinculadas à PEX correta estão documentadas no manifesto. Evidência em `phase3_evidence_20261124/build/phase3/diagnostics/strongarm_eight_integrated_ff_20261124/`. Isso não fecha P3 entre corners nem a qualificação elétrica.
- **Limite do ambiente na auditoria inicial:** a busca direta do executável não encontrou `ngspice` no PATH então configurado. Nesta retomada, o launcher adicionou `/opt/*/bin`, validou o container/PDK e encontrou ngspice 44.2. Os resultados anteriores à recuperação são reanálises; os dois novos transientes SS/FF estão identificados acima.

### Auditoria offline inicial — 24/11

- **Auditoria offline concluída antes da recuperação EDA:** branch confirmada em `integration/phase3-danilo-ss`, HEAD `4395e2ae`, quatro commits locais à frente de `origin/integration/phase3-danilo-ss`, worktree limpo antes destas atualizações de documentação. `memory/memory-ip/knowledge.md` não existe. No host há Python 3.12.3, sem executáveis EDA no PATH.
- **Recuperação do simulador concluída sem reinstalação:** a inspeção encontrou `sram-xschem` parado, imagem `isaiassh/unic-cass-tools:1.1.0` e montagem correta deste checkout em `/work`. `./tools/sram-eda --check` iniciou o container e passou: ngspice 44.2, Magic 8.3.613, Netgen 1.5.293, Icarus 13.0, Yosys 0.44, OpenROAD, Xschem, Python com gdstk 0.9.62/NumPy 1.26.4 e arquivos SKY130A requeridos presentes. O container permanece iniciado. Naquele ponto da auditoria não houve simulação; os replays SS de alta resolução e FF descritos acima foram executados depois. KLayout/OpenSTA não foram incluídos no check e não estão confirmados.
- **Próxima recuperação/uso:** executar comandos EDA pelo `./tools/sram-eda`, que valida o bind mount, configura `PDK_ROOT=/opt/pdks`, `PDK=sky130A` e injeta `/opt/*/bin` no PATH. Não há justificativa para reconstruir a imagem nem instalar ngspice paralelo. Antes de simular, preparar fixture controlada, confirmar probes/estímulos e reservar diretório de saída rastreável.
- **SNM reconciliado nesta revisão:** os `summary.json` históricos contêm Hold 200 válidas/200 tentativas e Read 200 válidas/206 tentativas, com seis erros e plano de 220 seeds. O arquivo posterior `snm_endpoints_final_20261120/audit.json` registra **Hold 200 e Read 206 válidas**, sem novas simulações: corrigiu o tratamento dos extremos das VTCs das seeds Read 30005, 30021, 30053, 30090, 30148 e 30192. O mínimo de 200 já está atendido nesse piloto; 220 é o planejamento da campanha, não o mínimo da especificação. Não repetir 406 seeds nem executar as 34 restantes automaticamente. A auditoria declara `tt_mm`, mismatch local ativo e processo global desativado, a 1,8 V/27 °C, em bitcell esquemática. Persistem homologação de método/domínio e definição da evidência pós-layout exigida. Preservar os resumos originais, a auditoria derivada e a ligação por hashes; ainda não é qualificação final.
- **Liberty existente não é final:** `build/phase3/danilo_ss_ff2_spaced_route/macro_interface.lib` declara `phase2_uncharacterized_interface` e contém interface/pinos sem tabelas de timing/potência. Pode servir para auditoria estática de nomes/unidades; não satisfaz P9 e não deve ser promovida. O contrato `docs/phase3_characterization_contract.md` confirma que falta implementar gerador `.lib`, lookup tables, sweeps de setup/hold, extração de waveform e validação sintática/contra SPICE.
- **Dimensões:** a especificação §§20–21 exige caracterização pelo menos em 8×8 e 32×8 e prevê geração nas profundidades 4/8/16/32. O handoff confirma geração física, DRC/LVS/PEX e caracterização de 8×8/32×8 pendentes. A aceitação de nomes de configuração pelo contrato/infraestrutura não representa existência de circuitos físicos. Para fechar integralmente, gerar as duas dimensões, validar vistas/DRC/LVS/PEX e caracterizar o escopo exigido; alternativa é obter e registrar alteração formal de escopo. Nenhuma exceção foi aprovada.
- **Pode avançar sem simulador:** revisar requisitos e domínio elétrico pendente; auditar manifests/hashes e cobertura dos dados preservados; revisar seeds/invalids SNM e fazer análise estatística offline; auditar interface e preparar/testar estaticamente o gerador Liberty sem publicar valores; preparar o fixture e critérios/controles negativos do teste c12. Essas ações não aprovam ownership, desempenho, SNM final ou Liberty.
- **Dependências não concluídas:** revisar com a equipe se o protocolo/intervalo pode oferecer witness conservador ≥50 ps e executar teste controlado correspondente; não reduzir o piso. Depois, fechar comparação virtual e selecionar formalmente arquitetura; fechar geometria final e PEX; repetir C250/integrado TT/SS/FF no PEX escolhido; caracterizar acesso, tDIS, setup/hold e potência/energia; completar/homologar SNM; gerar e validar Liberty; gerar/qualificar 8×8 e 32×8 ou aprovar formalmente mudança de escopo; revisão cruzada e pacote reproduzível. O container/PDK está validado, mas P2 segue inconclusivo e `signoff_achieved=false`.

## 1. Conclusão da análise

A Fase 3 está em fechamento funcional experimental. A infraestrutura, a recuperação dos checkpoints e uma macro física v6 estão disponíveis. A comparação virtual de oito StrongARM passou C250 nos três corners; em FF, o replay integrado passa funcionalmente nas 18 operações, mas dois eventos de ownership permanecem inconclusivos. Em SS, c12/bit6 ainda não alcança o witness conservador. Ainda faltam aceite integrado completo entre corners, escolha e congelamento da geometria final, caracterização elétrica, SNM homologado, Liberty validada e entrega reproduzível.

Oito StrongARM virtuais não constituem oito células físicas extraídas: cinco núcleos e seus buffers foram acrescentados sobre as rotas RC da v6. Portanto os resultados não autorizam transferir timing, potência ou DRC/LVS da v6 para uma nova geometria.

## 2. Fontes, alcance e inventário

Foram confrontados a especificação técnica (§§19–21), o plano operacional da Fase 3, o contrato de caracterização, o handoff de 22/11, a auditoria de oito StrongARM, os scripts novos e os recibos/análises TT/SS/baseline. A revisão do plano conferiu documentos, código do runner e relatórios persistidos, incluindo o diagnóstico FF e a auditoria final SNM. Os transientes SS/FF são resultados da rodada anterior; nesta revisão não foram executadas simulações, DRC/LVS nem campanhas SNM.

Fontes versionadas:

- [Especificação técnica](../specs/technical_specification.md).
- [Plano original e responsabilidades atualizadas em 13/11](phase3_plan_to_20261123.md).
- [Contrato de caracterização](phase3_characterization_contract.md).
- [Contrato temporal](../specs/sram_4x8_timing_contract.md).
- [Handoff técnico e matriz de 22 requisitos](phase3_handoff_equipe_20261122.md).
- [Guia de recuperação](phase3_transfer_quickstart.md).
- [Auditoria experimental recente](phase3_auditoria_virtual_oito_strongarm_20261123.md).

Os dados originais continuam em `/tmp/phase3-v6-handoff-20261122/historical-checkout/build/phase3/` e sua cópia persistente, validada por manifesto, está em `/home/danilo_cunha/projetos/ueletronica/phase3_evidence_20261124/build/phase3/`. Os diagnósticos novos têm manifestos próprios sob `diagnostics/`; o manifesto P0 descreve o snapshot original e não deve ser tratado como inventário atualizado desses acréscimos. A cópia local persistente não comprova distribuição dos novos artefatos à equipe. Preparar pacote incremental e verificar recuperação independente em P10.

| Frente | Evidência disponível | Limite ou pendência |
|---|---|---|
| Infraestrutura | Runner, contratos, validação nominal histórica e recibos | PASS de infraestrutura não qualifica a SRAM pós-layout |
| Histórico A/B/B′/C | Diagnósticos RC, clock, sense, barramento e SNM documentados | Não combinar métricas de variantes diferentes numa caracterização final |
| v6 física: 3 StrongARM | Handoff registra DRC=0, LVS único, PEX selado e C250 TT/SS/FF PASS | Regressão completa da geometria escolhida ainda necessária |
| Oito StrongARM virtuais, C250 | TT/SS/FF: qualification PASS | TT válido está em `strongarm_eight_virtual_20261123_retry1_analysis/TT`; o `retry1/TT` original contém análise inconclusiva. Preservar a ligação entre onda original e mapa corrigido |
| Integrado virtual TT | Reanálise derivada: topologia 72/72 StrongARM PEX; recibo 370 ns/319 hashes; dados 18/18 | Observer bruto INCONCLUSIVO no write c2, bits 4/7; suplemento externo é diagnóstico, não ownership/signoff |
| Integrado virtual SS | Reanálise derivada: topologia 72/72 StrongARM PEX; recibo 370 ns/319 hashes; dados 18/18 | INCONCLUSIVO no read→idle c12, bit 6; drive witness ausente |
| Controle v6 integrado SS | Topologia derivada passou: 27 StrongARM PEX + 45 nativos; recibo e cobertura PASS | Observer bruto ainda INCONCLUSIVO em c12/bit 6; a classificação de topologia não fecha ownership |
| Integrado virtual FF | Replay diagnóstico concluído em PEX identificado; waveform e manifestos verificados | Funcional 18/18 PASS; ownership inconclusivo em c2 write e c10 read→write; c12 passa apenas em FF; controles internos não avaliados pelo analisador diagnóstico. Não fecha o gate comparável TT/SS/FF nem signoff |
| Timing e potência finais | Medidas exploratórias/históricas em C e margens internas | Setup, hold, acesso, desabilitação, energia, leakage e domínio final não homologados |
| SNM | Auditoria final confere Hold 200/Read 206 válidas; piloto esquemático `tt_mm` | Homologar método, domínio e recorte pós-layout; mismatch local não cobre processo global |
| Liberty | Interface/infraestrutura histórica disponível | Geração a partir de tabelas qualificadas e validação ainda pendentes |
| 8×8 / 32×8 | Requisitos explícitos na especificação | Geração física e caracterização dessas dimensões pendentes; dependência da Fase 4 |

TT/SS/FF dos experimentos recentes usam o ponto nominal de tensão/temperatura e carga da fixture. Três corners de processo nesse ponto não representam toda uma grade PVT, slew e carga.

## 3. Correções necessárias na interpretação dos resultados

1. **Topologia por variante.** TT/SS candidatos passam 72/72 lanes StrongARM PEX. O gate baseline corrigido espera 3 lanes StrongARM PEX e 5 nativas por leitura; o replay derivado passou 27/45 em nove leituras, com recibo e cobertura PASS.
2. **Suplemento estático.** O auditor foi endurecido para comprovar duração/recibo/SHA-256, 18 ciclos únicos, 8 lanes cobertas, condições de isolamento e janela mínima com amostras. A saída é obrigatoriamente externa ao run de entrada. O suplemento aceita somente c2 bits 4/7 sem transição e mantém o raw inconclusivo; seus 13 testes cobrem hash divergente, recibo falho, ciclos incompletos/duplicados, overlap e janelas insuficientes.
3. **Ownership SS não resolvido.** Candidato e baseline repetem c12 bit 6. O gate `drive_verified` usa `WITNESS_NS=50 ps`; 100 ps é apenas diagnóstico. Bits 0/2/4 têm 57,6/80,8/80,8 ps e passam o gate; bits 1/3/5/7 também. Bit 6 não tem condução qualificável. A repetição baseline mostra que o gap não é exclusivo do ECO virtual, mas não identifica se falta estímulo/observabilidade ou drive elétrico.
4. **Rastreabilidade.** Distinguir snapshot original, reanálises derivadas e saída do suplemento. Os runs permanecem ligados aos hashes de waveform/modelos; não alterar os resultados brutos. O container EDA foi verificado e ngspice 44.2 executou o replay candidato SS de alta resolução e o integrado FF. O runner legado SS recusou o PEX FF por divergência de hash; o diagnóstico FF foi executado diretamente com proveniência explícita, sem alterar nem mascarar o PEX.

Esses pontos foram identificados por inspeção de fonte/recibos e devem ser resolvidos antes de promover o suplemento a critério de aceite.

## 4. Sequência de execução e gates

Responsáveis abaixo seguem a distribuição operacional de 13/11; representam encaminhamento proposto, não disponibilidade confirmada. Danilo: RC/timing/potência. André: leitura/sense/barramento. Leonardo: infraestrutura/integração/Liberty. Ícaro: SNM/Monte Carlo.

| Etapa | Ação e entregável | Responsável proposto | Dependência | Critério para avançar |
|---|---|---|---|---|
| P0 — Preservar evidência | **Concluído:** cópia integral, manifesto SHA-256 e proveniência; run_state Phase 1 arquivado e novo run_state Fase 3 iniciado | Danilo | Concluído | 2.717 arquivos / 1.807.007.816 bytes rehashados; zero divergências |
| P1 — Corrigir observadores | **COMPLETO:** topologia parametrizada, três replays finais, suplemento conservador e 13 testes | Leonardo + André; revisão Danilo | P0 | Gates de topologia, cobertura e recibo PASS nos três runs; resultado bruto permanece preservado |
| P2 — Resolver ownership | **INCONCLUSIVO:** SS c12/bit6 permanece em 45,050 ps conservadores; TT c2/bits4/7 depende de witness estático homologado; FF c2/c10 exige diagnóstico por lane | André + Danilo; revisão Leonardo | P1 | Revisar metodologia/intervalo e rodar contraste controlado com critério pré-aprovado; manter piso de 50 ps; não inferir PASS |
| P3 — Completar comparação virtual | **PARCIAL:** FF tem 18/18 operações, mas ownership e controles completos pendentes; integrar perfil por PEX/corner e comparar candidato/v6 no mesmo protocolo | Danilo | P2 | Nove palavras/72 bits, seis escritas com readback, quatro linhas, retenção e ownership aprovados em TT/SS/FF sobre PEX identificada |
| P4 — Escolher arquitetura | Registrar decisão v6 híbrida versus oito StrongARM, custos físicos, carga/clock, margens, risco e fallback | Equipe; André e Danilo apresentam evidências | P3 | Variante escolhida e escopo aprovados; nenhuma seleção automática baseada só no C250 |
| P5 — Fechar geometria | Se oito: gerar cinco novas células/rotas, revisar clock/rails, obter GDS/LEF/netlist, DRC/LVS/PEX. Se v6: validar identidade da geometria já qualificada | Danilo + André; integração Leonardo | P4 | DRC zero, LVS único com parâmetros, PEX distribuído auditado e vistas coerentes por hash |
| P6 — Qualificar candidata física | Repetir C250 e integrado completo com PEX final e grade funcional aprovada; revisar modelo Verilog/protocolo | Danilo + André | P5 | Aceite funcional e ownership completos da mesma geometria em todo domínio declarado |
| P7 — Caracterizar eletricamente | Gerar tabelas de acesso, clock→DATA quando aplicável, tDIS/Hi-Z, setup/hold, energia e potência estática/dinâmica | Danilo; revisão André | P6 + domínio congelado | Matrizes rastreáveis por PVT/slew/carga, limites e unidades claros, nenhuma célula inválida convertida em número |
| P8 — Homologar SNM | Revisar VTCs e extração hold/read; seeds, modelos, N≥200 conforme escopo, estatística e amostras inválidas; complementar se necessário | Ícaro; revisão Danilo | Método pode andar em paralelo; domínio final depende P4–P6 | Método e resultados aprovados; distinguir mismatch, processo, pre-layout e pós-layout; não inferir yield da macro |
| P9 — Gerar e validar Liberty | Consumir tabelas aprovadas, gerar arcos condicionais e tri-state, constraints e potência; validar leitura e comparar pontos com SPICE | Leonardo; revisão Ícaro/Danilo | P7 e domínio aprovado | Biblioteca reproduzível, unidades/pinos/arcos corretos e concordância em tolerância definida antes da comparação |
| D1 — Atender dimensões exigidas | **PENDENTE:** definir decoder maior; gerar 8×8/32×8, DRC/LVS/PEX, validar e caracterizar cada macro; registrar dependência da Fase 4 | Leonardo + Danilo + André; SNM Ícaro | Decisão de escopo e P4; aplicar P5–P9 por configuração | Resultados próprios nas duas dimensões ou alteração formal de escopo; nunca escalar tabelas 4×8 |
| P10 — Entregar e revisar | Relatório final, vistas, dados, release e reprodução independente | Leonardo + equipe | P6–P9 e D1 resolvido | Revisão cruzada registrada, pacote recuperável por outro membro e requisitos completos ou exceções explicitamente aprovadas |

Caminho crítico do 4×8: P0 → P1 → P2 → P3 → P4 → P5 → P6 → P7 → P9 → P10. P8 também condiciona P10. Para o fechamento integral, D1 exige o fluxo físico/elétrico por dimensão e converge em P10; não é apenas uma decisão administrativa ao fim. Definição do domínio, preparação do gerador Liberty e revisão SNM podem avançar em paralelo.

### 4.1 Rastreabilidade dos 22 requisitos do handoff

A numeração abaixo é a da Parte H do handoff de 22/11. O estado é atualizado por esta revisão; o handoff permanece histórico.

| Requisitos do handoff | Etapas deste plano | Entrega que ainda falta |
|---|---|---|
| 1 — Sense definitivo | P3–P4 | Comparação pareada, custos/cargas/margens e decisão de arquitetura |
| 2–5 — Integração, DRC, LVS, PEX | P5, D1 | Identidade da geometria escolhida e provas físicas correspondentes |
| 6–8 — PVT funcional, integrado, barramento | P2–P3, P6 | Todos os checks, inclusive controles internos e ownership, nos três corners |
| 9–12 — Acesso, desabilitação, setup, hold | P7 | Matrizes por arco/pino/transição, busca de fronteiras e limites declarados |
| 13–15 — Potência estática, dinâmica, energia | P7 | Medição na alimentação da macro, estado/atividade/janela e baseline explícitos |
| 16–17 — SNM e Monte Carlo | P8 | Homologação do piloto e complemento físico/domínio conforme requisito aprovado |
| 18 — Slew e carga | P7 | Grade e tolerâncias congeladas; cobertura e pontos-limite auditáveis |
| 19–20 — Geração e validação Liberty | P9 | Gerador automático, tabelas reais, parser consumidor e comparação SPICE |
| 21 — Configurações adicionais | D1 | 8×8/32×8 caracterizadas; rastrear geração 4/8/16/32 ao marco do compilador |
| 22 — Documentação e entrega | P10 | Relatório, fontes, vistas, pacote incremental e reprodução por outro membro |

### 4.2 Decisões necessárias antes das campanhas finais

Registrar responsável, decisão, justificativa, data e documento de aceite para: (a) arquitetura v6/oito StrongARM e prioridade robustez/desempenho/potência/área; (b) temperatura nominal e domínio PVT/slew/carga; (c) método de witness e tratamento de payload estático; (d) recorte SNM esquemático/pós-layout e cobertura de variação; (e) integração de 8×8/32×8 ao calendário e estratégia dos decoders maiores. A especificação deixa temperatura, prioridade de otimização e decoder maior em aberto. Não inventar valores de aprovação nem considerar o plano uma ratificação.

A preparação dos scripts, fixtures, tabelas de cobertura e propostas pode avançar já. Uma aprovação técnica pendente impede a promoção a resultado qualificado, não a investigação documentada dentro do escopo existente.

## 5. Trabalho imediato para o bloqueio de ownership

1. **Concluído:** reprocessar ondas existentes e verificar hashes/cobertura antes do novo transiente.
2. **Concluído:** replay candidato SS completo, com PEX, estímulos e guard preservados e passo máximo de 10 ps. O waveform e os manifests foram verificados e arquivados.
3. **Concluído:** o observer inalterado aplicou 50 ps e três amostras nativas. Sete lanes passam, a release passa em todas e o bit6 permanece inconclusivo.
4. **Resultado:** no bit6 a região elétrica interpolada satisfaz os limiares por 51,677 ps, mas o primeiro ponto nativo deixa 45,050 ps conservadores antes da borda de 247 ns. Em 247 ns, DATA6=1,488 V, TE_B=0,0878 V, corrente do probe weak=+312,3 µA e corrente DUT=−372,9 µA. Há condução concorrente no fim da janela; o observer não a aprova como witness mínimo. A onda não permite concluir se o intervalo prático atende ao protocolo sem revisão da regra/temporização.
5. **Próximo passo de metodologia:** acordar um intervalo de witness/protocolo que preserve o piso conservador de 50 ps, então executar contraste controlado e comparar baseline/candidato se necessário. Não alterar o critério depois de ver o resultado e não usar atraso artificial como prova de conformidade do fixture original.
6. Incluir/confirmar controles negativos: contenção deliberada e driver sem condução devem reprovar; nenhuma redução de limiar deve ser escolhida apenas para obter PASS.
7. Homologar a regra de TT para payload estático, preservando o resultado bruto e justificando todas as condições de aplicação. Repetir o integrado com critérios aprovados antes do aceite final.

### 5.1 Fila executável de diagnóstico e infraestrutura

| Ordem / vínculo | Trabalho concreto | Saída e condição de conclusão |
|---|---|---|
| 1 / P2 | Comparar no FF c2 e c10 as lanes, controles de host, DATA, TE_B e correntes com TT/SS; localizar o primeiro witness ausente | Relatório por evento/bit com tempos e motivo. Não assumir que a regra de payload estático TT se aplica ao FF |
| 2 / P2 | Preparar hipótese discriminante para SS c12: resolução temporal versus estímulo/drive; especificar variável alterada, baseline, observações e limiares antes de rodar | Fixture diagnóstica e critérios versionados; manter 50 ps/três amostras e separar resultado no protocolo original de resultado com estímulo alterado. Refinamento temporal só com hipótese de convergência e orçamento, sem busca cega por PASS |
| 3 / P2 | Demonstrar que contenção deliberada e ausência de drive reprovam; revisar witness de payload estático | Controles negativos e positivos com classificação esperada; supplement não promove automaticamente o raw |
| 4 / P3 | Resolver incompatibilidade entre preparador e runner: PEX preparada `a1e812…`, runner legado `12c41…` | Perfil explícito por variante/corner, identidade GDS/PEX/binding/modelos e topologia; rejeitar troca indevida de PEX. Não remover simplesmente a checagem nem substituir hashes esperados para passar |
| 5 / P3 | Integrar no perfil FF os controles omitidos pelo diagnóstico: WL/pré-carga/escrita/sense, captura local e recuperação | Cobertura esperada por categoria/bit/ciclo, relatório de controles e integridade de recibos. Reanalisar a onda existente se contiver todos os vetores; simular apenas o que faltar |
| 6 / P3 | Consolidar TT/SS/FF do candidato e comparação v6 exigida pela decisão, sob protocolo e ferramentas identificados | Matriz por variante/corner com função, ownership, controles, topologia e recibo; nenhum check ausente ou inconclusivo tratado como PASS |

P1 concluído cobre as correções e replays documentados. Qualquer novo perfil ou observador nos passos acima exige sua própria verificação; o PASS histórico de P1 não cobre automaticamente FF nem os controles negativos futuros.

## 6. Domínio elétrico e critérios de caracterização

Antes das matrizes, registrar valores numéricos aprovados para tensão, temperatura, slew, carga, período/duty, guardas, limiares, estado inicial e tolerâncias. As cargas 5/10/20 fF são propostas históricas; não tratar uma proposta como domínio homologado. Respeitar os limites do PDK e os contratos de pinos.

- Acesso: da borda pública contratada até a palavra nova inteira correta e estável. Releituras sem transição não fornecem atraso zero.
- tDIS: medir liberação sustentada por CSb/OEb/WEb e polaridade, com witness de Hi-Z.
- Setup/hold: buscar fronteiras por entrada capturada e operação; conferir armazenamento/readback e ownership, não só um nó interno. Refinar a fronteira com tolerância definida.
- Potência estática: clock parado, estado conhecido, repouso suficiente e fonte explicitada.
- Energia/dinâmica: integrar V×I em janelas de operação comparáveis, declarar contribuição de clock/pré-carga/carga e tratar leakage separadamente.
- SNM: método e população adequados ao requisito; conservar seeds ruins e falhas de extração, sem seleção das amostras favoráveis.
- Liberty: usar apenas a geometria e o domínio qualificados; validar semântica da memória e barramento bidirecional, condicionamento dos arcos, interpolação e coerência com o modelo funcional.

### 6.1 Implementação necessária para caracterização reproduzível

O contrato é infraestrutura preparada, não implementação completa de P7/P9. `tools/phase3/runner.py` mantém `sram_characterized=False`; `tools/phase3/functional_a.py:characterization_status` agrega `NOT_CHARACTERIZED` por ausência de qualificação B. Essa proteção precisa de uma implementação explícita do novo perfil e critérios aprovados, com compatibilidade dos perfis históricos; não basta trocar um booleano ou aceitar código de saída zero.

| Entrega de software | Responsável proposto | Aceite |
|---|---|---|
| Preparador paramétrico PVT/slew/carga | Leonardo + Danilo | Cada parâmetro aplicado a modelos, fontes, estímulos e cargas; netlist e dependências pinadas; recusar corner/PEX incompatível |
| Extrator de métricas e busca setup/hold | Danilo; revisão André | Arcos e polaridades definidos, waveforms finitas/completas, fronteiras delimitadas, refinamento/tolerância e casos sem transição ou censurados preservados |
| Perfil de qualificação B e agregador | Leonardo; revisão Danilo/André | Função, controles, ownership, cobertura e medidas aprovados independentemente; ausência, FAIL, ERROR e INCONCLUSIVO nunca promovidos; regressões preservam os perfis legados |
| Consolidador de tabelas | Danilo + Leonardo | CSV/JSON e manifestos rastreáveis por configuração, geometria, corner, VDD, temperatura, slew, carga, arco e polaridade; cobertura exigida sem lacunas ocultas |
| Gerador Liberty simplificada | Leonardo; revisão Ícaro/Danilo | Gerar automaticamente apenas a partir de tabelas aprovadas; validar unidades, pinos, índices, semântica de memória, enable/tri-state e condicionamento de arcos |
| Validador consumidor e comparação SPICE | Leonardo + Danilo | Ferramenta/versão consumidoras verificadas, leitura e arcos inspecionados; comparar pontos de tabela e pontos intermediários com tolerância definida previamente |

Para mudanças nesses scripts, incluir regressões de integridade/corner/troca de PEX, medidas ausentes, cobertura insuficiente e interpolação; executar os testes relevantes e o preflight antes de campanhas longas. As 13 regressões anteriores são evidência do auditor estático, não cobertura de todo esse desenvolvimento.

### 6.2 Entrega de SNM e critérios públicos

P8 deve produzir tabela por seed/tentativa com hashes de VTC, classificação original e revisada, método, modelo, estatística e alcance. Revisar as seis reclassificações Read e as hipóteses do extrator. Homologar a população `tt_mm` e definir quais medições adicionais com PEX final atendem ao requisito pós-layout e às dimensões exigidas. Mudança de modelo, temperatura ou circuito exige nova evidência no domínio afetado. Média, dispersão e intervalo de confiança da média não comprovam yield da macro nem cobertura de variação global.

Distinguir os parâmetros obrigatórios de caracterização dos limites ainda não prometidos. Declarar período/duty, rampas e condicionamento usados, margens de BL/SCLK/captura e recuperação observadas. Se a entrega passar a declarar Fmax, pulso mínimo, tSTARTUP ou limites universais de turnaround, esses limites exigem campanhas próprias; os 20 ns e a guarda de 1,5 ns são condições dos ensaios existentes. Definir limites numéricos de aceite/desempenho com a equipe antes das matrizes, ou declarar apenas o domínio medido sem inventar uma especificação de produção.

## 7. Dimensões e definição de encerramento

A especificação exige resultados pelo menos em 8×8 e 32×8, embora o cronograma original coloque sua geração na Fase 4. Há duas entregas possíveis, que não devem receber o mesmo status:

- **Fechamento técnico do 4×8:** todos os gates da geometria 4×8, relatório, SNM no escopo aprovado e Liberty. Continua entrega parcial frente ao requisito dimensional integral, salvo revisão formal de escopo.
- **Fechamento integral da Fase 3:** além do 4×8 de referência, disponibilizar e caracterizar as configurações exigidas com vistas e evidências próprias, ou registrar uma alteração formal do requisito pelos responsáveis.

Não extrapolar tabelas do 4×8 para outras profundidades: BL/WL, decoder, RC, potência e margens mudam. A decisão de antecipar essas configurações ou completar a entrega na Fase 4 precisa constar do plano aceito.

Para 16×8, a especificação exige suporte e vistas no compilador; a exigência explícita de resultados de caracterização mínimos cita 8×8 e 32×8. Rastrear a geração 16×8 ao marco acordado sem criar, por inferência, uma nova matriz elétrica obrigatória de Fase 3. O relatório final deve distinguir requisito atendido, pendência da Fase 4 e qualquer mudança de escopo efetivamente aprovada.

Otimização de área não é uma condição extra de fechamento desta rodada. Se escolhida, começar pelo posicionamento periférico conforme handoff; qualquer mudança física retorna a P5/P6 e invalida a transferência direta dos números elétricos anteriores. Preservar os seletores e artefatos congelados das Fases 1/2.

## 8. Orçamento e organização das próximas rodadas

As três execuções integradas recentes levaram aproximadamente 27,8–29,5 minutos por corner neste ambiente, sem contar preparação/análise. Reservar cerca de 1,5 hora de simulação serial para três runs de 370 ns comparáveis; isso não estima setup/hold, Monte Carlo ou nova extração física.

Usar `workers=1` inicialmente e estimar a grade após piloto: número de variantes × corners × tensões × temperaturas × slews × cargas × estímulos × repetições. Registrar timeout e custo por ponto. Não é responsável fixar uma data final antes de resolver ownership, arquitetura e dimensões.

Próxima rodada: itens 1–5 de §5.1, revisão SNM e contrato de domínio em paralelo. Em seguida: fechar P3 e decidir P4, iniciar P5/D1 conforme escopo. Depois: P6, pilotos P7/P8, completar matrizes e P9, culminando em P10. P0/P1 já realizados não são trabalho a repetir por rotina.

Antes de reservar cada campanha, estimar quantidade de pontos, custo medido por ponto, espaço de waveform, memória e timeout. Setup/hold acrescentam iterações de busca; Monte Carlo acrescenta seeds e modos. As durações históricas acima são referência do integrado, sem promessa de prazo para caracterização. Registrar checkpoints por gate e responsáveis; revisar o cronograma após o piloto de cada matriz.

### 8.1 Pacote de entrega e reprodução — P10

- Relatório de caracterização com configuração/arquitetura/domínio, métodos, matrizes, SNM, limitações e matriz dos 22 requisitos preenchida com evidências.
- Fontes e receitas versionadas; GDS, LEF, netlist/PEX, Verilog e Liberty com nomes de pinos, dimensões, alimentação e identidade coerentes. Conferir equivalência do comportamento público: subida para captura, descida para leitura, controles vivos, DATA bidirecional e partida sem reset.
- Manifesto da entrega final e pacote incremental dos diagnósticos/novas campanhas, com checksums, versões/digests efetivamente usados, comandos e dependências. Não confundir Magic disponível no container com a versão registrada na extração histórica; conferir a cadeia da ferramenta ao reproduzir.
- Guia de recuperação atualizado para o conjunto novo, fontes dos analisadores atualmente em diretórios de evidência e paths portáveis. Manter a recuperação histórica separada; verificar que todas as dependências necessárias existem fora de `/tmp`.
- Reprodução por outro membro em checkout limpo e diretório novo: recuperação/hashes, regeneração das tabelas/Liberty e execução de pontos representativos com comparação. Registrar o que foi reproduzido e o que permaneceu apenas arquivado.
- Revisão cruzada conforme responsabilidades, identificação do SHA fonte e aceite do domínio. Publicação da entrega como qualificada depende desses gates; o release experimental anterior não é substituído por um rótulo novo sem evidência.

## 9. Checklist de encerramento

- [ ] Escopo dimensional, domínio elétrico e arquitetura formalizados.
- [x] Snapshot inicial P0 preservado e auditado; correções/replays P1 documentados.
- [ ] Fontes, ferramentas, modelos e todos os artefatos finais preservados com manifesto recuperável, incluindo os acréscimos ao P0.
- [ ] Observadores auditados, cobertura completa e controles negativos aprovados.
- [ ] Geometria final com DRC/LVS/PEX e vistas consistentes.
- [ ] C250 e integrado TT/SS/FF aprovados no domínio declarado, incluindo ownership.
- [ ] Perfil final de caracterização implementado, validado e vinculado à PEX/domínio aprovados.
- [ ] Timing, setup/hold, tDIS, potência/energia medidos e revisados.
- [ ] SNM e Monte Carlo homologados com N e escopo exigidos.
- [ ] Liberty gerada de dados reais e validada contra SPICE/ferramentas consumidoras.
- [ ] 8×8/32×8 atendidos ou alteração formal de requisito registrada.
- [ ] Reprodução independente, revisão cruzada e entrega final aprovada.

Estado atual: nenhum PASS experimental isolado autoriza marcar essa lista completa. `electrical_qualification=NOT_CHARACTERIZED` permanece até a evidência correspondente ser produzida e aprovada.
