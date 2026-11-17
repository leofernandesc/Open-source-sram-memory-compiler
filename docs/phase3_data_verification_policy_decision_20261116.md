# Decisão P3-DATA-001 — separação funcional/temporal de DATA

Revisão documental: **r0, 16/11/2026**. Registro local preparado para revisão;
não há implementação nem commit associado a esta revisão.

Branch conferida: `feature/phase3-infra-leonardo`. HEAD:
`ebf60a2725e8a40857323d3bbfd93c587ef52f77`.

## 1. Estado e autoridade

**Direção técnica selecionada: A+B**, conforme a solicitação desta etapa.
**Critérios operacionais do novo perfil: pendentes de aprovação.** Este registro
documenta a seleção da direção; não constitui assinatura, homologação ou aprovação
final do proprietário do projeto. Não há aprovador final registrado neste documento.

A política vigente e seus resultados continuam válidos como registros históricos.
Nenhuma especificação, fixture, deadline, circuito ou verificador é alterado aqui.
O [plano de implementação](phase3_functional_a_implementation_plan_20261116.md)
define o trabalho futuro e os bloqueios de ativação do novo gate.

## 2. Motivação e fontes

A [proposta temporal](phase3_data_timing_contract_proposal_20261116.md) distingue
retenção de Q, visibilidade do pino, recuperação após enable e chegada da nova
palavra. Elas não são o mesmo evento. O caminho real contém FF, mux de retenção
e ebufn; o clock local do FF tem atraso/inversão relativamente ao CLK público.

Fontes de autoridade preservadas:

- [Especificação técnica](../specs/technical_specification.md), §§4/6/15/16:
  interface, captura na subida, leitura registrada na descida e propriedade do bus.
- [Contrato digital](../specs/sram_4x8_digital.md), DIG-01…11 e tabela de leituras
  consecutivas: retenção de Q e DATA enquanto ambos os enables permanecem ativos.
- [Contrato temporal público](../specs/sram_4x8_timing_contract.md), §§3/4/6/8/9:
  atrasos físicos existem; máximos públicos de leitura/enable/disable/turnaround
  estão pendentes. Não se prescreve um intervalo numérico arbitrário.
- [Binding físico](../specs/phase2_physical_interface.md): captura local,
  setup/hold interno, exclusão WL/WE/pré-carga e liberação antes do próximo acesso.
- [Contrato operacional da Fase 3](phase3_characterization_contract.md), revisão
  de 13/11: o perfil legado exige todos os 1.740 checks e separa simulador,
  medição e verificação funcional. Essa exigência não é revogada por este registro.

Evidências experimentais consultadas, sem nova simulação ou análise de waveform:

| Evidência nominal TT/1,8 V/27 °C | Resultado preservado | Interpretação limitada |
|---|---|---|
| [Smoke original](phase3_first_sram_smoke_20261113.md), 370 ns/40.507 amostras | 1.736 PASS, 4 FAIL; 72 novas leituras corretas; global FAIL, CLI 1 | DATA antigo ainda inválido no começo da janela de bancada após escrita |
| [Diagnóstico da janela](phase3_data_window_diagnostic_20261113.md) | Q retido; 40 checks read→read PASS; quatro falhas write→read, bits pares de c11 | Não demonstra corrupção de Q nem falha das novas palavras nos pontos avaliados |
| [Qualificação de enable](phase3_data_enable_qualification_20261113.md), 210 ns | 719 PASS, 8 FAIL; 32 novas leituras corretas; 16 medidas nativas | Confirma o mecanismo com padrões complementares; não qualifica um máximo |

TE_B50→DATA50 foi ≈0,134 ns em descida e ≈0,229 ns em subida. A palavra antiga
voltou a ser válida ≈1,098 ns após CLK50, com ≈9,123 ns de estabilidade observada
até a captura. São observações nominais, não limites de projeto ou tolerâncias novas.

A origem rastreada do check de DATA antigo em `rise_ns+1` é `c46e611`, usando
uma janela já empregada por observadores anteriores (`94256a5`/`9445169`). O
contrato público criado em `9445169` já deixava o atraso pendente. A unidade
`1ns` da biblioteca não fornece esse deadline. A cronologia e comandos de Git
estão na proposta temporal, §3; não foram reinterpretados como aprovação.

## 3. Alternativas consideradas e direção selecionada

| Alternativa | Avaliação |
|---|---|
| Manter 1 ns como obrigação elétrica pública | Sem fundamento normativo ou caracterização de máximo; permanece apenas no diagnóstico legado vigente |
| A apenas, conferindo Q ou um único readback | Insuficiente: pode perder driver errado, glitches e DATA válido só instantaneamente |
| B apenas, aumentar o prazo até passar | Sobreajuste aos ensaios; não assegura semântica síncrona, retenção ou propriedade |
| **A+B, resultados independentes e rastreáveis** | **Selecionada como direção**: mantém função e interface observável, com qualificação dos máximos separada |

## 4. Política funcional A recomendada

O novo perfil deverá verificar captura única de endereço/operação/escrita,
memória esperada independente do DUT, captura de leitura na descida correspondente,
retenção de Q, retenção visível em leitura continuamente habilitada, direção,
ausência de contenção, palavra nova correta e estabilidade de DATA nas janelas
aplicáveis. Deve observar **o pino elétrico**, além dos nós internos.

