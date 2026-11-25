# Fase 3 da SRAM 4×8 — plano de execução até P5

**Atualização de 25/11/2026.** P2 foi fechado tecnicamente para a candidata virtual de oito StrongARM nos três corners, com os vereditos brutos preservados e os suplementos aceitos por evento. P3 seleciona tecnicamente a geometria física v6 híbrida de três StrongARM: é a única variante com GDS, LEF, DRC, LVS e PEX coerentes disponíveis. P4 foi fechado tecnicamente na mesma identidade v6: C250 TT/SS/FF passa e os replays integrados de 370 ns passam em função, cobertura, topologia e recibos nos três corners, com idle c12 em 247,5 ns. Os witnesses suplementares TT c2, FF c2 e FF c10 foram reconciliados por evento, mantendo os vereditos brutos. P5 tem pilotos de tACCESS, tCLK_TO_DATA, liberação combinada read→idle e energia de ciclo completo nas ondas v6, todos `PROVISIONAL`. P_STATIC/P_IDLE qualificada, sweeps completos de timing, setup/hold, SNM pós-layout e Liberty caracterizada permanecem pendentes. A seleção v6 é uma decisão técnica local e ainda requer registro de aceite da equipe.

Este plano adota as prioridades da equipe de P0 a P5. **P5 termina com timing, potência, SNM Hold/Read e Liberty da geometria 4×8 selecionada.** As configurações 8×8 e 32×8 e a otimização de área ficam em P6. A exigência dimensional da especificação continua aberta no encerramento desta rodada. O registro anterior, ao fim do documento, conserva a numeração utilizada pelos recibos e pelo `run_state.md`. [Especificação, §§20–21](../specs/technical_specification.md) · [Estado da execução](../memory/memory-ip/run_state.md)

## Situação e ordem de execução

Base da campanha documentada em `integration/phase3-danilo-ss`, HEAD `e159052`. A revisão e as decisões subsequentes estão no checkout local atual. Os responsáveis abaixo são encaminhamentos propostos no plano de 13/11. [Distribuição de trabalho](phase3_plan_to_20261123.md)

| Prioridade | Estado verificado em 25/11 | Trabalho restante e critério de conclusão | Responsável proposto |
|---|---|---|---|
| **P0 · Analisador de payload estático** | Correções presentes no checkout, **23/23 testes passaram**. O replay TT reproduziu o suplemento para c2 bits 4/7, com veredito bruto inconclusivo e entradas intactas. FF c2 também tem suplemento diagnóstico, mas FF c10 permanece fora da regra de escrita após idle. | Registrar a revisão exata do código testado no pacote P1. O suplemento cobre escrita após idle com isolamento e ausência de transição comprovados. A aceitação elétrica desse método pertence a P2. | Leonardo e André |
| **P1 · Publicar evidências de 24/11** | Snapshot histórico local verificado. Pacote incremental criado com 295 membros, manifesto SHA-256 e links relativos, extraído e rehashado sem divergências em outro diretório local. | Registrar distribuição à equipe e restauração por outro integrante. A extração local é verificada, mas a publicação externa continua pendente. | Leonardo e Danilo |
| **P2 · Resolver eventos de barramento — FECHADO TECNICAMENTE** | Replays virtuais TT/SS/FF de 370 ns passam função 18/18 e c12. Doze lanes nos eventos TT c2 e FF c2/c10 têm veredito bruto `INCONCLUSIVO`. A decisão técnica aceita suplementos delimitados por evento e preserva os vereditos brutos. Sete controles negativos são rejeitados. | Aceite da metodologia registrado em [decisão técnica P2](phase3_p2_decisao_tecnica_20261125.md). Não transfere o resultado virtual para uma geometria física. | Revisão técnica local concluída |
| **P3 · Selecionar e fechar a arquitetura física** | Decisão técnica local pela v6 híbrida. GDS 540 × 380 µm, DRC=0, LVS `UNIQUE_MATCH`, LEF e PEX identificados por hash. A variante virtual de oito StrongARM não tem geometria física correspondente. | Registrar aceite da equipe e manter v6 como geometria de referência 4×8. Qualquer mudança de geometria reabre P3 e exige novo DRC/LVS/PEX. Evidência em [decisão P3](phase3_p3_decisao_arquitetura_20261125.md). | Revisão técnica local; aceite da equipe pendente |
| **P4 · Validar TT, SS e FF no PEX selecionado — FECHADO TECNICAMENTE** | C250 físico TT/SS/FF e replay integrado v6 de 370 ns passam em função, cobertura, topologia e recibos nos três corners. Os witnesses de ownership foram analisados por evento sob o método P2, preservando as classificações raw. | Registro técnico e hashes em [P4](phase3_p4_validacao_pex_v6_20261125.md). Uma alteração na geometria/binding reabre P3/P4. | Revisão técnica local concluída; aceite da arquitetura permanece em P3 |
| **P5 · Caracterizar e gerar Liberty** | Pilotos `PROVISIONAL` de tACCESS, tCLK_TO_DATA (48 transições/corner), liberação combinada read→idle e energia de ciclo completo na PEX v6 em TT/SS/FF. O c12 não mede P_IDLE porque a sonda fraca atravessa o ciclo. P_STATIC/P_IDLE, sweeps completos de timing, tDIS isolado/setup/hold, SNM pós-layout e Liberty caracterizada ainda pendentes. | Usar a mesma revisão física de P4. Congelar domínio PVT/slew/carga e limites; executar timing dirigido por arco e setup/hold; rodar decks separados de P_IDLE sem sondas e P_STATIC com clock parado; completar SNM Hold/Read por geometria exigida; então gerar e validar Liberty com dados aprovados. | Danilo, André, Ícaro e Leonardo |

