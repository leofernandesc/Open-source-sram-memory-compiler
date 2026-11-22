# Marco 3 · Entrega técnica parcial da SRAM 4×8

**Corte de evidências** 21/11/2026 · **Apresentação planejada** 23/11/2026  
**Entrega** `PARTIAL_DELIVERY_READY` · **Qualificação elétrica da macro** `NOT_CHARACTERIZED`  
**Referência de integração** Geometria C · `integration/phase3-danilo-ss` · `8e1d961d65054b59f9032ed5f9338d9ee4353c33`

## Parte A — Resumo executivo

O Marco 3 exige extração de parasitas, caracterização elétrica nos três corners e um relatório acompanhado de Liberty gerada a partir das medições. A entrega de 23/11 documenta o avanço da SRAM síncrona de quatro palavras de oito bits e explicita os requisitos ainda abertos. O circuito implementado tem 32 células 6T, seleção de quatro linhas, oito pares de bitlines, pré-carga e equalização por coluna, escrita, sense regenerativo e registradores. C conserva o tap 48 para antecipar a avaliação de linha, o acionamento de sense via tap 80, a captura associada à descida do CLK público e a interface DATA bidirecional. [Proposta, pp. 4–6](../proposta/Proposta_Adaptada_Memory_Compiler_OpenSource_09092026.pdf) · [Especificação, §§17–20](../specs/technical_specification.md)

- **Físico.** GDS, LEF e PEX distribuído estão vinculados à mesma geometria por SHA-256. Os recibos históricos registram DRC com zero marcadores e LVS com correspondência única de 1.749 MOS. Esta rodada conferiu os recibos e os arquivos.
- **SS integrado.** Nove de nove leituras com palavras corretas, seis de seis escritas confirmadas por readback e cobertura das quatro linhas. A revisão de propriedade concluiu 18 de 18 PASS, com o resultado histórico de 15 PASS e três inconclusivos preservado.
- **TT integrado.** Sete de nove leituras corretas e cinco de seis escritas confirmadas por readback. A linha 3 retornou `0xF8` em vez de `0xF0` nos ciclos 16 e 17. O ensaio com sondas adicionais confirmou bitcell correta, inversão da decisão no sense 3 e propagação por D, Q e DATA3. **FF integrado de C segue pendente.**
- **SNM experimental.** Na bitcell 6T esquemática, em `tt_mm`, 1,8 V e 27 °C, Hold teve 200 amostras válidas, média de **684,740 mV** e desvio-padrão de **8,473 mV**. Read teve 206 amostras válidas, média de **409,756 mV** e desvio-padrão de **10,761 mV**. A revisão reproduziu o resultado por seed a partir das curvas arquivadas. A homologação do domínio estatístico segue aberta.
- **Correção experimental.** O atraso conjunto de cerca de 182 ps corrigiu a regeneração no recorte do sense 3. O driver local SKY130 v2 também corrigiu c16/c17 nesse recorte, com risco de integração ligado a slew, corrente e impedâncias compartilhadas. O preflight de integração ficou em `COMPACT_BOUNDARY_PARTIALLY_DEFINED`. O GDS de C segue como referência física, com o FAIL em TT.

**O que falta para concluir.** Resolver o FAIL de TT, validar FF em condições comparáveis, qualificar temporização e potência em função de PVT, slew e carga, e gerar e validar a Liberty a partir desses dados. A caracterização pós-layout de 8×8 e 32×8 depende de suas vistas físicas verificadas. A proposta já prevê a geração dessas configurações na Fase 4. O calendário para complementar a caracterização e o domínio de SNM precisam de decisão registrada com os orientadores. [Contrato de caracterização](phase3_characterization_contract.md) · [Plano para o Marco 3](phase3_plan_to_20261123.md)

**Para 22 e 23/11.** Em 22/11, revisar a matriz, reproduzir a conferência de evidência e fechar as perguntas de escopo e SNM para os orientadores. Em 23/11, apresentar a entrega parcial com a demonstração TT/SS e registrar as decisões de calendário, temperatura e domínio estatístico. Deixar FF para a próxima rodada com meta de cobertura explícita e orçamento reservado. O custo histórico de um corner de C ficou em cerca de 36–41 min, além da análise, e o resultado de FF não resolveria o bloqueio funcional já comprovado em TT.

## Parte B — Evidência técnica

### B1. Requisitos e decisão

