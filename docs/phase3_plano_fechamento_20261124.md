# Plano de ação para fechamento da Fase 3

Data: 24/11/2026. Base auditada nesta retomada: `integration/phase3-danilo-ss`, HEAD `4395e2ae`, quatro commits à frente do remoto. Plano proposto; não representa aprovação da equipe nem execução das etapas futuras.

### Registro de execução — atualização 24/11

- **P0 concluído:** snapshot integral em `/home/danilo_cunha/projetos/ueletronica/phase3_evidence_20261124`; manifesto revalidado por SHA-256 em 2.717 arquivos / 1.807.007.816 bytes, zero divergências. O `run_state.md` de Phase 1 foi preservado em `metadata/run_state_phase1_20261007.md`; o registro corrente tem run_id `memory-ip_20261124_130441`, `IN_PROGRESS`, sem signoff.
- **P0, delta de fonte:** além do snapshot `build/phase3`, foram preservados os 126 arquivos modificados/não rastreados do checkout histórico; 126/126 foram comparados por SHA-256. O README e os manifestos estão em `phase3_evidence_20261124/README.md` e `phase3_evidence_20261124/metadata/`.
- **P1, classificação (COMPLETO):** replays finais derivados e imutáveis do candidato virtual TT/SS passaram `classification_gate`, `lane_coverage_gate` (9 leituras × 8 bits), `receipt_integrity_gate` e `p1_replay_gate`. Baseline SS v6 também passou: 27 StrongARM PEX + 45 nativos, oito bits únicos por leitura, recibo íntegro. Recibos finais: `derived_integrated/virtual_eight_TT_final/topology_classification.json`, `derived_integrated/virtual_eight_SS_final/topology_classification.json` e `derived_integrated/v6_baseline_SS_final/topology_classification.json`. Os três observers brutos continuam `INCONCLUSIVO` por ownership.
- **P1, suplemento TT:** o auditor preservou o resultado bruto e produziu `PASS_WITH_STATIC_PAYLOAD_WITNESS` somente para c2 bits 4/7 em `derived_integrated/virtual_eight_TT_final/static_payload_witness.json`, com `qualification=NOT_CHARACTERIZED`. É evidência diagnóstica, não fechamento de ownership. O auditor exige `--output` fora do run de entrada, valida recibos/hashes/cobertura e registra hashes dos artefatos de entrada inalterados. 13 regressões locais passaram.
- **P2, SS (INCONCLUSIVO):** candidato e baseline têm a mesma lacuna c12 `read_to_idle`, bit 6, registrada nos recibos finais SS acima. O gate de condução efetivo é 50 ps; os 100 ps são apenas diagnóstico de estresse. Candidate SS mede 57,6 ps no bit0, 80,8 ps nos bits2/4, ≥227 ps nos bits1/3/5/7; baseline mede 64,7 ps no bit0, 87,8 ps nos bits2/4 e ≥234 ps nos bits1/3/5/7. Só o bit6 não tem janela qualificável em ambos. Na onda candidate SS, DATA6 sobe de 0 para 0,951 V em 241,5–242,5 ns com pico weak-host de 1,717 mA; sobe a 1,799 V em 242,5–244 ns enquanto weak-host e DUT conduzem em sentidos opostos até 0,856 mA; em 244–245,5 ns fica em 1,799 V com ambos os ramos abaixo de ~1,5 µA. Isso é drive/corrente antes de restore e possível contention, não prova de ownership correto após restore nem de que a sobreposição seja permitida. O witness iniciado em 244 ns não encontra 50 ps antes da borda de 247 ns. Release é verificada até 247,653 ns em todas as lanes, mas `drive_verified=false`. A causa exige teste controlado.
- **P2, replay de alta resolução — 24/11 (INCONCLUSIVO):** o mesmo fixture candidato SS de 370 ns foi reexecutado com PEX, modelo, estímulos e guard de 1,5 ns preservados; passo máximo nativo de 10 ps e somente vetores de observação necessários. ngspice 44.2 terminou com código 0; 38.241 amostras, passo máximo observado 10,000 ps. Sete lanes atendem ao witness de 50 ps; o bit6 não. A região contínua interpolada do bit6 é 51,677 ps (246,948323–247 ns), mas o primeiro ponto nativo é 246,954950 ns, deixando apenas 45,050 ps conservadores até a borda de controle. Release passa nas oito lanes até 247,655195 ns. Isso mostra uma janela de drive extremamente curta, sem qualificar o gate; P2 permanece aberto e nenhuma regra foi relaxada. O replay, deck, log e onda estão preservados em `phase3_evidence_20261124/build/phase3/diagnostics/c12_highres_candidate_ss_20261124/`.
- **P3, replay integrado FF — 24/11 (PARCIAL):** o fixture candidato virtual de 18 ciclos completou 370 ns em ngspice 44.2 sobre o envelope RC da PEX v6 `a1e812…`; todas as 18 operações funcionais passam. O observer de ownership continua `INCONCLUSIVO` em c2 (`write`) e c10 (`read_to_write`); c12 `read_to_idle` passa em FF. O runner legado recusou a preparação antes de simular porque está preso a outro PEX (`12c41…`); a execução direta e a análise vinculadas à PEX correta estão documentadas no manifesto. Evidência em `phase3_evidence_20261124/build/phase3/diagnostics/strongarm_eight_integrated_ff_20261124/`. Isso não fecha P3 entre corners nem a qualificação elétrica.
- **Limite do ambiente na auditoria inicial:** a busca direta do executável não encontrou `ngspice` no PATH então configurado. Nesta retomada, o launcher adicionou `/opt/*/bin`, validou o container/PDK e encontrou ngspice 44.2. Não foram iniciadas novas simulações SPICE; os resultados prévios continuam reanálises dos waveforms preservados.