### Revalidação executada em 25/11

A [revalidação dos gates P2](phase3_p2_revalidacao_20261125.md) regenerou os fixtures TT/SS/FF, reproduziu os oito hashes de entrada e o preflight de cada corner e reconferiu os 319 modelos por corner no container EDA. O observador foi reexecutado em saídas isoladas e reproduziu os cinco arquivos de cada corner, **15/15 hashes idênticos**. Foram confirmados função 18/18, leitura/recuperação/retenção 72/72 lanes, seis escritas com readback e c12 PASS nos três corners. As precondições dos suplementos rejeitaram os sete controles físicos negativos. A decisão técnica posterior fechou P2 para a candidata virtual. A campanha v6 concluiu TT/SS/FF; o registro P4 distingue esses resultados físicos da regressão virtual de P2.

### Decisões e validação física v6 — 25/11

A [decisão P3](phase3_p3_decisao_arquitetura_20261125.md) seleciona localmente a v6 híbrida como geometria de referência 4×8. DRC/LVS/PEX e vistas foram identificados por hash. O aceite da equipe ainda precisa ser registrado. A [consolidação P4](phase3_p4_validacao_pex_v6_20261125.md) contém hashes dos três replays físicos de 370 ns e do C250 TT/SS/FF, separando a função aprovada dos resultados brutos de ownership. TT c2 tem witness estático aprovado para bits 4/7; FF c2 para bits 1/2/4/7; FF c10 passa a regra de turnaround em todas as oito lanes. Os vereditos brutos inconclusivos continuam anexados. P4 está fechado tecnicamente.

Os pilotos P5 da v6 incluem [tACCESS e liberação read→idle](phase3_p5_piloto_taccess_v6_20261125.md), [tCLK_TO_DATA](phase3_p5_piloto_tclk_to_data_v6_20261125.md) e [energia](phase3_p5_piloto_energia_v6_20261125.md). tACCESS usa a validade da palavra completa nas nove leituras por corner. tCLK_TO_DATA registra apenas lanes que transitam após a descida de CLK (48 por corner) e mantém as demais não caracterizadas. A liberação cobre uma troca combinada por corner. Energia integra `−VDD·I(VDD_SRC)` em ciclos completos, sem subtrair leakage ou clock/pré-carga. O ciclo c12 não é amostra válida de P_IDLE, pois a sonda fraca fica habilitada até 266,5 ns. Os resultados são provisórios e não substituem arcos isolados, setup/hold, `P_STATIC`, `P_IDLE` nem tabelas de potência Liberty.

### Próximas atividades de fechamento — ordem de execução

| Ordem | Atividade | Saída necessária para avançar |
|---|---|---|
| **A · decisões de entrada** | Registrar aceite da equipe para arquitetura v6 e decidir formalmente onde serão entregues 8×8/32×8: nesta fase ou na Fase 4. Aprovar o domínio e os limites de caracterização. Usar 1,8 V, 27 °C, 20 ns, slew 50 ps e 10 fF/lane apenas como ponto piloto até aprovação. | Decisão com responsáveis, justificativa, domínio PVT/slew/carga, métricas e tolerâncias. Sem esse registro, os números continuam exploratórios. |
| **B · potência** | Na PEX v6 vinculada a P4, criar decks separados: P_IDLE com clock ativo, memória em estado conhecido e sondas externas desligadas; P_STATIC com clock parado e estado armazenado conhecido. Repetir TT/SS/FF e medir janelas estabilizadas. Preservar os pilotos de energia de leitura/escrita e separar consumo da macro de host/sondas. | Recibos e ondas hash-bound; corrente/potência média, duração e estado da macro por janela; energia por leitura/escrita e método de baseline documentados. |
| **C · timing e barramento** | Completar tACCESS e tCLK_TO_DATA por bit/polaridade, incluindo transições dirigidas para lanes sem comutação nos replays atuais. Isolar tDIS por CSb, OEb e WEb; medir Z→0/1 e 0/1→Z com teste de condução/liberação. Fazer busca de setup/hold para ADDR, controles e DATA em torno da subida de CLK. Cobrir corners, slews e cargas aprovados. | Matriz por arco/bit/polaridade/PVT/slew/carga, bordas de passe/falha, critérios e formas de onda. Nenhuma transição ausente ou lane não exercitada recebe valor inferido. |
| **D · SNM** | Revisar o método e as 200 Hold/206 Read esquemáticas `tt_mm`; aprovar circuito, condição Hold/Read, modelo de variação e escopo pós-layout. Executar a população exigida em cada configuração que permanecer no escopo, mantendo seeds e tentativas inválidas. | VTCs por seed, classificação e hashes, N válido ≥200 por modo, estatísticas e escopo físico/estatístico aprovados. Distinguir mismatch local de variação global; não inferir yield. |
| **E · Liberty** | Só após C e B aceitos, implementar o gerador para a geometria e domínio aprovados. Incluir arcos condicionais de leitura, tri-state/enable/disable, setup/hold e potência; validar pinos e barramentos contra LEF/Verilog. | Geração determinística, parse em consumidor Liberty/STA e comparação de pontos e pontos intermediários contra SPICE com tolerância definida antes da validação. |
| **F · fechamento** | Agregar função, ownership, timing, potência, SNM e Liberty sob um perfil vinculado aos hashes de PEX/PDK/modelos. Atualizar matriz de requisitos, checklist, pacote e guia de reprodução; fazer revisão independente. | Todos os gates aprovados, reprodução independente documentada e decisão dimensional resolvida. Se 8×8/32×8 forem transferidas, registrar a mudança e declarar apenas o fechamento parcial 4×8, sem chamar a Fase 3 integral de concluída. |

