# Primeiro smoke elétrico SRAM da Fase 3 — 13/11/2026

## Resultado executivo

**Execução real realizada; simulador PASS, verificação funcional FAIL,
medições NOT_CHARACTERIZED e estado global FAIL, com saída 1 da CLI.**
Não há aprovação da SRAM nem prontidão para campanha PVT a partir deste ensaio.
Os 50 testes de software passaram novamente. Não foram necessárias ou realizadas
correções no código, circuito, layout, parâmetros do ensaio ou critérios.

Branch `feature/phase3-infra-leonardo`; HEAD inicial e preservado:
`ebf60a2725e8a40857323d3bbfd93c587ef52f77`. Working tree inicialmente limpo.
Baseline: `origin/release/phase2-acceptance-20261111`, commit
`89901e7e258b6955f6752163b918a296079466fa`. Nenhum commit, merge, push ou deploy.

Foram consultados integralmente o relatório `phase3_infra_review_20261113.md`,
o contrato `phase3_characterization_contract.md`, os documentos técnico/digital
e o planejamento da Fase 3; as interfaces reais foram conferidas no CLI,
preparador, runner, validador, adapter funcional e verificador de proveniência.

## Ambiente e limite do ensaio

- Container existente `sram-xschem`, imagem `isaiassh/unic-cass-tools:1.0.7`,
  acessado pelo launcher existente `tools/sram-eda`; repositório montado em `/work`.
- Plataforma: `Linux-7.0.0-43-generic-x86_64-with-glibc2.35`.
- Python: `3.10.12 (main, Jan  8 2026, 06:52:19) [GCC 11.4.0]`; NumPy `1.26.4`.
- ngspice 44.2: `/opt/ngspice/ngspice-44.2/bin/ngspice`;
  SHA-256 `af05592b4adc21e9c792b8bbda0d3ddb0a86bfccf80c8e6e5c5e7c366184fe77`.
- SKY130A/open_pdks, versão Volare `0fe599b2afb6708d281543108caf8310912f54af`;
  seção de modelo `tt`, conferida no arquivo e capturada com suas dependências.
- Preflight: 2720 MiB disponíveis de memória,
  3123 MiB livres de disco; aprovado pelos limites existentes.
- Limites efetivos do runner: um CPU, uma thread, 4.096 MiB de espaço virtual,
  timeout de parede 2.400 s, limite de CPU e 512 MiB por arquivo.
- Único cenário: 4×8/32 bits, 1.493 MOS, TT, 1,8 V, 27 °C provisórios,
  clock de 20 ns/50%, slew 50 ps e carga exploratória de 10 fF em cada bit DATA.
  Extração de dispositivos/junções, sem RC distribuído completo.
- Os 18 ciclos até 370 ns são o menor perfil SRAM aceito pelo adapter existente;
  sua cobertura fixa não permite truncá-lo para um piloto menor. Não houve sweep.
- Início UTC: `2026-11-13T23:02:06.453389+00:00`; fim UTC: `2026-11-13T23:18:50.778242+00:00`.
  Tempo registrado pelo runner: 1002.506 s, distinto de tempo elétrico.

## Seleção e identidade dos artefatos

A proveniência foi conferida antes e depois, incluindo 51 entradas históricas,
seletor/candidato ancorados no Git, provas/payload e as arestas de identidade
elétrica→fixture→GDS/extração. Não houve reextração ou mudança da seleção.