### Auditoria offline inicial — 24/11

- **Auditoria offline concluída antes da recuperação EDA:** branch confirmada em `integration/phase3-danilo-ss`, HEAD `4395e2ae`, quatro commits locais à frente de `origin/integration/phase3-danilo-ss`, worktree limpo antes destas atualizações de documentação. `memory/memory-ip/knowledge.md` não existe. No host há Python 3.12.3, sem executáveis EDA no PATH.
- **Recuperação do simulador concluída sem reinstalação:** a inspeção encontrou `sram-xschem` parado, imagem `isaiassh/unic-cass-tools:1.1.0` e montagem correta deste checkout em `/work`. `./tools/sram-eda --check` iniciou o container e passou: ngspice 44.2, Magic 8.3.613, Netgen 1.5.293, Icarus 13.0, Yosys 0.44, OpenROAD, Xschem, Python com gdstk 0.9.62/NumPy 1.26.4 e arquivos SKY130A requeridos presentes. O container permanece iniciado. Naquele ponto da auditoria não houve simulação; os replays SS de alta resolução e FF descritos acima foram executados depois. KLayout/OpenSTA não foram incluídos no check e não estão confirmados.
- **Próxima recuperação/uso:** executar comandos EDA pelo `./tools/sram-eda`, que valida o bind mount, configura `PDK_ROOT=/opt/pdks`, `PDK=sky130A` e injeta `/opt/*/bin` no PATH. Não há justificativa para reconstruir a imagem nem instalar ngspice paralelo. Antes de simular, preparar fixture controlada, confirmar probes/estímulos e reservar diretório de saída rastreável.
- **SNM reutilizável apenas como evidência provisória:** snapshot contém campanhas `nominal-proposed`, 1,8 V/27 °C. Hold: 200/220 amostras, 20 não executadas, 0 inválidas. Read: 200/220, 14 não executadas e 6 inválidas entre 206 tentativas. Os resumos marcam `PROVISIONAL`; a temperatura nominal ainda requer confirmação pelos orientadores na especificação. Isso permite revisar método, seeds, tentativas inválidas e estatística sem simulador, mas não fecha SNM da geometria final nem outras condições/cantos. Caminhos: `build/phase3/snm_campaign_results_20261120/{hold,read}/summary.json` e `build/phase3/snm_endpoints_final_20261120/audit.json` dentro do snapshot.
- **Liberty existente não é final:** `build/phase3/danilo_ss_ff2_spaced_route/macro_interface.lib` declara `phase2_uncharacterized_interface` e contém interface/pinos sem tabelas de timing/potência. Pode servir para auditoria estática de nomes/unidades; não satisfaz P9 e não deve ser promovida. O contrato `docs/phase3_characterization_contract.md` confirma que falta implementar gerador `.lib`, lookup tables, sweeps de setup/hold, extração de waveform e validação sintática/contra SPICE.
- **Dimensões:** a especificação §§20–21 exige caracterização pelo menos em 8×8 e 32×8 e prevê geração nas profundidades 4/8/16/32. O handoff confirma geração física, DRC/LVS/PEX e caracterização de 8×8/32×8 pendentes. A aceitação de nomes de configuração pelo contrato/infraestrutura não representa existência de circuitos físicos. Para fechar integralmente, gerar as duas dimensões, validar vistas/DRC/LVS/PEX e caracterizar o escopo exigido; alternativa é obter e registrar alteração formal de escopo. Nenhuma exceção foi aprovada.
- **Pode avançar sem simulador:** revisar requisitos e domínio elétrico pendente; auditar manifests/hashes e cobertura dos dados preservados; revisar seeds/invalids SNM e fazer análise estatística offline; auditar interface e preparar/testar estaticamente o gerador Liberty sem publicar valores; preparar o fixture e critérios/controles negativos do teste c12. Essas ações não aprovam ownership, desempenho, SNM final ou Liberty.
- **Dependências não concluídas:** revisar com a equipe se o protocolo/intervalo pode oferecer witness conservador ≥50 ps e executar teste controlado correspondente; não reduzir o piso. Depois, fechar comparação virtual e selecionar formalmente arquitetura; fechar geometria final e PEX; repetir C250/integrado TT/SS/FF no PEX escolhido; caracterizar acesso, tDIS, setup/hold e potência/energia; completar/homologar SNM; gerar e validar Liberty; gerar/qualificar 8×8 e 32×8 ou aprovar formalmente mudança de escopo; revisão cruzada e pacote reproduzível. O container/PDK está validado, mas P2 segue inconclusivo e `signoff_achieved=false`.