**Dependências atuais:** P2 e P4 têm fechamento técnico registrado; P3 aguarda aceite da equipe. A atividade A desbloqueia a qualificação formal de B–E. Os pilotos atuais permanecem válidos como evidência exploratória da PEX v6, mas não substituem novas medições depois que o domínio for congelado. Não repetir P2/P4 se a identidade física não mudar.

### Histórico controlado — replay SS c12 a 5 ps no estímulo original

O transiente de 370 ns concluiu em ngspice 44.2 com código 0. Passo nativo máximo 5,0000003 ps, 75.038 amostras. Com idle solicitado em **247 ns**, o observador original confirma liberação nas oito lanes até 247,6475 ns. Bit 6 tem 50,33027 ps interpolados, mas apenas 47,5 ps conservadores entre amostras nativas e borda, abaixo do gate de 50 ps. Portanto drive permanece sem witness suficiente **nesse estímulo histórico**. Deck, onda, log, observador e hashes estão em `build/phase3/diagnostics/c12_5ps_candidate_ss_20261124/`. A repetição custou cerca de 1 h 35 min, incluindo o transiente e a exportação da onda.

## Estado atual e próxima execução

O contraste preliminar de 267 ns terminou com código 0 e 27.547 amostras a passo máximo de 10 ps. Com CSb/OEb pedindo idle em **247,5 ns**, o witness conservador de DATA6 foi 545,05 ps, acima do piso de 50 ps. Condução e liberação passaram, com todas as lanes liberadas até 248,194623 ns. A regressão integrada de 370 ns confirmou c12 em **TT, SS e FF** com essa nova condição. O fixture original, com pedido em 247 ns, conserva seu resultado histórico inconclusivo. A autorização da nova condição como protocolo final e sua caracterização de setup permanecem pendentes. [Resultado do contraste](../build/phase3/diagnostics/c12_idle_247p5_ss/observer_summary.json)

O gerador aceita `--c12-idle-start-ns` e `--output`, valida o intervalo entre restauração e captura, atualiza as bordas CSb/OEb e o horário em `fixture.json`, e registra a origem nos hashes do preflight. A regeneração isolada para TT/SS/FF reproduziu **8/8 hashes de entrada e os preflights** das fixtures em `build/phase3/integrated_idle_247p5/` para 247,5 ns. O padrão de 247 ns conserva seu comportamento histórico e valores inválidos são rejeitados. As rampas acabam em 247,55 ns, deixando 2,45 ns antes da subida nominal de 250 ns. O setup público continua pendente de caracterização. [Gerador](../tools/phase3_prepare_virtual_eight_integrated.py)

### Replays integrados da condição de 247,5 ns

O executor com PEX física `a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f`, GDS `315c2ebceb2bc4cf258fa63be2279843805db3010637d0c273aea9db12813e37` e binding virtual `d2151cac96a35a99b200764eec6ebbea517915d413cc1ddb8664a1dc7e247227` validou os **319 hashes de modelos em cada corner**. Cada execução terminou com status `COMPLETED`, retorno 0, onda completa, logs e checks de integridade. O observador histórico foi adaptado à topologia virtual de oito StrongARM e ao fixture identificado, com saídas derivadas isoladas das entradas.

| Corner | Tempo de execução | Amostras nativas | SHA-256 da onda | Função | Barramento bruto |
|---|---:|---:|---|---|---|
| TT | 2452,34 s | 22.789 | `f71bca6f4ed39c315c349bfc59a1e1e4340f4f7f97c8bd7d33534bc83e41d761` | 18/18 PASS | c2 bits 4/7 INCONCLUSIVO |
| SS | 2729,96 s | 20.584 | `8dcaeb125dd91431ee305ca8a54ee5d6da028087474472a0973f0f00de00458f` | 18/18 PASS | PASS, inclusive c12 |
| FF | 1845,79 s | 23.199 | `39347e5db1aee1f49d7b53b204a6e634641d0612eaf2a837d6d3f00c97829ac3` | 18/18 PASS | c2 bits 1/2/4/7, c10 bits 1/2/3/4/5/7 INCONCLUSIVO |

