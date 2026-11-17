# Fase 3 — BASELINE / RUNNER — Marco 12–13/11 — Fechamento

**Veredito técnico: marco de infraestrutura concluído e apto à publicação.**
Auditoria final: 16/11/2026. Responsável: Leonardo.
Branch: `feature/phase3-infra-leonardo`; HEAD inicial auditado: `ebf60a2`.
Baseline Fase 2: `89901e7e258b6955f6752163b918a296079466fa`.
A instrução do proprietário nesta etapa autoriza commit e push somente nessa
branch, sem merge ou force-push. O SHA da publicação é identificável pelo Git.

## Escopo entregue

O marco 12–13/11 entrega contratos, baseline/candidato, preparação rastreável,
runner Python/ngspice, CSV/JSON, manifestos, hashes, isolamento, recursos,
timeout e estados/retornos. Inclui a integração funcional nominal complementar
de 16/11, sem antecipar os marcos de caracterização e Liberty.

Interfaces públicas: `tools/prepare_phase3_4x8.py`, `tools/run_phase3.py` e
o novo `tools/run_phase3_regressions.py`. Contratos e dependências estão em
[phase3_characterization_contract.md](phase3_characterization_contract.md).
Os módulos `contract`, `provenance`, `runner` e `functional` validam configuração,
seleção ancorada em Git, fechamento de includes/modelos e evidência funcional.
Os módulos A/nominal reutilizam os verificadores compartilhados da Fase 2.

Entrada: JSON v1 com arquivos/corner/modelo pinados, condições, estímulos,
medidas e recursos. Saída: manifesto v1 aditivo, snapshots/logs, evidências e
`metrics.csv` com as **14 colunas** vigentes. Destinos existentes são recusados.
PASS, FAIL, ERROR, BLOCKED e NOT_CHARACTERIZED permanecem públicos.
CLI: PASS global ou dry-run completo sem simulação retorna 0; real não
caracterizado, FAIL, ERROR ou BLOCKED retorna 1; argumentos/destino inválidos, 2.

`phase2_qualification_v1` permanece padrão. O opt-in nominal r1 exige contexto,
política, plano, candidato, deck e modelos aprovados/pinados. Prova de processo
novo e waveform criado na execução impedem promoção de replay pelo adapter.
`phase3_functional_a_v1` conserva seus bloqueios originais.

## Auditoria e correções mínimas

1. `schema_version=true` e `1.0` eram aceitos pela igualdade Python com `1`.
   Agora é exigido inteiro JSON; subcasos negativos foram acrescentados.
2. Duas suítes presumiam `reports/phase3/` preexistente. Agora seus setups
   provisionam a pasta ignorada; 23 e 43 testes passaram isoladamente sem ela.
3. O runner legado podia promover medidas configuradas PASS + função PASS a
   PASS global sem B. O guard agora vale para **todo scope=sram**, com B explícito
   no manifesto; FAIL/ERROR/BLOCKED prevalecem. A regressão mantém o PASS separado
   da medição/função e exige global NOT_CHARACTERIZED. Não muda checks legados.

As correções não alteram circuitos, limiares, deadlines, janelas ou avaliadores
pinados da homologação. Nenhuma nova simulação SPICE foi necessária/executada.
Os snapshots históricos de runner/contrato conservam os hashes originais,
mesmo com a evolução dos fontes atuais.

Foram conferidos **25.053 arquivos preexistentes** e **730 evidências** do smoke
nominal: nenhuma mudança protegida/histórica. Seletores, especificações, SRAM,
GDS, netlists, fixtures e verificadores compartilhados permanecem intactos.
As diferenças frente a `89901e7` se limitam à infraestrutura/documentação Fase 3.

## Regressão e homologação complementar

- **165 testes distintos PASS, zero skips**, tanto no checkout de trabalho
  quanto em cópia independente com os mesmos fontes; subcasos reforçados sem
  remoção de casos anteriores. Logs por suíte e resumo são arquivados.
- Preparação e dry-run legado/nominal: **PASS/CLI 0** em cópia limpa, sem waveform,
  sem medidas, CSV de 14 colunas e global NOT_CHARACTERIZED.
- Testes negativos cobrem configuração/proveniência, cobertura, replay,
  corrupção/glitches/direção/contenção, falhas do simulador e timeout.
- As primeiras tentativas preservadas demonstram a pasta ausente e, depois,
  um clone compartilhado com paths de objetos inacessíveis no container.
  A cópia foi tornada independente antes das rodadas finais aprovadas.

Ambiente: launcher [tools/sram-eda](../tools/sram-eda), container `sram-xschem`,
Python 3.10.12, NumPy 1.26.4, gdstk 0.9.62, ngspice 44.2 e SKY130A pinado.
Consulte [tools/ENVIRONMENT.md](../tools/ENVIRONMENT.md). Modelos PDK são uma
dependência externa do ambiente EDA, não conteúdo versionado desta entrega.

