# Fase 3 — revalidação dos gates P2 em 25/11/2026

A revalidação confirmou as etapas 1 e 2 do plano e reproduziu a análise da etapa 3. **Na data deste snapshot, P2 permanecia aberto:** o observador bruto era inconclusivo em TT c2 e FF c2/c10. A decisão técnica posterior de 25/11 aceitou as regras suplementares por evento para a candidata virtual, conforme [registro P2](phase3_p2_decisao_tecnica_20261125.md). Nenhum resultado bruto foi promovido a PASS.

Base local: branch `integration/phase3-danilo-ss`, HEAD `e15905237216098260774208305d8020fc1571e9`, com alterações locais preexistentes. A revisão começou em 25/11/2026 às 08:30, horário de Manaus. As fontes usadas e os resultados estão identificados por SHA-256 no [recibo de validação](../build/phase3/diagnostics/p2_revalidation_20261125T083047/validation_receipt.json) e no manifesto do diretório.

## Gerador e compatibilidade

O gerador foi executado novamente, em diretórios novos, para TT/SS/FF com idle em 247,5 ns e com o padrão de 247 ns. Na condição ajustada, cada corner reproduziu os oito hashes dos arquivos de entrada e o conteúdo integral do preflight existente. O padrão conservou o fixture histórico e a borda de 247 ns. Os seis valores inválidos testados — 244,05; 249,95; 243; 250 ns; NaN e infinito — foram rejeitados antes de criar saída.

Os hashes da PEX e do GDS foram recalculados nos próprios arquivos físicos do checkout histórico:

| Artefato | SHA-256 |
| --- | --- |
| PEX física v6 | `a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f` |
| GDS físico v6 | `315c2ebceb2bc4cf258fa63be2279843805db3010637d0c273aea9db12813e37` |
| Binding da candidata virtual | `d2151cac96a35a99b200764eec6ebbea517915d413cc1ddb8664a1dc7e247227` |

O executor passou novamente em `--check-only` nos três corners, conferindo os 319 arquivos de modelos de cada um no container EDA. O ambiente foi verificado por `./tools/sram-eda --check`. Os logs estão junto ao recibo.

## Replays e reprodução do observador

Foram reutilizados os três transientes completos e selados de 370 ns. A regeneração não alterou nenhuma entrada, e a reanálise reproduziu integralmente os resultados existentes; por isso não foi necessário repetir esses transientes. Esta rodada executou novas análises offline, sem novos transientes da candidata.

O observador foi executado novamente para cada corner, com `--topology virtual-eight`, referência explícita ao fixture de 247,5 ns e saídas isoladas em `observed/{TT,SS,FF}`. Os cinco arquivos de saída de cada corner — análise, ownership, observador histórico, tabela de ciclos e classificação — coincidiram por SHA-256 com os existentes: **15/15 arquivos idênticos**. A verificação conferiu também os hashes de onda, correntes, log, preflight e inventário de modelos contra os recibos.

| Corner | Operações | Lanes de leitura | c12 read→idle | Ownership bruto pendente |
| --- | --- | --- | --- | --- |
| TT | 18/18 PASS | 72/72 PASS | PASS | c2, bits 4/7 |
| SS | 18/18 PASS | 72/72 PASS | PASS | Nenhum |
| FF | 18/18 PASS | 72/72 PASS | PASS | c2, bits 1/2/4/7; c10, bits 1/2/3/4/5/7 |

Em cada corner, seleção de linha/modo/endereço passou nas 18 operações. As nove leituras cobrem oito lanes cada; regeneração, recuperação e retenção da saída até a captura seguinte passaram nas 72 lanes. As seis escritas têm readback nos pares de ciclos `2→6`, `3→7`, `4→15`, `5→16`, `8→9` e `10→11`, cobrindo as quatro linhas. Os gates de classificação, cobertura, integridade do recibo e replay P1 passaram.

Esses checks funcionais não qualificam todos os diagnósticos de corrente internos: o analisador conserva, por corner, 45 resultados `INCONCLUSIVE` de sobreposição de pré-carga sem sondas correspondentes, além de medições provisórias. Eles permanecem explícitos nos resultados e não são números finais de P5.

## Controles e suplementos

A [matriz revalidada](../build/phase3/diagnostics/p2_revalidation_20261125T083047/review_matrix_final.json) confirmou os sete controles físicos negativos e os controles positivos nativos SS c2, TT c10 e SS c10. Os negativos são host desligado e contenção no lado DUT em TT/FF c2; host desligado, liberação de leitura atrasada e host fraco persistente em FF c10.

