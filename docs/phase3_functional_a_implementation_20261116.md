# Implementação modular do perfil funcional A — 16/11/2026

**Software implementado e testado; gate A completo desabilitado. Smoke não aprovado.**

Branch preservada: `feature/phase3-infra-leonardo`. HEAD antes/depois:
`ebf60a2725e8a40857323d3bbfd93c587ef52f77`. Sem commit, merge ou push.
Base documental: [decisão P3-DATA-001](phase3_data_verification_policy_decision_20261116.md),
[plano](phase3_functional_a_implementation_plan_20261116.md),
[proposta temporal](phase3_data_timing_contract_proposal_20261116.md) e
[contrato vigente](phase3_characterization_contract.md).

## 1. Resultado e alcance autorizado

Foi implementado `phase3_functional_a_v1` como opt-in de desenvolvimento.
O padrão continua `phase2_qualification_v1`. Nenhum JSON pode ativar A nesta
versão: `gate_enabled` deve ser exatamente `false`, O1–O4 devem estar PENDING e
`observation_windows` deve estar vazio. Uma aprovação futura requer revisão e
autorização próprias; não basta editar um flag ou deslocar uma janela.

O runner recusa execução real desse perfil com **BLOCKED/CLI 1 antes de iniciar
ngspice**. O dry-run mantém **NOT_CHARACTERIZED/CLI 0**, sem medidas ou waveform
novo. Foi exercitada uma tentativa bloqueada, não uma simulação elétrica.

A avaliação offline é separada do runner e tem `assessment_mode=replay`,
`electrical_simulation_performed=false`. Reutiliza waveforms arquivados com
hashes verificados. Não configura uma execução nova com um raw antigo nem altera
o significado de dry-run. A CLI de replay também retorna 1 para o perfil bloqueado.

## 2. Código e dependências

| Arquivo | Implementado |
|---|---|
| `tools/phase3/functional_a.py` — novo | Contexto estrito/versionado, estímulos conhecidos, avaliação parcial por requisito, bloqueios e agregação A/B; replay pinado |
| `tools/phase3/functional_a_coverage.py` — novo | Matriz A01–A12, identidades de cobertura, rejeição de duplicatas/omissões e mapeamento aditivo integral do legado |
| `tools/phase3/functional_a_observers.py` — novo | Monitor de intervalo fixo e retenção de Q entre readback agendado e próxima captura local; primitivas existentes de níveis/cruzamento |
| `tools/replay_phase3_functional_a.py` — novo | CLI offline, pin obrigatório do manifesto-fonte, diretório novo, snapshots de código e evidência de comparação |
| `tools/phase3/functional.py` — modificado | Despacho opt-in e validação comum de condições/seleção; caminho legado preservado |
| `tools/phase3/runner.py` — modificado | Bloqueio antes do simulador; snapshots dos módulos novos e metadados aditivos; proteção contra promoção de A/medições a B |
| `tools/prepare_phase3_4x8.py` — modificado | Opção `--profile`; mesma fixture/netlists/condições, contexto A separado; padrão legado |
| `tools/tests/test_phase3_functional_a.py` — novo | 43 testes, incluindo mutações sintéticas e integração controlada sem SPICE |

As equações, thresholds, guardas e corpos de `phase2_extension.check` e
`phase2_access_checks.check` não foram copiados nem alterados. O checker completo
continua fornecendo as observações de captura, armazenamento, leitura, corrente,
máscara e exclusão. Reutilizam-se `validate_trace`, `levels`, `crossing` e `valid`.
Apenas o monitor de retenção mais longo e a estrutura de política/cobertura são novos.

O contexto de A usa o campo público existente `functional_validation: {path,
sha256}`. Exige adapter/schema corretos, pins válidos, seleção e baseline
coerentes, além das mesmas condições nominais conferidas pelo adapter existente.
`selected_inputs` permanece responsável pela âncora Git e cadeia de proveniência.
Não houve novo seletor nem alteração do módulo de proveniência.

## 3. Cobertura implementada e partes bloqueadas

O inventário legado de comparação vem do `checks.json` **pinado** da qualificação,
usando identidades e metadados, nunca seus valores PASS como resultado do novo
exame. O resultado executado vem dos checkers sobre o raw em avaliação. As
identidades incluem propriedade, cenário, ciclo, linha, bit/sinal e janela/origem.
Duplicatas e identidades omitidas ou trocadas são recusadas mesmo com totais iguais.
Um tipo legado sem mapeamento válido impede completar a comparação.

