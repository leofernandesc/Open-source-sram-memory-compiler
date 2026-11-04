# Fase 2 — quadro de aceite técnico

**APROVADO COM RESSALVAS**, para revisão da equipe. Não é aprovação formal dos
orientadores nem encerramento automático da fase.

Atualizado pela [rodada de contrato temporal e partida](phase2_final_polish.md).
O quadro anterior está preservado em
`reports/phase2/final_polish_20261104/source_before/docs/`.

## F2-DIG

| Critério | Estado | Fundamento |
|---|---|---|
| Síntese SKY130HD | PASS | Yosys real, biblioteca/versão identificadas |
| Macro preservada | PASS | Uma macro; nenhum array FF no núcleo |
| Tri-state 0/1/Z e enable | PASS | Oito ebufn, piloto e mutante de polaridade |
| Netlist/interface | PASS | 20 FF e semântica de captura/saída do contrato |
| GLS sintetizada/roteada | PASS | 15.619 checks/2.504 transações por execução |
| Regressão/infraestrutura | PASS | 154.303 checks RTL; 117 métodos Python sem skips |
| Limites temporais registrados | PASS | SDC experimental; GLS zero-delay não é STA/SDF |
| Contrato temporal público funcional | PASS | Protocolo, capturas, propriedade do barramento e parâmetros pendentes explícitos |
| Tempos externos numéricos qualificados | NOT_EVALUATED | Setup/hold públicos, read-valid, enable/disable e turnaround ainda sem limites |
| Timing/Fmax/SDF qualificado | NOT_EVALUATED | Macro sem Liberty caracterizada |

**F2-DIG aprovado funcionalmente no escopo mapeamento/GLS.** Isso não implica
frequência máxima ou fechamento temporal completo.

A regressão completa de 117 métodos acima é o resultado preservado da auditoria.
Nesta rodada foram executados 20 métodos direcionados, incluindo sete novos
e 13 já existentes. Não são 137 testes distintos nem nova campanha GLS.

## F2-FIS

| Critério | Estado | Fundamento |
|---|---|---|
| Gerador 4×8 reproduzível | PASS | Reconstrução completa; GDS normalizado/SPICE iguais |
| Estrutura completa | PASS | Terminais e coordenadas independentes do gerador |
| Células preservadas | PASS | Manifestos e índices congelados conferidos |
| Controle físico nominal | PASS | Fases, pré-carga, captura e recuperação verificadas |
| Partida ampliada sem reset | PASS | Cinco cenários TT; 3.383 checks totais incluindo 240 bits lidos, sem falhas; raws reanalisados |
| Leitura/escrita elétrica | PASS | Original 128/392; nova campanha 1.332 totais incluindo 160 leituras de bits |
| Captura/independência das entradas posteriores | PASS | Perturbações e observação D/Q/DATA |
| GDS/LEF completos | PASS | Top integrado, 16 pinos e 46 regiões de acesso |
| DRC/LVS | PASS | Zero DRC; comparação expandida; gate/bulk/W/L errados rejeitados |
| Evidências/empacotamento | PASS | Selo, dez adulterações e GDS trocado rejeitados |
| RC/PVT/yield/potência/confiabilidade completos | NOT_EVALUATED | Fora desta rodada nominal |

**F2-FIS aprovado experimentalmente para 4×8, TT/1,8 V/27 °C**, com conectividade
e junções extraídas, sem wire R/C. Núcleo e top completo têm entregas distintas;
o aceite isolado do núcleo não substituiu a verificação do conjunto.

## Ressalvas e fechamento imediato

1. A equipe deve revisar/aceitar explicitamente o escopo experimental. O
   contrato temporal funcional agora está documentado; IO delays e limites
   temporais públicos numéricos continuam sem caracterização.
2. Setup/hold usa referência TT/25 °C contra simulação a 27 °C; a folga nominal
   observada não é caracterização completa de STA/PVT.
3. A partida foi ampliada para as cinco combinações documentadas de rampas
   1/5/10 ns e 0/2/3 ciclos, mas não cobre todas as rampas/estados ou o tempo
   mínimo. Zero ciclos no ensaio ainda incluiu 9 ns de espera após o plateau.
4. A limitação de cobertura de modelos/confiabilidade da Fase 1 permanece
   registrada conforme a decisão anterior; não foi convertida em sign-off.
5. O protótipo físico é 4×8. Os modelos maiores foram verificados no RTL,
   mas não existem layouts 8/16/32 caracterizados nesta entrega.

Ações imediatas: revisão conjunta do manifesto e destes documentos, inspeção
das evidências necessárias e deliberação do aceite da equipe. Publicação
Git/PR exige instrução posterior. Nenhuma atividade da Fase 3 foi iniciada.

Referências: [auditoria](phase2_review_20261104.md),
[matriz](phase2_review_20261104_requirements.md),
[mudanças](phase2_review_20261104_changes.md),
[manifesto](../physical/phase2/delivery.json),
[aceite verificável](../reports/phase2/review_20261104/acceptance/results.json).
