# Plano de ação para fechamento da Fase 3

Data: 24/11/2026. Base auditada: `integration/phase3-danilo-ss`, commit `eac7abe4` (prefixo). Plano proposto; não representa aprovação da equipe nem execução das etapas futuras.

### Registro de execução — atualização 24/11

- **P0 concluído:** snapshot integral em `/home/danilo_cunha/projetos/ueletronica/phase3_evidence_20261124`; manifesto revalidado por SHA-256 em 2.717 arquivos / 1.807.007.816 bytes, zero divergências. O `run_state.md` de Phase 1 foi preservado em `metadata/run_state_phase1_20261007.md`; o registro corrente tem run_id `memory-ip_20261124_130441`, `IN_PROGRESS`, sem signoff.
- **P0, delta de fonte:** além do snapshot `build/phase3`, foram preservados os 126 arquivos modificados/não rastreados do checkout histórico; 126/126 foram comparados por SHA-256. O README e os manifestos estão em `phase3_evidence_20261124/README.md` e `phase3_evidence_20261124/metadata/`.
- **P1, classificação (COMPLETO):** replays finais derivados e imutáveis do candidato virtual TT/SS passaram `classification_gate`, `lane_coverage_gate` (9 leituras × 8 bits), `receipt_integrity_gate` e `p1_replay_gate`. Baseline SS v6 também passou: 27 StrongARM PEX + 45 nativos, oito bits únicos por leitura, recibo íntegro. Recibos finais: `derived_integrated/virtual_eight_TT_final/topology_classification.json`, `derived_integrated/virtual_eight_SS_final/topology_classification.json` e `derived_integrated/v6_baseline_SS_final/topology_classification.json`. Os três observers brutos continuam `INCONCLUSIVO` por ownership.
- **P1, suplemento TT:** o auditor preservou o resultado bruto e produziu `PASS_WITH_STATIC_PAYLOAD_WITNESS` somente para c2 bits 4/7 em `derived_integrated/virtual_eight_TT_final/static_payload_witness.json`, com `qualification=NOT_CHARACTERIZED`. É evidência diagnóstica, não fechamento de ownership. O auditor exige `--output` fora do run de entrada, valida recibos/hashes/cobertura e registra hashes dos artefatos de entrada inalterados. 13 regressões locais passaram.
- **P2, SS (INCONCLUSIVO):** candidato e baseline têm a mesma lacuna c12 `read_to_idle`, bit 6, registrada nos recibos finais SS acima. O gate de condução efetivo é 50 ps; os 100 ps são apenas diagnóstico de estresse. Candidate SS mede 57,6 ps no bit0, 80,8 ps nos bits2/4, ≥227 ps nos bits1/3/5/7; baseline mede 64,7 ps no bit0, 87,8 ps nos bits2/4 e ≥234 ps nos bits1/3/5/7. Só o bit6 não tem janela qualificável em ambos. Na onda candidate SS, DATA6 sobe de 0 para 0,951 V em 241,5–242,5 ns com pico weak-host de 1,717 mA; sobe a 1,799 V em 242,5–244 ns enquanto weak-host e DUT conduzem em sentidos opostos até 0,856 mA; em 244–245,5 ns fica em 1,799 V com ambos os ramos abaixo de ~1,5 µA. Isso é drive/corrente antes de restore e possível contention, não prova de ownership correto após restore nem de que a sobreposição seja permitida. O witness iniciado em 244 ns não encontra 50 ps antes da borda de 247 ns. Release é verificada até 247,653 ns em todas as lanes, mas `drive_verified=false`. A causa exige teste controlado.
- **Limite do ambiente:** `command -v ngspice` não encontrou executável no PATH do host nem do container; Python 3.10/NumPy 1.26 estão disponíveis para reanálise. A inspeção via Docker exigiu escalonamento e foi concluída. Não foram iniciadas novas simulações SPICE; os replays foram reanálises dos waveforms preservados.

## 1. Conclusão da análise