## 1. Conclusão da análise

A Fase 3 está em fechamento funcional experimental. A infraestrutura, a recuperação dos checkpoints e uma macro física v6 estão disponíveis. A comparação virtual de oito StrongARM passou C250 nos três corners; em FF, o replay integrado passa funcionalmente nas 18 operações, mas dois eventos de ownership permanecem inconclusivos. Em SS, c12/bit6 ainda não alcança o witness conservador. Ainda faltam aceite integrado completo entre corners, escolha e congelamento da geometria final, caracterização elétrica, SNM homologado, Liberty validada e entrega reproduzível.

Oito StrongARM virtuais não constituem oito células físicas extraídas: cinco núcleos e seus buffers foram acrescentados sobre as rotas RC da v6. Portanto os resultados não autorizam transferir timing, potência ou DRC/LVS da v6 para uma nova geometria.

## 2. Fontes, alcance e inventário

Foram confrontados a especificação técnica (§§19–21), o plano operacional da Fase 3, o contrato de caracterização, o handoff de 22/11, a auditoria de oito StrongARM, os scripts novos e os recibos/análises TT/SS/baseline. O snapshot P0 e os replays de análise TT/SS foram verificados; não foram feitas novas simulações SPICE, DRC/LVS ou campanhas SNM.

Fontes versionadas:

- [Especificação técnica](../specs/technical_specification.md).
- [Plano original e responsabilidades atualizadas em 13/11](phase3_plan_to_20261123.md).
- [Contrato de caracterização](phase3_characterization_contract.md).
- [Contrato temporal](../specs/sram_4x8_timing_contract.md).
- [Handoff técnico e matriz de 22 requisitos](phase3_handoff_equipe_20261122.md).
- [Guia de recuperação](phase3_transfer_quickstart.md).
- [Auditoria experimental recente](phase3_auditoria_virtual_oito_strongarm_20261123.md).

