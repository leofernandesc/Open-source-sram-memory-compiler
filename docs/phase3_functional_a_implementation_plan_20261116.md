# Plano do perfil funcional A — Fase 3 — 16/11/2026

Revisão **r0 — proposta de implementação, não implementada**.
Decisão relacionada: [P3-DATA-001](phase3_data_verification_policy_decision_20261116.md).
Base: `feature/phase3-infra-leonardo`, HEAD
`ebf60a2725e8a40857323d3bbfd93c587ef52f77`.

## 1. Escopo, prontidão e limites

Nome proposto: **`phase3_functional_a_v1`**, independente do legado
`phase2_qualification_v1`. O primeiro contexto será nominal, 4×8, TT/1,8 V/27 °C,
20 ns/50%, fontes de 50 ps, 10 fF/bit, extração devices/junctions e os 18 ciclos
pinados/370 ns. Não é um perfil PVT, de potência ou de sign-off da interface.

Este plano não cria código, configuração executável, fixture ou parâmetro temporal.
O artefato de política futura precisará de identificador, revisão e SHA-256
próprios. Esta revisão documental não preenche o lugar da aprovação exigida.

**Pronto para autorizar desenvolvimento limitado:** validação de contexto,
inventário, comparação de políticas, avaliadores das propriedades já definidas e
testes de software. **Bloqueado para ativar PASS de A completo:** decisões O1–O4
de observação externa e aprovação da cobertura/semântica de agregação. Um modo de
avaliação parcial deve expor os bloqueios e não se apresentar como perfil aprovado.

Referências de requisitos: [técnica](../specs/technical_specification.md),
[digital](../specs/sram_4x8_digital.md), [temporal](../specs/sram_4x8_timing_contract.md)
e [binding](../specs/phase2_physical_interface.md). A auditoria de autoridade e
história do deadline está na [proposta temporal](phase3_data_timing_contract_proposal_20261116.md).

## 2. Inventário existente e regra de reutilização

| Componente existente | Uso futuro, sem modificar os verificadores compartilhados |
|---|---|
| `phase3.provenance.selected_inputs` | Mesma âncora Git, seleção de candidato, hashes e arestas elétrica→fixture→extração |
| `phase2_extension.check` | Executar integralmente como comparação legada; preservar todos os checks e seu resultado |
| `phase2_access_checks.check` | Sequenciamento/exclusão e envelope de captura existentes, já chamados pelo checker acima |
| `run_phase2_startup_review.validate_trace/levels` | Reutilizar validação estrutural e níveis, incluindo rejeição de janela vazia |
| `analyze_phase2_extension_timing.crossing/valid` | Reutilizar observação de eventos/níveis quando sua semântica servir; um tempo de acomodação medido não inicia uma janela de aprovação |
| `phase3.functional.prepare_context/check_waveform` | Integração atual pinada, verificação de cabeçalho/cobertura e consumo de raw novo |
| `phase3.runner` e `run_phase3.py` | Timeout, recursos, snapshots, preservação de falhas, CSV/manifesto e CLI existentes |
| `run_digital_regression.py`, testbenches e mutantes existentes | Evidência lógica complementar, sem equivaler a observação elétrica de DATA |

Não copiar o corpo de `phase2_extension.check` para outra versão permissiva.
O novo avaliador deve ligar observações existentes a requisitos e implementar
somente propriedades ausentes, como continuidade sobre uma janela aprovada e
inventário de cobertura por identidade. Fatos reaproveitados devem registrar
origem, janela e limitações. Não basta selecionar os checks que passaram.

## 3. Matriz requisito → verificador → cobertura obrigatória

Os IDs A01–A12 abaixo são de rastreabilidade do perfil proposto, não requisitos
novos da especificação. “Cobertura” descreve oportunidades previstas, independentemente
do resultado PASS/FAIL. Cada oportunidade deve ser verificada mesmo se já houver
falha anterior. O denominador vem do plano pinado, nunca dos checks que sobraram.