A proposta oficial (itens 14–17 e §5) é a referência para o cronograma e os entregáveis. A especificação (§§17–20) delimita arquitetura, vistas, verificação e caracterização. Os contratos distinguem funcionamento, metodologia de medição e prazos públicos. `COMPLETE` vale para o escopo escrito na linha. `PARTIAL` indica cobertura relevante ainda insuficiente, `FAIL` uma violação demonstrada, `NOT_RUN` um ensaio ausente e `NEEDS_DECISION` uma condição a formalizar.

| ID | Requisito | Evidência localizada | Verificação realizada | Situação | Pendência |
| --- | --- | --- | --- | --- | --- |
| M03-01 | Macro 4×8 com vistas físicas e verificação de C, especificação §§17–19 | E02 | Hashes de GDS, LEF, netlists e logs ligados aos recibos históricos de C | COMPLETE | Repetir a verificação para qualquer geometria futura |
| M03-02 | Extração RC da macro 4×8, proposta item 14 | E02, E03 | Hash do PEX distribuído, recibo do GDS e associação aos decks TT/SS | COMPLETE | Extrair 8×8/32×8 após vistas físicas verificadas |
| M03-03 | Funcionamento integrado de C em SS no escopo ensaiado | E03, E04 | Conferidos 9/9, 6/6, quatro linhas e 18/18 no observador revisado | COMPLETE | Cobertura elétrica e de estímulos ampliada |
| M03-04 | Funcionamento integrado de C em TT | E03, E04, E05 | Conferidos c16/c17 com 0xF8 em vez de 0xF0, erro na regeneração | FAIL | Corrigir e validar C novamente com sequência integrada |
| M03-05 | Funcionamento integrado de C em FF, mesma geometria e fixture | E03, E07 | Inventário de cobertura separou as geometrias históricas | NOT_RUN | Obter execução FF comparável de C |
| M03-06 | Tempo de acesso, proposta item 15 e contrato de caracterização | E03, E06 | Intervalos de palavras completas estáveis e transições por bit extraídos dos recibos | PARTIAL | TT funcional, FF e dependência de carga, slew e PVT |
| M03-07 | tDIS e entrega de DATA conforme contrato de interface | E04, E06 | Três controles com sonda de corrente em SS, guarda integrada e vereditos por ciclo | PARTIAL | Limites públicos, complementos, corners e carga |
| M03-08 | Setup e hold, proposta item 15 | E01, E06 | Conferida a definição e a falta de medidas qualificáveis | NOT_RUN | Varrer fronteiras de entrada e critérios de violação nos corners |
| M03-09 | Potência estática, proposta item 15 | E06 | Separado idle com clock de janela estática | NOT_RUN | Medir clock parado, estado armazenado conhecido e PVT |
| M03-10 | Potência dinâmica, proposta item 15 | E06 | Identificadas integrais exploratórias em janelas ativas SS | PARTIAL | Coletar pares ativo/idle comparáveis e qualificar carga, slew e PVT |
| M03-11 | SNM Monte Carlo com pelo menos 200 amostras por modo no domínio experimental | E08 | Reprocessadas VTCs, contadas 406 seeds distintas, conferidas seis recuperações e estatísticas | COMPLETE | Alcance restrito à bitcell esquemática e às condições experimentais |
| M03-12 | SNM no domínio requerido e temperatura nominal de caracterização | E01, E08 | Comparadas configuração da campanha, exclusão de dispersão global e especificação §20 | NEEDS_DECISION | Homologar domínio, temperatura, alcance pós-layout e uso dos dados |
| M03-13 | Relatório de caracterização de 8×8 e 32×8, proposta §5 e especificação §20 | E01, E07 | Conferidos requisito e cronograma das vistas na Fase 4, sem dados elétricos pós-layout comparáveis no pacote | NOT_RUN | Gerar e verificar as duas geometrias e caracterizá-las |
| M03-14 | Calendário de 8×8/32×8 e contingência de escopo | E01 | Identificada a dependência da Fase 4 e a ausência de autorização registrada no conjunto auditado | NEEDS_DECISION | Acordar e registrar a data de complementação com orientadores |
| M03-15 | Liberty simplificada e validada, proposta item 17 | E01, E06 | Conferidos contrato, biblioteca de interface histórica e falta de dados qualificados para uma biblioteca de C | NOT_RUN | Gerar e verificar .lib somente a partir de medições qualificadas |
| M03-16 | Relatório do Marco 3, proposta pp. 4–5 | E01–E10 | Consolidação, matriz, índice e hashes reproduzíveis | PARTIAL | Completar o relatório de caracterização e a Liberty após os requisitos elétricos |

