# Entrega de infraestrutura da Fase 3 — 13/11/2026

Responsável: Leonardo. Branch: `feature/phase3-infra-leonardo`.
Baseline inicial conferida: `origin/release/phase2-acceptance-20261111`, commit
`89901e7e258b6955f6752163b918a296079466fa`. Checkout inicial limpo nessa mesma revisão.
Não houve merge, push, mudança de arquitetura, layout, células congeladas,
resultados históricos, especificações oficiais ou seletores de release.

## Arquivos entregues

- `tools/run_phase3.py`: CLI; `tools/phase3/{__init__,contract,runner}.py`: contrato,
  validação, snapshots, executor, parser e exportação CSV/JSON.
- `tools/prepare_phase3_4x8.py`: preparação rastreável de cópia do deck nominal
  existente, com oito cargas exploratórias novas de 10 fF, sem executar SPICE.
- `characterization/phase3/{smoke.json,smoke.spice.in,smoke_netlist.spice}`:
  exemplo de teste elétrico da infraestrutura com inversor SKY130.
- `tools/tests/test_phase3.py`: testes de contrato e execução/falha.
- `docs/phase3_characterization_contract.md`: contrato comum e fronteira Liberty.
- `docs/phase3_plan_to_20261123.md`: nova distribuição, mantendo a proposta antiga
  explicitamente identificada como histórica.
- `.gitignore`: exclui somente novos resultados locais em `reports/phase3/`,
  que retêm cópias de modelos PDK. Não apaga esses resultados.
- Este relatório.

## Como executar

Executar a partir da raiz do repositório. Usar identificadores novos em cada execução;
nenhum diretório de preparação ou execução é reutilizado. Os paths do modelo no
exemplo correspondem ao container existente, com SHA-256 conferido; em outra
instalação, auditar e fixar seus próprios paths e hashes.

```bash
# Testes sem depender do ngspice local
python3 -m unittest discover -s tools/tests -p test_phase3.py -v

# Preparação sem simulação: exemplo da infraestrutura
tools/sram-eda python3 tools/run_phase3.py \
  --config characterization/phase3/smoke.json \
  --output reports/phase3/meu_smoke_dry_01 --dry-run

# Smoke elétrico real com inversor, sem métrica SRAM
tools/sram-eda python3 tools/run_phase3.py \
  --config characterization/phase3/smoke.json \
  --output reports/phase3/meu_smoke_real_01

# Preparar cópia nominal 4x8 a partir da evidência existente
tools/sram-eda python3 tools/prepare_phase3_4x8.py \
  --output reports/phase3/meu_4x8_preparo_01

tools/sram-eda python3 tools/run_phase3.py \
  --config reports/phase3/meu_4x8_preparo_01/config.json \
  --output reports/phase3/meu_4x8_dry_01 --dry-run
```

Para um deck SRAM futuro aprovado, usar a mesma CLI com sua configuração pinada,
sem `--dry-run`. O adapter atual não define medidas de timing/potência, portanto
mesmo uma execução completa dele permanece NOT_CHARACTERIZED. Seu clock/PWL é fixo;
alterar metadados não gera novos estímulos. Para outros corners/slews/períodos,
fornecer um template adequado e validar correspondência entre configuração e deck.

## Validação

- 6 testes novos passaram no host, com subcasos para tipos/configurações inválidas,
  conversão SI e dimensões, CSV/JSON, valores ausentes/não finitos, medições repetidas,
  transitive includes e `.lib`, ciclos de includes, integridade, dry-run,
  sobrescrita, PASS/FAIL, erro SPICE, timeout, recursos insuficientes,
  modelo ausente e corner indisponível. Erros do simulador/timeout são injetados
  por mocks; o smoke abaixo usa o simulador real.
- 7 testes existentes de `test_phase2_evidence.py` passaram no host.
- O teste existente `test_phase2_output_safety.py` não passou inicialmente no host
  por ausência de `gdstk`; foi repetido com sucesso no container EDA.
- `compileall` dos módulos/CLIs e `git diff --check`: passaram.

Execuções locais definitivas, com ngspice 44.2 e SKY130A:

| Diretório em reports/phase3 | Execução elétrica | Resultado |
|---|---|---|
| `reviewed_infra_dry_20261113` | Não | NOT_CHARACTERIZED; CSV sem valor |
| `reviewed_infra_smoke_20261113` | Sim, inversor de teste | PASS; medida real SMOKE_VOLTAGE |
| `reviewed_sram_dry_20261113` | Não | NOT_CHARACTERIZED; nenhuma medida SRAM configurada |

Cada diretório contém manifesto, configuração, CSV, snapshots de código/entradas,
modelos reescritos e hashes. O smoke contém ainda log ngspice. Os diretórios
anteriores de teste permanecem preservados, inclusive o preparo inicial recusado
por uma suposição de carga que foi corrigida: o deck histórico não tinha as oito
cargas externas explícitas. Não foi executada simulação elétrica da SRAM nesta entrega.

## Handoff e dependências

Todos recebem contrato, CLI, configuração de exemplo, comando de testes e um
manifesto/CSV de referência. Os três diretórios definitivos estão preservados
localmente; não enviar cópias do PDK no Git.

| Pessoa | O que recebe e precisa fornecer |
|---|---|
| Danilo | Adapter 4x8 e contrato; fornecer RC com prova de conectividade/origem/hash e modelos/corners operacionais; decks e medidas timing/potência TT/SS/FF |
| André | Definições de tREAD_INTERNAL/tWL_TO_SCLK e limiares; fornecer observadores BL/BLB, pré-carga, sense e margens de captura, preservando falhas |
| Ícaro | Convenções de estados/proveniência; fornecer método SNM/variações, tabela por amostra, seeds e pelo menos 200 amostras, com falhas incluídas |

Antes da caracterização TT: revisar o novo carregamento e os critérios funcionais;
fechar nets/probes, janelas/ocorrências, direções, startup e potência da alimentação;
criar medidas ngspice reais e sweeps de setup/hold; validar o deck contra o protocolo
em bordas opostas; definir alcance de extração e revisar a ressalva do sense PEX.
O fluxo existente de verificação funcional permanece disponível e não foi duplicado.

Antes de Liberty: obter tabelas reais de slew/carga por corner e arcos públicos,
validar funcionalmente cada ensaio, fechar agregação de bits/palavra e condições de
energia, implementar o gerador e validar sintaxe/pins/unidades/lookup com consumidor.
Não há gerador Liberty nesta etapa, nem tabelas artificiais para antecipá-lo.

A validação de includes é textual e conservadora; paths dinâmicos são recusados.
O executor é específico para Linux. Os decks são código confiável da equipe, não
uma sandbox contra comandos maliciosos. Snapshots de todas as seções da biblioteca
consomem cerca de 70 MiB por ensaio neste ambiente. Não há scheduler distribuído,
extração RC, analisador automático de waveform, busca de setup/hold nem Monte Carlo
implementados nesta infraestrutura. 8x8/16x8/32x8 têm suporte no contrato, sem afirmar
existência ou validação dos circuitos físicos correspondentes.

**A SRAM não está caracterizada por esta entrega.**
