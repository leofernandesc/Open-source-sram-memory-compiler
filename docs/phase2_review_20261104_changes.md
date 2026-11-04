# Fase 2 — resumo de mudanças da revisão

Comparação com o snapshot pré-revisão, não com toda a implementação untracked
sobre `3b0675b`. Nenhuma mudança altera folhas congeladas, protocolo, bordas,
organização 4×8, alimentação ou sizing.

| Arquivo existente lapidado | Tipo/motivo | Invalidação e verificação |
|---|---|---|
| `tools/audit_phase2.py` | Bug: NaN, inventário opcional, hashes pré-run não reconciliados, condição/probes e payload sem selo | Aceite automático antigo deixa de ser atual; dados originais reanalisados e nova consolidação |
| `tools/package_phase2.py` | Bug: arquivo alterado podia herdar PASS; selo pré/pós, núcleo público e opções de saída | Manifesto anterior arquivado; mesmo GDS adulterado rejeitado e novo pacote conferido |
| `tools/verify_phase2_evidence_guards.py` | Novos testes: quatro negativos ampliados a dez; código validador identificado | Receipt original preservado; negativos em cópias executados |
| `tools/phase2_resources.py` | Manutenção: swap e preflight comum | Não muda bancada/modelo; preflights observados |
| `scripts/run_phase2.sh` | Manutenção: recursos e OMP/BLAS limitado | Usado na reconstrução física real |
| `tools/run_phase2_place.py` | Dependências explícitas, emit-only sem falso aceite, SDC, hashes e proteção de input | Fluxo nativo novamente executado; GDS equivalente |
| `tools/finish_phase2_layout.py` | Inputs/hash pós-run, núcleo/JSON públicos e proteção de report | Acabamento e DRC/LVS repetidos; SPICE idêntico |
| `tools/run_phase2_binding.py` | Inventário de outputs | Mapeamento repetido, sem mudança lógica |
| `tools/run_phase2_fabric.py` | Inventário de outputs | Núcleo novamente gerado e DRC/LVS/reimportado |
| `tools/verify_phase2_gds.py` | Rejeita output sobre input antes de escrever | Nova importação e teste de CLI |
| `tools/run_phase2_routed_gls.py` | Mesma proteção | GLS repetida e teste de preservação |
| `physical/phase2/checkpoints.json` | Seleção explícita dos reports revisados | Versão anterior arquivada e novos vínculos conferidos |
| `physical/phase2/delivery.json` | Novo índice/selo | Versão anterior arquivada; payload conferido |
| `README.md` | Documentação do estado atual e limites | Links e referências conferidos |
| `docs/sram_4x8_interfaces.md` | Separa vista RTL do binding físico disponível | Sem mudança de contrato |
| `tools/ENVIRONMENT.md` | Imagem real 1.0.7/ferramentas; registro antigo 1.1.0 mantido como histórico | `docker inspect`, `--check` e versões reais |
| `docs/phase2_execution.md` | Revisão, comandos e evidências atuais | Conferência com reports |

| Arquivo/grupo novo | Finalidade |
|---|---|
| `tools/phase2_evidence.py` | Finitude, inventários obrigatórios, legado explícito e selo verificável |
| `tools/run_phase2_directed_review.py` | TT com perturbação pós-captura, walking data e BL/BLB |
| `tools/review_phase2_structure.py` | Auditor independente de terminais/posições e contagem recursiva |
| `tools/analyze_phase2_capture_review.py` | Janelas de nível válido e flags de limite inferior |
| `tools/run_phase2_lvs_review.py` | LVS expandido e quatro defeitos deliberados no top |
| `tools/tests/test_phase2_evidence.py` | Regressões dos bugs reproduzidos |
| `tools/tests/test_phase2_output_safety.py` | Quatro CLIs reais; rejeição preserva input |
| `scripts/reproduce_phase2_4x8.sh` | Reconstrói candidato não selecionado a partir das fontes |
| `physical/phase2/experimental.sdc` | Mesmo clock original; sem inventar IO/arcos/uncertainty |
| `physical/phase2/history/` | Índices anteriores e inventário legado pré-revisão |
| `docs/phase2_review_20261104*.md` | Diagnóstico, relatório, matriz, mudanças e aceite |
| `reports/phase2/review_20261104/` | Logs reais, métricas, negativos e fontes anteriores críticas |
| `reports/digital/phase2_review_20261104/` | Regressão/consolidação atual; históricos intactos |

Não houve alteração no DUT RTL, em `macro_binding.v` ou nas folhas. Mudanças
nos produtores afetam dependências/constraints equivalentes/integridade;
mesmo assim a geração física foi repetida. Não se repetiu SPICE de 710 ns no
GDS reconstruído porque seu SPICE extraído é idêntico byte a byte. A bancada
nova de 830 ns foi realmente executada no mesmo circuito.

As primeiras tentativas do novo runner LVS estão em `lvs_negative_parser_trial*`:
Netgen já detectava os defeitos, mas o runner precisava reconhecer o formato
final de pin matching/property errors do top completo. Setup e tolerâncias
não foram alterados para fazer circuitos errados passarem.