`classification_gate`, `lane_coverage_gate`, `receipt_integrity_gate` e `p1_replay_gate` são **PASS** nos três corners, com nove leituras × oito lanes. Saídas e recibos em `build/phase3/integrated_replay_247p5/{TT,SS,FF}/` e `build/phase3/integrated_observed_247p5/{TT,SS,FF}/`. O comparador e os suplementos derivados estão em `build/phase3/integrated_audits_247p5/`. O comparador detalhado, reproduzido independentemente das mesmas três ondas, tem SHA-256 `3393bedff889f6e4c3fbab65b24840d4686c03e34fbe40bdc46ab5a28474e8f6`. [Executor](../tools/phase3_replay_integrated_idle.py) · [Compatibilidade do observador](../tools/run_phase3_integrated_review_compat.py) · [Comparador](../tools/phase3_compare_write_witness.py)

### Decisão de P2 e caminho crítico até P5

**O impedimento de P2 é demonstrar quem conduz DATA em três escritas.** Em TT c2 e FF c2, após idle, o pad já está no nível da palavra de escrita quando o host forte é ligado. Em FF c10, a macro precisa primeiro liberar a leitura anterior. Nos três eventos há lanes em que o observador não consegue atribuir uma resposta de carga ao host. Uma amostra isolada de correntes opostas na habilitação também não permite concluir contenção sustentada. O readback confirma o valor armazenado. A atribuição elétrica durante a troca de condutor exige a evidência de cada lane. A causa de uma eventual falha do circuito permanece indeterminada. [Comparação por lane](../build/phase3/integrated_audits_247p5/write_witness_comparison_detailed.json)

A matriz identifica **12 ocorrências de lane em três eventos**. SS passa integralmente. Os positivos SS c2 e TT/SS c10 exercitam a regra original. Os sete controles físicos negativos mostram que as precondições dos suplementos rejeitam os defeitos injetados. A matriz offline mantém `PENDING_PROTOCOL_APPROVAL` por projeto e preserva a trilha reproduzível anterior à decisão. A revisão técnica subsequente aceitou o método com os critérios por evento e hashes documentados na [decisão de P2](phase3_p2_decisao_tecnica_20261125.md). A classificação bruta continua preservada. [Matriz v2](../build/phase3/diagnostics/p2_revalidation_20261125T083047/review_matrix_v2.json) · [Controles físicos](../build/phase3/diagnostics/p2_revalidation_20261125T083047/supplement_physical_controls.json)

| Ordem | Ação e responsáveis propostos | Evidência para avançar |
|---|---|---|
| 1 · TT e FF c2 | André e Danilo revisam a regra idle→write nos bits 4/7 de TT e 1/2/4/7 de FF. Confrontar DATA antes e durante a escrita, liberação após idle, gate da macro, habilitação do host e correntes por lane. Leonardo reproduz a classificação. | Registrar a interpretação da amostra de oposição na habilitação e a decisão separada para TT c2 e FF c2. Exigir isolamento, estabilidade e ausência de oposição sustentada com o piso vigente de 50 ps. |
| 2 · FF c10 | Revisar a regra read→write nos bits 1/2/3/4/5/7. Conferir a condução e a liberação da leitura anterior, o intervalo isolado de 14 amostras, o desligamento da sonda fraca e DATA desde a primeira amostra do host forte até a captura e o fim da escrita. | O auditor agora exige DATA no nível esperado continuamente desde a habilitação do host até CLK, além da janela estável durante o restante do drive. Uma regressão de transição tardia falha nessa condição. A reanálise mantém as seis lanes elegíveis para revisão. Decidir se a regra e as 70 amostras antes de CLK são aceitas, vinculando a separação conservadora de 1,029869 ns. |
| 3 · Decisão do protocolo | André e Danilo registram o perfil de idle em 247,5 ns, com revisão de Leonardo. Vincular as três decisões, os resultados brutos, os suplementos e os controles à PEX, ao binding e à versão do observador. | P2 fechado tecnicamente para a candidata virtual com os 18 eventos por corner, checks funcionais, controles, cobertura e integridade aprovados. Preservar o resultado histórico de 247 ns. O setup público será medido em P5. |

**Se a revisão não aceitar um suplemento**, identificar a lane e a condição sem prova antes de simular. Para c2, propor um contraste que imponha uma transição conhecida no pad quando o host assume a escrita. Para c10, manter a leitura anterior e observar a última condução da macro, o intervalo isolado e a primeira condução do host. Fixar o estímulo e o critério antes do ensaio, incluindo o mínimo de três amostras e o piso conservador de 50 ps. Executar primeiro a fatia do corner afetado. Se o contraste indicar alteração do perfil integrado, gerar nova revisão e validá-la nos três corners com recibos próprios. Qualquer oposição sustentada exige diagnóstico da habilitação/liberação antes do aceite.

### Execução após P2