A Fase 3 está em fechamento funcional experimental. A infraestrutura, a recuperação dos checkpoints e uma macro física v6 estão disponíveis. A comparação virtual de oito StrongARM passou C250 nos três corners. Ainda faltam aceite funcional integrado completo, escolha e congelamento da geometria final, caracterização elétrica, SNM homologado, Liberty validada e entrega reproduzível.

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
| Integrado virtual FF | Nenhuma execução nova localizada no diretório da campanha | Pendente |
| Timing e potência finais | Medidas exploratórias/históricas em C e margens internas | Setup, hold, acesso, desabilitação, energia, leakage e domínio final não homologados |
| SNM | Handoff registra hold 200 e read 206, experimentais | Homologar método, seeds, variação global/local, domínio e escopo físico |
| Liberty | Interface/infraestrutura histórica disponível | Geração a partir de tabelas qualificadas e validação ainda pendentes |
| 8×8 / 32×8 | Requisitos explícitos na especificação | Geração física e caracterização dessas dimensões pendentes; dependência da Fase 4 |

TT/SS/FF dos experimentos recentes usam o ponto nominal de tensão/temperatura e carga da fixture. Três corners de processo nesse ponto não representam toda uma grade PVT, slew e carga.

## 3. Correções necessárias na interpretação dos resultados

1. **Topologia por variante.** TT/SS candidatos passam 72/72 lanes StrongARM PEX. O gate baseline corrigido espera 3 lanes StrongARM PEX e 5 nativas por leitura; o replay derivado passou 27/45 em nove leituras, com recibo e cobertura PASS.
2. **Suplemento estático.** O auditor foi endurecido para comprovar duração/recibo/SHA-256, 18 ciclos únicos, 8 lanes cobertas, condições de isolamento e janela mínima com amostras. A saída é obrigatoriamente externa ao run de entrada. O suplemento aceita somente c2 bits 4/7 sem transição e mantém o raw inconclusivo; seus 13 testes cobrem hash divergente, recibo falho, ciclos incompletos/duplicados, overlap e janelas insuficientes.
3. **Ownership SS não resolvido.** Candidato e baseline repetem c12 bit 6. O gate `drive_verified` usa `WITNESS_NS=50 ps`; 100 ps é apenas diagnóstico. Bits 0/2/4 têm 57,6/80,8/80,8 ps e passam o gate; bits 1/3/5/7 também. Bit 6 não tem condução qualificável. A repetição baseline mostra que o gap não é exclusivo do ECO virtual, mas não identifica se falta estímulo/observabilidade ou drive elétrico.
4. **Rastreabilidade.** Distinguir snapshot original, reanálises derivadas e saída do suplemento. Os runs permanecem ligados aos hashes de waveform/modelos; não alterar os resultados brutos. ngspice não está no PATH de host/container; a inspeção Docker exigiu escalonamento e foi concluída. Sem simulador disponível, esta rodada ficou restrita à análise existente.

Esses pontos foram identificados por inspeção de fonte/recibos e devem ser resolvidos antes de promover o suplemento a critério de aceite.

## 4. Sequência de execução e gates

Responsáveis abaixo seguem a distribuição operacional de 13/11; representam encaminhamento proposto, não disponibilidade confirmada. Danilo: RC/timing/potência. André: leitura/sense/barramento. Leonardo: infraestrutura/integração/Liberty. Ícaro: SNM/Monte Carlo.