| Artefato | Caminho | SHA-256 |
|---|---|---|
| `Seletor` | `release/phase2_current.json` | `65c82536a450caf11b3065cc252675f1dfe7720dd2491bb73a8677f089453849` |
| `Candidato` | `physical/phase2_direct_abutment/candidate.json` | `4765f8ec0c7b55e7323fba63bc04a7eedbdbb75ce89826c20fbf3a9cab3ba5e0` |
| `GDS selecionado` | `reports/phase2/direct_abutment_20261111/gds_v1/sram_4x8.gds` | `83e72aee8d45a9826751cdefd46dd062acc2a17ec0acfd33c07f218d20d8e64e` |
| `Extração` | `reports/phase2/direct_abutment_20261111/gds_v1/final_extracted.spice` | `ed9474b2681fb05e1aa69485b927d2da5a47a72e44e4cc5606a87eb9b8c3397a` |
| `Binding` | `/work/reports/phase2/direct_abutment_20261111/qualification_v1/binding.spice` | `f4b502bcf1c99fb18d02ebad712878ebf83c0a4cec04987d2dce3d9645baa510` |
| `Recibo elétrico histórico` | `reports/phase2/direct_abutment_20261111/qualification_v1/results.json` | `a559e9d90c3393b614c937b1e515717be8fc4fe624fc445fb21e05c8b76ec708` |
| `Recibo de fixture` | `reports/phase2/direct_abutment_20261111/fixture_v1/results.json` | `6e59291c69439336c711a67862a409d4a9aecf3298b8dc7270e1f3588a348d91` |
| `Deck preparado` | `/work/reports/phase3/smoke_sram4x8_20261113_01_prepare/nominal.spice.in` | `fd7e058b2b997b21c1a3f0347913ebf0b8ce3b4c03ce3bfc1329f0469c2b3acf` |
| `Modelo principal` | `/opt/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice` | `5efa041a988893c1a3580d0ecd57870ea3146b27741c7d42b56baaa336b9549e` |

Hashes de fabric, contexto pinado, código, dependências do modelo e demais
entradas estão nos manifestos e em `selection_before.json`/`selection_after.json`.
Os modelos foram copiados e seus includes reescritos pelo runner, sem inventar
paths ou corners. A seção TT foi usada; copiar seções SS/FF para integridade da
biblioteca não significa simular esses corners.

O preparador preservou os PWL e o binding histórico e acrescentou somente as oito
cargas exploratórias já previstas. A cadeia de 80 inversores e seus taps não foi
alterada. O `preparation_inspection.json` registra essa comparação.

## Comandos efetivamente executados

A partir da raiz do checkout:

```bash
tools/sram-eda python3 tools/prepare_phase3_4x8.py \
  --output reports/phase3/smoke_sram4x8_20261113_01_prepare

tools/sram-eda python3 tools/run_phase3.py \
  --config reports/phase3/smoke_sram4x8_20261113_01_prepare/config.json \
  --output reports/phase3/smoke_sram4x8_20261113_01_real

tools/sram-eda python3 reports/phase3/smoke_sram4x8_20261113_01_audit/inspect_results.py

tools/sram-eda python3 reports/phase3/smoke_sram4x8_20261113_01_audit/run_tests.py

tools/sram-eda python3 tools/run_phase3.py \
  --config reports/phase3/smoke_sram4x8_20261113_01_prepare/config.json \
  --output reports/phase3/smoke_sram4x8_20261113_01_dry --dry-run

tools/sram-eda python3 reports/phase3/smoke_sram4x8_20261113_01_audit/diagnose_failure.py
```

A execução SPICE interna foi `ngspice -n -b 320.spice`, no diretório
`/work/reports/phase3/smoke_sram4x8_20261113_01_real/inputs`.
O deck usa `tran 10p 370n 0 10p`. Um wrapper Python capturou stdout, stderr,
retorno e horário da CLI em `invocation_real.json`; o mesmo procedimento registrou
os testes e o dry-run. Os scripts de inspeção/diagnóstico/teste acima estão
preservados junto aos resultados e não integram ou modificam o código de produção.
Os nomes são exclusivos e já existem: uma reprodução deve escolher novos destinos.

## Resultados separados por etapa

| Etapa | Resultado | Evidência |
|---|---|---|
| Seleção, hashes e preparação | PASS | Cadeia histórica idêntica antes/depois |
| Simulador | PASS, retorno 0 | ngspice concluiu, sem mensagens de erro/warning |
| Waveform | Válido estruturalmente | 40,507 linhas, 154 colunas, 0–370 ns, dados finitos e tempo crescente |
| Medições de timing/potência | NOT_CHARACTERIZED | Configuração `measurements: []`, sem comandos de medição no deck |
| Verificação funcional | FAIL | 1.736 PASS e 4 FAIL, de 1.740 checks |
| Nova palavra lida | 72/72 checks PASS | `read_data`, e 72/72 `captured_ff_q` PASS |
| Execução real global | FAIL, CLI 1 | Falha funcional prevalece sobre ausência de métricas |
| Dry-run | NOT_CHARACTERIZED, CLI 0 | Sem processo de simulação, waveform ou medições |
| Suíte de software | 50 PASS, retorno 0 | Sem falhas, erros ou testes pulados |