| Etapa | Ação | Critério de conclusão |
|---|---|---|
| P3 · Arquitetura e fechamento físico | A equipe compara v6 e candidata no protocolo aceito. Para v6, reconciliar GDS, LEF, netlist e PEX existentes. Para oito StrongARM, integrar fisicamente os cinco núcleos restantes, buffers, clock, alimentação e rotas. | Decisão de arquitetura justificada, vistas da mesma geometria identificadas por hash, DRC zero, LVS único com propriedades conferidas e PEX distribuída. |
| P4 · Regressão física | Danilo e André executam C250 e integrado de 370 ns em TT/SS/FF na revisão selecionada. Reaproveitar um recibo existente somente após conferir identidade de geometria, binding, corner, estímulo e observador. | Em cada corner, C250 aprovado, 18 operações, 72 bits de leitura, seis escritas com readback, quatro linhas, retenção, controles internos e ownership aceitos. Uma mudança de geometria exige nova verificação física. |
| P5 · Caracterização e entrega | Congelar domínio PVT, slew, carga e tolerâncias. Danilo e André medem timing e potência/energia. Ícaro caracteriza SNM Hold/Read pós-layout. Leonardo gera Liberty das tabelas aceitas. | Mesma revisão de P4 em todas as medições, cobertura dos arcos e domínios declarados, estatísticas SNM, Liberty lida em STA e conferida contra SPICE, pacote reproduzido por outro integrante. Os critérios por medição constam na seção P5 abaixo. |

**Campanha física v6, atualização de 25/11.** TT e SS completaram os transientes de 370 ns com recibos e 319 modelos verificados por corner. FF está em execução serial. As três análises funcionais e de ownership continuam pendentes. Os resultados definirão se a geometria v6 pode avançar como candidata de P3/P4. [Recibo TT físico](../build/phase3/integrated_v6_idle_247p5/TT/simulation.json)

A distribuição e a restauração independente do pacote P1 podem avançar em paralelo. O fechamento em P5 cobre a geometria 4×8. As dimensões 8×8 e 32×8 continuam em P6, com a pendência da especificação registrada.

## Evidências para a revisão de P1 e P2

P1 pode avançar em paralelo à análise das ondas locais. Os caminhos de evidência abaixo partem de `../phase3_evidence_20261124/`, relativo à raiz de `projeto-sram`. O manifesto do snapshot cobre 1.807.007.816 bytes. Os runs derivados contêm links absolutos para esta máquina, inclusive para `waveform.dat`. Na restauração de P1, verificar os destinos e reproduzir as duas análises com o pacote extraído. [Inventário local](../../phase3_evidence_20261124/README.md)

| Evento | Observação reproduzida ou registrada | Teste discriminante e decisão |
|---|---|---|
| TT c2, escrita após idle | Bits 4/7 sem witness de carga. Nível correto antes e durante o host forte, gate DUT desabilitado, host habilitado e ausência de oposição sustentada. Uma amostra nativa de oposição ocorre exatamente em `48,0281608 ns`, no fechamento da habilitação do host. Suplemento `PASS_WITH_STATIC_PAYLOAD_WITNESS`, bruto inconclusivo. | Homologar interpretação de transiente de fechamento e witness estático. Controlar payload com e sem transição, ausência intencional do host e contenção persistente, conservando os limiares. |
| FF c2, escrita após idle | Bits 1/2/4/7 sem witness de carga, no nível correto desde antes do host. Oposição host/DUT aparece em **uma amostra por bit**, no mesmo fechamento de `48,0281608 ns`, com gate DUT desabilitado e sem oposição sustentada. O suplemento diagnóstico aplica-se apenas a c2, enquanto o bruto segue inconclusivo. | Confrontar controles físicos de TT/SS/FF e homologar a mesma regra de idle→write antes de promover qualquer suplemento a aceite. |
| FF c10, leitura → escrita | Bits 1/2/3/4/5/7 sem witness de carga. Liberação da leitura verificada até cerca de `207,492813 ns`. Janela isolada entre `208,428161` e `208,522682 ns` com 14 amostras. Host conduz a partir de `208,527893 ns`. Há uma amostra de oposição no início do host forte por bit, seguida de DATA estático no nível esperado e sem oposição sustentada. A janela **anterior** não fica no trilho do novo payload. | Definir e validar regra específica de turnaround `read_to_write` com controles que discriminem liberação insuficiente, host desligado e contenção persistente. O witness estático após idle não satisfaz as precondições de c10. |
| SS c12, leitura → idle | **PASS na regressão integrada** com pedido de idle em **247,5 ns** (idem TT e FF). O histórico a 247 ns permanece inconclusivo, mesmo com passo de 5 ps, pois DATA6 tem 47,5 ps conservadores frente a 50 ps mínimos. | Registrar e aprovar o perfil de estímulo de 247,5 ns para o protocolo de P2 e preservar a classificação histórica a 247 ns. Caracterizar o setup público posteriormente. |

Os replays novos usam o perfil explícito da PEX `a1e812…`, com o mesmo GDS e binding verificados. O runner histórico preso a `12c41…` foi mantido e o adaptador de perfil reproduziu a análise com topologia de oito lanes, incluindo seleção de linha, captura, sense e recuperação existentes no histórico. Os controles sintéticos negativos do auditor cobrem gate desabilitado inválido, host ausente, contenção sustentada e ausência de carga, com **23 testes passando**. A campanha concluiu os sete controles físicos negativos descritos abaixo. [Comparação nova por lane](../build/phase3/integrated_audits_247p5/write_witness_comparison_detailed.json) · [Observação SS integrada](../build/phase3/integrated_observed_247p5/SS/analysis.json) · [Observação FF integrada](../build/phase3/integrated_observed_247p5/FF/analysis.json)

### Diagnóstico físico incremental para P2