Os dados originais continuam em `/tmp/phase3-v6-handoff-20261122/historical-checkout/build/phase3/` e sua cópia persistente, validada por manifesto, está em `/home/danilo_cunha/projetos/ueletronica/phase3_evidence_20261124/build/phase3/`. Os três commits publicados contêm sete fontes/documentos, não os waveforms novos.

| Frente | Evidência disponível | Limite ou pendência |
|---|---|---|
| Infraestrutura | Runner, contratos, validação nominal histórica e recibos | PASS de infraestrutura não qualifica a SRAM pós-layout |
| Histórico A/B/B′/C | Diagnósticos RC, clock, sense, barramento e SNM documentados | Não combinar métricas de variantes diferentes numa caracterização final |
| v6 física: 3 StrongARM | Handoff registra DRC=0, LVS único, PEX selado e C250 TT/SS/FF PASS | Regressão completa da geometria escolhida ainda necessária |
| Oito StrongARM virtuais, C250 | TT/SS/FF: qualification PASS | TT válido está em `strongarm_eight_virtual_20261123_retry1_analysis/TT`; o `retry1/TT` original contém análise inconclusiva. Preservar a ligação entre onda original e mapa corrigido |
| Integrado virtual TT | Reanálise derivada: topologia 72/72 StrongARM PEX; recibo 370 ns/319 hashes; dados 18/18 | Observer bruto INCONCLUSIVO no write c2, bits 4/7; suplemento externo é diagnóstico, não ownership/signoff |
| Integrado virtual SS | Reanálise derivada: topologia 72/72 StrongARM PEX; recibo 370 ns/319 hashes; dados 18/18 | INCONCLUSIVO no read→idle c12, bit 6; drive witness ausente |
| Controle v6 integrado SS | Topologia derivada passou: 27 StrongARM PEX + 45 nativos; recibo e cobertura PASS | Observer bruto ainda INCONCLUSIVO em c12/bit 6; a classificação de topologia não fecha ownership |
| Integrado virtual FF | Replay diagnóstico concluído em PEX identificado; waveform e manifestos verificados | Funcional 18/18 PASS; ownership inconclusivo em c2 write e c10 read→write; c12 passa apenas em FF. Não fecha o gate comparável TT/SS/FF nem signoff |
| Timing e potência finais | Medidas exploratórias/históricas em C e margens internas | Setup, hold, acesso, desabilitação, energia, leakage e domínio final não homologados |
| SNM | Handoff registra hold 200 e read 206, experimentais | Homologar método, seeds, variação global/local, domínio e escopo físico |
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
| P2 — Resolver ownership | **INCONCLUSIVO / aguardando revisão do protocolo:** replay candidato SS a 10 ps confirmou release e sete lanes; bit6 tem região interpolada de 51,677 ps, mas witness conservador nativo de 45,050 ps | André + Danilo; revisão Leonardo | P1 | Revisar metodologia/intervalo e rodar contraste controlado com critério pré-aprovado; manter piso de 50 ps; não inferir PASS |
| P3 — Completar comparação virtual | **PARCIAL:** FF integrado passa nas 18 operações funcionais; ownership inconclusivo em c2 write e c10 read→write. SS c12 continua inconclusivo; concluir gates e comparar com v6 no mesmo protocolo | Danilo | P2 | Nove palavras/72 bits, seis escritas com readback, quatro linhas, retenção e ownership aprovados em TT/SS/FF sobre PEX identificada |
| P4 — Escolher arquitetura | Registrar decisão v6 híbrida versus oito StrongARM, custos físicos, carga/clock, margens, risco e fallback | Equipe; André e Danilo apresentam evidências | P3 | Variante escolhida e escopo aprovados; nenhuma seleção automática baseada só no C250 |
| P5 — Fechar geometria | Se oito: gerar cinco novas células/rotas, revisar clock/rails, obter GDS/LEF/netlist, DRC/LVS/PEX. Se v6: validar identidade da geometria já qualificada | Danilo + André; integração Leonardo | P4 | DRC zero, LVS único com parâmetros, PEX distribuído auditado e vistas coerentes por hash |
| P6 — Qualificar candidata física | Repetir C250 e integrado completo com PEX final e grade funcional aprovada; revisar modelo Verilog/protocolo | Danilo + André | P5 | Aceite funcional e ownership completos da mesma geometria em todo domínio declarado |
| P7 — Caracterizar eletricamente | Gerar tabelas de acesso, clock→DATA quando aplicável, tDIS/Hi-Z, setup/hold, energia e potência estática/dinâmica | Danilo; revisão André | P6 + domínio congelado | Matrizes rastreáveis por PVT/slew/carga, limites e unidades claros, nenhuma célula inválida convertida em número |
| P8 — Homologar SNM | Revisar VTCs e extração hold/read; seeds, modelos, N≥200 conforme escopo, estatística e amostras inválidas; complementar se necessário | Ícaro; revisão Danilo | Método pode andar em paralelo; domínio final depende P4–P6 | Método e resultados aprovados; distinguir mismatch, processo, pre-layout e pós-layout; não inferir yield da macro |
| P9 — Gerar e validar Liberty | Consumir tabelas aprovadas, gerar arcos condicionais e tri-state, constraints e potência; validar leitura e comparar pontos com SPICE | Leonardo; revisão Ícaro/Danilo | P7 e domínio aprovado | Biblioteca reproduzível, unidades/pinos/arcos corretos e concordância em tolerância definida antes da comparação |
| P10 — Entregar e revisar | Relatório final, vistas, dados, release e reprodução independente | Leonardo + equipe | P6–P9 e decisão de dimensões | Revisão cruzada registrada, pacote recuperável por outro membro e requisitos completos ou exceções explicitamente aprovadas |