| ID e requisito-fonte | Verificação objetiva / reutilização | Cobertura mínima obrigatória do contexto nominal |
|---|---|---|
| A01 — captura de endereço/operação; DIG-01/03/04, técnica §§4/6 | `captured_operation`, `captured_address`; comparar com pedido da subida, não com controles vivos posteriores | READ_Q/WRITE_Q em todos os 18 ciclos; 2 bits ADDR em cada um dos 15 acessos; todas as 4 linhas; READ/WRITE/inativo presentes |
| A02 — escrita; DIG-02/05, técnica §16 | `captured_write_data`, `known_storage`; scoreboard de palavras construído dos estímulos de escrita | 6 escritas × 8 bits; todas as linhas e reescritas de 0/1; preservar todas as células conhecidas após cada acesso, não apenas a linha lida |
| A03 — captura na descida; DIG-05, temporal §§3/4, binding sequência 4 | `local_capture_edge`, `output_ff_setup_hold_envelope`, `captured_ff_q`; associar cada bit ao clock local e à descida pública correspondente | 9 leituras × 8 bits; exatamente uma captura local correspondente por bit/ciclo; padrão que difere do Q anterior onde existe; monitor de atualização em borda errada |
| A04 — retenção interna; DIG-07/08 | `previous_ff_q_retained`, `mask_preserves_ff_q` e continuidade adicional de Q fora das janelas de atualização aprovadas | Todos os bits após primeiro read conhecido; atravessar read/write/idle/máscara; os 88 checks de retenção e 288 de máscara legados são testemunhos, não substituem cobertura contínua |
| A05 — retenção visível contínua; tabela Consecutive reads, temporal §4 | `previous_data_visible_before_new_capture` somente como observação legada contextualizada; monitor de DATA na janela contínua aprovada, comparando ao Q anterior esperado | Todos os bits em cada read→read elegível; linha igual e diferente; 5 pares/40 observações antigas no legado; habilitação e estabilidade do pino comprovadas, sem tratar retomada como continuidade |
| A06 — direção e propriedade; DIG-06/07, técnica §4 | `probe_observes_enabled_drive`, `masked_probe_current/voltage`, `restored_drive_current`, TE_B e controles; não inferir Z pela tensão sozinha | 9 leituras × 8 bits nas fases habilitada/mascarada/restaurada; Q não muda devido à máscara; modos write e idle não dirigem conforme seus intervalos legais |
| A07 — ausência de contenção; técnica §§4/16, temporal §6 | `no_strong_host_ebuf_overlap`, `strong_master_steady_current`; corrente e estados de driver independentes da correção da palavra | 8 bits em todo o trecho com host forte ativo; 6 escritas × 8 correntes estáveis; handoffs read→write com as duas guardas existentes; não ignorar sobreposição só porque ambos dirigem o mesmo valor |
| A08 — novas palavras corretas; DIG-05/11, técnica §15 | `read_data`, `captured_ff_q`, scoreboard independente e observação externa O1 | 9 leituras × 8 bits = **72 comparações externas obrigatórias**, além das 72 internas; quatro linhas, reescritas e leituras repetidas; palavra conhecida por escrita anterior |
| A09 — estabilidade elétrica; DIG-06/08 e tabela de leituras | Novo monitor de intervalo usando `levels`; não substituir pelo único ponto `sample_ns` | 8 bits em cada janela externa normal aprovada, antes/depois da captura onde aplicável; intervalos completos entre eventos, inclusive entre pontos de readback; sondas tratadas como calibração distinta |
| A10 — retomada após write/idle/máscara; DIG-06/07/08, temporal §§4/6/8 | Q retido, habilitação legal, recuperação da palavra correta e readback externo; separar recuperação de Q antigo de nova palavra; B registra prazo ainda não qualificado | Todas as retomadas existentes: 3 write→read, 1 idle→read e 9 restaurações de CSb; 8 bits, comutantes e não comutantes identificados; janelas O3 não definidas impedem fechar a propriedade |
| A11 — captura/recuperação interna segura; técnica §§6/8/14, binding | Preservar `one_hot_or_zero`, exclusão WL/WE/PRECH, `write_sense_exclusion`, prontidão baixa e envelope FF | Todas as 4 WL e todos os 18 ciclos; todas as leituras no envelope interno; margens de biblioteca TT/25 °C explícitas como referência, sem claim de setup/hold público |
| A12 — estado inicial, integridade e completude; DIG-09 e contrato Fase 3 | Rejeitar conteúdo inicial inventado, raw parcial, header/hash errado, checks ou intervalos ausentes | Condicionamento e todas as palavras conhecidas declarados; todos os probes/ciclos/identidades previstos presentes; escrita anterior para os 72 bits comparados |