M03-04 impede qualificar C em TT. M03-05, M03-08, M03-09, M03-13 e M03-15 seguem sem evidência de execução no escopo exigido. M03-12 e M03-14 dependem de decisão. Os resultados físicos, funcionais e experimentais rastreáveis sustentam `PARTIAL_DELIVERY_READY`.

### B2. Identidade física e histórico

| Versão | Relação física e cobertura disponível |
| --- | --- |
| A · 4×8 pré-ECO | Referência congelada em `release/phase2_current.json`. Há homologação nominal em outra condição e diagnóstico histórico 32/72 em janela com RC. A auditoria também encontrou falhas reais em sense/D/Q sob modelos com trilhos ideais. O waveform integral daquela contagem não está no acervo auditado para reclassificação completa. |
| B · primeiro ECO de Danilo | O commit `42f0b5128d7e5dde4385731e85fa504a6ee005a7` registra tap 48, captura vinculada ao CLK público e saída `ebufn_8`. As referências históricas TT/SS/FF pertencem a B. O conjunto original de vistas e waveforms não foi recuperado na auditoria. |
| B′ · reconstrução | Rota, GDS e PEX próprios, registradores `dfxtp_1`. Os testes de 170 ns avaliavam c6/c7. O contraste TT de 250 ns parou em 85,8258 ns, antes das escritas e leituras discriminantes. B′ segue inconclusivo para c16/c17. |
| C · referência atual | Rota `distributed-spaced`, saída `ebufn_8`, registradores `dfxtp_2`, captura pública via `clkinv_1`. PEX selado, TT e SS integrados de 370 ns. |
| Driver local v2 | Inversor CMOS de entrada assimétrico e restaurador `sky130_fd_sc_hd__inv_2` no ramo R87, em netlist experimental de 59 ns. Escopo separado da macro C. |

A comparação histórica tem coberturas diferentes. A auditoria mostrou benefício do tap 48 na ordem WL→sense nos ensaios diagnósticos. A causa de qualquer diferença entre B′ e C permanece sem discriminação experimental. [Auditoria arquitetural](phase3_auditoria_comparativa_arquitetura_4x8_20261120.md) · [Encerramento do contraste B′ × C](phase3_desempenho_ngspice_resultados_parciais_20261121.md)

| Vista de C | Identidade e recebimento histórico |
| --- | --- |
| GDSII | `b610c30b563c5830900792440e4f4295777029cfd9ab4496072f7d22fdab3365`. GDS final vinculado ao netlist de referência e aos logs Magic/Netgen de E02. DRC zero e LVS único com W/L, bulk e modelo. |
| LEF | `1b5250a4a1726a9e14b21d6ea5de8884c60f7750a10e20c8537cb6e4bac63091`. O recibo vincula o GDS ao LEF de 540 × 380 µm com 16 pinos públicos. |
| SPICE pós-layout | `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a`. PEX RC distribuído, 1.749 MOS, 16.187 R, 12.371 cartões C, dos quais 10.342 positivos. Manifesto vincula o mesmo GDS e recibo. |
| Netlists e modelos digitais | `routed.v` e `final.v` vinculados aos recibos de rota/layout. `reference_mos.spice` é a referência LVS e `final_extracted.spice` é o extraído de conectividade empregado na verificação física. A simulação usa o PEX RC e o binding sondado. O modelo comportamental da interface tem escopo lógico próprio. |

### B3. Funcional integrado

