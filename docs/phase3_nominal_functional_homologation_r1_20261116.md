# Homologação funcional nominal — P3-DATA-002 r1 — 16/11/2026

**Veredito: infraestrutura funcional nominal homologada no escopo aprovado.**
**Caracterização elétrica global: NOT_CHARACTERIZED; CLI real 1.**

Branch `feature/phase3-infra-leonardo`; HEAD preservado
`ebf60a2725e8a40857323d3bbfd93c587ef52f77`. Não houve commit, merge ou push.
O estado local anterior foi preservado; os arquivos protegidos da SRAM e as
evidências históricas não foram alterados.

## 1. Política, autoridade e limites

A [aprovação P3-DATA-002 r1](phase3_data_operational_policy_approval_r1_20261116.md)
registra a autorização explícita do usuário nesta sessão para O1a/O2/O3/O4 e
integração opt-in, condicionada a regressões aprovadas e um smoke real novo.
Ambas as condições foram atendidas nesta etapa.

Política executável:
[`nominal_bench_v1_r1.json`](../characterization/phase3/nominal_bench_v1_r1.json),
SHA-256 `ea5da44896590c71f0ddb11cd23c91084c9acbec0d5a550371ed31799674a8d4`.
Seu plano r0 aprovado tem hash canônico
`6eba5203cca52a101aab3e785e45a9fb0665dd358e8b8cd11000c73dda8241ec`.
R1 altera autoridade/integração; não muda os eventos, janelas, limiares ou as
626 oportunidades funcionais aprovadas.

A [proposta r0](phase3_data_operational_policy_proposal_20261116.md) permanece
byte a byte intacta, SHA-256
`f2cf919649a396fd00d107d4a2a8c845328bd8347aaf9eddaee537ae469667c2`;
a política JSON r0 conserva
`cd8f9d83ca3141d2768055d65846962c4d969ee36c50924964f61128fd7181f6`.
Não há aprovação retroativa dos runs anteriores nem mudança da especificação
normativa da SRAM. A homologação é da infraestrutura e do contrato **nominal de bancada**,
sem sign-off elétrico, PVT ou fabricação.

## 2. Arquivos e integração

| Arquivo | Alteração nesta etapa |
|---|---|
| `docs/phase3_data_operational_policy_approval_r1_20261116.md` | Novo registro versionado da autoridade, escopo e condições |
| `characterization/phase3/nominal_bench_v1_r1.json` | Nova política aprovada, com pins da r0, autoridade, plano, modelo e dependências |
| `tools/phase3/nominal_operational.py` | Novo adapter r1: validação, proveniência, evidência fresca e avaliação nominal |
| `tools/prepare_phase3_4x8.py` | Opt-in nominal r1; template canônico compartilhado entre preparo/validação; padrão legado mantido |
| `tools/phase3/functional.py` | Despacho nominal r1; caminhos legado e A anterior preservados |
| `tools/phase3/runner.py` | Snapshots, prova de execução nova, integração da avaliação e gate B separado |
| `tools/tests/test_phase3_nominal_operational.py` | 23 novos testes positivos/negativos de integração |
| Este relatório | Homologação, comparação, matriz e pendências |
| `reports/phase3/nominal_homologation_20261116_01/` | Scripts, logs, preparação, dry-run, novo smoke, snapshots e auditorias |

O padrão continua `phase2_qualification_v1`. `phase3_functional_a_v1` conserva
seu bloqueio original; seus módulos não foram modificados. O replay experimental
r0 continua separado e não é promovido a execução elétrica.

O contexto r1 é estrito, versionado e pinado. Confere a política aprovada, documento
de autoridade, candidato/baseline, modelo/netlist, deck canônico e plano exato.
Editar um plano e recalcular seu hash local não substitui o hash aprovado.
Alterações de domínio, comandos de leitura/cópia de raw antigo, modelo, seleção,
contexto de replay ou versões desconhecidas são recusadas.

Para o caminho real, o runner reserva um diretório novo, verifica ausência de
waveform antes do subprocesso e registra um marcador de filesystem e prova de
conclusão do simulador. O adapter exige essa prova e o waveform regular criado
na janela de execução. Os hashes são conferidos novamente após a avaliação.
Um replay não fornece a prova exigida por esse caminho.

## 3. Regressões realizadas antes do smoke

| Suíte | Testes | Resultado |
|---|---:|---|
| `test_phase3.py` | 6 | PASS |
| `test_phase3_revision.py` | 8 | PASS |
| `test_phase2_evidence.py` | 7 | PASS |
| `test_phase2_output_safety.py` | 1 | PASS |
| `test_phase2_extension.py` | 15 | PASS |
| `test_phase2_startup.py` | 7 | PASS |
| `test_phase2_protocol.py` | 6 | PASS |
| `test_phase3_functional_a.py` | 43 | PASS |
| `test_digital_regression_integration.py` | 6 | PASS |
| `test_phase3_nominal_bench.py` | 43 | PASS |
| **Subtotal preexistente** | **142** | **PASS** |
| `test_phase3_nominal_operational.py` | **23** | **PASS** |
| **Rodada final** | **165** | **PASS, sem skips** |