O waveform novo tem 99,852,241 bytes e SHA-256
`1a7670edaa2be0202c1861f053864dcd5f93b24ed727117dd2a6385c7893feae`. O ngspice e os verificadores foram realmente executados;
o waveform histórico não foi usado como evidência do novo resultado.

O parser/exportador recebeu a lista vazia prevista pelo preparador. Logo, a
extração e a validação de métricas numéricas de timing/potência **não foram
exercitadas eletricamente** neste smoke. Não há tACCESS, tCLK_TO_DATA, energia,
potência, setup/hold ou Fmax aprovados. `metrics.csv` conserva as 15 colunas do
contrato e zero linhas; o manifesto contém `measurements: []`,
`measurement_status=NOT_CHARACTERIZED` e `sram_characterized=false`.
Não foi inserido valor para preencher o CSV nem convertida ausência em zero.

A saída real é 1 por FAIL funcional. O caso real NOT_CHARACTERIZED→1 e o caso
dry-run NOT_CHARACTERIZED→0 continuam cobertos pelos testes de CLI. Este dry-run
real também confirmou exit 0. Não se executou uma segunda simulação apenas para
obter outro código de saída.

## Causa comprovada dos quatro FAILs e limite do diagnóstico

O checker existente `phase2_extension.check`, por meio do adapter da Fase 3,
reprovou `previous_data_visible_before_new_capture` no ciclo 11, bits 0, 2, 4 e 6.
Esse ciclo é leitura da linha 1, solicitando `0xAA`, após uma escrita; a palavra
retida pelo registrador da leitura anterior é `0x55`.

O observer exige que a palavra anterior já esteja válida durante toda a janela
absoluta [231; 239,5] ns. Nos quatro bits, foram observadas **16 amostras inválidas
por bit**: de 231,007658 a 231,119291 ns, com DATA mínimo de 0,957592467 V,
abaixo de 1,44 V (80% VDD). O registrador interno preservou o nível alto:
1,79896006–1,81363577 V na janela. HOST_EN estava em 0 V; a corrente máxima
absoluta do host nesses bits foi aproximadamente 1,80 pA no modelo, e os checks
de sobreposição de drivers passaram.

A causa imediata demonstrada é a recuperação de DATA ainda incompleta no início
da janela do observer após a troca escrita→leitura, sem corrupção demonstrada do
registrador interno ou das novas palavras lidas. A falha não é de ferramenta,
proveniência, preparação ou formato do waveform. Não foi comprovado defeito de
infraestrutura que autorizasse alterar o runner ou repetir SPICE após correção.

Para diagnóstico, foi reutilizado o helper existente `crossing`, sem duplicar os
verificadores. O cruzamento de 80% VDD em DATA0 ocorre em 231,122751930 ns no novo
waveform. A comparação com o raw histórico, cujo SHA-256 foi conferido antes/depois,
mostra 230,882357207 ns e mínimo de 1,79755463 V na mesma janela histórica sem as
oito cargas adicionais. Também foram conferidos os 319 pins de modelos históricos.
Esses são **tempos absolutos de diagnóstico funcional**, não medições de propagação
50%→50%, nem valores tACCESS/tCLK_TO_DATA inseridos no contrato CSV.

A comparação é compatível com o efeito da carga exploratória sobre a recuperação
do barramento; a origem física detalhada não foi isolada. O limite de +1 ns da
janela do observer não é um limite elétrico garantido pela especificação oficial.
Isso requer revisão de metodologia e caracterização da habilitação de DATA, sem
reescrever este FAIL ou afrouxar retroativamente sua janela. Não há conclusão de
aprovação integral ou falha universal da arquitetura com base neste ensaio.

Nenhum limiar, estímulo, carga, circuito ou checker foi modificado para produzir
PASS. Foi realizada uma única execução elétrica nova. Os FAILs e o raw completo
permanecem preservados em `functional_checks.json` e `inputs/waveform.dat`.