A falta de borda local produz `local_capture_edge=FAIL` no checker existente,
em lugar do envelope daquele bit. O inventário reconhece essa alternativa como
a mesma oportunidade e conserva seu FAIL, sem eliminar o bit por falta do envelope.

No replay original, a cobertura ficou:

| Propriedade | Observações legadas mapeadas | Observações novas de Q | Oportunidades externas bloqueadas | Estado do requisito completo |
|---|---:|---:|---:|---|
| A01 — endereço/operação | 66 | 0 | 0 | BLOCKED por O4; observações PASS |
| A02 — escrita/dados conhecidos | 512 | 0 | 0 | BLOCKED por O4; observações PASS |
| A03 — captura de leitura | 144 | 0 | 0 | BLOCKED por O2/O4; observações PASS |
| A04 — retenção de Q | 376 | 72 | 0 | BLOCKED por O2; intervalos parciais PASS |
| A05 — retenção visível contínua | 40 | 0 | 40 | BLOCKED; sem nova janela de aceitação |
| A06 — direção/propriedade | 288 | 0 | 0 | BLOCKED por O2/O3; observações PASS |
| A07 — contenção | 56 | 0 | 0 | BLOCKED por O4; observações PASS |
| A08 — novas palavras externas | 144 | 0 | 72 | BLOCKED por O1/O2; pontos legados PASS |
| A09 — estabilidade externa | 0 | 0 | 72 | BLOCKED; primitiva de intervalo testada, sem ligação a janela aprovada |
| A10 — retomadas | 168 | 0 | 104 | BLOCKED por O2/O3; quatro FAILs legados pendentes visíveis separadamente |
| A11 — sequenciamento/captura | 162 | 0 | 0 | BLOCKED por O4; observações PASS |
| A12 — evidência/estímulo/inventário | Validadores próprios | — | — | PASS das validações estruturais e de identidade realizadas |

Uma observação pode fundamentar mais de uma propriedade; a soma da coluna não
é outro total de checks nem uma contagem de medições. A08 inclui os 72 readbacks
e 72 observações após retirada da sonda. Os 1.740 checks legados permanecem um
conjunto separado. A12 não fornece garantia elétrica nem supera os bloqueios.

`observation_status` resume somente as observações avaliáveis daquele requisito.
`legacy_status_counts` conserva todos os veredictos mapeados e
`pending_legacy_status_counts` explicita os ainda não adjudicados normativamente.
Assim, A10 não pode esconder os quatro FAILs atrás de observações de corrente PASS.
O mapeamento distingue read→read de retomadas, sem alegar que o nome do ciclo
sozinho prova continuidade de enable. A05 permanece bloqueada.

O monitor adicional de Q começa no **readback previamente agendado**, não no
primeiro instante válido encontrado em Q/DATA. Termina na próxima borda local
de captura, ou no fim declarado do transiente. Cobre writes, idle e máscaras
entre esses eventos e detecta corrupção que desaparece antes do próximo readback.
Os intervalos captura→readback continuam sem qualificação completa; não se
inventa atraso zero, hold, guarda ou deadline para fechá-los.

## 4. Estados e compatibilidade

- Erros de configuração, identidade, evidência ou inventário não produzem PASS.
  Nas falhas de completude após executar o observer, seus checks são preservados.
- Um FAIL nas observações funcionais avaliáveis ou na retenção adicional
  produz FAIL parcial de A mesmo com O1–O4 pendentes.
- Os FAILs da janela legada de DATA antigo permanecem FAIL no comparador;
  sua disposição normativa é PENDING, sem conversão em PASS.
- PASS de observações parciais não implica PASS de A. O resultado completo dos
  replays atuais é BLOCKED. A aprovação de máximos B segue NOT_CHARACTERIZED.
- Mesmo uma entrada hipotética medição PASS + função PASS não aprova B no
  agregador de desenvolvimento. Os estados/retornos públicos não foram ampliados.
- `policy_assessment` e `temporal_qualification` são metadados aditivos. O perfil
  legado mantém a agregação existente; `sram_characterized` permanece false.

**Correção editorial autorizada:** o CSV vigente tem **14 colunas**, na ordem:

