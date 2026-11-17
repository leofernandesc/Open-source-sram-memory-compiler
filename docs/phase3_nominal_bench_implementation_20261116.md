# Implementação experimental de P3-DATA-002 — 16/11/2026

**Pronta para revisão da política nominal; sem homologação ou aprovação global.**
Branch `feature/phase3-infra-leonardo`, HEAD preservado
`ebf60a2725e8a40857323d3bbfd93c587ef52f77`. Usado o estado local da implementação
A anterior, sem reverter suas alterações ou modificar seus arquivos.

## 1. Resultado executivo

Foi preparado o perfil experimental **`phase3_nominal_bench_v1`**, isolado do
legado e do perfil A bloqueado. A [proposta P3-DATA-002 r0](phase3_data_operational_policy_proposal_20261116.md)
concretiza O1a, janelas O2, desdobramento A10 e precondições O4. Sua aprovação
permanece **PROPOSED**; `global_gate_enabled=false` é obrigatório.

Resultados da rodada final:

| Evidência | Resultado |
|---|---|
| Regressões de software | **142 testes PASS, sem skips: 99 existentes + 43 novos** |
| Nova tabela executável | **626 observações** por sinal/bit/ciclo/janela; todas PASS no replay |
| Nova palavra externa | 72 bits no ponto S; também 72 observações pós-sonda no ponto T, corretas |
| Retomadas A10-F | 104 vínculos funcionais completos; PASS no alcance experimental |
| Retomadas A10-E | 104 oportunidades registradas; **NOT_CHARACTERIZED**, sem deadline |
| Perfil nominal experimental | `nominal_functional_status=PASS`, `status=BLOCKED`, CLI 1 |
| Perfil A anterior, reaplicado sem mudança | BLOCKED |
| Perfil legado no mesmo raw | **1.740 checks: 1.736 PASS/4 FAIL**, intactos |
| Simulação elétrica nova | **Não executada**; somente replay do waveform pinado de 13/11 |

PASS nas observações não equivale a aprovação do proprietário, PASS do smoke
histórico, nova simulação ou sign-off elétrico. B permanece não qualificado.

## 2. Arquivos criados e isolamento

| Arquivo novo | Finalidade |
|---|---|
| `characterization/phase3/nominal_bench_v1.json` | Política r0 pinada: domínio nominal, eventos, regras, recuperação sem orçamento e ausência de aprovação |
| `tools/phase3/nominal_bench_plan.py` | Auditoria da fixture PWL, correspondência com registros, compilação independente de resultados e inventário obrigatório |
| `tools/phase3/nominal_bench.py` | Pontos/janelas, níveis existentes, resolução/completude, precondições observáveis, agregação e classificação aditiva |
| `tools/review_phase3_nominal_bench.py` | CLI exclusivamente offline; manifesto-fonte pinado, snapshots, plano, resultados e hashes em diretório novo |
| `tools/tests/test_phase3_nominal_bench.py` | 43 regressões positivas/negativas da política e de suas fronteiras |
| `docs/phase3_data_operational_policy_proposal_20261116.md` | P3-DATA-002 r0: autoridade, decisões, tabela temporal e aprovações necessárias |
| Este relatório | Resultado, matriz, limitações e reprodução |

Não foi necessário modificar nenhum arquivo preexistente. Não se registrou esse
perfil no preparador/runner: a execução operacional continua indisponível nesta
etapa de revisão. `phase2_qualification_v1` permanece como padrão;
`phase3_functional_a_v1` continua recusando ativação enquanto suas decisões
formais estiverem pendentes. A avaliação nova não muda esses contratos.

Os observers da Fase 2 e o avaliador A são reutilizados integralmente. Não se
copiou ou alterou seu corpo para retirar falhas. A nova camada acrescenta planos
e observações, conservando a comparação completa do legado e o resultado A.

## 3. Plano executável e precondições

A política canônica tem SHA-256
`cd8f9d83ca3141d2768055d65846962c4d969ee36c50924964f61128fd7181f6`.
O validador recusa alterações de condições, aprovação, regras ou deadlines;
é uma versão fixa de bancada, não uma DSL livre para escolher janelas.

O arquivo `observation_plan.json` da rodada final contém:

