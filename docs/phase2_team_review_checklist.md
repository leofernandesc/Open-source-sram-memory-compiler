# Fase 2 — pauta de revisão da equipe

Base publicada desta rodada: `4ffbbf5`, SRAM física 4×8. A distribuição abaixo
é uma **sugestão de revisão**, não uma redefinição de autoria. Todos os aceites
pessoais estão pendentes. PASS de uma ferramenta não representa aprovação
de Danilo, André, Leonardo ou dos orientadores.

| Questão técnica | Artefato para revisar | Evidência disponível | Risco/limitação | Revisor sugerido | Revisão humana |
|---|---|---|---|---|---|
| Cada linha contém oito bitcells reais e preserva palavras não selecionadas? | `tools/review_phase2_structure.py`; binding extraído | Auditoria dos terminais/coordenadas; readback e nós conhecidos em C1 | Conexões geradas em comum exigem comparação com extração e comportamento | Danilo | PENDENTE |
| Dados complementares chegam à coluna correta? | `reports/phase2/extracted_access_singlethread/binding.spice` | Auditoria complementar de oito inversores CMOS com bulk e alimentação | Mesmo padrão repetido sozinho poderia ocultar troca de coluna | Danilo e Leonardo | PENDENTE |
| Os quatro DEC/WL respeitam a ordem formal, inclusive DEC3/DEC2? | Manifesto Fase 1; extração final; `structure_corrected/results.json` | Mapeamento físico independente e quatro assinaturas armazenadas | Não utilizar ordem visual dos pinos como ordem formal | Leonardo e Danilo | PENDENTE |
| O precharge termina antes de escrita e WL? | `physical/phase2/macro_binding.v`; transientes C1/C2 | Eventos 20%/80% e pré-carga de N/BL/BLB antes de cada acesso | TT sem RC de fios; taps não são gerador de fase qualificado em PVT | André e Leonardo | PENDENTE |
| Existe diferencial BL/BLB antes de habilitar sense? | `timing_*/phase.csv`; formas de onda integrais | Diferencial e sinal de SCLK observados no circuito real | Diferencial no cruzamento de SCLK não caracteriza offset/sensibilidade do SA | André | PENDENTE |
| SA_OUT/RAW, FF_D, FF_Q e DATA estão sendo distinguidos? | Contrato temporal; `tools/analyze_phase2_extension_timing.py` | Cruzamentos locais, janelas estáveis e transições reais | Setup Liberty TT/25 °C versus SPICE TT/27 °C; sem STA completo | André e Leonardo | PENDENTE |
| O barramento é liberado antes da direção externa? | C2 `bench.spice`, `checks.json`, medições de corrente | Medidores externos de 0 V e probe opositor de 1 kΩ | Piso de 50 µA instrumental; não leakage nem turnaround garantido | Leonardo e André | PENDENTE |
| A máscara viva preserva a operação e o último FF_Q? | RTL wrapper, C2 e `structure_corrected/results.json` | Oito enables físicos NAND com mesma função e checks de FF_Q | DATA pode exibir leitura anterior antes da nova descida | Leonardo | PENDENTE |
| A partida está documentada sem presumir conteúdo inicial? | `docs/phase2_final_polish.md`; cinco cenários históricos | 3.383 checks incluindo 240 bits, sem IC/nodeset | Não demonstra mínimo universal de partida nem yield | Danilo e Leonardo | PENDENTE |
| Síntese/GLS usam células HD e macro black box correta? | `physical/phase2/delivery.json`; síntese/GLS selecionadas | 20 FF, oito ebufn; 15.619 checks por execução | GLS sem atraso não estabelece timing elétrico | Leonardo | PENDENTE |
| Geometria final e referência conferem sem black boxes de LVS? | `reports/phase2/final_gds/`; recibos DRC/LVS e mutantes | 1.493 MOS; DRC zero e LVS após reimportação | Não houve alteração geométrica nesta extensão; não foi refeito DRC | Danilo e Leonardo | PENDENTE |
| Outro integrante consegue reanalisar as evidências? | Guia de reprodução, bundles opcionais e `clean_reproduction/` | Worktree limpo, restauração de sete raws e verificadores anteriores | Mesma imagem Linux/PDK; não foi regenerada a simulação no clone | Equipe | PENDENTE |

Os caminhos `structure_corrected/`, `timing_*/` e `clean_reproduction/`
referem-se a [`reports/phase2/extension_20261104/`](../reports/phase2/extension_20261104/).
Os resultados das campanhas novas são consolidados no
[relatório de cobertura](phase2_coverage_extension.md) e no
[relatório temporal](phase2_timing_extension.md).

## Registro da discussão

Para cada revisão, registrar nome, data, commit examinado, documentos e raws
utilizados, conclusão e pendências. O parecer técnico automatizado permanece
distinto desse registro. Não preencher aprovação em nome de outro integrante.