As janelas devem derivar de um contrato de observação aprovado antes do ensaio,
não do instante em que DATA finalmente passa no waveform. Recuperação após
write/idle/máscara continua no inventário obrigatório, com suas fronteiras
funcionais e temporais explícitas. Não é permitido apagar a propriedade ou
eliminar todo um intervalo de leitura porque nele existe uma falha.

PASS funcional A só será possível com cobertura própria completa, evidência
válida e todas as propriedades funcionais obrigatórias satisfeitas. Uma lacuna
de contrato impede esse PASS; resultados internos parciais não aprovam a SRAM.

## 5. Obrigações B e contrato externo pendentes

Permanecem sem máximo qualificado `tDATA_ENABLE`, `tDATA_DISABLE`,
`tTURNAROUND`, `tREAD_VALID`, setup/hold públicos e a recuperação da **palavra
correta** após enable. Começar a conduzir não equivale a estar em 20%/80%, nem
a apresentar o resultado de uma nova leitura. Não se atribui valor a nenhum deles.

A especificação justifica a descida como **captura interna**, não como instante
de validade externa imediata. Justifica a ordenação “captura → Q → buffer → DATA”,
mas não define um consumidor externo nem um atraso universal para amostragem.
Os pontos e sondas da fixture existente são eventos de bancada reproduzíveis;
não são automaticamente garantias de interface.

Falta aprovar exatamente: **qual palavra deve estar válida, em qual evento
externo previamente definido, durante qual intervalo e sob quais condições de
direção/carga**, distinguindo retomada da palavra antiga de nova leitura. As
opções admissíveis e suas consequências estão no plano, decisões O1–O4. Sem
essa escolha, a ativação de um gate A completo permanece bloqueada.

## 6. Compatibilidade e consequências

Não se muda a arquitetura, portas, clock, células, retenção de Q nem o handoff
legal do mestre. A SRAM não deve manter a palavra antiga no pino enquanto o
mestre escreve; deve reter Q internamente. Leituras continuamente habilitadas
continuam exigindo retenção visível nas suas janelas legais.

O perfil legado `phase2_qualification_v1` permanece íntegro. O identificador
proposto `phase3_functional_a_v1` designa outra política, não uma renomeação dos
1.740 checks. O plano exige comparação explícita, matriz de requisitos,
inventário de cobertura independente e testes negativos. Reutilizam-se os
observers e primitivas existentes; não se copiam equações para afrouxá-las.

CSV de 14 colunas, `schema_version=1` e os cinco estados públicos permanecem.
PASS de medição não implica B qualificado. Futuro PASS de A com B pendente deve
continuar sem PASS global de caracterização: NOT_CHARACTERIZED, CLI real 1.
Dry-run completo continua NOT_CHARACTERIZED/0, sem simulação ou medidas.

Qualificação B futura precisa definir arcos, referência pública, 50% para eventos,
faixas funcionais, carga/slew, extração, domínio, orçamento e margem aprovados.
Não se extrapola TT/27 °C para PVT nem envelope do FF TT/25 °C para setup/hold macro.

## 7. Aprovações necessárias antes de implementar/ativar

| Decisão | Situação desta revisão | Condição para avançar |
|---|---|---|
| Direção A+B | Selecionada na solicitação | Sem novos valores ou mudança automática dos gates |
| Evento e intervalos externos O1–O4 | Pendente | Escolha concreta e versionada; sem resposta derivada de DATA |
| Escopo, matriz e cobertura do perfil A | Propostos no plano | Revisão dos critérios e das lacunas, inclusive estímulos ausentes |
| Classificação normativa aditiva do legado | Proposta | Aprovar mapa por requisito/contexto; nunca alterar resultados históricos |
| Estrutura de evidência e agregação A/B | Proposta | Revisão de compatibilidade, snapshots e CLI antes da implementação |
| Máximos B e domínio garantido | Pendentes de caracterização/aprovação | Não bloqueiam o desenho do software; bloqueiam qualificação elétrica |
| Execução de mudanças de software | Não autorizada por esta etapa documental | Autorização posterior com alcance definido |

É possível preparar implementação de validação, identidade, cobertura, comparação
e testes de software após autorização de escopo. Não é seguro ativar o gate
funcional completo com as decisões externas ainda abertas. Nenhuma ação de
implementação, simulação ou aprovação retroativa é consequência automática
da seleção A+B.

## 8. Preservação e ligação com o plano

O smoke original conserva **1.736 PASS/4 FAIL, global FAIL e CLI 1**. As oito
falhas adicionais conservam seu registro separado. A interpretação normativa
proposta é aditiva; tensão inválida permanece inválida e o deadline antigo
continua reproduzível. Uma aprovação futura de outro perfil não altera o run antigo.

Os três relatórios e a proposta de 16/11 eram arquivos locais preexistentes;
foram preservados. A organização adotada continua sendo documentos datados em
`docs/`, como os registros de decisão já presentes, sem criar um novo mecanismo
de release ou assinatura. O plano vinculado contém matriz, observação, módulos,
testes, migração e critérios de aceite. Nenhum teste de software ou SPICE foi
executado nesta preparação documental; os 50 PASS citados são históricos.