Caminho crítico: P0 → P1 → P2 → P3 → P4 → P5 → P6 → P7 → P9 → P10. Auditoria SNM, definição do domínio e preparação do gerador Liberty podem avançar em paralelo; números finais dependem da geometria selecionada.

## 5. Trabalho imediato para o bloqueio de ownership

1. **Concluído:** reprocessar ondas existentes e verificar hashes/cobertura antes do novo transiente.
2. **Concluído:** replay candidato SS completo, com PEX, estímulos e guard preservados e passo máximo de 10 ps. O waveform e os manifests foram verificados e arquivados.
3. **Concluído:** o observer inalterado aplicou 50 ps e três amostras nativas. Sete lanes passam, a release passa em todas e o bit6 permanece inconclusivo.
4. **Resultado:** no bit6 a região elétrica interpolada satisfaz os limiares por 51,677 ps, mas o primeiro ponto nativo deixa 45,050 ps conservadores antes da borda de 247 ns. Em 247 ns, DATA6=1,488 V, TE_B=0,0878 V, corrente do probe weak=+312,3 µA e corrente DUT=−372,9 µA. Há condução concorrente no fim da janela; o observer não a aprova como witness mínimo. A onda não permite concluir se o intervalo prático atende ao protocolo sem revisão da regra/temporização.
5. **Próximo passo dependente de revisão:** acordar um intervalo de witness/protocolo que preserve o piso conservador de 50 ps, então executar contraste controlado e comparar baseline/candidato se necessário. Não alterar o critério depois de ver o resultado e não usar atraso artificial como prova de conformidade do fixture original.
6. Incluir/confirmar controles negativos: contenção deliberada e driver sem condução devem reprovar; nenhuma redução de limiar deve ser escolhida apenas para obter PASS.
7. Homologar a regra de TT para payload estático, preservando o resultado bruto e justificando todas as condições de aplicação. Repetir o integrado com critérios aprovados antes do aceite final.

## 6. Domínio elétrico e critérios de caracterização