A01 não estabelece um prazo macro de captura em 1 ns; reaproveita uma observação
de bancada cujo intervalo é explícito. A03 não exige que Q elétrico mude
instantaneamente no clock local. A04/A05/A09 dependem das fronteiras de atualização
e estabilidade aprovadas em O2; não são implementáveis integralmente apenas com
os checks pontuais atuais. A06/A07 comprovam condições ensaiadas, não máximos de
disable/turnaround. Corrente da sonda oposta é intencional e difere de contenção
entre drivers fortes.

O perfil inicial não promete cobertura elétrica das oito combinações de controle,
dos 64 pares de transições ou de todas as máscaras individuais. O contexto pinado
usa `001`, `010`, `111` e máscara CSb. As regressões digitais existentes cobrem
as oito combinações, quatro linhas e alterações de entradas, mas não substituem
SPICE desses modos. Para ampliar o alcance declarado do perfil, criar outro
contexto aprovado e sua cobertura; nunca considerar cenário ausente como PASS.
Não há autorização aqui para modificar ou estender a fixture.

## 4. Contrato de observação externa: fatos e bloqueios

### 4.1 Eventos que já têm fundamento

| Evento | Definido pela arquitetura | Pode ser usado agora como garantia externa? |
|---|---|---|
| CLK50↑ público | Referência do pedido/escrita; setup/hold públicos pendentes | Não inicia automaticamente prazo de 1 ns para DATA |
| CLK50↓ público | Referência da captura de leitura | Não significa DATA novo válido exatamente nessa borda |
| Clock local do FF | Captura física correspondente, com CTS/inversão | Ponto interno; não é o clock de um consumidor externo |
| Atualização de Q após captura | Resultado armazenado até outro read | Relação funcional definida; atraso Q não fornece sozinho instante válido no pino |
| Enable lógico e TE_B local | Determinam condução/recuperação pelo buffer | Cruzamento TE_B50 é diagnóstico; não prova impedância nem palavra válida |
| Nova palavra em DATA após descida e propagação | Obrigação funcional existente | Precisa de ponto/janela de uso para uma decisão elétrica finita |
| `sample_ns` da fixture | Observação previamente agendada, primeira amostra em/apos esse tempo | Evidência limitada ao ponto de bancada; não limite público |

No contexto de 18 ciclos, `sample_ns = rise_ns+11` (queda PWL+1), não
CLK50↓+1. Como a rampa é 50 ps, há diferença de 25 ps. Os momentos existem antes
do waveform e podem sustentar comparação, mas sua existência não aprova uma nova
política. Amostragem deve registrar tempo-alvo, índice, tempo efetivo e tensão;
não interpolar um nível inválido para obter um lógico válido.

### 4.2 Janelas já existentes e o que realmente comprovam

Em relação ao início da subida PWL, o checker atual usa:

| Janela/ponto legado | Papel | Limitação para A |
|---|---|---|
| `[+1; +9,5]` | Estado capturado, Q e DATA antigo | Deadline de acomodação do pino após retomada não fundamentado como máximo público |
| `+11` | Nova palavra no pino e Q | Só um ponto; estabilidade posterior não pode ser deduzida dele |
| `[+12; +12,35]` | Condução com sonda oposta | Calibração carregada, não leitura normal sem perturbação |
| `[+13,2; +13,8]` | Saída mascarada, corrente/tensão de liberação | Prova na janela, não tempo máximo de disable |
| `[+14,7; +15,2]` | Corrente de condução restaurada | Não é garantia de recuperação da palavra inteira |
| `+16,3` | DATA após retirada da sonda | Ponto de bancada; não caracterização universal de enable |

