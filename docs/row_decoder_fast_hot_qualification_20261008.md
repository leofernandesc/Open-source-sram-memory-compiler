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
[documentação de dispositivos do SKY130](https://github.com/google/skywater-pdk/blob/main/docs/rules/device-details.rst#L196-L248).

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
`Pdibl1`/`Pdibl2`. O código-fonte do ngspice confirma a correção de `A2` e os
avisos dos demais parâmetros
([checagens BSIM4 do ngspice](https://github.com/ngspice/ngspice/blob/master/src/spicelib/devices/bsim4v5/b4v5check.c#L2683-L2729)).
Os 38 logs apresentaram os avisos: `A2` e `Pdibl1` nas bins PFET
`pshort_model.32/.40`, `Pdibl2` em `pshort_model.32`, e `Eta0` nas bins NFET
`nshort_model.40/.48`. Isso aponta para verificações dos parâmetros dos
modelos BSIM4 selecionados para as geometrias usadas, e não para um erro de
conectividade no esquemático. `A2` é alterado pelo ngspice; os avisos de
parâmetros negativos não indicam que o simulador os corrige. Os checks da
campanha passaram sob essa interpretação dos modelos, mas os avisos devem ser
revistos antes de usar FF como qualificação final.

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

## Próxima execução: matriz completa de endereços

O runner agora aceita `--all-address-pairs`, mantendo inalterada a matriz
selecionada quando a opção é omitida. Para FF quente, a opção gera as 16
combinações ordenadas de endereço anterior e novo, incluindo as quatro
combinações sem mudança de endereço. A campanha completa a 1 ps é reservada à
máquina mais potente: a campanha FF existente de nove pares a 1 ps ocupa
398.621.348 bytes; por extrapolação linear, 16 pares podem ocupar perto de
710 MB. A execução existente de nove pares a 5 ps ocupa 82.377.000 bytes.
Essas estimativas variam com a quantidade de dados das waveforms. Execute
primeiro a 5 ps como triagem e depois a 1 ps na outra máquina, cada uma em
diretório novo:

```bash
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py \
  --profiles fast --all-address-pairs --max-step-ps 5 --workers 1 \
  --timeout-s 300 --output-root sims/row_decoder/results/fast_all_pairs_5ps
./tools/sram-eda python3 sims/row_decoder/run_row_decoder_pex_contract.py \
  --profiles fast --all-address-pairs --max-step-ps 1 --workers 1 \
  --timeout-s 300 --output-root sims/row_decoder/results/fast_all_pairs_1ps
```

Esse conjunto ainda qualifica somente FF/1,8 V/125 °C, o decoder extraído,
buffers WL esquemáticos e carga estimada de 17,4 fF.