```text
run_id,configuration,corner,vdd_v,temp_c,operation,metric,bit,value,unit,status,transition,measure,reason
```

`tools/phase3/contract.py`, unidades e schema não foram modificados. Foram
corrigidas exclusivamente as referências “15 colunas” na proposta temporal,
registro de decisão e plano, e acrescentada a explicação ao contrato da Fase 3.
Os três relatórios experimentais anteriores foram preservados byte a byte: as
menções a 15 neles devem ser lidas com esta errata, sem reescrever evidência histórica.

## 5. Testes e comandos efetivamente executados

Evidências em
[`reports/phase3/functional_a_dev_20261116_01/`](../reports/phase3/functional_a_dev_20261116_01/).
O [sumário consolidado](../reports/phase3/functional_a_dev_20261116_01/validation_summary.json)
contém argumentos, retornos, tempos e contagens por comando; os arquivos
`*.stdout.txt`/`*.stderr.txt` preservam as transcrições.

| Suíte consolidada | Testes | Resultado |
|---|---:|---|
| `test_phase3.py` | 6 | PASS |
| `test_phase3_revision.py` | 8 | PASS |
| `test_phase2_evidence.py` | 7 | PASS |
| `test_phase2_output_safety.py` | 1 | PASS |
| `test_phase2_extension.py` | 15 | PASS |
| `test_phase2_startup.py` | 7 | PASS |
| `test_phase2_protocol.py` | 6 | PASS |
| **Subtotal das suítes anteriores** | **50** | **PASS** |
| `test_phase3_functional_a.py` | 43 | PASS |
| `test_digital_regression_integration.py` | 6 | PASS, Icarus real em cópias temporárias |
| **Testes distintos consolidados** | **99** | **PASS, sem skips** |

Após explicitar os contadores de FAILs pendentes por propriedade, os 43 testes
novos foram reexecutados e passaram (`new_tests_final.stderr.txt`). Houve ainda
uma primeira rodada de 41 testes novos e 8 da revisão. Total efetivamente
executado nesta etapa: **191 execuções de testes**, incluindo repetições;
isso não significa 191 casos distintos. Nenhuma dessas suítes é caracterização SPICE.

Os testes novos cobrem corrupção temporária de Q, mudança na borda errada,
retenção durante idle/máscara, DATA errado com Q correto, driver ativo/ausente,
contenção inclusive com valores iguais, glitches entre observações e validade
somente instantânea. Exercitam janelas vazias/sem amostras suficientes, traces
incompletos/não finitos, inventário duplicado/omitido, tipo sem mapa, pins e
identidades divergentes, aprovação falsa e referências dependentes de DATA.

Para A05/A09, a primitiva de continuidade foi testada com janelas **sintéticas
explicitamente rotuladas**; sua ligação a janelas operacionais permanece bloqueada.
Setup/hold interno foi testado por mutação do envelope existente com referência
sintética isolada. Não se testou um limite público macro inexistente: a falta de
aprovação de O4 continua bloqueadora, sem número inventado.

Comandos representativos efetivamente usados, com destinos novos na ocasião:

```bash
python3 reports/phase3/functional_a_dev_20261116_01/run_validation.py

tools/sram-eda python3 -m unittest discover -s tools/tests \
  -p test_phase3_functional_a.py -v

tools/sram-eda python3 tools/prepare_phase3_4x8.py \
  --profile phase3_functional_a_v1 \
  --output reports/phase3/functional_a_dev_20261116_01/prepare_a

tools/sram-eda python3 tools/run_phase3.py \
  --config reports/phase3/functional_a_dev_20261116_01/prepare_a/config.json \
  --output reports/phase3/functional_a_dev_20261116_01/a_dry --dry-run

tools/sram-eda python3 tools/run_phase3.py \
  --config reports/phase3/functional_a_dev_20261116_01/prepare_a/config.json \
  --output reports/phase3/functional_a_dev_20261116_01/a_blocked

tools/sram-eda python3 tools/replay_phase3_functional_a.py \
  --run reports/phase3/smoke_sram4x8_20261113_01_real \
  --output reports/phase3/functional_a_dev_20261116_01/replay_original_complete \
  --manifest-sha256 6cc1d6efc804f293d4a421678c06494cab63aacfc2fe75ad3ac5022d39750cc7
```