## Integridade, manifesto e contrato

A inspeção independente conferiu 700 hashes de entradas e
708 hashes de evidência da execução real, além da cadeia
selecionada. A validação foi repetida após os testes e o diagnóstico, incluindo
o dry-run. A referência existente do registrador também permaneceu idêntica:
`/opt/pdks/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib`, SHA-256
`8e78e14442062dba34d414fca6490b2f6b96038d4510d1438ca44fee31487135`. Ela fornece o envelope conservador
TT/25 °C, não setup/hold caracterizados da SRAM TT/27 °C; nenhum Liberty foi gerado.

SHA-256 do manifesto real: `6cc1d6efc804f293d4a421678c06494cab63aacfc2fe75ad3ac5022d39750cc7`.
O manifesto corresponde a simulador PASS, medições NOT_CHARACTERIZED,
validação funcional FAIL e estado global FAIL. O CSV é coerente com a configuração
sem métricas. `invocation_real.json` confirma CLI 1, `invocation_dry.json` confirma
CLI 0, e `validation_final.json` registra a verificação independente final.

## Testes automatizados posteriores à simulação

O driver `run_tests.py` executou exatamente as suítes da revisão anterior:

| Suíte | Testes | Resultado |
|---|---:|---|
| test_phase3*.py | 14 | PASS |
| test_phase2_evidence.py | 7 | PASS |
| test_phase2_output_safety.py | 1 | PASS |
| test_phase2_extension.py | 15 | PASS |
| test_phase2_startup.py | 7 | PASS |
| test_phase2_protocol.py | 6 | PASS |
| Total | 50 | PASS |

Transcrições: `tests_stdout.txt` e `tests_stderr.txt`; sumário:
`tests_summary.json`, no diretório de auditoria. As fixtures sintéticas e mocks
usadas nesses testes são testes de software; não substituem o waveform elétrico
novo nem anulam os quatro FAILs funcionais reais.

## Arquivos criados, preservação e pendências

Novo documento: `docs/phase3_first_sram_smoke_20261113.md`.
Nenhum arquivo de produção foi modificado. Resultados novos locais, ignorados
pelo Git conforme política existente:

- `reports/phase3/smoke_sram4x8_20261113_01_prepare/`: deck, config e contexto pinados.
- `reports/phase3/smoke_sram4x8_20261113_01_real/`: manifest/CSV/log, snapshots,
  modelos, checks funcionais e waveform completo.
- `reports/phase3/smoke_sram4x8_20261113_01_dry/`: recibo independente sem simulação.
- `reports/phase3/smoke_sram4x8_20261113_01_audit/`: ambiente, seleção antes/depois,
  invocações/retornos, inspeções e diagnóstico reproduzíveis, excerto CSV do
  barramento (diagnóstico, não CSV de métricas), transcrições e hashes.

Não foram apagados artefatos ou resultados anteriores. HEAD e caminhos de código,
células, layouts, temporização, specs e seletores foram comparados com `ebf60a2`
e permaneceram idênticos. O único diff de trabalho esperado é este relatório novo.

**PASS:** proveniência, preparação, simulador, estrutura do raw, nova palavra lida,
integridade, contrato sem métricas, semântica do dry-run e 50 testes de software.
**FAIL:** quatro checks de visibilidade da palavra anterior; estado global do smoke.
**NOT_RUN/NOT_CHARACTERIZED:** medidas timing/potência, extração numérica real pelo
parser, setup/hold públicos, PVT, SNM, RC distribuído e geração Liberty.

Próxima etapa recomendada: revisar com a equipe a relação entre a janela nominal
do observer e a habilitação elétrica do barramento carregado; definir medidas reais
rastreáveis para essa transição e para o primeiro arco TT, mantendo os FAILs atuais.
Depois, executar novo smoke TT com metodologia explicitamente revisada. A integração
já executa e preserva falhas corretamente, mas a validação de métricas elétricas
continua incompleta e o adapter rejeita condições diferentes das nominais.
**A infraestrutura ainda não está aprovada para iniciar a campanha PVT.**