TT e SS usaram o mesmo GDS, PEX, binding, fabric, fixture e manifesto de modelos. Os decks diferem somente na seleção `.lib` SKY130A. Condições arquivadas de 1,8 V, 27 °C, 20 ns de período, 50 ps de slew aplicado, 10 fF por DATA, passo máximo de 25 ps e 370 ns de horizonte. Os ensaios históricos terminaram normalmente, com 20.539 amostras em SS e 22.730 em TT. A fixture aplica uma guarda de 1,5 ns. O protocolo exige liberação efetiva da SRAM antes do acionamento forte pelo host. [Contrato temporal §6](../specs/sram_4x8_timing_contract.md#6-troca-de-direção-do-barramento) · [Validação integrada](phase3_validacao_integrada_ss_20261119.md)

| Indicador de C | TT | SS | FF |
| --- | --- | --- | --- |
| Leituras de palavra completa | 7/9 | 9/9 | Pendente |
| Escritas confirmadas por readback | 5/6. Escrita c5 sem confirmação integrada por leitura divergente | 6/6, linhas 0–3 | Pendente |
| Palavras c15 / c16 / c17 | 0x0F / 0xF8 / 0xF8 | 0x0F / 0xF0 / 0xF0 | Pendente |
| Propriedade, observador original | 16 PASS / 2 INCONCLUSIVO | 15 PASS / 3 INCONCLUSIVO | Pendente |
| Propriedade, revisão offline | 15 PASS / 3 INCONCLUSIVO, c2/c16/c17 | 18 PASS / 0 INCONCLUSIVO | Pendente |
| Janela diagnóstica histórica ±100 ps | 70/72 bits PASS, dois FAIL de DATA3 | 65/72 bits PASS, sete FAIL de DATA7, c6/c7/c11/c13/c14/c15/c16 | Pendente |
| Veredito funcional | FAIL | PASS no escopo ensaiado | NOT_RUN |

Em SS, a revisão recuperou c8/c10/c12 usando testes de condução e liberação sob sonda de 1 kΩ, correlação de corrente, tensão e enable, três amostras nativas e testemunho mínimo de 50 ps. A revisão separa corrente de deslocamento e oposição entre drivers. A guarda de 300 ps produziu contenção no ensaio de estresse. Em SS, todas as palavras completas permaneceram válidas no escopo. Os sete FAILs de DATA7 pertencem à janela diagnóstica de ±100 ps. O prazo público segue em aberto. Em TT, a incerteza de propriedade em três ciclos é separada do erro de leitura comprovado. [Revisão SS e controle de estresse](phase3_fechamento_barramento_ss_20261120.md) · [Dados TT/SS e vereditos E03/E04 no índice](../indice_evidencias.csv)

O TT reduzido de 250 ns com o mesmo PEX verificou Q/QB da célula da linha 3, bit 3, durante escrita e retenção. Q ficou entre −0,007 e 0,147 V e QB entre 1,772 e 1,832 V no intervalo observado. BLB−BL permaneceu positivo durante a inversão do latch. A polaridade incorreta estabilizou em D antes da captura e apareceu em Q e DATA3. Isso sustenta a localização em regeneração, sem evidência de corrupção da célula no ensaio. Os instantes do ensaio reduzido têm sequência própria. [Diagnóstico de DATA3](phase3_data3_tt_snm_piloto_20261120.md) · [Auditoria temporal TT × SS](phase3_auditoria_temporal_tt_ss_20261121.md)

### B4. Temporização, potência e Liberty

| Grandeza | Medida disponível | Alcance e pendência |
| --- | --- | --- |
| tACCESS | SS 10,875–10,911 ns em sete novas palavras. TT 10,589–10,617 ns em seis novas palavras corretas. | Medido de CLK público ↑50% até a nova palavra de oito bits válida e estável. Releituras sem mudança ficam separadas. Os dois reads TT errados não fornecem tACCESS válido. |
| tCLK_TO_DATA | Por bit em transição, SS 765–841 ps, 48 medições. TT 510–565 ps, 40 medições em reads corretos. | CLK público ↓50% até DATA50% do bit. A validade da palavra após a captura é tREAD_VALID e depende de todos os bits. Uma transição isolada não fornece tACCESS. |
| tDIS | SS, 24 observações bit×controle. Mais tardio observado para WEb↓ 1.067,5 ps, OEb↑ 888,2 ps, CSb↑ 881,6 ps. | Sonda 1 kΩ, palavra anterior 0xAA, critério conjunto de tensão, corrente ≤50 µA e estabilidade. Máximo público, fuga, polaridades e variação de carga/corner seguem pendentes. |
| Setup / hold | Sem curva qualificada da macro. | Variar entradas em torno da captura sob critérios do contrato, por PVT e slew. Tempos de estabilidade observados em D não medem setup/hold do pino. |
| Potência estática | SS com clock ativo em idle, 0,148–0,195 mW. | P_STATIC com clock parado e estado conhecido segue ausente. |
| Dinâmica | SS exploratório, 14,58–15,13 pJ/leitura e 10,71–11,51 pJ/escrita, em janelas de 20 ns. | Integrais da fonte incluem leakage e pré-carga. Faltam janelas comparáveis, baseline e caracterização por PVT, atividade e slew/carga. |
| PVT, slew e carga | TT/SS comparáveis em uma configuração de fixture. Sensibilidade diagnóstica de tACCESS de cerca de 27/44 ps em duas transições com outro perfil de PEX. | Cobertura de FF, ampliação de pontos, validade de caracterização elétrica e tolerâncias finais em aberto. |
| Liberty | Contrato e infraestrutura de análise com biblioteca de interface de roteamento `phase2_uncharacterized_interface`. | Liberty simplificada de C, com arcos, setup/hold, condições de direção e potência medidos, ainda ausente. Gerar e validar somente após fechamento elétrico. |

As métricas diagnósticas documentam o ponto ensaiado. Nenhuma está qualificada como limite público de C. [Contrato de caracterização](phase3_characterization_contract.md) · [Caracterização mínima SS](phase3_caracterizacao_minima_20261119.md)

### B5. Monte Carlo SNM

| Modo | Válidas originais / auditadas | Média (mV) | DP amostral (mV) | Mediana (mV) | Mín.–máx. (mV) | IC 95% da média (mV) |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| Hold | 200 / 200 | 684,740 | 8,473 | 685,271 | 655,439–701,742 | 683,568–685,909 |
| Read | 200 / 206 | 409,756 | 10,761 | 410,356 | 381,598–439,523 | 408,335–411,224 |

A bancada é a bitcell 6T **esquemática**, com BL/BLB em VDD e WL desativada em Hold e ativada em Read. A seção `tt_mm` usa parâmetros TT, mismatch local habilitado e variação de processo global desabilitada. Cada curva DC tem 1.801 pontos com passo de 1 mV. A SNM é o menor lado entre os maiores quadrados nos dois lóbulos da butterfly. O IC bootstrap corresponde à média amostral no domínio investigado. Uso como yield, tolerância física do modelo ou qualificação da macro exigiria evidência adicional.

As seeds Read 30005, 30021, 30053, 30090, 30148 e 30192 tinham sido rejeitadas por ambiguidade nos sinais de extremidade. A auditoria offline certificou três interseções dos interpolantes sob quantização do arquivo, preservou a rejeição original nos recibos e recuperou os valores individuais de 391,725 mV, 394,360 mV, 402,501 mV, 395,208 mV, 411,337 mV e 422,489 mV, na ordem das seeds. O replay das 406 curvas arquivadas gerou um `audit.json` idêntico byte a byte e a consolidação confirmou seeds distintas, média e desvio-padrão. A publicação preserva as 200 Read originalmente válidas e suas estatísticas, 409,961 mV e 10,690 mV. As 206 válidas satisfazem a contagem experimental por modo. [Método, recibos e limites](phase3_sclk_preflight_auditoria_snm_20261120.md)

### B6. Driver experimental, decisões e cronograma

A auditoria causal no recorte sustenta a temporização coordenada dos samplers com o tail. Atrasar só o tail preservou a decisão errada mesmo com BLB−BL maior no início da condução. O v2 corrigiu c16/c17 com D correto por cerca de 4,99 ns. O pico de tail foi de cerca de 314 µA, ante 133 µA no controle, e as bordas ficaram mais rápidas. O intervalo entre o fim da condução acima de 1 µA do tail e o início de PRECH pelo mesmo marcador foi de cerca de 126–127 ps, no recorte de 59 ns. A integração segue bloqueada pela falta de terminais físicos de alimentação e resposta incremental multiporta de SCLK/PRECH/retornos sob cargas representativas. Aprovar um ECO requer demonstrar comportamento na rede física compartilhada. [Auditoria causal](phase3_auditoria_causal_sense3_tt_20261121.md) · [Resultado do v2](phase3_driver_local_sclk_v2_tt_20261121.md) · [Preflight](phase3_preflight_integracao_sclk_v2_20261121.md)

- **Pronto para apresentar.** Vistas físicas de C rastreadas, PASS limitado em SS, FAIL localizado em TT, diagnóstico do sense, Monte Carlo esquemático reproduzível e matriz explícita de pendências.
- **Pode fechar com pouco esforço.** Revisão offline e registro das decisões sobre temperatura nominal, `tt_mm` e escopo exigido da estatística, critérios pendentes de aceite temporal e calendário de complemento de 8×8/32×8. A proposta exige essas dimensões, enquanto a Fase 4 agenda sua geração física. Recomenda-se manter o requisito e formalizar a caracterização após geração, DRC/LVS e PEX. Nenhuma redução do escopo é tratada como aprovada.
- **Etapa posterior.** Resolver TT com consideração da impedância compartilhada, validar FF de C na mesma fixture como cobertura adicional, qualificar temporização e potência, e gerar Liberty. FF agora acrescentaria um ponto de comparação por cerca de uma hora com conferência do run, sujeito a timeout. O FAIL de TT, a Liberty e a lacuna 8×8/32×8 permaneceriam. Priorizar o fechamento documental para o dia 23 e reservar a execução FF para uma pergunta explícita de cobertura ou regressão.

Esta rodada realizou apenas conferências offline. A rastreabilidade e os comandos estão no índice e no manifesto do pacote. Os waveforms volumosos e PEXs permanecem nos caminhos originais, com hashes para verificação local.