Dois controles negativos de **FF c2**, simulados em fatias isoladas de 70 ns com ngspice 44.2, terminaram `COMPLETED`, retorno 0 e recibos/ondas/decks com SHA-256 conferidos. O preparador preservou a PEX, o binding e os 319 hashes dos modelos do replay FF de 370 ns e modificou somente a duração diagnóstica e a condição de falha declarada.

| Controle FF c2 | Witness em amostras nativas | SHA-256 da onda | Saída |
|---|---:|---|---|
| Host desligado durante a escrita | 25 amostras, **582,058 ps**, corrente de host abaixo de 50 µA | `6f5fa8059c8233b1de199e36ddb73fe4991a15c196e71c5e349863490e3a29df` | `build/phase3/diagnostics/physical_controls_20261124/FF_c2_no_host_70ns/` |
| Fonte de contenção de 300 Ω conectada ao lado DUT da sonda | 34 amostras, **809,188 ps**, correntes de host e macro opostas, ambas acima de 50 µA | `89e5ba7b4b9f29b017e5a560237f34c7e2f82695ecc0786a7c9a71da8c202d60` | `build/phase3/diagnostics/physical_controls_20261124/FF_c2_contention_dut_70ns/` |

O detector isolado identificou os dois defeitos com piso conservador de 50 ps. Uma verificação independente com `inspect_strong` do observador original, na mesma janela de 48,2–49,05 ns, confirmou que **nenhum desses defeitos recebe PASS**. Ambos recebem `INCONCLUSIVO` no observador original. Com host desligado, o campo `strong_host_on` é falso. Na contenção, a lane 4 registra `opposition_with_gate_off` e perde `quiet_suffix`. A distinção entre a detecção pelo controle especializado e o veredito do observador original está preservada em `observer_crosscheck_c2_20261125.json`. A primeira tentativa de contenção, conectada diretamente ao barramento e não ao lado DUT da sonda, foi **interrompida** com retorno −2 e está preservada em `FF_c2_contention_70ns/` como experimento descartado. [Verificador independente](../tools/phase3_review_physical_controls.py) · [Launcher de controle](../tools/phase3_bus_physical_controls.py)

**FF c10, leitura→escrita, auditoria suplementar de 25/11.** O novo verificador exigiu condução e liberação da sonda anterior, isolamento entre os drivers com 14 amostras, separação positiva conservadora de 1,029869 ns, desligamento da sonda fraca, host forte habilitado, gate da macro desabilitado, ausência de oposição sustentada e quietude em todas as lanes. Para os bits 1/2/3/4/5/7, sem witness de carga, DATA está no trilho esperado desde a primeira amostra de host forte até a subida de CLK, com **70 amostras e 1.472,107 ps** de estabilidade conservadora antes da subida, e permanece estável até o fim da janela de escrita. O resultado é `ELIGIBLE_FOR_PROTOCOL_REVIEW`, condicionado à homologação elétrica da regra específica de `read_to_write` e à conclusão dos controles físicos. O observador original segue `INCONCLUSIVO` em FF c10. O relatório é `build/phase3/integrated_audits_247p5/FF_c10_read_to_write_candidate_20261125.json`, com hashes de entradas e revalidação de imutabilidade. Os quatro testes direcionados às precondições passaram. [Auditor read-to-write](../tools/phase3_audit_read_to_write.py)

**Novos controles físicos de 25/11.** Três simulações de diagnóstico adicionais terminaram com ngspice 44.2, retorno 0, 319 modelos verificados na preparação, recibos SHA-256 e defeitos identificados pelo detector especializado. São fatias da PEX vinculada aos replays de 370 ns, com falha deliberada no estímulo.

| Corner e evento | Defeito injetado | Witness nativo conservador | SHA-256 da onda |
|---|---|---:|---|
| FF c10, 230 ns | Host forte desligado na escrita após leitura | 25 amostras, **597,747 ps**, corrente do host abaixo de 50 µA | `821a4387ebe407471dc2109aafadebd3bb503bf7649b1c558753a15f7cd2e070` |
| TT c2, 70 ns | Host forte desligado na escrita após idle | 24 amostras, **575,000 ps**, corrente do host abaixo de 50 µA | `3a559bc78280c13c464d5d2c038fdc2720fcf169c5a9611cbaa8cedf944ac66c` |
| TT c2, 70 ns | Fonte de contenção de 300 Ω no lado DUT, bit 4 | 34 amostras, **825,000 ps**, correntes opostas acima de 50 µA | `41d31f440390f6d12d36414c970511b84799f333b74b98cad6ef261b62fcb8dd` |

Recibos e ondas em `build/phase3/diagnostics/physical_controls_20261124/{FF_c10_no_host_230ns,TT_c2_no_host_70ns,TT_c2_contention_dut_70ns}/`. O confronto independente de **quatro controles c2** (host desligado e contenção no lado DUT em TT e FF) com `inspect_strong` retornou `INCONCLUSIVO` em todos, e nenhum recebeu `PASS`. Em host desligado, `strong_host_on=false` no bit 4; na contenção, `opposition_with_gate_off=true` e `quiet_suffix=false` no mesmo bit. O relatório `build/phase3/diagnostics/physical_controls_20261124/c2_observer_crosscheck_20261125.json` tem SHA-256 `8d35527a1e294ddd8b02a1a70bfa38538b136d0ca8e17f98eca7d2b7e0c44b55`. A consolidação posterior `p2_review_matrix_20261125_v3.json` também executou o confronto dos três controles FF c10 com o observador original, sem falso `PASS`.