Evidência: [sumário de regressão](../reports/phase3/nominal_homologation_20261116_01/regression_summary.json)
e transcrições por suíte no mesmo diretório. A rodada inicial de integração teve
21 testes e uma falha no próprio teste: um mock global de Popen interceptou o
Git, além do simulador. O mock foi limitado à chamada batch de ngspice; uma
segunda rodada teve 22 PASS e a rodada final teve 23 PASS. As transcrições foram
preservadas. No total, 208 execuções de testes incluindo repetições, não 208 casos
distintos nem simulações elétricas.

Os novos testes cobrem autoridade/pins, perfil desconhecido/não aprovado, condições
incompatíveis, janela/limites/cobertura adulterados mesmo após rehash, dependências
ausentes e preservação dos documentos históricos. Rejeitam prova ausente, arquivo
antigo/symlink, contexto de replay e comandos para carregar raw anterior.
Verificam dry-run sem processo batch, separação B, FAIL/ERROR preservados e
impossibilidade de PASS global mesmo com função e medições PASS.

As regressões anteriores continuam exercitando corrupção temporária de Q,
borda incorreta, DATA errado com Q correto, glitches entre pontos, driver
indevido, contenção inclusive com valores iguais, validade instantânea, bits
estáveis durante captura, precondições e omissão/duplicação de cobertura.
Mutações e subprocessos falsos são testes de software isolados, não evidência
elétrica da SRAM. A execução elétrica descrita abaixo é distinta desses testes.

## 4. Novo smoke real

Diretório exclusivo:
[`approved_smoke_real/`](../reports/phase3/nominal_homologation_20261116_01/approved_smoke_real/).

| Item | Condição/resultado |
|---|---|
| Circuito | SRAM 4×8, candidato de abutment selecionado pela cadeia de release existente |
| Baseline | `origin/release/phase2-acceptance-20261111`, commit `89901e7e258b6955f6752163b918a296079466fa` |
| Netlist | `qualification_v1/binding.spice`, SHA-256 `f4b502bcf1c99fb18d02ebad712878ebf83c0a4cec04987d2dce3d9645baa510` |
| PDK/corner | SKY130A / TT |
| VDD / temperatura | 1,8 V / 27 °C |
| Clock / slew | 20 ns, duty 50%, transições de 50 ps |
| Carga | 10 fF por bit DATA |
| Extração | Devices/junctions selecionada; sem RC distribuído |
| Sequência | Fixture pinada, 18 ciclos, 370 ns |
| Simulador | ngspice 44.2, um CPU/thread, limites de memória/tempo existentes |
| Duração do runner | Aproximadamente 1.028,7 s |
| Dados produzidos | **40.507 amostras**, 154 colunas incluindo tempo |
| Simulador | **PASS**, código do subprocesso **0** |
| Função nominal r1 | **PASS**, **626/626** observações e 14 precondições de fontes PASS |
| Novas palavras | **72/72** bits nos pontos S; **72/72** observações após sonda em T |
| Qualificação B / medidas | **NOT_CHARACTERIZED**, sem medidas configuradas ou valores artificiais |
| Caracterização global | **NOT_CHARACTERIZED**, `sram_characterized=false` |
| CLI real | **1**, conforme esperado |

O deck preparado foi comparado byte a byte com o do smoke original e é idêntico.
O netlist/circuito e os estímulos não foram ajustados para eliminar falhas.
O dry-run anterior retornou 0 com `electrical_simulation_performed=false`;
o run real registrou `electrical_simulation_performed=true` e produziu seu próprio
arquivo, log e prova de execução.

SHA-256 do waveform novo:
`1a7670edaa2be0202c1861f053864dcd5f93b24ed727117dd2a6385c7893feae`.
Ele coincide com o arquivo antigo: o mesmo circuito/estímulo reproduziu os mesmos
bytes. **Isso não foi usado como prova de frescor.** Os arquivos têm inodes e
timestamps distintos; o diretório novo não existia no inventário inicial, o
simulador foi iniciado após as regressões e o waveform foi gerado entre o
marcador de início e a conclusão do novo subprocesso. A
[auditoria de frescor](../reports/phase3/nominal_homologation_20261116_01/freshness_audit.json)
e `execution_proof.json` documentam essa distinção.

As evidências incluem [manifesto](../reports/phase3/nominal_homologation_20261116_01/approved_smoke_real/manifest.json),
[avaliação nominal](../reports/phase3/nominal_homologation_20261116_01/approved_smoke_real/nominal_assessment.json),
plano pinado no preparo, observações, comparação legada, avaliação A anterior,
logs, snapshots e hashes. O CSV conserva 14 colunas e zero linhas de métricas.

## 5. Comparação com o legado e matriz final

O comparador legado foi executado **no waveform novo**, sem filtro:
**1.740 checks, 1.736 PASS/4 FAIL**. Os checks reproduzem o resultado original.
Os quatro FAILs continuam sendo a observação da palavra anterior na antiga
janela de retomada, c11/bits 0/2/4/6. Permanecem FAIL no comparador e são ligados
aditivamente ao alcance elétrico ainda não qualificado, segundo a decisão r1.