- 626 identidades próprias com referência, início/fim, inclusividade, sinal/bit,
  esperado obtido dos estímulos e requisitos vinculados.
- Eventos de cada leitura, mudanças reais de controles/driver e fases de atualização,
  sonda, máscara e recuperação; pontos PWL repetindo o mesmo valor não criam máscaras.
- As 27 janelas de calibração existentes, com bounds inclusivos e seus tipos de
  check, executados pelo observer legado sem alteração.
- 104 oportunidades de recuperação por cenário/ciclo/bit, todas sem prazo elétrico.
- Fontes PWL utilizadas na validação de precondições.

Todos os novos limites são programados. O plano é compilado **antes** de usar
DATA/Q para julgar os níveis. Nenhum começo de janela vem de `settle`, primeira
amostra correta ou máximo medido em TT. O ponto observa a primeira amostra
disponível em/depois do instante agendado; se ela estiver errada, não procura
outra correta. Se não houver amostra antes da próxima fase, a evidência é inválida.

As janelas normais verificam DATA, TE_B ativo baixo e READ_Q ativo alto. Q deve
reter o resultado até a captura seguinte; o monitor A existente complementa os
limites públicos programados com a referência local do FF, independente de DATA.
Bits esperados sem mudança mantêm a obrigação de nível válido durante a atualização:
20 intervalos adicionais de Q e 12 de DATA. Não recebem atraso zero fictício.

O4 confronta a programação de CLK/comando/endereço/payload com o receipt e os
platôs observáveis de 14 fontes com o raw. As rampas PWL são tratadas como rampas,
sem guarda nova. ADDR externo não foi salvo nesse contexto; sua programação pinada
é confrontada com ADDR_Q. Isso não é medida de setup/hold analógico externo.
As capturas e o envelope interno conservador TT/25 °C são reavaliados como screens
experimentais, sem atribuir limites públicos à macro TT/27 °C.

São recusados intervalos vazios, pontos ausentes, janelas com uma única amostra,
IDs omitidos/duplicados, requisitos retirados de uma identidade, raw não finito,
tempo não crescente ou lacunas superiores ao passo declarado. O ajuste de
quantização na verificação de passo deriva do formato numérico do wrdata; não
altera limiares elétricos ou tempo de recuperação permitido.

## 4. Matriz A01–A12 proposta para o perfil de bancada

Os resultados abaixo são **experimentais**, sob uma política ainda PROPOSED.
Não substituem o estado do perfil A anterior.

| Propriedade | Implementação / efeito O1–O4 | Observações próprias adicionais | Resultado no replay |
|---|---|---:|---|
| A01 — pedido/endereço | Observações internas existentes + auditoria PWL e precondições O4 | 0 | PASS nominal |
| A02 — escrita/dados conhecidos | DIN_Q/células e scoreboard existentes, sem conteúdo inicial fabricado | 0 | PASS nominal |
| A03 — captura de leitura | Captura/envelope existentes; Q no ponto S; 20 bits estáveis durante F→S | 92 | PASS nominal; setup/hold público NC |
| A04 — retenção de Q | Monitor A existente; 72 intervalos programados + 20 intervalos de bits estáveis | 92 | PASS nominal |
| A05 — retenção visível contínua | Intervalos que atravessam read→read sem mudança de enable, incluindo bits estáveis na captura | 52 | PASS nominal |
| A06 — direção/propriedade | Corrente/máscara existentes; 144 observações de TE_B e 18 de READ_Q nas novas janelas | 162 | PASS nominal; máximos disable/enable NC |
| A07 — contenção | Todos os checks existentes de sobreposição/host e corrente preservados | 0 | PASS nominal |
| A08 — palavras externas | Pontos S e T existentes, com índices/tempos efetivos registrados | 144 | PASS nominal, sem `tREAD_VALID` garantido |
| A09 — estabilidade externa | Intervalos após S e T + 12 bits estáveis durante F→S | 156 | PASS nominal |
| A10 — retomadas | Parte funcional nos 32 bits write/idle→read e 72 bits de máscara; parte elétrica separada | 104 | A10-F PASS; A10-E NOT_CHARACTERIZED |
| A11 — sequência interna | Exclusão/pré-carga/WL/sense e captura existentes, sem alterar timing | 0 | PASS nominal |
| A12 — integridade/cobertura | Identidade, hashes, contexto, inventário e resolução completos | Validações próprias | PASS dessas verificações |