A sonda é ativada em `+11,5`, máscara em `+12,5`, restauração em `+14` e retirada
em `+15,5`, com as transições do deck. Estes valores são **existentes e não foram
alterados**. O1/O2 precisam distinguir janela normal e calibração. Subtrair do
waveform todos os trechos perturbados e declarar estabilidade plena seria errado:
os trechos de calibração mantêm suas próprias obrigações de corrente/Q/propriedade.

### 4.3 Decisões exatas O1–O4

| ID | Decisão que falta | Alternativas admissíveis e consequências |
|---|---|---|
| O1 — nova palavra externa | Qual é o evento de uso da nova palavra e qual é o alcance da garantia? | **O1a:** adotar formalmente os pontos já agendados da fixture como contrato de ensaio nominal, com alegação limitada; **O1b:** definir consumidor externo e seu evento/setup/hold; **O1c:** qualificar e aprovar `tREAD_VALID` antes do gate. O1a é o menor caminho para software limitado, sem equivaler a O1b/c |
| O2 — estabilidade/atualização | Onde começam/terminam as janelas normais de DATA/Q e as exceções físicas de captura/máscara? | Para O1a, propor fronteiras derivadas dos eventos **de estímulo** pinados, com fase normal até a perturbação seguinte e fases de calibração separadas; aprovar início e retomada de cada janela. Para O1b/c, usar a janela do consumidor/orçamento. Não usar `settle(DATA)` para iniciar o PASS, nem excluir um intervalo arbitrário em torno da falha |
| O3 — retomada da palavra antiga | Exige-se uma janela visível antes da nova captura após write/idle/máscara? Se sim, qual referência, prazo e intervalo? | **O3a:** aprovar obrigação nominal de ensaio e janela independente de DATA; **O3b:** definir máximo B por arco e janela útil mínima, se requerida. Se só se decidir observar a nova palavra, a recuperação anterior deve continuar explicitamente não qualificada; não pode receber PASS como propriedade completa A10 |
| O4 — captura e integridade do estímulo | Como julgar setup/hold e as janelas de propagação sem números públicos aprovados? | Manter estímulos pinados e envelope conservador interno já existente como evidência nominal; distinguir violação da precondição do teste de defeito do DUT. Limites públicos ou consumidor novo exigem qualificação/decisão separada; nunca substituir por setup/hold isolado do FF |

**Recomendação para a próxima decisão:** discutir O1a com O2 inteiramente
especificado como perfil nominal limitado, mantendo B NOT_CHARACTERIZED. Resolver
explicitamente O3; não herdar o início `+1` das retomadas nem prometer um intervalo
pré-captura que ainda não foi aprovado. Registrar O4 como referência experimental
limitada. Esta recomendação não escolhe valores ou cria janelas executáveis.

Sem O1/O2, não há contrato seguro para A08/A09. Sem a disposição de O3, A10 está
aberta. Q correto e 72 readbacks corretos não removem esses bloqueios. Se O3 for
mantida integralmente pendente, uma avaliação parcial é possível, mas não PASS
do perfil completo definido neste plano.

## 5. Definição executável futura do perfil e da cobertura

Usar o campo público existente `functional_validation: {path, sha256}`. O contexto
apontado declarará o novo adapter; o validador do novo adapter será separado do
legado. Não criar campos extras na configuração raiz, que hoje é estrita.

O contexto proposto deverá conter, com validação estrita por versão:

- Identificador/revisão do perfil, base Git e seleção retornada por
  `selected_inputs`, pins dos mesmos deck/netlist/modelo e probes/receipts.