**FF c10, liberação de leitura atrasada — CONCLUÍDO em 25/11.** O ngspice 44.2 terminou a fatia de 211 ns com retorno 0, sem erros. A injeção modificou apenas as fontes `V_OEb` e `V_WEb`, preservando `V_CSb`, o host e os demais estímulos da PEX vinculada ao replay FF. A macro continuou conduzindo na troca leitura→escrita e o detector registrou **26 amostras nativas de correntes opostas**, com **625,000 ps** conservadores, corrente do host de aproximadamente −0,488 mA e da macro de +0,488 mA, acima do limite de 50 µA. Resultado `negative_control_rejected=true`, `fault_detected=true`, `status=COMPLETED`. A verificação independente de hashes no container confirmou a onda SHA-256 `fcdbb41f38a294358e2409f59336549cf90be6d787575f2bcd06da47b6442550`, recibo `a27fdf0d7b992ad0f29f16d88651e78609ff9c491f8e7cd858ba864796133348`, manifesto `b8982bf0ad100367e24e780a665e97ddb7f5f2983a04d7732f7ca310a69f4dfe`, a origem de 370 ns e os **319 modelos**. Evidência em `build/phase3/diagnostics/physical_controls_20261124/FF_c10_delayed_release_211ns/`. O controle identifica a falha física injetada, sem homologar o suplemento do evento natural c10. O gerador e os auditores direcionados passaram **29/29 testes em unittest** após a conclusão.

**FF c10, host fraco indevidamente mantido — CONCLUÍDO em 25/11.** A fatia de 211 ns terminou `COMPLETED`, retorno 0 e sem erros, modificando somente a fonte `V_HOST_WEAK_EN`. O detector identificou **28 amostras** e **675,000 ps** conservadores de habilitação simultânea do host fraco e do host forte durante a transição leitura→escrita (`negative_control_rejected=true`). Esse testemunho verifica a violação da condição de exclusividade de habilitação. A corrente no ramo forte ficou abaixo de 1 µA na janela, portanto **não constitui prova de contenção elétrica por corrente**. O rehash independente no container confirmou os 319 modelos e a origem integral de 370 ns, onda SHA-256 `4712861d00be55bd24e7c62e74fd45b4c64736ca1bc7bc8b763a026ba07332f4`, recibo `8a7aeac0fc33a12f1426b64da8af9ed3dfc3c9f66aae0c46dd27d906c6f0a0cf` e manifesto `68f78d02f77eafb77d7298d67f786aa0619785de6c69d0a84819028d872bc8ff`. Evidência em `build/phase3/diagnostics/physical_controls_20261124/FF_c10_stuck_weak_211ns/`.

**Registro histórico da revisão anterior à decisão P2.** Os parágrafos e tabelas seguintes preservam resultados e pendências registrados antes da decisão técnica de 25/11. Para o estado vigente, usar o resumo no início, as decisões P2/P3/P4 e o `run_state.md` atualizado. A qualificação elétrica global continua `NOT_CHARACTERIZED` até concluir P5.

### Pacote P1 incremental — checkpoint local de 25/11

O empacotador `tools/phase3_package_incremental.py` validou os três recibos, as ondas e a matriz P2. A revisão v2 contém **295 arquivos** e **1.215.865.055 bytes** de conteúdo listado no manifesto. O SHA-256 do manifesto é `7940aea6718df74d074c59a2c89f4d05dba115bf893773cfad559f4905e4376a`. O arquivo local `../phase3_incremental_20261125_v2.tar.gz` tem SHA-256 `575fd9732cdd8aabb70194f34907c4c091fb77c92d4338cd1e9cbf2ebed5fa53`. A extração em `../phase3_verify_20261125_v2/phase3_incremental_20261125` e a verificação independente de todos os membros e links passaram. O pacote é um delta do snapshot preservado `../phase3_evidence_20261124/`, requer o PDK SKY130A e o ambiente EDA para reexecutar simulações. O teste de extração foi local; distribuição e restauração por outro membro ainda precisam ser registradas.

Para reproduzir a verificação offline, executar na raiz de `projeto-sram` com Python e NumPy. Cada execução cria um diretório de saída novo.

```bash
evidencia=../phase3_evidence_20261124
saida=$(mktemp -d)
python3 -m unittest discover -s tools -p 'test_phase3_audit_integrated_no_transition.py'
python3 tools/phase3_audit_integrated_no_transition.py   "$evidencia/derived_integrated/virtual_eight_TT_final" --output "$saida/TT.json"
python3 tools/phase3_compare_write_witness.py "$evidencia" --output "$saida/comparison.json"
python3 tools/phase3_compare_write_witness.py "$evidencia" \
  --replay-root build/phase3/integrated_replay_247p5 \
  --observed-root build/phase3/integrated_observed_247p5 \
  --output "$saida/integrated_247p5_comparison.json"
```

## P5 — quatro entregas e critérios de aceite