A [homologação nominal r1](phase3_nominal_functional_homologation_r1_20261116.md)
continua íntegra: simulador PASS, **626/626 oportunidades PASS**, 72 bits de novas
leituras corretos em S, observações T corretas, A10-E/B/global NOT_CHARACTERIZED,
CLI real 1. Sua autoridade é [P3-DATA-002 r1](phase3_data_operational_policy_approval_r1_20261116.md).
O legado continua **1.736 PASS/4 FAIL**; o diagnóstico **719 PASS/8 FAIL**.
Não há aprovação retroativa nem repetição elétrica nesta auditoria.

## Reprodução a partir da branch

Um clone normal precisa conter o histórico e o ref
`origin/release/phase2-acceptance-20261111` resolvendo em `89901e7`. No ambiente
EDA documentado, executar na raiz, usando destinos novos:

```bash
tools/sram-eda python3 -c 'import json; from pathlib import Path; import sys; sys.path.insert(0,"tools"); from phase3.contract import validate; validate(json.loads(Path("characterization/phase3/smoke.json").read_text()))'
tools/sram-eda python3 tools/run_phase3_regressions.py --output reports/phase3/repro_testes_01
tools/sram-eda python3 tools/prepare_phase3_4x8.py --profile phase3_nominal_bench_v1 --output reports/phase3/repro_preparo_01
tools/sram-eda python3 tools/run_phase3.py --config reports/phase3/repro_preparo_01/config.json --output reports/phase3/repro_dry_01 --dry-run
```

Omitir `--profile` prepara o legado. A execução elétrica usa o mesmo runner sem
`--dry-run`, quando autorizada e com dependências disponíveis; o perfil nominal
atual permanece global NOT_CHARACTERIZED/CLI 1. Os testes criam seus próprios
temporários: nenhum arquivo ignorado anterior é necessário para carregar o
código ou executar a regressão no ambiente documentado.

## Evidências arquivadas separadamente

`reports/phase3/` permanece ignorado. Não entram no commit waveforms, modelos
PDK, snapshots duplicados, caches nem o clone de auditoria.

Pacote local: `~/Downloads/phase3_baseline_runner_evidencias_fechamento_20261116.zip`
(62.751.482 bytes), SHA-256:
`ae722e5bb9c77022b5c6bb0a44f83c92d7d79df0f1fc4d2338eb61bdedbed7f0`.
CRC e SHA-256 de todas as 1.560 entradas de evidência foram conferidos.
Contém auditorias, regressões finais, preparação/dry-run e o ZIP anterior intacto
com waveform real, manifesto e prova de frescor. O ZIP anterior tem SHA-256
`c1777f044ef7fbb97ebf8abcb23ff023ba85aabfcc01a2f19389ff7a14e41693`.

O pacote é entregue separadamente; **não está hospedado no Git**. Para recuperar,
obter esse arquivo do responsável, comparar seu SHA acima e extrair somente
evidências em um destino novo:

```bash
P3_PACOTE="$HOME/Downloads/phase3_baseline_runner_evidencias_fechamento_20261116.zip"
sha256sum "$P3_PACOTE"
unzip -t "$P3_PACOTE"
P3_RECUPERACAO=$(mktemp -d)
unzip "$P3_PACOTE" 'reports/phase3/*' 'arquivo_anterior/*' -d "$P3_RECUPERACAO"
unzip "$P3_RECUPERACAO/arquivo_anterior/phase3_homologacao_nominal_r1_20261116.zip" 'reports/phase3/*' -d "$P3_RECUPERACAO"
```

Fontes atuais vêm da branch; não substituir por fontes históricas do ZIP interno.
Os índices de integridade são `EVIDENCIAS_SHA256.json` no pacote e `evidence` nos
manifestos. Transcrições finais estão sob
`reports/phase3/final_baseline_runner_20261116_01/`, incluindo `audit_summary.json`,
`protected_audit.json`, `regressions_final/summary.json` e `clean_final_summary.json`.

## Dependências da equipe e limites do marco

| Pessoa | Entrega/continuidade |
|---|---|
| Leonardo | Entrega runner/contratos/política/testes; posteriormente integra evidências reais e desenvolve/valida o gerador Liberty |
| Danilo | Recebe preparador e contratos; fornece RC com identidade/conectividade e timing/potência TT/SS/FF |
| André | Recebe observadores/matriz; fornece margens e interpretação BL/BLB, pré-carga, WL, sense e captura |
| Ícaro | Recebe convenções CSV/proveniência; fornece SNM Monte Carlo N≥200, método, seeds e falhas |

Enable/disable/turnaround, disponibilidade de leitura, setup/hold público,
timing, potência e margens permanecem NOT_CHARACTERIZED. Não foram iniciados RC,
PVT, novas extrações, campanhas de timing/potência, SNM ou geração Liberty.
A interface nominal é fixa; suportar outras condições/dimensões exige novos
artefatos e revisão de domínio. O executor é Linux e os decks são código confiável,
não sandbox. A retenção elétrica fora das janelas aprovadas não ganhou garantia.

**O runner pode estar concluído sem TT/SS/FF ou Liberty concluídos.** Este
fechamento não declara a SRAM eletricamente caracterizada nem fecha o Marco 3
completo de 23/11. A próxima atuação de Leonardo é integração e Liberty quando
as frentes elétricas entregarem dados qualificados, em autorização própria.
