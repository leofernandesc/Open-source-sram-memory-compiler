# Decoder compacto — campanha FF quente

## Resultado

Foi avaliado o perfil rápido/quente já definido no projeto: canto FF, 1,8 V e
125 °C. A matriz contém nove transições de endereço selecionadas, iguais às
usadas na matriz TT. As quatro saídas são exercitadas, mas isto não cobre as
16 combinações possíveis de endereço anterior/novo.

| Passo máximo | Esquemático | PEX | Checks do baseline | Checks do PEX |
|---:|---:|---:|---:|---:|
| 5 ps | 9/9 PASS | 9/9 PASS | 936/936 | 1.440/1.440 |
| 1 ps | 9/9 PASS | 9/9 PASS | 936/936 | 1.440/1.440 |
| 0,5 ps, caso de maior excursão | 1/1 PASS | 1/1 PASS | 104/104 | 160/160 |

No caso direcionado `01→10`, a maior magnitude de `VGD` no esquemático foi
1,949037 V a 1 ps e 1,949031 V a 0,5 ps. Isso deixa aproximadamente **0,963
mV** até a tela experimental de 1,95 V. O PEX atingiu 1,878690 V na matriz
completa a 1 ps e 1,878005 V no caso direcionado a 0,5 ps. Todos os casos
passaram a tela e os critérios lógicos/precharge. A tela de 1,95 V é um limite
experimental do checker, não um limite definido pela especificação nem uma
aprovação de confiabilidade.

| Métrica PEX | Máximo a 1 ps | Diferença máxima entre 5 ps e 1 ps |
|---|---:|---:|
| WL até 90% | 492,795 ps | 0,129 ps |
| Pré-carga do WL até 10% | 461,940 ps | 0,191 ps |
| Slew de subida do WL | 250,119 ps | 0,058 ps |
| Magnitude terminal examinada | 1,878690 V | 0,373 mV |

No baseline, o atraso máximo de WL a 90% foi 394,006 ps e a pré-carga até
10% foi 306,280 ps. Os deltas PEX menos schematic chegaram a 99,397 ps para
WL a 90% e 157,474 ps para a pré-carga. Essa comparação descreve somente
estes estímulos e a carga estimada usada no testbench.

## Avisos dos modelos

Os 38 logs ngspice foram inspecionados. Não apresentam linhas `Error:`; todos
os processos e manifests indicam conclusão sem erro. O ngspice registra,
porém, avisos para parâmetros dos modelos FF, incluindo `A2 > 1` (o próprio
ngspice informa que limita `A2` a 1 e define `A1` a 0), `Eta0 < 0` e alguns
valores negativos de `Pdibl1`/`Pdibl2`. Os checks da campanha passaram sob a
interpretação desses modelos pelo ngspice. Esses avisos devem ser discutidos
com os orientadores antes de tratar o canto FF como qualificação final de
confiabilidade ou de domínio de modelo.

## Escopo e arquivos

O PEX é o do layout compacto, SHA-256
`8ee6b99aabf94bde9a1de2a13f0c040cda41dd55bb9568672e38a7f6bb54a6dc`, com
762 resistores e 389 capacitores. O bench mantém quatro WL drivers
esquemáticos, cada um ligado a 17,4 fF estimados. Não representa a linha física
completa nem a macro 4×8.

- [Resumo auditável, hashes, medidas e avisos por campanha](../sims/row_decoder/results/compact_decoder_fast_hot_audit.json)
- [Matriz FF a 5 ps](../sims/row_decoder/results/compact_decoder_fast_5ps/comparison.csv)
- [Matriz FF a 1 ps](../sims/row_decoder/results/compact_decoder_fast_1ps/comparison.csv)
- [Caso de maior excursão a 0,5 ps](../sims/row_decoder/results/compact_decoder_fast_peak_0p5ps/comparison.csv)
- Cada deck e saída de ngspice estão sob `artifacts/`; cópias de texto dos
  logs estão nomeadas `ngspice_output.txt`. As waveforms binárias `.raw` não
  foram adicionadas ao Git.

Comandos reproduzidos no container headless `sram-pex-diag-20261008`, com
ngspice 44.2, Xschem 3.4.6 e o mesmo hash de modelos registrado nas duas
matrizes TT/SS anteriores:

```bash
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py \
  --profiles fast --max-step-ps 5 --workers 1 --timeout-s 300 \
  --output-root sims/row_decoder/results/compact_decoder_fast_5ps
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py \
  --profiles fast --max-step-ps 1 --workers 1 --timeout-s 300 \
  --output-root sims/row_decoder/results/compact_decoder_fast_1ps
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py \
  --profiles fast --cases fast_01_to_10 --max-step-ps 0.5 --workers 1 \
  --timeout-s 300 \
  --output-root sims/row_decoder/results/compact_decoder_fast_peak_0p5ps
```

Esta extensão cobre nove transições no perfil FF quente. Ruído/retenção,
variação/mismatch, captura/fanout de endereço e a carga da wordline física
continuam pendentes.
