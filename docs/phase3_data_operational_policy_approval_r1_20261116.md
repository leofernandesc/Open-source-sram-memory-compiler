# P3-DATA-002 r1 — aprovação do contrato funcional nominal

**Estado: APPROVED_NOMINAL_BENCH — autorização de integração e teste opt-in.**
Revisão datada de 16/11/2026, na branch `feature/phase3-infra-leonardo`,
HEAD de referência `ebf60a2725e8a40857323d3bbfd93c587ef52f77`.

## Autoridade e condição de homologação

A autoridade desta decisão é a instrução explícita do usuário nesta sessão:

> Aprovo a política P3-DATA-002 r0 exclusivamente como contrato funcional de
> bancada nominal, dentro do domínio e das condições documentadas.

> Autorizo implementar e testar a ativação operacional opt-in do perfil
> phase3_nominal_bench_v1, condicionado à aprovação das regressões e de uma
> nova execução real.

A instrução aprova O1a, O2, O3 e O4 no alcance abaixo. Isso autoriza a
implementação e o smoke limitado após regressões aprovadas. Não antecipa o
resultado da execução nem constitui sign-off elétrico. A homologação funcional
será registrada em relatório separado somente com regressões e evidência nova.

## Preservação da revisão original

A [proposta r0](phase3_data_operational_policy_proposal_20261116.md) é preservada
integralmente, SHA-256
`f2cf919649a396fd00d107d4a2a8c845328bd8347aaf9eddaee537ae469667c2`.
A [política executável r0](../characterization/phase3/nominal_bench_v1.json)
também é preservada, SHA-256
`cd8f9d83ca3141d2768055d65846962c4d969ee36c50924964f61128fd7181f6`.
Esta r1 é um registro novo, não uma reescrita das aprovações ou resultados antigos.

## Contrato aprovado

- **O1a:** pontos S e T preexistentes, primeira amostra em/depois do alvo e
  antes da próxima fase. Não procurar amostra correta nem prometer `tREAD_VALID`.
- **O2:** exatamente as janelas, inclusividade e tratamento de transições da
  r0, incluindo bits estáveis na captura: **626 oportunidades**. O plano é
  pinado por hash canônico; não se autorizam deslocamentos de eventos ou guardas.
- **O3:** A10-F exige retenção, direção, ausência de contenção e palavras nos
  eventos aprovados. A10-E conserva 104 oportunidades NOT_CHARACTERIZED, sem
  deadline de 1 ns nem qualquer outro máximo garantido de recuperação.
- **O4:** programação PWL, precondições, integridade e capturas conforme fixture
  existente. Envelope interno do FF é screen experimental TT/25 °C contra o
  ensaio TT/27 °C, sem equivalência a setup/hold público da macro.

Domínio: SRAM 4×8, SKY130A, TT, 1,8 V, 27 °C, clock 20 ns/50%, slew 50 ps,
10 fF por bit, extração devices/junctions selecionada, 18 ciclos/370 ns,
6 escritas/9 leituras/3 ciclos inativos e os mesmos controles/sondas. Não são
autorizados novo circuito, netlist, layout, fixture, RC distribuído ou PVT.

O contexto deve fixar candidato/baseline, deck/modelo/netlist, aprovação r1,
documento de autoridade, plano e dependências dos avaliadores. Aprovação não
é obtida editando flags da r0. Contextos desconhecidos, adulterados, sem pins,
com plano/cobertura diferente ou provenientes de replay são recusados.

## Relação entre perfis e resultados

`phase2_qualification_v1` continua como padrão. `phase3_functional_a_v1`
preserva seu bloqueio original. A integração r1 aplica-se exclusivamente ao
opt-in `phase3_nominal_bench_v1` com contexto novo de execução real; a avaliação
offline r0 continua separada, rotulada replay, sem promoção a execução elétrica.

Devem permanecer independentes: simulador, função nominal, qualificação B e
resultado global. Mesmo com função PASS e medidas numéricas PASS, B pendente
impede PASS global. CSV de 14 colunas, cinco estados e códigos CLI são preservados.
O dry-run não simula nem mede; a execução real não caracterizada retorna 1.

O legado é executado integralmente no waveform novo para comparação explícita.
Seus veredictos não são filtrados nem reescritos; a nova avaliação funcional usa
os requisitos aprovados e conserva a classificação aditiva por contexto.
O smoke antigo 1.736 PASS/4 FAIL e o diagnóstico 719 PASS/8 FAIL permanecem
imutáveis, com os manifestos e hashes antigos. Não há aprovação retroativa.

## Limitações e dependências

Não há limites B aprovados de enable, disable, turnaround ou leitura; setup/hold
público, timing e potência continuam não caracterizados. Não há garantia PVT,
RC distribuído, Fmax, margem estatística ou fabricação. O ensaio não cobre
todas as combinações de controle nem todas as máscaras. ADDR externo é auditado
pela fonte pinada e por ADDR_Q, sem probe externo salvo nesse contexto.

Liberty exige métricas reais qualificadas posteriormente; não é gerado aqui.
Qualquer expansão de domínio, orçamento B ou alteração do plano exige nova
decisão. Não se autoriza commit, merge ou push nesta etapa.