**Entrada da campanha.** Preparar bancadas, extratores e gerador durante P1–P4. Antes de medir valores finais, congelar o hash da PEX aprovada em P4 e a matriz de processo, VDD, temperatura, slew, carga, período e duty. Os 1,8 V, 27 °C, 20 ns, 50 ps e 5/10/20 fF do contrato são pontos iniciais propostos. Fixar limiares, tolerâncias e cobertura antes do piloto. Usar o launcher `./tools/sram-eda`, um worker e um diretório por execução. Medir custo e espaço do piloto para dimensionar a matriz. As execuções históricas de 370 ns levaram cerca de 28–30 minutos por corner. [Contrato de caracterização](phase3_characterization_contract.md) · [Protocolo da 4×8](../specs/sram_4x8_timing_contract.md)

1. **Timing — Danilo e André.** Medir `tACCESS` da subida de CLK até a **nova palavra inteira válida** e `tCLK_TO_DATA` da descida até DATA50, por bit e polaridade. Registrar também propagação interna até DOUT_RAW e margens na captura local. Varrer setup e hold de ADDR, CSb/OEb/WEb e DATA de escrita em relação à subida pública. Delimitar sucesso/falha e refinar a fronteira com leitura de retorno e verificação funcional. Para habilitação e desabilitação de DATA, excitar cada controle aplicável com READ_Q e controles vivos conhecidos, medir Z→0/1 e 0/1→Z com sonda de condução/liberação. **Aceite:** tabelas em ns/ps por arco, polaridade, PVT, slew e carga, com formas de onda e cobertura. Gerar transições dirigidas para os arcos obrigatórios que não comutaram. Registrar casos estáveis e fronteiras não delimitadas explicitamente.
2. **Potência — Danilo.** Medir `P_STATIC` com clock parado, estado armazenado conhecido e corrente estabilizada. Medir `P_IDLE` com clock ativo e sem acesso, declarando frequência. Integrar a potência fornecida à macro, `−V(VDD) × I(VDD_SRC)`, em ciclos completos de leitura e escrita após inicialização. Excluir fontes de host/sonda da soma. Declarar padrões, transições, carga, janela, pré-carga, baseline e eventual subtração. **Aceite:** potência estática e idle em W ou submúltiplos, energia em J/leitura e J/escrita, potência média igual a energia/duração na mesma janela, rastreável às correntes e operações válidas. Distinguir energia total de ciclo e a parcela interna usada na Liberty.
3. **SNM Hold e Read — Ícaro, revisão de Danilo.** A auditoria de VTCs já registra **200 Hold e 206 Read válidas** na bitcell esquemática `tt_mm`, 1,8 V/27 °C, com mismatch local. Seis tentativas Read foram recuperadas ao revisar os extremos das curvas. Revisar essas classificações e definir o recorte extraído representativo da célula selecionada, condições de WL/BL/BLB de Hold e Read e modelo de variação. Conferir as duas curvas e os dois lóbulos da butterfly, reportando a menor margem por amostra. Reaproveitar as VTCs no domínio em que foram medidas e executar a cobertura pós-layout pendente. **Aceite:** Hold e Read identificados por circuito, PVT/modelo e seed, N válido ≥200 por modo na campanha MC declarada, lista de tentativas inválidas, distribuição, mínimo, média e dispersão em mV. [Auditoria das amostras](../../phase3_evidence_20261124/build/phase3/snm_endpoints_final_20261120/audit.json)
4. **Liberty — Leonardo, revisão de Danilo e Ícaro.** Implementar o gerador a partir das tabelas aceitas de timing e potência. Emitir uma vista por condição caracterizada, com pinos e barramentos coerentes com LEF/Verilog, DATA bidirecional, condição de tri-state, arcos de leitura, enable/disable, setup/hold e grupos de potência compatíveis com o método medido. Associar cada entrada ao run, unidades, índices e revisão física. O relatório SNM acompanha a biblioteca. **Aceite:** regeneração determinística, leitura em consumidor Liberty/STA, inspeção dos arcos condicionais e comparação com SPICE em pontos da grade e pontos intermediários independentes, dentro da tolerância definida antes da validação. Um arco obrigatório sem medição mantém a entrega aberta.

**Fechamento de P5.** Implementar o perfil de caracterização no runner com verificação de função, controles, ownership e cobertura das medidas. Consolidar `metrics.csv`, VTCs/estatísticas, tabelas Liberty e relatório com hashes de geometria, PDK/modelos, decks, ferramentas e ondas. Um segundo integrante deve conseguir regenerar as tabelas e a biblioteca e conferir pontos representativos. Registrar o aceite das quatro entregas sobre a mesma revisão, no domínio declarado. O relatório deve identificar separadamente o requisito dimensional de P6.

---

<details>
<summary>Histórico anterior a esta revisão — numeração legada P0–P10/D1</summary>

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

Estado atual: P2 fechado tecnicamente para a candidata virtual; P3 selecionado tecnicamente para a geometria v6, com aceite da equipe pendente; P4 fechado tecnicamente para a PEX v6; P5 permanece parcial, com pilotos provisórios de tACCESS, tCLK_TO_DATA, liberação read→idle e energia. P_STATIC/P_IDLE, timing por arco e sweeps de slew/carga, setup/hold, SNM pós-layout, Liberty qualificada e decisão formal sobre 8×8/32×8 ainda impedem o fechamento integral da Fase 3. Nenhum desses marcos promove `electrical_qualification` além de `NOT_CHARACTERIZED`.

</details>
