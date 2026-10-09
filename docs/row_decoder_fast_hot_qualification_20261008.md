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

No caso direcionado `01→10`, o maior valor absoluto da diferença gate-drain
(`VGD`) no esquemático foi 1,949037 V a 1 ps e 1,949031 V a 0,5 ps. Isso fica
0,963 mV abaixo do limite numérico de 1,95 V usado pela tela do runner. Esse
valor não é margem de domínio do modelo: a documentação do SKY130 define faixas
assinadas para `VGS`, `VDS` e `VBS`, mas não para `VGD`. Assim, a tela atual de
`max(|VGS|, |VGD|, |VDS|) <= 1,95 V` é uma triagem numérica parcial do projeto, não
uma checagem completa do domínio SPICE. O PEX atingiu 1,878690 V nessa tela na
matriz a 1 ps e 1,878005 V no caso direcionado a 0,5 ps. Os casos passaram a
tela e aos critérios lógicos/pré-carga; isso não constitui aprovação de
confiabilidade nem de domínio do modelo.

Para referência, o PDK documenta `nfet_01v8` com `VDS` e `VGS` de 0 a +1,95 V
e `VBS` de -1,95 a +0,3 V; para `pfet_01v8`, `VDS` e `VGS` vão de 0 a -1,95 V
e `VBS` de -0,1 a +1,95 V. Os registros atuais guardam as tensões entre pinos,
mas ainda não fazem uma avaliação assinada e orientada por tipo de dispositivo
para essas três variáveis. A definição de faixa está na
[documentação de dispositivos do SKY130](https://github.com/google/skywater-pdk/blob/main/docs/rules/device-details.rst#L4-L100).

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
porém, avisos para parâmetros dos modelos FF, incluindo `A2 > 1` (o ngspice
limita `A2` a 1 e define `A1` a 0), `Eta0 < 0` e alguns valores negativos de
`Pdibl1`/`Pdibl2`. O [check BSIM4 do ngspice 44.2 para `A2`](https://github.com/imr/ngspice/blob/ngspice-44.2/src/spicelib/devices/bsim4v5/b4v5check.c#L485-L498)
confirma que `A2` e `A1` são alterados; os [checks dos parâmetros negativos](https://github.com/imr/ngspice/blob/ngspice-44.2/src/spicelib/devices/bsim4v5/b4v5check.c#L471-L575)
emitem avisos sem modificar `Eta0`, `Pdibl1` ou `Pdibl2` nessa rotina. Os 38
logs da campanha selecionada apresentaram `A2` e `Pdibl1` nas bins PFET
`pshort_model.32/.40`, `Pdibl2` em `pshort_model.32`, e `Eta0` nas bins NFET
`nshort_model.40/.48`. Isso identifica avisos de validação de parâmetros dos
modelos BSIM4 para as geometrias usadas; não é evidência de erro de
conectividade no esquemático. Os checks passaram sob o tratamento reportado
pelo ngspice, mas esses avisos continuam como ressalva para qualificação FF e
precisam da avaliação do responsável pelo modelo/PDK.

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
- [Convergência PCLK a 0,5 ps nos três cantos](../sims/row_decoder/results/compact_decoder_pclk_energy_convergence_audit.json)
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

## Matriz FF completa de pares de endereço — concluída

A opção `--all-address-pairs` foi executada no perfil `fast` (FF, 1,8 V,
125 °C), cobrindo as 16 transições ordenadas entre `00`, `01`, `10` e `11`,
incluindo endereço sem mudança. O baseline e o PEX compacto atual passaram
16/16 casos em cada passo temporal, sem falhas nos checks registrados.

| Passo máximo | Baseline | PEX | Checks baseline | Checks PEX | Máximo terminal baseline | Máximo terminal PEX |
|---:|---:|---:|---:|---:|---:|---:|
| 5 ps | 16/16 PASS | 16/16 PASS | 1.664/1.664 | 2.560/2.560 | 1,948349 V | 1,879030 V |
| 1 ps | 16/16 PASS | 16/16 PASS | 1.664/1.664 | 2.560/2.560 | 1,949037 V | 1,878690 V |

A 1 ps, o maior atraso do WL até 90% foi 394,006 ps no baseline e
492,795 ps no PEX. A maior pré-carga até 10% foi 306,280 ps e 461,940 ps,
respectivamente. O pico baseline de 1,949037 V é magnitude absoluta de `VGD`
na transição `01→10`, apenas 0,963 mV abaixo da tela numérica histórica de
1,95 V. Isso não representa margem assinada de domínio do modelo. O pico PEX
de magnitude terminal é 1,878690 V em `10→01`.

Entre 5 ps e 1 ps, os maiores deltas por par no PEX foram 0,130 ps em atraso
de WL, 0,191 ps em pré-carga, 0,058 ps em slew de subida do WL e 0,373 mV em
magnitude terminal. A energia PCLK teve variação máxima de 0,502 fJ no par
`01→00`. Na verificação direcionada a 0,5 ps, o PEX desse par foi
3,897121 fJ, contra 3,907003 fJ a 1 ps (0,253%); no baseline `01→11`, a
variação foi 0,576%. A revisão abrangeu também os casos mais sensíveis em TT
e SS; consulte a [auditoria de convergência PCLK](../sims/row_decoder/results/compact_decoder_pclk_energy_convergence_audit.json).

Os 64 logs ngspice desta matriz não contêm linhas `Error:`, mas todos mantêm
os avisos dos modelos FF vistos na campanha selecionada: `A2 > 1` (o ngspice
limita `A2` e redefine `A1`) e valores negativos de `Eta0`, `Pdibl1` e
`Pdibl2`. Logo, os checks lógicos e as telas de tensão passaram sob o
tratamento reportado pelo simulador, mas não demonstram domínio assinado
completo do modelo nem confiabilidade. As waveforms brutas totalizam
845.475.232 bytes, permanecem locais e são ignoradas pelo Git.

O audit JSON reúne hashes, contagem de avisos, resultados por passo e deltas
por transição: [matriz FF completa](../sims/row_decoder/results/compact_decoder_full_fast_matrix_audit.json).
As pastas de resultados contêm casos, checks, manifests, decks e logs de
texto: [5 ps](../sims/row_decoder/results/compact_decoder_full_fast_matrix_5ps/)
e [1 ps](../sims/row_decoder/results/compact_decoder_full_fast_matrix_1ps/).
O PEX é o arquivo compacto com SHA-256
`8ee6b99aabf94bde9a1de2a13f0c040cda41dd55bb9568672e38a7f6bb54a6dc`.

Comandos usados no container `sram-pex-diag-20261008`, um worker por vez:

```bash
SRAM_EDA_CONTAINER=sram-pex-diag-20261008 ./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py \
  --profiles fast --all-address-pairs --max-step-ps 5 --workers 1 \
  --timeout-s 900 --output-root sims/row_decoder/results/compact_decoder_full_fast_matrix_5ps
SRAM_EDA_CONTAINER=sram-pex-diag-20261008 ./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py \
  --profiles fast --all-address-pairs --max-step-ps 1 --workers 1 \
  --timeout-s 900 --output-root sims/row_decoder/results/compact_decoder_full_fast_matrix_1ps
```

Esta execução fecha a matriz FF completa para o testbench e carga registrados.
A revisão direcionada de energia PCLK a 0,5 ps está concluída para os pares
mais sensíveis de TT/SS/FF; entre 1 ps e 0,5 ps, o maior delta foi 0,889% no
baseline e 0,503% no PEX. Isso sustenta 1 ps como referência para os casos
registrados, sem substituir uma matriz completa a 0,5 ps ou medir dissipação
de um driver PCLK físico. Ainda não cobre PVT amplo, wordline física,
ruído, retenção, mismatch, captura/fanout de endereço ou comportamento da
macro completa. Os avisos FF foram interpretados, mas permanecem como ressalva
de qualificação dos modelos.