Uma observação pode sustentar mais de um requisito; não somar a coluna como
medições ou como nova contagem de checks legados. O perfil possui 626 IDs próprios.

As fases sem obrigação de tensão normal de DATA são explícitas na proposta:
propagação de bits que mudam após captura, sonda/calibração e recuperação sem
orçamento B. Elas não dispensam retenção interna, captura, direção/corrente,
ausência de contenção nem os pontos agendados. Uma palavra errada nesses pontos
ou glitch dentro da janela válida continua FAIL.

## 5. Legado, A10 e estados

O comparador conserva todos os 1.740 checks, seus índices e seus PASS/FAIL.
Uma classificação nova é guardada separadamente, identificada como proposta.
Os 40 checks legados de palavra anterior em read→read têm correspondência com
as novas janelas A05 contínuas. Os 24 de retomadas com Q anterior conhecido
continuam consultáveis como observação temporal legada; os quatro FAILs de
c11/bits 0/2/4/6 não desaparecem nem viram PASS retroativo.

A10 agora possui, **neste perfil experimental**, `functional_status` separado
de `electrical_recovery`. A10-F exige os eventos corretos de leitura/direção;
A10-E registra 104 oportunidades e `deadline_ns=null`. Seu `status` permanece
NOT_CHARACTERIZED quando só a parte funcional passa. Isso formaliza a mudança
de alcance proposta, sem eliminar a recuperação do inventário.

Os oito FAILs adicionais do diagnóstico curto permanecem nos arquivos originais.
Não foram reapresentados como contexto válido desse perfil de 18 ciclos.

Estados/CLI:

- FAIL funcional demonstrado prevalece sobre proposta pendente; uma precondição
  de estímulo inválida é ERROR de ensaio, com as evidências mantidas.
- Com observações corretas, o perfil experimental continua **BLOCKED**, pois não
  há aprovação operacional e B não está qualificado. A CLI retorna **1**.
- Argumento/pin inválido ou destino recusado conserva a convenção de retorno **2**.
- Runner/dry-run legados e o CSV de **14 colunas** permanecem inalterados.

## 6. Testes e evidência reproduzível

Diretório de evidência:
[`reports/phase3/nominal_bench_dev_20261116_01/`](../reports/phase3/nominal_bench_dev_20261116_01/).
Ambiente final: container existente `sram-xschem`, launcher `tools/sram-eda`,
Python 3.10.12 e NumPy 1.26.4; versões registradas em
[`environment.json`](../reports/phase3/nominal_bench_dev_20261116_01/environment.json).
O ngspice não foi executado nesta etapa; o simulador do waveform-fonte é o
ngspice 44.2 registrado no manifesto original.

| Rodada final | Testes | Resultado |
|---|---:|---|
| Suítes anteriores da infraestrutura/revisão Fase 2/3 | 50 | PASS |
| `test_phase3_functional_a.py` | 43 | PASS |
| `test_digital_regression_integration.py` | 6 | PASS, Icarus em cópias temporárias |
| **Subtotal dos testes existentes** | **99** | **PASS** |
| `test_phase3_nominal_bench.py` | **43** | **PASS** |
| **Total final distinto** | **142** | **PASS, sem skips** |

Foram exercitados DATA errado, primeira amostra errada seguida de correta,
glitches entre pontos, validade só instantânea, retenção corrompida, driver ativo
indevido, contenção e bits estáveis com glitch durante captura. Também foram
testadas fronteiras inclusivas/exclusivas, amostra imediatamente após o limite,
intervalos/pontos ausentes, duplicação/omissão de IDs e requisitos, fontes
inválidas, hash, domínio PVT/carga e tentativa de atribuir deadline ou aprovação
à proposta. Nenhuma passagem numérica em TT promove B ou o resultado global.

As mutações de software são sintéticas e rotuladas. Os checks de corrente,
captura, Q e contenção já existentes continuam abrangidos pelas 99 regressões,
pelas mutações adicionais e pelo replay sem alteração dos verificadores.

Ocorrências durante o desenvolvimento, mantidas em transcrições próprias:

1. Primeira rodada nova: 40 testes, uma falha de teste na fronteira fechada. O
   timestamp construído por multiplicação era ligeiramente **após** o limite.
   Corrigida a construção para testar a fronteira exata e acrescentado o caso
   imediatamente posterior; o avaliador não ganhou tolerância.
2. A extensão para bits estáveis inicialmente recusou o plano por contagem
   esperada incorreta. A conferência dos registros mostrou row2=`0x0F` e
   row3=`0xF0`, não valores iguais. Foram corrigidos o total esperado e os testes
   para **20 Q/12 DATA, 626 IDs**, sem mover janelas ou alterar padrões.
   A rodada intermediária teve erro de preparação da classe de plano e replay
   ERROR, corretamente sem aprovação; os casos dessa classe não executados
   naquela rodada foram executados na rodada final.
3. As demais rodadas estão registradas: 41 testes novos PASS; consolidação de
   140 PASS anterior à extensão; 126 testes executados na rodada intermediária
   não concluída; preflight de 43 PASS; e rodada final de 142 PASS.
   Ao todo foram **532 execuções de testes, incluindo repetições**, não 532 casos
   distintos aprovados. As falhas intermediárias não foram apagadas.

O [sumário final](../reports/phase3/nominal_bench_dev_20261116_01/validation_final/validation_summary.json)
registra comandos/retornos/contagens. O
[resultado nominal](../reports/phase3/nominal_bench_dev_20261116_01/validation_final/replay_final/nominal_assessment.json)
e o [plano executado](../reports/phase3/nominal_bench_dev_20261116_01/validation_final/replay_final/observation_plan.json)
permitem conferir cada janela, amostra e requisito. O comparador e a avaliação
A original ficam em arquivos separados no mesmo diretório.

Comandos efetivamente utilizados:

```bash
python3 reports/phase3/nominal_bench_dev_20261116_01/run_validation.py \
  reports/phase3/nominal_bench_dev_20261116_01/validation_final

tools/sram-eda python3 -m unittest discover -s tools/tests \
  -p test_phase3_nominal_bench.py -v

tools/sram-eda python3 tools/review_phase3_nominal_bench.py \
  --run reports/phase3/smoke_sram4x8_20261113_01_real \
  --output reports/phase3/nominal_bench_dev_20261116_01/validation_final/replay_final \
  --manifest-sha256 6cc1d6efc804f293d4a421678c06494cab63aacfc2fe75ad3ac5022d39750cc7
```

Usar novos destinos para repetir; os existentes são recusados. O último comando
retornou 1 com estado BLOCKED, como esperado. Nenhum desses comandos executa SPICE.

## 7. Integridade, pendências e parecer

O inventário inicial registrou **24.892 arquivos preexistentes** e o estado Git.
A [auditoria final](../reports/phase3/nominal_bench_dev_20261116_01/final_integrity.json)
verificou **zero arquivos preexistentes alterados**, fonte pinada, igualdade integral dos
checks legados, planos, snapshots e manifestos novos. Nenhum arquivo anterior
precisou ser alterado: inclusive os módulos A não commitados e todos os seus
resultados permanecem byte a byte preservados. HEAD não foi avançado.

Permanecem dependentes de sua aprovação os cinco itens da seção 6 de P3-DATA-002:
alcance O1a, fronteiras O2, separação A10-F/E e classificação aditiva O3,
precondições/limitações O4 e autorização de ativação operacional. A proposta
torna essas decisões concretas; não declara que já foram homologadas.

Validade contínua desde enable antes dos pontos adotados, máximos de
enable/disable/turnaround/read, setup/hold público, outros domínios e PVT seguem
não qualificados. São bloqueios para garantias elétricas, sem parâmetro inventado
para fechá-los. Não há necessidade de inventar outra janela para o alcance
nominal restrito proposto; uma exigência de integração adicional precisa de
decisão e orçamento próprios.

**Parecer:** a política e o software estão prontos para revisão e eventual
homologação **funcional nominal limitada**, apoiada pelo replay rastreável.
Falta aprovação explícita para ativá-la como gate e decidir a evidência de
homologação operacional futura. Não houve novo smoke elétrico, PVT ou Liberty,
commit, merge ou push. O smoke histórico continua FAIL; B continua não qualificado.