- Referência/hash da política aprovada e das decisões O1–O4; pendência não pode
  ser preenchida com `approved=true` sem registro de decisão verificável.
- Plano de observação independente de DATA: evento, palavra esperada, ciclo/bit,
  domínio, referências pública/local/PWL, início/fim e inclusividade das janelas,
  tratamento das transições e razão de cada fase de calibração.
- Inventário esperado por A01–A12, com identidades únicas
  `(propriedade, cenário, ciclo, linha, bit/sinal, janela)` e multiplicidades.
  Se uma propriedade for por palavra, registrar também o resultado dos oito bits.
- Domínio B e orçamentos somente quando aprovados; ausências permanecem ausências.

Comparar conjuntos de identidades e cobertura temporal com o inventário **antes
de agregar**. Duplicatas, janela vazia, trecho truncado, probe ausente, denominador
reduzido ou check não executado são ERROR de evidência, não PASS. Janela que chega
ao fim do raw sem cobrir o intervalo prometido é incompleta. Não preencher
lacuna por interpolação de linhas faltantes. A resolução declarada limita a
detecção de glitches; o perfil deve registrar a discretização e não alegar
detecção de pulsos menores que a resolução do transiente.

O plano de janelas deve aceitar somente referências declaradas de estímulo,
CLK público/local e controles previstos, com parâmetros aprovados. Não aceitar
expressões executáveis nem referências a acomodação/primeira validade de DATA/Q
como início automático do PASS. Determinar continuidade pelo histórico de enable
no intervalo e pelo plano, não apenas por `operation` do ciclo anterior; uma
máscara dentro de um read cria uma retomada própria.

Dados conhecidos vêm das escritas dos estímulos, não de Q/DATA observado. Ler
endereço nunca escrito não autoriza esperar zero. O contexto inicial não contém
esse cenário elétrico; manter a evidência de desconhecido no modelo digital e
exigir contexto adicional para qualquer claim elétrico correspondente.

### 5.1 Comparação explícita com os 1.740 checks

Rodar o checker legado completo em paralelo lógico à nova avaliação, no mesmo
raw/contexto quando compatível, e salvar seu resultado integral. Não alterar sua
contagem, thresholds, janelas ou interpretação. Não mudar seu estado para PASS.

Criar um mapa aditivo de **todas** as observações legadas para requisitos/contextos:
reutilizada por A, evidência auxiliar/calibração, ou hipótese temporal de bancada
sem máximo público. A classificação é metadado revisado, não um novo estado CLI.
Um check de tipo não mapeado impede aprovação da comparação. Mesmo tipo pode ter
papéis diferentes: `previous_data_visible_before_new_capture` em read→read
continuamente habilitado não recebe a disposição de uma retomada write→read.

A avalia a própria matriz com propriedades adicionais e cobertura própria.
Reutilizar uma observação exige conservar sua origem e janela. Não calcular A
como `legado - checks falhos` ou `legado - tipo previous_data...`. Falha legada
que evidencia obrigação funcional de A deve reaparecer como FAIL de sua propriedade.
Uma falha temporal não adjudicável contra B continua visível, com B não qualificado.

Evidência futura sugerida: `functional_a_checks.json`, `legacy_comparison.json`
e `policy_assessment.json`, em diretório novo reservado pelo runner. Cada
propriedade registra fonte normativa, esperado/observado, tempo/janela, origem,
status, motivo e hash do raw. Registrar modo `fresh_run` ou `replay` quando
aplicável; replay em teste offline nunca equivale a nova simulação elétrica.

### 5.2 Estados, agregação e CLI sem incompatibilidade