Uma [verificação adicional](../build/phase3/diagnostics/p2_revalidation_20261125T083047/supplement_physical_controls.json) recalculou nas ondas dos controles as condições necessárias dos suplementos: host forte, gate da macro, quietude, oposição, desligamento do host fraco e liberação/isolamento da operação anterior. Os sete controles foram rejeitados nessas precondições. A verificação preservou os hashes das entradas e não transplantou uma liberação do evento natural para a onda com falha.

Os controles continuam sendo fatias diagnósticas de 70, 211 ou 230 ns. A rejeição de uma precondição nessas fatias não é uma aceitação integrada de 370 ns nem uma homologação do método estático. O script dessa análise está preservado junto ao relatório, em `check_supplement_controls.py`.

| Evento | Evidência que sustenta a proposta | Condição que falta para fechar P2 |
| --- | --- | --- |
| TT c2 | DATA estático esperado, macro isolada, host habilitado, quietude e controles negativos rejeitados | Homologar witness estático idle→write nos bits 4/7 e registrar a decisão do evento |
| FF c2 | Mesmas condições, com quatro lanes sem witness de carga | Homologar o mesmo método nos bits 1/2/4/7 e registrar a decisão do evento |
| FF c10 | Leitura anterior com condução/liberação, bridge de 14 amostras e estabilidade antes de CLK; controles negativos rejeitados | Homologar a regra específica read→write nos bits 1/2/3/4/5/7 e registrar a decisão do evento |
| TT/SS/FF c12 | Observador original PASS em todos, com pedido de idle em 247,5 ns | Registrar o perfil de 247,5 ns como protocolo de P2; o histórico de 247 ns conserva sua classificação |

O piso de 50 ps foi preservado. A regra idle→write não foi aplicada a FF c10. O plano exige homologação do witness e do protocolo; esta revalidação confirma as evidências para essa decisão, sem registrar aprovação em nome da equipe.

## Sequência restante

O critério de encerramento definido nesta revisão foi atendido pela decisão técnica de 25/11 para a candidata virtual, com os checks exigidos por corner e os vereditos brutos preservados. A matriz mantém a decisão da arquitetura e a PEX física final em **P3/P4**, sem tratá-las como dependências anteriores ao fechamento de P2.

P3 decide entre v6 híbrida e oito StrongARM e fecha as vistas físicas da escolha. P4 valida novamente no PEX final. P5 mede timing, potência, SNM Hold/Read e gera/valida Liberty. A candidata continua virtual em cinco lanes; `electrical_qualification=NOT_CHARACTERIZED` e `signoff_achieved=false`.

Havia uma campanha física v6 independente em execução serial (`phase3_replay_v6_integrated.py all`, TT em andamento quando esta revisão começou). Ela foi preservada. O host tinha aproximadamente 2,3 GiB disponíveis e swap bastante ocupada; não foi aberto outro simulador. Essa campanha não constitui uma decisão de arquitetura nem muda os vereditos da candidata.

## Correção do auditor FF c10

A continuação da revisão encontrou uma lacuna no auditor. Ele aceitava um trecho terminal de DATA estável até CLK mesmo que o pad ainda estivesse incorreto quando o host forte foi habilitado. O auditor agora verifica também o sinal esperado durante todo o intervalo host→CLK, além das janelas nativas já exigidas. A regressão injeta uma transição tardia e confirma que o caso é rejeitado. Os cinco testes direcionados do auditor passaram.

A análise FF c10 foi recalculada em uma saída nova. O resultado permanece `ELIGIBLE_FOR_PROTOCOL_REVIEW`, com as seis lanes no trilho desde a primeira amostra observada em 208,527893 ns até a subida de CLK em 210 ns. A decisão de protocolo continua pendente. O relatório revisado está em `build/phase3/diagnostics/p2_revalidation_20261125T083047/FF_c10_read_to_write_candidate_v2.json`, e a matriz atualizada em `review_matrix_v2.json`.

A regressão de análise não altera a onda original. A campanha física v6 continua serial. TT completou a simulação com 370 ns e 319 modelos verificados. Na atualização das 09h49 de Manaus, SS alcançou cerca de 288 ns de 370 e FF aguardava na fila serial. Análises de função e ownership da v6 serão registradas após os recibos, sem inferir o resultado apenas da simulação.


A decisão técnica subsequente fechou P2 para a candidata virtual no domínio nominal declarado. O relatório de decisão registra os limites e evidências e mantém os vereditos brutos inconclusivos. P3 seleciona tecnicamente a geometria v6; P4 valida sua própria identidade física e continua em andamento.