Não se promove o smoke original a PASS. Seus arquivos/manifesto e os
719 PASS/8 FAIL do diagnóstico complementar permanecem intactos. A avaliação
do perfil A anterior também permanece BLOCKED; sua implementação não foi contornada.

| Requisito | Evidência obrigatória no domínio aprovado | Veredito funcional |
|---|---|---|
| A01 — pedido/endereço | Capturas internas e programação/precondições da fixture | PASS |
| A02 — escrita/dados conhecidos | DIN_Q, armazenamento conhecido e scoreboard dos estímulos | PASS |
| A03 — captura na descida | Clock local/envelope experimental, Q em S, 20 bits estáveis durante captura; 92 observações próprias | PASS |
| A04 — retenção de Q | Monitor existente até captura local, 72 intervalos programados e 20 de bits estáveis | PASS |
| A05 — retenção visível contínua | 40 intervalos entre reads e 12 de bits estáveis na captura, com enable mantido | PASS |
| A06 — direção/propriedade | Checks existentes de corrente/máscara e 162 observações novas de TE_B/READ_Q | PASS |
| A07 — contenção | Sobreposição de host/ebuf e correntes, sem excluir valores iguais | PASS |
| A08 — novas palavras | 72 bits em S + 72 em T | PASS |
| A09 — estabilidade de DATA | 156 intervalos/relações aprovados, sem seleção por acomodação medida | PASS |
| A10-F — retomada funcional | 32 bits write/idle→read e 72 bits de máscara, retenção/direção/readback | PASS |
| A10-E — recuperação elétrica | 104 oportunidades, sem orçamento/deadline | **NOT_CHARACTERIZED** |
| A11 — sequência interna | Pré-carga/WL/WE/sense e envelope experimental preservados | PASS |
| A12 — integridade/cobertura | Pins, contexto, waveform, precondições e identidades completos | PASS |

As observações podem fundamentar vários requisitos; a soma por propriedade não
é outra contagem de métricas. Há exatamente 626 IDs próprios completos.
O envelope do FF TT/25 °C continua um screen interno; não caracteriza setup/hold
público da macro TT/27 °C. O resultado funcional PASS não qualifica máximos B.

## 6. Reprodução e resultados globais

Comandos usados, em destinos novos na ocasião:

```bash
python3 reports/phase3/nominal_homologation_20261116_01/run_regressions.py

tools/sram-eda python3 tools/prepare_phase3_4x8.py \
  --profile phase3_nominal_bench_v1 \
  --output reports/phase3/nominal_homologation_20261116_01/approved_prepare

tools/sram-eda python3 tools/run_phase3.py \
  --config reports/phase3/nominal_homologation_20261116_01/approved_prepare/config.json \
  --output reports/phase3/nominal_homologation_20261116_01/approved_dry --dry-run

tools/sram-eda python3 tools/run_phase3.py \
  --config reports/phase3/nominal_homologation_20261116_01/approved_prepare/config.json \
  --output reports/phase3/nominal_homologation_20261116_01/approved_smoke_real
```

O último comando retorna **1 mesmo com função PASS**, pois o estado global é
NOT_CHARACTERIZED. Usar destinos novos ao repetir; não sobrescrever resultados.
O [registro de invocações](../reports/phase3/nominal_homologation_20261116_01/smoke_invocations.json)
separa retornos da preparação, dry-run, CLI real e simulador. A auditoria posterior
confere 25.053 arquivos preexistentes, as três alterações de integração autorizadas
e a preservação de circuito, r0, verificadores e históricos.

## 7. Pendências elétricas e próximos domínios

Continuam ausentes/não caracterizados:

- Máximos de enable/disable, turnaround e disponibilidade de leitura; A10-E.
- `tACCESS`, `tCLK_TO_DATA`, `tREAD_INTERNAL`, `tWL_TO_SCLK`, setup/hold públicos
  e margens caracterizadas do registrador de saída. Não confundir os eventos
  de bancada com medidas desses parâmetros.
- `P_STATIC`, `P_IDLE`, `E_READ`, `E_WRITE`, `P_READ_AVG` e `P_WRITE_AVG`.
- RC distribuído, outros corners/VDD/temperaturas/cargas/slews, SNM/Monte Carlo,
  Fmax e sign-off elétrico.

A infraestrutura está homologada para o contrato nominal restrito. Para integrar
RC/PVT, é preciso selecionar e validar novos artefatos de extração, rever domínio,
modelos, cobertura, condições de observação e orçamentos B em nova revisão aprovada.
O contexto r1 rejeita essas mudanças; não basta editar corner/carga ou flags.
Liberty depende de medições reais qualificadas e tabelas correspondentes, com
função validada e caracterização global concluída. Nenhuma Liberty foi gerada.

**Conclusão:** integração operacional opt-in e infraestrutura de verificação
funcional nominal homologadas pelas regressões e pelo novo smoke real.
O padrão legado e os resultados históricos estão preservados. A SRAM não está
declarada eletricamente caracterizada: B e o estado global continuam
NOT_CHARACTERIZED, com CLI 1.