| Situação | Tratamento proposto para o novo perfil |
|---|---|
| Falta decisão O1–O4 indispensável | BLOCKED do perfil, identificado antes de uma nova execução; sem PASS parcial disfarçado |
| Evidência/header/hash/cobertura inválida | ERROR; preservar todos os defeitos já observados e evidência parcial |
| Violação funcional demonstrada sob estímulo legal | FAIL de A; B pendente não absorve a falha |
| Estímulo viola setup/hold ou propriedade do mestre | Não adjudicar como FAIL do DUT; ERROR de ensaio ou BLOCKED se a precondição não puder ser definida; registrar separadamente a violação |
| A completo PASS, B sem orçamento/qualificação | A PASS, B NOT_CHARACTERIZED; global NOT_CHARACTERIZED, CLI real 1 |
| Valores de `.meas` válidos sem máximo B aprovado | Medição PASS; B continua NOT_CHARACTERIZED |
| Dry-run concluído | Sem execução/medições; NOT_CHARACTERIZED, CLI 0 |
| Erro de argumento/destino recusado | Preservar retorno 2 da CLI |

Propor metadados aditivos para perfil/escopo e `temporal_qualification` no manifesto,
mais evidência separada; revisar consumidores antes de adotá-los. CSV de 14 colunas
e unidades não mudam. Checks funcionais não são linhas numéricas fictícias.

O agregador atual conhece medição e função; não conhece aprovação de B. Portanto,
no caminho novo, **mesmo medição PASS + A PASS não basta para PASS global**:
incluir explicitamente B como gate separado, preservando o comportamento legado.
Manter precedência de erro de evidência, FAIL demonstrado e bloqueio; preservar
resultados de cada gate. `sram_characterized` permanece false; este perfil não
autoriza sua promoção. Não adicionar estados ou exit codes novos.

## 6. Testes positivos e negativos projetados

São testes futuros de software/modelo, rotulados como tais. Mutar cópias em
memória ou arquivos temporários dos testes, nunca netlists, raw ou recibos
históricos. Um teste de software que detecta corretamente um FAIL pode passar;
isso não é aprovação elétrica do DUT mutado. Nenhum destes testes foi executado
nesta etapa documental.

| ID | Estímulo/mutação | Detecção e resultado exigidos |
|---|---|---|
| P01 | Referência correta, todas as janelas e identidades presentes | A PASS no contrato de teste aprovado; B ausente continua NC/global NC |
| P02 | Todos os 18 ciclos e 72 readbacks do contexto, incluindo mesmos/diferentes endereços | Cobertura exata por propriedade; observações do pino e internas distintas |
| P03 | Complementos AA/55, 00/FF, walking bits e bits sem transição nos testes dos observers | Oito bits, ambos os sentidos; estável não recebe propagação zero |
| N01 | Inverter Q brevemente entre readbacks, durante write/idle ou máscara | A04 FAIL, mesmo se Q se recuperar antes da amostra final |
| N02 | Atualizar Q/DATA na subida em vez da descida, com palavras distintas | A03/A04/A05 FAIL; nenhum guard pode esconder a atualização de meia fase |
| N03 | Perder retenção de DATA antigo em read→read mantendo enable | A05/A09 FAIL; não classificar como recuperação após write |
| N04 | Q correto e pino errado, bit trocado ou driver ausente | A08/A06 FAIL; apenas observar Q nunca aprova |
| N05 | Glitch dentro de janela contínua entre dois pontos legados | A09 FAIL; exercitar interior e fronteiras da janela, sem aumentar tolerância |
| N06 | Driver SRAM ativo com máscara/idle/write | A06 FAIL quando o estímulo é legal; tensão correta/flutuante não comprova liberação |
| N07 | Sobreposição SRAM/host forte, inclusive ambos com mesmo valor | A07 FAIL por estado de enable e corrente; separar fixture ilegal deliberada em teste negativo |
| N08 | DATA correto somente na amostra agendada e inválido antes/depois dentro da janela de uso | A09 FAIL; pontos isolados não aprovam estabilidade |
| N09 | FF_D sai da faixa válida dentro do setup/hold interno existente; perturbação fora versus dentro | Envelope interno FAIL dentro; caso legal fora não falha por limite inventado. Referência TT/25 °C explícita |
| N10 | Endereço/controle/DIN externo viola precondição temporal declarada do ensaio | Ensaio inválido detectado; não alegar caracterização dos limites macro sem orçamento aprovado |
| N11 | Omitir bit/ciclo/janela/probe, duplicar check, produzir intervalo vazio ou raw truncado | ERROR; nenhuma redução de denominador nem PASS vacuamente verdadeiro |
| N12 | Falta O1/O2/O3; orçamento B ausente; valores `.meas` todos numéricos | BLOCKED de A sem decisão; NC de B sem limite; nunca global PASS por métricas válidas |
| N13 | Início de janela calculado por `settle(DATA)`, ou exclusão ampliada até o glitch desaparecer | Rejeitar plano dependente do resultado; teste deve provar que a mutação não muda a janela esperada |
| N14 | Modelo, candidato, seletor, contexto ou decisão adulterados; hash local refeito sem âncora aprovada | ERROR/BLOCKED conforme contrato atual; baseline/proveniência continuam vinculantes |
| N15 | Mesma palavra após enable mas buffer em Z; tensão preservada pela carga | A06 FAIL pela sonda/corrente; não fabricar atraso zero |
| N16 | O3 aprovado e palavra antiga não recupera na janela; nova leitura eventualmente correta | Propriedade de retomada FAIL; sucesso de A08 não oculta a falha de A10/B |