Antes das matrizes, registrar valores numéricos aprovados para tensão, temperatura, slew, carga, período/duty, guardas, limiares, estado inicial e tolerâncias. As cargas 5/10/20 fF são propostas históricas; não tratar uma proposta como domínio homologado. Respeitar os limites do PDK e os contratos de pinos.

- Acesso: da borda pública contratada até a palavra nova inteira correta e estável. Releituras sem transição não fornecem atraso zero.
- tDIS: medir liberação sustentada por CSb/OEb/WEb e polaridade, com witness de Hi-Z.
- Setup/hold: buscar fronteiras por entrada capturada e operação; conferir armazenamento/readback e ownership, não só um nó interno. Refinar a fronteira com tolerância definida.
- Potência estática: clock parado, estado conhecido, repouso suficiente e fonte explicitada.
- Energia/dinâmica: integrar V×I em janelas de operação comparáveis, declarar contribuição de clock/pré-carga/carga e tratar leakage separadamente.
- SNM: método e população adequados ao requisito; conservar seeds ruins e falhas de extração, sem seleção das amostras favoráveis.
- Liberty: usar apenas a geometria e o domínio qualificados; validar semântica da memória e barramento bidirecional, condicionamento dos arcos, interpolação e coerência com o modelo funcional.

## 7. Dimensões e definição de encerramento

A especificação exige resultados pelo menos em 8×8 e 32×8, embora o cronograma original coloque sua geração na Fase 4. Há duas entregas possíveis, que não devem receber o mesmo status:

- **Fechamento técnico do 4×8:** todos os gates da geometria 4×8, relatório, SNM no escopo aprovado e Liberty. Continua entrega parcial frente ao requisito dimensional integral, salvo revisão formal de escopo.
- **Fechamento integral da Fase 3:** além do 4×8 de referência, disponibilizar e caracterizar as configurações exigidas com vistas e evidências próprias, ou registrar uma alteração formal do requisito pelos responsáveis.

Não extrapolar tabelas do 4×8 para outras profundidades: BL/WL, decoder, RC, potência e margens mudam. A decisão de antecipar essas configurações ou completar a entrega na Fase 4 precisa constar do plano aceito.

## 8. Orçamento e organização das próximas rodadas

As três execuções integradas recentes levaram aproximadamente 27,8–29,5 minutos por corner neste ambiente, sem contar preparação/análise. Reservar cerca de 1,5 hora de simulação serial para três runs de 370 ns comparáveis; isso não estima setup/hold, Monte Carlo ou nova extração física.

Usar `workers=1` inicialmente e estimar a grade após piloto: número de variantes × corners × tensões × temperaturas × slews × cargas × estímulos × repetições. Registrar timeout e custo por ponto. Não é responsável fixar uma data final antes de resolver ownership, arquitetura e dimensões.

Primeira rodada: P0, P1 e diagnóstico de P2 com ondas existentes. Segunda: experimento mínimo que discrimine a causa e regressões necessárias. Terceira: decisão arquitetural e cronograma de geometria/caracterização baseado no throughput medido.

## 9. Checklist de encerramento

- [ ] Escopo dimensional, domínio elétrico e arquitetura formalizados.
- [ ] Fontes, ferramentas, modelos e artefatos preservados com manifesto recuperável.
- [ ] Observadores auditados, cobertura completa e controles negativos aprovados.
- [ ] Geometria final com DRC/LVS/PEX e vistas consistentes.
- [ ] C250 e integrado TT/SS/FF aprovados no domínio declarado, incluindo ownership.
- [ ] Timing, setup/hold, tDIS, potência/energia medidos e revisados.
- [ ] SNM e Monte Carlo homologados com N e escopo exigidos.
- [ ] Liberty gerada de dados reais e validada contra SPICE/ferramentas consumidoras.
- [ ] 8×8/32×8 atendidos ou alteração formal de requisito registrada.
- [ ] Reprodução independente, revisão cruzada e entrega final aprovada.

Estado atual: nenhum PASS experimental isolado autoriza marcar essa lista completa. `electrical_qualification=NOT_CHARACTERIZED` permanece até a evidência correspondente ser produzida e aprovada.
