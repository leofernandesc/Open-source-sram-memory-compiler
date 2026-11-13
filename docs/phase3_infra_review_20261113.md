# Revisão da infraestrutura da Fase 3 — 13/11/2026

Branch: `feature/phase3-infra-leonardo`. Revisão sobre
`ae318bc43319ab96170c53cde8ab1a7262631f2d`, com checkout inicialmente limpo.
Nenhuma simulação elétrica da SRAM, campanha PVT ou geração Liberty foi iniciada.
Nenhum layout, célula congelada, netlist histórica, controle temporal ou seletor
foi alterado. O relatório anterior de entrega permanece como registro histórico.

## Ajustes implementados

1. **CLI:** execução real NOT_CHARACTERIZED retorna 1. Dry-run preparado com
   NOT_CHARACTERIZED e sem simulação continua retornando 0. O teste de CLI executa
   argparse/main/SystemExit em processo Python separado com somente o runner mockado;
   cobre oito combinações de estado, dry-run e realização da simulação.
2. **Separação de resultados:** manifesto com `simulator_status`,
   `measurement_status` e `functional_validation.status`; CSV e schema_version=1
   preservados. Métricas numéricas PASS não aprovam uma execução SRAM sem checks
   funcionais. FAIL funcional e ERROR do observer mantêm as medições numéricas
   válidas, o log e seu significado separado, com estado global não aprovado.
3. **Integração funcional:** `tools/phase3/functional.py` chama o checker existente
   `phase2_extension.check` e, por ele, `phase2_access_checks.check`. Nenhuma equação
   elétrica foi copiada. O contexto pinado é opcional para compatibilidade com
   configurações antigas; sem ele, scope=sram não obtém PASS global. O adapter
   suporta somente as condições nominais e o protocolo do perfil selecionado.
4. **Identidade:** `tools/phase3/provenance.py` ancora seletor/candidato na baseline
   Git, confere 51 entradas históricas, hashes/status dos recibos, payload e GDS,
   e verifica as arestas elétrica→fixture→GDS/extração. Confere binding/fabric
   publicados contra os netlists simulados e o payload escolhido. Mudanças
   consistentes apenas entre recibos/hashes locais continuam recusadas pela âncora.
5. **Preparador:** gera novo contexto com essa identidade, pins do deck/netlist/modelo
   e um pin do contexto na configuração. O mapa `inputs` do recibo de preparação
   permanece disponível, ampliado para a cadeia auditada. A evidência existente é
   somente lida; não é corrigida nem resselada.

O [contrato atualizado](phase3_characterization_contract.md) define os critérios do
futuro smoke: 18 ciclos completos até 370 ns, quatro linhas, 72 bits lidos e
cobertura por tipo equivalente aos 1.740 checks existentes, todos PASS, incluindo
captura, retenção, pré-carga/WL/sense e direção de DATA com sonda de corrente/tensão.
Esses números são critérios do protocolo, não novas medições nem desempenho garantido.
A carga nova de 10 fF/bit ainda precisa ser validada eletricamente.

## Validação realizada

| Suíte | Ambiente | Resultado |
|---|---|---|
| `test_phase3*.py` | Host Python | 14 testes PASS |
| `test_phase2_evidence.py` | Container EDA | 7 testes PASS |
| `test_phase2_output_safety.py` | Container EDA | 1 teste PASS |
| `test_phase2_extension.py` | Container EDA | 15 testes PASS |
| `test_phase2_startup.py` | Container EDA | 7 testes PASS |
| `test_phase2_protocol.py` | Container EDA | 6 testes PASS |

Total: **50 testes PASS**, incluindo subcasos de CLI, estados independentes,
falha funcional com medidas válidas, observer com erro, ausência de adapter,
dry-run sem chamar observer, delegação ao checker existente, cabeçalho/coverage
inválidos, adulteração de netlist/recibo/seletor/candidato e arestas de identidade.
Fixtures sintéticas e mocks são explicitamente testes de software, não evidência
elétrica da SRAM. Os testes existentes dos observers também usam traces sintéticos.

Transcrições completas locais: `reports/phase3/revision_tests_20261113/phase3.txt`
e `phase2.txt` no mesmo diretório. Elas não contêm resultados SPICE novos.

```bash
python3 -m unittest discover -s tools/tests -p 'test_phase3*.py' -v
# Repetir para cada suíte Phase 2 listada na tabela:
tools/sram-eda python3 -m unittest discover -s tools/tests \
  -p test_phase2_extension.py -v
```

O preparador reforçado e seu contexto também foram exercitados sem simulação:

```bash
tools/sram-eda python3 tools/prepare_phase3_4x8.py \
  --output reports/phase3/revision_prepare_20261113
tools/sram-eda python3 tools/run_phase3.py \
  --config reports/phase3/revision_prepare_20261113/config.json \
  --output reports/phase3/revision_sram_dry_20261113 --dry-run
```

Resultado: exit 0, estado global e três etapas NOT_CHARACTERIZED,
`electrical_simulation_performed=false`, lista de medidas vazia e nenhum log de
simulação. Esses diretórios estão preservados e não podem ser sobrescritos.
Para repetir, usar novos nomes. `compileall`, `git diff --check` e a comparação
com HEAD dos caminhos protegidos também passaram.

## Limites e próxima execução

O adapter está preparado e testado como software; não foi validado em um novo
waveform elétrico da SRAM. Ele consumirá exclusivamente o waveform produzido no
novo diretório de execução. Não reutiliza o PASS ou o raw antigo como resultado.
A referência conservadora TT/25 °C do registrador permanece explicitamente uma
referência de biblioteca, sem caracterizar setup/hold públicos da SRAM TT/27 °C.

Continuam pendentes a autorização/início do futuro smoke elétrico nominal,
revisão dos efeitos da carga, medidas reais de timing/potência e, em etapa posterior,
PVT, RC distribuído e Liberty. Como o preparador ainda configura zero medidas,
uma execução real dele retorna NOT_CHARACTERIZED/exit 1 mesmo que a validação
funcional passe. O sucesso funcional de um cenário isolado também não define
caracterização completa: `sram_characterized` continua false.