Também conservar os testes de CLI real NC→1 e dry-run NC→0, timeout, ausência de
métrica, falha funcional com medidas válidas e impedimento de sobrescrita. Reexecutar
a suíte de **50 testes** da revisão anterior e os mutantes digitais existentes
pertinentes; a tabela não é substituto de execução ou evidência desses testes.
Violações públicas de setup/hold sem limites definidos não podem receber resultado
elétrico normativo fabricado; N09/N10 têm alcances distintos.

## 7. Arquivos e implementação mínima futura

Todos os caminhos abaixo são **propostos**, não alterados ou criados nesta etapa.

| Arquivo | Alteração futura necessária |
|---|---|
| `tools/phase3/functional.py` | Despacho explícito por adapter; preservar ramo legado; integrar validação/resultado do novo módulo |
| `tools/phase3/functional_a.py` (novo) | Matriz, plano de observação aprovado, cobertura e monitores ausentes; reutilização das primitivas existentes |
| `characterization/phase3/functional_a_v1.json` (novo, após decisões) | Política fixa: requisitos, janelas, domínio e inventário independente; nada derivado de um PASS observado |
| `tools/prepare_phase3_4x8.py` | Opção explícita para novo perfil/contexto; padrão continua legado; mesmos estímulos e netlists; contexto pinado separado |
| `tools/phase3/runner.py` | Snapshot de todos os novos módulos/decisões/políticas; sidecars e metadados aditivos; agregação B explícita no ramo novo |
| `tools/tests/test_phase3_functional_a.py` (novo) | Positivos, negativos, cobertura, distinção de políticas e observação externa |
| `tools/tests/test_phase3_revision.py` e/ou `test_phase3.py` | Regressões de integração/CLI sem remover casos atuais |
| `docs/phase3_characterization_contract.md` | Só após aprovação: seção aditiva para perfil novo, escopo/gates e evidências; manter descrição do legado |

`tools/phase3/contract.py` não precisa de campo raiz ou métrica fictícia nova;
`tools/run_phase3.py` não precisa mudar os códigos de retorno. O módulo de
proveniência pode ser reutilizado sem alteração. Se a revisão de implementação
demonstrar necessidade diferente, justificar antes de mudar o contrato.

Permanecem fora da lista: células, netlists, layouts, taps, fixtures/recibos,
seletores, `phase2_extension.py`, `phase2_access_checks.py`, demais verificadores
compartilhados e especificações normativas. Nenhum hash histórico será atualizado
para fazer uma versão nova parecer a antiga.

## 8. Migração e compatibilidade

1. Registrar decisão operacional sobre O1–O4 e aprovar a matriz/escopo. Manter
   B sem valores até qualificação independente; aprovar a separação A/B no manifesto.