| Etapa | Ação e entregável | Responsável proposto | Dependência | Critério para avançar |
|---|---|---|---|---|
| P0 — Preservar evidência | **Concluído:** cópia integral, manifesto SHA-256 e proveniência; run_state Phase 1 arquivado e novo run_state Fase 3 iniciado | Danilo | Concluído | 2.717 arquivos / 1.807.007.816 bytes rehashados; zero divergências |
| P1 — Corrigir observadores | **COMPLETO:** topologia parametrizada, três replays finais, suplemento conservador e 13 testes | Leonardo + André; revisão Danilo | P0 | Gates de topologia, cobertura e recibo PASS nos três runs; resultado bruto permanece preservado |
| P2 — Resolver ownership | **INCONCLUSIVO / bloqueado:** gap c12 bit6 reproduzido no candidato e baseline; preparar teste de contraste controlado | André + Danilo; revisão Leonardo | P1 | Necessário witness de drive pós-restore ou causa elétrica/protocolar isolada; nenhuma aprovação por diagnóstico pré-restore |
| P3 — Completar comparação virtual | Executar somente runs necessários após reanálise; fechar SS e então FF integrado; comparar com v6 no mesmo protocolo | Danilo | P2 | Nove palavras/72 bits, seis escritas com readback, quatro linhas, retenção e ownership aprovados em TT/SS/FF |
| P4 — Escolher arquitetura | Registrar decisão v6 híbrida versus oito StrongARM, custos físicos, carga/clock, margens, risco e fallback | Equipe; André e Danilo apresentam evidências | P3 | Variante escolhida e escopo aprovados; nenhuma seleção automática baseada só no C250 |
| P5 — Fechar geometria | Se oito: gerar cinco novas células/rotas, revisar clock/rails, obter GDS/LEF/netlist, DRC/LVS/PEX. Se v6: validar identidade da geometria já qualificada | Danilo + André; integração Leonardo | P4 | DRC zero, LVS único com parâmetros, PEX distribuído auditado e vistas coerentes por hash |
| P6 — Qualificar candidata física | Repetir C250 e integrado completo com PEX final e grade funcional aprovada; revisar modelo Verilog/protocolo | Danilo + André | P5 | Aceite funcional e ownership completos da mesma geometria em todo domínio declarado |
| P7 — Caracterizar eletricamente | Gerar tabelas de acesso, clock→DATA quando aplicável, tDIS/Hi-Z, setup/hold, energia e potência estática/dinâmica | Danilo; revisão André | P6 + domínio congelado | Matrizes rastreáveis por PVT/slew/carga, limites e unidades claros, nenhuma célula inválida convertida em número |
| P8 — Homologar SNM | Revisar VTCs e extração hold/read; seeds, modelos, N≥200 conforme escopo, estatística e amostras inválidas; complementar se necessário | Ícaro; revisão Danilo | Método pode andar em paralelo; domínio final depende P4–P6 | Método e resultados aprovados; distinguir mismatch, processo, pre-layout e pós-layout; não inferir yield da macro |
| P9 — Gerar e validar Liberty | Consumir tabelas aprovadas, gerar arcos condicionais e tri-state, constraints e potência; validar leitura e comparar pontos com SPICE | Leonardo; revisão Ícaro/Danilo | P7 e domínio aprovado | Biblioteca reproduzível, unidades/pinos/arcos corretos e concordância em tolerância definida antes da comparação |
| P10 — Entregar e revisar | Relatório final, vistas, dados, release e reprodução independente | Leonardo + equipe | P6–P9 e decisão de dimensões | Revisão cruzada registrada, pacote recuperável por outro membro e requisitos completos ou exceções explicitamente aprovadas |

Caminho crítico: P0 → P1 → P2 → P3 → P4 → P5 → P6 → P7 → P9 → P10. Auditoria SNM, definição do domínio e preparação do gerador Liberty podem avançar em paralelo; números finais dependem da geometria selecionada.

## 5. Trabalho imediato para o bloqueio de ownership

1. Reprocessar as ondas existentes com verificação de hashes e cobertura antes de gastar outro transiente.
2. Extrair no SS c12/bit6 a janela de restauração até desabilitação: DATA6, saída interna, TE_B, HOST_EN, HOST_WEAK_EN e correntes macro/host/weak. Comparar baseline e candidato na mesma escala temporal. Antes de restore, candidate DATA6 chega a 1,799 V com ramo weak-host e DUT opostos; depois, fica quieto, e em 246,9 ns mantém 1,797 V com correntes de poucos µA. No pedido de disable em 247 ns as correntes chegam a centenas de µA. Determinar se a rampa/temporização do estímulo ou o ramo DUT explica a ausência da janela pós-restore. A evidência pré-restore é diagnóstica e não aprova ownership.
3. Aplicar o gate real de 50 ps a todas as lanes; registrar 100 ps somente como diagnóstico de estresse. Bits 0/2/4 já passam o gate real; bit6 permanece sem intervalo qualificável.
4. Examinar se o estímulo realmente fornece contraste de tensão/corrente suficiente para testemunhar condução e se os controles chegam em ordem correta. Tensão estável isoladamente não demonstra Hi-Z nem autoria do drive.
5. Se houver limitação de resolução, repetir um controle com passo menor. Se a sonda não discriminar o estado, criar fixture diagnóstica versionada com perturbação controlada e acordo de metodologia. Se houver erro elétrico/protocolo, corrigir a causa e repetir os gates afetados.
6. Incluir controles negativos: contenção deliberada e driver sem condução devem reprovar; nenhuma redução de limiar deve ser escolhida apenas para obter PASS.
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