Para repetir preparações, runner, replay ou transcrições, escolher destinos novos;
os diretórios existentes são recusados. O runner bloqueado e o replay retornaram
1 conforme esperado. Preparação e dry-run retornaram 0. Nenhum processo de
simulação elétrica foi iniciado; a consulta de versão no dry-run não é simulação.

## 6. Comparação reproduzida sem reescrever o histórico

O [replay original completo](../reports/phase3/functional_a_dev_20261116_01/replay_original_complete/functional_a_checks.json)
reproduziu, campo a campo, os **1.740 checks**, com **1.736 PASS/4 FAIL** e
**72 readbacks novos corretos**. Referência de captura e checks são idênticos
ao arquivo original. As 72 observações novas de intervalo de Q passaram,
mas o perfil completo continua BLOCKED. O manifesto original permanece
global FAIL e a CLI histórica permanece 1; nada recebeu aprovação retroativa.

O diagnóstico de 210 ns foi comparado separadamente pelo driver
`replay_diagnostic.py --output-name replay_diagnostic_complete.json`, sobre os
artefatos pinados do experimento original. Reproduziu **727 checks, 719 PASS e
8 FAIL, com 32 readbacks corretos**, preservando cada check. Não se apresentou
esse contexto curto como contexto nominal aprovado de 18 ciclos do adapter.
Seu runner histórico continua NOT_CHARACTERIZED/CLI 1, e os checks separados
continuam FAIL. O novo resultado parcial dessa comparação também é BLOCKED.

## 7. Integridade e arquivos documentais

O [inventário inicial](../reports/phase3/functional_a_dev_20261116_01/initial_integrity.json)
registrou 16.701 arquivos preexistentes, branch/HEAD e working tree antes das
alterações. A [auditoria final](../reports/phase3/functional_a_dev_20261116_01/final_integrity.json)
confere os hashes, diferenças autorizadas, checks originais e artefatos gerados.
Os únicos arquivos preexistentes alterados são os três módulos de integração
listados na seção 2 e os quatro documentos indicados na errata da seção 4.

Este relatório é o novo documento. A pasta de evidência contém scripts de
reprodução, inventários, contextos/preparação, manifestos, snapshots, comparação
e transcrições. Permanecem íntegros SRAM/netlists/layouts/GDS/fixtures/seletores,
verificadores compartilhados, testes anteriores e resultados experimentais.
Nenhuma alteração local preexistente foi descartada.

## 8. Pendências e prontidão para decisão de ativação

| Situação | Entrega/pendência |
|---|---|
| Implementado e testado | Validação/identidade, matriz, inventário, comparação integral, observações parciais reutilizadas, retenção adicional, primitivas de intervalo, estados/CLI e proteção do runner |
| Implementado, mas bloqueado | Estrutura de A05/A08/A09/A10, oportunidades por bit/ciclo e razões O1–O4; avaliação completa das demais propriedades não é promovida a PASS |
| Planejado, não implementado | Política operacional externa aprovada, arquivo de configuração com essas janelas, consumo de decisões aprovadas, gate A completo e qualificação B |
| Não executado | Nova simulação SPICE, smoke novo, caracterização PVT/timing/potência, geração Liberty |
| Dependente de aprovação externa | Conteúdo e alcance de O1–O4, cobertura operacional final e autorização de ativação |

As decisões exatas continuam:

1. **O1:** evento externo de uso da nova palavra — ponto de ensaio nominal,
   consumidor com captura/setup/hold ou limite `tREAD_VALID` aprovado.
2. **O2:** início/fim e exceções das janelas de estabilidade/atualização de Q/DATA,
   distinguindo operação normal e calibração; sem referência à acomodação observada.
3. **O3:** obrigação de visibilidade da palavra antiga após write/idle/máscara,
   referência e janela útil, se exigida; sem herdar ou substituir o prazo de 1 ns.
4. **O4:** precondições de captura e setup/hold do ensaio e classificação de
   estímulo inválido, distinguindo referência interna experimental de limite público.

A infraestrutura pode avançar à decisão final dessas políticas e à revisão do
escopo de ativação. **Não pode ativar ou aprovar A completo enquanto elas faltarem.**
Após a decisão será necessária uma alteração explícita e testada para consumir
o contrato aprovado. O smoke atual permanece não aprovado; B não está qualificado.