2. Implementar opt-in e testes de software em alcance autorizado. Perfil ausente
   ou adapter legado não deve ativar A; configuração inválida falha fechada.
3. Validar em testes offline comparações usando cópias ou leitura dos raws
   arquivados. Evidência nova de replay identifica o run-fonte/hash, sem dizer
   que houve SPICE e sem executar o runner como se o raw fosse novo.
4. Comparar os dois perfis explicitamente. Exigir igualdade integral do replay
   legado original: **1.736 PASS/4 FAIL**, 72 leituras, CLI histórica 1/global FAIL.
   Preservar também 719 PASS/8 FAIL do caso curto e sua distinção de execução
   manual do checker versus adapter automático não configurado.
5. Autorizar separadamente um ensaio real futuro se necessário para homologação
   integrada. Usar novo diretório; nenhum ensaio é autorizado por este plano.
6. Somente após aprovação e regressões, permitir o perfil novo como gate
   funcional dentro do alcance declarado. Não alterar automaticamente o padrão
   legado, os pins da baseline ou os critérios antigos. Publicação/commit exige
   instrução própria.

O contexto curto de 210 ns não cabe no adapter legado de 18 ciclos/370 ns.
Não falsificar recibo para aceitá-lo; um replay de teste deve fornecer seu próprio
contexto exato e não ampliá-lo silenciosamente ao alcance de A nominal inicial.

## 9. Critérios de aceitação da implementação futura

- Decisões O1–O4 resolvidas para o alcance reivindicado; janelas fixadas antes
  de observar DATA; requisitos e limites pendentes explicitamente identificados.
- Matriz A01–A12 completa, pino e nós internos observados, inventário exato e
  todos os negativos demonstrando detecção; nenhuma exclusão motivada por falha.
- Preservação integral dos resultados/checkers históricos, sem filtro por
  status/tipo, sem alterações de limiar/deadline e sem reciclar PASS de outro run.
- Os 50 testes anteriores continuam PASS; testes novos cobrem política, comparação,
  resolução, hashes/snapshots, falhas parciais e estados/CLI. Registrar comandos,
  transcrições e resultados reais; caso não executado permanece não executado.
- Configuração raiz, CSV de 14 colunas e estados/retornos atuais compatíveis;
  medição PASS com B NC nunca produz caracterização global PASS no novo ramo.
- Evidência por propriedade e gate, perfis/hashes explícitos, denominadores
  preservados e arquivos antigos byte a byte intactos. Replay identificado como tal.
- Aceitação do software não é aceitação elétrica: se homologação integrada real
  não tiver sido autorizada/executada, registrar essa limitação, sem claim de PVT,
  Liberty, setup/hold público ou SRAM caracterizada.

## 10. Resultado desta preparação

Foram consultados a especificação, os contratos, os quatro documentos anteriores,
o preparador, runner, observers e testes existentes. Foram preparados somente este
plano e o registro P3-DATA-001, seguindo documentos datados em `docs/`.

Não houve código, fixture, deadline ou evidência histórica alterados. Não foram
executados testes automatizados, replay, SPICE, PVT ou Liberty nesta etapa; os
50 PASS permanecem evidência anterior, sem uma nova alegação de execução. Não
houve commit, merge ou push.

Conferências documentais realizadas: links locais dos dois entregáveis válidos,
ausência de whitespace final, HEAD inalterado, diff dos arquivos rastreados vazio
e 607 hashes de arquivos preexistentes do inventário conferidos sem divergência.
Essas verificações de integridade não são execução da suíte de software nem
validação elétrica do perfil proposto.

**Prontidão:** a proposta permite autorizar trabalho modular e testes de software
com escopo limitado. **Não está pronta para ativar o novo gate funcional completo**
enquanto O1/O2/O3 e a disposição de O4 não forem aprovadas. A direção A+B está
selecionada; os critérios que fariam DATA passar ou falhar não estão implicitamente
aprovados. O smoke original continua FAIL, sem aprovação retroativa.
